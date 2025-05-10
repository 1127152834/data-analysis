from typing import Optional, Any
from sqlmodel import Field, Column, JSON, String
from pydantic import BaseModel
from app.rag.llms.provider import LLMProvider
from .base import UpdatableBaseModel, AESEncryptedColumn

"""
大语言模型(LLM)模块

定义了系统中使用的大语言模型的数据结构，
包括模型基本信息、配置参数和安全凭证等
"""


class BaseLLM(UpdatableBaseModel):
    """
    大语言模型基础类

    定义了所有LLM模型共有的基本属性，如名称、提供商、模型标识符等
    作为具体LLM模型类的基类
    """

    name: str = Field(max_length=64)  # 模型名称，用于在系统中展示
    provider: LLMProvider = Field(
        sa_column=Column(String(32), nullable=False)
    )  # 模型提供商，如OpenAI、Azure等
    model: str = Field(max_length=256)  # 具体模型标识符，如gpt-4、claude-3等
    config: dict | list | None = Field(
        sa_column=Column(JSON), default={}
    )  # 模型配置，如温度、最大令牌等参数
    is_default: bool = Field(default=False)  # 是否为系统默认模型


class LLM(BaseLLM, table=True):
    """
    大语言模型数据库模型

    继承基础LLM类，添加主键和凭证信息，用于数据库存储
    """

    id: Optional[int] = Field(default=None, primary_key=True)  # 主键ID
    credentials: Any = Field(
        sa_column=Column(AESEncryptedColumn, nullable=True)
    )  # 加密存储的API密钥等凭证信息

    __tablename__ = "llms"  # 数据库表名


class AdminLLM(BaseLLM):
    """
    管理员视图LLM模型

    用于管理界面显示的LLM信息，不包含敏感的凭证数据
    """

    id: int  # 模型ID


class LLMUpdate(BaseModel):
    """
    LLM更新模型

    用于部分更新LLM配置的Pydantic模型，
    所有字段都是可选的，只更新提供的字段
    """

    name: Optional[str] = None  # 更新模型名称
    config: Optional[dict] = None  # 更新模型配置
    credentials: Optional[str | dict] = None  # 更新模型凭证
