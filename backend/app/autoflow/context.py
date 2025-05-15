from typing import Any, Dict, Optional, TypeVar, Type
from llama_index.core.tools import ToolOutput

T = TypeVar('T')

class Context:
    """工作流上下文，用于在工作流步骤间传递状态"""
    
    def __init__(self, workflow=None):
        self._data: Dict[str, Any] = {}
        self._workflow = workflow
    
    async def get(self, key: str, default: Any = None) -> Any:
        """获取上下文中的数据"""
        return self._data.get(key, default)
    
    async def set(self, key: str, value: Any) -> None:
        """设置上下文中的数据"""
        self._data[key] = value
    
    async def get_typed(self, key: str, type_: Type[T], default: Optional[T] = None) -> Optional[T]:
        """获取指定类型的上下文数据"""
        value = await self.get(key, default)
        if isinstance(value, type_):
            return value
        return default
    
    def data(self) -> Dict[str, Any]:
        """获取所有上下文数据"""
        return self._data
    
    @property
    def workflow(self):
        """获取关联的工作流"""
        return self._workflow
    
    def create_tool_output(self, 
                          raw_input: Dict[str, Any], 
                          raw_output: Dict[str, Any]) -> ToolOutput:
        """创建标准化的工具输出对象"""
        return ToolOutput(
            raw_input=raw_input,
            raw_output=raw_output,
            content=str(raw_output)
        ) 