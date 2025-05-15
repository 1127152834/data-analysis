import asyncio
from typing import AsyncGenerator, Generator, TypeVar, Any

T = TypeVar('T')

class AsyncToSyncAdapter:
    """
    将异步生成器转换为同步生成器的适配器
    用法:
        async_gen = some_async_generator()
        sync_gen = AsyncToSyncAdapter(async_gen)
        for item in sync_gen:
            # 使用item
    """
    
    def __init__(self, async_gen: AsyncGenerator[T, None]):
        """
        初始化适配器
        参数:
            async_gen: 要转换的异步生成器
        """
        self.async_gen = async_gen
        # 创建一个事件循环
        self.loop = asyncio.new_event_loop()
    
    def __iter__(self) -> Generator[T, None, None]:
        """使对象可迭代"""
        return self
    
    def __next__(self) -> T:
        """获取下一个值"""
        try:
            # 在事件循环中运行协程，获取下一个值
            coro = self.async_gen.__anext__()
            return self.loop.run_until_complete(coro)
        except StopAsyncIteration:
            # 当异步生成器结束时，抛出StopIteration
            raise StopIteration
        except Exception as e:
            # 处理其他异常
            self.loop.close()
            raise e
    
    def __del__(self):
        """销毁对象时关闭事件循环"""
        if hasattr(self, 'loop') and self.loop is not None:
            self.loop.close() 