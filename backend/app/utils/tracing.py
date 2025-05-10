from contextlib import contextmanager
from typing import Optional, Generator
from langfuse.client import StatefulSpanClient, StatefulClient
from langfuse.llama_index import LlamaIndexInstrumentor
from langfuse.llama_index._context import langfuse_instrumentor_context

"""
Langfuse追踪工具模块

提供与Langfuse集成的追踪功能，用于监控和分析LLM应用的性能和调用情况
该模块封装了Langfuse的基本功能，便于在应用中使用追踪和观测功能
"""


class LangfuseContextManager:
    """
    Langfuse上下文管理器

    管理Langfuse的追踪和观测上下文，提供跟踪LLM调用的功能
    支持追踪（trace）和跨度（span）的创建和管理
    """

    langfuse_client: Optional[StatefulSpanClient] = None

    def __init__(self, instrumentor: LlamaIndexInstrumentor):
        """
        初始化Langfuse上下文管理器

        参数:
            instrumentor: LlamaIndex的Langfuse检测器实例
        """
        self.instrumentor = instrumentor

    @contextmanager
    def observe(self, **kwargs):
        """
        创建和管理观测上下文

        启动追踪器并创建一个观测上下文，用于跟踪一系列相关操作

        参数:
            **kwargs: 传递给observe方法的关键字参数，如trace_name等

        返回:
            上下文管理器，yield一个追踪客户端
        """
        try:
            self.instrumentor.start()
            with self.instrumentor.observe(**kwargs) as trace_client:
                trace_client.update(name=kwargs.get("trace_name"), **kwargs)
                self.langfuse_client = trace_client
                yield trace_client
        except Exception:
            raise
        finally:
            self.instrumentor.flush()
            self.instrumentor.stop()

    @contextmanager
    def span(
        self, parent_client: Optional[StatefulClient] = None, **kwargs
    ) -> Generator["StatefulSpanClient", None, None]:
        """
        创建和管理跨度上下文

        在当前追踪中创建一个新的跨度，用于跟踪特定子操作

        参数:
            parent_client: 父追踪客户端，如果不提供则使用当前的langfuse_client
            **kwargs: 传递给span方法的关键字参数

        返回:
            上下文管理器，yield一个跨度客户端
        """
        if parent_client:
            client = parent_client
        else:
            client = self.langfuse_client
        span = client.span(**kwargs)

        ctx = langfuse_instrumentor_context.get().copy()
        old_parent_observation_id = ctx.get("parent_observation_id")
        langfuse_instrumentor_context.get().update(
            {
                "parent_observation_id": span.id,
            }
        )

        try:
            yield span
        except Exception:
            raise
        finally:
            ctx.update(
                {
                    "parent_observation_id": old_parent_observation_id,
                }
            )
            langfuse_instrumentor_context.get().update(ctx)

    @property
    def trace_id(self) -> Optional[str]:
        """
        获取当前追踪的ID

        返回:
            str或None: 当前追踪的ID，如果没有活动追踪则返回None
        """
        if self.langfuse_client:
            return self.langfuse_client.trace_id
        else:
            return None

    @property
    def trace_url(self) -> Optional[str]:
        """
        获取当前追踪的URL

        返回:
            str或None: 当前追踪的Langfuse控制台URL，如果没有活动追踪则返回None
        """
        if self.langfuse_client:
            return self.langfuse_client.get_trace_url()
        else:
            return None
