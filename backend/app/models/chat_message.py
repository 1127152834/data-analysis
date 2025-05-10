from uuid import UUID
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime

from sqlmodel import (
    Field,
    Column,
    DateTime,
    Text,
    JSON,
    Relationship as SQLRelationship,
    Boolean,
    Index,
)

from .base import UpdatableBaseModel

"""
聊天消息模型模块

定义了聊天会话中的单条消息数据结构，包括消息内容、
元数据、引用源、图形数据和追踪信息等
"""

# 使用TYPE_CHECKING解决循环导入问题
if TYPE_CHECKING:
    from .chat import Chat
    from .auth import User


class ChatMessage(UpdatableBaseModel, table=True):
    """
    聊天消息模型

    表示聊天会话中的一条消息，可以是用户的问题或系统的回答。
    包含消息内容、元数据、知识源引用和追踪信息等完整数据。
    """

    id: Optional[int] = Field(default=None, primary_key=True)  # 消息ID，主键
    ordinal: int = Field(default=0)  # 消息在会话中的序号，用于排序
    role: str = Field(max_length=64)  # 消息角色，如"user"、"assistant"或"system"
    content: str = Field(sa_column=Column(Text))  # 消息内容文本
    error: Optional[str] = Field(sa_column=Column(Text))  # 处理消息时可能发生的错误信息

    # 消息引用的知识源数组，如检索到的文档片段、知识图谱节点等
    sources: List = Field(default=[], sa_column=Column(JSON))

    # 知识图谱数据，用于可视化展示相关的图谱信息
    graph_data: dict = Field(default={}, sa_column=Column(JSON))

    # 元数据，存储各种额外信息，如令牌计数、处理时间、模型参数等
    meta: dict = Field(default={}, sa_column=Column(JSON))

    # LangFuse追踪URL，用于查看详细的处理过程和性能指标
    trace_url: Optional[str] = Field(max_length=512)

    # 标记是否为最佳回答，用于在历史会话中突出显示高质量回答
    is_best_answer: bool = Field(
        default=False,
        sa_column=Column(Boolean, nullable=False, default=False, server_default="0"),
    )

    # 消息完成时间，特别是对于流式响应，标记生成完毕的时间点
    finished_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime))

    # 关联的聊天会话
    chat_id: UUID = Field(foreign_key="chats.id")  # 所属聊天会话ID
    chat: "Chat" = SQLRelationship(
        sa_relationship_kwargs={
            "lazy": "joined",
            "primaryjoin": "ChatMessage.chat_id == Chat.id",
        },
    )

    # 关联的用户信息
    user_id: UUID = Field(foreign_key="users.id", nullable=True)  # 发送消息的用户ID
    user: "User" = SQLRelationship(
        sa_relationship_kwargs={
            "lazy": "joined",
            "primaryjoin": "ChatMessage.user_id == User.id",
        },
    )

    # 回答后验证结果URL，指向验证回答准确性和质量的详细报告
    post_verification_result_url: Optional[str] = Field(
        max_length=512,
        nullable=True,
    )

    __tablename__ = "chat_messages"  # 表名
    __table_args__ = (
        Index("ix_chat_message_is_best_answer", "is_best_answer"),
    )  # 索引，优化对最佳回答的查询
