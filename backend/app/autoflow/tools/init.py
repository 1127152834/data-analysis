"""
工具注册与初始化模块
"""

import logging
from typing import Optional, List

from .registry import ToolRegistry
from .knowledge_graph_tool import KnowledgeGraphTool
from .knowledge_retrieval_tool import KnowledgeRetrievalTool
from .database_query_tool import DatabaseQueryTool
from .further_questions_tool import FurtherQuestionsTool

logger = logging.getLogger("autoflow.tools.init")

def register_tools(db_session=None, engine_config=None) -> ToolRegistry:
    """
    注册所有工具到工具注册表
    
    Args:
        db_session: 数据库会话
        engine_config: 引擎配置
        
    Returns:
        ToolRegistry: 包含注册的所有工具的注册表
    """
    # 获取工具注册表实例
    registry = ToolRegistry()
    
    # 创建并注册各种工具
    tools = [
        KnowledgeGraphTool(db_session=db_session, engine_config=engine_config),
        KnowledgeRetrievalTool(db_session=db_session, engine_config=engine_config),
        DatabaseQueryTool(db_session=db_session, engine_config=engine_config),
        FurtherQuestionsTool(db_session=db_session, engine_config=engine_config)
    ]
    
    # 注册所有工具
    for tool in tools:
        registry.register_tool(tool)
    
    logger.info(f"已注册 {len(tools)} 个工具: {', '.join(registry.list_tools())}")
    return registry

# 添加register_default_tools作为register_tools的别名
register_default_tools = register_tools

def get_tool_registry() -> ToolRegistry:
    """
    获取工具注册表实例
    
    Returns:
        ToolRegistry: 工具注册表实例
    """
    return ToolRegistry() 