import asyncio
import logging
import time
from typing import Any, AsyncGenerator, Iterator, TypeVar, Generic

# 创建专用日志器
logger = logging.getLogger("autoflow.utils")

T = TypeVar('T')

class AsyncToSyncAdapter(Generic[T]):
    """异步生成器到同步迭代器的适配器
    
    用于将异步生成器（AsyncGenerator）转换为同步迭代器（Iterator），
    使得可以在同步环境中使用异步生成器。
    """
    
    def __init__(self, async_gen: AsyncGenerator[T, None]):
        """初始化适配器
        
        参数:
            async_gen: 要转换的异步生成器
        """
        logger.info("【AsyncToSyncAdapter】初始化适配器")
        self.async_gen = async_gen
        self.loop = asyncio.get_event_loop()
        self.buffer = []
        self.exhausted = False
        self.current_future = None
        logger.info("【AsyncToSyncAdapter】适配器初始化完成")
    
    def __iter__(self) -> Iterator[T]:
        """返回迭代器自身"""
        logger.info("【AsyncToSyncAdapter】开始迭代")
        return self
    
    def __next__(self) -> T:
        """获取下一个元素
        
        如果缓冲区为空且异步生成器未耗尽，则运行事件循环获取下一个元素
        
        返回:
            T: 下一个元素
            
        抛出:
            StopIteration: 迭代完成时抛出
        """
        logger.debug("【AsyncToSyncAdapter】获取下一个元素")
        
        # 如果缓冲区有元素，直接返回
        if self.buffer:
            item = self.buffer.pop(0)
            logger.debug(f"【AsyncToSyncAdapter】从缓冲区返回元素: {type(item).__name__}")
            return item
        
        # 如果生成器已耗尽，抛出StopIteration
        if self.exhausted:
            logger.info("【AsyncToSyncAdapter】生成器已耗尽，停止迭代")
            raise StopIteration
        
        # 运行事件循环获取下一批元素
        try:
            logger.debug("【AsyncToSyncAdapter】运行事件循环获取下一批元素")
            self._run_until_next()
            
            # 再次检查缓冲区
            if self.buffer:
                item = self.buffer.pop(0)
                logger.debug(f"【AsyncToSyncAdapter】从新填充的缓冲区返回元素: {type(item).__name__}")
                return item
            
            # 如果缓冲区仍为空，则生成器已耗尽
            logger.info("【AsyncToSyncAdapter】缓冲区为空，生成器已耗尽，停止迭代")
            raise StopIteration
            
        except Exception as e:
            logger.error(f"【AsyncToSyncAdapter错误】获取下一个元素失败: {str(e)}", exc_info=True)
            raise
    
    def _run_until_next(self):
        """运行事件循环直到获取下一个元素或生成器耗尽"""
        try:
            logger.debug("【AsyncToSyncAdapter】开始运行事件循环")
            
            # 尝试获取下一个元素
            async def _anext():
                try:
                    logger.debug("【AsyncToSyncAdapter】调用async_gen.__anext__()")
                    return await self.async_gen.__anext__()
                except StopAsyncIteration:
                    logger.debug("【AsyncToSyncAdapter】捕获到StopAsyncIteration")
                    return None
                except Exception as e:
                    logger.error(f"【AsyncToSyncAdapter错误】__anext__执行失败: {str(e)}", exc_info=True)
                    return None
            
            # 创建一个Future对象用于等待异步生成器的下一个元素
            self.current_future = asyncio.ensure_future(_anext())
            
            # 设置最大等待时间10秒，避免无限等待
            max_wait_time = 10  # 秒
            start_time = time.time()
            
            # 运行事件循环直到Future完成或超时
            while not self.current_future.done():
                logger.debug("【AsyncToSyncAdapter】等待Future完成")
                # 只等待短时间，避免长时间阻塞
                self.loop.run_until_complete(asyncio.sleep(0.05))
                
                # 检查是否超时
                if time.time() - start_time > max_wait_time:
                    logger.warning(f"【AsyncToSyncAdapter】等待异步生成器结果超时({max_wait_time}秒)")
                    # 取消Future并记录为耗尽
                    self.current_future.cancel()
                    self.exhausted = True
                    return
            
            # 获取结果，处理可能的异常
            try:
                result = self.current_future.result()
                logger.debug(f"【AsyncToSyncAdapter】获取到结果: {result is not None}")
            except asyncio.CancelledError:
                logger.warning("【AsyncToSyncAdapter】Future被取消")
                self.exhausted = True
                return
            except Exception as e:
                logger.error(f"【AsyncToSyncAdapter错误】获取Future结果失败: {str(e)}", exc_info=True)
                self.exhausted = True
                return
            
            # 如果结果为None，表示生成器已耗尽
            if result is None:
                logger.info("【AsyncToSyncAdapter】生成器已耗尽")
                self.exhausted = True
                return
            
            # 否则，将结果添加到缓冲区
            logger.debug(f"【AsyncToSyncAdapter】将结果添加到缓冲区: {type(result).__name__}")
            self.buffer.append(result)
            
        except Exception as e:
            logger.error(f"【AsyncToSyncAdapter错误】运行事件循环失败: {str(e)}", exc_info=True)
            self.exhausted = True
            raise 