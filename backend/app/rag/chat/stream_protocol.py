import json
import logging
from dataclasses import dataclass

from pydantic import BaseModel

from app.models import ChatMessage, Chat
from app.rag.types import ChatEventType, ChatMessageSate

# 添加日志记录器
logger = logging.getLogger("stream_protocol")

class ChatStreamPayload:
    def dump(self):
        pass


@dataclass
class ChatStreamDataPayload(ChatStreamPayload):
    chat: Chat
    user_message: ChatMessage
    assistant_message: ChatMessage

    def dump(self):
        logger.debug(f"【ChatStreamDataPayload.dump】序列化数据事件: chat_id={getattr(self.chat, 'id', 'unknown')}, user_msg_id={getattr(self.user_message, 'id', 'unknown')}")
        dump_result = [
            {
                "chat": self.chat.model_dump(mode="json"),
                "user_message": self.user_message.model_dump(mode="json"),
                "assistant_message": self.assistant_message.model_dump(mode="json"),
            }
        ]
        logger.debug(f"【ChatStreamDataPayload.dump】序列化结果: type={type(dump_result).__name__}, is_list={isinstance(dump_result, list)}")
        return dump_result


@dataclass
class ChatStreamMessagePayload(ChatStreamPayload):
    state: ChatMessageSate = ChatMessageSate.TRACE
    display: str = ""
    context: dict | list | str | BaseModel | None = None
    message: str = ""

    def dump(self):
        logger.debug(f"【ChatStreamMessagePayload.dump】序列化消息事件: state={self.state.name}, display={self.display}")
        if isinstance(self.context, list):
            context = [c.model_dump() for c in self.context]
        elif isinstance(self.context, BaseModel):
            context = self.context.model_dump()
        else:
            context = self.context

        dump_result = [
            {
                "state": self.state.name,
                "display": self.display,
                "context": context,
                "message": self.message,
            }
        ]
        logger.debug(f"【ChatStreamMessagePayload.dump】序列化结果: type={type(dump_result).__name__}, is_list={isinstance(dump_result, list)}")
        return dump_result


@dataclass
class ChatEvent:
    event_type: ChatEventType
    payload: str | ChatStreamPayload | None = None

    def encode(self, charset) -> bytes:
        logger.info(f"【ChatEvent.encode】开始编码事件: type={self.event_type.name}, payload_type={type(self.payload).__name__}")
        body = self.payload

        # 如果是ChatStreamPayload类型，使用其dump方法获取数组格式
        if isinstance(body, ChatStreamPayload):
            logger.debug("【ChatEvent.encode】调用payload.dump()方法")
            body = body.dump()
            logger.info(f"【ChatEvent.encode】dump后的结果: type={type(body).__name__}, is_list={isinstance(body, list)}")
        # 如果已经是列表，直接使用
        elif isinstance(body, list):
            logger.debug("【ChatEvent.encode】payload已经是列表格式")
        # 其他情况，将其包装成列表
        else:
            logger.warning(f"【ChatEvent.encode】payload类型为: {type(body).__name__}，将其转换为列表")
            # 处理None、字符串和其他类型
            if body is None:
                logger.info("【ChatEvent.encode】payload为None，使用空列表")
                body = []
            elif isinstance(body, str):
                logger.info("【ChatEvent.encode】payload为字符串，包装为列表")
                body = [body]
            elif isinstance(body, dict):
                logger.info("【ChatEvent.encode】payload为字典，包装为列表")
                body = [body]
            else:
                # 尝试转换为JSON，如果失败则使用空列表
                try:
                    logger.info("【ChatEvent.encode】payload为其他类型，尝试转换后包装为列表")
                    body = [body]
                except Exception as e:
                    logger.error(f"【ChatEvent.encode】转换payload失败: {e}，使用空列表")
                    body = []

        # 确保body是列表
        if not isinstance(body, list):
            logger.warning("【ChatEvent.encode】转换后payload仍不是列表，强制转为空列表")
            body = []

        try:
            body_str = json.dumps(body, separators=(",", ":"))
            logger.debug(f"【ChatEvent.encode】JSON序列化成功: body_str={body_str[:100] if body_str else None}")
        except Exception as e:
            logger.error(f"【ChatEvent.encode】JSON序列化失败: {str(e)}", exc_info=True)
            # 失败时使用空列表作为备选
            body_str = "[]"

        event_str = f"{self.event_type.value}:{body_str}\n"
        logger.info(f"【ChatEvent.encode】编码完成: event_str={event_str[:100]}")
        return event_str.encode(charset)
