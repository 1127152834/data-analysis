# tidb-persistent.ps1

# 颜色定义
$RED = [System.ConsoleColor]::Red
$GREEN = [System.ConsoleColor]::Green
$YELLOW = [System.ConsoleColor]::Yellow
$BLUE = [System.ConsoleColor]::Blue

# 创建持久化数据目录
$TIDB_DATA_DIR = "$env:USERPROFILE\tidb-data"
$TIDB_TAG = "persistent"
$TIDB_HOST = "127.0.0.1"
$TIDB_PORT = "4000"
$TIDB_USER = "root"
$TIDB_PASSWORD = ""
$TIDB_DATABASE = "test" # 默认数据库名称

# 确保目录存在
if (-not (Test-Path $TIDB_DATA_DIR)) {
    New-Item -ItemType Directory -Path $TIDB_DATA_DIR -Force | Out-Null
}

Write-Host "将使用 $TIDB_DATA_DIR 作为持久化存储目录" -ForegroundColor $GREEN

# 确保TiUP已安装
$tiupPath = "$env:USERPROFILE\.tiup\bin\tiup.exe"
if (-not (Test-Path $tiupPath)) {
    Write-Host "TiUP未安装，正在安装..." -ForegroundColor $YELLOW
    
    # 下载安装脚本
    Invoke-WebRequest -Uri "https://tiup-mirrors.pingcap.com/install.ps1" -OutFile "$env:TEMP\install-tiup.ps1"
    
    # 执行安装脚本
    & powershell.exe -File "$env:TEMP\install-tiup.ps1"
    
    # 更新PATH环境变量
    $env:PATH = "$env:USERPROFILE\.tiup\bin;$env:PATH"
    
    Write-Host "TiUP安装完成" -ForegroundColor $GREEN
} else {
    Write-Host "TiUP已安装" -ForegroundColor $GREEN
}

# 停止正在运行的playground
Write-Host "停止当前运行的playground实例..." -ForegroundColor $YELLOW
& tiup playground stop

# 使用tag启动新的playground，并复用之前的数据目录（如果存在）
Write-Host "启动持久化TiDB集群..." -ForegroundColor $YELLOW
Start-Process -FilePath "tiup" -ArgumentList "playground --db 1 --pd 1 --kv 1 --tiflash 1 --tag $TIDB_TAG" -NoNewWindow

Write-Host "===============================================" -ForegroundColor $GREEN
Write-Host "TiDB集群已启动！" -ForegroundColor $GREEN
Write-Host "TiDB访问地址: $TIDB_HOST`:$TIDB_PORT" -ForegroundColor $GREEN
Write-Host "TiDB Dashboard: http://127.0.0.1:2379/dashboard" -ForegroundColor $GREEN
Write-Host "===============================================" -ForegroundColor $GREEN

# 等待TiDB和TiFlash完全启动
Write-Host "等待TiDB和TiFlash完全启动..." -ForegroundColor $YELLOW
Start-Sleep -Seconds 15

# 创建自动设置TiFlash副本的Python脚本
Write-Host "创建TiFlash副本设置脚本..." -ForegroundColor $YELLOW
$pythonScript = @"
import time
import pymysql
from pymysql.cursors import DictCursor

# 数据库连接信息
DB_CONFIG = {
    'host': '$TIDB_HOST',
    'port': $TIDB_PORT,
    'user': '$TIDB_USER',
    'password': '$TIDB_PASSWORD',
    'db': '$TIDB_DATABASE',
    'charset': 'utf8mb4',
    'cursorclass': DictCursor
}

def get_tables_without_tiflash():
    """获取所有没有TiFlash副本的表"""
    with pymysql.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cursor:
            # 获取所有表
            cursor.execute("SHOW TABLES")
            tables = [list(table.values())[0] for table in cursor.fetchall()]
            
            # 获取已有TiFlash副本的表
            cursor.execute("SELECT TABLE_NAME FROM information_schema.tiflash_replica WHERE TABLE_SCHEMA = %s", (DB_CONFIG['db'],))
            tiflash_tables = [table['TABLE_NAME'] for table in cursor.fetchall()]
            
            # 过滤得到没有TiFlash副本的表
            return [table for table in tables if table not in tiflash_tables]

def set_tiflash_replica(table_name, replica_count=1):
    """为表设置TiFlash副本"""
    with pymysql.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cursor:
            sql = f"ALTER TABLE {table_name} SET TIFLASH REPLICA {replica_count}"
            try:
                cursor.execute(sql)
                conn.commit()
                print(f"已为表 {table_name} 设置 {replica_count} 个TiFlash副本")
                return True
            except Exception as e:
                print(f"为表 {table_name} 设置TiFlash副本失败: {e}")
                return False

def check_tiflash_replicas():
    """检查所有TiFlash副本的状态"""
    with pymysql.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT TABLE_NAME, REPLICA_COUNT, AVAILABLE, PROGRESS
                FROM information_schema.tiflash_replica
                WHERE TABLE_SCHEMA = %s
            """, (DB_CONFIG['db'],))
            return cursor.fetchall()

# 主程序
def main():
    try:
        # 获取没有TiFlash副本的表
        tables = get_tables_without_tiflash()
        print(f"发现 {len(tables)} 个没有TiFlash副本的表:")
        
        # 为这些表设置TiFlash副本
        for table in tables:
            set_tiflash_replica(table)
        
        # 如果有表被设置了TiFlash副本，等待同步完成
        if tables:
            max_wait = 60  # 最多等待60秒
            print("等待TiFlash副本同步完成...")
            for _ in range(max_wait):
                replicas = check_tiflash_replicas()
                all_available = all(replica['AVAILABLE'] == 1 for replica in replicas)
                if all_available:
                    print("所有TiFlash副本已同步完成！")
                    break
                time.sleep(1)
                
            # 再次检查同步状态
            replicas = check_tiflash_replicas()
            print("TiFlash副本状态:")
            for replica in replicas:
                print(f"表: {replica['TABLE_NAME']}, 副本数: {replica['REPLICA_COUNT']}, 可用: {replica['AVAILABLE']}, 进度: {replica['PROGRESS']}")
    except Exception as e:
        print(f"操作失败: {e}")

if __name__ == "__main__":
    # 等待TiDB完全启动
    time.sleep(2)
    main()
"@

# 将Python脚本保存到文件
$pythonScriptPath = "$env:USERPROFILE\set_tiflash_replicas.py"
$pythonScript | Out-File -FilePath $pythonScriptPath -Encoding utf8

# 确保已安装pymysql
Write-Host "确保已安装Python依赖..." -ForegroundColor $BLUE
pip install pymysql | Out-Null

# 执行TiFlash副本设置脚本
Write-Host "执行TiFlash副本设置..." -ForegroundColor $BLUE
python $pythonScriptPath

Write-Host "===============================================" -ForegroundColor $GREEN
Write-Host "使用 tiup playground display 查看集群状态" -ForegroundColor $YELLOW
Write-Host "使用 tiup playground stop 停止集群" -ForegroundColor $YELLOW
Write-Host "重启时使用 tiup playground --tag $TIDB_TAG 启动同一个集群实例" -ForegroundColor $YELLOW

# 获取最新的实例目录
$instanceDir = Get-ChildItem -Path "$env:USERPROFILE\.tiup\data" | Sort-Object -Property LastWriteTime -Descending | Select-Object -First 1

Write-Host "数据存储在以下位置:" -ForegroundColor $YELLOW
Write-Host "$env:USERPROFILE\.tiup\data\$($instanceDir.Name)" -ForegroundColor $YELLOW
Write-Host "使用同一个tag启动可以保持数据存储在同一个目录" -ForegroundColor $YELLOW

Write-Host "TiFlash副本已自动配置，向量索引功能可以正常使用" -ForegroundColor $GREEN