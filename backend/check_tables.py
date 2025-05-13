#!/usr/bin/env python
"""
检查数据库中的表
"""
from app.core.db import engine
from sqlalchemy import text

def main():
    with engine.connect() as conn:
        result = conn.execute(text('SHOW TABLES'))
        tables = [row[0] for row in result]
        print("数据库中的表:")
        for table in sorted(tables):
            print(f"- {table}")
        
        # 检查特定表是否存在
        print("\n检查特定表:")
        for table_name in ['database_connections', 'database_query_history']:
            exists = table_name in tables
            print(f"- {table_name}: {'存在' if exists else '不存在'}")

if __name__ == "__main__":
    main() 