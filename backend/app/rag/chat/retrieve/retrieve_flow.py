import logging
from datetime import datetime
from typing import List, Optional, Tuple

from llama_index.core.instrumentation import get_dispatcher
from llama_index.core.llms import LLM
from llama_index.core.schema import NodeWithScore, QueryBundle
from llama_index.core.prompts.rich import RichPromptTemplate
from pydantic import BaseModel
from sqlmodel import Session

from app.models import (
    Document as DBDocument,
    KnowledgeBase,
)
from app.rag.chat.config import ChatEngineConfig
from app.rag.retrievers.knowledge_graph.fusion_retriever import (
    KnowledgeGraphFusionRetriever,
)
from app.rag.retrievers.knowledge_graph.schema import (
    KnowledgeGraphRetrievalResult,
    KnowledgeGraphRetrieverConfig,
)
from app.rag.retrievers.chunk.fusion_retriever import ChunkFusionRetriever
from app.repositories import document_repo
from app.rag.chat.retrieve.database_query import DatabaseQueryManager, DatabaseQueryResult

dispatcher = get_dispatcher(__name__)
logger = logging.getLogger(__name__)


class SourceDocument(BaseModel):
    id: int
    name: str
    source_uri: Optional[str] = None


class RetrieveFlow:
    def __init__(
        self,
        db_session: Session,
        engine_name: str = "default",
        engine_config: Optional[ChatEngineConfig] = None,
        llm: Optional[LLM] = None,
        fast_llm: Optional[LLM] = None,
        knowledge_bases: Optional[List[KnowledgeBase]] = None,
    ):
        self.db_session = db_session
        self.engine_name = engine_name
        self.engine_config = engine_config or ChatEngineConfig.load_from_db(
            db_session, engine_name
        )
        self.db_chat_engine = self.engine_config.get_db_chat_engine()

        # Init LLM.
        self._llm = llm or self.engine_config.get_llama_llm(self.db_session)
        self._fast_llm = fast_llm or self.engine_config.get_fast_llama_llm(
            self.db_session
        )

        # Load knowledge bases.
        self.knowledge_bases = (
            knowledge_bases or self.engine_config.get_knowledge_bases(self.db_session)
        )
        self.knowledge_base_ids = [kb.id for kb in self.knowledge_bases]

        # 初始化数据库查询管理器
        self.db_query_manager = None
        if self.engine_config.database.enabled:
            self.db_query_manager = DatabaseQueryManager(
                db_session=self.db_session,
                engine_config=self.engine_config,
                llm=self._llm,
            )

    def retrieve(self, user_question: str) -> Tuple[List[NodeWithScore], List[DatabaseQueryResult]]:
        """
        检索包括知识库文档和数据库查询结果
        
        Args:
            user_question: 用户问题
            
        Returns:
            包含知识库文档节点和数据库查询结果的元组
        """
        knowledge_graph_context = ""
        
        if self.engine_config.refine_question_with_kg:
            # 1. 检索与用户问题相关的知识图谱
            _, knowledge_graph_context = self.search_knowledge_graph(user_question)

            # 2. 使用知识图谱和聊天历史优化用户问题
            self._refine_user_question(user_question, knowledge_graph_context)

        # 3. 基于用户问题搜索相关文本块
        nodes = self.search_relevant_chunks(user_question=user_question)
        
        # 4. 执行数据库查询
        db_results = []
        if self.engine_config.database.enabled and self.db_query_manager:
            try:
                db_results = self.db_query_manager.query_databases(user_question)
                logger.debug(f"数据库查询完成，获得 {len(db_results)} 条结果")
            except Exception as e:
                logger.error(f"执行数据库查询时出错: {str(e)}")
                
        return nodes, db_results

    def retrieve_documents(self, user_question: str) -> Tuple[List[DBDocument], List[DatabaseQueryResult]]:
        """
        检索文档和数据库查询结果
        
        Args:
            user_question: 用户问题
            
        Returns:
            包含文档和数据库查询结果的元组
        """
        nodes, db_results = self.retrieve(user_question)
        return self.get_documents_from_nodes(nodes), db_results

    def search_knowledge_graph(
        self, user_question: str
    ) -> Tuple[KnowledgeGraphRetrievalResult, str]:
        kg_config = self.engine_config.knowledge_graph
        knowledge_graph = KnowledgeGraphRetrievalResult()
        knowledge_graph_context = ""
        if kg_config is not None and kg_config.enabled:
            try:
                kg_retriever = KnowledgeGraphFusionRetriever(
                    db_session=self.db_session,
                    knowledge_base_ids=[kb.id for kb in self.knowledge_bases],
                    llm=self._llm,
                    use_query_decompose=kg_config.using_intent_search,
                    config=KnowledgeGraphRetrieverConfig.model_validate(
                        kg_config.model_dump(exclude={"enabled", "using_intent_search"})
                    ),
                )
                knowledge_graph = kg_retriever.retrieve_knowledge_graph(user_question)
                knowledge_graph_context = self._get_knowledge_graph_context(
                    knowledge_graph
                )
            except ValueError as e:
                if "Expected dict_keys(['subquestions'])" in str(e):
                    logger.warning(f"知识图谱查询分解失败，但将继续进行: {e}")
                else:
                    logger.error(f"知识图谱检索过程中出现错误: {e}")
            except Exception as e:
                logger.error(f"知识图谱检索过程中出现未预期的错误: {e}")
        return knowledge_graph, knowledge_graph_context

    def _get_knowledge_graph_context(
        self, knowledge_graph: KnowledgeGraphRetrievalResult
    ) -> str:
        if self.engine_config.knowledge_graph.using_intent_search:
            kg_context_template = RichPromptTemplate(
                self.engine_config.llm.intent_graph_knowledge
            )
            return kg_context_template.format(
                sub_queries=knowledge_graph.to_subqueries_dict(),
            )
        else:
            kg_context_template = RichPromptTemplate(
                self.engine_config.llm.normal_graph_knowledge
            )
            return kg_context_template.format(
                entities=knowledge_graph.entities,
                relationships=knowledge_graph.relationships,
            )

    def _refine_user_question(
        self, user_question: str, knowledge_graph_context: str
    ) -> str:
        prompt_template = RichPromptTemplate(
            self.engine_config.llm.condense_question_prompt
        )
        refined_question = self._fast_llm.predict(
            prompt_template,
            graph_knowledges=knowledge_graph_context,
            question=user_question,
            current_date=datetime.now().strftime("%Y-%m-%d"),
        )
        return refined_question.strip().strip(".\"'!")

    def search_relevant_chunks(self, user_question: str) -> List[NodeWithScore]:
        retriever = ChunkFusionRetriever(
            db_session=self.db_session,
            knowledge_base_ids=self.knowledge_base_ids,
            llm=self._llm,
            config=self.engine_config.vector_search,
            use_query_decompose=False,
        )
        return retriever.retrieve(QueryBundle(user_question))

    def get_documents_from_nodes(self, nodes: List[NodeWithScore]) -> List[DBDocument]:
        if not nodes:
            return []
            
        document_ids = [n.node.metadata["document_id"] for n in nodes]
        documents = document_repo.fetch_by_ids(self.db_session, document_ids)
        # Keep the original order of document ids, which is sorted by similarity.
        return sorted(documents, key=lambda x: document_ids.index(x.id))

    def get_source_documents_from_nodes(
        self, nodes: List[NodeWithScore]
    ) -> List[SourceDocument]:
        documents = self.get_documents_from_nodes(nodes)
        return [
            SourceDocument(
                id=doc.id,
                name=doc.name,
                source_uri=doc.source_uri,
            )
            for doc in documents
        ]
