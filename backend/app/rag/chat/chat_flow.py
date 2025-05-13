# 导入必要的库和模块
import json  # 用于处理JSON格式的数据
import logging  # 用于记录程序运行日志
from datetime import datetime, UTC  # 用于处理日期和时间，UTC表示协调世界时
from typing import List, Optional, Generator, Tuple, Any, Dict, Union, cast
from urllib.parse import urljoin  # 用于构建完整的URL
from uuid import UUID  # 用于处理通用唯一标识符
import os
import time
import asyncio

# 导入网络请求库
import requests  # 用于发送HTTP请求

# 导入性能追踪相关的库
from langfuse.llama_index import LlamaIndexInstrumentor  # 用于接入Langfuse性能追踪系统
from langfuse.llama_index._context import langfuse_instrumentor_context  # 用于管理追踪上下文
from langfuse.client import Langfuse  # 用于Langfuse客户端

# 导入LlamaIndex核心组件
from llama_index.core import get_response_synthesizer, VectorStoreIndex, StorageContext, load_index_from_storage, Settings, Response, QueryBundle  # 用于获取响应合成器
from llama_index.core.base.llms.types import ChatMessage, MessageRole  # 用于定义聊天消息和角色
from llama_index.core.schema import NodeWithScore  # 用于表示带有相关度分数的文档节点
from llama_index.core.prompts.rich import RichPromptTemplate  # 用于处理富文本提示模板
from llama_index.core.agent.react import ReActAgent  # 用于创建ReAct代理
from llama_index.core.tools import ToolOutput, QueryEngineTool, ToolMetadata, FunctionTool  # 工具输出类型

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
    Source,  # 源文档模型
    DatabaseConnection,  # 数据库连接模型
)

# 导入聊天引擎配置
from app.rag.chat.config import ChatEngineConfig  # 聊天引擎配置类

# 导入检索流程和数据结构
from app.rag.chat.retrieve.retrieve_flow import SourceDocument, RetrieveFlow  # 检索流程和源文档模型

# 导入流式协议相关组件
from app.rag.chat.stream_protocol import (
    ChatEvent,  # 聊天事件
    ChatStreamDataPayload,  # 聊天流数据载荷
    ChatStreamMessagePayload,  # 聊天流消息载荷
)

# 导入DSPy（用于声明式语言处理）相关库
from app.rag.llms.dspy import get_dspy_lm_by_llama_llm, setup_dspy_rm  # 将LlamaLLM转换为DSPy语言模型

# 导入知识图谱相关组件
from app.rag.retrievers.knowledge_graph.schema import KnowledgeGraphRetrievalResult  # 知识图谱检索结果
from app.rag.chat.kg_retriever import DatabaseMetadataKGRetriever  # 数据库元数据知识图谱检索器

# 导入类型定义
from app.rag.types import ChatEventType, ChatMessageSate, DocumentWithScore  # 聊天事件类型和消息状态

# 导入工具函数
from app.rag.utils import parse_goal_response_format  # 解析目标响应格式

# 导入仓库
from app.repositories import chat_repo, message_repo, source_repo, knowledge_base_repo  # 聊天仓库，用于数据库操作

# 导入站点设置
from app.site_settings import SiteSetting  # 站点设置，包含全局配置

# 导入追踪工具
from app.utils.tracing import LangfuseContextManager  # Langfuse上下文管理器

# 导入数据库工具工厂
from app.rag.tools.database_tools import create_database_connection_tools, create_db_tools  # 创建数据库工具

# 导入知识图谱相关任务
from app.tasks.knowledge_graph_tasks import index_database_metadata_to_kg  # 将数据库元数据索引到知识图谱

# 导入聊天流程相关工具
from app.rag.chat.utils import get_trace_manager  # 获取追踪管理器
from app.rag.chat.search_query_rewrite import search_query_rewrite  # 搜索查询重写

# 导入LlamaIndex相关工具
from llama_index.core.callbacks import CallbackManager, CBEventType, EventPayload  # 用于回调管理
from llama_index.core.base.response.schema import StreamingResponse  # 用于流式响应

# 导入DSPy相关工具
import dspy  # 用于DSPy语言模型

# 设置日志记录器
logger = logging.getLogger(__name__)  # 创建一个与当前模块同名的日志记录器

# 设置DSPy模型
setup_dspy_rm()

# 初始化Langfuse
langfuse = None
if settings.LANGFUSE_SECRET_KEY and settings.LANGFUSE_HOST and settings.LANGFUSE_PUBLIC_KEY:
    try:
        langfuse = Langfuse(
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            secret_key=settings.LANGFUSE_SECRET_KEY,
            host=settings.LANGFUSE_HOST
        )
    except Exception as e:
        logger.error(f"无法初始化Langfuse: {str(e)}")

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
        self.chat_start_time = time.time()  # 保存聊天开始时间

        # 解析聊天消息，获取用户问题和历史记录
        self.user_question, self.chat_history = parse_chat_messages(chat_messages)
        
        # 初始化追踪管理器
        self._trace_manager = get_trace_manager(user.email)
        
        # 加载配置
        self.config = ChatEngineConfig.load_from_db(self.db_session, self.engine_name)
        
        # 创建聊天记录
        self.chat = self._create_chat()
        
        # 初始化工具和代理
        self.db_tools = []
        self.agent = None
        self.db_kg_retriever = None
        
        # 如果配置中包含数据库连接，初始化数据库工具
        if self.config.database is not None:
            self._init_database_tools()
        
        # 初始化大语言模型(LLM)
        self._llm = self.config.get_llama_llm(self.db_session)  # 主LLM，用于生成完整回答
        self._fast_llm = self.config.get_fast_llama_llm(self.db_session)  # 快速LLM，用于辅助任务
        self._fast_dspy_lm = get_dspy_lm_by_llama_llm(self._fast_llm)  # 创建DSPy语言模型

        # 加载知识库
        self.knowledge_bases = self.config.get_knowledge_bases(self.db_session)  # 获取配置的知识库
        self.knowledge_base_ids = [kb.id for kb in self.knowledge_bases]  # 提取知识库ID列表

        # 初始化检索流程
        self.retrieve_flow = RetrieveFlow(
            db_session=self.db_session,  # 数据库会话
            engine_name=self.engine_name,  # 引擎名称
            engine_config=self.config,  # 引擎配置
            llm=self._llm,  # 主LLM
            fast_llm=self._fast_llm,  # 快速LLM
            knowledge_bases=self.knowledge_bases,  # 知识库列表
        )

    def _init_database_tools(self):
        """初始化数据库工具和知识图谱检索器"""
        # 创建数据库查询工具
        self.db_tools = create_db_tools(self.config)
        
        # 初始化知识图谱检索器
        try:
            # 如果知识图谱索引不存在，则创建
            kg_persist_dir = "./kg_storage/db_metadata"
            if not os.path.exists(kg_persist_dir):
                logger.info("数据库元数据知识图谱不存在，正在创建...")
                kg_index = index_database_metadata_to_kg(kg_persist_dir)
            else:
                # 加载现有知识图谱索引
                logger.info("从存储中加载数据库元数据知识图谱...")
                from llama_index.graph_stores.simple import SimpleGraphStore
                graph_store = SimpleGraphStore()
                storage_context = StorageContext.from_defaults(graph_store=graph_store)
                
                try:
                    kg_index = load_index_from_storage(
                        storage_context=storage_context,
                        persist_dir=kg_persist_dir,
                        index_id="db_metadata_kg"
                    )
                    logger.info("成功加载数据库元数据知识图谱")
                except Exception as e:
                    logger.error(f"加载知识图谱失败: {e}，将创建新的知识图谱")
                    kg_index = index_database_metadata_to_kg(kg_persist_dir)
                
            # 创建数据库元数据知识图谱检索器
            self.db_kg_retriever = DatabaseMetadataKGRetriever(kg_index)
            logger.info("数据库元数据知识图谱检索器初始化完成")
            
        except Exception as e:
            logger.exception(f"初始化知识图谱检索器失败: {e}")
            self.db_kg_retriever = None
            
        # 如果有数据库工具，创建ReAct代理
        if self.db_tools:
            try:
                llm = self.config.get_llama_llm()
                
                # 根据配置的工具模式决定是否使用代理
                if self.config.database.tool_mode == "autonomous":
                    logger.info("以自主模式创建数据库代理")
                    self.agent = ReActAgent.from_tools(
                        self.db_tools,
                        llm=llm,
                        verbose=True,
                        context="""你是一个强大的AI助手，可以帮助用户查询数据库。当用户询问数据相关的问题时，你可以使用数据库工具来获取信息并回答。
                        请在需要时使用工具，但不要过度使用。只有当需要查询数据库时才使用查询工具。"""
                    )
                else:
                    logger.info("配置为引导模式，不创建自主代理")
            except Exception as e:
                logger.exception(f"创建数据库代理失败: {e}")
                self.agent = None

    def _create_chat(self) -> Chat:
        """创建聊天记录"""
        # 如果已有聊天ID，则获取现有聊天
        if self.chat_id:
            chat = chat_repo.get(self.db_session, self.chat_id)
            if chat:
                return chat
        
        # 创建新聊天
        chat = chat_repo.create(
            self.db_session,
            DBChat(
                # 待做: 标题应该由LLM生成
                title=self.user_question[:100],  # 使用问题前100个字符作为标题
                engine_id=self.config.get_db_chat_engine().id,  # 设置引擎ID
                engine_options=self.config.screenshot(),  # 保存引擎配置快照
                user_id=self.user.id if self.user else None,  # 设置用户ID
                browser_id=self.browser_id,  # 设置浏览器ID
                origin=self.origin,  # 设置请求来源
                visibility=(
                    ChatVisibility.PUBLIC  # 如果是匿名用户，设为公开
                    if not self.user
                    else ChatVisibility.PRIVATE  # 如果是登录用户，设为私有
                ),
            ),
        )
        self.chat_id = chat.id  # 获取新创建的聊天ID

        # 注意: Slack/Discord机器人可能创建带有历史消息的新聊天
        now = datetime.now(UTC)  # 获取当前UTC时间
        # 保存聊天历史到数据库
        for i, m in enumerate(self.chat_history):
            chat_repo.create_message(
                session=self.db_session,
                chat=chat,
                chat_message=DBChatMessage(
                    role=m.role,  # 消息角色
                    content=m.content,  # 消息内容
                    ordinal=i + 1,  # 消息序号
                    created_at=now,  # 创建时间
                    updated_at=now,  # 更新时间
                    finished_at=now,  # 完成时间
                ),
            )

        return chat

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
                    "is_external_engine": self.config.is_external_engine,  # 是否使用外部引擎
                    "chat_engine_config": self.config.screenshot(),  # 引擎配置快照
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
                if self.config.is_external_engine:
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

    def _builtin_chat(self) -> Generator[ChatEvent | str, None, Tuple[Optional[str], List[Any]]]:
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
        ) = yield from self._search_knowledge_graph(self.user_question)

        # 步骤3: 使用知识图谱和聊天历史重写用户问题以增强检索效果
        refined_question = yield from self._refine_user_question(
            self.user_question,
            self.chat_history,
            knowledge_graph_context,
            refined_question_prompt=self.config.llm.condense_question_prompt,
        )

        # 步骤4: 检查问题是否提供了足够的上下文信息，是否需要澄清
        if self.config.clarify_question:
            need_clarify, need_clarify_response = yield from self._clarify_question(
                refined_question,
                self.chat_history,
                knowledge_graph_context,
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

        # 步骤5: 使用优化后的问题搜索相关的文档块
        relevant_chunks = yield from self._search_relevance_chunks(refined_question)

        # 步骤6: 决定使用代理还是传统RAG流程生成回答
        response_text = ""
        source_documents = []
        
        # 检查是否应该使用数据库工具
        should_use_db_tools = (
            self.agent is not None and 
            self._should_use_database_tools(refined_question, relevant_chunks)
        )
        
        if should_use_db_tools:
            # 通知前端正在思考
            yield ChatEvent(
                event_type=ChatEventType.MESSAGE_ANNOTATIONS_PART,
                payload=ChatStreamMessagePayload(
                    state=ChatMessageSate.THINKING,
                    display="分析问题，准备查询数据库...",
                ),
            )
            
            # 使用追踪管理器记录代理决策的性能
            with self._trace_manager.span(
                name="agent_reasoning", input=refined_question
            ) as span:
                try:
                    # 构建完整的提示
                    prompt_with_context = f"""基于以下上下文信息回答问题。如果上下文信息不足以回答，你可以使用数据库查询工具获取更多信息。

                    问题: {refined_question}

                    知识图谱上下文:
                    {knowledge_graph_context}

                    相关知识:
                    """
                    # 添加文档上下文
                    if relevant_chunks:
                        for i, chunk in enumerate(relevant_chunks):
                            prompt_with_context += f"\n文档 {i+1}:\n{chunk.node.get_content()}\n"
                            
                    # 收集工具调用信息以展示给用户
                    tool_calls_for_display = []
                    
                    # 流式输出代理的思考过程和工具调用
                    for step in self.agent.stream_chat(prompt_with_context):
                        # 检查是否是思考过程
                        if hasattr(step, "thinking") and step.thinking:
                            # 将思考过程作为注释发送
                            yield ChatEvent(
                                event_type=ChatEventType.MESSAGE_ANNOTATIONS_PART,
                                payload=ChatStreamMessagePayload(
                                    state=ChatMessageSate.TOOL_CALLING,
                                    display=f"思考: {step.thinking}",
                                ),
                            )
                        
                        # 检查是否是工具调用
                        if hasattr(step, "tool_call") and step.tool_call:
                            tool_name = step.tool_call.tool_name
                            tool_input = step.tool_call.tool_input
                            
                            # 提取查询文本，用于前端展示
                            if isinstance(tool_input, dict) and 'natural_language_query' in tool_input:
                                query_text = tool_input['natural_language_query']
                            else:
                                query_text = str(tool_input)
                                
                            # 为前端准备工具调用信息
                            tool_call_display = {
                                "tool": tool_name.replace("query_", "").replace("_", " "),
                                "query": query_text,
                                "status": "执行中..."
                            }
                            tool_calls_for_display.append(tool_call_display)
                            
                            # 通知前端正在执行工具调用
                            yield ChatEvent(
                                event_type=ChatEventType.MESSAGE_ANNOTATIONS_PART,
                                payload=ChatStreamMessagePayload(
                                    state=ChatMessageSate.TOOL_CALLING,
                                    display=f"正在查询数据库: {tool_name}",
                                    context=tool_calls_for_display,
                                ),
                            )
                        
                        # 检查是否是工具输出
                        if hasattr(step, "tool_output") and step.tool_output:
                            tool_output = step.tool_output
                            
                            if isinstance(tool_output, ToolOutput):
                                # 提取工具名称和输出内容
                                output_str = str(tool_output.content)
                                tool_name = tool_output.tool_name if hasattr(tool_output, 'tool_name') else "未知工具"
                                
                                # 尝试从输出中提取SQL
                                sql_query = "未提供SQL"
                                if "生成的SQL:" in output_str:
                                    sql_parts = output_str.split("生成的SQL:", 1)
                                    if len(sql_parts) > 1:
                                        sql_query = sql_parts[1].split("\n\n", 1)[0].strip()
                                
                                # 更新工具调用展示信息
                                for call_display in tool_calls_for_display:
                                    if call_display["tool"] == tool_name.replace("query_", "").replace("_", " "):
                                        call_display["status"] = "已完成"
                                        call_display["sql"] = sql_query
                                
                                # 创建源文档对象，用于展示查询结果
                                source_doc = SourceDocument(
                                    id=f"db_tool_{tool_name}",
                                    title=f"数据库查询: {tool_name}",
                                    text=f"查询: {query_text}\nSQL: {sql_query}\n结果: {output_str}",
                                    metadata={
                                        "tool_name": tool_name,
                                        "query": query_text,
                                        "sql": sql_query
                                    }
                                )
                                source_documents.append(source_doc)
                                
                                # 通知前端更新工具调用状态
                                yield ChatEvent(
                                    event_type=ChatEventType.MESSAGE_ANNOTATIONS_PART,
                                    payload=ChatStreamMessagePayload(
                                        state=ChatMessageSate.TOOL_CALLING,
                                        display=f"数据库查询结果",
                                        context=tool_calls_for_display,
                                    ),
                                )
                        
                        # 检查是否是响应片段
                        if hasattr(step, "response") and step.response and hasattr(step, "delta") and step.delta:
                            response_text += step.delta
                            yield ChatEvent(
                                event_type=ChatEventType.TEXT_PART,
                                payload=step.delta,
                            )
                    
                    # 如果回答为空，抛出异常
                    if not response_text:
                        raise Exception("代理未能生成有效响应")
                    
                    # 记录追踪结果
                    span.end(
                        output=response_text,
                        metadata={
                            "source_documents": source_documents,
                            "used_database_tools": True,
                            "tool_calls": tool_calls_for_display
                        }
                    )
                    
                except Exception as e:
                    # 记录异常日志
                    logger.exception(f"代理处理过程中出错: {e}")
                    
                    # 通知前端发生错误
                    yield ChatEvent(
                        event_type=ChatEventType.MESSAGE_ANNOTATIONS_PART,
                        payload=ChatStreamMessagePayload(
                            state=ChatMessageSate.ERROR,
                            display="数据库查询过程中出错，尝试使用知识库回答"
                        ),
                    )
                    
                    # 回退到传统RAG流程
                    response_text, source_documents = yield from self._fallback_to_rag(
                        refined_question, knowledge_graph_context
                    )
        else:
            # 如果不需要使用数据库工具，使用传统RAG流程
            response_text, source_documents = yield from self._generate_answer(
                refined_question, knowledge_graph_context, relevant_chunks
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
            chat=self.chat,
            chat_message=DBChatMessage(
                role=MessageRole.USER.value,  # 设置角色为用户
                trace_url=self._trace_manager.trace_url,  # 设置追踪URL
                content=self.user_question.strip(),  # 设置消息内容（去除首尾空格）
            ),
        )
        
        # 创建助手消息记录（初始为空内容）
        db_assistant_message = chat_repo.create_message(
            session=self.db_session,
            chat=self.chat,
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
                chat=self.chat,
                user_message=db_user_message,
                assistant_message=db_assistant_message,
            ),
        )
        
        # 返回创建的消息对象
        return db_user_message, db_assistant_message

    async def _search_knowledge_graph(
        self, user_query: str, relevant_kg: Optional[Dict] = None
    ) -> Generator[ChatEvent, None, Tuple[Dict, str]]:
        """
        搜索知识图谱获取相关信息
        
        Args:
            user_query: 用户查询
            relevant_kg: 可选的已有相关知识图谱
            
        Returns:
            生成器，最终返回(知识图谱结果, 提示词)
        """
        with self._trace_manager.span("search_knowledge_graph"):
            # 创建事件并提供进度更新
            event = ChatEvent(
                event_type=ChatEventType.SEARCHING,
                message_state=ChatMessageSate.SEARCHING,
                payload={"target": "knowledge_graph"}
            )
            yield event
            
            results = {}
            prompt = ""
            
            # 检索数据库元数据知识图谱
            if self.db_kg_retriever is not None:
                try:
                    logger.info(f"从数据库元数据知识图谱检索信息: {user_query}")
                    db_metadata = self.db_kg_retriever.retrieve(user_query)
                    
                    if db_metadata:
                        # 提取与查询相关的数据库、表和列信息
                        mentioned_entities = self._extract_mentioned_entities(db_metadata)
                        
                        # 如果找到了相关的数据库实体，提取完整结构信息
                        if mentioned_entities.get("databases"):
                            db_structures = {}
                            for db_name in mentioned_entities["databases"]:
                                db_structure = self.db_kg_retriever.retrieve_db_structure(db_name)
                                if db_structure:
                                    db_structures.update(db_structure)
                            
                            if db_structures:
                                results["database_metadata"] = {
                                    "structures": db_structures,
                                    "relations": db_metadata
                                }
                                
                                # 构建提示词
                                prompt = self._build_db_metadata_prompt(results["database_metadata"])
                                logger.info(f"检索到数据库元数据并构建提示词")
                except Exception as e:
                    logger.exception(f"搜索数据库元数据知识图谱时出错: {e}")
            
            # 更新事件表明搜索完成
            event = ChatEvent(
                event_type=ChatEventType.SEARCHING_DONE,
                message_state=ChatMessageSate.SEARCHING_DONE,
                payload={"target": "knowledge_graph"}
            )
            yield event
            
            return results, prompt

    def _extract_mentioned_entities(self, metadata_list: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """从知识图谱检索结果中提取提到的实体"""
        entities = {
            "databases": set(),
            "tables": set(),
            "columns": set()
        }
        
        for item in metadata_list:
            subject = item.get("subject", "")
            relation = item.get("relation", "")
            obj = item.get("object", "")
            
            # 识别数据库
            if relation == "is_a" and obj == "Database":
                entities["databases"].add(subject)
                
            # 识别表
            elif relation == "is_a" and obj == "Table":
                # 表名通常是 db_name.table_name 格式
                parts = subject.split(".")
                if len(parts) >= 2:
                    entities["databases"].add(parts[0])
                    entities["tables"].add(subject)
                    
            # 识别列
            elif relation == "is_a" and obj == "Column":
                # 列名通常是 db_name.table_name.column_name 格式
                parts = subject.split(".")
                if len(parts) >= 3:
                    entities["databases"].add(parts[0])
                    entities["tables"].add(f"{parts[0]}.{parts[1]}")
                    entities["columns"].add(subject)
                    
            # 通过关系图进一步提取
            elif relation == "contains_table":
                entities["databases"].add(subject)
                entities["tables"].add(obj)
                
            elif relation == "contains_column":
                entities["tables"].add(subject)
                entities["columns"].add(obj)
        
        return {
            "databases": list(entities["databases"]),
            "tables": list(entities["tables"]),
            "columns": list(entities["columns"])
        }
    
    def _build_db_metadata_prompt(self, db_metadata: Dict[str, Any]) -> str:
        """根据数据库元数据构建提示词"""
        prompt = "以下是与用户查询相关的数据库元数据信息，可帮助你理解数据结构:\n\n"
        
        # 添加数据库结构信息
        if "structures" in db_metadata:
            for db_name, db_info in db_metadata["structures"].items():
                prompt += f"数据库: {db_name}\n"
                if "description" in db_info:
                    prompt += f"描述: {db_info['description']}\n"
                
                if "tables" in db_info:
                    prompt += "表:\n"
                    for table_name, table_info in db_info["tables"].items():
                        prompt += f"  - {table_name}"
                        if "description" in table_info:
                            prompt += f": {table_info['description']}"
                        prompt += "\n"
                        
                        if "columns" in table_info:
                            prompt += "    列:\n"
                            for col_name, col_info in table_info["columns"].items():
                                prompt += f"      * {col_name}"
                                if "description" in col_info:
                                    prompt += f": {col_info['description']}"
                                prompt += "\n"
                prompt += "\n"
        
        # 添加关系提示
        if "relations" in db_metadata and db_metadata["relations"]:
            prompt += "相关元数据关系:\n"
            for rel in db_metadata["relations"][:5]:  # 限制显示数量
                prompt += f"- {rel['subject']} {rel['relation']} {rel['object']}\n"
        
        return prompt

    def _should_use_database_tools(self, user_query: str, kg_results: Dict) -> bool:
        """
        确定是否应该使用数据库工具
        
        Args:
            user_query: 用户查询
            kg_results: 知识图谱检索结果
            
        Returns:
            布尔值，表示是否应该使用数据库工具
        """
        # 如果没有配置数据库或工具，不使用数据库工具
        if not self.config.database or not self.db_tools or not self.agent:
            return False
            
        # 检查工具模式
        tool_mode = self.config.database.tool_mode
        
        # 自主模式：总是使用代理
        if tool_mode == "autonomous":
            return True
            
        # 引导模式：只有在查询涉及数据库且知识图谱中有相关数据库元数据时使用
        elif tool_mode == "guided":
            # 检查知识图谱结果中是否包含数据库元数据
            has_db_metadata = (
                "database_metadata" in kg_results and 
                kg_results["database_metadata"]["structures"]
            )
            
            if has_db_metadata:
                # 使用快速LLM确定是否是数据库相关查询
                fast_llm = self.config.get_fast_llama_llm()
                
                # 构建系统提示
                system_prompt = """
                你的任务是判断用户的查询是否与数据库查询相关。
                如果用户询问需要查询数据库的问题（如查询数据、统计信息、数据分析等），
                回答"是"；否则回答"否"。
                """
                
                try:
                    # 准备上下文
                    db_context = ""
                    for db_name in kg_results["database_metadata"]["structures"]:
                        db_context += f"- 数据库: {db_name}\n"
                    
                    prompt = f"""
                    可用的数据库:
                    {db_context}
                    
                    用户查询: {user_query}
                    
                    这是关于数据库查询的问题吗？只回答"是"或"否"
                    """
                    
                    messages = [
                        ChatMessage(role=MessageRole.SYSTEM, content=system_prompt),
                        ChatMessage(role=MessageRole.USER, content=prompt)
                    ]
                    
                    response = fast_llm.chat(messages)
                    answer = response.message.content.strip().lower()
                    
                    # 检查回答是否表示这是数据库查询
                    is_db_query = "是" in answer or "yes" in answer
                    logger.info(f"数据库查询判断: {answer} (是数据库查询: {is_db_query})")
                    
                    return is_db_query
                    
                except Exception as e:
                    logger.exception(f"判断是否使用数据库工具时出错: {e}")
            
        # 默认不使用数据库工具
        return False

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
        post_verification_url = self.config.post_verification_url
        post_verification_token = self.config.post_verification_token

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
            self.chat.id,
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
                chat=self.chat,
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
                if self.config.clarify_question:
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
            self.config.external_engine_config.stream_chat_api_url
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
                self.chat.id,
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
                chat=self.chat,
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
                refined_question_prompt=self.config.llm.generate_goal_prompt,
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

    def _fallback_to_rag(
        self, 
        user_question: str, 
        knowledge_graph_context: str
    ) -> Generator[ChatEvent, None, Tuple[str, List[SourceDocument]]]:
        """
        当代理处理失败时回退到传统RAG流程
        
        参数:
            user_question: 用户问题
            knowledge_graph_context: 知识图谱上下文
            
        返回:
            生成器，最终产生回答文本和源文档列表的元组
        """
        # 发送回退通知
        yield ChatEvent(
            event_type=ChatEventType.MESSAGE_ANNOTATIONS_PART,
            payload=ChatStreamMessagePayload(
                state=ChatMessageSate.INFO,
                display="回退到知识库检索以获取答案",
            ),
        )
        
        # 搜索相关文档块
        relevant_chunks = yield from self._search_relevance_chunks(user_question)
        
        # 使用标准RAG流程生成回答
        response_text, source_documents = yield from self._generate_answer(
            user_question=user_question,
            knowledge_graph_context=knowledge_graph_context,
            relevant_chunks=relevant_chunks,
        )
        
        return response_text, source_documents

    def _search_relevance_chunks(
        self, user_question: str
    ) -> Generator[ChatEvent, None, List[NodeWithScore]]:
        """
        搜索与问题最相关的文档块
        
        参数:
            user_question: 用户问题（可能是已重写的）
            
        返回:
            生成器，最终产生带有相关度分数的文档节点列表
        """
        # 使用追踪管理器记录相关文档搜索的性能
        with self._trace_manager.span(
            name="search_relevance_chunks", input=user_question
        ) as span:
            # 发送步骤提示
            yield ChatEvent(
                event_type=ChatEventType.MESSAGE_ANNOTATIONS_PART,
                payload=ChatStreamMessagePayload(
                    state=ChatMessageSate.SEARCHING,
                    display="检索最相关的文档",
                ),
            )

            # 调用检索流程搜索相关文档块
            relevance_chunks = self.retrieve_flow.search_relevant_chunks(user_question)

            # 记录追踪结果
            span.end(
                output={
                    "relevance_chunks": relevance_chunks,
                }
            )

            # 返回相关文档块
            return relevance_chunks

    def _generate_answer(
        self,
        user_question: str,
        knowledge_graph_context: str,
        relevant_chunks: List[NodeWithScore],
    ) -> Generator[ChatEvent, None, Tuple[str, List[SourceDocument]]]:
        """
        使用传统RAG流程根据用户问题、知识图谱上下文和相关文档块生成回答
        
        注意：此方法仅处理传统RAG流程，不处理数据库工具调用逻辑
        数据库工具调用已移至_builtin_chat方法中处理
        
        参数:
            user_question: 用户问题（可能是已重写的）
            knowledge_graph_context: 知识图谱上下文
            relevant_chunks: 相关文档块列表
            
        返回:
            生成器，最终产生回答文本和源文档列表的元组
        """
        # 使用追踪管理器记录回答生成的性能
        with self._trace_manager.span(
            name="generate_answer", input=user_question
        ) as span:
            # 初始化响应合成器
            text_qa_template = RichPromptTemplate(
                template_str=self.config.llm.text_qa_prompt
            )
            # 部分格式化模板，填入固定参数
            text_qa_template = text_qa_template.partial_format(
                current_date=datetime.now().strftime("%Y-%m-%d"),  # 当前日期
                graph_knowledges=knowledge_graph_context,  # 知识图谱上下文
                original_question=self.user_question,  # 原始问题
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
                nodes=relevant_chunks,  # 相关文档块
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
                    "used_database_tools": False,
                },
            )

            # 返回回答文本和源文档
            return response_text, source_documents

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
                self.config.llm.clarifying_question_prompt
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

            # 创建提示模板
            prompt_template = RichPromptTemplate(refined_question_prompt)
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