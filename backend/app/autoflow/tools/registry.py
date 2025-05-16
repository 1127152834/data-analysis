from typing import Dict, List, Type, Optional, Any
from .base import BaseTool
import logging

logger = logging.getLogger("autoflow.tools.registry")

class ToolRegistry:
    """工具注册器，管理所有可用工具"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ToolRegistry, cls).__new__(cls)
            cls._instance._tools = {}
        return cls._instance
    
    def register_tool(self, tool: BaseTool) -> None:
        """注册工具到注册表"""
        if tool.name in self._tools:
            logger.warning(f"Tool {tool.name} already registered, overwriting")
        self._tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")
    
    def get_tool(self, name: str) -> Optional[BaseTool]:
        """获取指定名称的工具"""
        return self._tools.get(name)
    
    def list_tools(self) -> List[str]:
        """列出所有注册的工具名称"""
        return list(self._tools.keys())
    
    def get_tools_metadata(self) -> List[Dict[str, Any]]:
        """获取所有工具的元数据"""
        return [tool.get_metadata() for tool in self._tools.values()] 