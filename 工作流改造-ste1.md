## 工作流改造实施计划与 Checklist

**总体目标**：根据 `工作流改造.md` 文档，全面升级 `backend` 应用，实现基于工具调用模式的智能工作流系统。

---

### **阶段一：基础框架搭建 - 工具与事件系统**

**目标**：建立符合 `工作流改造.md` 规范的工具基础类、工具注册器、事件定义和事件转换器。

**涉及文件**：

*   `backend/app/autoflow/tools/base.py`
*   `backend/app/autoflow/tools/registry.py`
*   `backend/app/autoflow/events/tool_events.py` (新建)
*   `backend/app/autoflow/events/converter.py` (新建)
*   `backend/app/autoflow/events.py` (将被废弃)

**Checklist 与验证**：

1.  **[ ] 创建 `backend/app/autoflow/events/tool_events.py`**
    *   **任务**: 复制 `工作流改造.md` 中 "1.3 工具调用事件" 部分的代码到此文件。
        *   包含 `EventType` 枚举。
        *   包含 `BaseEvent` 基类。
        *   包含 `ToolCallEvent`, `ToolResultEvent`, `StepEndEvent`, `InfoEvent`, `ErrorEvent`, `TextEvent` 类。
    *   **验证**:
        *   代码静态检查通过 (e.g., linter)。
        *   能够成功导入这些类和枚举。
        *   手动实例化每个事件类，检查字段是否符合预期。
        *   `ToolCallEvent`, `ToolResultEvent`, `StepEndEvent`, `InfoEvent`, `ErrorEvent`, `TextEvent` 的 `to_dict()` 方法存在且可调用。

2.  **[ ] 创建 `backend/app/autoflow/events/converter.py`**
    *   **任务**: 复制 `工作流改造.md` 中 "1.4 事件转换器" 部分的 `EventConverter` 类代码到此文件。
        *   确保导入路径正确 (如 `from app.rag.chat.stream_protocol import ChatEvent`, `from .tool_events import ...`)。
    *   **验证**:
        *   代码静态检查通过。
        *   能够成功导入 `EventConverter`。
        *   手动创建 `tool_events.py` 中的每种事件实例。
        *   调用 `EventConverter.to_chat_event()` 方法转换这些实例，检查返回的 `ChatEvent` 对象的 `event_type` 和 `payload` 是否符合 `工作流改造.md` 中定义的转换逻辑。

3.  **[ ] 规范化 `backend/app/autoflow/tools/base.py`**
    *   **任务**:
        *   读取现有 `backend/app/autoflow/tools/base.py` 内容 (如果存在)。
        *   对照 `工作流改造.md` 中 "1.1 基础工具接口" 部分的代码，确保 `ToolCallStatus`, `ToolParameters`, `ToolResult`, `BaseTool` 类完全一致。
        *   特别注意 `BaseTool` 的泛型定义 `Generic[P, R]`、构造函数、`execute` 抽象方法和 `get_metadata` 方法。
    *   **验证**:
        *   代码静态检查通过。
        *   能够成功导入这些类和枚举。
        *   能够创建一个继承自 `BaseTool` 的简单 mock 工具类（如下面单元测试中的 `SimpleTool`），并能实例化。
        *   `SimpleTool` 实例的 `get_metadata()` 方法返回的 JSON Schema 符合预期。

4.  **[ ] 规范化 `backend/app/autoflow/tools/registry.py`**
    *   **任务**:
        *   读取现有 `backend/app/autoflow/tools/registry.py` 内容 (如果存在)。
        *   对照 `工作流改造.md` 中 "1.2 工具注册器" 部分的 `ToolRegistry` 类代码，确保其单例模式、`register_tool`, `get_tool`, `list_tools`, `get_tools_metadata` 方法完全一致。
    *   **验证**:
        *   代码静态检查通过。
        *   能够成功导入 `ToolRegistry`。
        *   `ToolRegistry()` 多次调用返回同一实例。
        *   能够注册一个 mock 工具，并通过名称获取到它。
        *   `list_tools()` 和 `get_tools_metadata()` 返回预期的列表。

5.  **[ ] 编写阶段一单元测试 (参考 `工作流改造.md` 10.1 节)**
    *   **任务**: 在 `tests/autoflow/tools/test_tools.py` (如果尚不存在，则创建目录和文件) 中，实现类似文档中的 `test_tool_registration` 和 `test_tool_execution` (后者可以先针对一个非常简单的同步 mock 工具，异步部分待工具实现后再加强)。
    *   **验证**: 所有为阶段一编写的单元测试通过。

6.  **[ ] 废弃旧的 `backend/app/autoflow/events.py`**
    *   **任务**: 在确认新的 `events/tool_events.py` 和 `events/converter.py` 工作正常后，删除 `backend/app/autoflow/events.py` 或将其重命名/移动到归档位置。
    *   **验证**: 系统中不再引用旧的 `backend/app/autoflow/events.py`。后续代码导入事件时，均从 `backend/app/autoflow/events.tool_events` 或 `backend/app/autoflow/events.converter` 导入。


好的，我们继续制定后续阶段的计划。

---

### **阶段二：核心工具实现与注册**

**目标**：根据 `工作流改造.md` 的规范，实现所有核心工具 (`KnowledgeGraphTool`, `KnowledgeRetrievalTool`, `DatabaseQueryTool`, `FurtherQuestionsTool`)，并确保它们可以通过 `ToolRegistry` 正确注册。

**涉及文件**：

*   `backend/app/autoflow/tools/knowledge_graph_tool.py` (新建或修改)
*   `backend/app/autoflow/tools/knowledge_retrieval_tool.py` (新建或修改)
*   `backend/app/autoflow/tools/database_query_tool.py` (新建或修改)
*   `backend/app/autoflow/tools/further_questions_tool.py` (新建或修改)
*   `backend/app/autoflow/tools/init.py` (新建或修改)
*   `tests/autoflow/tools/test_tools.py` (扩展测试)

**Checklist 与验证**：

1.  **[ ] 实现/规范化 `KnowledgeGraphTool` (`backend/app/autoflow/tools/knowledge_graph_tool.py`)**
    *   **任务**:
        *   对照 `工作流改造.md` "4.1 知识图谱工具" 部分的代码。
        *   确保 `KnowledgeGraphParameters` 和 `KnowledgeGraphResult` 类定义正确。
        *   确保 `KnowledgeGraphTool` 类继承自 `BaseTool`，`__init__` 方法正确设置元数据。
        *   重点检查 `execute` 方法：
            *   参数类型为 `KnowledgeGraphParameters`，返回类型为 `KnowledgeGraphResult`。
            *   正确处理 `engine_config` 中知识图谱的启用状态。
            *   正确获取知识库 (`engine_config.get_knowledge_bases`)。
            *   正确导入和使用 `KnowledgeGraphFusionRetriever` 和 `KnowledgeGraphRetrieverConfig` (注意路径 `app.rag.retrievers.knowledge_graph...`)。
            *   `_run_async` 方法用于异步执行同步的LlamaIndex调用。
            *   正确处理意图搜索 (`using_intent_search`) 和普通搜索的上下文生成逻辑。
            *   错误处理和日志记录。
    *   **验证**:
        *   代码静态检查通过。
        *   单元测试（mock `engine_config`, `db_session`, `KnowledgeGraphFusionRetriever` 等依赖）：
            *   测试工具在知识图谱未启用时返回空结果。
            *   测试在获取不到知识库时返回错误。
            *   测试工具能正确调用 `KnowledgeGraphFusionRetriever.retrieve_knowledge_graph`。
            *   测试上下文生成逻辑（意图和普通模式）。
            *   测试返回的 `KnowledgeGraphResult` 结构和内容正确。
            *   测试异常情况下的错误返回。

2.  **[ ] 实现/规范化 `KnowledgeRetrievalTool` (`backend/app/autoflow/tools/knowledge_retrieval_tool.py`)**
    *   **任务**:
        *   对照 `工作流改造.md` "4.2 知识库检索工具" 部分的代码。
        *   确保 `KnowledgeRetrievalParameters` 和 `KnowledgeRetrievalResult` 类定义正确。
        *   确保 `KnowledgeRetrievalTool` 类继承自 `BaseTool`，`__init__` 方法正确。
        *   重点检查 `execute` 方法：
            *   正确获取知识库。
            *   正确导入和使用 `ChunkFusionRetriever` (注意路径 `app.rag.retrievers.chunk.fusion_retriever`)。
            *   `_run_async` 方法用于异步执行 `retriever.retrieve`。
            *   正确处理和转换检索到的节点 (`NodeWithScore`, `Node`, `dict` 类型) 为 `KnowledgeRetrievalResult` 中的 `nodes` 和 `sources`。
            *   错误处理和日志记录。
    *   **验证**:
        *   代码静态检查通过。
        *   单元测试（mock `engine_config`, `db_session`, `ChunkFusionRetriever` 等依赖）：
            *   测试在获取不到知识库时返回错误。
            *   测试工具能正确调用 `ChunkFusionRetriever.retrieve`。
            *   测试不同类型的返回节点都能被正确处理和转换。
            *   测试返回的 `KnowledgeRetrievalResult` 结构和内容正确。
            *   测试异常情况下的错误返回。

3.  **[ ] 实现/规范化 `DatabaseQueryTool` (`backend/app/autoflow/tools/database_query_tool.py`)**
    *   **任务**:
        *   对照 `工作流改造.md` "4.3 数据库查询工具" 部分的代码。
        *   确保 `DatabaseQueryParameters` 和 `DatabaseQueryResult` 类定义正确。
        *   确保 `DatabaseQueryTool` 类继承自 `BaseTool`，`__init__` 方法正确。
        *   重点检查 `execute` 方法：
            *   正确处理 `engine_config` 中数据库查询的启用状态。
            *   正确获取数据库连接 (`engine_config.get_linked_database_connections`)。
            *   正确选择目标数据库连接。
            *   正确导入和使用 `TextToSQLProcessor` (注意路径 `app.rag.database.text_to_sql`)。
            *   `_run_async` 方法用于异步执行 `processor.generate_sql`, `processor.execute_sql`, `processor.format_results`。
            *   错误处理和日志记录。
    *   **验证**:
        *   代码静态检查通过。
        *   单元测试（mock `engine_config`, `db_session`, `TextToSQLProcessor` 等依赖）：
            *   测试在数据库查询未启用时返回空结果。
            *   测试在获取不到数据库连接时返回错误。
            *   测试工具能正确调用 `TextToSQLProcessor` 的各个方法。
            *   测试返回的 `DatabaseQueryResult` 结构和内容正确。
            *   测试异常情况下的错误返回。

4.  **[ ] 实现/规范化 `FurtherQuestionsTool` (`backend/app/autoflow/tools/further_questions_tool.py`)**
    *   **任务**:
        *   对照 `工作流改造.md` "4.4 后续问题生成工具" 部分的代码。
        *   确保 `FurtherQuestionsParameters` 和 `FurtherQuestionsResult` 类定义正确。
        *   确保 `FurtherQuestionsTool` 类继承自 `BaseTool`，`__init__` 方法正确，并尝试获取 `llm`。
        *   重点检查 `execute` 方法：
            *   正确处理 `engine_config.further_questions` 的启用状态。
            *   检查 `llm` 是否可用。
            *   正确使用 `RichPromptTemplate` 和 `llm.predict` 生成后续问题。
            *   包含对生成结果的校验和重试逻辑。
            *   限制问题数量。
            *   错误处理和日志记录。
    *   **验证**:
        *   代码静态检查通过。
        *   单元测试（mock `engine_config`, `db_session`, `llm` 等依赖）：
            *   测试在后续问题生成未启用或LLM不可用时返回空结果。
            *   测试工具能正确调用 `llm.predict`。
            *   测试对生成结果的校验和处理逻辑。
            *   测试返回的 `FurtherQuestionsResult` 结构和内容正确。
            *   测试异常情况下的错误返回。

5.  **[ ] 实现/规范化工具初始化脚本 (`backend/app/autoflow/tools/init.py`)**
    *   **任务**:
        *   对照 `工作流改造.md` "5. 工具注册与初始化" 部分的代码。
        *   创建或修改 `backend/app/autoflow/tools/init.py` 文件。
        *   实现 `register_default_tools` 函数，确保它：
            *   获取 `ToolRegistry` 实例。
            *   实例化所有核心工具 (`KnowledgeGraphTool`, `KnowledgeRetrievalTool`, `DatabaseQueryTool`, `FurtherQuestionsTool`)，并传入 `db_session` 和 `engine_config`。
            *   使用 `registry.register_tool()` 注册这些工具。
            *   返回 `registry` 实例。
    *   **验证**:
        *   代码静态检查通过。
        *   能够成功导入 `register_default_tools` 函数。
        *   调用 `register_default_tools(mock_session, mock_config)` 后：
            *   返回的 `registry` 实例中包含所有已注册的工具名称。
            *   通过 `registry.get_tool()` 可以获取到每个工具的实例。

6.  **[ ] 扩展阶段一的单元测试**
    *   **任务**: 在 `tests/autoflow/tools/test_tools.py` 中，为每个具体实现的工具添加更详细的执行测试（如果之前的 mock 工具测试不够充分）。
    *   **验证**: 所有为阶段二（包括对阶段一的扩展）编写的单元测试通过。


好的，我们继续规划阶段三。

---

### **阶段三：智能体与工作流引擎实现**

**目标**：根据 `工作流改造.md` 的规范，实现智能体基类、各个具体智能体、上下文管理器以及核心工作流引擎。这些组件将协同工作，使用阶段二实现的工具来处理用户请求。

**涉及文件**：

*   `backend/app/autoflow/agents/base_agent.py` (新建或修改)
*   `backend/app/autoflow/agents/question_optimizer_agent.py` (新建或修改)
*   `backend/app/autoflow/agents/qa_agent.py` (新建或修改)
*   `backend/app/autoflow/agents/content_organizer_agent.py` (新建或修改)
*   `backend/app/autoflow/agents/structured_output_agent.py` (新建或修改)
*   `backend/app/autoflow/context.py` (检查与 `工作流改造.md` 的一致性)
*   `backend/app/autoflow/workflow.py` (检查与 `工作流改造.md` 的一致性)
*   `backend/app/autoflow/autoflow_agent.py` (检查与 `工作流改造.md` 的一致性，作为对外接口)
*   `tests/autoflow/test_workflow.py` (新建或扩展，参考 `工作流改造.md` 10.2 节)

**Checklist 与验证**：

1.  **[ ] 实现/规范化 `BaseAgent` (`backend/app/autoflow/agents/base_agent.py`)**
    *   **任务**:
        *   对照 `工作流改造.md` "2.1 智能体基类" 部分的代码。
        *   确保 `BaseAgent` 类的 `__init__` 方法正确初始化 `name`, `db_session`, `engine_config`, `step_id`, `tool_registry`, `logger`。
        *   确保 `process` 方法为异步生成器 (`AsyncGenerator[BaseEvent, None]`) 且标记为 `NotImplementedError`。
        *   重点检查 `call_tool` 方法：
            *   正确获取工具实例。
            *   正确处理工具未找到的情况并生成 `ErrorEvent`。
            *   正确生成 `tool_id`。
            *   正确转换参数 (`tool.parameter_type(**parameters)`)。
            *   按顺序生成 `ToolCallEvent`，执行工具 (`await tool.execute(param_obj)`)，然后生成 `ToolResultEvent`。
            *   正确处理工具执行异常并生成 `ErrorEvent`。
            *   确保 `call_tool` 是一个异步生成器，能 `yield` 事件并最终 `return` 工具的执行结果。
    *   **验证**:
        *   代码静态检查通过。
        *   单元测试：
            *   能够实例化 `BaseAgent` (或一个简单的子类)。
            *   测试 `call_tool`：
                *   当工具不存在时，正确 `yield` `ErrorEvent`。
                *   当工具存在时，mock工具的 `execute` 方法，验证 `call_tool` 能按预期 `yield` `ToolCallEvent` 和 `ToolResultEvent`，并返回结果。
                *   当工具的 `execute` 方法抛出异常时，验证 `call_tool` 能 `yield` `ErrorEvent`。

2.  **[ ] 实现/规范化 `QuestionOptimizerAgent` (`backend/app/autoflow/agents/question_optimizer_agent.py`)**
    *   **任务**:
        *   对照 `工作流改造.md` "2.2 优化问题智能体" 部分的代码。
        *   确保类继承自 `BaseAgent`，`__init__` 方法正确调用 `super()` 并初始化 `llm`。
        *   重点检查 `process` 方法：
            *   正确获取 `user_question` फ्रॉम `context`。
            *   根据 `engine_config.refine_question_with_kg` 判断是否优化。
            *   若不优化，直接将 `user_question` 存入 `refined_question` 并 `yield StepEndEvent`。
            *   若优化，正确调用 `self.call_tool("knowledge_graph_tool", ...)` 并处理其返回的事件和结果。
            *   若KG上下文不存在，则使用原问题。
            *   若LLM存在，使用 `RichPromptTemplate` 和 `self.llm.predict` 进行问题优化。
            *   将优化后的问题（或原问题）存入 `context` 中的 `refined_question`。
            *   处理异常情况并 `yield ErrorEvent`。
            *   最后 `yield StepEndEvent`。
    *   **验证**:
        *   代码静态检查通过。
        *   单元测试 (mock `context`, `engine_config`, `llm`, `self.call_tool`)：
            *   测试在不优化配置下，直接使用原问题。
            *   测试在优化配置下，正确调用 `knowledge_graph_tool`。
            *   测试在获取到KG上下文后，正确调用 `llm.predict`。
            *   测试能正确 `yield` `InfoEvent`, `ErrorEvent`, `StepEndEvent`。
            *   测试 `context` 中的 `refined_question` 被正确设置。

3.  **[ ] 实现/规范化 `QAAgent` (`backend/app/autoflow/agents/qa_agent.py`)**
    *   **任务**:
        *   对照 `工作流改造.md` "2.3 问答智能体" 部分的代码。
        *   确保类继承自 `BaseAgent`，`__init__` 方法正确。
        *   重点检查 `process` 方法的复杂逻辑：
            *   获取 `refined_question`。
            *   **问题澄清逻辑**: 若 `engine_config.clarify_question` 为真，调用 `knowledge_graph_tool`，然后使用 `llm` 和 `clarifying_question_prompt` 判断是否需要澄清，并提取澄清信息，设置 `context` 中的 `needs_clarification` 和 `clarification_message`。
            *   **知识库检索**: 调用 `knowledge_retrieval_tool` 并获取 `knowledge_nodes`。
            *   **数据库查询**: 若 `engine_config.database.enabled` 为真，调用 `database_query_tool` 并获取 `database_results`。
            *   **生成回答**: 准备 `context_str`，根据是否有 `database_results` 和相应的提示词 (`hybrid_response_synthesis_prompt` 或 `text_qa_prompt`) 调用 `llm.predict` 生成答案。
            *   将答案存入 `context` 中的 `answer`。
            *   处理异常并 `yield StepEndEvent`。
    *   **验证**:
        *   代码静态检查通过。
        *   单元测试 (mock `context`, `engine_config`, `llm`, `self.call_tool`)：
            *   测试问题澄清的完整逻辑（需要/不需要澄清）。
            *   测试知识库检索的调用和结果处理。
            *   测试数据库查询的调用和结果处理（启用/禁用时）。
            *   测试混合回答和纯文本QA回答的生成逻辑。
            *   测试 `context` 中的 `answer`, `needs_clarification`, `clarification_message` 被正确设置。
            *   测试能正确 `yield` 各类事件。

4.  **[ ] 实现/规范化 `ContentOrganizerAgent` (`backend/app/autoflow/agents/content_organizer_agent.py`)**
    *   **任务**:
        *   对照 `工作流改造.md` "2.4 内容整理智能体" 部分的代码。
        *   确保类继承自 `BaseAgent`，`__init__` 方法正确。
        *   重点检查 `process` 方法：
            *   获取 `answer`。
            *   判断回答是否简短且已结构化，若是则跳过整理。
            *   若LLM和提示词 (`reasoning_analysis_prompt`) 可用，调用 `llm.predict` 整理内容。
            *   将整理后的内容（或原回答）存入 `context` 中的 `organized_content`。
            *   处理异常并 `yield StepEndEvent`。
    *   **验证**:
        *   代码静态检查通过。
        *   单元测试 (mock `context`, `engine_config`, `llm`)：
            *   测试简短回答跳过整理的逻辑。
            *   测试调用 `llm.predict` 进行内容整理的逻辑。
            *   测试 `context` 中的 `organized_content` 被正确设置。
            *   测试能正确 `yield` 各类事件。

5.  **[ ] 实现/规范化 `StructuredOutputAgent` (`backend/app/autoflow/agents/structured_output_agent.py`)**
    *   **任务**:
        *   对照 `工作流改造.md` "2.5 结构化输出智能体" 部分的代码。
        *   确保类继承自 `BaseAgent`，`__init__` 方法正确。
        *   重点检查 `process` 方法：
            *   获取 `organized_content`。
            *   处理问题澄清：若 `needs_clarification` 为真且有 `clarification_message`，则 `yield TextEvent` 输出澄清消息并结束。
            *   处理后续问题：若 `engine_config.further_questions` 且 `llm` 可用，调用 `further_questions_tool` 并获取问题列表。
            *   `yield TextEvent` 输出最终回答 (`organized_content`)。
            *   若有后续问题，`yield TextEvent` 输出后续问题。
            *   处理异常并 `yield StepEndEvent`。
    *   **验证**:
        *   代码静态检查通过。
        *   单元测试 (mock `context`, `engine_config`, `llm`, `self.call_tool`)：
            *   测试问题澄清分支的逻辑和事件输出。
            *   测试后续问题生成分支的逻辑和事件输出（启用/禁用时）。
            *   测试主要回答的 `TextEvent` 输出。
            *   测试能正确 `yield` 各类事件。

6.  **[ ] 检查/规范化 `Context` (`backend/app/autoflow/context.py`)**
    *   **任务**: 对照 `工作流改造.md` "3.1 上下文管理器" 部分的代码，确保 `Context` 类的 `set`, `get`, `update`, `delete`, `clear`, `keys`, `has`, `get_workflow`, `get_current_date` 方法，以及 `asyncio.Lock` 的使用完全一致。
    *   **验证**: 代码静态检查。通过简单的实例化和方法调用进行手动验证，或编写小型单元测试验证其功能和线程安全（对于异步锁）。

7.  **[ ] 检查/规范化 `Workflow` (`backend/app/autoflow/workflow.py`)**
    *   **任务**: 对照 `工作流改造.md` "3.2 工作流引擎" 部分的代码。
        *   确保 `Workflow` 类的 `__init__` 方法正确初始化 `db_session`, `engine_config`, `logger`, `context`, `event_converter`。
        *   **关键**：确保 `self.agents`列表中的智能体实例化顺序和传入的 `step_id` 与文档一致 (`QuestionOptimizerAgent` step 0, `QAAgent` step 1, `ContentOrganizerAgent` step 2, `StructuredOutputAgent` step 3)。
        *   确保 `initialize` 方法正确设置初始上下文。
        *   确保 `run` 方法能按顺序异步迭代执行每个智能体的 `process` 方法，并使用 `event_converter` 转换和 `yield` 每个 `ChatEvent`。包含异常处理。
    *   **验证**: 代码静态检查。单元测试见下面的 `test_workflow.py`。

8.  **[ ] 检查/规范化 `AutoFlowAgent` (`backend/app/autoflow/autoflow_agent.py`)**
    *   **任务**: 对照 `工作流改造.md` "3.3 AutoFlow代理" 部分的代码。
        *   确保 `AutoFlowAgent` 类的 `__init__` 方法正确初始化。
        *   `set_indices` 方法按文档实现。
        *   重点检查 `stream_chat` 方法：
            *   正确创建和初始化 `Workflow` 实例。
            *   如果 `db_chat_obj` 存在，正确设置到 `workflow.context`。
            *   正确异步迭代 `workflow.run()` 并 `yield` 事件。
            *   包含异常处理并 `yield` 错误类型的 `ChatEvent`。
    *   **验证**: 代码静态检查。主要通过集成测试进行验证（阶段四）。

9.  **[ ] 编写/扩展工作流单元测试 (`tests/autoflow/test_workflow.py`)**
    *   **任务**: 参考 `工作流改造.md` "10.2 工作流集成测试" 部分的代码，创建或扩展此测试文件。
        *   实现 `test_workflow_initialization`。
        *   实现 `test_workflow_simple_execution` (mock 所有智能体的 `process` 方法，让它们 `yield` 一些预定义的 `BaseEvent`，然后验证 `workflow.run()` 是否能正确调用它们并转换事件为 `ChatEvent`)。
    *   **验证**: 所有为阶段三编写的单元测试通过。

好的，这是阶段四的计划。

---

### **阶段四：提示词、配置、集成与全面测试**

**目标**：将新的工作流系统与应用的其余部分（提示词定义、LLM配置、聊天服务）完全集成。进行全面的单元测试和集成测试，确保系统按预期工作。

**涉及文件**：

*   `backend/app/rag/default_prompt.py` (修改)
*   `backend/app/rag/chat/config.py` (修改)
*   `backend/app/rag/chat/chat_service.py` (修改)
*   `backend/app/__init__.py` (或应用主入口，用于调用 `init_autoflow`)
*   所有测试文件 (扩展，确保覆盖率)

**Checklist 与验证**：

1.  **[ ] 更新提示词定义 (`backend/app/rag/default_prompt.py`)**
    *   **任务**:
        *   对照 `工作流改造.md` "6. 提示词更新" 部分。
        *   将文档中定义的 `TOOL_DECISION_PROMPT`, `REASONING_ANALYSIS_PROMPT`, `HYBRID_RESPONSE_SYNTHESIS_PROMPT` 三个提示词模板字符串完整复制到 `backend/app/rag/default_prompt.py` 文件中。
        *   确保这些常量名称与文档一致。
    *   **验证**:
        *   代码静态检查通过。
        *   手动检查文件内容，确认新的提示词模板已正确添加。

2.  **[ ] 更新LLM配置 (`backend/app/rag/chat/config.py`)**
    *   **任务**:
        *   对照 `工作流改造.md` "7. 提示词配置注册" 部分。
        *   在 `LLMOption` 类中，添加新的字段定义：
            *   `tool_decision_prompt: str = DEFAULT_TOOL_DECISION_PROMPT`
            *   `reasoning_analysis_prompt: str = DEFAULT_REASONING_ANALYSIS_PROMPT`
            *   `hybrid_response_synthesis_prompt: str = DEFAULT_HYBRID_RESPONSE_SYNTHESIS_PROMPT`
        *   确保从 `backend/app/rag/default_prompt.py` 正确导入了 `DEFAULT_TOOL_DECISION_PROMPT` 等常量。
    *   **验证**:
        *   代码静态检查通过。
        *   能够成功实例化 `LLMOption`，并且新的提示词字段具有正确的默认值。
        *   如果应用中有加载配置的逻辑，验证这些新字段能被正确加载和访问。

3.  **[ ] 实现AutoFlow初始化 (`backend/app/__init__.py` 或相关入口)**
    *   **任务**:
        *   对照 `工作流改造.md` "8. 工具初始化和注册" 部分 (`init_autoflow` 函数的示例)。
        *   在应用启动时会调用的地方（通常是 `backend/app/__init__.py` 或主 FastAPI 应用创建的地方），添加 `init_autoflow` 函数的定义和调用。
        *   确保 `init_autoflow` 函数：
            *   导入 `register_default_tools` 从 `app.autoflow.tools.init`。
            *   调用 `register_default_tools(db_session, engine_config)`。
            *   包含日志记录，打印已注册的工具。
    *   **验证**:
        *   应用启动时，`init_autoflow` 被调用。
        *   日志中能看到 "AutoFlow工具已注册: ..." 的信息，且列出的工具与 `register_default_tools` 中注册的一致。
        *   `ToolRegistry` 单例中确实包含了这些注册的工具。

4.  **[ ] 集成AutoFlow到聊天服务 (`backend/app/rag/chat/chat_service.py`)**
    *   **任务**:
        *   对照 `工作流改造.md` "9. 工作流集成" 部分。
        *   在 `chat` (或类似的流式聊天处理) 函数中：
            *   在判断 `engine_config.agent.enabled` 为 `True` 的分支内：
                *   导入 `AutoFlowAgent` from `app.autoflow.autoflow_agent`。
                *   实例化 `AutoFlowAgent(db_session, engine_config)`。
                *   **重要**: 根据文档，有一行 `from app.autoflow.tools.init import register_default_tools` 和 `register_default_tools(db_session, engine_config)` 的调用。这似乎与上一步在应用初始化时调用 `init_autoflow` 重复。 **需要决策**：工具注册应该只在应用启动时进行一次。此处应移除 `register_default_tools` 的调用，因为 `AutoFlowAgent` 内部会通过 `ToolRegistry()` 获取已注册的工具。
                *   正确转换 `chat_messages` 为 `AutoFlowAgent.stream_chat` 所需的 `chat_history_list` 格式。
                *   正确调用 `autoflow_agent.stream_chat(query, chat_history_list, db_chat_obj)`。
                *   正确处理 `stream_chat` 返回的 `ChatEvent`，包括处理首个事件的 `CHAT_START` 逻辑。
                *   确保异常能被捕获并转换为 `ChatEventType.ERROR_PART` 事件。
    *   **验证**:
        *   代码静态检查通过。
        *   **集成测试/手动测试**:
            *   设置 `engine_config.agent.enabled = True`。
            *   发起聊天请求。
            *   观察日志，确认 `AutoFlowAgent` 被调用。
            *   （需要mock LLM 和各个工具的调用）验证整个工作流（至少是简化的）能够运行，并能流式返回事件。
            *   前端（如果对接）能接收并正确解析这些事件。
            *   测试错误处理：模拟工作流中某个环节抛出异常，验证是否能正确返回错误事件。

5.  **[ ] 全面单元测试和集成测试审查与增强**
    *   **任务**:
        *   回顾所有阶段编写的单元测试，确保关键逻辑路径都有覆盖。
        *   特别是 `BaseAgent.call_tool`，各个具体Agent的 `process` 方法中的分支逻辑，`Workflow.run` 的智能体调用顺序和事件转换。
        *   编写更细致的集成测试，测试从 `AutoFlowAgent.stream_chat` 入口到各个智能体、工具（mocked）的交互。
        *   考虑边界条件和异常情况的测试。
    *   **验证**:
        *   所有单元测试和集成测试通过。
        *   测试覆盖率达到项目要求的目标。

6.  **[ ] 端到端测试 (可选，但推荐)**
    *   **任务**: 如果条件允许，进行实际的端到端测试。
        *   配置一个真实的（或功能完整的mock）LLM。
        *   准备一些测试用的知识库数据、数据库表结构和数据、知识图谱数据（如果工具依赖这些）。
        *   通过API或前端界面发起真实的查询，覆盖不同的问题类型，预期会触发不同的工具和智能体逻辑。
    *   **验证**:
        *   系统能够针对不同类型的查询，调用合适的工具，并生成合理的、结构化的回答。
        *   整个流程符合预期，事件流正确。
        *   性能在可接受范围内。

7.  **[ ] 文档和代码清理**
    *   **任务**:
        *   确保所有新代码都有适当的类型提示和必要的文档字符串。
        *   移除开发过程中产生的临时代码或注释。
        *   格式化所有修改过的代码文件。
    *   **验证**: 代码审查通过。
