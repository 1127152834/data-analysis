#!/usr/bin/env python3
"""
TiFlash补丁脚本 - 修复TiDB向量索引需要TiFlash副本的问题

此脚本通过猴子补丁方式修改tidb_vector库的create_vector_index方法，
确保在创建向量索引前自动设置TiFlash副本。

使用方法:
1. 在应用启动前导入此模块
2. 或添加到应用的启动脚本中
"""

import logging
import time
from sqlalchemy import text
import tidb_vector.sqlalchemy.adaptor

# 保存原始方法
original_create_vector_index = (
    tidb_vector.sqlalchemy.adaptor.VectorAdaptor.create_vector_index
)

logger = logging.getLogger("tiflash_patch")


def patched_create_vector_index(
    self,
    column,
    distance_metric,
    skip_existing=False,
    enable_tiflash=True,
    wait_for_tiflash=True,
):
    """
    创建向量索引的补丁方法

    自动为表设置TiFlash副本，然后等待副本同步完成后再创建向量索引

    参数:
        column: SQLAlchemy列对象
        distance_metric: 距离度量方法
        skip_existing: 是否跳过已存在的索引
        enable_tiflash: 是否启用TiFlash副本(默认为True)
        wait_for_tiflash: 是否等待TiFlash副本同步完成(默认为True)
    """
    self._check_vector_column(column)

    if column.type.dim is None:
        raise ValueError("Vector index is only supported for fixed dimension vectors")

    if skip_existing:
        if self.has_vector_index(column):
            return

    with self.engine.begin() as conn:
        table_name = conn.dialect.identifier_preparer.format_table(column.table)

        if enable_tiflash:
            try:
                # 获取当前表所在的数据库
                db_query = text("SELECT DATABASE()")
                db_result = conn.execute(db_query).scalar()

                # 检查表是否已有TiFlash副本
                check_query = text(
                    "SELECT TABLE_NAME, AVAILABLE, PROGRESS FROM information_schema.tiflash_replica "
                    "WHERE TABLE_SCHEMA = :db AND TABLE_NAME = :table"
                )
                check_result = conn.execute(
                    check_query, {"db": db_result, "table": column.table.name}
                ).fetchone()

                if not check_result:
                    # 设置TiFlash副本
                    logger.info(f"为表 {table_name} 设置TiFlash副本")
                    set_query = text(f"ALTER TABLE {table_name} SET TIFLASH REPLICA 1")
                    conn.execute(set_query)

                    if wait_for_tiflash:
                        # 等待TiFlash副本同步完成
                        max_wait = 60  # 最多等待60秒
                        for i in range(max_wait):
                            sync_query = text(
                                "SELECT AVAILABLE, PROGRESS FROM information_schema.tiflash_replica "
                                "WHERE TABLE_SCHEMA = :db AND TABLE_NAME = :table"
                            )
                            sync_result = conn.execute(
                                sync_query,
                                {"db": db_result, "table": column.table.name},
                            ).fetchone()

                            if sync_result and sync_result[0] == 1:  # AVAILABLE = 1
                                logger.info(
                                    f"表 {table_name} 的TiFlash副本同步完成，进度: {sync_result[1]}"
                                )
                                break

                            logger.info(
                                f"正在等待表 {table_name} 的TiFlash副本同步...({i + 1}/{max_wait})"
                            )
                            time.sleep(1)
                else:
                    if check_result[1] != 1 and wait_for_tiflash:  # AVAILABLE != 1
                        # 等待已存在但未同步完成的TiFlash副本
                        max_wait = 60  # 最多等待60秒
                        for i in range(max_wait):
                            sync_query = text(
                                "SELECT AVAILABLE, PROGRESS FROM information_schema.tiflash_replica "
                                "WHERE TABLE_SCHEMA = :db AND TABLE_NAME = :table"
                            )
                            sync_result = conn.execute(
                                sync_query,
                                {"db": db_result, "table": column.table.name},
                            ).fetchone()

                            if sync_result and sync_result[0] == 1:  # AVAILABLE = 1
                                logger.info(
                                    f"表 {table_name} 的TiFlash副本同步完成，进度: {sync_result[1]}"
                                )
                                break

                            logger.info(
                                f"正在等待表 {table_name} 的TiFlash副本同步...({i + 1}/{max_wait})"
                            )
                            time.sleep(1)

            except Exception as e:
                logger.error(f"设置TiFlash副本时出错: {e}")

    # 调用原始方法创建向量索引
    return original_create_vector_index(
        self, column, distance_metric, skip_existing, enable_tiflash=False
    )


# 应用猴子补丁
tidb_vector.sqlalchemy.adaptor.VectorAdaptor.create_vector_index = (
    patched_create_vector_index
)

logger.info("已应用TiFlash补丁，向量索引创建前将自动设置TiFlash副本")

if __name__ == "__main__":
    print("TiFlash补丁已应用。请在启动应用前导入此模块。")
    print("例如: python -c 'import tiflash_patch' -m your_app")
