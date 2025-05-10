import enum
from typing import Optional, TYPE_CHECKING, Union
from datetime import datetime

from llama_index.core.schema import Document as LlamaDocument
from pydantic import ConfigDict
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlmodel import (
    Field,
    Column,
    Text,
    DateTime,
    JSON,
    String,
    Relationship as SQLRelationship,
)

from .base import UpdatableBaseModel
from app.types import MimeTypes

"""
文档模型模块

定义了系统中文档的数据结构，包括文档的基本信息、内容、元数据、
索引状态等。文档是知识库的基本单位，用于存储和管理待检索的内容。
"""

# 使用TYPE_CHECKING解决循环导入问题
if TYPE_CHECKING:
    from .data_source import DataSource
    from .knowledge_base import KnowledgeBase


class DocIndexTaskStatus(str, enum.Enum):
    """
    文档索引任务状态枚举

    定义了文档索引过程中可能的状态
    """

    NOT_STARTED = "not_started"  # 未开始索引
    PENDING = "pending"  # 等待索引
    RUNNING = "running"  # 索引进行中
    COMPLETED = "completed"  # 索引完成
    FAILED = "failed"  # 索引失败


class ContentFormat(str, enum.Enum):
    """
    内容格式枚举

    定义了文档内容的可能格式
    """

    TEXT = "text"  # 纯文本格式
    MARKDOWN = "markdown"  # Markdown格式


class Document(UpdatableBaseModel, table=True):
    """
    文档模型

    表示系统中的一个文档，包含文档的内容、元数据和索引状态等信息。
    文档是知识库中的基本单位，用于存储和检索信息。
    """

    # 避免"expected `enum` but got `str`"错误
    model_config = ConfigDict(use_enum_values=True)

    id: Optional[int] = Field(default=None, primary_key=True)  # 文档ID，主键
    hash: str = Field(max_length=32)  # 文档内容的哈希值，用于检测重复和变更
    name: str = Field(max_length=256)  # 文档名称
    content: str = Field(
        sa_column=Column(MEDIUMTEXT)
    )  # 文档内容，使用MEDIUMTEXT类型存储大文本
    mime_type: MimeTypes = Field(
        sa_column=Column(String(128), nullable=False)
    )  # 文档MIME类型，如text/plain、application/pdf等
    source_uri: str = Field(max_length=512)  # 文档来源URI，指示文档的原始位置
    meta: Union[dict, list] = Field(
        default={}, sa_column=Column(JSON)
    )  # 文档元数据，如作者、创建日期等

    # 文档在源系统中的最后修改时间
    last_modified_at: Optional[datetime] = Field(sa_column=Column(DateTime))

    # TODO: 重命名为vector_index_status, vector_index_result
    index_status: DocIndexTaskStatus = (
        DocIndexTaskStatus.NOT_STARTED
    )  # 文档向量索引状态
    index_result: str = Field(
        sa_column=Column(Text, nullable=True)
    )  # 索引结果或错误信息

    # TODO: 添加kg_index_status, kg_index_result列，统一索引状态

    # 关联的数据源
    data_source_id: int = Field(
        foreign_key="data_sources.id", nullable=True
    )  # 数据源ID
    data_source: "DataSource" = SQLRelationship(
        sa_relationship_kwargs={
            "lazy": "joined",
            "primaryjoin": "Document.data_source_id == DataSource.id",
        },
    )

    # 关联的知识库
    knowledge_base_id: int = Field(
        foreign_key="knowledge_bases.id", nullable=True
    )  # 知识库ID
    knowledge_base: "KnowledgeBase" = SQLRelationship(
        sa_relationship_kwargs={
            "lazy": "joined",
            "primaryjoin": "Document.knowledge_base_id == KnowledgeBase.id",
        },
    )

    __tablename__ = "documents"  # 表名

    def to_llama_document(self) -> LlamaDocument:
        """
        转换为LlamaIndex文档

        将当前文档模型转换为LlamaIndex库使用的Document对象，
        便于使用LlamaIndex的检索和处理功能

        返回:
            LlamaDocument: LlamaIndex文档对象
        """
        return LlamaDocument(
            id_=str(self.id),
            text=self.content,
            metadata=self.meta,
        )
