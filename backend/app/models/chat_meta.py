from uuid import UUID
from typing import Optional
from datetime import datetime

from sqlmodel import (
    Field,
    Column,
    DateTime,
    Text,
    Index,
)

from app.models.base import UpdatableBaseModel

"""
聊天元数据模型模块

定义了存储与聊天相关的元数据信息的数据模型，用于支持对话状态管理、
数据库上下文和权限缓存等功能
"""


class ChatMeta(UpdatableBaseModel, table=True):
    """
    聊天元数据模型
    
    存储与聊天会话相关的键值对形式的元数据，支持对话状态管理
    """
    id: Optional[int] = Field(default=None, primary_key=True)  # 主键ID
    
    # 关联信息
    chat_id: UUID = Field(foreign_key="chats.id", index=True)  # 所属聊天会话ID
    
    # 元数据键值
    key: str = Field(max_length=256, index=True)  # 元数据键名
    value: str = Field(sa_column=Column(Text))  # 元数据值，存储为JSON字符串
    
    # 时间相关字段
    expires_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime)
    )  # 过期时间，如果设置，表示该元数据有效期
    
    __tablename__ = "chat_meta"  # 表名
    __table_args__ = (
        Index("ix_chat_meta_chat_id_key", "chat_id", "key", unique=True),  # 复合唯一索引，确保每个聊天的每个键只有一个值
    ) 