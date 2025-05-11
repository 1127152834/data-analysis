from typing import Type

from sqlalchemy import func, delete
from sqlmodel import Session, select, SQLModel
from app.repositories.base_repo import BaseRepo

from app.models import (
    Document as DBDocument,
)


class ChunkRepo(BaseRepo):
    def __init__(self, chunk_model: Type[SQLModel]):
        self.model_cls = chunk_model

    def document_exists_chunks(self, session: Session, document_id: int) -> bool:
        return (
            session.exec(
                select(self.model_cls).where(self.model_cls.document_id == document_id)
            ).first()
            is not None
        )

    def get_documents_by_chunk_ids(
        self, session: Session, chunk_ids: list[str]
    ) -> list[DBDocument]:
        stmt = select(DBDocument).where(
            DBDocument.id.in_(
                select(self.model_cls.document_id).where(
                    self.model_cls.id.in_(chunk_ids),
                )
            ),
        )
        return list(session.exec(stmt).all())

    def get_document_chunks(self, session: Session, document_id: int):
        return session.exec(
            select(self.model_cls).where(self.model_cls.document_id == document_id)
        ).all()

    def get_chunk_by_hash(self, session: Session, document_id: int, chunk_hash: str):
        """
        通过hash查找特定文档中的chunk
        
        Args:
            session: 数据库会话
            document_id: 文档ID
            chunk_hash: chunk的哈希值
            
        Returns:
            匹配的chunk对象，如果未找到则返回None
        """
        return session.exec(
            select(self.model_cls).where(
                self.model_cls.document_id == document_id,
                self.model_cls.hash == chunk_hash
            )
        ).first()
        
    def get_chunk_by_hash_only(self, session: Session, chunk_hash: str):
        """
        仅通过hash查找chunk（不限定文档ID）
        
        Args:
            session: 数据库会话
            chunk_hash: chunk的哈希值
            
        Returns:
            匹配的chunk对象，如果未找到则返回None
        """
        return session.exec(
            select(self.model_cls).where(
                self.model_cls.hash == chunk_hash
            )
        ).first()

    def fetch_by_document_ids(self, session: Session, document_ids: list[int]):
        return session.exec(
            select(self.model_cls).where(self.model_cls.document_id.in_(document_ids))
        ).all()

    def count(self, session: Session):
        return session.scalar(select(func.count(self.model_cls.id)))

    def delete_by_datasource(self, session: Session, datasource_id: int):
        doc_ids_subquery = select(DBDocument.id).where(
            DBDocument.data_source_id == datasource_id
        )
        stmt = delete(self.model_cls).where(
            self.model_cls.document_id.in_(doc_ids_subquery)
        )
        session.exec(stmt)

    def delete_by_document(self, session: Session, document_id: int):
        stmt = delete(self.model_cls).where(self.model_cls.document_id == document_id)
        session.exec(stmt)
