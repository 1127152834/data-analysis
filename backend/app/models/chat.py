import enum
from uuid import UUID
from typing import Optional, Dict, TYPE_CHECKING, Union
from pydantic import BaseModel
from datetime import datetime

from sqlmodel import (
    Field,
    Column,
    DateTime,
    JSON,
    Relationship as SQLRelationship,
)

from .base import IntEnumType, UUIDBaseModel, UpdatableBaseModel

"""
聊天模型模块

定义了聊天会话的数据模型，包括聊天的基本信息、可见性设置、
过滤条件和统计数据结构等
"""

# 使用TYPE_CHECKING解决循环导入问题
if TYPE_CHECKING:
    from .chat_engine import ChatEngine
    from .auth import User


class ChatVisibility(int, enum.Enum):
    """
    聊天可见性枚举

    定义聊天会话的可见性级别
    """

    PRIVATE = 0  # 私有，仅创建者可见
    PUBLIC = 1  # 公开，所有用户可见


class Chat(UUIDBaseModel, UpdatableBaseModel, table=True):
    """
    聊天会话模型

    定义了用户与系统之间的一个完整对话会话，
    包含会话的基本信息、使用的聊天引擎及其配置等
    """

    title: str = Field(max_length=256)  # 聊天标题

    # 关联的聊天引擎
    engine_id: int = Field(
        foreign_key="chat_engines.id", nullable=True
    )  # 使用的聊天引擎ID
    engine: "ChatEngine" = SQLRelationship(
        sa_relationship_kwargs={
            "lazy": "joined",
            "primaryjoin": "Chat.engine_id == ChatEngine.id",
        },
    )

    # 聊天引擎特定配置，可覆盖引擎默认设置
    # FIXME: why fastapi_pagination return string(json) instead of dict?
    engine_options: Union[Dict, str] = Field(default={}, sa_column=Column(JSON))

    # 软删除字段
    deleted_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime))

    # 关联用户信息
    user_id: UUID = Field(foreign_key="users.id", nullable=True)  # 创建聊天的用户ID
    user: "User" = SQLRelationship(
        sa_relationship_kwargs={
            "lazy": "joined",
            "primaryjoin": "Chat.user_id == User.id",
        },
    )

    # 客户端信息
    browser_id: str = Field(
        max_length=50, nullable=True
    )  # 浏览器唯一标识，用于跟踪匿名用户
    origin: str = Field(
        max_length=256, default=None, nullable=True
    )  # 聊天来源，如网站URL或应用ID

    # 可见性设置
    visibility: ChatVisibility = Field(
        sa_column=Column(
            IntEnumType(ChatVisibility),
            nullable=False,
            default=ChatVisibility.PRIVATE,  # 默认为私有
        )
    )

    __tablename__ = "chats"  # 表名


class ChatUpdate(BaseModel):
    """
    聊天更新模型

    用于部分更新聊天会话信息的Pydantic模型
    """

    title: Optional[str] = None  # 更新聊天标题
    visibility: Optional[ChatVisibility] = None  # 更新可见性设置


class ChatFilters(BaseModel):
    """
    聊天过滤条件模型

    用于筛选和查询聊天会话的条件，常用于管理界面或统计分析
    """

    created_at_start: Optional[datetime] = None  # 创建时间范围开始
    created_at_end: Optional[datetime] = None  # 创建时间范围结束
    updated_at_start: Optional[datetime] = None  # 更新时间范围开始
    updated_at_end: Optional[datetime] = None  # 更新时间范围结束
    chat_origin: Optional[str] = None  # 按来源筛选
    # user_id: Optional[UUID] = None             # 按用户筛选，当前未使用
    engine_id: Optional[int] = None  # 按聊天引擎筛选


class ChatOrigin(BaseModel):
    """
    聊天来源统计模型

    用于统计不同来源的聊天数量
    """

    origin: str  # 来源标识
    chats: int  # 该来源的聊天数量
