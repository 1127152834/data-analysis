import asyncio
from typing import Any, Dict, List, Optional, Union, AsyncGenerator
from datetime import datetime

from sqlalchemy.orm import Session
from llama_index.core.llms import LLM
from llama_index.core.indices import VectorStoreIndex
from llama_index.core.indices.knowledge_graph import KnowledgeGraphIndex

from app.rag.chat.stream_protocol import ChatEvent
from app.rag.types import ChatEventType, ChatMessageSate

from .context import Context
from .events import Event, StartEvent, StopEvent, PrepEvent, ReasoningEvent, ResponseEvent, ExternalEngineEvent
from .agents.input_processor import InputProcessorAgent
from .agents.knowledge_agent import KnowledgeAgent
from .agents.reasoning_agent import ReasoningAgent
from .agents.response_agent import ResponseAgent
from .agents.external_engine_agent import ExternalEngineAgent
from .workflow import Workflow

class AutoFlowAgent:
    """基于事件驱动的工作流智能体，实现模块化、可扩展的聊天流程"""
    
    def __init__(self, db_session: Session = None, engine_config: Any = None):
        """初始化工作流智能体
        
        参数:
            db_session: 数据库会话，用于数据存储和检索
            engine_config: 引擎配置，包含LLM和检索器配置
        """
        self.db_session = db_session
        self.engine_config = engine_config
        
        # 初始化工作流
        self.workflow = Workflow()
        
        # 从engine_config获取LLM模型
        self.llm = None
        self.fast_llm = None
        
        if engine_config:
            if hasattr(engine_config, "get_llama_llm"):
                self.llm = engine_config.get_llama_llm(db_session)
                
            if hasattr(engine_config, "get_fast_llama_llm"):
                self.fast_llm = engine_config.get_fast_llama_llm(db_session)
        
        # 判断是否为外部引擎
        self.is_external_engine = False
        if engine_config and hasattr(engine_config, "is_external_engine"):
            self.is_external_engine = engine_config.is_external_engine
        
        # 初始化数据库聊天对象
        self.db_chat_obj = None
        
        # 初始化各个专用智能体
        self.input_processor = InputProcessorAgent(db_session, engine_config, self.llm, self.fast_llm)
        self.knowledge_agent = KnowledgeAgent(db_session, engine_config, self.llm, self.fast_llm)
        self.reasoning_agent = ReasoningAgent(db_session, engine_config, self.llm, self.fast_llm)
        self.response_agent = ResponseAgent(db_session, engine_config, self.llm, self.fast_llm)
        self.external_engine_agent = ExternalEngineAgent(db_session, engine_config, self.llm, self.fast_llm)
        
        # 设置回调函数
        self.response_agent.set_callback(self._on_chat_complete)
        
        # 初始化知识索引
        self.knowledge_index = None
        self.kg_index = None
        
        # 注册工作流步骤
        self._register_workflow_steps()
    
    def set_indices(self, knowledge_index: VectorStoreIndex = None, kg_index: KnowledgeGraphIndex = None):
        """设置知识索引"""
        self.knowledge_index = knowledge_index
        self.kg_index = kg_index
        
        # 将索引传递给知识智能体
        self.knowledge_agent.set_indices(knowledge_index, kg_index)
    
    def _register_workflow_steps(self):
        """注册工作流步骤"""
        # 注册各个步骤的处理函数
        self.workflow.add_step(StartEvent, self.input_processor.process)
        
        # 根据引擎类型注册不同的路径
        if self.is_external_engine:
            # 如果是外部引擎，StartEvent后直接使用ExternalEngineEvent
            self.workflow.add_step(PrepEvent, self._generate_external_engine_event)
            self.workflow.add_step(ExternalEngineEvent, self.external_engine_agent.process)
        else:
            # 内部引擎路径
            self.workflow.add_step(PrepEvent, self.knowledge_agent.process)
            self.workflow.add_step(ReasoningEvent, self.reasoning_agent.process)
            self.workflow.add_step(ResponseEvent, self.response_agent.process)
    
    async def _generate_external_engine_event(self, ctx: Context, event: Event) -> Event:
        """生成外部引擎事件，用于处理外部引擎路径"""
        # 获取用户问题
        user_question = await ctx.get("user_question", "")
        refined_question = await ctx.get("refined_question", user_question)
        
        # 简单处理：直接使用优化后的问题作为目标
        return ExternalEngineEvent(goal=refined_question)
    
    async def stream_chat(self, query: str, chat_history: List[Dict] = None, db_chat_obj = None) -> AsyncGenerator[ChatEvent, None]:
        """流式聊天实现，遵循与前端的约定
        
        参数:
            query: 用户查询
            chat_history: 聊天历史记录
            db_chat_obj: 数据库聊天对象，可选
            
        返回:
            AsyncGenerator: 生成ChatEvent对象的异步生成器
        """
        if chat_history is None:
            chat_history = []
            
        try:
            # 创建初始事件和上下文
            start_event = StartEvent(user_question=query, chat_history=chat_history)
            context = Context(self.workflow)
            
            # 设置数据库聊天对象到上下文
            if db_chat_obj:
                await context.set("db_chat_obj", db_chat_obj)
            
            # 启动工作流
            first_handler = self.workflow.start(start_event, context)
            
            # 生成事件流
            event_count = 0
            async for event in first_handler.stream_events():
                event_count += 1
                # 确保事件是ChatEvent类型
                if event:
                    if not isinstance(event, ChatEvent):
                        # 如果不是ChatEvent，尝试转换
                        if hasattr(event, 'answer') and getattr(event, 'answer'):
                            # 如果有answer属性，转换为TEXT_PART
                            yield ChatEvent(
                                event_type=ChatEventType.TEXT_PART,
                                payload={"message": getattr(event, 'answer')}
                            )
                        elif hasattr(event, 'delta') and getattr(event, 'delta'):
                            # 如果有delta属性，转换为TEXT_PART
                            yield ChatEvent(
                                event_type=ChatEventType.TEXT_PART,
                                payload={"message": getattr(event, 'delta')}
                            )
                        else:
                            # 其他情况，转换为DATA_PART
                            import json
                            
                            try:
                                if hasattr(event, 'model_dump'):
                                    # Pydantic模型
                                    event_data = event.model_dump()
                                else:
                                    # 普通对象
                                    event_data = {
                                        "event_type": type(event).__name__,
                                        "data": {k: v for k, v in event.__dict__.items() if not k.startswith('_')}
                                    }
                                
                                yield ChatEvent(
                                    event_type=ChatEventType.DATA_PART,
                                    payload=event_data
                                )
                            except Exception as conv_e:
                                # 转换失败，发送错误事件
                                yield ChatEvent(
                                    event_type=ChatEventType.ERROR_PART,
                                    payload=f"事件转换失败: {str(conv_e)}"
                                )
                    else:
                        # 已经是ChatEvent，直接返回
                        yield event
                    
        except Exception as e:
            # 处理错误
            error_event = ChatEvent(
                event_type=ChatEventType.ERROR_PART,
                payload=f"工作流执行错误: {str(e)}"
            )
            yield error_event
    
    async def _on_chat_complete(self, user_message: Dict, assistant_message: Dict, knowledge_nodes: List[Dict] = None):
        """聊天完成回调，用于执行后续操作，如记录日志、发送统计等"""
        # 实际应用中，此处可以进行各种后处理
        # 例如：更新用户模型、记录反馈、更新统计等
        pass 