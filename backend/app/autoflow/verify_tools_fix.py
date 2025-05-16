"""
验证工具导入修复
"""

import logging
import sys

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 测试事件导入
def test_events_import():
    try:
        from app.autoflow.events.tool_events import (
            BaseEvent, ToolCallEvent, ToolResultEvent, StepEndEvent, InfoEvent, ErrorEvent, TextEvent
        )
        from app.autoflow.events.converter import EventConverter
        logger.info("✅ 事件模块导入成功")
        return True
    except ImportError as e:
        logger.error(f"❌ 事件模块导入失败: {str(e)}")
        return False

# 测试工具导入
def test_tools_import():
    try:
        from app.autoflow.tools.base import BaseTool, ToolParameters, ToolResult
        from app.autoflow.tools.registry import ToolRegistry
        from app.autoflow.tools.knowledge_graph_tool import KnowledgeGraphTool
        from app.autoflow.tools.knowledge_retrieval_tool import KnowledgeRetrievalTool
        from app.autoflow.tools.database_query_tool import DatabaseQueryTool
        from app.autoflow.tools.further_questions_tool import FurtherQuestionsTool
        from app.autoflow.tools.init import register_tools, get_tool_registry
        logger.info("✅ 工具模块导入成功")
        return True
    except ImportError as e:
        logger.error(f"❌ 工具模块导入失败: {str(e)}")
        return False

# 测试依赖模块导入
def test_dependencies_import():
    try:
        # 测试SQL执行器导入
        from app.rag.sql.sql_executor import SQLExecutor, SQLExecutionResult
        logger.info("✅ SQL执行器模块导入成功")
        
        # 测试后续问题生成器导入
        from app.rag.further_questions.generator import FurtherQuestionsGenerator
        from app.rag.further_questions.schema import FurtherQuestionsGeneratorConfig
        logger.info("✅ 后续问题生成器模块导入成功")
        
        # 测试混合检索器导入
        from app.rag.retrievers.hybrid_retriever import HybridRetriever
        from app.rag.retrievers.schema import RetrieverConfig, RetrievalResult, Context
        logger.info("✅ 混合检索器模块导入成功")
        
        # 测试类型导入
        from app.rag.types import SQLExecutionConfig, ChatEventType
        logger.info("✅ 类型模块导入成功")
        
        # 测试事件协议导入
        from app.rag.chat.stream_protocol import ChatEvent
        logger.info("✅ 事件协议模块导入成功")
        
        return True
    except ImportError as e:
        logger.error(f"❌ 依赖模块导入失败: {str(e)}")
        return False

# 测试BaseAgent导入
def test_agent_import():
    try:
        from app.autoflow.agents.base_agent import BaseAgent
        logger.info("✅ BaseAgent模块导入成功")
        return True
    except ImportError as e:
        logger.error(f"❌ BaseAgent模块导入失败: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("开始验证工具导入修复...")
    
    results = [
        test_events_import(),
        test_tools_import(),
        test_dependencies_import(),
        test_agent_import()
    ]
    
    if all(results):
        logger.info("🎉 所有模块验证成功!")
        sys.exit(0)
    else:
        logger.error("❌ 部分模块验证失败!")
        sys.exit(1) 