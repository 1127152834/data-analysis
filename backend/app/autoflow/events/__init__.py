"""autoflow events模块，包含工作流中使用的各种事件定义。"""

# 导入新的tool_events模块中的事件类
from .tool_events import (
    EventType,
    BaseEvent,
    ToolCallEvent,
    ToolResultEvent,
    StepEndEvent,
    InfoEvent,
    ErrorEvent,
    TextEvent,
    # 兼容性事件类型
    StartEvent,
    StopEvent,
    StreamEvent,
    ResponseEvent,
    # 新增兼容性事件类型
    PrepEvent,
    InputEvent,
    KnowledgeEvent,
    ReasoningEvent,
    ExternalEngineEvent
)

# 从converter模块导出转换器
from .converter import EventConverter

# 定义公共接口，Event是BaseEvent的别名
Event = BaseEvent

__all__ = [
    # 新版事件基类和Event别名
    "EventType", "BaseEvent", "Event", 
    
    # 工具相关事件
    "ToolCallEvent", "ToolResultEvent", "StepEndEvent", 
    "InfoEvent", "ErrorEvent", "TextEvent",
    
    # 兼容旧版系统的事件
    "StartEvent", "StopEvent", "StreamEvent", "ResponseEvent",
    "PrepEvent", "InputEvent", "KnowledgeEvent", "ReasoningEvent", "ExternalEngineEvent",
    
    # 转换器
    "EventConverter"
]

# 注意：此模块不再从旧版events.py导入，以避免循环导入问题
# 在后续阶段，我们将修改依赖于旧版事件系统的模块，使其使用新的事件类 