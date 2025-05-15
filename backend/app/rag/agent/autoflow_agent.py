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
        return ChatEvent(
            event_type=ChatEventType(event_type.value), 
            payload=json.dumps(data)
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
            
            # 准备chat_history供agent使用
            chat_messages = []
            for msg in self.chat_history:
                chat_messages.append(
                    ChatMessage(
                        role=msg.role,
                        content=msg.content
                    )
                )
            
            # 将当前用户问题添加到messages中
            chat_messages.append(
                ChatMessage(
                    role=MessageRole.USER,
                    content=self.user_question
                )
            )
            
            # 使用同步方式执行agent
            # 这里可以改为异步方式，但需要处理streaming response
            response = self.agent.chat(chat_messages)
            
            # 获取agent思考过程
            for step in self.agent.get_steps():
                # 记录工具选择过程
                yield self._create_tool_event(
                    ToolEventType.TOOL_THINKING,
                    {
                        "step": step.get("step", ""),
                        "thought": step.get("thought", ""),
                        "observation": step.get("observation", ""),
                    }
                )
                
                # 如果有工具调用，记录工具调用信息
                tool_call = step.get("action")
                if tool_call:
                    tool_name = tool_call.get("tool", "")
                    tool_input = tool_call.get("tool_input", {})
                    
                    # 记录工具调用
                    yield self._create_tool_event(
                        ToolEventType.TOOL_CALL,
                        {
                            "tool": tool_name,
                            "input": tool_input,
                            "step_id": str(step.get("step", ""))
                        }
                    )
                    
                    # 记录工具调用结果
                    yield self._create_tool_event(
                        ToolEventType.TOOL_RESULT,
                        {
                            "tool": tool_name,
                            "result": step.get("observation", ""),
                            "step_id": str(step.get("step", ""))
                        }
                    )
            
            # 返回最终回答
            yield self._create_message_event(
                response.message.content,
                ChatMessageSate.GENERATE_ANSWER
            )
            
            # 如果有source nodes信息，添加到响应中
            source_nodes = getattr(response, "source_nodes", [])
            if source_nodes:
                yield ChatEvent(
                    event_type=ChatEventType.DATA_PART,
                    payload=json.dumps({"sources": source_nodes})
                )
            
            # 结束
            yield self._create_message_event("处理完成", ChatMessageSate.FINISHED)
            
        except Exception as e:
            logger.error(f"Agent执行失败: {str(e)}")
            # 返回错误信息
            yield ChatEvent(
                event_type=ChatEventType.ERROR_PART,
                payload=f"处理问题时出错: {str(e)}"
            )