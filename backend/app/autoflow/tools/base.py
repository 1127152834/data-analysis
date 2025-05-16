from typing import Any, Dict, List, Optional, Union, TypeVar, Generic, Type
from pydantic import BaseModel, Field
import logging
import asyncio
import time
import uuid
from enum import Enum

# 工具调用状态枚举
class ToolCallStatus(str, Enum):
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"

# 工具参数基类
class ToolParameters(BaseModel):
    """所有工具参数必须继承此类"""
    pass

# 工具结果基类
class ToolResult(BaseModel):
    """所有工具结果必须继承此类"""
    success: bool = True
    error_message: Optional[str] = None

# 泛型类型定义
P = TypeVar('P', bound=ToolParameters)
R = TypeVar('R', bound=ToolResult)

# 基础工具类
class BaseTool(Generic[P, R]):
    """所有工具必须继承此类"""
    
    # 工具元数据
    name: str
    description: str
    parameter_type: Type[P]
    result_type: Type[R]
    
    def __init__(self, name: str, description: str, parameter_type: Type[P], result_type: Type[R]):
        self.name = name
        self.description = description
        self.parameter_type = parameter_type
        self.result_type = result_type
        self.logger = logging.getLogger(f"autoflow.tools.{self.name}")
    
    async def execute(self, parameters: P) -> R:
        """执行工具逻辑，必须由子类实现"""
        raise NotImplementedError("Tool must implement execute method")
    
    def get_metadata(self) -> Dict[str, Any]:
        """获取工具元数据"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameter_type.model_json_schema(),
            "result": self.result_type.model_json_schema()
        } 