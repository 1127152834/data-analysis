#!/usr/bin/env python
"""
列出数据库中所有的表名，用于完善初始化脚本
"""
from app.core.db import engine
from sqlalchemy import inspect, text

def main():
    inspector = inspect(engine)
    
    # 获取所有表名
    table_names = inspector.get_table_names()
    print(f"数据库中共有 {len(table_names)} 个表:")
    
    for i, table_name in enumerate(sorted(table_names)):
        print(f"{i+1}. {table_name}")
    
    print("\n以下是已在初始化脚本中包含的表:")
    included_tables = [
        'users',
        'database_connections',
        'chats',
        'chat_messages',
        'chat_meta',
        'database_query_history'
    ]
    
    for table in included_tables:
        print(f"- {table}")
    
    print("\n需要在初始化脚本中添加的表:")
    for table_name in sorted(table_names):
        if table_name not in included_tables and table_name != 'alembic_version':
            print(f"- {table_name}")

if __name__ == "__main__":
    main() 