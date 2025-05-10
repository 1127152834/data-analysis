# flake8: noqa
"""
模型模块 (Models)

本模块定义了应用的所有数据库模型和数据结构
这些模型由SQLModel构建，用于与数据库进行交互
"""

# 知识图谱相关模型
from .entity import (
    EntityType,
    EntityPublic,
    get_kb_entity_model,
)
from .relationship import RelationshipPublic, get_kb_relationship_model
from .chunk import KgIndexStatus, get_kb_chunk_model

# 反馈与评价相关模型
from .feedback import (
    Feedback,
    FeedbackType,
    AdminFeedbackPublic,
    FeedbackFilters,
    FeedbackOrigin,
)
from .evaluation_task import EvaluationTask, EvaluationTaskItem, EvaluationStatus
from .evaluation_dataset import EvaluationDataset, EvaluationDatasetItem

# 聊天与消息相关模型
from .chat_engine import ChatEngine, ChatEngineUpdate
from .chat import Chat, ChatUpdate, ChatVisibility, ChatFilters, ChatOrigin
from .chat_message import ChatMessage
from .recommend_question import RecommendQuestion
from .semantic_cache import SemanticCache

# 文档与知识库相关模型
from .document import Document, DocIndexTaskStatus
from .knowledge_base import KnowledgeBase, KnowledgeBaseDataSource
from .data_source import DataSource, DataSourceType
from .upload import Upload

# 用户与认证相关模型
from .auth import User, UserSession
from .api_key import ApiKey, PublicApiKey
from .staff_action_log import StaffActionLog

# 系统设置与配置相关模型
from .site_setting import SiteSetting

# AI模型相关模型
from .llm import LLM, AdminLLM, LLMUpdate
from .embed_model import EmbeddingModel
from .reranker_model import RerankerModel, AdminRerankerModel

# 更新前向引用以解决循环导入问题
Chat.update_forward_refs()
ChatEngine.update_forward_refs()
ChatMessage.update_forward_refs()
Document.update_forward_refs()
