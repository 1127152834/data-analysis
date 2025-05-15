import json
from dataclasses import dataclass
import logging

from pydantic import BaseModel

from app.models import ChatMessage, Chat
from app.rag.types import ChatEventType, ChatMessageSate
logger = logging.getLogger(__name__)

class ChatStreamPayload:
    def dump(self):
        pass


@dataclass
class ChatStreamDataPayload(ChatStreamPayload):
    chat: Chat
    user_message: ChatMessage
    assistant_message: ChatMessage

    def dump(self):
        result = [
            {
                "chat": self.chat.model_dump(mode="json"),
                "user_message": self.user_message.model_dump(mode="json"),
                "assistant_message": self.assistant_message.model_dump(mode="json"),
            }
        ]
        logger.info(f"ChatStreamDataPayload.dump() -> {result}")
        return result


@dataclass
class ChatStreamMessagePayload(ChatStreamPayload):
    state: ChatMessageSate = ChatMessageSate.TRACE
    display: str = ""
    context: dict | list | str | BaseModel | None = None
    message: str = ""

    def dump(self):
        if isinstance(self.context, list):
            context = [c.model_dump() for c in self.context]
        elif isinstance(self.context, BaseModel):
            context = self.context.model_dump()
        else:
            context = self.context

        result = [
            {
                "state": self.state.name,
                "display": self.display,
                "context": context,
                "message": self.message,
            }
        ]
        logger.info(f"ChatStreamMessagePayload.dump() -> {result}")
        return result


@dataclass
class ChatEvent:
    event_type: ChatEventType
    payload: str | ChatStreamPayload | None = None

    def encode(self, charset) -> bytes:
        body = self.payload
        event_id = self.event_type.value
        
        logger.info(f"ChatEvent.encode() - 事件类型: {event_id}, payload类型: {type(body)}")

        # 处理ChatStreamPayload对象
        if isinstance(body, ChatStreamPayload):
            body = body.dump()
            logger.info(f"ChatStreamPayload.dump()结果类型: {type(body)}, 内容: {body}")

        # 编码为JSON
        encoded_body = json.dumps(body, separators=(",", ":"))
        
        # 使用原始格式
        result = f"{event_id}:{encoded_body}\n"
        
        logger.info(f"最终编码结果: {result}")
        return result.encode(charset)
