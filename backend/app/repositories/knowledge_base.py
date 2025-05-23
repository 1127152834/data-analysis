from typing import List, Optional, Type
from datetime import datetime, UTC
import logging

from sqlalchemy import delete
from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import SQLModel, select, Session, func, update
from fastapi_pagination import Params, Page
from fastapi_pagination.ext.sqlmodel import paginate

from app.api.admin_routes.knowledge_base.models import (
    VectorIndexError,
    KGIndexError,
    KnowledgeBaseUpdate,
)
from app.exceptions import KBDataSourceNotFound, KBNotFound
from app.models import (
    KnowledgeBase,
    Document,
    DocIndexTaskStatus,
    KgIndexStatus,
    KnowledgeBaseDataSource,
)
from app.models.chat_engine import ChatEngine
from app.models.chunk import get_kb_chunk_model
from app.models.data_source import DataSource
from app.models.knowledge_base import IndexMethod
from app.repositories.base_repo import BaseRepo
from app.repositories.chunk import ChunkRepo
from app.repositories.graph import get_kb_graph_repo

logger = logging.getLogger("knowledge_base")


class KnowledgeBaseRepo(BaseRepo):
    model_cls = KnowledgeBase

    def paginate(
        self, session: Session, params: Params | None = Params()
    ) -> Page[KnowledgeBase]:
        query = (
            select(KnowledgeBase)
            .where(KnowledgeBase.deleted_at == None)
            .order_by(KnowledgeBase.created_at.desc())
        )
        return paginate(session, query, params)

    def get(
        self, session: Session, knowledge_base_id: int, show_soft_deleted: bool = True
    ) -> Optional[KnowledgeBase]:
        stmt = select(KnowledgeBase).where(KnowledgeBase.id == knowledge_base_id)

        if not show_soft_deleted:
            stmt = stmt.where(KnowledgeBase.deleted_at == None)

        return session.exec(stmt).first()

    def must_get(
        self, session: Session, knowledge_base_id: int, show_soft_deleted: bool = True
    ) -> Optional[KnowledgeBase]:
        kb = self.get(session, knowledge_base_id, show_soft_deleted)
        if kb is None:
            raise KBNotFound(knowledge_base_id)
        return kb

    def get_by_ids(
        self, session: Session, knowledge_base_ids: List[int]
    ) -> List[KnowledgeBase]:
        return session.exec(
            select(KnowledgeBase).where(KnowledgeBase.id.in_(knowledge_base_ids))
        ).all()

    def update(
        self,
        session: Session,
        knowledge_base: KnowledgeBase,
        partial_update: KnowledgeBaseUpdate,
    ) -> KnowledgeBase:
        for field, value in partial_update.model_dump(exclude_unset=True).items():
            setattr(knowledge_base, field, value)
            flag_modified(knowledge_base, field)

        session.commit()
        session.refresh(knowledge_base)
        return knowledge_base

    def delete(self, session: Session, knowledge_base: KnowledgeBase) -> None:
        knowledge_base.deleted_at = datetime.now(UTC)
        session.add(knowledge_base)
        session.commit()

    def get_index_overview(self, session: Session, kb: KnowledgeBase) -> dict:
        # TODO: store and query the count numbers in the knowledge base table.
        documents_total = self.count_documents(session, kb)
        chunks_total = self.count_chunks(session, kb)
        overview_data = {
            "documents": {"total": documents_total},
            "chunks": {"total": chunks_total},
        }

        if IndexMethod.VECTOR in kb.index_methods:
            overview_data.update(
                self.count_documents_by_vector_index_status(session, kb)
            )

        if IndexMethod.KNOWLEDGE_GRAPH in kb.index_methods:
            relationships_total = self.count_relationships(session, kb)
            entities_total = self.count_entities(session, kb)
            overview_data.update(
                {
                    "entities": {"total": entities_total},
                    "relationships": {"total": relationships_total},
                }
            )
            overview_data.update(self.count_chunks_by_kg_index_status(session, kb))

        return overview_data

    def count_data_sources(self, session: Session, kb: KnowledgeBase) -> int:
        return session.scalar(
            select(func.count(KnowledgeBaseDataSource.data_source_id)).where(
                KnowledgeBaseDataSource.knowledge_base_id == kb.id
            )
        )

    def count_documents(self, session: Session, kb: KnowledgeBase) -> int:
        return session.scalar(
            select(func.count(Document.id)).where(Document.knowledge_base_id == kb.id)
        )

    def count_chunks(self, session: Session, kb: KnowledgeBase):
        chunk_repo = ChunkRepo(get_kb_chunk_model(kb))
        return chunk_repo.count(session)

    def count_relationships(self, session: Session, kb: KnowledgeBase):
        graph_repo = get_kb_graph_repo(kb)
        return graph_repo.count_relationships(session)

    def count_entities(self, session: Session, kb: KnowledgeBase):
        graph_repo = get_kb_graph_repo(kb)
        return graph_repo.count_entities(session)

    def count_documents_by_vector_index_status(
        self, session: Session, kb: KnowledgeBase
    ) -> dict:
        stmt = (
            select(Document.index_status, func.count(Document.id))
            .where(Document.knowledge_base_id == kb.id)
            .group_by(Document.index_status)
            .order_by(Document.index_status)
        )
        results = session.exec(stmt).all()
        vector_index_status = {s: c for s, c in results}

        return {
            "vector_index": vector_index_status,
        }

    def count_chunks_by_kg_index_status(
        self, session: Session, kb: KnowledgeBase
    ) -> dict:
        # FIXME: Maybe we should count the documents (instead of chunks) like vector index?
        chunk_model = get_kb_chunk_model(kb)
        stmt = (
            select(chunk_model.index_status, func.count(chunk_model.id))
            .where(chunk_model.document.has(Document.knowledge_base_id == kb.id))
            .group_by(chunk_model.index_status)
            .order_by(chunk_model.index_status)
        )
        results = session.exec(stmt).all()
        kg_index_status = {s: c for s, c in results}

        return {"kg_index": kg_index_status}

    def batch_update_document_status(
        self, session: Session, document_ids: list[int], status: DocIndexTaskStatus
    ):
        stmt = (
            update(Document)
            .where(Document.id.in_(document_ids))
            .values(index_status=status)
        )
        session.exec(stmt)
        session.commit()

    def set_failed_documents_status_to_pending(
        self, session: Session, kb: KnowledgeBase
    ) -> list[int]:
        stmt = select(Document.id).where(
            Document.knowledge_base_id == kb.id,
            Document.index_status == DocIndexTaskStatus.FAILED,
        )
        failed_document_ids = session.exec(stmt).all()
        self.batch_update_document_status(
            session, failed_document_ids, DocIndexTaskStatus.PENDING
        )
        return failed_document_ids

    def batch_update_chunk_status(
        self,
        session: Session,
        chunk_model: Type[SQLModel],
        chunk_ids: list[int],
        status: KgIndexStatus,
    ):
        stmt = (
            update(chunk_model)
            .where(chunk_model.id.in_(chunk_ids))
            .values(index_status=status)
        )
        session.exec(stmt)
        session.commit()

    def set_failed_chunks_status_to_pending(
        self, session: Session, kb: KnowledgeBase
    ) -> list[int]:
        chunk_model = get_kb_chunk_model(kb)
        stmt = select(chunk_model.id).where(
            chunk_model.document.has(Document.knowledge_base_id == kb.id),
            chunk_model.index_status == KgIndexStatus.FAILED,
        )
        chunk_ids = session.exec(stmt).all()

        # Update status.
        self.batch_update_chunk_status(
            session, chunk_model, chunk_ids, KgIndexStatus.PENDING
        )

        return chunk_ids

    def list_vector_index_built_errors(
        self,
        session: Session,
        kb: KnowledgeBase,
        params: Params | None = Params(),
    ) -> Page[VectorIndexError]:
        query = (
            select(
                Document.id,
                Document.name,
                Document.source_uri,
                Document.index_result,
            )
            .where(
                Document.knowledge_base_id == kb.id,
                Document.index_status == DocIndexTaskStatus.FAILED,
            )
            .order_by(Document.id.desc())
        )

        return paginate(
            session,
            query,
            params,
            transformer=lambda rows: [
                VectorIndexError(
                    document_id=row[0],
                    document_name=row[1],
                    source_uri=row[2],
                    error=row[3],
                )
                for row in rows
            ],
        )

    def list_kg_index_built_errors(
        self,
        session: Session,
        kb: KnowledgeBase,
        params: Params | None = Params(),
    ) -> Page[KGIndexError]:
        chunk_model = get_kb_chunk_model(kb)
        query = (
            select(
                Document.id,
                Document.name,
                chunk_model.source_uri,
                chunk_model.id,
                chunk_model.index_result,
            )
            .join(Document)
            .where(
                chunk_model.document_id == Document.id,
                Document.knowledge_base_id == kb.id,
                chunk_model.index_status == KgIndexStatus.FAILED,
            )
            .order_by(chunk_model.id.desc())
        )

        return paginate(
            session,
            query,
            params,
            transformer=lambda rows: [
                KGIndexError(
                    document_id=row[0],
                    document_name=row[1],
                    source_uri=row[2],
                    chunk_id=row[3],
                    error=row[4],
                )
                for row in rows
            ],
        )

    def get_kb_datasource(
        self,
        session: Session,
        kb: KnowledgeBase,
        datasource_id: int,
        show_soft_deleted: bool = False,
    ) -> DataSource:
        stmt = select(DataSource).where(DataSource.id == datasource_id)
        if not show_soft_deleted:
            stmt = stmt.where(DataSource.deleted_at == None)
        return session.exec(stmt).first()

    def must_get_kb_datasource(
        self,
        session: Session,
        kb: KnowledgeBase,
        datasource_id: int,
        show_soft_deleted: bool = False,
    ) -> DataSource:
        data_source = self.get_kb_datasource(
            session, kb, datasource_id, show_soft_deleted
        )
        if data_source is None:
            raise KBDataSourceNotFound(kb.id, datasource_id)
        return data_source

    def add_kb_datasource(
        self, session: Session, kb: KnowledgeBase, data_source: DataSource
    ) -> DataSource:
        session.add(data_source)
        kb.data_sources.append(data_source)

        session.add(kb)
        session.commit()
        session.refresh(data_source)

        return data_source

    def list_kb_datasources(
        self, session: Session, kb_id: int, params: Params | None = Params()
    ) -> Page[DataSource]:
        query = (
            select(DataSource)
            .join(KnowledgeBaseDataSource)
            .where(
                DataSource.deleted_at == None,
                KnowledgeBaseDataSource.knowledge_base_id == kb_id,
            )
            .order_by(DataSource.created_at.desc())
        )
        return paginate(session, query, params)

    def remove_kb_datasource(
        self, session: Session, kb: KnowledgeBase, data_source: DataSource
    ) -> None:
        # Flag the data source to be deleted.
        data_source.deleted_at = datetime.now(UTC)
        session.add(data_source)

        # Remove the data source from the knowledge base.
        stmt = delete(KnowledgeBaseDataSource).where(
            KnowledgeBaseDataSource.knowledge_base_id == kb.id,
            KnowledgeBaseDataSource.data_source_id == data_source.id,
        )
        session.exec(stmt)

    def list_linked_chat_engines(
        self, session: Session, kb_id: int
    ) -> List[ChatEngine]:
        logger.debug(f"Listing chat engines linked to knowledge base ID {kb_id}")

        # Get engines with legacy linked_knowledge_base.id field
        query = select(ChatEngine).where(
            ChatEngine.deleted_at == None,
            func.JSON_UNQUOTE(
                func.JSON_EXTRACT(
                    ChatEngine.engine_options,
                    "$.knowledge_base.linked_knowledge_base.id",
                )
            )
            == str(kb_id),  # Convert to string since JSON values are strings
        )
        logger.debug(f"SQL Query for legacy linked_knowledge_base: {str(query)}")

        # Execute the query
        chat_engines = session.exec(query).all()
        logger.debug(
            f"Found {len(chat_engines)} chat engines with linked_knowledge_base.id = {kb_id}"
        )

        # Check linked_knowledge_bases array with id field matching kb_id
        # This is more complex as we need to check if kb_id exists in the array
        kb_id_str = str(kb_id)
        linked_kbs_query = select(ChatEngine).where(
            ChatEngine.deleted_at == None,
            # Use JSON_CONTAINS to check if an object with the specified id exists in the array
            func.JSON_CONTAINS(
                func.JSON_EXTRACT(
                    ChatEngine.engine_options,
                    "$.knowledge_base.linked_knowledge_bases",
                ),
                f'{{"id":{kb_id}}}',
                "$",
            ),
        )
        logger.debug(f"SQL Query for linked_knowledge_bases: {str(linked_kbs_query)}")

        # Execute the linked_knowledge_bases query
        linked_kbs_engines = session.exec(linked_kbs_query).all()
        logger.debug(
            f"Found {len(linked_kbs_engines)} chat engines with linked_knowledge_bases containing ID {kb_id}"
        )

        # Combine results without duplicates
        all_engines = list(
            {engine.id: engine for engine in chat_engines + linked_kbs_engines}.values()
        )
        logger.debug(f"Total unique engines linked: {len(all_engines)}")

        # Print engine details for debugging
        for engine in all_engines:
            logger.debug(
                f"Engine {engine.id}: {engine.name}, options: {engine.engine_options}"
            )

        return all_engines


knowledge_base_repo = KnowledgeBaseRepo()
