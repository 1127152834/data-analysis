import inspect
from typing import Any, Callable, Dict, List, Type, TypeVar, Union, AsyncGenerator, Optional, get_type_hints
import asyncio
from functools import wraps
import logging

# 使用新的事件系统导入所有事件类型
from .events import Event, StartEvent, StopEvent, StreamEvent, ResponseEvent

from .context import Context

# 添加专用日志器
logger = logging.getLogger("autoflow.workflow")

E = TypeVar('E', bound=Event)
T = TypeVar('T', bound=Event)

class StepHandler:
    """步骤处理器，封装工作流步骤的执行逻辑"""
    
    def __init__(self, workflow, event_type, handler):
        self.workflow = workflow
        self.event_type = event_type
        self.handler = handler
        self.result = None
        self.error = None
        self.next_handler = None
        self.context = None
        # 打印函数信息，便于调试
        logger.info(f"【工作流】注册处理器: {handler.__name__} -> {event_type.__name__}")
    
    async def handle(self, event: Event, context: Context):
        """处理事件"""
        logger.info(f"【工作流】开始处理事件: {type(event).__name__} --> 使用处理器: {self.handler.__name__}")
        self.context = context
        try:
            # 调用处理函数，可能返回下一个事件
            logger.info(f"【工作流】执行处理器: {self.handler.__name__}")
            next_event = await self.handler(context, event)
            self.result = next_event
            
            if next_event:
                logger.info(f"【工作流】处理器 {self.handler.__name__} 返回事件: {type(next_event).__name__}")
            else:
                logger.warning(f"【工作流】处理器 {self.handler.__name__} 未返回事件!")
            
            # 如果是StopEvent，工作流结束
            if isinstance(next_event, StopEvent):
                logger.info(f"【工作流】收到StopEvent, 工作流结束, 结果: {next_event.result}")
                return next_event.result
            
            # 否则继续处理下一个事件
            if next_event and self.next_handler:
                logger.info(f"【工作流】继续处理下一个事件: {type(next_event).__name__} --> 下一个处理器: {self.next_handler.handler.__name__}")
                return await self.next_handler.handle(next_event, context)
            elif next_event and not self.next_handler:
                logger.warning(f"【工作流】没有合适的处理器处理 {type(next_event).__name__} 事件!")
            
            return next_event
        except Exception as e:
            self.error = e
            logger.error(f"【工作流错误】处理器 {self.handler.__name__} 执行失败: {str(e)}", exc_info=True)
            raise
    
    async def stream_events(self) -> AsyncGenerator[Any, None]:
        """事件流生成器"""
        logger.info(f"【工作流】开始生成事件流: 处理器={self.handler.__name__}")
        # 等待处理器完成
        await asyncio.sleep(0)
        
        # 首先生成处理器的事件
        if hasattr(self.handler, 'events') and self.handler.events:
            logger.info(f"【工作流】处理器 {self.handler.__name__} 有 {len(self.handler.events)} 个事件")
            for event in self.handler.events:
                logger.info(f"【工作流】生成事件: {type(event).__name__}")
                # 转换事件为ChatEvent或可序列化对象
                transformed_event = self._transform_event(event)
                if transformed_event:
                    yield transformed_event
            # 清空事件队列
            logger.info(f"【工作流】清空处理器 {self.handler.__name__} 的事件队列")
            self.handler.events = []
        
        # 如果当前事件是StreamEvent，生成其delta
        if isinstance(self.result, StreamEvent):
            logger.info(f"【工作流】生成StreamEvent: {self.result.delta}")
            yield self._transform_event(self.result)
        
        # 如果当前结果是其他类型的事件，也生成它
        elif self.result and not isinstance(self.result, StopEvent):
            logger.info(f"【工作流】生成非流式事件: {type(self.result).__name__}")
            if hasattr(self.result, 'answer') and getattr(self.result, 'answer'):
                logger.info(f"【工作流】生成ResponseEvent，回答: {getattr(self.result, 'answer')[:50]}...")
            transformed_result = self._transform_event(self.result)
            if transformed_result:
                yield transformed_result
        
        # 然后递归生成下一个处理器的事件
        if self.result and not isinstance(self.result, StopEvent) and self.next_handler:
            logger.info(f"【工作流】开始递归生成下一个处理器的事件: {self.next_handler.handler.__name__}")
            try:
                event_count = 0
                async for event in self.next_handler.stream_events():
                    event_count += 1
                    logger.info(f"【工作流】递归生成事件 #{event_count}: {type(event).__name__}")
                    if event:
                        yield event
                logger.info(f"【工作流】递归生成完成，共生成 {event_count} 个事件")
            except Exception as e:
                logger.error(f"【工作流错误】递归生成事件出错: {str(e)}", exc_info=True)
                # 生成错误事件确保前端仍能收到回复
                logger.info("【工作流】生成错误响应事件")
                from app.rag.chat.stream_protocol import ChatEvent
                from app.rag.types import ChatEventType
                yield ChatEvent(
                    event_type=ChatEventType.ERROR_PART,
                    payload=f"处理您的请求时遇到了问题。错误: {str(e)}"
                )
        else:
            logger.info(f"【工作流】不再继续递归生成事件, result={self.result}, next_handler={self.next_handler}")
            
            # 如果整个链执行完毕但未生成任何结果，返回默认响应
            if (not hasattr(self, 'events') or not self.events) and not isinstance(self.result, ResponseEvent):
                logger.warning("【工作流】整个处理器链执行完毕但未生成有效响应，返回默认响应")
                from app.rag.chat.stream_protocol import ChatEvent
                from app.rag.types import ChatEventType
                yield ChatEvent(
                    event_type=ChatEventType.TEXT_PART,
                    payload={"message": "很抱歉，我无法找到相关信息来回答您的问题。请尝试用不同的方式提问，或者询问其他问题。"}
                )
    
    def _transform_event(self, event):
        """将事件对象转换为可序列化对象
        
        处理各种不同类型的事件，确保返回的对象可以被FastAPI序列化
        """
        from app.rag.chat.stream_protocol import ChatEvent
        from app.rag.types import ChatEventType
        
        # 已经是ChatEvent，直接返回
        if hasattr(event, 'event_type') and hasattr(event, 'payload'):
            return event
            
        # 处理ResponseEvent
        if hasattr(event, 'answer') and getattr(event, 'answer'):
            return ChatEvent(
                event_type=ChatEventType.TEXT_PART,
                payload={"message": getattr(event, 'answer')}
            )
        
        # 处理StreamEvent
        if hasattr(event, 'delta') and getattr(event, 'delta'):
            return ChatEvent(
                event_type=ChatEventType.TEXT_PART,
                payload={"message": getattr(event, 'delta')}
            )
            
        # 处理其他类型事件
        try:
            import json
            from pydantic import BaseModel
            
            # 如果是Pydantic模型，使用model_dump
            if hasattr(event, 'model_dump'):
                event_dict = event.model_dump()
            else:
                # 否则尝试直接转换为字典
                event_dict = {
                    "event_type": type(event).__name__,
                    "data": {k: v for k, v in event.__dict__.items() if not k.startswith('_')}
                }
                
            return ChatEvent(
                event_type=ChatEventType.DATA_PART,
                payload=event_dict
            )
        except Exception as e:
            logger.error(f"【工作流错误】转换事件失败: {str(e)}", exc_info=True)
            return None

def step(func=None, event_type=None):
    """步骤装饰器，有两种使用方式:
    
    1. @step - 不指定事件类型 
    2. @step(event_type=SomeEvent) - 指定事件类型
    """
    # 如果直接作为装饰器使用 @step，不带参数
    if func is not None:
        @wraps(func)
        async def direct_wrapper(self, ctx, event):
            # 直接调用函数，不进行类型检查
            logger.info(f"【工作流】执行步骤 {func.__name__} (不带类型检查)")
            try:
                result = await func(self, ctx, event)
                logger.info(f"【工作流】步骤 {func.__name__} 执行完成，返回类型: {type(result).__name__ if result else 'None'}")
                return result
            except Exception as e:
                logger.error(f"【工作流错误】步骤 {func.__name__} 执行失败: {str(e)}", exc_info=True)
                raise
        return direct_wrapper
    
    # 如果使用带参数的方式 @step(event_type=SomeEvent)
    def decorator(func):
        @wraps(func)
        async def wrapper(self, ctx, event):
            # 检查事件类型
            if event_type is not None and not isinstance(event, event_type):
                error_msg = f"Expected event of type {event_type}, got {type(event)}"
                logger.error(f"【工作流错误】事件类型不匹配: {error_msg}")
                raise TypeError(error_msg)
            
            # 调用原始处理函数
            logger.info(f"【工作流】执行步骤 {func.__name__} (事件类型: {event_type.__name__ if event_type else 'Any'})")
            try:
                result = await func(self, ctx, event)
                logger.info(f"【工作流】步骤 {func.__name__} 执行完成，返回类型: {type(result).__name__ if result else 'None'}")
                return result
            except Exception as e:
                logger.error(f"【工作流错误】步骤 {func.__name__} 执行失败: {str(e)}", exc_info=True)
                raise
        return wrapper
    return decorator

class Workflow:
    """工作流引擎，负责管理和执行工作流步骤"""
    
    def __init__(self, agent=None):
        self.handlers: Dict[Type[Event], Callable] = {}
        self._event_queue = asyncio.Queue()
        self._is_running = False
        self.agent = agent
        logger.info("【工作流】初始化工作流引擎")
        
        # 如果提供了agent，自动添加agent的process方法作为事件处理器
        if self.agent:
            logger.info(f"【工作流】集成Agent: {self.agent.name}")
    
    def add_step(self, event_type: Type[Event], handler: Callable):
        """添加工作流步骤"""
        logger.info(f"【工作流】添加步骤: {event_type.__name__} -> {handler.__name__}")
        self.handlers[event_type] = handler
    
    def start(self, event: Event, context: Context = None) -> StepHandler:
        """启动工作流
        
        参数:
            event: 触发工作流的初始事件
            context: 上下文对象，如果为None则创建新的上下文
            
        返回:
            StepHandler: 第一个步骤处理器
        """
        logger.info(f"【工作流】启动工作流: 初始事件={type(event).__name__}")
        if context is None:
            context = Context(self)
            logger.info("【工作流】创建新的上下文对象")
        else:
            logger.info("【工作流】使用已有的上下文对象")
            
        event_type = type(event)
        handler = self.handlers.get(event_type)
        
        if not handler:
            error_msg = f"No handler for event type {event_type}"
            logger.error(f"【工作流错误】{error_msg}")
            raise ValueError(error_msg)
            
        logger.info(f"【工作流】创建第一个步骤处理器: {handler.__name__}")
        first_handler = StepHandler(self, event_type, handler)
        
        # 根据事件类型链接后续处理器
        logger.info("【工作流】链接后续处理器")
        self._link_handlers(first_handler)
        
        # 异步执行第一个处理器
        logger.info(f"【工作流】异步执行第一个处理器: {handler.__name__}")
        asyncio.create_task(first_handler.handle(event, context))
        
        return first_handler
    
    def _link_handlers(self, first_handler: StepHandler):
        """链接处理器链"""
        current = first_handler
        
        # 如果处理器返回的事件类型有对应的处理器，链接它们
        for event_type, handler in self.handlers.items():
            if current.event_type != event_type and event_type not in self._get_visited_types(first_handler):
                next_handler = StepHandler(self, event_type, handler)
                logger.info(f"【工作流】链接处理器: {current.handler.__name__} -> {handler.__name__}")
                current.next_handler = next_handler
                current = next_handler
    
    def _get_visited_types(self, handler: StepHandler) -> List[Type[Event]]:
        """获取处理器链中已经访问过的事件类型"""
        visited = []
        current = handler
        
        while current:
            visited.append(current.event_type)
            current = current.next_handler
        
        logger.debug(f"【工作流】已访问的事件类型: {[t.__name__ for t in visited]}")
        return visited

    async def process(self, ctx: Context, event: Event) -> Union[Event, AsyncGenerator[Event, None]]:
        """处理事件，集成Agent的处理逻辑
        
        参数:
            ctx: 上下文对象
            event: 输入事件
            
        返回:
            Event或事件生成器
        """
        logger.info(f"【工作流】开始处理事件: {type(event).__name__}")
        
        # 如果有集成的Agent，则委托给Agent处理
        if self.agent:
            logger.info(f"【工作流】委托给Agent处理: {self.agent.name}")
            return await self.agent.process(ctx, event)
        
        # 否则使用传统的工作流处理逻辑
        logger.info("【工作流】使用传统工作流处理逻辑")
        runner = WorkflowRunner(self, ctx, event)
        return await runner.run()

class WorkflowRunner:
    """工作流运行器，负责执行具体工作流实例"""
    
    def __init__(self, workflow: Workflow, ctx: Context, start_event: Event):
        self.workflow = workflow
        self.ctx = ctx
        self.start_event = start_event
        self._result = None
        self._is_running = False
        self._event_queue = asyncio.Queue()
        self._event_stream = asyncio.Queue()
        
        # 添加初始事件到队列
        logger.info(f"【工作流】初始化WorkflowRunner, 初始事件={type(start_event).__name__}")
        asyncio.create_task(self._event_queue.put(start_event))
    
    async def run(self) -> Any:
        """执行工作流直到完成并返回结果"""
        if self._is_running:
            logger.info("【工作流】工作流已在运行中，等待结果")
            return await self._get_result()
            
        logger.info("【工作流】开始执行工作流")
        self._is_running = True
        
        try:
            while True:
                # 从队列获取下一个事件
                logger.info("【工作流】等待下一个事件...")
                event = await self._event_queue.get()
                logger.info(f"【工作流】收到事件: {type(event).__name__}")
                
                # 发送事件到流
                await self._event_stream.put(event)
                logger.info(f"【工作流】事件已添加到事件流: {type(event).__name__}")
                
                # 如果是停止事件，则结束工作流
                if isinstance(event, StopEvent):
                    logger.info("【工作流】收到StopEvent，工作流将结束")
                    self._result = event.result
                    break
                
                # 查找对应的处理器
                handler = self.workflow.handlers.get(type(event))
                
                if not handler:
                    error_msg = f"No handler found for event type {type(event)}"
                    logger.error(f"【工作流错误】{error_msg}")
                    raise ValueError(error_msg)
                
                # 执行处理器
                try:
                    # 调用处理器处理事件
                    logger.info(f"【工作流】执行处理器: {handler.__name__}")
                    next_event = await handler(self.ctx, event)
                    
                    # 如果处理器返回了新事件，则添加到队列
                    if next_event:
                        logger.info(f"【工作流】处理器返回新事件: {type(next_event).__name__}, 添加到队列")
                        await self._event_queue.put(next_event)
                        
                        # 如果是停止事件，可以提前结束当前处理器循环
                        if isinstance(next_event, StopEvent):
                            logger.info("【工作流】收到StopEvent，提前结束处理器循环")
                            break
                    else:
                        logger.warning(f"【工作流】处理器 {handler.__name__} 没有返回事件")
                except Exception as e:
                    # 记录错误详情
                    import traceback
                    error_msg = f"处理器 {handler.__name__} 执行出错: {str(e)}"
                    logger.error(f"【工作流错误】{error_msg}")
                    logger.error(traceback.format_exc())
                    
                    # 处理异常并添加停止事件
                    error_event = StopEvent(result={"error": str(e)})
                    logger.info("【工作流】创建错误StopEvent，添加到队列")
                    await self._event_queue.put(error_event)
                    break
        finally:
            logger.info("【工作流】工作流执行完成")
            self._is_running = False
            
        logger.info(f"【工作流】工作流结果: {self._result}")
        return self._result
    
    async def _get_result(self) -> Any:
        """等待并获取工作流结果"""
        logger.info("【工作流】等待工作流结果...")
        while self._is_running or not self._event_queue.empty():
            await asyncio.sleep(0.1)
            
        logger.info(f"【工作流】获取到结果: {self._result}")
        return self._result
    
    async def stream_events(self) -> AsyncGenerator[Event, None]:
        """流式获取工作流事件"""
        # 启动工作流但不等待完成
        if not self._is_running:
            logger.info("【工作流】开始流式事件处理，启动工作流")
            asyncio.create_task(self.run())
            
        # 持续从事件流中获取事件
        logger.info("【工作流】开始生成流式事件")
        try:
            while True:
                logger.info("【工作流】等待新的事件...")
                event = await self._event_stream.get()
                logger.info(f"【工作流】生成流式事件: {type(event).__name__}")
                yield event
                
                # 如果是停止事件，则结束流
                if isinstance(event, StopEvent):
                    logger.info("【工作流】收到StopEvent，流式事件生成结束")
                    break
        except asyncio.CancelledError:
            logger.warning("【工作流】流式事件生成被取消")
    
    def __await__(self):
        """使WorkflowRunner对象可等待"""
        return self.run().__await__() 