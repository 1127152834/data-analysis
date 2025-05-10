import os
from dotenv import load_dotenv
from app.core.config import settings

# 确保加载.env文件
load_dotenv()

# 打印环境变量
print("环境变量:")
print(f"TIDB_HOST={os.environ.get('TIDB_HOST')}")
print(f"TIDB_USER={os.environ.get('TIDB_USER')}")
print(f"TIDB_DATABASE={os.environ.get('TIDB_DATABASE')}")
print(f"TIDB_SSL={os.environ.get('TIDB_SSL')}")

# 打印配置对象中的值
print("\n配置对象:")
print(f"settings.TIDB_HOST={settings.TIDB_HOST}")
print(f"settings.TIDB_USER={settings.TIDB_USER}")
print(f"settings.TIDB_DATABASE={settings.TIDB_DATABASE}")
print(f"settings.TIDB_SSL={settings.TIDB_SSL}")

# 打印实际的数据库URI
print("\n数据库连接字符串:")
print(f"SQLALCHEMY_DATABASE_URI={settings.SQLALCHEMY_DATABASE_URI}")
print(f"SQLALCHEMY_ASYNC_DATABASE_URI={settings.SQLALCHEMY_ASYNC_DATABASE_URI}")
