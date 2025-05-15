# LlamaIndex Agent - Controlling Reasoning Loop with Return Direct Tools 最佳实践

本节总结了使用 LlamaIndex `FunctionTool` 的 `return_direct=True` 参数来控制 Agent 推理循环的最佳实践，基于 "Controlling Agent Reasoning Loop with Return Direct Tools" 示例。

### 1. `return_direct=True` 的核心概念

*   **目的**: 当一个工具的输出本身就是用户期望的最终答案，或者不需要经过 LLM 进一步处理或润色时，可以将该工具的 `return_direct` 参数设置为 `True`。
*   **行为**: 设置为 `True` 后，一旦 Agent 调用该工具并获得结果，这个结果将直接作为 Agent 的最终响应返回给用户。Agent 的推理循环会在此处停止，不会再进行后续的思考步骤或调用 LLM 生成最终答案。
*   **适用场景**:
    *   **信息确认类工具**: 例如，创建预订、确认操作、执行一个明确的动作后返回成功/失败信息。
    *   **直接数据获取**: 当工具的输出是格式化数据或用户直接请求的信息片段时。
    *   **避免不必要的LLM调用**: 当工具的原始输出已经足够清晰和完整时，可以节省 LLM 的调用成本和时间。

### 2. 工具设置 (Tools Setup)

*   **定义普通工具**: 正常定义你的 `FunctionTool`，这些工具的执行结果会返回给 Agent 进行下一步的思考。
    ```python
    from llama_index.core.tools import FunctionTool
    from pydantic import BaseModel

    # 示例数据模型和存储
    # class Booking(BaseModel):
    #     name: str = None
    #     email: str = None
    #     # ...其他字段
    # bookings = {}

    # def get_booking_state(user_id: str) -> str:
    #     """Get the current state of a booking for a given booking ID."""
    #     # ...实现
    # get_booking_state_tool = FunctionTool.from_defaults(fn=get_booking_state)

    # def update_booking(user_id: str, property: str, value: str) -> str:
    #     """Update a property of a booking for a given booking ID."""
    #     # ...实现
    # update_booking_tool = FunctionTool.from_defaults(fn=update_booking)
    ```
*   **定义 `return_direct=True` 的工具**: 在创建 `FunctionTool` 时，设置 `return_direct=True`。
    ```python
    # def create_booking(user_id: str) -> str:
    #     """Create a new booking and return the booking ID. Asks for more details."""
    #     bookings[user_id] = Booking()
    #     return "Booking created, but not yet confirmed. Please provide your name, email, phone, date, and time."
    # create_booking_tool = FunctionTool.from_defaults(
    #     fn=create_booking,
    #     return_direct=True # 核心设置
    # )

    # def confirm_booking(user_id: str) -> str:
    #     """Confirm a booking for a given booking ID if all details are present."""
    #     # ... (检查所有必要字段)
    #     # if all_details_present:
    #     #     return f"Booking ID {user_id} confirmed!"
    #     # else:
    #     #     raise ValueError("Missing details for booking.")
    # confirm_booking_tool = FunctionTool.from_defaults(
    #     fn=confirm_booking,
    #     return_direct=True # 核心设置
    # )
    ```
*   **工具描述**: 即使 `return_direct=True`，工具的描述（docstring）依然重要，因为它帮助 Agent 理解何时选择这个工具。

### 3. Agent 设置

*   **Agent 类型**: 该示例使用的是 `FunctionAgent` (来自 `llama_index.core.agent.workflow`)。这个特性通常适用于能够进行工具选择的 Agent 类型（如 `ReActAgent`, `FunctionAgent`)。
*   **系统提示 (`system_prompt`)**: 根据应用场景定制系统提示，指导 Agent 的行为。在示例中，系统提示强调 Agent 应该只使用用户明确提供的信息。
    ```python
    # from llama_index.llms.anthropic import Anthropic
    # from llama_index.core.agent.workflow import FunctionAgent
    # from llama_index.core.workflow import Context

    # llm = Anthropic(model="claude-3-sonnet-20240229") # 或其他 LLM
    # user = "user123"
    # system_prompt = f"""You are now connected to the booking system and helping {user} with making a booking.
    # Only enter details that the user has explicitly provided.
    # Do not make up any details.
    # """

    # agent = FunctionAgent(
    #     tools=[
    #         get_booking_state_tool,
    #         update_booking_tool,
    #         create_booking_tool, # return_direct tool
    #         confirm_booking_tool, # return_direct tool
    #     ],
    #     llm=llm,
    #     system_prompt=system_prompt,
    # )
    # ctx = Context(agent) # 用于维护会话状态
    ```

### 4. 运行与交互

*   **调用 Agent**: 使用 `agent.run()` (或其异步/流式版本) 与 Agent 交互。
*   **观察行为**: 当 Agent 调用一个 `return_direct=True` 的工具时：
    *   Agent 会进行思考，选择该工具并提供输入。
    *   工具执行。
    *   工具的输出**直接**作为最终响应返回。
    *   不会有后续的 LLM 调用来处理或改写这个工具的输出。
    ```python
    # from llama_index.core.agent.workflow import AgentStream, ToolCallResult

    # # 示例：用户请求创建预订
    # handler = agent.run(
    #     "Hello! I would like to make a booking, around 5pm?", ctx=ctx
    # )
    # async for ev in handler.stream_events():
    #     if isinstance(ev, AgentStream):
    #         print(f"{ev.delta}", end="", flush=True)
    #     elif isinstance(ev, ToolCallResult):
    #         # 可以观察到工具被调用及其原始输出
    #         print(f"\nCall {ev.tool_name} with {ev.tool_kwargs}\nReturned: {ev.tool_output}")
    # response = await handler
    # print(str(response)) # 此处 response 将是 create_booking_tool 的直接输出
    ```

### 5. 何时使用 `return_direct=True`

*   **明确的指令性任务**: 当用户指令导致一个工具执行一个动作，并且该工具的返回消息就是对该动作的确认或结果时（例如，"预订已创建"，"文件已上传"）。
*   **避免冗余LLM思考**: 如果一个工具的输出已经是完整、准确且用户友好的，再次通过LLM处理可能会增加延迟和成本，甚至可能引入不必要的改写。
*   **流程控制**: 在更复杂的 Agent 逻辑中，`return_direct` 可以作为一种控制机制，确保在特定步骤后，Agent 停止并等待外部系统的进一步指令或用户的下一步输入。

### 6. 注意事项

*   **工具输出的清晰度**: 由于工具的输出将直接展示给用户，确保这些输出信息是清晰、完整且易于理解的。
*   **错误处理**: 在 `return_direct=True` 的工具内部进行适当的错误处理。如果工具抛出异常，这个异常可能会直接传递给 Agent 的调用者，或者导致 Agent 流程中断，具体取决于 Agent 的实现。
*   **与Agent类型的兼容性**: 确保所使用的 Agent 类型支持并正确处理 `return_direct` 工具。大多数现代的、支持工具调用的 LlamaIndex Agent (如 `FunctionAgent`, `ReActAgent`) 应该能处理。

---
