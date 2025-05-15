"""
AutoFlow Agent模块

实现智能代理，协调多个工具完成复杂任务
"""

import enum
import json
import logging
from typing import Dict, List, Optional, Any, Generator, Union, Tuple
from uuid import UUID

from llama_index.core.agent import ReActAgent
from llama_index.core.llms.llm import LLM
from llama_index.core.tools.types import BaseTool
from llama_index.core.base.llms.types import ChatMessage, MessageRole
from sqlmodel import Session

from app.rag.chat.config import ChatEngineConfig 
from app.rag.chat.stream_protocol import ChatEvent, ChatStreamMessagePayload
from app.rag.types import ChatEventType, ChatMessageSate
from app.models import User

# 导入工具类
from app.rag.agent.tools.knowledge_retrieval_tool import KnowledgeRetrievalTool
from app.rag.agent.tools.knowledge_graph_tool import KnowledgeGraphQueryTool
from app.rag.agent.tools.response_generator_tool import ResponseGeneratorTool
from app.rag.agent.tools.deep_research_tool import DeepResearchTool
from app.rag.agent.tools.sql_query_adapter import SQLQueryToolAdapter

# 导入ToolManager
from app.rag.agent.tool_manager import ToolManager

logger = logging.getLogger(__name__)

# 定义工具调用事件类型（扩展现有ChatEventType）
class ToolEventType(int, enum.Enum):
    TOOL_START = 10    # 工具调用开始
    TOOL_THINKING = 11  # 工具选择思考过程
    TOOL_CALL = 12      # 工具调用
    TOOL_RESULT = 13    # 工具调用结果
    AGENT_THINKING = 14 # Agent思考过程


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
    
    def _create_tool_event(
        self, event_type: ToolEventType, data: Any
    ) -> ChatEvent:
        """创建工具相关的事件"""
        # 创建一个ChatStreamMessagePayload对象来包装数据
        # 使用一个固定状态，但将数据放在message字段中
        payload = ChatStreamMessagePayload(
            state=ChatMessageSate.TRACE,  # 使用TRACE状态表示工具事件
            message=json.dumps(data) if not isinstance(data, str) else data,  # 确保消息是字符串
            context=data  # 在context中保留原始数据结构
        )
        
        return ChatEvent(
            event_type=ChatEventType(event_type.value), 
            payload=payload
        )
    
    def _create_message_event(
        self, message: str, state: ChatMessageSate = ChatMessageSate.TRACE
    ) -> ChatEvent:
        """创建消息事件"""
        payload = ChatStreamMessagePayload(
            state=state,
            message=message
        )
        return ChatEvent(event_type=ChatEventType.TEXT_PART, payload=payload)
    
    def chat(self) -> Generator[ChatEvent, None, None]:
        """
        执行聊天对话流程
        
        返回:
            Generator[ChatEvent, None, None]: 事件生成器
        """
        # 创建开始事件
        yield self._create_message_event("开始处理您的问题...", ChatMessageSate.TRACE)
        
        try:
            # 发送思考事件
            yield self._create_tool_event(
                ToolEventType.AGENT_THINKING,
                {"message": "分析问题中...", "query": self.user_question}
            )
            
            # self.user_question 是当前用户消息 (str)
            # self.chat_history 是 List[ChatMessage] 历史记录
            # ReActAgent.chat() 期望 message: str 和可选的 chat_history: List[ChatMessage]
            
            logger.info(f"Calling agent.chat with user_question: '{self.user_question}' and chat_history of length {len(self.chat_history) if self.chat_history else 0}")
            response = self.agent.chat(message=self.user_question, chat_history=self.chat_history)
            
            # 获取agent思考过程 - response.sources 包含工具输出信息
            # 详细的思考步骤（Thought, Action, Observation）目前依赖 verbose=True 输出到日志
            # 后续可以考虑使用 CallbackManager 捕获更细致的步骤

            if response and hasattr(response, 'sources') and response.sources:
                for tool_output in response.sources:
                    # 记录工具调用结果
                    yield self._create_tool_event(
                        ToolEventType.TOOL_RESULT,
                        {
                            "tool": tool_output.tool_name,
                            "input": tool_output.raw_input.get("args", {}) if tool_output.raw_input else {},
                            "result": tool_output.content,
                        }
                    )
            
            # 返回最终回答
            # response.response 是最终的文本回答
            # response.message 是 ChatMessage 类型，也包含最终回答
            final_answer = ""
            if response:
                if hasattr(response, 'response'):
                    final_answer = response.response
                elif hasattr(response, 'message') and hasattr(response.message, 'content'):
                    final_answer = response.message.content

            yield self._create_message_event(
                final_answer if final_answer else "未能生成回答。",
                ChatMessageSate.GENERATE_ANSWER
            )
            
            # 如果有source nodes信息（通常由 RetrieverTool 直接返回，Agent 的 sources 更通用）
            # AgentChatResponse 的 sources 已经是 ToolOutput，我们上面处理过了
            # 如果需要更底层的 NodeWithScore，可能需要工具内部返回并传递
            
            # 结束
            yield self._create_message_event("处理完成", ChatMessageSate.FINISHED)
            
        except Exception as e:
            logger.error(f"Agent执行失败: {str(e)}", exc_info=True)
            # 返回错误信息
            # 确保错误事件的payload也是一个结构化的JSON字符串
            error_payload = ChatStreamMessagePayload(
                state=ChatMessageSate.ERROR,
                message=f"处理问题时出错: {str(e)}"
            )
            yield ChatEvent(
                event_type=ChatEventType.ERROR_PART,
                payload=error_payload # ChatEvent 会自动处理序列化
            )