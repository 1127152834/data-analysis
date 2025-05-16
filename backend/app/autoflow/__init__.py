"""
Autoflow module initialization.
This is a temporary workaround until full migration to new event system.
"""

# When we complete the migration, uncomment this:
from .events.tool_events import (
    BaseEvent, ToolCallEvent, ToolResultEvent, StepEndEvent, InfoEvent, ErrorEvent, TextEvent
)
from .events.converter import EventConverter

from .context import Context
from .workflow import Workflow, step
from .agents import (
    BaseAgent, InputProcessorAgent, 
    ReasoningAgent, ResponseAgent,
    ExternalEngineAgent
)
from .autoflow_agent import AutoFlowAgent

__all__ = [
    # Events will be added back later
    "BaseEvent", "ToolCallEvent", "ToolResultEvent", "StepEndEvent", 
    "InfoEvent", "ErrorEvent", "TextEvent", "EventConverter",
    
    # Context
    "Context",
    
    # Workflow
    "Workflow", "step",
    
    # Agents
    "BaseAgent", "InputProcessorAgent",
    "ReasoningAgent", "ResponseAgent",
    "ExternalEngineAgent",
    
    # Main workflow
    "AutoFlowAgent",
] 