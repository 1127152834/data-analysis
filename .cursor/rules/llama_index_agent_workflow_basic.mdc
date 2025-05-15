---
description: 
globs: 
alwaysApply: false
---
# LlamaIndex Agent 最佳实践

## AgentWorkflow 基础介绍

本节涵盖了从 `AgentWorkflow` 基础介绍中提取的最佳实践。

### 1. Agent 与 Workflow 初始化

*   **清晰定义**: 设置 `AgentWorkflow` 时，清晰定义每个 Agent 的目的。这包括：
    *   指定 `FunctionAgent` 及其 `tools`。
    *   提供描述性的 `system_prompt` 来指导 Agent 的行为。
    *   使用如 `OpenAI(model="gpt-4o")` 这样强大的语言模型 (LLM)。
*   **Workflow 编排**: `AgentWorkflow` 类是管理 Agent 序列和交互的核心。
    ```python
    from llama_index.core.agent import AgentWorkflow, FunctionAgent
    from llama_index.llms.openai import OpenAI

    # 示例：定义一个 agent
    agent = FunctionAgent(
        tools=[tool_function],
        llm=OpenAI(model="gpt-4o"),
        system_prompt="你是一个乐于助人的助手。"
    )

    # 示例：创建一个 workflow
    workflow = AgentWorkflow(agents=[agent])
    ```
*   **上下文初始化 (Context Initialization)**: 对于需要维护状态或在步骤间传递数据的 workflow，初始化一个 `Context` 对象。
    *   如果需要，可以向 workflow 提供 `initial_state` 字典。
    ```python
    from llama_index.core.workflow import Context

    # 带有初始状态
    workflow_with_state = AgentWorkflow(
        agents=[agent_using_state],
        initial_state={"key": "initial_value"}
    )
    ctx = Context(workflow_with_state)
    ```

### 2. 运行 Agent 和处理响应

*   **同步执行**: 适用于等待完整响应的简单请求-响应交互。
    ```python
    response = workflow.run(user_msg="你的查询")
    print(str(response))
    ```
*   **异步执行与流式处理**: 适用于实时输出和观察中间步骤，使用异步执行和事件流。
    *   将工具和 workflow 方法定义为 `async`。
    *   使用 `await workflow.run_async(...)` 或 `workflow.stream_run(...)`。
    *   使用 `async for event in handler.stream_events():` 遍历事件。
    *   处理不同类型的事件 (`AgentStream`, `AgentInput`, `AgentOutput`, `ToolCall`, `ToolCallResult`) 以获取 workflow 执行的详细信息。
    ```python
    # 示例：流式事件
    # handler = await workflow.run_async(user_msg="你的查询", ctx=ctx) # 如果使用 context
    handler = workflow.stream_run(user_msg="你的查询") # 或者 stream_run
    async for event in handler.stream_events():
        if isinstance(event, AgentStream):
            print(event.delta, end="", flush=True)
        # 根据需要处理其他事件类型
    ```

### 3. Workflow 中的状态管理

*   **访问上下文 (Accessing Context)**: 需要与 workflow 共享状态交互的工具，必须接受 `Context` 作为其第一个参数。
*   **读写状态**:
    *   使用 `state = await ctx.get("state")` 来检索当前状态。
    *   修改状态字典。
    *   使用 `await ctx.set("state", state)` 来更新上下文中的状态。
    ```python
    from llama_index.core.workflow import Context

    async def tool_modifying_state(ctx: Context, new_value: str) -> str:
        state = await ctx.get("state")
        state["some_key"] = new_value
        await ctx.set("state", state)
        return f"状态已更新为 {new_value}"
    ```
*   **上下文序列化 (Context Serialization)**: `Context` 对象是可序列化的，这对于以下情况至关重要：
    *   持久化 workflow 状态。
    *   实现长时间运行的任务。
    *   处理可能异步发生的人机交互 (human-in-the-loop)。
    *   使用 `ctx.to_dict(serializer=JsonSerializer())` 保存和 `Context.from_dict(agent, ctx_dict, serializer=JsonSerializer())` 恢复。
    *   **注意**: 当 workflow 被恢复时，任何正在进行的函数/步骤都将从头开始。

### 4. 定义和使用工具

*   **工具签名**: 工具是 Agent 可以执行的 Python 函数 (可以是 `async`)。
*   **目的明确的工具**: 设计工具以执行特定的、定义明确的任务。
*   **有状态的工具**: 如果工具需要访问或修改共享的 workflow 数据，确保它接受 `ctx: Context` 作为其第一个参数。

### 5. 实现人机交互 (Human-in-the-Loop, HITL)

*   **标记输入需求**: 使用 `InputRequiredEvent` 来表明 workflow 需要人工输入。
*   **等待响应**: `ctx.wait_for_event(HumanResponseEvent, ...)` 方法会暂停 workflow，直到收到相应的 `HumanResponseEvent`。
    *   `waiter_id`: 等待操作的唯一标识符，通常是被提出的问题。
    *   `waiter_event`: 要发出的事件 (例如, `InputRequiredEvent`)。
    *   `requirements`: `HumanResponseEvent` 必须满足的条件 (例如, 匹配的 `user_name`)。
*   **发送人工响应**: 外部系统 (或用户界面) 通过 `handler.ctx.send_event(...)` 将 `HumanResponseEvent` 发送回 workflow 的上下文中。
    ```python
    from llama_index.core.workflow import InputRequiredEvent, HumanResponseEvent

    async def dangerous_task_requiring_confirmation(ctx: Context) -> str:
        question = "您确定要继续吗？"
        response_event = await ctx.wait_for_event(
            HumanResponseEvent,
            waiter_id=question,
            waiter_event=InputRequiredEvent(prefix=question, user_name="user_id_example"),
            requirements={"user_name": "user_id_example"},
        )
        if response_event.response.lower() == "yes":
            return "任务已执行。"
        else:
            return "任务被用户中止。"

    # 在事件处理循环中:
    # if isinstance(event, InputRequiredEvent):
    #     user_response = input(event.prefix) # 从用户获取输入
    #     handler.ctx.send_event(
    #         HumanResponseEvent(response=user_response, user_name=event.user_name)
    #     )
    ```
*   **生产环境中的 HITL**: 对于生产系统，人工交互可能通过单独的 API 调用或 WebSocket 连接进行。利用上下文的序列化和恢复来管理这些异步交互。

---
