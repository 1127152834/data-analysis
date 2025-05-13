from uuid import UUID
from typing import Optional, Dict, List, Any
from datetime import datetime

from sqlmodel import (
    Field,
    Column,
    DateTime,
    Text,
    JSON,
    Relationship as SQLRelationship,
    Index,
)

from app.models.chat_message import ChatMessage
from app.models.database_connection import DatabaseType
from app.models.base import UpdatableBaseModel

"""
数据库查询历史模型模块

定义了存储数据库查询历史的数据模型，包括查询、结果、执行时间等信息
"""


class DatabaseQueryHistory(UpdatableBaseModel, table=True):
    """
    数据库查询历史模型
    
    存储用户在对话中执行的数据库查询历史信息，包括查询语句、结果和性能指标等
    """
    id: Optional[int] = Field(default=None, primary_key=True)  # 主键ID
    
    # 关联信息
    chat_id: UUID = Field(foreign_key="chats.id", index=True)  # 所属聊天会话ID
    chat_message_id: Optional[int] = Field(foreign_key="chat_messages.id", nullable=True, index=True)  # 关联的消息ID
    user_id: Optional[UUID] = Field(foreign_key="users.id", nullable=True, index=True)  # 执行查询的用户ID
    
    # 数据库连接信息
    connection_id: int = Field(foreign_key="database_connections.id", index=True)  # 数据库连接ID
    connection_name: str = Field(max_length=256)  # 数据库连接名称
    database_type: DatabaseType  # 数据库类型
    
    # 查询信息
    question: str = Field(sa_column=Column(Text))  # 原始自然语言问题
    query: str = Field(sa_column=Column(Text))  # 执行的SQL查询
    is_successful: bool = Field(default=True)  # 查询是否成功
    error_message: Optional[str] = Field(default=None, sa_column=Column(Text))  # 错误信息
    
    # 结果信息
    result_summary: Dict = Field(default={}, sa_column=Column(JSON))  # 结果摘要，包括行数、列信息等
    result_sample: List = Field(default=[], sa_column=Column(JSON))  # 结果样本（最多5行）
    execution_time_ms: int = Field(default=0)  # 执行时间，毫秒
    rows_returned: int = Field(default=0)  # 返回行数
    
    # 路由信息
    routing_score: Optional[float] = Field(default=None)  # 路由得分
    routing_context: Dict = Field(default={}, sa_column=Column(JSON))  # 路由上下文
    
    # 用户反馈
    user_feedback: Optional[int] = Field(default=None)  # 用户反馈评分(1-5)
    user_feedback_comments: Optional[str] = Field(default=None, sa_column=Column(Text))  # 用户反馈评论
    
    # 元数据和执行时间信息
    meta: Dict = Field(default={}, sa_column=Column(JSON))  # 元数据，存储其他相关信息
    executed_at: datetime = Field(sa_column=Column(DateTime))  # 执行时间
    
    # 聊天消息关联
    chat_message: "ChatMessage" = SQLRelationship(  # noqa:F821
        sa_relationship_kwargs={
            "lazy": "joined",
            "primaryjoin": "DatabaseQueryHistory.chat_message_id == ChatMessage.id",
        },
    )
    
    __tablename__ = "database_query_history"  # 表名
    __table_args__ = (
        Index("ix_db_query_history_chat_id_executed_at", "chat_id", "executed_at"),
        Index("ix_db_query_history_connection_id_executed_at", "connection_id", "executed_at"),
    )  # 索引，优化查询性能 