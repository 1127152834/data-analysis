import enum
from datetime import datetime
from typing import Dict, Optional, Union
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import JSON, func
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlmodel import (
    Field,
    Column,
    DateTime,
    Relationship as SQLRelationship,
    SQLModel,
)
from llama_index.core.node_parser.text.sentence import (
    DEFAULT_PARAGRAPH_SEP,
    SENTENCE_CHUNK_OVERLAP,
)
from app.rag.node_parser.file.markdown import (
    DEFAULT_CHUNK_HEADER_LEVEL,
    DEFAULT_CHUNK_SIZE,
)
from app.api.admin_routes.models import KnowledgeBaseDescriptor
from app.exceptions import KBDataSourceNotFound
from app.models.auth import User
from app.models.data_source import DataSource
from app.models.embed_model import EmbeddingModel
from app.models.llm import LLM
from app.types import MimeTypes

"""
知识库模型模块

定义了知识库及其相关组件的数据模型，包括知识库本身、索引方法、
文本分块配置和知识库与数据源的关联关系等
"""

# 为了与旧代码兼容，定义一个虚拟知识库ID
PHONY_KNOWLEDGE_BASE_ID = 0


class IndexMethod(str, enum.Enum):
    """
    索引方法枚举

    定义了知识库支持的索引方法类型
    """

    KNOWLEDGE_GRAPH = "knowledge_graph"  # 知识图谱索引
    VECTOR = "vector"  # 向量索引


class KnowledgeBaseDataSource(SQLModel, table=True):
    """
    知识库与数据源的关联模型

    定义了知识库和数据源之间的多对多关系
    """

    knowledge_base_id: int = Field(
        primary_key=True, foreign_key="knowledge_bases.id"
    )  # 知识库ID
    data_source_id: int = Field(
        primary_key=True, foreign_key="data_sources.id"
    )  # 数据源ID

    __tablename__ = "knowledge_base_datasources"  # 表名


# 分块设置相关模型


class ChunkSplitter(str, enum.Enum):
    """
    文本分块器类型枚举

    定义了系统支持的不同文本分块方法
    """

    SENTENCE_SPLITTER = "SentenceSplitter"  # 基于句子的分块器
    MARKDOWN_NODE_PARSER = "MarkdownNodeParser"  # Markdown专用分块器


class SentenceSplitterOptions(BaseModel):
    """
    句子分块器选项

    配置基于句子的文本分块器的参数
    """

    chunk_size: int = Field(
        description="每个块的令牌大小",
        default=1000,
        gt=0,
    )
    chunk_overlap: int = Field(
        description="每个块之间的重叠大小",
        default=SENTENCE_CHUNK_OVERLAP,
        gt=0,
    )
    paragraph_separator: str = Field(
        description="用于分割文本的段落分隔符",
        default=DEFAULT_PARAGRAPH_SEP,
    )


class MarkdownNodeParserOptions(BaseModel):
    """
    Markdown分块器选项

    配置用于Markdown文档的特殊分块器参数
    """

    chunk_size: int = Field(
        description="每个块的令牌大小",
        default=1000,
        gt=0,
    )
    chunk_header_level: int = Field(
        description="按哪一级标题进行分割",
        default=DEFAULT_CHUNK_HEADER_LEVEL,
        ge=1,
        le=6,
    )


class ChunkSplitterConfig(BaseModel):
    """
    分块器配置

    定义使用哪种分块器以及其相关选项
    """

    splitter: ChunkSplitter = Field(
        default=ChunkSplitter.SENTENCE_SPLITTER
    )  # 分块器类型
    splitter_options: Union[SentenceSplitterOptions, MarkdownNodeParserOptions] = (
        Field()  # 分块器选项
    )


class ChunkingMode(str, enum.Enum):
    """
    分块模式枚举

    定义了系统支持的分块配置模式
    """

    GENERAL = "general"  # 通用分块模式，使用统一配置
    ADVANCED = "advanced"  # 高级分块模式，可按文件类型定制配置


class BaseChunkingConfig(BaseModel):
    """
    基础分块配置

    所有分块配置的基类
    """

    mode: ChunkingMode = Field(default=ChunkingMode.GENERAL)  # 分块模式


class GeneralChunkingConfig(BaseChunkingConfig):
    """
    通用分块配置

    使用统一参数对所有文档进行分块的配置
    """

    mode: ChunkingMode = Field(default=ChunkingMode.GENERAL)
    chunk_size: int = Field(default=DEFAULT_CHUNK_SIZE, gt=0)  # 块大小
    chunk_overlap: int = Field(default=SENTENCE_CHUNK_OVERLAP, gt=0)  # 块重叠
    paragraph_separator: str = Field(default=DEFAULT_PARAGRAPH_SEP)  # 段落分隔符


class AdvancedChunkingConfig(BaseChunkingConfig):
    """
    高级分块配置

    允许按照不同文件类型使用不同分块策略的配置
    """

    mode: ChunkingMode = Field(default=ChunkingMode.ADVANCED)
    rules: Dict[MimeTypes, ChunkSplitterConfig] = Field(
        default_factory=list
    )  # 按MIME类型配置分块规则


# 分块配置联合类型，可以是通用配置或高级配置
ChunkingConfig = Union[GeneralChunkingConfig | AdvancedChunkingConfig]


# 知识库模型


class KnowledgeBase(SQLModel, table=True):
    """
    知识库模型

    定义了知识库的数据结构，包括基本信息、分块配置、索引方法、
    关联的数据源和模型以及元数据信息等
    """

    id: Optional[int] = Field(default=None, primary_key=True)  # 知识库ID
    name: str = Field(max_length=255, nullable=False)  # 知识库名称
    description: Optional[str] = Field(
        sa_column=Column(MEDIUMTEXT), default=None
    )  # 知识库描述

    # 分块配置，用于将文档分解为更小的块进行处理
    chunking_config: Dict = Field(
        sa_column=Column(JSON), default=GeneralChunkingConfig().model_dump()
    )

    # 数据源配置
    data_sources: list["DataSource"] = SQLRelationship(
        link_model=KnowledgeBaseDataSource  # 通过关联表连接数据源
    )

    # 索引配置
    index_methods: list[IndexMethod] = Field(
        default=[IndexMethod.VECTOR],
        sa_column=Column(JSON),  # 默认使用向量索引
    )
    llm_id: int = Field(foreign_key="llms.id", nullable=True)  # 关联的LLM模型ID
    llm: "LLM" = SQLRelationship(
        sa_relationship_kwargs={
            "lazy": "joined",
            "foreign_keys": "KnowledgeBase.llm_id",
        },
    )
    embedding_model_id: int = Field(
        foreign_key="embedding_models.id", nullable=True
    )  # 关联的嵌入模型ID
    embedding_model: "EmbeddingModel" = SQLRelationship(
        sa_relationship_kwargs={
            "lazy": "joined",
            "foreign_keys": "KnowledgeBase.embedding_model_id",
        },
    )
    documents_total: int = Field(default=0)  # 包含的文档总数
    data_sources_total: int = Field(default=0)  # 包含的数据源总数

    # TODO: 支持知识库级别的权限控制

    # 元数据信息
    created_by: UUID = Field(foreign_key="users.id", nullable=True)  # 创建者ID
    creator: "User" = SQLRelationship(
        sa_relationship_kwargs={
            "lazy": "joined",
            "primaryjoin": "KnowledgeBase.created_by == User.id",
        },
    )
    created_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(), server_default=func.now()),  # 创建时间
    )
    updated_by: UUID = Field(foreign_key="users.id", nullable=True)  # 更新者ID
    updated_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(
            DateTime(), server_default=func.now(), onupdate=func.now()
        ),  # 更新时间
    )
    deleted_by: UUID = Field(foreign_key="users.id", nullable=True)  # 删除者ID
    deleted_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime())
    )  # 删除时间

    __tablename__ = "knowledge_bases"  # 表名

    def __hash__(self):
        """
        哈希方法

        使知识库对象可哈希，便于在集合中使用
        """
        return hash(self.id)

    def get_data_source_by_id(self, data_source_id: int) -> Optional[DataSource]:
        """
        根据ID获取数据源

        参数:
            data_source_id: 数据源ID

        返回:
            找到的数据源对象，如果不存在则返回None
        """
        return next(
            (
                ds
                for ds in self.data_sources
                if ds.id == data_source_id and not ds.deleted_at
            ),
            None,
        )

    def must_get_data_source_by_id(self, data_source_id: int) -> DataSource:
        """
        必须根据ID获取数据源

        参数:
            data_source_id: 数据源ID

        返回:
            找到的数据源对象

        异常:
            KBDataSourceNotFound: 如果数据源不存在
        """
        data_source = self.get_data_source_by_id(data_source_id)
        if data_source is None:
            raise KBDataSourceNotFound(self.id, data_source_id)
        return data_source

    def to_descriptor(self) -> KnowledgeBaseDescriptor:
        """
        转换为知识库描述符

        创建一个简化的知识库描述对象，用于API响应

        返回:
            KnowledgeBaseDescriptor: 知识库描述符对象
        """
        return KnowledgeBaseDescriptor(
            id=self.id,
            name=self.name,
        )
