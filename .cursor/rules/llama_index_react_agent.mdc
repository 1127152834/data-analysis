# LlamaIndex ReAct Agent 最佳实践

本节总结了使用 LlamaIndex ReAct (Reasoning and Acting) Agent 的最佳实践，基于 "ReAct Agent - A Simple Intro with Calculator Tools" 示例。

### 1. ReAct Agent 初始化

*   **LLM选择**: 为 ReAct Agent 选择一个合适的 LLM。示例中使用的是 `OpenAI(model="gpt-4o")`。
*   **工具定义**: 定义一组 `FunctionTool`。这些工具是 Agent 用来与外部世界交互或执行计算的函数。
    *   每个工具应该有清晰的函数签名和文档字符串 (docstring)，以便 Agent 理解其功能和参数。
    ```python
    from llama_index.core.tools import FunctionTool

    def add(a: int, b: int) -> int:
        """Add two integers and returns the result integer"""
        return a + b
    add_tool = FunctionTool.from_defaults(fn=add)

    def multiply(a: int, b: int) -> int:
        """Multiply two integers and returns the result integer"""
        return a * b
    multiply_tool = FunctionTool.from_defaults(fn=multiply)
    ```
*   **Agent创建**: 使用 `ReActAgent.from_tools` 方法创建 Agent 实例，传入工具列表和 LLM。
    *   可以设置 `verbose=True` 来查看 Agent 的思考过程。
    ```python
    from llama_index.core.agent import ReActAgent
    from llama_index.llms.openai import OpenAI

    llm = OpenAI(model="gpt-4o")
    agent = ReActAgent.from_tools(
        tools=[add_tool, multiply_tool],
        llm=llm,
        verbose=True
    )
    ```

### 2. ReAct Agent 的核心交互模式 (Thought, Action, Action Input, Observation)

*   **思考 (Thought)**: Agent首先会思考如何解决问题，以及是否需要使用工具。
*   **行动 (Action)**: 如果需要使用工具，Agent会指定要调用的工具名称。
*   **行动输入 (Action Input)**: Agent会以JSON格式提供工具所需的参数。
*   **观察 (Observation)**: Agent接收并处理工具执行的结果。
*   这个"Thought -> Action -> Action Input -> Observation"循环会持续进行，直到Agent认为它有足够的信息来回答用户的问题，或者认为无法回答。

### 3. 运行 Agent 与获取响应

*   **同步运行**: 使用 `agent.chat()` 或 `agent.query()` 方法。
    ```python
    response = agent.chat("20乘以5是多少？")
    print(response)
    ```
*   **异步运行与流式处理**: 使用 `agent.astream_chat()` 或 `agent.arun()`。
    *   通过迭代 `handler.stream_events()` 可以观察到 `AgentStream` 等事件，实时查看 Agent 的思考过程和工具调用细节。
    ```python
    # handler = await agent.astream_chat("5加3再加2等于多少？")
    # async for ev in handler.stream_events():
    #     if isinstance(ev, AgentStream):
    #         print(f"{ev.delta}", end="", flush=True)
    # response = await handler
    ```
    *(注意: `AgentStream` 事件在 `agent.run()` 的流式版本中可能需要特定处理才能按预期工作，文档中示例使用的是 `agent.run()` 配合 `stream_events()`，但 `chat` 模式有 `stream_chat`)*

### 4. Prompt 定制

*   **查看默认Prompt**: 使用 `agent.get_prompts()` 可以查看 Agent 内部使用的默认 Prompt 模板，特别是 `react_header`。
*   **更新Prompt**: 使用 `agent.update_prompts({"react_header": custom_prompt_template})` 可以替换默认的 ReAct 系统 Prompt。
    *   这允许开发者定制 Agent 的行为、输出格式、附加规则等。
    *   在定制 Prompt 时，需要确保保留必要的占位符，如 `{tool_desc}` 和 `{tool_names}`，并遵循 ReAct 的输出格式要求 (Thought, Action, Action Input, Answer)。
    ```python
    from llama_index.core import PromptTemplate

    custom_react_system_header_str = """
    你是一个专门进行数学运算的助手。
    ## 工具
    你有以下工具可用:
    {tool_desc}

    ## 输出格式
    请严格按照以下格式回答:
    Thought: 我需要使用一个工具来帮助我回答问题。
    Action: 工具名称 (必须是以下之一: {tool_names})
    Action Input: 工具的输入，JSON格式 (例如：{{"input": "hello world"}})
    Observation: 工具的响应
    ... (重复 Thought/Action/Action Input/Observation 直到可以回答)
    Thought: 我现在可以直接回答了。
    Answer: [你的答案]
    """
    custom_react_prompt = PromptTemplate(custom_react_system_header_str)
    # agent.update_prompts({"react_header": custom_react_prompt})
    ```
*   **Prompt中的关键指令**:
    *   清晰描述 Agent 的角色和任务。
    *   详细列出可用工具及其描述 (`{tool_desc}`)。
    *   明确指定输出格式，包括 `Thought`, `Action`, `Action Input`, 和最终的 `Answer`。
    *   强调 Action Input 必须是有效的 JSON。
    *   指导 Agent 在有足够信息后直接回答，并使用与用户相同的语言。

### 5. 工具设计与使用注意事项

*   **清晰的工具描述 (Docstrings)**: 工具的文档字符串对于 ReAct Agent 至关重要，因为 Agent 会根据这些描述来决定何时以及如何使用工具。
*   **参数类型提示**: 确保工具函数的参数有类型提示，这有助于 Agent 正确构造 Action Input。
*   **原子性**: 工具最好执行单一、明确的操作。

### 6. 详细模式 (Verbose Mode)

*   在创建 Agent 时设置 `verbose=True`，或者在运行时动态调整，可以帮助开发者理解 Agent 的每一步决策过程，包括其内部的思考、工具选择和观察结果。这对于调试和优化 Agent 非常有用。

---
