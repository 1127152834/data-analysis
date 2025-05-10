import os
from sqlalchemy import create_engine, text

# 直接使用test数据库，不依赖环境变量
host = '127.0.0.1'  
user = 'root'
password = ''
database = 'test'  # 明确使用test数据库

# 构建连接字符串
connection_string = f"mysql+pymysql://{user}:{password}@{host}:4000/{database}"
print(f"连接字符串: {connection_string}")

try:
    # 尝试连接
    engine = create_engine(connection_string)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT VERSION()"))
        version = result.fetchone()[0]
        print(f"连接成功，数据库版本: {version}")
except Exception as e:
    print(f"连接失败: {str(e)}") 