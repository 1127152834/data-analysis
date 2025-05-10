import logging
from typing import Optional, Sequence
from llama_index.llms.openai import OpenAI
from llama_index.core.tools.types import BaseTool
from llama_index.core.tools import FunctionTool

"""
查询分发器模块

本模块实现了查询分发功能，用于将用户的复杂查询分解为子查询并路由到适当的工具处理。
这是RAG系统中的关键组件，负责理解用户意图并选择合适的检索和处理策略。
"""

logger = logging.getLogger(__name__)

# 默认系统提示词，指导LLM如何分发查询
DefaultSystemPrompt = """
You are a highly skilled customer assistant, responsible for dispatching user questions to the most appropriate tools or resources. Your primary objective is to ensure each user question is handled accurately and efficiently by selecting the best-suited tool for the task.
For more complex questions, you should break them down into clear, manageable sub-questions and route each to the relevant tools for individual resolution. It's important to maintain clarity and precision in this process, ensuring that the sub-questions are well-defined and can be resolved independently.
If you encounter concepts or entities you are not familiar with, you can break the query down into a sub-question to clarify the specific concept or entity. For example, if the query involves "what is the latest version," you can treat this as a sub-question to better understand the context before proceeding with the solution.
"""


class QueryDispatcher:
    """
    查询分发器类

    负责将用户查询分发到适当的工具处理。可以处理复杂查询，
    将其分解为子查询并路由到相关工具进行解析。
    """

    def __init__(self, llm: OpenAI, system_prompt: Optional[str] = None):
        """
        初始化查询分发器

        参数:
            llm: OpenAI大语言模型实例，用于理解和分解查询
            system_prompt: 系统提示词，指导LLM如何分发查询，如果为None则使用默认提示词
        """
        if system_prompt is None:
            system_prompt = DefaultSystemPrompt

        self._llm = llm
        self._llm.system_prompt = system_prompt

    def route(self, query: str, tools: Sequence["BaseTool"]) -> str:
        """
        路由查询到适当的工具

        将用户查询分析并路由到提供的工具列表中的适当工具进行处理

        参数:
            query: 用户查询字符串
            tools: 可用工具序列，每个工具应实现BaseTool接口

        返回:
            str: 处理结果或工具调用信息

        注意:
            该方法使用LLM识别查询意图并选择合适的工具。
            对于复杂查询，可能会分解为多个子查询并并行调用多个工具。
        """
        # 使用LLM和可用工具处理查询
        response = self._llm.chat_with_tools(
            tools, query, allow_parallel_tool_calls=True, verbose=True
        )

        try:
            # 从响应中提取工具调用
            tool_calls = self._llm.get_tool_calls_from_response(
                response, error_on_no_tool_call=True
            )
        except Exception as e:
            # 记录异常并返回错误信息
            logger.exception(e)
            return f"An error occurred while processing the query: {query}"

        return tool_calls


# 模拟回答过程的工具函数
def answer(query: str) -> str:
    """
    回答用户查询的示例函数

    这是一个简单的示例函数，演示如何实现工具函数以供分发器使用

    参数:
        query: 用户查询字符串

    返回:
        str: 回答字符串
    """
    return f"I need some time to answer your question: {query}."


# 创建示例工具，从默认值构建函数工具
answer_tool = FunctionTool.from_defaults(fn=answer)
