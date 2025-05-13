# 导入必要的库和模块
import json  # 用于处理JSON格式的数据
import logging  # 用于记录程序运行日志
from datetime import datetime, UTC, timedelta  # 用于处理日期和时间，UTC表示协调世界时
from typing import List, Optional, Generator, Tuple, Any, Dict
from urllib.parse import urljoin  # 用于构建完整的URL
from uuid import UUID  # 用于处理通用唯一标识符
import re

# 导入网络请求库
import requests  # 用于发送HTTP请求

# 导入性能追踪相关的库
from langfuse.llama_index import LlamaIndexInstrumentor  # 用于接入Langfuse性能追踪系统
from langfuse.llama_index._context import langfuse_instrumentor_context  # 用于管理追踪上下文

# 导入LlamaIndex核心组件
from llama_index.core import get_response_synthesizer  # 用于获取响应合成器
from llama_index.core.base.llms.types import ChatMessage, MessageRole  # 用于定义聊天消息和角色
from llama_index.core.schema import NodeWithScore  # 用于表示带有相关度分数的文档节点
from llama_index.core.prompts.rich import RichPromptTemplate  # 用于处理富文本提示模板

# 导入数据库相关的库
from sqlmodel import Session  # 用于管理数据库会话

# 导入应用配置
from app.core.config import settings  # 应用配置设置

# 导入异常处理
from app.exceptions import ChatNotFound  # 聊天未找到异常

# 导入数据模型
from app.models import (
    User,  # 用户模型
    Chat as DBChat,  # 数据库中的聊天模型
    ChatVisibility,  # 聊天可见性枚举
    ChatMessage as DBChatMessage,  # 数据库中的聊天消息模型
)
from app.models.database_connection import DatabaseConnection  # 数据库连接模型

# 导入聊天引擎配置
from app.rag.chat.config import ChatEngineConfig  # 聊天引擎配置类

# 导入检索流程和数据结构
from app.rag.chat.retrieve.retrieve_flow import SourceDocument, RetrieveFlow  # 检索流程和源文档模型
from app.rag.chat.retrieve.database_query import DatabaseQueryManager

# 导入流式协议相关组件
from app.rag.chat.stream_protocol import (
    ChatEvent,  # 聊天事件
    ChatStreamDataPayload,  # 聊天流数据载荷
    ChatStreamMessagePayload,  # 聊天流消息载荷
)

# 导入DSPy（用于声明式语言处理）相关库
from app.rag.llms.dspy import get_dspy_lm_by_llama_llm  # 将LlamaLLM转换为DSPy语言模型

# 导入知识图谱相关组件
from app.rag.retrievers.knowledge_graph.schema import KnowledgeGraphRetrievalResult  # 知识图谱检索结果

# 导入类型定义
from app.rag.types import ChatEventType, ChatMessageSate  # 聊天事件类型和消息状态

# 导入工具函数
from app.rag.utils import parse_goal_response_format  # 解析目标响应格式

# 导入仓库
from app.repositories import chat_repo  # 聊天仓库，用于数据库操作
from app.repositories.database_connection import DatabaseConnectionRepo
from app.repositories.database_query_history import DatabaseQueryHistoryRepo

# 导入站点设置
from app.site_settings import SiteSetting  # 站点设置，包含全局配置

# 导入追踪工具
from app.utils.tracing import LangfuseContextManager  # Langfuse上下文管理器

# 设置日志记录器
logger = logging.getLogger(__name__)  # 创建一个与当前模块同名的日志记录器


# 解析聊天消息的辅助函数
def parse_chat_messages(
    chat_messages: List[ChatMessage],  # 输入一系列聊天消息
) -> tuple[str, List[ChatMessage]]:  # 返回用户问题和历史消息
    """
    从聊天消息列表中提取最新的用户问题和之前的聊天历史
    
    参数:
        chat_messages: 完整的聊天消息列表
        
    返回:
        用户最新问题和之前的聊天历史的元组
    """
    user_question = chat_messages[-1].content  # 最后一条消息是用户的问题
    chat_history = chat_messages[:-1]  # 除了最后一条消息之外的所有消息是聊天历史
    return user_question, chat_history


# 聊天流程类 - 系统的核心类，管理整个聊天流程
class ChatFlow:
    # 声明一个类变量，用于性能追踪
    _trace_manager: LangfuseContextManager  # 用于跟踪和记录性能指标的管理器

    def __init__(
        self,
        *,  # 星号后的参数必须使用关键字传递
        db_session: Session,  # 数据库会话，用于数据库操作
        user: User,  # 当前用户对象
        browser_id: str,  # 浏览器ID，用于标识匿名用户
        origin: str,  # 请求来源URL
        chat_messages: List[ChatMessage],  # 聊天消息列表
        engine_name: str = "default",  # 聊天引擎名称，默认为"default"
        chat_id: Optional[UUID] = None,  # 聊天ID，可选参数
    ) -> None:
        """
        初始化聊天流程对象
        
        参数:
            db_session: 数据库会话对象
            user: 当前用户对象
            browser_id: 浏览器唯一标识
            origin: 请求来源
            chat_messages: 聊天消息列表
            engine_name: 使用的聊天引擎名称
            chat_id: 聊天ID，如果是继续已有聊天则提供
        """
        # 保存基本信息
        self.chat_id = chat_id  # 保存聊天ID
        self.db_session = db_session  # 保存数据库会话
        self.user = user  # 保存用户对象
        self.browser_id = browser_id  # 保存浏览器ID
        self.engine_name = engine_name  # 保存引擎名称

        # 解析聊天消息，获取用户问题和历史记录
        self.user_question, self.chat_history = parse_chat_messages(chat_messages)
        
        # 处理已有聊天的情况
        if chat_id:
            # 注意: 这里有一个待修复的问题
            # 只有聊天所有者或超级用户可以访问聊天
            # 匿名用户只能通过track_id访问匿名聊天
            
            # 获取聊天对象
            self.db_chat_obj = chat_repo.get(self.db_session, chat_id)
            if not self.db_chat_obj:
                # 如果找不到对应ID的聊天，抛出异常
                raise ChatNotFound(chat_id)
            
            try:
                # 尝试加载聊天引擎配置
                self.engine_config = ChatEngineConfig.load_from_db(
                    db_session, self.db_chat_obj.engine.name
                )
                # 获取数据库中的聊天引擎
                self.db_chat_engine = self.engine_config.get_db_chat_engine()
            except Exception as e:
                # 如果加载失败，记录错误并使用默认引擎
                logger.error(f"加载聊天引擎配置失败: {e}")
                self.engine_config = ChatEngineConfig.load_from_db(
                    db_session, engine_name
                )
                self.db_chat_engine = self.engine_config.get_db_chat_engine()
                
            # 记录日志
            logger.info(
                f"为聊天 {chat_id} 初始化ChatFlow (聊天引擎: {self.db_chat_obj.engine.name})"
            )
            
            # 从数据库加载聊天历史
            self.chat_history = [
                ChatMessage(role=m.role, content=m.content, additional_kwargs={})
                for m in chat_repo.get_messages(self.db_session, self.db_chat_obj)
            ]
        else:
            # 如果是新聊天，从数据库加载默认引擎配置
            self.engine_config = ChatEngineConfig.load_from_db(db_session, engine_name)
            self.db_chat_engine = self.engine_config.get_db_chat_engine()
            
            # 创建新的聊天对象
            self.db_chat_obj = chat_repo.create(
                self.db_session,
                DBChat(
                    # 待做: 标题应该由LLM生成
                    title=self.user_question[:100],  # 使用问题前100个字符作为标题
                    engine_id=self.db_chat_engine.id,  # 设置引擎ID
                    engine_options=self.engine_config.screenshot(),  # 保存引擎配置快照
                    user_id=self.user.id if self.user else None,  # 设置用户ID
                    browser_id=self.browser_id,  # 设置浏览器ID
                    origin=origin,  # 设置请求来源
                    visibility=(
                        ChatVisibility.PUBLIC  # 如果是匿名用户，设为公开
                        if not self.user
                        else ChatVisibility.PRIVATE  # 如果是登录用户，设为私有
                    ),
                ),
            )
            chat_id = self.db_chat_obj.id  # 获取新创建的聊天ID

            # 注意: Slack/Discord机器人可能创建带有历史消息的新聊天
            now = datetime.now(UTC)  # 获取当前UTC时间
            # 保存聊天历史到数据库
            for i, m in enumerate(self.chat_history):
                chat_repo.create_message(
                    session=self.db_session,
                    chat=self.db_chat_obj,
                    chat_message=DBChatMessage(
                        role=m.role,  # 消息角色
                        content=m.content,  # 消息内容
                        ordinal=i + 1,  # 消息序号
                        created_at=now,  # 创建时间
                        updated_at=now,  # 更新时间
                        finished_at=now,  # 完成时间
                    ),
                )

        # 初始化Langfuse性能追踪
        enable_langfuse = (
            SiteSetting.langfuse_secret_key and SiteSetting.langfuse_public_key
        )  # 检查是否启用Langfuse
        instrumentor = LlamaIndexInstrumentor(
            host=SiteSetting.langfuse_host,  # Langfuse主机地址
            secret_key=SiteSetting.langfuse_secret_key,  # 密钥
            public_key=SiteSetting.langfuse_public_key,  # 公钥
            enabled=enable_langfuse,  # 是否启用
        )
        self._trace_manager = LangfuseContextManager(instrumentor)  # 创建追踪管理器

        # 初始化大语言模型(LLM)
        self._llm = self.engine_config.get_llama_llm(self.db_session)  # 主LLM，用于生成完整回答
        self._fast_llm = self.engine_config.get_fast_llama_llm(self.db_session)  # 快速LLM，用于辅助任务
        self._fast_dspy_lm = get_dspy_lm_by_llama_llm(self._fast_llm)  # 创建DSPy语言模型

        # 加载知识库
        self.knowledge_bases = self.engine_config.get_knowledge_bases(self.db_session)  # 获取配置的知识库
        self.knowledge_base_ids = [kb.id for kb in self.knowledge_bases]  # 提取知识库ID列表

        # 初始化检索流程
        self.retrieve_flow = RetrieveFlow(
            db_session=self.db_session,  # 数据库会话
            engine_name=self.engine_name,  # 引擎名称
            engine_config=self.engine_config,  # 引擎配置
            llm=self._llm,  # 主LLM
            fast_llm=self._fast_llm,  # 快速LLM
            knowledge_bases=self.knowledge_bases,  # 知识库列表
        )

    def chat(self) -> Generator[ChatEvent | str, None, None]:
        """
        主聊天方法，处理用户提问并生成回答
        
        这是一个生成器函数，会逐步产生事件或文本片段用于流式响应
        
        返回:
            生成器，产生聊天事件或字符串
        """
        try:
            # 使用追踪管理器记录整个聊天过程的性能
            with self._trace_manager.observe(
                trace_name="ChatFlow",  # 追踪名称
                user_id=(
                    self.user.email if self.user else f"anonymous-{self.browser_id}"
                ),  # 用户ID
                metadata={
                    "is_external_engine": self.engine_config.is_external_engine,  # 是否使用外部引擎
                    "chat_engine_config": self.engine_config.screenshot(),  # 引擎配置快照
                },
                tags=[f"chat_engine:{self.engine_name}"],  # 添加标签
                release=settings.ENVIRONMENT,  # 环境信息
            ) as trace:
                # 更新追踪输入信息
                trace.update(
                    input={
                        "user_question": self.user_question,  # 用户问题
                        "chat_history": self.chat_history,  # 聊天历史
                    }
                )

                # 根据引擎类型选择处理方式
                if self.engine_config.is_external_engine:
                    # 如果是外部引擎，使用外部聊天处理
                    yield from self._external_chat()
                else:
                    # 如果是内置引擎，使用内置聊天处理
                    response_text, source_documents = yield from self._builtin_chat()
                    # 更新追踪输出信息
                    trace.update(output=response_text)
        except Exception as e:
            # 捕获并记录任何异常
            logger.exception(e)
            # 向用户发送错误消息
            yield ChatEvent(
                event_type=ChatEventType.ERROR_PART,
                payload="处理聊天时遇到错误。请稍后再试。",
            )

    def _builtin_chat(
        self,
    ) -> Generator[ChatEvent | str, None, Tuple[Optional[str], List[Any]]]:
        """
        使用内置引擎处理聊天的方法
        
        这是一个生成器函数，会逐步产生事件或文本片段用于流式响应
        
        返回:
            生成器，最终产生回答文本和源文档的元组
        """
        # 保存当前的追踪上下文
        ctx = langfuse_instrumentor_context.get().copy()
        
        # 步骤1: 创建聊天消息记录
        db_user_message, db_assistant_message = yield from self._chat_start()
        
        # 恢复追踪上下文
        langfuse_instrumentor_context.get().update(ctx)

        # 步骤2: 搜索知识图谱获取与用户问题相关的上下文
        (
            knowledge_graph,
            knowledge_graph_context,
        ) = yield from self._search_knowledge_graph(user_question=self.user_question)

        # 步骤3: 使用知识图谱和聊天历史重写用户问题以增强检索效果
        refined_question = yield from self._refine_user_question(
            user_question=self.user_question,
            chat_history=self.chat_history,
            knowledge_graph_context=knowledge_graph_context,
            refined_question_prompt=self.engine_config.llm.condense_question_prompt,
        )

        # 步骤4: 检查问题是否提供了足够的上下文信息，是否需要澄清
        if self.engine_config.clarify_question:
            need_clarify, need_clarify_response = yield from self._clarify_question(
                user_question=refined_question,
                chat_history=self.chat_history,
                knowledge_graph_context=knowledge_graph_context,
            )
            if need_clarify:
                # 如果需要澄清，直接返回澄清请求，不继续处理
                yield from self._chat_finish(
                    db_assistant_message=db_assistant_message,
                    db_user_message=db_user_message,
                    response_text=need_clarify_response,
                    knowledge_graph=knowledge_graph,
                    source_documents=[],
                )
                return None, []

        # 步骤5: 使用优化后的问题搜索相关的文档块和执行数据库查询
        relevant_chunks, db_results = yield from self._search_relevance_chunks(
            query=refined_question,
            chat_id=self.chat_id,
            user_id=self.user.id,
            retrieval_type=None,
            limit=None,
            filters=None,
        )

        # 步骤6: 使用优化的问题和相关文档块生成回答
        response_text, source_documents = yield from self._generate_answer(
            user_question=refined_question,
            knowledge_graph_context=knowledge_graph_context,
            relevant_chunks=relevant_chunks,
            db_results=db_results,
        )

        # 步骤7: 完成聊天，保存回答和相关信息
        yield from self._chat_finish(
            db_assistant_message=db_assistant_message,
            db_user_message=db_user_message,
            response_text=response_text,
            knowledge_graph=knowledge_graph,
            source_documents=source_documents,
        )

        # 返回生成的回答和源文档
        return response_text, source_documents

    def _chat_start(
        self,
    ) -> Generator[ChatEvent, None, Tuple[DBChatMessage, DBChatMessage]]:
        """
        开始聊天处理，创建用户和助手的消息记录
        
        返回:
            生成器，最终产生用户消息和助手消息对象的元组
        """
        # 创建用户消息记录
        db_user_message = chat_repo.create_message(
            session=self.db_session,
            chat=self.db_chat_obj,
            chat_message=DBChatMessage(
                role=MessageRole.USER.value,  # 设置角色为用户
                trace_url=self._trace_manager.trace_url,  # 设置追踪URL
                content=self.user_question.strip(),  # 设置消息内容（去除首尾空格）
            ),
        )
        
        # 创建助手消息记录（初始为空内容）
        db_assistant_message = chat_repo.create_message(
            session=self.db_session,
            chat=self.db_chat_obj,
            chat_message=DBChatMessage(
                role=MessageRole.ASSISTANT.value,  # 设置角色为助手
                trace_url=self._trace_manager.trace_url,  # 设置追踪URL
                content="",  # 初始内容为空
            ),
        )
        
        # 发送数据事件，通知前端已创建消息
        yield ChatEvent(
            event_type=ChatEventType.DATA_PART,
            payload=ChatStreamDataPayload(
                chat=self.db_chat_obj,
                user_message=db_user_message,
                assistant_message=db_assistant_message,
            ),
        )
        
        # 返回创建的消息对象
        return db_user_message, db_assistant_message

    def _search_knowledge_graph(
        self,
        user_question: str,
        annotation_silent: bool = False,
    ) -> Generator[ChatEvent, None, Tuple[KnowledgeGraphRetrievalResult, str]]:
        """
        搜索知识图谱获取与用户问题相关的实体和关系
        
        参数:
            user_question: 用户问题
            annotation_silent: 是否静默注释（不发送步骤提示）
            
        返回:
            生成器，最终产生知识图谱检索结果和上下文文本的元组
        """
        # 获取知识图谱配置
        kg_config = self.engine_config.knowledge_graph
        # 如果知识图谱未启用，返回空结果
        if kg_config is None or kg_config.enabled is False:
            return KnowledgeGraphRetrievalResult(), ""

        # 使用追踪管理器记录知识图谱搜索的性能
        with self._trace_manager.span(
            name="search_knowledge_graph", input=user_question
        ) as span:
            # 如果不是静默模式，发送步骤提示
            if not annotation_silent:
                if kg_config.using_intent_search:
                    # 如果使用意图搜索，显示不同的提示
                    yield ChatEvent(
                        event_type=ChatEventType.MESSAGE_ANNOTATIONS_PART,
                        payload=ChatStreamMessagePayload(
                            state=ChatMessageSate.KG_RETRIEVAL,
                            display="识别问题意图并执行知识图谱搜索",
                        ),
                    )
                else:
                    # 否则显示标准提示
                    yield ChatEvent(
                        event_type=ChatEventType.MESSAGE_ANNOTATIONS_PART,
                        payload=ChatStreamMessagePayload(
                            state=ChatMessageSate.KG_RETRIEVAL,
                            display="搜索知识图谱获取相关上下文",
                        ),
                    )

            # 调用检索流程搜索知识图谱
            knowledge_graph, knowledge_graph_context = (
                self.retrieve_flow.search_knowledge_graph(user_question)
            )

            # 记录追踪结果
            span.end(
                output={
                    "knowledge_graph": knowledge_graph,
                    "knowledge_graph_context": knowledge_graph_context,
                }
            )

        # 返回知识图谱结果和上下文
        return knowledge_graph, knowledge_graph_context

    def _refine_user_question(
        self,
        user_question: str,
        chat_history: Optional[List[ChatMessage]] = [],
        refined_question_prompt: Optional[str] = None,
        knowledge_graph_context: str = "",
        annotation_silent: bool = False,
    ) -> Generator[ChatEvent, None, str]:
        """
        使用大语言模型重写用户问题，以增强检索效果
        
        参数:
            user_question: 原始用户问题
            chat_history: 聊天历史
            refined_question_prompt: 重写问题的提示模板
            knowledge_graph_context: 知识图谱上下文
            annotation_silent: 是否静默注释
            
        返回:
            生成器，最终产生重写后的问题
        """
        # 使用追踪管理器记录问题重写的性能
        with self._trace_manager.span(
            name="refine_user_question",
            input={
                "user_question": user_question,
                "chat_history": chat_history,
                "knowledge_graph_context": knowledge_graph_context,
            },
        ) as span:
            # 如果不是静默模式，发送步骤提示
            if not annotation_silent:
                yield ChatEvent(
                    event_type=ChatEventType.MESSAGE_ANNOTATIONS_PART,
                    payload=ChatStreamMessagePayload(
                        state=ChatMessageSate.REFINE_QUESTION,
                        display="查询重写以增强信息检索",
                    ),
                )

            # 检查问题是否可能涉及数据库查询
            is_database_query = self._is_potential_database_query(user_question, chat_history)
            
            # 选择合适的提示词模板
            if is_database_query and hasattr(self.engine_config.llm, 'database_aware_condense_question_prompt'):
                # 如果可能是数据库查询且配置了专用模板，使用数据库查询优化的提示词模板
                prompt_template = RichPromptTemplate(self.engine_config.llm.database_aware_condense_question_prompt)
                logger.debug("使用数据库查询优化的问题改写模板")
            elif refined_question_prompt:
                # 使用传入的模板
            prompt_template = RichPromptTemplate(refined_question_prompt)
            else:
                # 使用默认模板
                prompt_template = RichPromptTemplate(self.engine_config.llm.condense_question_prompt)

            # 使用快速LLM重写问题
            refined_question = self._fast_llm.predict(
                prompt_template,
                graph_knowledges=knowledge_graph_context,
                chat_history=chat_history,
                question=user_question,
                current_date=datetime.now().strftime("%Y-%m-%d"),
            )

            # 如果不是静默模式，发送重写后的问题
            if not annotation_silent:
                yield ChatEvent(
                    event_type=ChatEventType.MESSAGE_ANNOTATIONS_PART,
                    payload=ChatStreamMessagePayload(
                        state=ChatMessageSate.REFINE_QUESTION,
                        message=refined_question,
                    ),
                )

            # 记录追踪结果
            span.end(output=refined_question)

            # 返回重写后的问题
            return refined_question
            
    def _is_potential_database_query(self, question: str, chat_history: List[ChatMessage] = []) -> bool:
        """
        判断问题是否可能需要数据库查询
        
        该方法使用多重策略判断:
        1. LLM辅助判断 - 使用快速LLM分析问题和上下文，进行综合判断
        2. 上下文理解 - 分析最近的对话记录，检测多轮查询意图的延续
        3. 模式匹配 - 基于关键词和模式识别可能的数据库查询特征
        
        Args:
            question: 用户问题
            chat_history: 聊天历史
            
        Returns:
            bool: 是否可能需要数据库查询
        """
        try:
            # 1. 快速检查 - 如果聊天中有活跃的数据库会话，增加判断权重
            from app.models.chat_meta import ChatMeta
            
            # 检查是否有活跃的数据库上下文
            if hasattr(self, 'db_chat_obj') and self.db_chat_obj:
                chat_id = self.db_chat_obj.id
                # 尝试获取数据库上下文元数据
                chat_meta = (
                    self.db_session.query(ChatMeta)
                    .filter(ChatMeta.chat_id == chat_id, ChatMeta.key == "db_context")
                    .first()
                )
                
                if chat_meta and chat_meta.value:
                    context = json.loads(chat_meta.value)
                    
                    # 检查是否有最近的数据库查询
                    has_recent_queries = "recent_queries" in context and context["recent_queries"]
                    
                    if has_recent_queries:
                        # 检查最近查询是否在30分钟内
                        now = datetime.now(UTC)
                        recent_query = context["recent_queries"][0]
                        query_time = datetime.fromisoformat(recent_query["timestamp"])
                        
                        if (now - query_time) < timedelta(minutes=30):
                            # 检查问题是否可能是对前一个查询的跟进
                            # 如果是简短问题，很可能是对前一个数据库查询的后续提问
                            if len(question.split()) < 8 and not any(kw in question.lower() for kw in ["文档", "知识", "内容"]):
                                logger.debug(f"检测到可能的数据库查询跟进问题: {question}")
                                return True
            
            # 2. 使用快速LLM判断问题是否需要数据库查询
            if self._fast_llm:
                # 构造上下文和问题分析提示
                context_str = ""
                
                # 添加聊天历史上下文
                if chat_history and len(chat_history) > 0:
                    recent_history = chat_history[-min(3, len(chat_history)):]
                    context_messages = []
                    for msg in recent_history:
                        role = "用户" if msg.role == MessageRole.USER else "助手"
                        context_messages.append(f"{role}: {msg.content}")
                    
                    if context_messages:
                        context_str += "最近的对话:\n" + "\n".join(context_messages) + "\n\n"
                
                # 添加数据库信息
                db_info = []
                if hasattr(self.engine_config, 'database') and self.engine_config.database.enabled:
                    for db_config in self.engine_config.database.linked_database_configs:
                        db_info.append(f"- 数据库: {db_config.name} (类型: {db_config.type})")
                
                if db_info:
                    context_str += "可用数据库:\n" + "\n".join(db_info) + "\n\n"
                
                # 构造判断提示
                prompt = f"""请判断以下问题是否需要查询数据库来回答，仅回答"是"或"否"。

上下文信息:
{context_str}

用户当前问题: {question}

判断标准:
1. 问题是否询问需要从数据库查询的结构化数据或统计信息
2. 问题是否与数据分析、趋势计算或比较相关
3. 问题是否是对前一个数据库查询的后续提问或扩展
4. 问题中是否包含时间、数量、范围等需要精确数据回答的要素

判断结果(仅回答"是"或"否"):"""

                # 使用快速LLM进行判断
                response = self._fast_llm.complete(prompt).text.strip().lower()
                if "是" in response[:10]:
                    logger.debug(f"LLM判断问题需要数据库查询: {question}")
                    return True
                elif "否" in response[:10]:
                    # 如果LLM明确判断不需要，但问题具有明显数据特征，进行二次检查
                    if any(kw in question.lower() for kw in ["数据", "统计", "多少", "数量", "趋势", "比较"]):
                        logger.debug(f"LLM判断问题不需要数据库查询，但检测到数据关键词，进一步分析: {question}")
                        # 继续进行关键词匹配检查
                    else:
                        return False
            
            # 3. 基于问题特征和关键词的模式匹配
            
            # 数据库相关关键词
            db_keywords = [
                "数据库", "查询", "sql", "表", "数据表", "记录", "行", "列",
                "mysql", "postgresql", "mongodb", "database", "query",
            ]
            
            # 数据分析相关关键词
            data_keywords = [
                "数据", "统计", "分析", "计算", "汇总", "平均", "总和", "最大", "最小",
                "趋势", "比例", "占比", "分布", "分组", "排序", "排名", "top", "前几",
            ]
            
            # 数据属性关键词
            attribute_keywords = [
                "销售", "收入", "利润", "成本", "收益", "支出", "价格", "金额",
                "人数", "数量", "年龄", "工资", "薪资", "面积", "体积", "重量",
                "百分比", "增长率", "降低率", "比率", "速度", "频率", "密度",
            ]
            
            # 时间相关关键词
            time_keywords = [
                "今天", "昨天", "明天", "本周", "上周", "下周", "本月", "上个月", "下个月",
                "今年", "去年", "明年", "季度", "年度", "每日", "每周", "每月", "每年",
                "日期", "时间", "期间", "区间", "天", "月", "年", "小时", "分钟",
            ]
            
            # 查询动作关键词
            query_action_words = [
                "查", "找", "获取", "列出", "显示", "给我", "告诉我", "计算", "统计",
                "比较", "分析", "汇总", "报告", "总结", "检索", "提取",
            ]
            
            # 问题中的量词和数字
            quantity_patterns = [
                r"多少", r"几", r"(\d+)个", r"(\d+)人", r"(\d+)次", r"百分之(\d+)",
                r"(\d+)%", r"(\d+\.\d+)", r"第(\d+)", r"前(\d+)",
            ]
            
            # 检测数据库相关关键词
            question_lower = question.lower()
            
            # 如果包含直接的数据库关键词
            if any(kw in question_lower for kw in db_keywords):
                logger.debug(f"检测到数据库关键词，判断为潜在数据库查询: {question}")
                return True
            
            # 至少有1个数据分析关键词 + 1个其他特征
            has_data_keyword = any(kw in question_lower for kw in data_keywords)
            has_attribute_keyword = any(kw in question_lower for kw in attribute_keywords)
            has_time_keyword = any(kw in question_lower for kw in time_keywords)
            has_query_action = any(kw in question_lower for kw in query_action_words)
            has_quantity_pattern = any(re.search(pattern, question_lower) for pattern in quantity_patterns)
            
            # 特征组合判断
            if has_data_keyword and (has_attribute_keyword or has_time_keyword or has_quantity_pattern):
                logger.debug(f"检测到数据分析关键词和属性/时间/数量特征，判断为潜在数据库查询: {question}")
                return True
            
            if has_query_action and (has_attribute_keyword or has_data_keyword) and (has_time_keyword or has_quantity_pattern):
                logger.debug(f"检测到查询动作、数据属性和时间/数量特征，判断为潜在数据库查询: {question}")
                return True
            
            # 4. 检查聊天历史中的上下文延续
            if chat_history and len(chat_history) >= 2:
                # 获取最后一次助手回复
                last_assistant_msg = None
                for msg in reversed(chat_history):
                    if msg.role == MessageRole.ASSISTANT:
                        last_assistant_msg = msg.content
                        break
                
                if last_assistant_msg:
                    # 检查上一次回复是否包含数据库查询结果的特征
                    db_result_indicators = [
                        "查询结果", "数据显示", "根据数据库", "数据库中", "查询到", "数据记录",
                        "行数据", "返回结果", "统计结果", "分析结果", "表中数据"
                    ]
                    
                    if any(indicator in last_assistant_msg for indicator in db_result_indicators):
                        # 如果当前问题是简短的后续提问
                        if len(question.split()) < 10:
                            logger.debug(f"检测到对数据库查询结果的后续提问: {question}")
                            return True
            
            return False
            
        except Exception as e:
            logger.warning(f"判断是否为数据库查询时出错: {str(e)}")
            
            # 使用简单的关键词匹配作为回退策略
            fallback_keywords = ["数据", "查询", "统计", "多少", "数量", "比例", "趋势"]
            return any(kw in question.lower() for kw in fallback_keywords)

    def _clarify_question(
        self,
        user_question: str,
        chat_history: Optional[List[ChatMessage]] = [],
        knowledge_graph_context: str = "",
    ) -> Generator[ChatEvent, None, Tuple[bool, str]]:
        """
        检查问题是否清晰且提供了足够的上下文信息，否则需要停止对话并向用户请求进一步澄清
        
        参数:
            user_question: 用户问题（可能是已重写的）
            chat_history: 聊天历史
            knowledge_graph_context: 知识图谱上下文
            
        返回:
            生成器，最终产生是否需要澄清和澄清请求内容的元组
        """
        # 使用追踪管理器记录问题澄清的性能
        with self._trace_manager.span(
            name="clarify_question",
            input={
                "user_question": user_question,
                "knowledge_graph_context": knowledge_graph_context,
            },
        ) as span:
            # 创建提示模板
            prompt_template = RichPromptTemplate(
                self.engine_config.llm.clarifying_question_prompt
            )

            # 使用快速LLM判断是否需要澄清
            prediction = self._fast_llm.predict(
                prompt_template,
                graph_knowledges=knowledge_graph_context,
                chat_history=chat_history,
                question=user_question,
            )
            
            # 待做: 使用结构化输出获取澄清结果
            # 处理预测结果
            clarity_result = prediction.strip().strip(".\"'!")
            need_clarify = clarity_result.lower() != "false"  # 如果结果不是"false"，则需要澄清
            need_clarify_response = clarity_result if need_clarify else ""  # 如果需要澄清，使用预测结果作为回复

            # 如果需要澄清，发送澄清请求
            if need_clarify:
                yield ChatEvent(
                    event_type=ChatEventType.TEXT_PART,
                    payload=need_clarify_response,
                )

            # 记录追踪结果
            span.end(
                output={
                    "need_clarify": need_clarify,
                    "need_clarify_response": need_clarify_response,
                }
            )

            # 返回是否需要澄清和澄清请求内容
            return need_clarify, need_clarify_response

    def _search_relevance_chunks(
        self,
        query: str,
        chat_id: str,
        user_id: str,
        retrieval_type: str = None,
        limit: int = None,
        filters: Optional[Dict] = None,
    ) -> Generator[ChatEvent, None, Tuple[List[NodeWithScore], List[NodeWithScore]]]:
        """
        搜索与问题最相关的文档块和执行数据库查询
        
        Args:
            query: 查询文本
            chat_id: 对话ID
            user_id: 用户ID
            retrieval_type: 检索类型
            limit: 结果数量限制
            filters: 过滤条件
            
        Returns:
            生成器，最终产生带有相关度分数的文档节点列表和数据库查询结果节点列表的元组
        """
        # 使用追踪管理器记录相关文档搜索的性能
        with self._trace_manager.span(
            name="search_relevance_chunks", input=query
        ) as span:
            # 发送步骤提示
            yield ChatEvent(
                event_type=ChatEventType.MESSAGE_ANNOTATIONS_PART,
                payload=ChatStreamMessagePayload(
                    state=ChatMessageSate.SEARCH_RELATED_DOCUMENTS,
                    display="检索最相关的文档",
                ),
            )

            # 获取对话级别的数据库上下文
            db_nodes = []
            
            # 如果数据库查询功能已启用，执行数据库查询
            if (
                hasattr(self.engine_config, "database")
                and self.engine_config.database.enabled
                and self.engine_config.database.linked_database_configs
            ):
                try:
                    # 获取对话级别的数据库上下文
                    chat_db_context = self._get_database_context(chat_id, user_id)
                    
                    # 执行数据库查询
                    db_query_manager = DatabaseQueryManager(
                        self.db_session, self.engine_config, self._llm
                    )
                    
                    # 传递对话上下文给查询管理器
                    db_results = db_query_manager.query_databases(
                        question=query, 
                        user_id=user_id,
                        context=chat_db_context
                    )
                    
                    # 将数据库查询结果转换为NodeWithScore
                    if db_results:
                        db_nodes = self.retrieve_flow._process_db_results(db_results)

            # 如果有数据库查询结果，显示数据库查询提示
                        if db_nodes and len(db_nodes) > 0:
                yield ChatEvent(
                    event_type=ChatEventType.MESSAGE_ANNOTATIONS_PART,
                    payload=ChatStreamMessagePayload(
                        state=ChatMessageSate.DATABASE_QUERY,
                        display="执行数据库查询",
                                    context={"db_results_count": len(db_nodes)},
                                ),
                            )
                except Exception as e:
                    logger.error(f"数据库查询失败: {str(e)}")
                    db_nodes = []
            
            # 调用检索流程搜索相关文档块
            relevance_chunks = self.retrieve_flow.retrieve_from_knowledge_base(query)

            # 记录追踪结果
            span.end(
                output={
                    "relevance_chunks": relevance_chunks,
                    "db_results_count": len(db_nodes) if db_nodes else 0,
                }
            )

            # 返回相关文档块和数据库查询结果
            return relevance_chunks, db_nodes

    def _get_database_context(self, chat_id: UUID, user_id: UUID) -> Dict[str, Any]:
        """
        获取对话级别的数据库上下文信息
        
        用于控制特定对话中的数据库访问权限和偏好设置，以及维护多轮查询的上下文
        
        Args:
            chat_id: 对话ID
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 数据库上下文信息，包含权限、历史、表结构等
        """
        try:
            from app.models.chat_meta import ChatMeta
            from app.rag.chat.retrieve.database_query import DatabaseQueryManager
            
            # 1. 获取聊天元数据记录中的数据库上下文
            chat_meta = (
                self.db_session.query(ChatMeta)
                .filter(ChatMeta.chat_id == chat_id, ChatMeta.key == "db_context")
                .first()
            )
            
            # 检查元数据是否存在且未过期
            if chat_meta and chat_meta.value:
                context = json.loads(chat_meta.value)
                # 检查缓存是否过期（默认30分钟）
                cache_time = datetime.fromisoformat(context.get("cache_time", ""))
                if datetime.now(UTC) - cache_time < timedelta(minutes=30):
                    logger.debug(f"使用缓存的数据库上下文，聊天ID: {chat_id}")
                    return context
            
            # 2. 构建新的数据库上下文
            db_context = {
                "chat_id": str(chat_id),
                "user_id": str(user_id),
                "cache_time": datetime.now(UTC).isoformat(),
            }
            
            # 3. 获取数据库权限信息
            db_restrictions = self._get_chat_db_restrictions(chat_id, user_id)
            if db_restrictions:
                db_context["permissions"] = db_restrictions.get("permissions", {})
            
            # 4. 获取最近的查询历史
            db_query_manager = DatabaseQueryManager(self.db_session, self.engine_config, self._llm)
            recent_queries = db_query_manager.get_recent_queries(
                chat_id=chat_id,
                limit=5,
                time_window=timedelta(hours=1)
            )
            
            # 将查询历史转换为上下文格式
            if recent_queries:
                query_history = []
                for query in recent_queries:
                    history_item = {
                        "database": query.connection_name,
                        "question": query.question,
                        "query": query.query,
                        "success": query.error is None,
                        "timestamp": query.executed_at.isoformat(),
                        "rows_returned": query.rows_returned or 0
                    }
                    query_history.append(history_item)
                
                db_context["recent_queries"] = query_history
            
            # 5. 获取查询统计信息
            query_stats = db_query_manager.get_query_statistics(chat_id)
            if query_stats:
                db_context["query_stats"] = query_stats
            
            # 6. 从聊天记录获取用户指定的数据库
            chat_messages = self._get_latest_chat_messages(chat_id, limit=5)
            specified_db = self._extract_database_instruction(chat_messages)
            if specified_db:
                db_context["specified_database_id"] = specified_db
            
            # 7. 获取推荐的数据库连接（基于历史和权限）
            recommended_dbs = []
            
            # 首先添加用户指定的数据库
            if specified_db and str(specified_db) in db_context.get("permissions", {}):
                db_repo = DatabaseConnectionRepo()
                specified_db_obj = db_repo.get_by_id(self.db_session, specified_db)
                if specified_db_obj:
                    recommended_dbs.append({
                        "id": specified_db_obj.id,
                        "name": specified_db_obj.name,
                        "type": specified_db_obj.db_type,
                        "score": 1.0,  # 用户明确指定，得分最高
                        "reason": "用户指定"
                    })
            
            # 然后添加历史查询过的数据库
            if "query_stats" in db_context and "databases_used" in db_context["query_stats"]:
                for db_info in db_context["query_stats"]["databases_used"]:
                    # 检查是否已经添加过
                    if not any(r["id"] == db_info["connection_id"] for r in recommended_dbs):
                        # 检查权限
                        if str(db_info["connection_id"]) in db_context.get("permissions", {}):
                            recommended_dbs.append({
                                "id": db_info["connection_id"],
                                "name": db_info["connection_name"],
                                "type": db_info["database_type"],
                                "score": 0.8,  # 历史查询的数据库得分较高
                                "reason": "历史查询"
                            })
            
            # 添加推荐的数据库到上下文
            if recommended_dbs:
                db_context["recommended_databases"] = recommended_dbs
            
            # 8. 保存上下文到元数据
            if chat_meta:
                chat_meta.value = json.dumps(db_context)
                chat_meta.updated_at = datetime.now(UTC)
            else:
                from app.repositories.chat_meta import ChatMetaRepo
                meta_repo = ChatMetaRepo()
                meta_repo.create(
                    self.db_session,
                    ChatMeta(
                        chat_id=chat_id,
                        key="db_context",
                        value=json.dumps(db_context),
                    ),
                )
            
            self.db_session.commit()
            logger.debug(f"已更新聊天数据库上下文，聊天ID: {chat_id}")
            
            return db_context
            
        except Exception as e:
            logger.warning(f"获取对话数据库上下文出错: {str(e)}")
            # 返回基本上下文
            return {
                "chat_id": str(chat_id),
                "user_id": str(user_id),
                "cache_time": datetime.now(UTC).isoformat(),
                "error": str(e)
            }
        
    def _extract_database_instruction(self, chat_messages: List[Dict]) -> Optional[int]:
        """
        从聊天消息中提取数据库指令
        
        Args:
            chat_messages: 聊天消息列表
            
        Returns:
            Optional[int]: 指定的数据库ID，如果没有则返回None
        """
        # 数据库指令的关键词模式
        db_instruction_patterns = [
            r"使用(\w+)数据库",
            r"切换到(\w+)数据库",
            r"查询(\w+)数据库",
            r"在(\w+)数据库中查找",
            r"使用数据库\s*[:|：]?\s*(\w+)",
            r"数据库\s*[:|：]?\s*(\w+)",
        ]
        
        # 数据库名称到ID的映射（这里应该从实际配置中获取）
        db_name_to_id = self._get_database_name_mapping()
        
        # 从最近的消息开始检查
        for message in reversed(chat_messages):
            if message["role"] != "user":
                continue
                
            content = message.get("content", "")
            
            # 检查是否有明确的数据库ID指定
            id_match = re.search(r"数据库ID\s*[:|：]?\s*(\d+)", content)
            if id_match:
                try:
                    return int(id_match.group(1))
                except ValueError:
                    pass
                    
            # 检查是否有数据库名称指定
            for pattern in db_instruction_patterns:
                match = re.search(pattern, content)
                if match:
                    db_name = match.group(1)
                    if db_name in db_name_to_id:
                        return db_name_to_id[db_name]
                        
        return None
        
    def _get_database_name_mapping(self) -> Dict[str, str]:
        """获取数据库名称到ID的映射"""
        name_to_id_map = {}
        
        try:
            # 使用DatabaseConnectionRepo
            from app.repositories.database_connection import DatabaseConnectionRepo
            db_repo = DatabaseConnectionRepo()
            
            # 获取所有数据库连接
            if (hasattr(self.engine_config, 'database') and 
                self.engine_config.database.enabled and 
                self.engine_config.database.linked_database_configs):
                
                for db_config in self.engine_config.database.linked_database_configs:
                    try:
                        # 使用仓库方法获取数据库连接
                        db_connection = db_repo.get_by_id(self.db_session, db_config.id)
                        if db_connection:
                            name_to_id_map[db_connection.name.lower()] = db_connection.id
                    except Exception as e:
                        logger.warning(f"获取数据库连接时出错: {str(e)}")
        except Exception as e:
            logger.warning(f"创建数据库名称映射时出错: {str(e)}")
        
        return name_to_id_map
        
    def _get_chat_db_restrictions(self, chat_id: UUID, user_id: UUID) -> Dict[str, Any]:
        """
        获取聊天的数据库访问限制和权限信息
        
        Args:
            chat_id: 聊天ID
            user_id: 用户ID
            
        Returns:
            Dict: 数据库访问限制和权限信息
        """
        try:
            from app.models.chat_meta import ChatMeta
            
            # 获取聊天元数据记录
            chat_meta = (
                self.db_session.query(ChatMeta)
                .filter(ChatMeta.chat_id == chat_id, ChatMeta.key == "db_restrictions")
                .first()
            )
            
            # 检查元数据是否存在并且未过期
            if chat_meta and chat_meta.value:
                restrictions = json.loads(chat_meta.value)
                # 检查缓存是否过期（默认1小时）
                cache_time = datetime.fromisoformat(restrictions.get("cache_time", ""))
                if datetime.now(UTC) - cache_time < timedelta(hours=1):
                    logger.debug(f"使用缓存的数据库权限信息，聊天ID: {chat_id}")
                    return restrictions
            
            # 获取用户数据库权限
            user_permissions = self._get_user_db_permissions(user_id)
            
            # 获取历史查询的数据库
            historical_dbs = self._get_historical_queried_databases(chat_id)
            
            # 构建数据库访问限制信息
            restrictions = {
                "user_id": str(user_id),
                "chat_id": str(chat_id),
                "permissions": user_permissions,
                "historical_dbs": historical_dbs,
                "cache_time": datetime.now(UTC).isoformat(),
            }
            
            # 保存到聊天元数据
            if chat_meta:
                chat_meta.value = json.dumps(restrictions)
                chat_meta.updated_at = datetime.now(UTC)
            else:
                from app.repositories.chat_meta import ChatMetaRepo
                meta_repo = ChatMetaRepo()
                meta_repo.create(
                    self.db_session,
                    ChatMeta(
                        chat_id=chat_id,
                        key="db_restrictions",
                        value=json.dumps(restrictions),
                    ),
                )
            
            self.db_session.commit()
            logger.debug(f"已更新聊天数据库权限缓存，聊天ID: {chat_id}")
            
            return restrictions
        except Exception as e:
            logger.warning(f"获取聊天数据库限制时出错: {str(e)}")
            return {
                "user_id": str(user_id),
                "chat_id": str(chat_id),
                "permissions": {},
                "historical_dbs": [],
                "cache_time": datetime.now(UTC).isoformat(),
            }
        
    def _get_chat_tags(self, chat_id: str) -> List[str]:
        """
        获取对话的标签或业务场景
        
        Args:
            chat_id: 对话ID
            
        Returns:
            List[str]: 标签列表
        """
        # 这里应该从数据库或缓存中获取对话的标签
        # 简化实现，实际中应替换为真实逻辑
        return []
        
    def _get_user_db_permissions(self, user_id: str) -> Dict[str, bool]:
        """获取用户的数据库访问权限"""
        permissions = {}
        
        try:
            # 导入必要的模型和仓库
            from app.repositories.database_connection import DatabaseConnectionRepo
            
            db_repo = DatabaseConnectionRepo()
            
            # 获取用户权限
            if (hasattr(self.engine_config, 'database') and 
                self.engine_config.database.enabled and 
                self.engine_config.database.linked_database_configs):
                
                for db_config in self.engine_config.database.linked_database_configs:
                    try:
                        # 使用仓库方法获取数据库连接
                        db_connection = db_repo.get_by_id(self.db_session, db_config.id)
                        
                        if db_connection:
                            # 简化实现：暂时默认所有用户都有访问权限
                            # TODO: 当PermissionRepo实现完成后，替换为真实的权限检查
                            permissions[db_connection.id] = True
                    except Exception as e:
                        logger.warning(f"获取用户数据库权限时出错: {str(e)}")
        except Exception as e:
            logger.warning(f"创建用户数据库权限映射时出错: {str(e)}")
        
        return permissions
        
    def _get_historical_queried_databases(self, chat_id: UUID) -> List[Dict[str, Any]]:
        """
        获取历史查询过的数据库记录
        
        Args:
            chat_id: 对话ID
            
        Returns:
            List[Dict[str, Any]]: 历史数据库查询记录，包含数据库连接信息和查询统计
        """
        try:
            # 使用数据库查询历史仓库获取查询统计和历史
            history_repo = DatabaseQueryHistoryRepo()
            
            # 获取聊天会话中的查询统计信息
            db_stats = history_repo.get_query_stats_by_chat(self.db_session, chat_id)
            
            # 获取最近一小时的查询历史
            recent_queries = history_repo.get_recent_queries_in_chat(
                self.db_session,
                chat_id=chat_id,
                limit=10,
                since=datetime.now(UTC) - timedelta(hours=1)
            )
            
            # 构建结果列表
            result = []
            
            # 添加数据库使用统计
            if db_stats and db_stats.get("databases_used"):
                for db_info in db_stats.get("databases_used", []):
                    db_item = {
                        "connection_id": db_info.get("connection_id"),
                        "connection_name": db_info.get("connection_name"),
                        "database_type": db_info.get("database_type"),
                        "total_queries": db_info.get("query_count", 0),
                        "successful_queries": db_info.get("successful_count", 0),
                        "last_query_time": db_info.get("last_query_time"),
                        "recent_queries": []
                    }
                    
                    # 添加该数据库的最近查询
                    for query in recent_queries:
                        if query.connection_id == db_item["connection_id"]:
                            db_item["recent_queries"].append({
                                "question": query.question,
                                "query": query.query,
                                "is_successful": query.is_successful,
                                "executed_at": query.executed_at,
                                "rows_returned": query.rows_returned
                            })
                            
                    result.append(db_item)
            
            logger.debug(f"获取到历史查询数据库: {len(result)} 个")
            return result
            
        except Exception as e:
            logger.warning(f"获取历史查询数据库记录时出错: {str(e)}")
            return []

    def _generate_answer(
        self,
        user_question: str,
        knowledge_graph_context: str,
        relevant_chunks: List[NodeWithScore],
        db_results: Optional[List[NodeWithScore]] = None,
    ) -> Generator[ChatEvent, None, Tuple[str, List[SourceDocument]]]:
        """
        根据用户问题、知识图谱上下文、相关文档块和数据库查询结果生成回答
        
        参数:
            user_question: 用户问题（可能是已重写的）
            knowledge_graph_context: 知识图谱上下文
            relevant_chunks: 相关文档块列表
            db_results: 数据库查询结果节点列表
            
        返回:
            生成器，最终产生回答文本和源文档列表的元组
        """
        # 使用追踪管理器记录回答生成的性能
        with self._trace_manager.span(
            name="generate_answer", input=user_question
        ) as span:
            # 处理数据库查询结果
            database_context = ""
            has_db_results = db_results and len(db_results) > 0
            
            if has_db_results:
                # 合并所有数据库节点的文本内容
                db_contents = []
                for node in db_results:
                    # 每个节点的内容已经包含格式化后的数据库查询结果
                    db_contents.append(node.node.text)
                
                if db_contents:
                    database_context = "\n\n数据库查询结果:\n" + "\n\n".join(db_contents)
            
            # 添加数据库查询结果节点到相关上下文中
            all_nodes = relevant_chunks.copy()
            if has_db_results:
                all_nodes.extend(db_results)
            
            # 选择合适的提示词模板和响应合成方法
            if has_db_results and relevant_chunks and hasattr(self.engine_config.llm, 'hybrid_response_synthesis_prompt'):
                # 如果同时有知识库文档和数据库查询结果，使用混合内容模板
                text_qa_template = RichPromptTemplate(
                    template_str=self.engine_config.llm.hybrid_response_synthesis_prompt
                )
                logger.debug("使用混合内容响应合成模板")
            else:
                # 使用标准模板
                text_qa_template = RichPromptTemplate(
                    template_str=self.engine_config.llm.text_qa_prompt
                )
            
            # 部分格式化模板，填入固定参数
            text_qa_template = text_qa_template.partial_format(
                current_date=datetime.now().strftime("%Y-%m-%d"),  # 当前日期
                graph_knowledges=knowledge_graph_context,  # 知识图谱上下文
                original_question=self.user_question,  # 原始问题
                database_results=database_context,  # 数据库查询结果
            )

            # 获取响应合成器
            response_synthesizer = get_response_synthesizer(
                llm=self._llm,  # 使用主LLM
                text_qa_template=text_qa_template,  # 问答模板
                streaming=True  # 启用流式输出
            )

            # 使用响应合成器生成回答
            response = response_synthesizer.synthesize(
                query=user_question,  # 查询（可能是已重写的问题）
                nodes=all_nodes,  # 所有相关节点，包括文档和数据库查询结果
            )
            # 从响应中获取源文档
            source_documents = self.retrieve_flow.get_source_documents_from_nodes(
                response.source_nodes
            )
            # 发送源文档信息
            yield ChatEvent(
                event_type=ChatEventType.MESSAGE_ANNOTATIONS_PART,
                payload=ChatStreamMessagePayload(
                    state=ChatMessageSate.SOURCE_NODES,
                    context=source_documents,
                ),
            )

            # 生成回答
            yield ChatEvent(
                event_type=ChatEventType.MESSAGE_ANNOTATIONS_PART,
                payload=ChatStreamMessagePayload(
                    state=ChatMessageSate.GENERATE_ANSWER,
                    display="使用大模型生成精确答案",
                ),
            )
            # 流式输出回答文本
            response_text = ""
            for word in response.response_gen:
                response_text += word  # 累积回答文本
                # 逐字发送回答
                yield ChatEvent(
                    event_type=ChatEventType.TEXT_PART,
                    payload=word,
                )

            # 如果回答为空，抛出异常
            if not response_text:
                raise Exception("从LLM获取到的响应为空")

            # 记录追踪结果
            span.end(
                output=response_text,
                metadata={
                    "source_documents": source_documents,
                    "has_db_results": bool(db_results and len(db_results) > 0),
                },
            )

            # 返回回答文本和源文档
            return response_text, source_documents

    def _post_verification(
        self, user_question: str, response_text: str, chat_id: UUID, message_id: int
    ) -> Optional[str]:
        """
        将问答对发送到外部验证服务，返回验证结果的URL
        
        参数:
            user_question: 用户问题
            response_text: 回答文本
            chat_id: 聊天ID
            message_id: 消息ID
            
        返回:
            验证结果URL，如果不需要验证则返回None
        """
        # 获取后验证URL和令牌
        post_verification_url = self.engine_config.post_verification_url
        post_verification_token = self.engine_config.post_verification_token

        # 如果未配置后验证URL，返回None
        if not post_verification_url:
            return None

        # 构建外部请求ID和问答内容
        external_request_id = f"{chat_id}_{message_id}"
        qa_content = f"User question: {user_question}\n\nAnswer:\n{response_text}"

        # 使用追踪管理器记录后验证的性能
        with self._trace_manager.span(
            name="post_verification",
            input={
                "external_request_id": external_request_id,
                "qa_content": qa_content,
            },
        ) as span:
            try:
                # 发送POST请求到验证服务
                resp = requests.post(
                    post_verification_url,
                    json={
                        "external_request_id": external_request_id,
                        "qa_content": qa_content,
                    },
                    headers=(
                        {
                            "Authorization": f"Bearer {post_verification_token}",
                        }
                        if post_verification_token  # 如果有令牌，添加到请求头
                        else {}  # 否则使用空头部
                    ),
                    timeout=10,  # 超时设置为10秒
                )
                # 检查响应状态
                resp.raise_for_status()
                # 获取任务ID
                job_id = resp.json()["job_id"]
                # 构建验证结果链接
                post_verification_link = urljoin(
                    f"{post_verification_url}/", str(job_id)
                )

                # 记录追踪结果
                span.end(
                    output={
                        "post_verification_link": post_verification_link,
                    }
                )

                # 返回验证结果链接
                return post_verification_link
            except Exception as e:
                # 记录失败日志
                logger.exception("后验证失败: %s", e.message)
                return None

    def _chat_finish(
        self,
        db_assistant_message: ChatMessage,
        db_user_message: ChatMessage,
        response_text: str,
        knowledge_graph: KnowledgeGraphRetrievalResult = KnowledgeGraphRetrievalResult(),
        source_documents: Optional[List[SourceDocument]] = [],
        annotation_silent: bool = False,
    ):
        """
        完成聊天处理，保存回答和相关信息
        
        参数:
            db_assistant_message: 助手消息对象
            db_user_message: 用户消息对象
            response_text: 回答文本
            knowledge_graph: 知识图谱检索结果
            source_documents: 源文档列表
            annotation_silent: 是否静默注释
        """
        # 如果不是静默模式，发送完成事件
        if not annotation_silent:
            yield ChatEvent(
                event_type=ChatEventType.MESSAGE_ANNOTATIONS_PART,
                payload=ChatStreamMessagePayload(
                    state=ChatMessageSate.FINISHED,
                ),
            )

        # 执行后验证
        post_verification_result_url = self._post_verification(
            self.user_question,
            response_text,
            self.db_chat_obj.id,
            db_assistant_message.id,
        )

        # 更新助手消息
        db_assistant_message.sources = [s.model_dump() for s in source_documents]  # 保存源文档
        db_assistant_message.graph_data = knowledge_graph.to_stored_graph_dict()  # 保存知识图谱数据
        db_assistant_message.content = response_text  # 保存回答文本
        db_assistant_message.post_verification_result_url = post_verification_result_url  # 保存验证结果URL
        db_assistant_message.updated_at = datetime.now(UTC)  # 更新时间
        db_assistant_message.finished_at = datetime.now(UTC)  # 完成时间
        self.db_session.add(db_assistant_message)  # 添加到会话

        # 更新用户消息
        db_user_message.graph_data = knowledge_graph.to_stored_graph_dict()  # 保存知识图谱数据
        db_user_message.updated_at = datetime.now(UTC)  # 更新时间
        db_user_message.finished_at = datetime.now(UTC)  # 完成时间
        self.db_session.add(db_user_message)  # 添加到会话
        self.db_session.commit()  # 提交事务

        # 发送数据事件，通知前端聊天完成
        yield ChatEvent(
            event_type=ChatEventType.DATA_PART,
            payload=ChatStreamDataPayload(
                chat=self.db_chat_obj,
                user_message=db_user_message,
                assistant_message=db_assistant_message,
            ),
        )

    # 待做: 将_external_chat()方法分离到另一个ExternalChatFlow类，但同时，我们需要
    # 通过ChatMixin或BaseChatFlow共享一些公共方法。
    def _external_chat(self) -> Generator[ChatEvent | str, None, None]:
        """
        使用外部引擎处理聊天的方法
        
        这是一个生成器函数，会逐步产生事件或文本片段用于流式响应
        """
        # 创建聊天消息记录
        db_user_message, db_assistant_message = yield from self._chat_start()

        # 初始化变量
        cache_messages = None
        goal, response_format = self.user_question, {}
        
        # 如果启用了问题缓存且没有聊天历史，尝试查找最佳答案
        if settings.ENABLE_QUESTION_CACHE and len(self.chat_history) == 0:
            try:
                logger.info(f"开始查找问题的最佳答案: {self.user_question}")
                # 从缓存中查找最佳答案
                cache_messages = chat_repo.find_best_answer_for_question(
                    self.db_session, self.user_question
                )
                if cache_messages and len(cache_messages) > 0:
                    logger.info(
                        f"为问题 {self.user_question} 找到 {len(cache_messages)} 个最佳答案结果"
                    )
            except Exception as e:
                logger.error(f"为问题 {self.user_question} 查找最佳答案失败: {e}")

        # 如果没有找到缓存答案，生成目标和回答
        if not cache_messages or len(cache_messages) == 0:
            try:
                # 1. 根据用户问题、知识图谱和聊天历史生成目标
                goal, response_format = yield from self._generate_goal()

                # 2. 检查目标是否提供了足够的上下文信息，是否需要澄清
                if self.engine_config.clarify_question:
                    (
                        need_clarify,
                        need_clarify_response,
                    ) = yield from self._clarify_question(
                        user_question=goal, chat_history=self.chat_history
                    )
                    if need_clarify:
                        # 如果需要澄清，直接返回澄清请求，不继续处理
                        yield from self._chat_finish(
                            db_assistant_message=db_assistant_message,
                            db_user_message=db_user_message,
                            response_text=need_clarify_response,
                            annotation_silent=True,
                        )
                        return
            except Exception as e:
                # 如果生成目标失败，使用用户问题作为目标
                goal = self.user_question
                logger.warning(
                    f"生成优化目标失败，回退使用用户问题作为目标: {e}",
                    exc_info=True,
                    extra={},
                )

            # 尝试根据目标查找最近的助手消息
            cache_messages = None
            if settings.ENABLE_QUESTION_CACHE:
                try:
                    logger.info(
                        f"开始根据目标查找最近的助手消息, 目标: {goal}, 响应格式: {response_format}"
                    )
                    cache_messages = chat_repo.find_recent_assistant_messages_by_goal(
                        self.db_session,
                        {"goal": goal, "Lang": response_format.get("Lang", "Chinese")},
                        90,  # 查找90天内的消息
                    )
                    logger.info(
                        f"根据目标 {goal} 找到 {len(cache_messages)} 个最近的助手消息"
                    )
                except Exception as e:
                    logger.error(
                        f"根据目标查找最近的助手消息失败: {e}"
                    )

        # 获取外部聊天API的URL
        stream_chat_api_url = (
            self.engine_config.external_engine_config.stream_chat_api_url
        )
        
        # 如果找到了缓存消息，直接使用缓存的回答
        if cache_messages and len(cache_messages) > 0:
            stackvm_response_text = cache_messages[0].content
            task_id = cache_messages[0].meta.get("task_id")
            # 分段输出回答
            for chunk in stackvm_response_text.split(". "):
                if chunk:
                    if not chunk.endswith("."):
                        chunk += ". "
                    yield ChatEvent(
                        event_type=ChatEventType.TEXT_PART,
                        payload=chunk,
                    )
        else:
            # 如果没有缓存，调用外部聊天API
            logger.debug(
                f"使用外部聊天引擎 (api_url: {stream_chat_api_url}) 回答用户问题: {self.user_question}"
            )
            # 准备聊天参数
            chat_params = {
                "goal": goal,
                "response_format": response_format,
                "namespace_name": "Default",
            }
            # 发送POST请求并获取流式响应
            res = requests.post(stream_chat_api_url, json=chat_params, stream=True)

            # 注意: 外部类型聊天引擎目前不支持非流式模式
            stackvm_response_text = ""
            task_id = None
            # 处理流式响应的每一行
            for line in res.iter_lines():
                if not line:
                    continue

                # 追加到最终回答文本
                chunk = line.decode("utf-8")
                if chunk.startswith("0:"):
                    # 如果是文本片段（0:表示文本片段）
                    word = json.loads(chunk[2:])
                    stackvm_response_text += word
                    # 发送文本片段
                    yield ChatEvent(
                        event_type=ChatEventType.TEXT_PART,
                        payload=word,
                    )
                else:
                    # 如果是其他类型的消息，直接转发
                    yield line + b"\n"

                try:
                    # 尝试获取任务ID（8:表示状态信息）
                    if chunk.startswith("8:") and task_id is None:
                        states = json.loads(chunk[2:])
                        if len(states) > 0:
                            # 通过 http://endpoint/?task_id=$task_id 访问任务
                            task_id = states[0].get("task_id")
                except Exception as e:
                    logger.error(f"从块中获取task_id失败: {e}")

        # 保存回答文本
        response_text = stackvm_response_text
        # 构建基础URL
        base_url = stream_chat_api_url.replace("/api/stream_execute_vm", "")
        try:
            # 执行后验证
            post_verification_result_url = self._post_verification(
                goal,
                response_text,
                self.db_chat_obj.id,
                db_assistant_message.id,
            )
            db_assistant_message.post_verification_result_url = (
                post_verification_result_url
            )
        except Exception:
            logger.error(
                "后验证任务期间发生特定错误。", exc_info=True
            )

        # 构建追踪URL
        trace_url = f"{base_url}?task_id={task_id}" if task_id else ""
        # 准备消息元数据
        message_meta = {
            "task_id": task_id,
            "goal": goal,
            **response_format,
        }

        # 更新助手消息
        db_assistant_message.content = response_text
        db_assistant_message.trace_url = trace_url
        db_assistant_message.meta = message_meta
        db_assistant_message.updated_at = datetime.now(UTC)
        db_assistant_message.finished_at = datetime.now(UTC)
        self.db_session.add(db_assistant_message)

        # 更新用户消息
        db_user_message.trace_url = trace_url
        db_user_message.meta = message_meta
        db_user_message.updated_at = datetime.now(UTC)
        db_user_message.finished_at = datetime.now(UTC)
        self.db_session.add(db_user_message)
        self.db_session.commit()

        # 发送数据事件，通知前端聊天完成
        yield ChatEvent(
            event_type=ChatEventType.DATA_PART,
            payload=ChatStreamDataPayload(
                chat=self.db_chat_obj,
                user_message=db_user_message,
                assistant_message=db_assistant_message,
            ),
        )

    def _generate_goal(self) -> Generator[ChatEvent, None, Tuple[str, dict]]:
        """
        生成目标和响应格式
        
        返回:
            生成器，最终产生目标和响应格式的元组
        """
        try:
            # 使用问题优化方法生成目标
            refined_question = yield from self._refine_user_question(
                user_question=self.user_question,
                chat_history=self.chat_history,
                refined_question_prompt=self.engine_config.llm.generate_goal_prompt,
                annotation_silent=True,
            )

            # 处理优化后的问题得到目标
            goal = refined_question.strip()
            if goal.startswith("Goal: "):
                goal = goal[len("Goal: ") :].strip()
        except Exception as e:
            # 如果生成失败，使用原始问题作为目标
            logger.error(f"使用相关知识图谱优化问题失败: {e}")
            goal = self.user_question

        # 解析目标和响应格式
        response_format = {}
        try:
            clean_goal, response_format = parse_goal_response_format(goal)
            logger.info(f"清理后的目标: {clean_goal}, 响应格式: {response_format}")
            if clean_goal:
                goal = clean_goal
        except Exception as e:
            logger.error(f"解析目标和响应格式失败: {e}")

        # 返回目标和响应格式
        return goal, response_format

    def _get_latest_chat_messages(self, chat_id: str, limit: int = 5) -> List[Dict]:
        """
        获取最近的聊天消息
        
        Args:
            chat_id: 聊天ID
            limit: 最大返回消息数
            
        Returns:
            List[Dict]: 聊天消息列表
        """
        try:
            # 从数据库获取聊天消息
            chat = chat_repo.get(self.db_session, chat_id)
            if not chat:
                return []
                
            # 获取所有消息并限制数量
            messages = chat_repo.get_messages(self.db_session, chat)
            if not messages:
                return []
                
            # 转换为简化的字典格式，便于后续处理
            result = []
            for msg in messages[-limit:]:  # 取最新的limit条消息
                result.append({
                    "id": msg.id,
                    "role": msg.role,
                    "content": msg.content,
                    "created_at": msg.created_at
                })
                
            return result
        except Exception as e:
            logger.warning(f"获取最近聊天消息时出错: {str(e)}")
            return []