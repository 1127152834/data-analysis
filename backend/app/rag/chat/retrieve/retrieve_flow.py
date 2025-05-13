import logging
from datetime import datetime
from typing import Any, Dict, Generator, List, Optional, Tuple, Union

from llama_index.core.instrumentation import get_dispatcher
from llama_index.core.llms import LLM
from llama_index.core.schema import NodeWithScore, QueryBundle, Document
from llama_index.core.prompts.rich import RichPromptTemplate
from pydantic import BaseModel, Field
from sqlmodel import Session

from app.models import (
    KnowledgeBase,
)
from app.models.document import Document as DBDocument
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
from app.models.database_connection import DatabaseType

dispatcher = get_dispatcher(__name__)
logger = logging.getLogger(__name__)


class SourceDocument(BaseModel):
    id: int
    name: str
    source_uri: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    content: Optional[str] = None


class DBSourceDocument(SourceDocument):
    """数据库来源的文档，包含数据库查询结果信息"""
    database_name: str
    query: str
    database_type: str
    execution_time: Optional[float] = None
    row_count: Optional[int] = None


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

    def retrieve(self, user_question: str) -> Tuple[List[NodeWithScore], List[NodeWithScore]]:
        """
        检索包括知识库文档和数据库查询结果
        
        Args:
            user_question: 用户问题
            
        Returns:
            包含知识库文档节点和数据库查询节点的元组
        """
        knowledge_graph_context = ""
        
        if self.engine_config.refine_question_with_kg:
            # 1. 检索与用户问题相关的知识图谱
            _, knowledge_graph_context = self.search_knowledge_graph(user_question)

            # 2. 使用知识图谱和聊天历史优化用户问题
            refined_question = self._refine_user_question(user_question, knowledge_graph_context)
            # 如果问题被优化，使用优化后的问题
            if refined_question and refined_question != user_question:
                user_question = refined_question
                logger.debug(f"用户问题已优化为: {user_question}")

        # 3. 基于用户问题搜索相关文本块
        nodes = self.search_relevant_chunks(user_question=user_question)
        
        # 4. 执行数据库查询并转换为NodeWithScore
        db_nodes = []
        if self.engine_config.database.enabled and self.db_query_manager:
            try:
                db_nodes = self.retrieve_from_database(user_question)
                logger.debug(f"数据库查询完成，转换为 {len(db_nodes)} 个节点")
            except Exception as e:
                logger.error(f"执行数据库查询时出错: {str(e)}")
                
        return nodes, db_nodes

    def retrieve_from_database(self, user_question: str) -> List[NodeWithScore]:
        """
        从数据库中检索信息
        
        Args:
            user_question: 用户问题
            
        Returns:
            数据库查询结果转换为的NodeWithScore列表
        """
        if not self.engine_config.database.enabled or not self.db_query_manager:
            logger.debug("数据库查询功能未启用")
            return []
            
        # 执行数据库查询
        try:
            db_results = self.db_query_manager.query_databases(user_question)
            logger.debug(f"数据库查询完成，获得 {len(db_results)} 条结果")
            
            # 根据查询模式处理结果
            query_mode = self.engine_config.database.query_mode
            
            # 过滤空结果
            valid_results = [r for r in db_results if not r.error and r.result]
            
            if not valid_results:
                logger.debug("没有获得有效的数据库查询结果")
                return []
                
            # 转换数据库查询结果为NodeWithScore
            result_nodes = []
            for db_result in valid_results:
                # 转换为Document对象
                doc = self._format_db_result_to_document(db_result)
                # 创建NodeWithScore
                node = NodeWithScore(
                    node=doc,
                    score=db_result.routing_score or 1.0  # 使用路由分数或默认1.0
                )
                result_nodes.append(node)
                
            return result_nodes
            
        except Exception as e:
            logger.error(f"执行数据库查询时出错: {str(e)}")
            return []

    def _format_db_result_to_document(self, db_result: DatabaseQueryResult) -> Document:
        """
        将数据库查询结果格式化为文档对象
        
        Args:
            db_result: 数据库查询结果
            
        Returns:
            Document对象
        """
        # 将查询结果转换为上下文字符串
        content = db_result.to_context_str()
        
        # 创建元数据
        metadata = {
            "source": "database",
            "database_name": db_result.connection_name,
            "database_type": db_result.database_type.value,
            "query": db_result.query,
            "source_type": "database_query",
            "id": f"db_{db_result.connection_id}_{hash(db_result.query)}",
            "created_at": db_result.executed_at.isoformat(),
        }
        
        if hasattr(db_result, "routing_score") and db_result.routing_score is not None:
            metadata["routing_score"] = db_result.routing_score
            
        # 创建Document对象
        return Document(
            text=content,
            metadata=metadata,
            excluded_embed_metadata_keys=["source", "source_type", "created_at"],
            excluded_llm_metadata_keys=["database_type", "id"]
        )

    def retrieve_documents(self, user_question: str) -> Tuple[List[DBDocument], List[DBSourceDocument]]:
        """
        检索文档和数据库查询结果
        
        Args:
            user_question: 用户问题
            
        Returns:
            包含文档和数据库来源文档的元组
        """
        kb_nodes, db_nodes = self.retrieve(user_question)
        
        # 处理知识库文档
        kb_documents = self.get_documents_from_nodes(kb_nodes)
        
        # 处理数据库查询结果
        db_documents = self.get_db_source_documents_from_nodes(db_nodes)
        
        return kb_documents, db_documents
    
    def get_db_source_documents_from_nodes(self, nodes: List[NodeWithScore]) -> List[DBSourceDocument]:
        """
        从数据库查询节点中提取数据库源文档
        
        Args:
            nodes: 数据库查询节点
            
        Returns:
            数据库源文档列表
        """
        if not nodes:
            return []
            
        db_documents = []
        for node in nodes:
            metadata = node.node.metadata
            db_documents.append(
                DBSourceDocument(
                    id=int(hash(metadata.get("id", ""))),  # 生成一个唯一ID
                    name=f"数据库查询: {metadata.get('database_name', '未知数据库')}",
                    source_uri=None,
                    metadata=metadata,
                    content=node.node.text,
                    database_name=metadata.get("database_name", "未知数据库"),
                    query=metadata.get("query", ""),
                    database_type=metadata.get("database_type", ""),
                    execution_time=metadata.get("execution_time"),
                    row_count=metadata.get("row_count")
                )
            )
        return db_documents

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
            
        document_ids = []
        for n in nodes:
            if "document_id" in n.node.metadata:
                document_ids.append(n.node.metadata["document_id"])
                
        if not document_ids:
            return []
            
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
        
    def get_all_source_documents(
        self, user_question: str
    ) -> List[Union[SourceDocument, DBSourceDocument]]:
        """
        获取所有来源文档，包括知识库文档和数据库查询结果
        
        Args:
            user_question: 用户问题
            
        Returns:
            包含所有来源文档的列表
        """
        kb_nodes, db_nodes = self.retrieve(user_question)
        
        # 获取知识库来源文档
        kb_source_docs = self.get_source_documents_from_nodes(kb_nodes)
        
        # 获取数据库来源文档
        db_source_docs = self.get_db_source_documents_from_nodes(db_nodes)
        
        # 合并结果
        all_source_docs: List[Union[SourceDocument, DBSourceDocument]] = []
        all_source_docs.extend(kb_source_docs)
        all_source_docs.extend(db_source_docs)
        
        return all_source_docs
