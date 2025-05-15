import logging
import dspy
from datetime import datetime
from enum import Enum
from typing import Optional, List, TYPE_CHECKING, Dict, Union, Any

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

# 处理循环导入问题
if TYPE_CHECKING:
    from app.models.database_connection import DatabaseConnection

from app.rag.default_prompt import (
    DEFAULT_INTENT_GRAPH_KNOWLEDGE,
    DEFAULT_NORMAL_GRAPH_KNOWLEDGE,
    DEFAULT_CONDENSE_QUESTION_PROMPT,
    DEFAULT_TEXT_QA_PROMPT,
    DEFAULT_FURTHER_QUESTIONS_PROMPT,
    DEFAULT_GENERATE_GOAL_PROMPT,
    DEFAULT_CLARIFYING_QUESTION_PROMPT,
    DEFAULT_TEXT_TO_SQL_PROMPT,
    DEFAULT_RESPONSE_SYNTHESIS_PROMPT,
    DATABASE_AWARE_CONDENSE_QUESTION_PROMPT,
    HYBRID_RESPONSE_SYNTHESIS_PROMPT,
)

from llama_index.core.tools import ToolMetadata

logger = logging.getLogger("chat_engine")

# 数据库路由策略枚举
class DatabaseRoutingStrategy(str, Enum):
    """
    数据库路由策略枚举
    
    定义系统如何在多个可用数据库之间进行选择的策略
    """
    SINGLE_BEST = "single_best"      # 只选择得分最高的单个数据库进行查询
    ALL_QUALIFIED = "all_qualified"  # 查询所有得分超过阈值的数据库
    TOP_N = "top_n"                  # 查询得分最高的N个数据库
    MANUAL = "manual"                # 手动模式，由用户明确指定要查询的数据库
    CONTEXTUAL = "contextual"        # 上下文感知模式，基于对话历史和上下文选择数据库

# 用户数据库访问权限级别枚举
class UserAccessLevel(str, Enum):
    """
    用户数据库访问权限级别
    
    定义用户对数据库的访问权限级别，从只读到管理员
    """
    READ_ONLY = "read_only"     # 只读权限，只能执行SELECT查询
    READ_WRITE = "read_write"   # 读写权限，可以执行SELECT、INSERT、UPDATE等操作
    ADMIN = "admin"             # 管理员权限，可以执行所有操作，包括结构更改


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
    
    
    # 用于LlamaIndex NLSQLTableQueryEngine将自然语言转换为SQL查询的提示词模板
    text_to_sql_prompt: str = DEFAULT_TEXT_TO_SQL_PROMPT
    
    # 用于LlamaIndex NLSQLTableQueryEngine将SQL查询结果合成自然语言回答的提示词模板
    response_synthesis_prompt: str = DEFAULT_RESPONSE_SYNTHESIS_PROMPT
    
    # 针对数据库查询优化的问题改写提示词模板
    database_aware_condense_question_prompt: str = DATABASE_AWARE_CONDENSE_QUESTION_PROMPT
    
    # 混合内容（知识库+数据库结果）的回答生成提示词模板
    hybrid_response_synthesis_prompt: str = HYBRID_RESPONSE_SYNTHESIS_PROMPT


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


class LinkedDatabaseConfig(BaseModel):
    """
    链接数据库配置类
    
    定义了单个数据库连接的配置项，包括优先级和业务描述等。
    """
    # 数据库连接的唯一标识符
    id: int
    
    # 数据库连接的优先级（值越小优先级越高）
    priority: int = 0
    
    # 业务描述覆盖（如果设置，将覆盖数据库连接中的description_for_llm）
    business_description_override: Optional[str] = None
    
    # 是否为只读模式（安全模式，只允许SELECT查询）
    read_only: Optional[bool] = None
    
    # 是否允许直接执行用户提供的SQL（高级选项，默认不允许）
    allow_direct_sql: bool = False

    # 此连接的表白名单（仅这些表可被查询，为空表示允许所有表）
    allowed_tables: List[str] = Field(default_factory=list)
    
    # 此连接的表黑名单（这些表不可被查询）
    forbidden_tables: List[str] = Field(default_factory=list)
    
    # 此连接的列黑名单（格式："table_name.column_name"）
    forbidden_columns: List[str] = Field(default_factory=list)
    
    # 此连接的行数限制（覆盖全局设置）
    max_results_override: Optional[int] = None
    
    # 此连接的SQL操作类型（覆盖全局设置）
    allowed_operations_override: Optional[List[str]] = None
    
    # 是否启用该数据库连接（可用于临时禁用）
    enabled: bool = True
    
    # 是否为主要数据库（在多数据库环境中可用于设置首选查询目标）
    is_primary: bool = False
    
    # 特定于此连接的敏感列名模式（优先于全局设置）
    sensitive_column_patterns_override: Optional[List[str]] = None
    
    # 访问权限控制配置
    # 允许访问此数据库的用户ID列表，为空表示允许所有用户
    allowed_user_ids: List[str] = Field(default_factory=list)
    
    # 禁止访问此数据库的用户ID列表
    forbidden_user_ids: List[str] = Field(default_factory=list)
    
    # 允许访问此数据库的用户角色列表
    allowed_user_roles: List[str] = Field(default_factory=list)
    
    # 是否启用敏感查询保护（对潜在危险操作进行额外验证）
    sensitive_queries_protection: bool = True
    
    # 业务场景标签，用于智能路由
    business_tags: List[str] = Field(default_factory=list)
    
    # 路由权重调整因子(0.0-2.0)，用于手动调整路由得分
    routing_weight: float = 1.0


class DatabaseOption(BaseModel):
    """
    数据库选项配置类
    
    管理聊天引擎如何与数据库交互的设置，支持通过自然语言查询数据库。
    """
    # 是否启用数据库查询功能
    enabled: bool = False
    
    # 关联的数据库连接(旧版单连接配置，保留用于向后兼容)
    linked_database_connections: List[LinkedEntity] = Field(default_factory=list)
    
    # 关联的数据库配置列表(新版多连接配置)
    linked_database_configs: List[LinkedDatabaseConfig] = Field(default_factory=list)
    
    # 全局只读模式（安全模式，只允许SELECT查询）
    read_only: bool = True
    
    # 查询结果的最大行数
    max_results: int = 100
    
    # 最大生成SQL数量（当单个问题可能需要多个SQL查询时）
    max_queries_per_question: int = 3
    
    # 是否在回答中显示生成的SQL
    show_sql_in_answer: bool = True
    
    # 查询超时时间（秒）
    query_timeout: int = 30
    
    # 是否允许聊天引擎自动选择最合适的数据库
    auto_select_database: bool = True
    
    # 数据库上下文行为模式
    # standalone: 每次查询独立处理
    # conversational: 在对话上下文中理解查询
    # hybrid: 混合模式，优先考虑当前查询，但保留上下文
    context_mode: str = "hybrid"
    
    # 是否允许跨库查询
    allow_cross_database_queries: bool = False
    
    # 表描述缓存过期时间（秒），0表示不缓存
    table_schema_cache_ttl: int = 3600
    
    # 查询模式选择
    # auto: 自动判断是否需要进行数据库查询
    # always: 始终尝试进行数据库查询
    # explicit: 只有当用户明确表示要查询数据库时才进行查询
    # mixed: 同时使用数据库查询和知识库检索，并合并结果
    query_mode: str = "auto"
    
    # 权限设置
    # 允许的SQL操作类型（例如：["SELECT"]或["SELECT", "INSERT", "UPDATE"]）
    allowed_operations: List[str] = Field(default_factory=lambda: ["SELECT"])
    
    # 是否保留敏感列（如密码、token等）
    mask_sensitive_data: bool = True
    
    # 敏感列名模式（用于自动识别和屏蔽敏感数据）
    sensitive_column_patterns: List[str] = Field(
        default_factory=lambda: [
            "password", "passwd", "secret", "token", "key", 
            "auth", "credential", "hash", "salt", "pin", "ssn", 
            "credit", "card", "cvv", "social"
        ]
    )
    
    # 查询历史记录设置
    # 是否保存查询历史
    save_query_history: bool = True
    
    # 保存历史查询的最大数量
    max_query_history: int = 100
    
    # 用户反馈设置
    # 是否允许用户反馈查询结果
    allow_user_feedback: bool = True
    
    # 安全限制
    # 单次查询的最大执行时间（秒）
    max_execution_time: int = 60
    
    # 单次查询允许扫描的最大行数
    max_scan_rows: Optional[int] = 10000
    
    # 数据库路由系统配置
    # 路由分数阈值，只有得分高于此值的数据库才会被查询
    routing_score_threshold: float = 0.3
    
    # 多数据库查询策略
    # single_best: 只查询得分最高的数据库
    # all_qualified: 查询所有得分超过阈值的数据库
    # top_n: 查询得分最高的N个数据库
    # manual: 用户手动指定要查询的数据库
    # contextual: 基于对话上下文智能选择数据库
    routing_strategy: DatabaseRoutingStrategy = DatabaseRoutingStrategy.SINGLE_BEST
    
    # top_n策略的N值
    routing_top_n: int = 2
    
    # 路由结果是否包含在最终结果中（用于调试）
    show_routing_info: bool = False
    
    # 是否使用LLM进行路由决策（高级选项，可能增加延迟）
    use_llm_for_routing: bool = False
    
    # LLM路由提示词模板
    llm_routing_prompt_template: str = """
    你是一个智能的数据库路由专家。给定用户问题和候选数据库的描述，你需要决定哪些数据库最适合回答这个问题。
    
    用户问题: {question}
    
    可用数据库:
    {database_descriptions}
    
    请为每个数据库评分(0.0-1.0)，表示它对回答此问题的相关性。1.0表示非常相关，0.0表示完全不相关。
    返回JSON格式的结果：
    {{
        "reasoning": "你的推理过程，解释为什么某些数据库更相关",
        "scores": {{
            "database_id_1": 0.9,
            "database_id_2": 0.2,
            ...
        }}
    }}
    """
    
    # 应急回退策略（当所有数据库路由分数都低于阈值时）
    # none: 不执行任何查询
    # primary: 使用标记为主要的数据库
    # any: 使用任意一个可用数据库
    fallback_strategy: str = "none"
    
    # 审计设置
    # 是否启用数据库操作审计
    enable_audit_log: bool = True
    
    # 审计日志保留天数，0表示永久保存
    audit_log_retention_days: int = 90
    
    # 是否启用访问控制
    enable_access_control: bool = False
    
    # 默认用户访问权限级别
    default_user_access_level: UserAccessLevel = UserAccessLevel.READ_ONLY
    
    # 是否启用增强的权限检查
    enhanced_permission_check: bool = False


# 添加Agent模式配置类
class AgentOption(BaseModel):
    """
    Agent选项配置类
    
    管理聊天引擎使用的Agent设置
    """
    # 是否启用Agent模式
    enabled: bool = True
    
    # Agent模式使用的工具列表，可以是预定义的工具名称
    enabled_tools: List[str] = Field(
        default_factory=lambda: [
            "knowledge_retrieval",
            "knowledge_graph_query",
            "response_generator",
            "deep_research",
            "sql_query"
        ]
    )
    
    # 是否允许深度研究
    allow_deep_research: bool = True
    
    # 是否使用思考轨迹可视化
    show_thinking: bool = True
    
    # 思考链最大长度限制
    max_thinking_steps: int = 10
    
    # 最大工具调用次数
    max_tool_calls: int = 5
    
    # Agent超时时间（秒）
    timeout_seconds: int = 60
    
    # 是否启用流式响应
    streaming: bool = True
    
    # Agent系统提示词
    system_prompt: str = """你是AutoFlow，一个智能的知识库助手。
你的任务是理解用户问题并使用提供的工具来回答问题。
你有以下工具可用：
1. knowledge_retrieval - 从知识库中检索相关内容
2. knowledge_graph_query - 从知识图谱中查询实体和关系
3. response_generator - 基于检索的内容生成回答
4. deep_research - 对复杂问题进行深入研究
5. sql_query - 通过SQL查询数据库获取信息

为了给用户提供最好的回答，请遵循以下流程：
1. 首先分析用户问题，理解用户意图
2. 使用knowledge_retrieval和knowledge_graph_query工具获取相关信息
3. 如果问题涉及数据库查询，使用sql_query工具
4. 使用response_generator基于检索到的信息生成回答
5. 如果是复杂问题，可以使用deep_research深入分析

请确保你的回答准确、全面、有条理。如果你不知道答案，请诚实地说明。"""


class ChatEngineConfig(BaseModel):
    """
    聊天引擎主配置类
    
    这是整个聊天系统的核心配置类，管理所有聊天相关的设置和功能开关。
    """
    # 外部聊天引擎配置（如果使用外部服务）
    external_engine_config: Optional[ExternalChatEngine] = None

    # 语言模型相关的配置
    llm: LLMOption = LLMOption()

    # Agent相关配置
    agent: AgentOption = AgentOption()

    # 知识库相关的配置
    knowledge_base: KnowledgeBaseOption = KnowledgeBaseOption()
    
    # 数据库源列表（用于直接数据库查询）
    database_sources: Optional[List[LinkedEntity]] = Field(default_factory=list)
    
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
        
    def get_linked_database_connections(self, session: Session) -> List["DatabaseConnection"]:
        """
        获取所有关联的数据库连接
        
        从新旧两种配置方式中获取所有数据库连接，并按照优先级排序
        
        参数:
            session: 数据库会话对象
            
        返回值:
            关联的数据库连接对象列表
        """
        from app.repositories.database_connection import DatabaseConnectionRepo
        from app.models.database_connection import DatabaseConnection
        
        if not self.database.enabled:
            return []
            
        db_repo = DatabaseConnectionRepo()
        connection_ids = set()
        
        # 获取所有数据库连接ID（老配置方式）
        for link in self.database.linked_database_connections:
            connection_ids.add(link.id)
            
        # 获取所有数据库连接ID（新配置方式）
        for config in self.database.linked_database_configs:
            connection_ids.add(config.id)
            
        # 如果没有配置任何数据库连接，返回空列表
        if not connection_ids:
            return []
            
        # 获取所有数据库连接对象
        connections = db_repo.get_by_ids(session, list(connection_ids))
        
        # 如果使用了新配置方式，按照优先级排序
        if self.database.linked_database_configs:
            # 创建ID到优先级的映射
            priority_map = {
                config.id: config.priority 
                for config in self.database.linked_database_configs
            }
            
            # 使用优先级排序（优先级值越小越靠前）
            connections.sort(key=lambda conn: priority_map.get(conn.id, 999))
            
        return connections
        
    def get_database_connection_config(self, connection_id: int) -> Optional[LinkedDatabaseConfig]:
        """
        获取指定数据库连接的配置
        
        参数:
            connection_id: 数据库连接ID
            
        返回值:
            数据库连接配置对象或None
        """
        if not self.database.enabled:
            return None
            
        # 在新配置方式中查找
        for config in self.database.linked_database_configs:
            if config.id == connection_id:
                return config
                
        # 如果在新配置方式中未找到，则创建一个基于全局设置的默认配置
        for link in self.database.linked_database_connections:
            if link.id == connection_id:
                return LinkedDatabaseConfig(
                    id=connection_id,
                    priority=999,  # 默认最低优先级
                    read_only=self.database.read_only
                )
                
        return None

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
        logger.info(f"========== 开始从数据库加载聊天引擎配置 ==========")
        logger.info(f"请求的引擎名称: {engine_name}")
        
        if not engine_name or engine_name == "default":
            logger.info("加载默认引擎配置")
            db_chat_engine = chat_engine_repo.get_default_engine(session)
        else:
            logger.info(f"查找名称为 {engine_name} 的引擎配置")
            db_chat_engine = chat_engine_repo.get_engine_by_name(session, engine_name)

        if not db_chat_engine:
            logger.warning(
                f"Chat engine {engine_name} not found in DB, using default engine"
            )
            db_chat_engine = chat_engine_repo.get_default_engine(session)

        logger.info(f"加载到引擎: {db_chat_engine.name}, ID: {db_chat_engine.id}")
        
        # 检查原始配置中的agent部分，以确保它包含必要的字段
        engine_options = db_chat_engine.engine_options
        agent_config = engine_options.get("agent", {})
        logger.info(f"原始Agent配置: {agent_config}")
        
        # 确保agent配置中有enabled字段
        if "enabled" not in agent_config:
            logger.warning("引擎配置中缺少agent.enabled字段，将使用默认值True")
            if "agent" not in engine_options:
                engine_options["agent"] = {}
            engine_options["agent"]["enabled"] = True
        else:
            # 确保enabled字段是布尔类型
            if not isinstance(agent_config["enabled"], bool):
                logger.warning(f"agent.enabled字段类型不正确，值为{agent_config['enabled']}，将转换为布尔值")
                engine_options["agent"]["enabled"] = bool(agent_config["enabled"])
                
        logger.info(f"修正后的engine_options: {engine_options}")
        
        obj = cls.model_validate(engine_options)
        obj._db_chat_engine = db_chat_engine
        obj._db_llm = db_chat_engine.llm
        obj._db_fast_llm = db_chat_engine.fast_llm
        obj._db_reranker = db_chat_engine.reranker
        
        # 打印关键配置信息
        logger.info(f"Agent配置: enabled={obj.agent.enabled}, 工具: {obj.agent.enabled_tools}")
        logger.info(f"知识库配置: {obj.knowledge_base}")
        logger.info(f"知识图谱配置: enabled={obj.knowledge_graph.enabled}")
        logger.info(f"数据库配置: enabled={obj.database.enabled}")
        logger.info(f"========== 引擎配置加载完成 ==========")
        
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
    
    def get_database_sources(self, db_session: Session) -> List["DatabaseConnection"]:
        """
        获取与聊天引擎关联的所有数据库源
        
        参数:
            db_session: 数据库会话
            
        返回:
            List[DatabaseConnection]: 数据库连接对象列表
        """
        from app.repositories import database_connection_repo
        
        result = []
        
        # 处理直接关联的数据库源
        if self.database_sources:
            for db_source in self.database_sources:
                try:
                    db_connection = database_connection_repo.get(db_session, db_source.id)
                    if db_connection:
                        result.append(db_connection)
                except Exception as e:
                    logger.warning(f"Failed to get database connection {db_source.id}: {e}")
        
        return result

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
