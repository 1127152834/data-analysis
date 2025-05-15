from typing import Any, Dict, Optional, Callable, Union, TypeVar, AsyncGenerator
from abc import ABC, abstractmethod

from sqlalchemy.orm import Session
from llama_index.core.llms import LLM

from ..context import Context
from ..events import Event, StreamEvent
from app.rag.chat.stream_protocol import ChatEvent, ChatStreamDataPayload, ChatStreamMessagePayload
from app.rag.types import ChatEventType, ChatMessageSate

T = TypeVar('T', bound=Event)

class BaseAgent(ABC):
    """基础Agent类，定义所有Agent的共同行为"""
    
    def __init__(self, db_session: Session = None, engine_config: Any = None):
        self.db_session = db_session
        self.engine_config = engine_config
        self._event_emitter: Optional[Callable] = None
        # 初始化事件队列
        self.events = []
    
    def set_event_emitter(self, emitter: Callable):
        """设置事件发射器"""
        self._event_emitter = emitter
    
    def _emit_event(self, event_type: str, payload: Any):
        """发送事件到前端的统一入口
        
        参数:
            event_type: 事件类型，如 "TEXT_PART"、"DATA_PART" 等
            payload: 事件载荷，根据事件类型而不同
        """
        event = None
        
        # 根据事件类型创建相应的ChatEvent
        if event_type == "TEXT_PART":
            event = ChatEvent(
                event_type=ChatEventType.TEXT_PART,
                payload=payload,
            )
        elif event_type == "DATA_PART":
            event = ChatEvent(
                event_type=ChatEventType.DATA_PART,
                payload=ChatStreamDataPayload(**payload),
            )
        elif event_type == "MESSAGE_ANNOTATIONS_PART":
            event = ChatEvent(
                event_type=ChatEventType.MESSAGE_ANNOTATIONS_PART,
                payload=ChatStreamMessagePayload(**payload),
            )
        elif event_type == "ERROR_PART":
            event = ChatEvent(
                event_type=ChatEventType.ERROR_PART,
                payload=payload,
            )
        
        # 将事件添加到队列中
        if event:
            self.events.append(event)
    
    def _emit_stream_event(self, delta: str):
        """发射流式事件"""
        return StreamEvent(delta=delta)
    
    @abstractmethod
    async def process(self, ctx: Context, event: Event) -> Union[Event, AsyncGenerator[Event, None]]:
        """处理事件并返回下一个事件"""
        pass 