from app.repositories.database_connection import DatabaseConnectionRepo
from app.models.database_connection import ConnectionStatus
from app.rag.database.connectors.mysql import MySQLConnector
from datetime import datetime
from app.core.db import get_db_session

# 获取连接信息
repo = DatabaseConnectionRepo()
session = next(get_db_session())
conn = repo.get(session, 2)  # 使用刚刚创建的TiDB连接ID

try:
    print(f"尝试连接到 {conn.name}...")
    
    # 使用MySQL连接器（TiDB兼容MySQL协议）
    connector = MySQLConnector(conn)  # 传入整个数据库连接对象
    
    # 测试查询版本
    results, error = connector.execute_query('SELECT VERSION() as version')
    if error:
        raise Exception(f"查询版本失败: {error}")
    print(f'连接TiDB成功！版本: {results[0]["version"]}')
    
    # 获取所有数据库
    results, error = connector.execute_query('SHOW DATABASES')
    if error:
        raise Exception(f"查询数据库列表失败: {error}")
    print('\n可用数据库:')
    for db in results:
        print(f'- {db["Database"]}')
    
    # 获取所有表（在mysql数据库中）
    results, error = connector.execute_query('SHOW TABLES FROM mysql')
    if error:
        raise Exception(f"查询表列表失败: {error}")
    print('\nmysql数据库中的表:')
    for table in results:
        print(f'- {table["Tables_in_mysql"]}')
    
    # 更新连接状态
    repo.update_status(
        session,
        conn.id, 
        ConnectionStatus.CONNECTED, 
        datetime.now()
    )
    print('\n连接状态已更新为已连接。')
    
except Exception as e:
    print(f'连接失败: {str(e)}') 