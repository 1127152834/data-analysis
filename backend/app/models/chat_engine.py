from typing import Optional, Dict, TYPE_CHECKING
from pydantic import BaseModel
from datetime import datetime

from sqlmodel import (
    Field,
    Column,
    JSON,
    DateTime,
    Relationship as SQLRelationship,
)

from .base import UpdatableBaseModel

"""
聊天引擎模型模块

定义了聊天引擎的数据模型，聊天引擎负责协调大语言模型、
重排序模型和知识库之间的交互，为用户提供基于知识的对话能力
"""

# 使用TYPE_CHECKING解决循环导入问题
if TYPE_CHECKING:
    from .llm import LLM
    from .reranker_model import RerankerModel


class ChatEngine(UpdatableBaseModel, table=True):
    """
    聊天引擎模型

    聊天引擎是系统中处理对话的核心组件，它整合了大语言模型、
    重排序模型和各种配置选项，为用户提供对话服务
    """

    id: Optional[int] = Field(default=None, primary_key=True)  # 主键ID
    name: str = Field(max_length=256)  # 聊天引擎名称
    engine_options: Dict = Field(
        default={}, sa_column=Column(JSON)
    )  # 引擎配置选项，如温度、知识库ID等

    # 主要LLM，用于生成完整回复
    llm_id: Optional[int] = Field(
        foreign_key="llms.id", nullable=True
    )  # 关联的LLM模型ID
    llm: "LLM" = SQLRelationship(
        sa_relationship_kwargs={
            "foreign_keys": "ChatEngine.llm_id",
        },
    )

    # 快速LLM，用于生成更简短的回复或执行辅助任务
    fast_llm_id: Optional[int] = Field(
        foreign_key="llms.id", nullable=True
    )  # 关联的快速LLM模型ID
    fast_llm: "LLM" = SQLRelationship(
        sa_relationship_kwargs={
            "foreign_keys": "ChatEngine.fast_llm_id",
        },
    )

    # 重排序模型，用于对检索结果进行排序和过滤
    reranker_id: Optional[int] = Field(
        foreign_key="reranker_models.id", nullable=True
    )  # 关联的重排序模型ID
    reranker: "RerankerModel" = SQLRelationship(
        sa_relationship_kwargs={
            "foreign_keys": "ChatEngine.reranker_id",
        },
    )

    is_default: bool = Field(default=False)  # 是否为默认聊天引擎
    deleted_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime)
    )  # 删除时间，用于软删除

    __tablename__ = "chat_engines"  # 表名


class ChatEngineUpdate(BaseModel):
    """
    聊天引擎更新模型

    用于部分更新聊天引擎配置的Pydantic模型，
    所有字段都是可选的，只更新提供的字段
    """

    name: Optional[str] = None  # 更新引擎名称
    llm_id: Optional[int] = None  # 更新主LLM模型
    fast_llm_id: Optional[int] = None  # 更新快速LLM模型
    reranker_id: Optional[int] = None  # 更新重排序模型
    engine_options: Optional[dict] = None  # 更新引擎配置选项
    is_default: Optional[bool] = None  # 更新是否为默认引擎
