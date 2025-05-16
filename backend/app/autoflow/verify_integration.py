#!/usr/bin/env python
"""
验证工作流、Agent与工具框架的完整集成
"""

import logging
import asyncio
import sys
from typing import List, Dict, Any, Optional, Union, AsyncGenerator
from pydantic import BaseModel

# 设置日志格式
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 导入必要的模块
from app.autoflow.context import Context
from app.autoflow.events import Event, StartEvent, StopEvent, StreamEvent, ResponseEvent
from app.autoflow.events.tool_events import (
    BaseEvent, ToolCallEvent, ToolResultEvent, InfoEvent, ErrorEvent, TextEvent
)
from app.autoflow.workflow import Workflow
from app.autoflow.agents.base_agent import BaseAgent
from app.autoflow.tools.base import BaseTool, ToolParameters, ToolResult
from app.autoflow.tools.registry import ToolRegistry
from app.autoflow.tools.init import register_tools, get_tool_registry

# 定义测试工具
class CalculateParameters(ToolParameters):
    """计算工具参数"""
    a: int
    b: int
    operation: str = "add"  # add, subtract, multiply, divide
    
class CalculateResult(ToolResult):
    """计算工具结果"""
    result: float = 0
    
    def model_dump(self) -> Dict[str, Any]:
        """重写model_dump方法，确保返回字典包含result字段"""
        return {
            "result": self.result,
            "success": self.success,
            "error_message": self.error_message or ""
        }
    
class CalculateTool(BaseTool[CalculateParameters, CalculateResult]):
    """计算工具"""
    
    def __init__(self):
        super().__init__(
            name="calculate",
            description="执行简单的数学计算",
            parameter_type=CalculateParameters,
            result_type=CalculateResult
        )
    
    async def execute(self, parameters: CalculateParameters) -> CalculateResult:
        """执行计算操作"""
        logger.info(f"执行计算: {parameters.a} {parameters.operation} {parameters.b}")
        
        try:
            result = 0
            if parameters.operation == "add":
                result = parameters.a + parameters.b
            elif parameters.operation == "subtract":
                result = parameters.a - parameters.b
            elif parameters.operation == "multiply":
                result = parameters.a * parameters.b
            elif parameters.operation == "divide":
                if parameters.b == 0:
                    return CalculateResult(
                        success=False,
                        error_message="除数不能为零"
                    )
                result = parameters.a / parameters.b
            else:
                return CalculateResult(
                    success=False,
                    error_message=f"不支持的操作: {parameters.operation}"
                )
            
            return CalculateResult(
                success=True,
                result=result
            )
        except Exception as e:
            return CalculateResult(
                success=False,
                error_message=f"计算错误: {str(e)}"
            )

# 定义测试Agent
class TestWorkflowAgent(BaseAgent):
    """测试工作流的Agent"""
    
    def __init__(self):
        super().__init__(
            name="workflow_test_agent",
            description="用于测试工作流的Agent",
            tool_registry=ToolRegistry()
        )
        
        # 注册测试工具
        self.register_tools([CalculateTool()])
        
        # 设置事件接收器
        self.received_events: List[BaseEvent] = []
    
    def _event_receiver(self, event):
        """接收并记录事件"""
        logger.info(f"收到事件: {event.event_type} - {event.payload if hasattr(event, 'payload') else 'No payload'}")
        self.received_events.append(event)
    
    async def process(self, ctx: Context, event: Event) -> Union[Event, AsyncGenerator[Event, None]]:
        """处理事件"""
        # 设置事件发射器
        self.set_event_emitter(self._event_receiver)
        
        # 如果是开始事件
        if isinstance(event, StartEvent):
            self.emit_info("开始处理工作流")
            
            # 调用计算工具
            result_event = await self.call_tool(
                tool_name="calculate",
                parameters={
                    "a": 10,
                    "b": 5,
                    "operation": "add"
                },
                step=1
            )
            
            # 检查工具执行结果
            if result_event.success:
                result = result_event.result.get("result", 0)
                self.emit_text(f"计算结果: {result}")
            else:
                self.emit_error(f"计算失败: {result_event.error_message}")
            
            # 再次调用工具，使用不同操作
            result_event = await self.call_tool(
                tool_name="calculate",
                parameters={
                    "a": 10,
                    "b": 2,
                    "operation": "divide"
                },
                step=2
            )
            
            # 检查工具执行结果
            if result_event.success:
                result = result_event.result.get("result", 0)
                self.emit_text(f"计算结果: {result}")
            else:
                self.emit_error(f"计算失败: {result_event.error_message}")
            
            # 返回响应事件
            return ResponseEvent(content="工作流处理完成")
        else:
            self.emit_error(f"不支持的事件类型: {type(event)}")
            return ErrorEvent(message=f"不支持的事件类型: {type(event)}")

# 定义工作流测试函数
async def test_workflow_integration():
    """测试工作流集成"""
    logger.info("开始测试工作流集成...")
    
    try:
        # 创建测试Agent
        agent = TestWorkflowAgent()
        
        # 创建工作流
        workflow = Workflow(agent=agent)
        
        # 创建上下文和事件
        ctx = Context()
        event = StartEvent()
        
        # 处理事件
        result = await workflow.process(ctx, event)
        
        # 验证结果
        if isinstance(result, ResponseEvent):
            logger.info(f"✅ 工作流返回响应事件: {result.answer}")
            success = True
        else:
            logger.error(f"❌ 工作流没有返回响应事件: {type(result)}")
            success = False
            
        # 验证事件数量
        if len(agent.received_events) >= 5:  # 应至少有开始、两次工具调用、两次工具结果
            logger.info(f"✅ 工作流生成了足够的事件: {len(agent.received_events)}")
            success = success and True
        else:
            logger.error(f"❌ 工作流事件数量不足: {len(agent.received_events)}")
            success = False
        
        return success
            
    except Exception as e:
        logger.error(f"❌ 工作流测试异常: {str(e)}", exc_info=True)
        return False

# 主函数
if __name__ == "__main__":
    logger.info("验证工作流、Agent与工具框架完整集成...")
    result = asyncio.run(test_workflow_integration())
    
    if result:
        logger.info("🎉 验证成功: 工作流、Agent与工具框架已完全集成!")
        sys.exit(0)
    else:
        logger.error("❌ 验证失败: 工作流、Agent与工具框架集成测试失败!")
        sys.exit(1) 