import os
from sqlalchemy import create_engine, text

# 打印环境变量
print(f"TIDB_HOST: {os.environ.get('TIDB_HOST', '未设置')}")
print(f"TIDB_USER: {os.environ.get('TIDB_USER', '未设置')}")
print(f"TIDB_PASSWORD: {os.environ.get('TIDB_PASSWORD', '未设置')}")
print(f"TIDB_DATABASE: {os.environ.get('TIDB_DATABASE', '未设置')}")
print(f"TIDB_SSL: {os.environ.get('TIDB_SSL', '未设置')}")

# 尝试从环境变量构建连接字符串
host = os.environ.get("TIDB_HOST", "127.0.0.1")
user = os.environ.get("TIDB_USER", "root")
password = os.environ.get("TIDB_PASSWORD", "")
database = os.environ.get("TIDB_DATABASE", "test")
use_ssl = os.environ.get("TIDB_SSL", "false").lower() == "true"

# 构建连接字符串
connection_string = f"mysql+pymysql://{user}:{password}@{host}:4000/{database}"
if use_ssl:
    connection_string += "?ssl_verify_cert=true&ssl_verify_identity=true"

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
