### LlamaIndex PandasQueryEngine 最佳实践

**核心功能**:
*   `PandasQueryEngine` 允许用户使用自然语言查询 Pandas DataFrame。
*   它将自然语言查询转换为可执行的 Python 代码 (Pandas DataFrame 操作)，在 DataFrame 上执行该代码，并返回结果。
*   可以选择直接返回 Pandas 操作的输出，或者通过 LLM 进一步合成更自然的语言响应。

**主要应用场景**:
*   当数据存储在 Pandas DataFrame 中，并且希望通过自然语言进行数据查询、分析和提取时。
*   例如："人口最多的城市是哪个？" 或 "计算生存率与年龄之间的相关性。"

**核心组件与实施流程**:
1.  **准备 Pandas DataFrame**:
    *   加载或创建一个 Pandas DataFrame 作为查询目标。
    *   例如：`df = pd.DataFrame({"city": ["Toronto", "Tokyo"], "population": [2930000, 13960000]})`

2.  **初始化 `PandasQueryEngine`**:
    *   实例化 `PandasQueryEngine`，传入 DataFrame。
    *   `query_engine = PandasQueryEngine(df=your_dataframe, verbose=True)`
    *   **关键参数**:
        *   `df` (Pandas DataFrame, 必需): 要查询的 DataFrame。
        *   `llm` (LLM, 可选): 用于将自然语言转换为 Pandas 命令以及合成响应的语言模型。默认为 OpenAI gpt-3.5-turbo。
        *   `pandas_prompt` (PromptTemplate, 可选): 自定义用于生成 Pandas 命令的提示模板。
        *   `instruction_str` (str, 可选): 在 `pandas_prompt` 中使用的指令字符串，指导 LLM 如何转换查询。默认为一组预定义指令，强调生成可 `eval()` 的 Python 表达式。
        *   `output_processor` (Callable, 可选): 一个函数，用于后处理 `eval()` 执行 Pandas 命令后的输出。
        *   `synthesize_response` (bool, 默认为 `False`): 是否使用 LLM 将 Pandas 输出合成为自然语言响应。如果为 `False` (默认)，直接返回 Pandas 操作的输出。如果为 `True`，则会使用 `response_synthesis_prompt` 来生成最终答案。
        *   `response_synthesis_prompt` (PromptTemplate, 可选): 当 `synthesize_response=True` 时，用于合成最终自然语言响应的提示模板。
        *   `verbose` (bool, 默认为 `False`): 是否打印中间生成的 Pandas 指令和输出，便于调试。
        *   `service_context` (ServiceContext, 可选): 服务上下文，用于配置 LLM、嵌入模型等。
        *   `head` (int, 默认为 5): DataFrame 的 `head(n)` 输出行数，用于在提示中向 LLM 展示 DataFrame 的结构。

3.  **查询执行**:
    *   调用查询引擎的 `query("你的自然语言问题")` 方法。
    *   `response = query_engine.query("What is the city with the highest population?")`
    *   引擎内部流程：
        1.  LLM 根据 `pandas_prompt` 和 `instruction_str` 将自然语言查询转换为 Pandas Python 代码字符串。
        2.  使用 `eval()` 执行该 Python 代码字符串。
        3.  (如果 `synthesize_response=True`) LLM 根据 `response_synthesis_prompt` 和 Pandas 输出合成自然语言响应。
        4.  返回结果 (Pandas 输出或合成的自然语言响应)。

**重要注意事项与最佳实践**:
*   **Prompt 定制**: 
    *   `instruction_str` 是控制 LLM 生成 Pandas 代码的关键。默认指令强调生成单行可 `eval()` 的表达式。根据需求，可以修改指令以支持更复杂的代码块或不同的输出格式。
    *   通过 `get_prompts()` 方法可以获取当前的提示模板 (`pandas_prompt`, `response_synthesis_prompt`)，并通过 `update_prompts()` 更新它们。
*   **LLM 的能力**: 生成准确的 Pandas 代码高度依赖 LLM 的能力。更强大的 LLM 通常能更好地理解查询意图并生成正确的代码。
*   **DataFrame 的上下文**: LLM 通过 `df.head()` 的输出来理解 DataFrame 的结构。确保 `head` 参数能提供足够代表性的列信息。
*   **安全性**: 由于引擎使用 `eval()` 执行 LLM 生成的代码，这存在潜在的安全风险，特别是当 DataFrame 或查询来源不可信时。应在受控环境中使用。
*   **错误处理与调试**: 设置 `verbose=True` 可以看到 LLM 生成的 Pandas 指令和中间输出，有助于调试 LLM 未能正确理解查询或生成错误代码的情况。
*   **`synthesize_response` 的使用**: 
    *   如果只需要直接的 Pandas 输出 (例如，一个值、一个 Series 或一个 DataFrame)，将 `synthesize_response` 设为 `False` 更高效。
    *   如果需要一个解释性的自然语言答案，则设为 `True`。
*   **复杂查询**: 对于非常复杂的查询，可能需要分解问题或优化 `instruction_str` 和 `pandas_prompt`。
*   **查询管道语法**: 对于更高级的定制，可以参考使用查询管道 (Query Pipeline) 语法从头构建类似的 Pandas 查询引擎的文档。

**返回对象**:
*   查询结果 (`response`) 是一个 `Response` 对象。
*   `response.response`: 包含最终的答案 (Pandas 输出或合成的文本)。
*   `response.metadata`: 一个字典，包含额外信息，例如：
    *   `"pandas_instruction_str"`: LLM 生成的 Pandas Python 代码字符串。
    *   `"raw_pandas_output"`: Pandas 代码执行后的原始输出 (在 `synthesize_response=True` 时有用)。
