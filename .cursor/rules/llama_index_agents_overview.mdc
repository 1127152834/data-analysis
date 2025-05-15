# LlamaIndex Agents (O'Reilly Cookbook Overview) 最佳实践

本节总结了 LlamaIndex 中 Agent 使用的通用最佳实践，基于 O'Reilly 课程手册中的 "Agents" 模块。内容涵盖了 Agent 的基本概念、工具定义以及不同类型 Agent (ReAct, Function Calling) 的应用，特别强调了与RAG（QueryEngineTool）的结合。

### 1. Agent 与工具的核心概念

*   **Agent**: 一个由 LLM 驱动的实体，能够通过一系列思考和行动（通常是调用工具）来完成复杂任务。
*   **工具 (Tools)**: Agent 用来与外部世界交互、获取信息或执行操作的接口。常见的工具类型包括：
    *   **`FunctionTool`**: 从 Python 函数创建，用于执行通用计算或操作。
    *   **`QueryEngineTool`**: 将一个查询引擎（如向量索引查询引擎）包装成工具，使 Agent 能够从知识库中检索信息 (RAG)。

### 2. 定义工具的最佳实践

*   **`FunctionTool.from_defaults`**: 创建简单函数工具的便捷方法。
*   **`ToolMetadata`**: 对于 `QueryEngineTool` 或其他更复杂的工具，使用 `ToolMetadata` 来提供：
    *   `name`: 一个简短、唯一且具有描述性的工具名称，Agent 将用此名称来选择和调用工具。
    *   `description`: **极其重要**。清晰、准确地描述工具的功能、能回答什么类型的问题、期望的输入格式等。Agent 的工具选择能力在很大程度上依赖于这些描述的质量。
    ```python
    from llama_index.core.tools import FunctionTool, QueryEngineTool, ToolMetadata

    # 示例：简单的函数工具
    # def add(a: int, b: int) -> int:
    #     """Add two integers."""
    #     return a + b
    # add_tool = FunctionTool.from_defaults(fn=add)

    # 示例：QueryEngineTool
    # # 假设 lyft_query_engine 是一个已配置的查询引擎
    # lyft_tool = QueryEngineTool(
    #     query_engine=lyft_query_engine,
    #     metadata=ToolMetadata(
    #         name="lyft_financial_data_2021",
    #         description="提供关于Lyft公司2021年度的财务信息。输入应为一个具体的问题。"
    #     )
    # )
    ```

### 3. Agent 类型与选择

LlamaIndex 支持多种 Agent 实现，常见的有：

*   **`ReActAgent` (`llama_index.core.agent.ReActAgent`)**:
    *   通过"思考（Thought）-> 行动（Action）-> 观察（Observation）"的循环来进行推理和工具调用。
    *   依赖于精心设计的 Prompt 来指导其行为。
    *   通常使用 `ReActAgent.from_tools()` 初始化。
    ```python
    # from llama_index.core.agent import ReActAgent
    # from llama_index.llms.openai import OpenAI
    # llm = OpenAI(model="gpt-4o") # 或者其他模型
    # react_agent = ReActAgent.from_tools([add_tool, lyft_tool], llm=llm, verbose=True)
    ```
*   **基于函数调用的 Agent (如 `FunctionCallingAgentWorker`)**:
    *   利用支持函数调用（Function Calling）能力的 LLM（例如 OpenAI 的 gpt-3.5-turbo, gpt-4 等）。
    *   LLM 会直接输出要调用的函数名和参数，通常更结构化和可靠。
    *   使用 `FunctionCallingAgentWorker.from_tools()` 初始化，然后通过 `.as_agent()` 得到 Agent 实例。
    *   可以配置 `allow_parallel_tool_calls` (通常默认为 `False`，但在某些高级 LLM 和场景下可以设为 `True`)。
    ```python
    # from llama_index.core.agent import FunctionCallingAgentWorker
    # agent_worker = FunctionCallingAgentWorker.from_tools(
    #     tools=[add_tool, lyft_tool],
    #     llm=llm, # 需要是支持函数调用的LLM
    #     verbose=True,
    #     allow_parallel_tool_calls=False
    # )
    # function_agent = agent_worker.as_agent()
    ```
*   **选择标准**: 
    *   如果 LLM 支持函数调用，通常推荐使用基于函数调用的 Agent，因为其工具调用通常更精确。
    *   如果 LLM 不支持函数调用，或者需要更细致地控制思考过程的格式，`ReActAgent` 是一个好的选择。

### 4. 将 Agent 与 RAG (QueryEngineTool) 结合

这是 Agent 的一个非常强大的应用场景，使 Agent 能够从外部知识库中检索信息来回答问题。

*   **构建 RAG**: 
    1.  加载数据 (`SimpleDirectoryReader`)。
    2.  构建索引 (`VectorStoreIndex`)。
    3.  从索引创建查询引擎 (`as_query_engine()`)。
*   **包装为 `QueryEngineTool`**: 如上所述，使用 `QueryEngineTool` 将每个查询引擎包装成 Agent 可以使用的工具，并提供清晰的 `name` 和 `description`。
*   **Agent 配置**: 将这些 `QueryEngineTool` 实例提供给 Agent。
    ```python
    # # (接上文 lyft_tool, uber_tool 的定义)
    # combined_tools = [lyft_tool, uber_tool]
    # rag_agent = FunctionCallingAgentWorker.from_tools(combined_tools, llm=llm, verbose=True).as_agent()
    ```
*   **Agent 的决策**: Agent 会根据用户的问题和每个 `QueryEngineTool` 的描述来决定：
    1.  是否需要调用某个查询引擎。
    2.  如果需要，调用哪个查询引擎。
    3.  向该查询引擎传递什么样的问题字符串。

### 5. 与 Agent 交互

*   **`chat()` / `query()`**: 用于与 Agent 进行单轮或多轮对话。
    *   `chat()` 通常用于保持对话历史（如果 Agent 支持记忆功能）。
    *   `query()` 更像是一次性的问题查询。
    ```python
    # response = rag_agent.chat("对比一下Uber和Lyft在2021年的投资情况。")
    # print(response.response)
    ```
*   **`stream_chat()` / `stream_query()`**: (如果可用) 用于流式获取响应，可以实时看到 Agent 的思考过程或最终答案的逐步生成。
*   **`verbose=True`**: 在 Agent 初始化时设置 `verbose=True` 对于调试非常重要，它会打印出 Agent 的思考过程、工具调用、函数参数和工具返回的原始输出。

### 6. 通用最佳实践

*   **LLM选择**: Agent 的能力很大程度上取决于其背后 LLM 的能力。对于复杂的任务和精确的工具使用，推荐使用能力更强的 LLM (如 GPT-4, Claude 3 Sonnet/Opus 等)。
*   **清晰的指令和问题**: 向 Agent 提出的问题或指令应该清晰明确。
*   **迭代和测试**: Agent 的开发通常是一个迭代的过程。需要不断测试 Agent 在不同场景下的表现，并根据结果调整工具定义 (尤其是描述)、Agent 类型或 Prompt。
*   **记忆 (Memory)**: 对于需要进行多轮对话的 Agent，需要为其配置记忆模块，以便 Agent 能够记住之前的交互内容。

---
