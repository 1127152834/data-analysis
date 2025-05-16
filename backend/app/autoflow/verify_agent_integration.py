#!/usr/bin/env python
"""
验证Agent集成工具框架
"""

import logging
import asyncio
import sys
from typing import Optional, List, Dict, Any

# 设置日志格式
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 导入必要的模块
from app.autoflow.agents.base_agent import BaseAgent
from app.autoflow.tools.base import BaseTool, ToolParameters, ToolResult
from app.autoflow.tools.registry import ToolRegistry
from app.autoflow.events import Event
from app.autoflow.events.tool_events import BaseEvent, InfoEvent
from app.autoflow.context import Context
from app.rag.chat.stream_protocol import ChatEvent

# 定义一个简单的测试工具
class EchoParameters(ToolParameters):
    """回显工具参数"""
    message: str = "默认消息"
    
class EchoResult(ToolResult):
    """回显工具结果"""
    echo: str = ""
    
class EchoTool(BaseTool[EchoParameters, EchoResult]):
    """回显测试工具"""
    
    def __init__(self):
        super().__init__(
            name="echo_tool",
            description="一个简单的回显测试工具",
            parameter_type=EchoParameters,
            result_type=EchoResult
        )
    
    async def execute(self, parameters: EchoParameters) -> EchoResult:
        """执行回显操作"""
        # 日志记录工具执行
        logger.info(f"EchoTool执行: {parameters.message}")
        
        # 返回结果
        return EchoResult(
            success=True,
            echo=f"回显: {parameters.message}"
        )

# 定义一个简单的测试Agent
class TestAgent(BaseAgent):
    """测试用的Agent"""
    
    def __init__(self):
        super().__init__(
            name="test_agent",
            description="用于测试工具集成的Agent",
            tool_registry=ToolRegistry()
        )
        
        # 注册测试工具
        self.register_tools([EchoTool()])
        
        # 设置事件接收器
        self.received_events: List[ChatEvent] = []
    
    def _event_receiver(self, event: ChatEvent):
        """接收并记录事件"""
        logger.info(f"收到事件: {event.event_type} - {event.payload}")
        self.received_events.append(event)
    
    async def process(self, ctx: Context, event: Event) -> Event:
        """处理事件"""
        # 设置事件发射器
        self.set_event_emitter(self._event_receiver)
        
        # 发送信息事件
        self.emit_info("测试Agent开始处理")
        
        # 调用工具
        await self.call_tool(
            tool_name="echo_tool", 
            parameters={"message": "Hello, Agent!"}, 
            step=1
        )
        
        # 发送处理完成事件
        self.emit_info("测试Agent处理完成")
        
        return InfoEvent(message="处理完成")

# 验证Agent集成
async def verify_agent():
    """验证Agent集成情况"""
    logger.info("开始验证Agent集成...")
    
    # 创建测试Agent
    agent = TestAgent()
    
    # 创建上下文
    ctx = Context()
    
    # 创建测试事件
    event = InfoEvent(message="开始测试")
    
    # 处理事件
    result = await agent.process(ctx, event)
    
    # 验证结果
    if len(agent.received_events) >= 3:  # 应该至少有3个事件：信息+工具调用+工具结果
        logger.info(f"✅ Agent成功集成工具框架，共发出 {len(agent.received_events)} 个事件")
        return True
    else:
        logger.error(f"❌ Agent集成测试失败，只发出了 {len(agent.received_events)} 个事件")
        return False

if __name__ == "__main__":
    logger.info("验证Agent与工具框架集成...")
    result = asyncio.run(verify_agent())
    
    if result:
        logger.info("🎉 验证成功: Agent成功集成了工具框架!")
        sys.exit(0)
    else:
        logger.error("❌ 验证失败: Agent未能成功集成工具框架!")
        sys.exit(1) 