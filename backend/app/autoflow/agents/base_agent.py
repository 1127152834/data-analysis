from typing import Any, Dict, Optional, Callable, Union, TypeVar, AsyncGenerator, List, Type
from abc import ABC, abstractmethod
import uuid
import logging
import asyncio
import json

from sqlalchemy.orm import Session
from llama_index.core.llms import LLM

from ..context import Context
from ..events import Event, StreamEvent
from ..events.tool_events import BaseEvent, ToolCallEvent, ToolResultEvent, InfoEvent, ErrorEvent, TextEvent, StepEndEvent
from ..events.converter import EventConverter
from ..tools.base import BaseTool, ToolParameters
from ..tools.registry import ToolRegistry

from app.rag.chat.stream_protocol import ChatEvent
from app.rag.types import ChatEventType

T = TypeVar('T', bound=Event)
E = TypeVar('E', bound=BaseEvent)

class BaseAgent(ABC):
    """基础Agent类，定义所有Agent的共同行为"""
    
    def __init__(self, 
                 name: str,
                 description: str,
                 db_session: Session = None, 
                 engine_config: Any = None,
                 tool_registry: Optional[ToolRegistry] = None):
        # 基本属性
        self.name = name
        self.description = description
        self.db_session = db_session
        self.engine_config = engine_config
        self._event_emitter: Optional[Callable] = None
        
        # 工具相关
        self.tool_registry = tool_registry or ToolRegistry()
        self.tools: Dict[str, BaseTool] = {}
        
        # 日志
        self.logger = logging.getLogger(f"autoflow.agents.{self.name}")
        
        # 事件队列
        self.events = []
        self.internal_events: List[BaseEvent] = []
    
    def set_event_emitter(self, emitter: Callable):
        """设置事件发射器"""
        self._event_emitter = emitter
    
    def emit_event(self, event: BaseEvent):
        """发送内部事件
        
        参数:
            event: 内部事件对象
        """
        self.internal_events.append(event)
        
        # 记录事件信息
        self.logger.info(f"【事件发送】添加内部事件: type={event.event_type}, id={event.id}")
        
        # 如果已设置事件发射器，转换内部事件为ChatEvent并发送
        if self._event_emitter:
            self.logger.info(f"【事件发送】转换并发送事件: type={event.event_type}")
            chat_event = EventConverter.to_chat_event(event)
            self.logger.info(f"【事件发送】调用事件发射器发送ChatEvent: type={chat_event.event_type.name}")
            self._event_emitter(chat_event)
        else:
            self.logger.warning(f"【事件发送】未设置事件发射器，无法发送事件: type={event.event_type}")
    
    def emit_info(self, message: str):
        """发送信息事件"""
        event = InfoEvent(message=message)
        self.emit_event(event)
    
    def emit_error(self, message: str):
        """发送错误事件"""
        event = ErrorEvent(message=message)
        self.emit_event(event)
    
    def emit_text(self, text: Any):
        """发送文本事件
        
        参数:
            text: 文本内容，可以是字符串或其他可序列化为字符串的对象
        """
        # 确保text是字符串
        if text is None:
            self.logger.warning("【emit_text】收到None文本，将使用空字符串")
            text = ""
        elif not isinstance(text, str):
            try:
                # 如果是字典或列表，尝试转为JSON
                if isinstance(text, (dict, list)):
                    self.logger.info(f"【emit_text】将复杂对象转换为JSON字符串: type={type(text).__name__}")
                    text = json.dumps(text, ensure_ascii=False)
                else:
                    # 其他类型直接转为字符串
                    self.logger.info(f"【emit_text】将非字符串类型转换为字符串: type={type(text).__name__}")
                    text = str(text)
            except Exception as e:
                self.logger.error(f"【emit_text】转换文本出错: {str(e)}")
                text = f"[无法显示的内容: {type(text).__name__}]"
        
        # 创建事件并发送
        self.logger.info(f"【emit_text】发送文本事件: length={len(text)}")
        event = TextEvent(message=text)
        self.emit_event(event)
    
    def emit_step_end(self, step: int):
        """发送步骤结束事件"""
        event = StepEndEvent(step=step)
        self.emit_event(event)
    
    async def call_tool(self, tool_name: str, parameters: Dict[str, Any], step: int) -> ToolResultEvent:
        """调用工具并发送相关事件
        
        参数:
            tool_name: 工具名称
            parameters: 工具参数
            step: 当前步骤
            
        返回:
            工具结果事件
        """
        # 获取工具
        tool = self.tool_registry.get_tool(tool_name)
        if not tool:
            error_msg = f"找不到工具: {tool_name}"
            self.logger.error(error_msg)
            self.emit_error(error_msg)
            return ToolResultEvent(
                tool_id=str(uuid.uuid4()),
                tool_name=tool_name,
                success=False,
                error_message=error_msg,
                step=step
            )
            
        # 创建工具参数
        try:
            # 创建工具调用事件
            tool_id = str(uuid.uuid4())
            call_event = ToolCallEvent(
                tool_name=tool_name,
                tool_id=tool_id,
                parameters=parameters,
                step=step
            )
            
            # 发送工具调用事件
            self.emit_event(call_event)
            
            # 创建参数实例
            param_instance = tool.parameter_type(**parameters)
            
            # 执行工具
            self.logger.info(f"执行工具 {tool_name} 参数: {parameters}")
            result = await tool.execute(param_instance)
            
            # 创建工具结果事件
            result_event = ToolResultEvent(
                tool_id=tool_id,
                tool_name=tool_name,
                success=result.success,
                error_message=result.error_message,
                result=result.model_dump() if hasattr(result, 'model_dump') else {},
                step=step
            )
            
            # 发送工具结果事件
            self.emit_event(result_event)
            
            return result_event
            
        except Exception as e:
            error_msg = f"工具 {tool_name} 执行错误: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            
            # 创建工具结果事件
            result_event = ToolResultEvent(
                tool_id=tool_id if 'tool_id' in locals() else str(uuid.uuid4()),
                tool_name=tool_name,
                success=False,
                error_message=error_msg,
                result={},
                step=step
            )
            
            # 发送工具结果事件
            self.emit_event(result_event)
            
            return result_event
    
    def register_tools(self, tools: List[BaseTool]):
        """注册多个工具"""
        for tool in tools:
            self.tool_registry.register_tool(tool)
    
    def _emit_legacy_event(self, event_type: str, payload: Any):
        """发送旧版事件到前端（兼容旧版代码）
        
        参数:
            event_type: 事件类型，如 "TEXT_PART"、"DATA_PART" 等
            payload: 事件载荷，根据事件类型而不同
        """
        self.logger.info(f"【Legacy事件】开始发送旧版事件: type={event_type}")
        
        # 确保payload格式正确
        if not isinstance(payload, list):
            self.logger.warning(f"【Legacy事件】payload不是数组格式: type={event_type}, payload_type={type(payload).__name__}")
            
            # 对于传入None的情况
            if payload is None:
                self.logger.info("【Legacy事件】payload为None，使用空数组")
                payload = []
            # 其他情况转换为数组
            else:
                self.logger.info(f"【Legacy事件】将payload转换为数组格式: {type(payload).__name__} -> list")
                payload = [payload]
        
        # 根据事件类型创建相应的ChatEvent
        event = None
        
        try:
            if event_type == "TEXT_PART":
                self.logger.debug(f"【Legacy事件】创建TEXT_PART事件: payload长度={len(payload)}")
                event = ChatEvent(
                    event_type=ChatEventType.TEXT_PART,
                    payload=payload,
                )
            elif event_type == "DATA_PART":
                self.logger.debug(f"【Legacy事件】创建DATA_PART事件: payload长度={len(payload)}")
                event = ChatEvent(
                    event_type=ChatEventType.DATA_PART,
                    payload=payload,
                )
            elif event_type == "MESSAGE_ANNOTATIONS_PART":
                self.logger.debug(f"【Legacy事件】创建MESSAGE_ANNOTATIONS_PART事件: payload长度={len(payload)}")
                event = ChatEvent(
                    event_type=ChatEventType.MESSAGE_ANNOTATIONS_PART,
                    payload=payload,
                )
            elif event_type == "ERROR_PART":
                self.logger.debug(f"【Legacy事件】创建ERROR_PART事件: payload长度={len(payload)}")
                event = ChatEvent(
                    event_type=ChatEventType.ERROR_PART,
                    payload=payload,
                )
            else:
                self.logger.warning(f"【Legacy事件】未识别的事件类型: {event_type}")
                return
                
            # 验证事件有效性
            if not hasattr(event, 'event_type') or not hasattr(event, 'payload'):
                self.logger.error(f"【Legacy事件】创建的事件无效: {event}")
                return
                
            # 将事件添加到队列中
            self.events.append(event)
            self.logger.info(f"【Legacy事件】事件已添加到队列: type={event_type}")
        except Exception as e:
            self.logger.error(f"【Legacy事件】创建事件失败: {str(e)}", exc_info=True)
    
    def _emit_stream_event(self, delta: str):
        """发射流式事件（兼容旧版代码）"""
        return StreamEvent(delta=delta)
    
    @abstractmethod
    async def process(self, ctx: Context, event: Event) -> Union[Event, AsyncGenerator[Event, None]]:
        """处理事件并返回下一个事件
        
        参数:
            ctx: 上下文对象
            event: 输入事件
            
        返回:
            下一个事件或事件生成器
        """
        pass 