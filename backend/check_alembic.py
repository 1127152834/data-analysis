#!/usr/bin/env python
"""
检查alembic_version表
"""
from app.core.db import engine
from sqlalchemy import text

def main():
    with engine.connect() as conn:
        # 检查alembic_version表中的内容
        result = conn.execute(text('SELECT * FROM alembic_version'))
        versions = [row[0] for row in result]
        print("当前的alembic版本:")
        for version in versions:
            print(f"- {version}")
            
        # 再次重置alembic_version表
        conn.execute(text('DROP TABLE alembic_version'))
        print("\nalembic_version表已删除，请再次运行 'python -m alembic revision --autogenerate -m initial_schema'")

if __name__ == "__main__":
    main() 