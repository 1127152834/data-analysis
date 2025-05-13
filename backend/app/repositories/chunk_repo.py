import logging
import sqlalchemy as sa
from sqlalchemy.orm import Session
from sqlalchemy.sql import text
from typing import Optional, List, Any
from app.models.knowledge_base_scoped.table_naming import CHUNKS_TABLE_PREFIX

logger = logging.getLogger(__name__)


class ChunkRepo:
    def __init__(self, db_session: Session):
        self.db_session = db_session

    def get_chunk_by_id(self, chunk_id: str) -> Optional[Any]:
        """
        通过ID获取chunk内容

        Args:
            chunk_id: chunk ID

        Returns:
            匹配的chunk对象，如果未找到则返回None
        """
        try:
            # 获取所有chunks_开头的表
            inspector = sa.inspect(self.db_session.bind)
            table_names = inspector.get_table_names()

            # 记录所有发现的表名以便调试
            logger.info(f"数据库中的所有表: {table_names}")

            # 过滤出所有chunks_开头的表（不区分大小写）
            chunk_tables = [
                name
                for name in table_names
                if name.lower().startswith(CHUNKS_TABLE_PREFIX.lower())
            ]

            # 也查询默认chunks表
            if "chunks" in table_names:
                chunk_tables.append("chunks")

            logger.info(f"将要查询的chunk表: {chunk_tables}")
            logger.info(f"查询的chunk ID: {chunk_id}")

            # 在所有表中查找匹配ID的chunk
            for table_name in chunk_tables:
                try:
                    # 执行原生SQL查询，获取文本内容
                    query = text(f"SELECT * FROM {table_name} WHERE id = :id LIMIT 1")
                    result = self.db_session.execute(query, {"id": chunk_id}).first()

                    if result:
                        # 记录找到结果的表
                        logger.info(f"在表 {table_name} 中找到ID为 {chunk_id} 的chunk")
                        return result
                except Exception as e:
                    logger.warning(f"查询表 {table_name} 时出错: {e}")
                    continue

            # 如果所有表都没找到，返回None
            logger.warning(f"在所有表中都未找到ID为 {chunk_id} 的chunk")
            return None

        except Exception as e:
            logger.error(f"获取chunk时发生错误: {str(e)}")
            return None

    def get_chunk_by_hash(self, chunk_hash: str) -> Optional[Any]:
        """
        通过哈希获取chunk内容

        Args:
            chunk_hash: chunk哈希值

        Returns:
            匹配的chunk对象，如果未找到则返回None
        """
        try:
            # 获取所有chunks_开头的表
            inspector = sa.inspect(self.db_session.bind)
            table_names = inspector.get_table_names()

            # 过滤出所有chunks_开头的表
            chunk_tables = [
                name
                for name in table_names
                if name.lower().startswith(CHUNKS_TABLE_PREFIX.lower())
            ]

            # 也查询默认chunks表
            if "chunks" in table_names:
                chunk_tables.append("chunks")

            logger.info(f"将要查询的chunk表: {chunk_tables}")
            logger.info(f"查询的chunk哈希: {chunk_hash}")

            # 在所有表中查找匹配哈希的chunk
            for table_name in chunk_tables:
                try:
                    # 执行原生SQL查询，获取文本内容
                    query = text(
                        f"SELECT * FROM {table_name} WHERE hash = :hash LIMIT 1"
                    )
                    result = self.db_session.execute(
                        query, {"hash": chunk_hash}
                    ).first()

                    if result:
                        # 记录找到结果的表
                        logger.info(
                            f"在表 {table_name} 中找到哈希为 {chunk_hash} 的chunk"
                        )
                        return result
                except Exception as e:
                    logger.warning(f"查询表 {table_name} 时出错: {e}")
                    continue

            # 如果所有表都没找到，返回None
            logger.warning(f"在所有表中都未找到哈希为 {chunk_hash} 的chunk")
            return None

        except Exception as e:
            logger.error(f"获取chunk时发生错误: {str(e)}")
            return None
