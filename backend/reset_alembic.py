#!/usr/bin/env python
"""
重置并重新创建Alembic迁移脚本
"""

import os
import shutil
from sqlalchemy import text
from app.core.db import engine


def main():
    # 1. 删除alembic_version表
    print("删除alembic_version表...")
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS alembic_version"))

    # 2. 清空versions目录
    versions_dir = os.path.join("app", "alembic", "versions")
    print(f"清空迁移脚本目录: {versions_dir}")
    for file in os.listdir(versions_dir):
        if file.endswith(".py") and file != "__init__.py":
            file_path = os.path.join(versions_dir, file)
            os.remove(file_path)
            print(f"已删除: {file_path}")

    print("Migration history reset successfully!")
    print(
        "Now run 'python -m alembic revision --autogenerate -m initial_schema' to create a new initial migration"
    )


if __name__ == "__main__":
    main()
