import logging
import dspy

from typing import Optional, List
from pydantic import BaseModel, Field
from sqlmodel import Session

from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.core.llms.llm import LLM

from app.rag.postprocessors.metadata_post_filter import MetadataPostFilter
from app.rag.retrievers.chunk.schema import VectorSearchRetrieverConfig
from app.rag.retrievers.knowledge_graph.schema import KnowledgeGraphRetrieverConfig
from app.rag.llms.dspy import get_dspy_lm_by_llama_llm
from app.rag.llms.resolver import get_default_llm, resolve_llm
from app.rag.rerankers.resolver import get_default_reranker_model, resolve_reranker

from app.models import (
    LLM as DBLLM,
    RerankerModel as DBRerankerModel,
    KnowledgeBase,
    ChatEngine as DBChatEngine,
)
from app.repositories import chat_engine_repo, knowledge_base_repo
from app.rag.default_prompt import (
    DEFAULT_INTENT_GRAPH_KNOWLEDGE,
    DEFAULT_NORMAL_GRAPH_KNOWLEDGE,
    DEFAULT_CONDENSE_QUESTION_PROMPT,
    DEFAULT_TEXT_QA_PROMPT,
    DEFAULT_FURTHER_QUESTIONS_PROMPT,
    DEFAULT_GENERATE_GOAL_PROMPT,
    DEFAULT_CLARIFYING_QUESTION_PROMPT,
    DEFAULT_DATABASE_QUERY_PROMPT,
)


logger = logging.getLogger("chat_engine")


class LLMOption(BaseModel):
    """
    语言模型(LLM)选项配置类
    
    这个类定义了与语言模型相关的各种提示词模板，用于指导AI如何回答不同类型的问题。
    提示词是指引导AI生成特定类型回答的文本指令。
    """
    # 用于知识图谱意图搜索的提示词模板
    intent_graph_knowledge: str = DEFAULT_INTENT_GRAPH_KNOWLEDGE
    
    # 用于常规知识图谱搜索的提示词模板
    normal_graph_knowledge: str = DEFAULT_NORMAL_GRAPH_KNOWLEDGE
    
    # 用于将用户问题转化为更精确搜索查询的提示词模板
    condense_question_prompt: str = DEFAULT_CONDENSE_QUESTION_PROMPT
    
    # 用于生成澄清问题的提示词模板（当用户问题不够明确时）
    clarifying_question_prompt: str = DEFAULT_CLARIFYING_QUESTION_PROMPT
    
    # 用于生成问题答案的主要提示词模板
    text_qa_prompt: str = DEFAULT_TEXT_QA_PROMPT
    
    # 用于生成后续问题建议的提示词模板
    further_questions_prompt: str = DEFAULT_FURTHER_QUESTIONS_PROMPT
    
    # 用于理解用户目标的提示词模板
    generate_goal_prompt: str = DEFAULT_GENERATE_GOAL_PROMPT
    
    # 用于将自然语言转换为SQL查询的提示词模板
    database_query_prompt: str = DEFAULT_DATABASE_QUERY_PROMPT


class VectorSearchOption(VectorSearchRetrieverConfig):
    """
    向量搜索选项配置类
    
    这个类定义了如何在知识库中进行向量搜索的参数，
    向量搜索是通过将文本转换为数字向量并查找相似内容的技术。
    """
    pass


class KnowledgeGraphOption(KnowledgeGraphRetrieverConfig):
    """
    知识图谱选项配置类
    
    这个类定义了知识图谱搜索的相关设置，知识图谱是一种表示实体之间关系的结构。
    """
    # 是否启用知识图谱搜索
    enabled: bool = True
    
    # 是否使用意图搜索（一种更智能的搜索方式）
    using_intent_search: bool = True


class ExternalChatEngine(BaseModel):
    """
    外部聊天引擎配置类
    
    用于配置外部聊天服务API，而不是使用内部聊天引擎。
    """
    # 外部流式聊天API的URL地址
    stream_chat_api_url: str = None


class LinkedKnowledgeBase(BaseModel):
    """
    链接知识库配置类
    
    定义了聊天引擎可以访问的知识库ID。
    """
    # 知识库的唯一标识符
    id: int


class KnowledgeBaseOption(BaseModel):
    """
    知识库选项配置类
    
    管理聊天引擎与哪些知识库关联的设置。
    """
    # 单个链接的知识库（旧版配置方式）
    linked_knowledge_base: LinkedKnowledgeBase = None
    
    # 多个链接的知识库列表（新版配置方式）
    linked_knowledge_bases: Optional[List[LinkedKnowledgeBase]] = Field(
        default_factory=list
    )


class LinkedEntity(BaseModel):
    """
    链接实体基类
    
    用于链接外部资源（如数据库连接）的通用配置类。
    """
    # 外部资源的唯一标识符
    id: int


class DatabaseOption(BaseModel):
    """
    数据库选项配置类
    
    管理聊天引擎如何与数据库交互的设置，支持通过自然语言查询数据库。
    """
    # 是否启用数据库查询功能
    enabled: bool = False
    
    # 关联的数据库连接列表
    linked_database_connections: List[LinkedEntity] = Field(default_factory=list)
    
    # 是否为只读模式（安全模式，只允许SELECT查询）
    read_only: bool = True
    
    # 查询结果的最大行数
    max_results: int = 100


class ChatEngineConfig(BaseModel):
    """
    聊天引擎主配置类
    
    这是整个聊天系统的核心配置类，管理所有聊天相关的设置和功能开关。
    """
    # 外部聊天引擎配置（如果使用外部服务）
    external_engine_config: Optional[ExternalChatEngine] = None

    # 语言模型相关的配置
    llm: LLMOption = LLMOption()

    # 知识库相关的配置
    knowledge_base: KnowledgeBaseOption = KnowledgeBaseOption()
    
    # 知识图谱相关的配置
    knowledge_graph: KnowledgeGraphOption = KnowledgeGraphOption()
    
    # 向量搜索相关的配置
    vector_search: VectorSearchOption = VectorSearchOption()

    # 数据库查询相关的配置
    database: DatabaseOption = DatabaseOption()

    # 是否使用知识图谱优化用户问题
    refine_question_with_kg: bool = True
    
    # 是否在问题不明确时生成澄清问题
    clarify_question: bool = False
    
    # 是否生成后续问题建议
    further_questions: bool = False

    # 回答验证的API地址（可选）
    post_verification_url: Optional[str] = None
    
    # 回答验证的API令牌（可选）
    post_verification_token: Optional[str] = None
    
    # 是否在回答中隐藏知识来源
    hide_sources: bool = False

    # 数据库中的聊天引擎实例（内部使用）
    _db_chat_engine: Optional[DBChatEngine] = None
    
    # 数据库中的语言模型实例（内部使用）
    _db_llm: Optional[DBLLM] = None
    
    # 数据库中的快速语言模型实例（内部使用）
    _db_fast_llm: Optional[DBLLM] = None
    
    # 数据库中的重排序模型实例（内部使用）
    _db_reranker: Optional[DBRerankerModel] = None

    @property
    def is_external_engine(self) -> bool:
        """
        判断是否使用外部聊天引擎
        
        当配置了外部聊天API地址时，系统会使用外部服务而不是内部引擎。
        
        返回值:
            布尔值，表示是否使用外部引擎
        """
        return (
            self.external_engine_config is not None
            and self.external_engine_config.stream_chat_api_url
        )

    def get_db_chat_engine(self) -> Optional[DBChatEngine]:
        """
        获取数据库中的聊天引擎实例
        
        返回值:
            数据库中的聊天引擎对象或None
        """
        return self._db_chat_engine

    def get_linked_knowledge_base(self, session: Session) -> KnowledgeBase | None:
        """
        获取关联的知识库
        
        参数:
            session: 数据库会话对象
            
        返回值:
            关联的知识库对象或None
        """
        if not self.knowledge_base:
            return None
        return knowledge_base_repo.must_get(
            session, self.knowledge_base.linked_knowledge_base.id
        )

    @classmethod
    def load_from_db(cls, session: Session, engine_name: str) -> "ChatEngineConfig":
        """
        从数据库加载聊天引擎配置
        
        根据名称从数据库中加载聊天引擎配置。如果指定名称的引擎不存在，
        则返回默认引擎配置。
        
        参数:
            session: 数据库会话对象
            engine_name: 聊天引擎名称
            
        返回值:
            加载的聊天引擎配置对象
        """
        if not engine_name or engine_name == "default":
            db_chat_engine = chat_engine_repo.get_default_engine(session)
        else:
            db_chat_engine = chat_engine_repo.get_engine_by_name(session, engine_name)

        if not db_chat_engine:
            logger.warning(
                f"Chat engine {engine_name} not found in DB, using default engine"
            )
            db_chat_engine = chat_engine_repo.get_default_engine(session)

        obj = cls.model_validate(db_chat_engine.engine_options)
        obj._db_chat_engine = db_chat_engine
        obj._db_llm = db_chat_engine.llm
        obj._db_fast_llm = db_chat_engine.fast_llm
        obj._db_reranker = db_chat_engine.reranker
        return obj

    def get_llama_llm(self, session: Session) -> LLM:
        """
        获取主语言模型实例
        
        参数:
            session: 数据库会话对象
            
        返回值:
            语言模型对象
        """
        if not self._db_llm:
            return get_default_llm(session)
        return resolve_llm(
            self._db_llm.provider,
            self._db_llm.model,
            self._db_llm.config,
            self._db_llm.credentials,
        )

    def get_dspy_lm(self, session: Session) -> dspy.LM:
        """
        获取DSPy格式的语言模型
        
        DSPy是一种用于处理语言模型的框架。
        
        参数:
            session: 数据库会话对象
            
        返回值:
            DSPy格式的语言模型对象
        """
        llama_llm = self.get_llama_llm(session)
        return get_dspy_lm_by_llama_llm(llama_llm)

    def get_fast_llama_llm(self, session: Session) -> LLM:
        """
        获取快速语言模型实例
        
        快速语言模型通常用于处理简单任务，如问题重构。
        
        参数:
            session: 数据库会话对象
            
        返回值:
            快速语言模型对象
        """
        if not self._db_fast_llm:
            return get_default_llm(session)
        return resolve_llm(
            self._db_fast_llm.provider,
            self._db_fast_llm.model,
            self._db_fast_llm.config,
            self._db_fast_llm.credentials,
        )

    def get_fast_dspy_lm(self, session: Session) -> dspy.LM:
        """
        获取DSPy格式的快速语言模型
        
        参数:
            session: 数据库会话对象
            
        返回值:
            DSPy格式的快速语言模型对象
        """
        llama_llm = self.get_fast_llama_llm(session)
        return get_dspy_lm_by_llama_llm(llama_llm)

    # FIXME: Reranker top_n should be config in the retrieval config.
    def get_reranker(
        self, session: Session, top_n: int = None
    ) -> Optional[BaseNodePostprocessor]:
        """
        获取重排序模型
        
        重排序模型用于优化搜索结果的排序。
        
        参数:
            session: 数据库会话对象
            top_n: 保留的顶部结果数量
            
        返回值:
            重排序处理器对象或None
        """
        if not self._db_reranker:
            return get_default_reranker_model(session, top_n)

        top_n = self._db_reranker.top_n if top_n is None else top_n
        return resolve_reranker(
            self._db_reranker.provider,
            self._db_reranker.model,
            top_n,
            self._db_reranker.config,
            self._db_reranker.credentials,
        )

    def get_metadata_filter(self) -> BaseNodePostprocessor:
        """
        获取元数据过滤器
        
        元数据过滤器用于根据元数据信息筛选搜索结果。
        
        返回值:
            元数据过滤处理器对象
        """
        return MetadataPostFilter(self.vector_search.metadata_filters)

    def get_knowledge_bases(self, db_session: Session) -> List[KnowledgeBase]:
        """
        获取所有关联的知识库
        
        从配置中解析并获取所有关联的知识库对象。
        
        参数:
            db_session: 数据库会话对象
            
        返回值:
            知识库对象列表
        """
        logger.debug("Getting knowledge bases from chat engine config")
        if not self.knowledge_base:
            logger.debug("No knowledge_base in engine_options")
            return []
            
        kb_config: KnowledgeBaseOption = self.knowledge_base
        logger.debug(f"Knowledge base config: {kb_config}")
        
        linked_knowledge_base_ids = []
        
        if len(kb_config.linked_knowledge_bases) == 0:
            if kb_config.linked_knowledge_base and hasattr(kb_config.linked_knowledge_base, 'id'):
                logger.debug(f"Using legacy linked_knowledge_base.id: {kb_config.linked_knowledge_base.id}")
                linked_knowledge_base_ids.append(kb_config.linked_knowledge_base.id)
            else:
                logger.debug("No knowledge base IDs found in config (neither linked_knowledge_base nor linked_knowledge_bases)")
        else:
            logger.debug(f"Found {len(kb_config.linked_knowledge_bases)} linked knowledge bases")
            linked_knowledge_base_ids.extend(
                [kb.id for kb in kb_config.linked_knowledge_bases]
            )
            
        logger.debug(f"Getting knowledge bases with IDs: {linked_knowledge_base_ids}")
        knowledge_bases = knowledge_base_repo.get_by_ids(
            db_session, knowledge_base_ids=linked_knowledge_base_ids
        )
        logger.debug(f"Retrieved {len(knowledge_bases)} knowledge bases: {[kb.id for kb in knowledge_bases]}")
        return knowledge_bases

    def screenshot(self) -> dict:
        """
        获取配置的快照
        
        创建配置的简化版本，用于展示或调试，排除敏感信息和大型提示词。
        
        返回值:
            配置的字典表示
        """
        return self.model_dump(
            exclude={
                "llm": [
                    "condense_question_prompt",
                    "text_qa_prompt",
                    "refine_prompt",
                ],
                "post_verification_token": True,
            }
        )
