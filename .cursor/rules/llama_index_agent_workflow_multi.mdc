---
description: 
globs: 
alwaysApply: false
---
# LlamaIndex Agent 最佳实践

## 多智能体工作流 (Multi-Agent Workflow)

本节基于"Multi-Agent Research Workflow with AgentWorkflow"示例，总结了构建和管理多智能体系统的最佳实践。

### 1. 系统设计与智能体角色定义

*   **明确角色与职责**: 为系统中的每个智能体定义清晰、专门的角色（例如，研究员 `ResearcherAgent`、评审员 `ReviewAgent`）。
    *   每个智能体应专注于一组特定的任务。
*   **定制化系统提示 (System Prompts)**: 为每个智能体编写独特的系统提示，以精确指导其行为、语气和决策过程，确保其符合预设的角色。
*   **专用工具集**: 为每个智能体配备与其角色和职责相关的特定工具。避免让一个智能体承担过多不相关的工具。
    ```python
    # 示例: 研究员 Agent
    research_agent = FunctionAgent(
        tools=[get_content_for_topic_tool, ...],
        llm=llm,
        system_prompt="你是一名研究员，负责根据主题搜集信息并撰写报告。"
    )

    # 示例: 评审员 Agent
    review_agent = FunctionAgent(
        tools=[review_report_tool, ...],
        llm=llm,
        system_prompt="你是一名评审员，负责审查报告的准确性和完整性。"
    )
    ```

### 2. Workflow 配置与智能体选择

*   **智能体列表**: 在 `AgentWorkflow` 初始化时，传入所有参与的智能体实例列表。
*   **智能体选择器 (Agent Selector)**: 使用智能体选择器来动态决定在工作流的每一步应激活哪个智能体。`LLMSelector` 是一个强大的选择，它允许一个LLM根据当前对话历史、任务状态和智能体的能力来选择下一个最合适的智能体。
    ```python
    from llama_index.core.agent.runner.selectors import LLMSelector

    workflow = AgentWorkflow(
        agents=[research_agent, review_agent],
        agent_selector=LLMSelector(
            llm=llm, # 通常是能力较强的 LLM，如 GPT-4
            agents=[research_agent, review_agent]
        ),
        initial_state={...}
    )
    ```
*   **共享初始状态 (Initial State)**: 定义一个所有智能体都可以访问和修改的共享初始状态。这对于在智能体之间传递信息和跟踪总体进度至关重要。
    ```python
    initial_workflow_state = {
        "research_topic": None,  # 由用户或初始步骤设定
        "report_content": None,  # 由 ResearcherAgent 生成
        "review_comments": None, # 由 ReviewAgent 生成
        "current_task_description": "用户初始请求"
    }
    # ... workflow = AgentWorkflow(..., initial_state=initial_workflow_state)
    ```

### 3. 智能体间的协作与任务交接

*   **通过共享状态协作**: 智能体通过读写共享的 `Context` 状态来进行隐式协作。一个智能体的输出（例如，研究报告）可以被存储在状态中，供下一个智能体（例如，评审员）使用。
*   **LLMSelector 驱动的交接**: 当使用 `LLMSelector` 时，任务交接由选择器 LLM 智能地管理。当前智能体完成其部分任务后，选择器 LLM 会分析当前状态和目标，然后决定下一个应该激活的智能体。
*   **明确的交接工具 (Optional but Recommended for Clarity)**: 虽然 `LLMSelector` 可以自动处理流程，但在某些情况下，可以为智能体设计一个明确的"交接"工具。当智能体调用此工具时，它表明其当前子任务已完成，并可能建议下一个接收者或任务阶段。这可以为 `LLMSelector` 提供更强的信号。
    ```python
    # 示例：研究员 Agent 可以有一个工具来表明研究已完成
    # async def research_complete_handoff(ctx: Context, summary: str) -> str:
    #     state = await ctx.get("state")
    #     state["current_task_description"] = f"研究报告已完成: {summary}。等待评审。"
    #     await ctx.set("state", state)
    #     return "研究报告已完成并提交评审。"
    # research_agent.add_tools([Tool.from_function(research_complete_handoff, ...)])
    ```
    (注意：上述交接工具是一个概念示例，实际文档中的 `LLMSelector` 会根据整体对话和工具输出来决定流程，不一定需要显式的 `handoff` 函数作为工具。关键在于智能体的输出和系统提示能引导 `LLMSelector` 做出正确决策。)

### 4. 多智能体环境下的工具设计与状态管理

*   **上下文感知工具**: 工具应设计为能够访问和修改共享的 `Context` (`ctx`)。
    *   工具的第一个参数应为 `ctx: Context`。
    *   使用 `await ctx.get("state")` 获取状态，并使用 `await ctx.set("state", updated_state)` 更新状态。
    ```python
    async def write_report(ctx: Context, topic: str, research_findings: str) -> str:
        report = f"关于 {topic} 的报告：\n{research_findings}"
        state = await ctx.get("state")
        state["report_content"] = report
        state["current_task_description"] = f"报告已撰写，主题：{topic}。"
        await ctx.set("state", state)
        return "报告已成功撰写并存入状态。"
    ```
*   **原子化工具**: 工具最好执行单一、明确的操作，使其易于被 LLM 理解和调用。
*   **状态更新的清晰性**: 当工具修改状态时，其返回消息应清晰地表明状态已更新，这有助于 `LLMSelector` 和开发者理解当前进展。

### 5. 运行与观察多智能体工作流

*   **启动工作流**: 与单智能体工作流类似，通过 `workflow.run()` (同步), `workflow.run_async()` (异步), 或 `workflow.stream_run()` (流式) 启动。
    ```python
    ctx = Context(workflow) # 初始化上下文，如果 workflow 有 initial_state
    response = await workflow.run_async(
        user_msg="请研究一下互联网的历史并生成一份报告，然后评审该报告。",
        ctx=ctx
    )
    ```
*   **监控与调试**: 利用事件流 (`stream_events()`) 来观察智能体之间的切换、工具调用和状态变化，这对于调试复杂的多智能体交互至关重要。
*   **最终状态检索**: 工作流完成后，最终的结果和中间产物（如报告、评审意见）可以从 `Context` 的状态中检索。
    ```python
    final_state = await ctx.get("state")
    final_report = final_state.get("report_content")
    review = final_state.get("review_comments")
    print(f"最终报告:\n{final_report}")
    print(f"评审意见:\n{review}")
    ```

### 6. 迭代与优化

*   **逐步构建**: 从简单的双智能体系统开始，逐步增加复杂性。
*   **测试智能体选择逻辑**: 重点测试 `LLMSelector` (或自定义选择器) 在不同场景下是否能正确选择下一个智能体。
*   **明确的错误处理与重试机制**: 考虑在工具或智能体层面加入错误处理和重试逻辑，尤其是在涉及外部 API 调用或复杂计算时。

---
