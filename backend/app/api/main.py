from fastapi import APIRouter
from app.api.routes import (
    index,
    chat,
    user,
    api_key,
    feedback,
    document,
    chunks,
)
from app.api.admin_routes.knowledge_base.routes import (
    router as admin_knowledge_base_router,
)
from app.api.admin_routes.knowledge_base.graph.routes import (
    router as admin_kb_graph_router,
)
from app.api.admin_routes.knowledge_base.graph.knowledge.routes import (
    router as admin_kb_graph_knowledge_router,
)
from app.api.admin_routes.knowledge_base.data_source.routes import (
    router as admin_kb_data_source_router,
)
from app.api.admin_routes.knowledge_base.document.routes import (
    router as admin_kb_document_router,
)
from app.api.admin_routes.knowledge_base.chunk.routes import (
    router as admin_kb_chunk_router,
)
from app.api.admin_routes.document.routes import router as admin_document_router
from app.api.admin_routes.llm.routes import router as admin_llm_router
from app.api.admin_routes.embedding_model.routes import (
    router as admin_embedding_model_router,
)
from app.api.admin_routes.reranker_model.routes import (
    router as admin_reranker_model_router,
)
from app.api.admin_routes.chat.routes import router as admin_user_router
from app.api.admin_routes import (
    chat_engine as admin_chat_engine,
    feedback as admin_feedback,
    legacy_retrieve as admin_legacy_retrieve,
    site_setting as admin_site_settings,
    upload as admin_upload,
    stats as admin_stats,
    semantic_cache as admin_semantic_cache,
    langfuse as admin_langfuse,
    user as admin_user,
)
from app.api.admin_routes.debug.routes import router as admin_debug_router
from app.api.admin_routes.evaluation import (
    evaluation_task as admin_evaluation_task,
    evaluation_dataset as admin_evaluation_dataset,
)
from app.api.routes.retrieve import (
    routes as retrieve_routes,
)

from app.auth.users import auth_backend, fastapi_users

"""
API路由管理模块

本模块负责组织和注册所有API路由，包括：
1. 用户端API路由：供普通用户使用的公开接口
2. 管理端API路由：供管理员使用的后台管理接口
3. 认证相关路由：处理用户登录、注册和权限验证

路由按功能领域进行分组和标记，便于API文档的自动生成和组织
"""

# 创建主路由器
api_router = APIRouter()

# =============================================================
# 用户端API路由
# =============================================================
# 基础功能路由
api_router.include_router(index.router, tags=["index"])  # 首页和基础功能
api_router.include_router(chat.router, tags=["chat"])  # 聊天功能
api_router.include_router(feedback.router, tags=["chat"])  # 聊天反馈
api_router.include_router(user.router, tags=["user"])  # 用户信息
api_router.include_router(api_key.router, tags=["auth"])  # API密钥管理
api_router.include_router(document.router, tags=["documents"])  # 文档管理
api_router.include_router(retrieve_routes.router, tags=["retrieve"])  # 检索功能
api_router.include_router(chunks.router, tags=["chunks"])  # 文本块功能

# =============================================================
# 管理端API路由
# =============================================================
# 用户和聊天管理
api_router.include_router(admin_user_router)  # 用户管理
api_router.include_router(
    admin_chat_engine.router, tags=["admin/chat-engines"]
)  # 聊天引擎管理

# 文档和反馈管理
api_router.include_router(admin_document_router, tags=["admin/documents"])  # 文档管理
api_router.include_router(admin_feedback.router)  # 反馈管理

# 系统设置和上传管理
api_router.include_router(
    admin_site_settings.router, tags=["admin/site_settings"]
)  # 站点设置
api_router.include_router(admin_upload.router, tags=["admin/upload"])  # 文件上传

# 知识库管理相关路由
api_router.include_router(
    admin_knowledge_base_router, tags=["admin/knowledge_base"]
)  # 知识库管理
api_router.include_router(
    admin_kb_graph_router, tags=["admin/knowledge_base/graph"]
)  # 知识图谱
api_router.include_router(
    admin_kb_graph_knowledge_router,
    tags=["admin/knowledge_base/graph/knowledge"],  # 知识图谱知识点
)
api_router.include_router(
    admin_kb_data_source_router,
    tags=["admin/knowledge_base/data_source"],  # 知识库数据源
)
api_router.include_router(
    admin_kb_document_router,
    tags=["admin/knowledge_base/document"],  # 知识库文档
)
api_router.include_router(
    admin_kb_chunk_router, tags=["admin/knowledge_base/chunk"]
)  # 知识库文本块

# AI模型管理路由
api_router.include_router(admin_llm_router, tags=["admin/llm"])  # LLM模型管理
api_router.include_router(
    admin_embedding_model_router, tags=["admin/embedding_model"]
)  # 嵌入模型管理
api_router.include_router(
    admin_reranker_model_router, tags=["admin/reranker_model"]
)  # 重排序模型管理

# 监控和分析路由
api_router.include_router(
    admin_langfuse.router, tags=["admin/langfuse"]
)  # LangFuse追踪
api_router.include_router(
    admin_legacy_retrieve.router, tags=["admin/retrieve_old"]
)  # 旧版检索
api_router.include_router(admin_stats.router, tags=["admin/stats"])  # 统计数据
api_router.include_router(
    admin_semantic_cache.router, tags=["admin/semantic_cache"]
)  # 语义缓存

# 评估系统路由
api_router.include_router(
    admin_evaluation_task.router, tags=["admin/evaluation/task"]
)  # 评估任务
api_router.include_router(
    admin_evaluation_dataset.router,
    tags=["admin/evaluation/dataset"],  # 评估数据集
)
api_router.include_router(admin_user.router)  # 管理员用户路由

# Debug routes
api_router.include_router(admin_debug_router, tags=["admin/debug"])

# =============================================================
# 认证相关路由
# =============================================================
# 使用FastAPI Users提供的认证路由
api_router.include_router(
    fastapi_users.get_auth_router(auth_backend), prefix="/auth", tags=["auth"]
)
