# LlamaIndex ReAct Agent with Query Engine (RAG) Tools 最佳实践

本节总结了将 LlamaIndex ReAct Agent 与查询引擎 (Query Engine) 工具（通常用于 RAG 场景）相结合的最佳实践，基于 "ReAct Agent with Query Engine (RAG) Tools" 示例。

### 1.构建查询引擎 (Query Engine)

*   **数据加载与索引**: 首先，加载您的数据源 (例如，PDF 文件、文本目录) 并为每个数据集构建一个向量存储索引 (`VectorStoreIndex`)。
    ```python
    from llama_index.core import SimpleDirectoryReader, VectorStoreIndex

    # 示例：加载PDF文档并构建索引
    # lyft_docs = SimpleDirectoryReader(input_files=["./data/10k/lyft_2021.pdf"]).load_data()
    # lyft_index = VectorStoreIndex.from_documents(lyft_docs)
    ```
*   **持久化索引 (Optional but Recommended)**: 对于大型索引，建议将其持久化到磁盘，以便后续快速加载，避免重复构建。
    ```python
    # lyft_index.storage_context.persist(persist_dir="./storage/lyft")
    # # 后续加载:
    # from llama_index.core import load_index_from_storage, StorageContext
    # storage_context = StorageContext.from_defaults(persist_dir="./storage/lyft")
    # lyft_index = load_index_from_storage(storage_context)
    ```
*   **创建查询引擎**: 从索引中创建查询引擎实例 (`as_query_engine()`)。可以配置参数如 `similarity_top_k` 来控制检索到的上下文数量。
    ```python
    # lyft_engine = lyft_index.as_query_engine(similarity_top_k=3)
    ```

### 2. 创建查询引擎工具 (QueryEngineTool)

*   **`QueryEngineTool.from_defaults`**: 使用此便捷方法从现有的查询引擎创建工具。
*   **清晰的工具名称 (`name`)**: 为每个查询引擎工具指定一个简短、唯一且具有描述性的名称。Agent 将使用此名称来选择和调用工具。
*   **详细的工具描述 (`description`)**: 这是至关重要的一步。工具的描述应该清晰地说明该工具能提供什么信息（例如，"提供关于某公司2021年财务状况的信息"），以及它期望的输入类型（例如，"使用详细的纯文本问题作为工具的输入"）。ReAct Agent 会严重依赖这些描述来决定何时使用哪个工具。
    ```python
    from llama_index.core.tools import QueryEngineTool

    # query_engine_tools = [
    #     QueryEngineTool.from_defaults(
    #         query_engine=lyft_engine,
    #         name="lyft_10k_financials_2021",
    #         description=(
    #             "提供关于Lyft公司2021年度的财务信息。"
    #             "使用一个详细的纯文本问题作为工具的输入。"
    #         ),
    #     ),
    #     QueryEngineTool.from_defaults(
    #         query_engine=uber_engine,
    #         name="uber_10k_financials_2021",
    #         description=(
    #             "提供关于Uber公司2021年度的财务信息。"
    #             "使用一个详细的纯文本问题作为工具的输入。"
    #         ),
    #     ),
    # ]
    ```

### 3. 配置 ReAct Agent

*   **初始化 Agent**: 使用 `ReActAgent` 类（在示例中是 `llama_index.core.agent.workflow.ReActAgent`，这似乎是新版或特定版本的路径，通常也可能是 `llama_index.core.agent.ReActAgent`），传入创建的查询引擎工具列表和 LLM。
    ```python
    from llama_index.core.agent import ReActAgent # 或者根据实际版本调整路径
    from llama_index.llms.openai import OpenAI

    # llm = OpenAI(model="gpt-4o-mini")
    # agent = ReActAgent(
    #     tools=query_engine_tools,
    #     llm=llm,
    #     verbose=True # 推荐用于调试
    # )
    ```
*   **可选的系统提示 (`system_prompt`)**: 可以为 Agent 提供一个可选的系统提示，该提示会附加到核心 ReAct 系统提示中，用以进一步指导 Agent 的行为或提供特定任务的上下文。
*   **上下文管理 (`Context`)**: 虽然此示例中 `Context` 主要用于持有会话/状态，但对于 ReAct Agent 来说，它不像 `AgentWorkflow` 中那样被工具直接修改。不过，如果需要跨多次 Agent 调用保持状态，`Context` 仍然有用。
    ```python
    from llama_index.core.workflow import Context # 或者根据实际版本调整路径
    # ctx = Context(agent)
    ```

### 4. 运行查询与观察 Agent 行为

*   **清晰的问题表述**: 向 Agent 提出的问题应该足够清晰，以便 Agent 能够理解并选择合适的查询引擎工具。
*   **流式响应 (`stream_events()`)**: 强烈建议使用流式响应来观察 Agent 的完整思考过程，包括它选择的工具、工具的输入、以及从工具返回的观察结果。这对于理解 Agent 的决策逻辑和调试非常重要。
    ```python
    # from llama_index.core.agent.workflow import AgentStream # 或相应事件类型

    # handler = agent.run("Lyft在2021年的收入增长是多少？", ctx=ctx)
    # async for ev in handler.stream_events():
    #     if isinstance(ev, AgentStream): # 根据实际事件类型调整
    #         print(f"{ev.delta}", end="", flush=True)
    # response = await handler
    ```
*   **Agent 的推理能力**: ReAct Agent 会根据用户问题和每个 `QueryEngineTool` 的描述来推理应该使用哪个工具来回答问题。如果问题需要多个数据源的信息（例如，比较 Uber 和 Lyft 的收入），Agent 应该能够依次调用相应的工具收集信息，然后进行整合和分析。

### 5. 设计有效的工具描述

*   **特异性**: 描述应尽可能具体地说明工具能做什么，覆盖什么样的数据范围（例如，特定公司、特定年份、特定类型的信息）。
*   **清晰的输入指令**: 明确告知 Agent 输入应该是什么样的（例如，"一个详细的纯文本问题"）。
*   **关键词**: 包含用户可能会用到的，或者与数据内容紧密相关的关键词，有助于 Agent 进行匹配。

### 6. 迭代与调试

*   **从小处着手**: 先用一两个查询引擎工具测试 Agent 的行为。
*   **检查 Agent 的思考过程**: `verbose=True` 和流式事件对于调试至关重要。观察 Agent 的 "Thought" 过程，看它是否正确理解了问题，是否根据工具描述做出了合理的工具选择。
*   **优化工具描述**: 如果 Agent 经常选择错误的工具，或者无法有效利用工具，首先应该检查和优化工具的描述。

---
