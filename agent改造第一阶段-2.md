您说得对，当前 `AutoFlowAgent` 的实现确实存在一些基础问题，导致它基本不可用。在重构过程中，我会特别注意LlamaIndex Agent和Tool的正确使用方法。

这是一个重构计划的Checklist，重点标记了需要特别注意Agent和Tool正确用法的地方：

**重构计划 Checklist**

**Phase 0: 基础工具修复与验证 (当前)**

*   **[ ] 工具: `__init__` 方法修复**
    *   **[ ] `KnowledgeRetrievalTool`**: 确认直接设置 `self._metadata = ToolMetadata(...)`，移除或正确调用 `super().__init__`，解决 `object.__init__` 错误。
    *   **[ ] `KnowledgeGraphQueryTool`**: 同上。
    *   **[ ] `ResponseGeneratorTool`**: 同上。
    *   **[ ] `DeepResearchTool`**: 同上。
    *   **[ ] `SQLQueryToolAdapter`**: 同上，并确保抽象方法问题解决。
*   **[ ] 工具: `metadata` 属性修复**
    *   **[ ] 所有工具**: 确保 `@property def metadata(self) -> ToolMetadata:` 正确返回 `self._metadata` (或 `BaseTool` 提供的机制)。
    *   **[Critical] 注意**: `ToolMetadata` 对象必须包含 `name` (字符串) 和 `description` (字符串)。`name` 是Agent调用工具时使用的标识符。`description` 帮助LLM理解工具的功能。
*   **[ ] Agent: `AutoFlowAgent._initialize_tools()`**
    *   **[Critical] 注意**: 此方法必须返回一个 `List[BaseTool]`，其中每个工具都已正确实例化并通过了上述 `__init__` 和 `metadata` 检查。
*   **[ ] Agent: `AutoFlowAgent._initialize_agent()`**
    *   **[Critical] 注意**: `ReActAgent.from_tools(tools=..., llm=..., system_prompt=...)` 中的 `tools` 参数必须是包含有效工具对象的列表。如果工具列表为空或工具无效，Agent将无法工作。
*   **[ ] Agent: `AutoFlowAgent.chat()` 调用修复**
    *   **[ ]** 确认 `self.agent.chat(message=self.user_question, chat_history=self.chat_history)` 的参数类型和Agent期望一致，解决Pydantic错误。
    *   **[Critical] 注意**: `ReActAgent.chat()` (同步版本) 通常返回一个 `AgentChatResponse` 对象，其 `response.response` 属性包含最终的文本回复，`response.sources` (如果工具生成了) 包含源信息。 `stream_chat()` 则返回一个生成器。
*   **[ ] 测试: 基本Agent调用**
    *   **[ ]** 在修复上述问题后，运行一个简单的用户查询，观察日志中Agent的思考过程 (`Thought: ... Action: ToolName Action Input: ... Observation: ...`)。
    *   **[ ]** 确保Agent至少能尝试调用一个工具，并且工具能执行（即使只是返回模拟数据）。

**Phase 1: 核心检索与生成流程的Agent化**

*   **[ ] 工具: `KnowledgeRetrievalTool.__call__`**
    *   **[Critical] 注意**: 输入参数应符合Agent的 `Action Input` (通常是字符串或简单JSON)。输出应是Agent可以理解的格式（通常是字符串形式的观察结果）。`ChatFlow` 中复杂的对象可能需要序列化或简化。
*   **[ ] 工具: `ResponseGeneratorTool.__call__`**
    *   **[Critical] 注意**: 输入参数需要包含从前一个工具（如 `KnowledgeRetrievalTool`）传递过来的上下文。Agent的系统提示或ReAct的思考过程需要指导它如何从 `Observation` 中提取上下文并作为 `Action Input` 传递给此工具。
*   **[ ] Agent: `ChatCoordinatorAgent_V1` 系统提示**
    *   **[Critical] 注意**: 提示词需要清晰地列出可用工具的 `name` 和 `description` (与 `ToolMetadata` 一致)。
    *   **[Critical] 注意**: 提示词需要明确指导Agent如何按顺序使用工具，以及如何处理工具的输出。例如："First, use 'knowledge_retrieval' with the user's question. Then, take the observation from 'knowledge_retrieval' and use it with the original question as input to 'response_generator'."
*   **[ ] Agent: `AutoFlowAgent` 更新**
    *   **[ ]** 确保 `_initialize_tools` 只加载此阶段所需的工具。
    *   **[ ]** 确保 `_initialize_agent` 使用新的 `ChatCoordinatorAgent_V1` 的系统提示。
*   **[ ] 测试: 端到端流程**
    *   **[ ]** 测试简单问答，验证Agent是否按预期调用工具链。

**Phase 2: 引入问题预处理和可选工具**

*   **[ ] 工具: `QuestionRefinementTool.__call__`**
    *   **[Critical] 注意**: 设计清晰的输入（原始问题，聊天历史）和输出（优化后的问题）。
*   **[ ] Agent: `ChatCoordinatorAgent_V2` 系统提示**
    *   **[Critical] 注意**: 更新提示词，加入新工具及其使用场景的描述。
    *   **[Critical] 注意**: 提示词需要包含决策逻辑，指导Agent何时选择调用 `QuestionRefinementTool`, `SQLQueryToolAdapter`, 或 `DeepResearchTool`。例如："If the user question is vague, first use 'question_refinement_tool'. If the refined question seems to require database information, use 'sql_query'. If initial retrieval is insufficient for a complex question, use 'deep_research_tool'."
*   **[ ] 测试: 条件性工具调用**
    *   **[ ]** 设计不同类型的查询，测试Agent是否能根据提示正确决策并调用合适的工具。

**Phase 3: 工作流编排 (Workflow/Pipeline)**

*   **[ ] `QueryPipeline` 设计**
    *   **[Critical] 注意**: 理解 `QueryPipeline` 中模块的输入/输出是如何通过 `ChainableMixin` 和 `Link` 连接的。每个模块的 `run()` 方法的签名很重要。
    *   **[Critical] 注意**: `InputComponent` 用于定义Pipeline的输入。
*   **[ ] `AgentWorkflow` 设计**
    *   **[Critical] 注意**: 理解 `AgentWorkflow` 如何管理状态并在Agent步骤之间传递数据。
    *   **[Critical] 注意**: Agent（作为工作流的一个步骤）的输出是什么，以及工作流如何根据这个输出来路由到下一个步骤。
*   **[ ] 事件生成对齐**
    *   **[ ]** 在Pipeline的模块或Workflow的步骤中，确保能发出与 `ChatFlow` 中类似的 `ChatEvent`，用于前端展示。

**Phase 4: 高级功能与优化**

*   **[ ] 流式处理**
    *   **[Critical] 注意**: 如果工具支持流式输出 (e.g., `ResponseGeneratorTool` 返回生成器)，Agent (如 `ReActAgent.stream_chat()`) 和工作流需要能正确处理和传递这些流。
*   **[ ] 错误处理**
    *   **[Critical] 注意**: 工具的 `__call__` 方法应包含 `try-except` 块，并将错误信息作为 `Observation` 的一部分返回给Agent，Agent需要能理解并处理这些错误。

**通用注意事项 (贯穿所有阶段):**

*   **[ ] LlamaIndex 版本兼容性**: 确保所使用的Agent、Tool和Workflow API与您项目中的LlamaIndex版本兼容。API可能会有变化。
*   **[ ] 文档查阅**: 在实现每个LlamaIndex组件（Agent, Tool, Pipeline, Workflow）时，**务必参考最新的LlamaIndex官方文档** (docs.llamaindex.ai) 以获取最准确的用法和示例。
*   **[ ] 日志**: 在Agent的决策点、工具的调用前后、工作流的步骤转换处添加非常详细的日志。这是调试Agent行为的关键。
*   **[ ] 简单到复杂**: 从最简单的Agent和工具组合开始，验证通过后再逐步增加复杂性。

我将严格遵循这个Checklist，并在每一步都仔细检查LlamaIndex组件的正确用法。首要任务是完成 **Phase 0**，确保我们有一个可运行的Agent基础。

请您在我执行每个修复步骤后，提供完整的测试日志，这样我们可以一起确认问题是否得到解决。
