"""
工具管理器模块

负责管理和注册Agent可用的工具，提供工具集成和动态加载功能
"""

import logging
from typing import Dict, List, Optional, Any, Type

from llama_index.core.tools.types import BaseTool
from sqlmodel import Session

from app.rag.chat.config import ChatEngineConfig, AgentOption
from app.rag.agent.tools.knowledge_retrieval_tool import KnowledgeRetrievalTool
from app.rag.agent.tools.knowledge_graph_tool import KnowledgeGraphQueryTool
from app.rag.agent.tools.response_generator_tool import ResponseGeneratorTool
from app.rag.agent.tools.deep_research_tool import DeepResearchTool
from app.rag.agent.tools.sql_query_adapter import SQLQueryToolAdapter

logger = logging.getLogger(__name__)

class ToolRegistry:
    """工具注册表，管理所有可用的工具类"""
    
    _registry: Dict[str, Type[BaseTool]] = {}
    
    @classmethod
    def register(cls, tool_name: str, tool_class: Type[BaseTool]) -> None:
        """
        注册工具类
        
        参数:
            tool_name: 工具名称
            tool_class: 工具类
        """
        cls._registry[tool_name] = tool_class
        logger.debug(f"已注册工具: {tool_name}")
    
    @classmethod
    def get_tool_class(cls, tool_name: str) -> Optional[Type[BaseTool]]:
        """
        获取工具类
        
        参数:
            tool_name: 工具名称
            
        返回:
            Optional[Type[BaseTool]]: 工具类，如果不存在则返回None
        """
        return cls._registry.get(tool_name)
    
    @classmethod
    def list_tools(cls) -> List[str]:
        """
        列出所有已注册的工具
        
        返回:
            List[str]: 工具名称列表
        """
        return list(cls._registry.keys())


class ToolManager:
    """
    工具管理器
    
    负责根据配置创建和管理Agent可用的工具
    """
    
    def __init__(self, db_session: Session, engine_config: ChatEngineConfig):
        """
        初始化工具管理器
        
        参数:
            db_session: 数据库会话
            engine_config: 聊天引擎配置
        """
        self.db_session = db_session
        self.engine_config = engine_config
        self.agent_config = engine_config.agent
        
        # 注册内置工具
        self._register_builtin_tools()
    
    def _register_builtin_tools(self) -> None:
        """注册内置工具"""
        # 注册知识检索工具
        ToolRegistry.register("knowledge_retrieval", KnowledgeRetrievalTool)
        
        # 注册知识图谱查询工具
        ToolRegistry.register("knowledge_graph_query", KnowledgeGraphQueryTool)
        
        # 注册响应生成工具
        ToolRegistry.register("response_generator", ResponseGeneratorTool)
        
        # 注册深度研究工具
        ToolRegistry.register("deep_research", DeepResearchTool)
        
        # 注册SQL查询工具适配器
        ToolRegistry.register("sql_query", SQLQueryToolAdapter)
    
    def get_enabled_tools(self) -> List[BaseTool]:
        """
        获取已启用的工具实例列表
        
        返回:
            List[BaseTool]: 工具实例列表
        """
        tools = []
        
        # 遍历配置中启用的工具
        for tool_name in self.agent_config.enabled_tools:
            # 获取工具类
            tool_class = ToolRegistry.get_tool_class(tool_name)
            if not tool_class:
                logger.warning(f"未找到工具: {tool_name}")
                continue
            
            # 创建工具实例
            try:
                # 创建工具实例
                # 特殊处理：知识图谱查询工具只在知识图谱功能启用时创建
                if tool_name == "knowledge_graph_query" and not self.engine_config.knowledge_graph.enabled:
                    continue
                    
                # 特殊处理：SQL查询工具只在数据库查询功能启用时创建
                if tool_name == "sql_query" and not self.engine_config.database.enabled:
                    continue
                    
                # 特殊处理：深度研究工具只在允许深度研究时创建
                if tool_name == "deep_research" and not self.agent_config.allow_deep_research:
                    continue
                
                # 创建工具实例
                tool = tool_class(
                    db_session=self.db_session,
                    engine_config=self.engine_config
                )
                tools.append(tool)
                logger.debug(f"已创建工具实例: {tool_name}")
            except Exception as e:
                logger.error(f"创建工具实例 {tool_name} 失败: {str(e)}")
        
        return tools 