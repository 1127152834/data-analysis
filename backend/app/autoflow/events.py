from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field

class Event(BaseModel):
    """工作流事件基类"""
    pass

class StartEvent(Event):
    """工作流启动事件"""
    user_question: str
    chat_history: List[Any] = Field(default_factory=list)

class PrepEvent(Event):
    """准备事件，用于启动或循环工作流"""
    pass

class InputEvent(Event):
    """输入事件，包含用户输入和聊天历史"""
    input: List[Any] = Field(default_factory=list)

class KnowledgeEvent(Event):
    """知识检索事件，包含从知识库和知识图谱检索的结果"""
    knowledge_nodes: List[Dict] = Field(default_factory=list)
    knowledge_graph_context: str = ""

class ReasoningEvent(Event):
    """推理事件，包含Agent的推理过程和决策"""
    reasoning_result: str = ""
    tool_calls: Optional[List[Dict]] = None

class ResponseEvent(Event):
    """推理结果事件，指示生成最终回答"""
    pass

class ExternalEngineEvent(Event):
    """外部引擎事件，指示使用外部引擎处理查询"""
    def __init__(self, goal: str = "", response_format: dict = None, **kwargs):
        super().__init__(**kwargs)
        self.goal = goal
        self.response_format = response_format or {}

class StreamEvent(Event):
    """流式输出事件，包含增量文本"""
    delta: str = ""

class StopEvent(Event):
    """工作流停止事件，包含最终结果"""
    result: Any = None

# 定义前端期望的事件类型兼容层
class ChatEventAdapter:
    """事件适配器，将内部事件转换为前端期望的格式"""
    
    @staticmethod
    def adapt_event(event_type: str, payload: Any) -> Dict[str, Any]:
        """将内部事件适配为前端期望的事件格式"""
        # 这里需要根据实际前端期望的格式进行适配
        return {
            "event_type": event_type,
            "payload": payload
        } 