from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field
import uuid
import time
from enum import Enum

# 事件类型枚举
class EventType(str, Enum):
    TOOL_CALL = "9"  # 工具调用
    TOOL_RESULT = "a"  # 工具结果
    STEP_END = "e"  # 步骤结束
    INFO = "8"  # 信息
    ERROR = "3"  # 错误
    TEXT = "2"  # 文本输出
    START = "1"  # 开始事件
    STOP = "z"  # 结束事件
    STREAM = "s"  # 流式事件
    RESPONSE = "r"  # 响应事件

# 基础事件模型
class BaseEvent(BaseModel):
    event_type: EventType
    timestamp: float = Field(default_factory=time.time)
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))

# 工具调用事件
class ToolCallEvent(BaseEvent):
    event_type: EventType = EventType.TOOL_CALL
    tool_name: str
    tool_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    parameters: Dict[str, Any]
    step: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "toolCallId": self.tool_id,
            "toolName": self.tool_name,
            "args": self.parameters,
            "step": self.step
        }

# 工具结果事件
class ToolResultEvent(BaseEvent):
    """工具结果事件，描述工具执行结果"""
    event_type: EventType = EventType.TOOL_RESULT
    tool_id: str
    tool_name: str
    success: bool = True
    error_message: str = ""  # 添加默认值空字符串
    result: Optional[Dict[str, Any]] = None
    step: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "toolCallId": self.tool_id,
            "result": self.result,
            "success": self.success,
            "errorMessage": self.error_message if not self.success else ""
        }

# 步骤结束事件
class StepEndEvent(BaseEvent):
    event_type: EventType = EventType.STEP_END
    step: int
    finish_reason: str = "stop"
    usage: Dict[str, int] = Field(default_factory=lambda: {"promptTokens": 0, "completionTokens": 0})
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "step": self.step,
            "finishReason": self.finish_reason,
            "usage": self.usage
        }

# 信息事件
class InfoEvent(BaseEvent):
    event_type: EventType = EventType.INFO
    message: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {"message": self.message}

# 错误事件
class ErrorEvent(BaseEvent):
    event_type: EventType = EventType.ERROR
    message: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {"message": self.message}

# 文本输出事件
class TextEvent(BaseEvent):
    event_type: EventType = EventType.TEXT
    message: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {"message": self.message}

# 以下是兼容旧系统的事件类型定义

# 开始事件
class StartEvent(BaseEvent):
    """工作流启动事件"""
    event_type: EventType = EventType.START
    user_question: Optional[str] = ""
    chat_history: List[Any] = Field(default_factory=list)

# 停止事件
class StopEvent(BaseEvent):
    """工作流停止事件，包含最终结果"""
    event_type: EventType = EventType.STOP
    result: Any = None

# 流式输出事件
class StreamEvent(BaseEvent):
    """流式输出事件，包含增量文本"""
    event_type: EventType = EventType.STREAM
    delta: str = ""

# 响应事件
class ResponseEvent(BaseEvent):
    """响应事件，指示生成最终回答"""
    event_type: EventType = EventType.RESPONSE
    answer: str = ""

# 准备事件
class PrepEvent(BaseEvent):
    """准备事件，用于启动或循环工作流"""
    event_type: EventType = EventType.START
    
# 输入事件
class InputEvent(BaseEvent):
    """输入事件，包含用户输入和聊天历史"""
    event_type: EventType = EventType.START
    input: List[Any] = Field(default_factory=list)

# 知识检索事件
class KnowledgeEvent(BaseEvent):
    """知识检索事件，包含从知识库和知识图谱检索的结果"""
    event_type: EventType = EventType.INFO
    knowledge_nodes: List[Dict] = Field(default_factory=list)
    knowledge_graph_context: str = ""

# 推理事件
class ReasoningEvent(BaseEvent):
    """推理事件，包含Agent的推理过程和决策"""
    event_type: EventType = EventType.INFO
    reasoning_result: str = ""
    tool_calls: Optional[List[Dict]] = None

# 外部引擎事件
class ExternalEngineEvent(BaseEvent):
    """外部引擎事件，指示使用外部引擎处理查询"""
    event_type: EventType = EventType.INFO
    goal: str = ""
    response_format: Dict[str, Any] = Field(default_factory=dict) 