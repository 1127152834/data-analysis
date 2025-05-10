from typing import Optional
from uuid import UUID
from datetime import datetime

from pydantic import EmailStr
from sqlmodel import (
    Field,
    SQLModel,
    DateTime,
    func,
    Relationship as SQLRelationship,
)

from app.models.base import UpdatableBaseModel, UUIDBaseModel

"""
用户认证模型模块

定义了系统中用户认证相关的数据模型，包括用户账户信息和用户会话，
用于实现用户注册、登录和权限管理等功能。
"""


class User(UUIDBaseModel, UpdatableBaseModel, table=True):
    """
    用户模型

    表示系统中的一个用户账户，包含用户的基本信息、认证信息和权限信息。
    继承UUIDBaseModel使用UUID作为主键，继承UpdatableBaseModel自动跟踪创建和更新时间。
    """

    email: EmailStr = Field(
        index=True, unique=True, nullable=False
    )  # 用户邮箱，作为唯一标识符
    hashed_password: str  # 哈希后的密码，存储密码的哈希值而非明文
    is_active: bool = Field(True, nullable=False)  # 账户是否激活，默认为激活状态
    is_superuser: bool = Field(
        False, nullable=False
    )  # 是否为超级用户，具有系统管理权限
    is_verified: bool = Field(False, nullable=False)  # 是否已验证，如邮箱验证等

    __tablename__ = "users"  # 表名


class UserSession(SQLModel, table=True):
    """
    用户会话模型

    表示用户的一个登录会话，用于跟踪用户的登录状态。
    当用户登录时创建会话，登出时删除会话。
    """

    token: str = Field(max_length=43, primary_key=True)  # 会话令牌，作为主键
    created_at: Optional[datetime] = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={
            "server_default": func.now()
        },  # 会话创建时间，自动设置为当前时间
    )
    user_id: UUID = Field(foreign_key="users.id", nullable=False)  # 关联的用户ID
    user: User = SQLRelationship(
        sa_relationship_kwargs={
            "lazy": "joined",
            "primaryjoin": "UserSession.user_id == User.id",
        },
    )

    __tablename__ = "user_sessions"  # 表名
