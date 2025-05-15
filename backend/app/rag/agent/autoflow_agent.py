"""
AutoFlow Agent模块

实现智能代理，协调多个工具完成复杂任务
"""

import enum
import json
import logging
from typing import Dict, List, Optional, Any, Generator, Union, Tuple
from uuid import UUID
from datetime import datetime, UTC

from llama_index.core.agent import ReActAgent
from llama_index.core.llms.llm import LLM
from llama_index.core.tools.types import BaseTool
from llama_index.core.base.llms.types import ChatMessage, MessageRole
from sqlmodel import Session

from app.core.config import settings
from app.rag.chat.config import ChatEngineConfig 
from app.rag.chat.stream_protocol import ChatEvent, ChatStreamMessagePayload, ChatStreamDataPayload
from app.rag.types import ChatEventType, ChatMessageSate
from app.models import User, ChatMessage as DBChatMessage
from app.repositories import chat_repo
from app.utils.tracing import LangfuseContextManager
from langfuse.llama_index import LlamaIndexInstrumentor
from langfuse.llama_index._context import langfuse_instrumentor_context

# 导入工具类
from app.rag.agent.tools.knowledge_retrieval_tool import KnowledgeRetrievalTool
from app.rag.agent.tools.knowledge_graph_tool import KnowledgeGraphQueryTool
from app.rag.agent.tools.response_generator_tool import ResponseGeneratorTool
from app.rag.agent.tools.deep_research_tool import DeepResearchTool
from app.rag.agent.tools.sql_query_adapter import SQLQueryToolAdapter

# 导入ToolManager
from app.rag.agent.tool_manager import ToolManager

logger = logging.getLogger(__name__)



class AutoFlowAgent:
    """
    AutoFlow智能代理
    
    协调多个工具完成复杂任务的智能代理实现
    """
    
    def __init__(
        self,
        db_session: Session,
        user: User,
        browser_id: str,
        origin: str,
        chat_messages: List[ChatMessage],
        engine_name: str = "default",
        chat_id: Optional[UUID] = None,
    ):
        """
        初始化AutoFlow智能代理
        
        参数:
            db_session: 数据库会话对象
            user: 当前用户对象
            browser_id: 浏览器ID
            origin: 请求来源
            chat_messages: 聊天消息列表
            engine_name: 引擎名称
            chat_id: 聊天ID
        """
        self.db_session = db_session
        self.user = user
        self.browser_id = browser_id
        self.origin = origin
        self.chat_messages = chat_messages
        self.engine_name = engine_name
        self.chat_id = chat_id
        
        # 解析用户问题和聊天历史
        self.user_question, self.chat_history = self._parse_chat_messages(chat_messages)
        
        # 加载引擎配置
        self.engine_config = ChatEngineConfig.load_from_db(db_session, engine_name)
        
        # 获取主LLM
        self.llm = self.engine_config.get_llama_llm(db_session)
        
        # 初始化所有工具
        self.tools = self._initialize_tools()
        
        # 初始化ReActAgent
        self.agent = self._initialize_agent()
        
        # 初始化追踪管理器
        self._initialize_tracing()
        
        # 初始化或获取当前聊天对象（与chat_flow保持一致）
        self.db_chat_obj = self._get_or_create_chat(chat_id)
    
    def _initialize_tracing(self):
        """初始化Langfuse性能追踪"""
        from app.site_settings import SiteSetting
        
        try:
            # 检查是否启用Langfuse
            enable_langfuse = (
                SiteSetting.langfuse_secret_key and SiteSetting.langfuse_public_key
            )
            
            # 创建Langfuse观察器
            instrumentor = LlamaIndexInstrumentor(
                host=SiteSetting.langfuse_host,
                secret_key=SiteSetting.langfuse_secret_key,
                public_key=SiteSetting.langfuse_public_key,
                enabled=enable_langfuse,
            )
            
            # 创建追踪管理器
            self._trace_manager = LangfuseContextManager(instrumentor)
        except Exception as e:
            # 捕获所有追踪初始化错误，记录但不中断主流程
            logger.warning(f"追踪初始化失败，禁用性能追踪: {str(e)}")
            
            # 创建一个无操作的追踪管理器
            class NoOpContextManager:
                def observe(self, **kwargs):
                    class NoOpTrace:
                        def __enter__(self): return self
                        def __exit__(self, *args, **kwargs): pass
                        def update(self, **kwargs): pass
                        trace_url = None
                    return NoOpTrace()
                
            self._trace_manager = NoOpContextManager()
    
    def _get_or_create_chat(self, chat_id: Optional[UUID] = None):
        """获取或创建聊天对象"""
        from app.models import Chat as DBChat, ChatVisibility
        
        if chat_id:
            # 获取已有聊天
            db_chat_obj = chat_repo.get(self.db_session, chat_id)
            if not db_chat_obj:
                from app.exceptions import ChatNotFound
                raise ChatNotFound(chat_id)
                
            logger.info(f"为聊天 {chat_id} 初始化AutoFlowAgent (聊天引擎: {db_chat_obj.engine.name})")
            return db_chat_obj
        else:
            # 创建新聊天
            db_chat_engine = self.engine_config.get_db_chat_engine()
            
            db_chat_obj = chat_repo.create(
                self.db_session,
                DBChat(
                    title=self.user_question[:100],  # 使用问题前100个字符作为标题
                    engine_id=db_chat_engine.id,
                    engine_options=self.engine_config.screenshot(),
                    user_id=self.user.id if self.user else None,
                    browser_id=self.browser_id,
                    origin=self.origin,
                    visibility=(
                        ChatVisibility.PUBLIC
                        if not self.user
                        else ChatVisibility.PRIVATE
                    ),
                ),
            )
            
            # 保存聊天历史（如果有）
            now = datetime.now(UTC)
            for i, m in enumerate(self.chat_history):
                chat_repo.create_message(
                    session=self.db_session,
                    chat=db_chat_obj,
                    chat_message=DBChatMessage(
                        role=m.role,
                        content=m.content,
                        ordinal=i + 1,
                        created_at=now,
                        updated_at=now,
                        finished_at=now,
                    ),
                )
            
            return db_chat_obj
        
    def _parse_chat_messages(
        self, chat_messages: List[ChatMessage]
    ) -> tuple[str, List[ChatMessage]]:
        """解析聊天消息"""
        user_question = chat_messages[-1].content
        chat_history = chat_messages[:-1]
        return user_question, chat_history
    
    def _initialize_tools(self) -> List[BaseTool]:
        """初始化所有工具"""
        # 使用ToolManager获取已启用的工具
        tool_manager = ToolManager(db_session=self.db_session, engine_config=self.engine_config)
        return tool_manager.get_enabled_tools()
    
    def _initialize_agent(self) -> ReActAgent:
        """初始化ReActAgent"""
        # 创建系统提示词
        system_prompt = """你是AutoFlow，一个智能的知识库助手。
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
        
        # 创建ReActAgent
        return ReActAgent.from_tools(
            tools=self.tools,
            llm=self.llm,
            system_prompt=system_prompt,
            verbose=True
        )
    
    def _create_tool_call_event(
        self, tool_name: str, tool_args: Dict[str, Any], tool_id: str = "1"
    ) -> ChatEvent:
        """
        创建工具调用事件（与前端tool_call事件兼容）
        
        参数:
            tool_name: 工具名称
            tool_args: 工具参数
            tool_id: 工具调用ID（默认为"1"）
        """
        logger.info(f"开始调用工具 - 工具: {tool_name}, 参数: {tool_args}")
        
        # 使用前端期望的格式创建事件
        return ChatEvent(
            event_type=ChatEventType.MESSAGE_ANNOTATIONS_PART,
            payload={
                "toolCallId": tool_id,
                "toolName": tool_name,
                "args": tool_args
            }
        )
    
    def _create_tool_result_event(
        self, tool_result: Any, tool_id: str = "1"
    ) -> ChatEvent:
        """
        创建工具结果事件（与前端tool_result事件兼容）
        
        参数:
            tool_result: 工具返回结果
            tool_id: 工具调用ID（默认为"1"，需要与调用ID匹配）
        """
        logger.info(f"创建工具结果 - 结果类型: {type(tool_result).__name__}")
        
        # 使用前端期望的格式创建事件
        return ChatEvent(
            event_type=ChatEventType.MESSAGE_ANNOTATIONS_PART,
            payload={
                "toolCallId": tool_id,
                "result": tool_result
            }
        )
    
    def _create_message_event(
        self, message: str, state: ChatMessageSate = ChatMessageSate.TRACE
    ) -> ChatEvent:
        """创建消息事件"""
        logger.info(f"创建消息事件 - 消息类型: TEXT_PART (ID=0), 状态: {state.name}, 消息内容: {message[:50]}...")
        
        # 对于 TEXT_PART 事件，直接使用字符串作为 payload
        return ChatEvent(event_type=ChatEventType.TEXT_PART, payload=message)
    
    def _create_state_event(
        self, 
        state: ChatMessageSate, 
        message: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> ChatEvent:
        """
        创建状态更新事件（基于MESSAGE_ANNOTATIONS_PART）
        
        参数:
            state: 消息状态
            message: 状态描述
            context: 上下文数据（可选）
        """
        logger.info(f"创建状态事件 (MESSAGE_ANNOTATIONS_PART) - 状态: {state.name}, 消息: {message}")
        
        payload = ChatStreamMessagePayload(
            state=state,
            message=message,
            context=context
        )
        
        return ChatEvent(
            event_type=ChatEventType.MESSAGE_ANNOTATIONS_PART,
            payload=payload
        )
    
    def _chat_start(
        self,
    ) -> Generator[ChatEvent, None, Tuple[DBChatMessage, DBChatMessage]]:
        """
        开始聊天处理，创建用户和助手的消息记录
        
        返回:
            生成器，最终产生用户消息和助手消息对象的元组
        """
        logger.info(f"开始聊天处理，创建用户和助手消息记录")
        
        # 创建用户消息记录
        db_user_message = chat_repo.create_message(
            session=self.db_session,
            chat=self.db_chat_obj,
            chat_message=DBChatMessage(
                role=MessageRole.USER.value,  # 设置角色为用户
                trace_url=self._trace_manager.trace_url if hasattr(self, '_trace_manager') else None,  # 设置追踪URL
                content=self.user_question.strip(),  # 设置消息内容（去除首尾空格）
            ),
        )
        
        # 创建助手消息记录（初始为空内容）
        db_assistant_message = chat_repo.create_message(
            session=self.db_session,
            chat=self.db_chat_obj,
            chat_message=DBChatMessage(
                role=MessageRole.ASSISTANT.value,  # 设置角色为助手
                trace_url=self._trace_manager.trace_url if hasattr(self, '_trace_manager') else None,  # 设置追踪URL
                content="",  # 初始内容为空
            ),
        )
        
        # 发送数据事件，通知前端已创建消息
        logger.info(f"发送初始化数据事件 (DATA_PART)")
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
    
    def _chat_finish(
        self,
        db_assistant_message: DBChatMessage,
        db_user_message: DBChatMessage,
        response_text: str,
        source_documents: Optional[List] = [],
        knowledge_graph: Optional[Any] = None,
    ) -> Generator[ChatEvent, None, None]:
        """
        完成聊天处理，保存回答和相关信息
        
        参数:
            db_assistant_message: 助手消息对象
            db_user_message: 用户消息对象
            response_text: 回答文本
            source_documents: 源文档列表（可选）
            knowledge_graph: 知识图谱数据（可选）
        """
        logger.info(f"完成聊天处理，保存回答和相关信息")
        
        # 保存当前的追踪上下文
        ctx = langfuse_instrumentor_context.get().copy()
        
        # 发送完成事件
        yield self._create_state_event(
            state=ChatMessageSate.FINISHED,
            message="回答完成"
        )

        # 更新助手消息
        db_assistant_message.sources = [s.model_dump() if hasattr(s, 'model_dump') else s for s in source_documents] if source_documents else []  # 保存源文档
        if knowledge_graph and hasattr(knowledge_graph, 'to_stored_graph_dict'):
            db_assistant_message.graph_data = knowledge_graph.to_stored_graph_dict()  # 保存知识图谱数据
        db_assistant_message.content = response_text  # 保存回答文本
        db_assistant_message.updated_at = datetime.now(UTC)  # 更新时间
        db_assistant_message.finished_at = datetime.now(UTC)  # 完成时间
        self.db_session.add(db_assistant_message)  # 添加到会话

        # 更新用户消息
        if knowledge_graph and hasattr(knowledge_graph, 'to_stored_graph_dict'):
            db_user_message.graph_data = knowledge_graph.to_stored_graph_dict()  # 保存知识图谱数据
        db_user_message.updated_at = datetime.now(UTC)  # 更新时间
        db_user_message.finished_at = datetime.now(UTC)  # 完成时间
        self.db_session.add(db_user_message)  # 添加到会话
        self.db_session.commit()  # 提交事务

        # 恢复追踪上下文
        langfuse_instrumentor_context.get().update(ctx)

        # 发送数据事件，通知前端聊天完成
        logger.info(f"发送最终数据事件 (DATA_PART)")
        yield ChatEvent(
            event_type=ChatEventType.DATA_PART,
            payload=ChatStreamDataPayload(
                chat=self.db_chat_obj,
                user_message=db_user_message,
                assistant_message=db_assistant_message,
            ),
        )
    
    def chat(self) -> Generator[ChatEvent, None, None]:
        """
        执行聊天对话流程
        
        返回:
            Generator[ChatEvent, None, None]: 事件生成器
        """
        logger.info("===== 开始AutoFlowAgent.chat流程 =====")
        
        # 使用追踪管理器记录整个聊天过程的性能
        try:
            with self._trace_manager.observe(
                trace_name="AutoFlowAgent",  # 追踪名称
                user_id=(
                    self.user.email if self.user else f"anonymous-{self.browser_id}"
                ),  # 用户ID
                metadata={
                    "chat_engine": self.engine_name,  # 引擎名称
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
                
                # 保存当前的追踪上下文
                ctx = langfuse_instrumentor_context.get().copy()
                
                # 步骤1: 创建聊天消息记录
                db_user_message, db_assistant_message = yield from self._chat_start()
                
                # 恢复追踪上下文
                langfuse_instrumentor_context.get().update(ctx)
                
                # 创建开始事件 (使用纯文本消息)
                logger.info("生成开始事件 (TEXT_PART) - 消息: '开始处理您的问题...'")
                start_event = self._create_message_event("开始处理您的问题...", ChatMessageSate.TRACE)
                
                logger.info(f"开始事件payload类型: {type(start_event.payload).__name__}")
                yield start_event
                
                try:
                    # 发送思考事件 - 使用message_annotations类型事件而不是工具事件
                    logger.info("生成思考事件 (TRACE)")
                    yield self._create_state_event(
                        state=ChatMessageSate.TRACE,
                        message="分析问题中...",
                        context={"message": "分析问题中...", "query": self.user_question}
                    )
                    
                    # 调用Agent处理问题
                    logger.info(f"Calling agent.chat with user_question: '{self.user_question}' and chat_history of length {len(self.chat_history) if self.chat_history else 0}")
                    try:
                        # 使用安全的方式调用agent.chat并处理结果
                        raw_response = self.agent.chat(message=self.user_question, chat_history=self.chat_history)
                        logger.info(f"Agent回复类型: {type(raw_response).__name__}")
                        
                        # 创建自定义响应对象避免raw_output问题
                        class CustomResponse:
                            def __init__(self, original_response):
                                # 复制原始响应的所有属性
                                self.original = original_response
                                self.response = getattr(original_response, 'response', str(original_response))
                                self.sources = []
                                
                                # 安全提取sources
                                if hasattr(original_response, 'sources'):
                                    self.sources = original_response.sources
                        
                        # 转换为安全的响应对象
                        response = CustomResponse(raw_response)
                        logger.info(f"已创建自定义响应对象，sources数量: {len(response.sources)}")
                        
                    except Exception as e:
                        logger.error(f"Agent.chat调用失败: {str(e)}", exc_info=True)
                        # 创建一个基本的响应对象
                        class CustomResponse:
                            def __init__(self, response_text):
                                self.response = response_text
                                self.sources = []
                        
                        response = CustomResponse("很抱歉，在处理您的问题时遇到了技术问题。请稍后再试。")
                        
                        # 创建自定义工具输出对象
                        class CustomTool:
                            def __init__(self, tool_name, content, raw_input):
                                self.tool_name = tool_name
                                self.content = content
                                self.raw_input = raw_input
                        
                        # 添加错误信息作为工具输出
                        error_tool = CustomTool(
                            tool_name="error",
                            content={"error": str(e)},
                            raw_input={"query": self.user_question}
                        )
                        response.sources.append(error_tool)
                    
                    # 获取agent思考过程 - response.sources 包含工具输出信息
                    # 详细的思考步骤（Thought, Action, Observation）目前依赖 verbose=True 输出到日志
                    # 后续可以考虑使用 CallbackManager 捕获更细致的步骤
                    source_documents = []
                    
                    if response and hasattr(response, 'sources') and response.sources:
                        # 为每个工具调用分配唯一ID
                        for i, tool_output in enumerate(response.sources):
                            tool_id = str(i + 1)  # 从1开始的工具ID
                            
                            # 安全获取工具名称
                            if hasattr(tool_output, 'tool_name'):
                                tool_name = tool_output.tool_name
                            elif isinstance(tool_output, dict) and 'tool_name' in tool_output:
                                tool_name = tool_output['tool_name']
                            else:
                                tool_name = f"tool_{tool_id}"
                                
                            logger.info(f"处理工具输出 #{tool_id} - 工具名称: {tool_name}")
                            
                            # 安全获取工具输入参数
                            tool_input = {}
                            # 简化工具输入提取逻辑
                            if hasattr(tool_output, 'raw_input') and tool_output.raw_input:
                                if isinstance(tool_output.raw_input, dict):
                                    tool_input = tool_output.raw_input
                                    if "args" in tool_input:
                                        tool_input = tool_input["args"]
                            elif isinstance(tool_output, dict) and 'raw_input' in tool_output:
                                raw_input = tool_output['raw_input']
                                if isinstance(raw_input, dict):
                                    tool_input = raw_input
                                    if "args" in raw_input:
                                        tool_input = raw_input["args"]
                            
                            logger.info(f"工具 #{tool_id} ({tool_name}) 输入参数: {tool_input}")
                            
                            # 发送工具开始状态更新
                            yield self._create_state_event(
                                state=ChatMessageSate.SEARCH_RELATED_DOCUMENTS,
                                message=f"使用工具: {tool_name}",
                                context={"tool": tool_name}
                            )
                            
                            # 1. 发送工具调用事件
                            logger.info(f"开始调用工具 - 工具: {tool_name}, ID: {tool_id}")
                            yield self._create_tool_call_event(
                                tool_name=tool_name,
                                tool_args=tool_input,
                                tool_id=tool_id
                            )
                            
                            # 安全获取工具结果
                            tool_result = None
                            # 简化工具结果获取逻辑
                            if hasattr(tool_output, 'content'):
                                tool_result = tool_output.content
                            elif hasattr(tool_output, 'output'):
                                tool_result = tool_output.output
                            elif isinstance(tool_output, dict):
                                # 依次尝试常见的结果属性名
                                for key in ['content', 'output', 'result', 'response', 'data']:
                                    if key in tool_output:
                                        tool_result = tool_output[key]
                                        break
                            
                            # 如果仍为None，创建基本结果
                            if tool_result is None:
                                tool_result = {"tool_output": str(tool_output)}
                            
                            logger.info(f"工具 #{tool_id} ({tool_name}) 结果获取成功")
                            
                            # 2. 发送工具结果事件
                            logger.info(f"生成工具结果 - 工具: {tool_name}, ID: {tool_id}")
                            yield self._create_tool_result_event(
                                tool_result=tool_result,
                                tool_id=tool_id
                            )
                            
                            # 收集源文档（如果有）
                            if tool_name == "knowledge_retrieval":
                                logger.info(f"处理知识检索工具 #{tool_id} 源文档")
                                try:
                                    if hasattr(tool_output, 'source_nodes'):
                                        # 标准对象方式
                                        logger.info(f"从source_nodes属性发现 {len(tool_output.source_nodes)} 个节点")
                                        source_documents.extend(tool_output.source_nodes)
                                    elif hasattr(tool_output, 'nodes') and tool_output.nodes:
                                        # 直接节点属性
                                        logger.info(f"从nodes属性发现 {len(tool_output.nodes)} 个节点")
                                        source_documents.extend(tool_output.nodes)
                                    elif isinstance(tool_output, dict):
                                        # 字典方式
                                        if "nodes" in tool_output:
                                            logger.info(f"从nodes字典键发现 {len(tool_output['nodes'])} 个节点")
                                            # 对每个节点进行转换，确保它们是可序列化的
                                            for node in tool_output["nodes"]:
                                                # 尝试各种转换方法，确保节点可以序列化
                                                if isinstance(node, dict):
                                                    # 已经是字典，直接添加
                                                    source_documents.append(node)
                                                elif hasattr(node, 'to_dict'):
                                                    # 使用to_dict方法
                                                    source_documents.append(node.to_dict())
                                                elif hasattr(node, 'model_dump'):
                                                    # 使用model_dump方法
                                                    source_documents.append(node.model_dump())
                                                elif hasattr(node, 'dict'):
                                                    # 使用dict方法
                                                    source_documents.append(node.dict())
                                                elif hasattr(node, '__dict__'):
                                                    # 尝试将对象转换为字典
                                                    source_documents.append(node.__dict__)
                                                else:
                                                    # 如果什么都不行，转换为字符串并存储
                                                    logger.warning(f"无法将节点转换为字典，存储为字符串: {type(node).__name__}")
                                                    source_documents.append({
                                                        "node_type": str(type(node)),
                                                        "node_string": str(node)
                                                    })
                                        elif "source_nodes" in tool_output:
                                            logger.info(f"从source_nodes字典键发现 {len(tool_output['source_nodes'])} 个节点")
                                            for node in tool_output["source_nodes"]:
                                                if isinstance(node, dict):
                                                    source_documents.append(node)
                                                else:
                                                    try:
                                                        node_dict = vars(node)
                                                        source_documents.append(node_dict)
                                                    except:
                                                        logger.warning(f"无法将source_node转换为字典: {type(node).__name__}")
                                        elif "content" in tool_output and isinstance(tool_output["content"], dict) and "nodes" in tool_output["content"]:
                                            logger.info(f"从content.nodes字典键发现 {len(tool_output['content']['nodes'])} 个节点")
                                            for node in tool_output["content"]["nodes"]:
                                                if isinstance(node, dict):
                                                    source_documents.append(node)
                                                else:
                                                    try:
                                                        node_dict = vars(node)
                                                        source_documents.append(node_dict)
                                                    except:
                                                        logger.warning(f"无法将content.nodes转换为字典: {type(node).__name__}")
                                    # 如果工具结果是字典并包含节点
                                    if isinstance(tool_result, dict):
                                        if "nodes" in tool_result:
                                            logger.info(f"从工具结果中发现 {len(tool_result['nodes'])} 个节点")
                                            for node in tool_result["nodes"]:
                                                if isinstance(node, dict):
                                                    source_documents.append(node)
                                                else:
                                                    try:
                                                        node_dict = vars(node)
                                                        source_documents.append(node_dict)
                                                    except:
                                                        logger.warning(f"无法将工具结果节点转换为字典: {type(node).__name__}")
                                except Exception as e:
                                    logger.error(f"处理知识检索源文档时出错: {str(e)}", exc_info=True)
                                
                                logger.info(f"知识检索工具 #{tool_id} 总共收集了 {len(source_documents)} 个源文档")
                    
                    # 发送生成回答状态事件
                    logger.info("生成状态事件 - 正在生成回答")
                    yield self._create_state_event(
                        state=ChatMessageSate.GENERATE_ANSWER,
                        message="正在生成回答..."
                    )
                    
                    # 获取最终回答
                    # response.response 是最终的文本回答
                    # response.message 是 ChatMessage 类型，也包含最终回答
                    final_answer = ""
                    if response:
                        if hasattr(response, 'response'):
                            final_answer = response.response
                        elif hasattr(response, 'message') and hasattr(response.message, 'content'):
                            final_answer = response.message.content
        
                    # 对于最终回答，使用纯文本事件
                    logger.info(f"生成最终回答事件 (TEXT_PART) - 内容长度: {len(final_answer)}")
                    final_event = self._create_message_event(
                        final_answer if final_answer else "未能生成回答。",
                        ChatMessageSate.GENERATE_ANSWER
                    )
                    logger.info(f"最终回答事件payload类型: {type(final_event.payload).__name__}")
                    yield final_event
                    
                    # 步骤7: 完成聊天，保存回答和相关信息
                    yield from self._chat_finish(
                        db_assistant_message=db_assistant_message,
                        db_user_message=db_user_message,
                        response_text=final_answer,
                        source_documents=source_documents,
                    )
                    
                    # 更新追踪输出信息
                    trace.update(output=final_answer)
                    
                except Exception as e:
                    logger.error(f"Agent执行失败: {str(e)}", exc_info=True)
                    # 返回错误信息
                    error_message = f"处理问题时出错: {str(e)}"
                    
                    # 发送错误状态事件 - 使用ERROR状态代替FAILED
                    logger.info("生成错误状态事件")
                    yield self._create_state_event(
                        state=ChatMessageSate.FINISHED,
                        message="处理失败",
                        context={"error": str(e)}
                    )
                    
                    # 发送错误文本事件
                    logger.info("生成错误事件 (ERROR_PART)")
                    yield ChatEvent(
                        event_type=ChatEventType.ERROR_PART,
                        payload=error_message
                    )
                    
                    # 更新失败的助手消息
                    db_assistant_message.content = error_message
                    db_assistant_message.updated_at = datetime.now(UTC)
                    db_assistant_message.finished_at = datetime.now(UTC)
                    self.db_session.add(db_assistant_message)
                    self.db_session.commit()
                    
                    # 更新追踪错误信息
                    trace.update(error=str(e))
                
        except Exception as e:
            # 捕获并记录任何异常
            logger.exception(e)
            # 向用户发送错误消息
            error_message = f"处理聊天时遇到错误: {str(e)}。请稍后再试。"
            
            # 发送错误状态事件 - 使用ERROR状态代替FAILED
            yield self._create_state_event(
                state=ChatMessageSate.FINISHED,
                message="系统错误",
                context={"error": str(e)}
            )
            
            # 发送错误文本事件
            yield ChatEvent(
                event_type=ChatEventType.ERROR_PART,
                payload=error_message
            )
            
        logger.info("===== 结束AutoFlowAgent.chat流程 =====")