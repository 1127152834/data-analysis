from typing import Any, Dict
import logging
from app.rag.chat.stream_protocol import ChatEvent
from app.rag.types import ChatEventType
from .tool_events import BaseEvent, EventType, ToolCallEvent, ToolResultEvent, StepEndEvent, InfoEvent, ErrorEvent, TextEvent

# 添加日志记录器
logger = logging.getLogger("autoflow.events.converter")

class EventConverter:
    """事件转换器，将内部事件转换为前端可用的ChatEvent"""
    
    @staticmethod
    def to_chat_event(event: BaseEvent) -> ChatEvent:
        """将内部事件转换为ChatEvent"""
        logger.info(f"【事件转换】开始转换事件: type={event.event_type}, id={event.id}")
        
        chat_event = None
        if event.event_type == EventType.TOOL_CALL:
            chat_event = ChatEvent(
                event_type=ChatEventType.DATA_PART,
                payload=[event.to_dict()]
            )
            logger.debug(f"【事件转换】工具调用事件: {event.to_dict()}")
        elif event.event_type == EventType.TOOL_RESULT:
            chat_event = ChatEvent(
                event_type=ChatEventType.DATA_PART,
                payload=[event.to_dict()]
            )
            logger.debug(f"【事件转换】工具结果事件: {event.to_dict()}")
        elif event.event_type == EventType.STEP_END:
            chat_event = ChatEvent(
                event_type=ChatEventType.DATA_PART,
                payload=[event.to_dict()]
            )
            logger.debug(f"【事件转换】步骤结束事件: {event.to_dict()}")
        elif event.event_type == EventType.INFO:
            payload = [{"state": "INFO", "display": event.message}]
            chat_event = ChatEvent(
                event_type=ChatEventType.MESSAGE_ANNOTATIONS_PART,
                payload=payload
            )
            logger.debug(f"【事件转换】信息事件: {payload}")
        elif event.event_type == EventType.ERROR:
            payload = [event.message]
            chat_event = ChatEvent(
                event_type=ChatEventType.ERROR_PART,
                payload=payload
            )
            logger.debug(f"【事件转换】错误事件: {payload}")
        elif event.event_type == EventType.TEXT:
            payload = [event.message]
            chat_event = ChatEvent(
                event_type=ChatEventType.TEXT_PART,
                payload=payload
            )
            logger.debug(f"【事件转换】文本事件: {payload}")
        else:
            # 默认转换为DATA_PART
            payload = [event.to_dict()]
            chat_event = ChatEvent(
                event_type=ChatEventType.DATA_PART,
                payload=payload
            )
            logger.debug(f"【事件转换】默认转换事件: {payload}")
        
        logger.info(f"【事件转换】事件转换完成: type={chat_event.event_type.name}, payload_type={type(chat_event.payload).__name__}")
        return chat_event 