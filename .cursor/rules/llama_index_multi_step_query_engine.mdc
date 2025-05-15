### LlamaIndex MultiStepQueryEngine 最佳实践

**核心功能**:
*   `MultiStepQueryEngine` 能够将一个复杂的自然语言查询分解为一系列连续的、更简单的子问题。
*   它首先使用一个查询转换模块 (`query_transform`，例如 `StepDecomposeQueryTransform`) 来生成子问题。
*   然后，它按顺序执行这些子问题，并将前一个子问题的答案作为上下文信息融入到下一个子问题的生成或执行中。
*   最终，它会综合所有子问题的答案来形成对原始复杂问题的回答。

**主要应用场景**:
*   当原始查询过于复杂，直接在索引上查询难以获得精确或完整答案时。
*   当回答一个问题需要多个逻辑步骤或依赖于先前推断出的信息时。
    *   例如："作者创办的加速器项目的第一批成员都有谁？" 这可能会被分解为："谁是作者？" -> "作者创办了哪个加速器项目？" -> "这个项目的第一批成员是谁？"
*   适用于需要进行推理链 (Chain-of-Thought) 或逐步细化查询的场景。

**核心组件与实施流程**:
1.  **准备基础查询引擎 (`query_engine`)**: 
    *   首先需要一个能够处理简单查询的基础查询引擎，通常是通过 `VectorStoreIndex.as_query_engine()` 创建的。
    *   这个引擎将负责执行分解后的各个子问题。

2.  **初始化查询转换模块 (`query_transform`)**: 
    *   `StepDecomposeQueryTransform` 是一个关键组件，负责将复杂问题分解为子问题。
    *   **关键参数**:
        *   `llm` (LLM): 用于驱动问题分解的大语言模型。文档示例中分别使用了 GPT-4 和 GPT-3.5，GPT-4 通常在问题分解的质量上表现更好。
        *   `verbose` (布尔值): 设置为 `True` 可以在执行过程中打印出分解的子问题和中间步骤，便于调试。

3.  **初始化 `MultiStepQueryEngine`**:
    *   `query_engine = MultiStepQueryEngine(query_engine=base_query_engine, query_transform=step_decompose_transform, index_summary="描述索引内容的摘要")`
    *   **关键参数**:
        *   `query_engine`: 步骤 1 中准备的基础查询引擎。
        *   `query_transform`: 步骤 2 中初始化的查询转换模块。
        *   `index_summary` (字符串, 可选但推荐): 对索引内容的简要描述。这有助于 `StepDecomposeQueryTransform` 更好地理解上下文，并生成更相关的子问题。例如："用于回答关于作者（保罗·格雷厄姆）的问题"。
        *   `num_steps` (整数, 可选): 限制问题分解的最大步数。

4.  **执行查询**: 
    *   调用 `MultiStepQueryEngine` 的 `query()` 方法并传入复杂的自然语言查询。
    *   响应对象 (`response`) 的 `metadata["sub_qa"]` 属性会包含分解出的子问题及其各自的答案，这对于理解引擎的决策过程非常有用。

**最佳实践与注意事项**:
*   **LLM 选择**: 问题分解的质量高度依赖于 `StepDecomposeQueryTransform` 中使用的 LLM。更强大的 LLM (如 GPT-4) 通常能产生更合理、更有效的子问题序列。
*   **`index_summary`的重要性**: 提供清晰且相关的 `index_summary` 可以显著提高子问题生成的准确性。
*   **详细日志 (`verbose=True`)**: 在开发和调试阶段，将 `StepDecomposeQueryTransform` 的 `verbose` 参数设置为 `True`，可以观察到完整的问题分解过程和中间查询，有助于诊断问题。
*   **结果解析**: 检查 `response.metadata["sub_qa"]` 可以帮助理解引擎是如何逐步得到最终答案的，并验证每一步的正确性。
*   **迭代优化**: 如果发现分解的子问题不理想，可以尝试调整 `index_summary` 的内容，或更换/微调用于问题分解的 LLM 的提示 (如果 LlamaIndex 版本支持更底层的提示定制)。
*   **与 `SubQuestionQueryEngine` 的区别**: 
    *   `MultiStepQueryEngine` 处理的是需要*顺序*依赖、逐步解决的复杂问题，前一步的输出会影响后一步。
    *   `SubQuestionQueryEngine` 更侧重于将一个复杂问题分解为多个可以*并行*查询不同数据源 (工具) 的子问题，然后汇总结果。
