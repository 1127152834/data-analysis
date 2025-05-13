"""
API路由导入模块

该文件负责导入和重新导出所有的API路由模块供app.api.main使用
"""

from app.api.routes import (
    index,
    chat,
    user,
    api_key,
    feedback,
    document,
    chunks,
    database_query,
)
