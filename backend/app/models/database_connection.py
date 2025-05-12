from enum import Enum
from uuid import UUID
from typing import Dict, Optional
from datetime import datetime

from sqlmodel import (
    Column,
    Field,
    JSON,
    DateTime,
    Relationship as SQLRelationship,
)

from app.models.auth import User
from app.models.base import UpdatableBaseModel

"""
数据库连接模型模块

定义了系统中数据库连接的数据模型，包括数据库类型枚举、
连接状态枚举以及数据库连接主模型
"""


class DatabaseType(str, Enum):
    """
    数据库类型枚举
    
    定义系统支持的所有数据库类型
    """
    MYSQL = "mysql"
    POSTGRESQL = "postgresql"
    MONGODB = "mongodb"
    SQLSERVER = "sql_server"
    ORACLE = "oracle"


class ConnectionStatus(str, Enum):
    """
    连接状态枚举
    
    定义数据库连接的可能状态
    """
    CONNECTED = "connected"  # 已连接
    DISCONNECTED = "disconnected"  # 已断开
    ERROR = "error"  # 连接错误


class DatabaseConnection(UpdatableBaseModel, table=True):
    """
    数据库连接模型
    
    存储数据库连接的所有相关信息，包括连接配置、
    状态信息和元数据缓存
    """
    id: Optional[int] = Field(default=None, primary_key=True)  # 主键ID
    name: str = Field(max_length=256)  # 连接名称
    description: str = Field(max_length=512)  # 连接描述
    database_type: DatabaseType  # 数据库类型
    config: Dict = Field(default={}, sa_column=Column(JSON))  # 连接配置（包含加密的敏感信息）
    # 关联用户信息
    user_id: UUID = Field(foreign_key="users.id", nullable=True)  # 创建聊天的用户ID
    user: "User" = SQLRelationship(
        sa_relationship_kwargs={
            "lazy": "joined",
            "primaryjoin": "DatabaseConnection.user_id == User.id",
        },
    )
    read_only: bool = Field(default=True)  # 是否只读模式
    connection_status: ConnectionStatus = Field(default=ConnectionStatus.DISCONNECTED)  # 连接状态
    last_connected_at: Optional[datetime] = Field(default=None)  # 最后连接时间
    metadata_cache: Dict = Field(default={}, sa_column=Column(JSON))  # 元数据缓存
    metadata_updated_at: Optional[datetime] = Field(default=None)  # 元数据更新时间
    deleted_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime),
    )  # 删除时间（用于软删除）

    __tablename__ = "database_connections"  # 表名 