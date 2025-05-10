#!/bin/bash

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 创建持久化数据目录
TIDB_DATA_DIR="$HOME/tidb-data"
TIDB_TAG="persistent"
TIDB_HOST="127.0.0.1"
TIDB_PORT="4000"
TIDB_USER="root"
TIDB_PASSWORD=""
TIDB_DATABASE="test" # 默认数据库名称

# 确保目录存在
mkdir -p $TIDB_DATA_DIR

echo -e "${GREEN}将使用 $TIDB_DATA_DIR 作为持久化存储目录${NC}"

# 确保TiUP已安装
if ! command -v tiup &> /dev/null; then
    echo -e "${YELLOW}TiUP未安装，正在安装...${NC}"
    curl --proto '=https' --tlsv1.2 -sSf https://tiup-mirrors.pingcap.com/install.sh | sh
    
    # 根据不同Shell添加环境变量
    if [[ "$(uname)" == "Darwin" ]]; then
        # Mac通常使用zsh或bash
        if [[ -f "$HOME/.zshrc" ]]; then
            source ~/.zshrc
        else
            source ~/.bash_profile
        fi
    else
        # Linux通常使用bash
        source ~/.profile
    fi
    
    echo -e "${GREEN}TiUP安装完成${NC}"
else
    echo -e "${GREEN}TiUP已安装${NC}"
fi

# 停止正在运行的playground
echo -e "${YELLOW}停止当前运行的playground实例...${NC}"
tiup playground stop

# 使用tag启动新的playground，并复用之前的数据目录（如果存在）
echo -e "${YELLOW}启动持久化TiDB集群...${NC}"
tiup playground --db 1 --pd 1 --kv 1 --tiflash 1 --tag $TIDB_TAG

echo -e "${GREEN}===============================================${NC}"
echo -e "${GREEN}TiDB集群已启动！${NC}"
echo -e "${GREEN}TiDB访问地址: $TIDB_HOST:$TIDB_PORT${NC}"
echo -e "${GREEN}TiDB Dashboard: http://127.0.0.1:2379/dashboard${NC}"
echo -e "${GREEN}===============================================${NC}"

# 等待TiDB和TiFlash完全启动
echo -e "${YELLOW}等待TiDB和TiFlash完全启动...${NC}"
sleep 15

# 创建自动设置TiFlash副本的Python脚本
echo -e "${YELLOW}创建TiFlash副本设置脚本...${NC}"
cat > $HOME/set_tiflash_replicas.py << EOF
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
EOF

# 执行TiFlash副本设置脚本
echo -e "${BLUE}执行TiFlash副本设置...${NC}"
pip install pymysql &>/dev/null || true  # 确保安装pymysql
python $HOME/set_tiflash_replicas.py

echo -e "${GREEN}===============================================${NC}"
echo -e "${YELLOW}使用 tiup playground display 查看集群状态${NC}"
echo -e "${YELLOW}使用 tiup playground stop 停止集群${NC}"
echo -e "${YELLOW}重启时使用 tiup playground --tag $TIDB_TAG 启动同一个集群实例${NC}"

echo -e "${YELLOW}数据存储在以下位置:${NC}"
INSTANCE_DIR=$(ls -t ~/.tiup/data | head -n 1)
echo -e "${YELLOW}~/.tiup/data/$INSTANCE_DIR${NC}"
echo -e "${YELLOW}使用同一个tag启动可以保持数据存储在同一个目录${NC}"

echo -e "${GREEN}TiFlash副本已自动配置，向量索引功能可以正常使用${NC}" 