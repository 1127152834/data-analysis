好的，我们开始设计这个改造方案。

**项目：AutoFlow Agent 化改造方案**

**目标**：将现有的 `ChatFlow` 固定聊天逻辑，全面改造为基于 LlamaIndex 的 `ReActAgent`、`FunctionTool` 以及可能的 `AgentWorkflow` 的动态智能体系统，以支持更灵活的对话、数据库查询、知识图谱查询、Web 搜索及未来“深度研究”等高级功能。

**核心原则**：

1.  **模块化工具**：将现有 RAG 功能及新功能封装为独立的、可被 Agent 调用的 `FunctionTool`。
2.  **Agent 驱动**：`ReActAgent` 作为核心决策者，根据用户输入和对话历史动态选择并执行工具。
3.  **配置驱动**：新的“Agent 引擎”配置将取代旧的 `ChatEngineConfig` 部分功能，用于定义 Agent 类型、可用工具集及其配置。
4.  **前端可管理**：工具的设计应考虑到未来可以通过前端界面进行管理和配置（例如，启用/禁用工具、配置工具参数等）。
5.  **分阶段实施**：确保每个阶段结束后，系统都能达到一个可运行和可验证的状态。
6.  **不依赖特定大模型**：设计上应尽可能允许灵活替换 LLM，尽管 `ReActAgent` 通常对强大 LLM 的依赖性较高。

---

**第一阶段：奠定 Agent 基础与核心 RAG 工具化**

**目标**：搭建 `ReActAgent` 的基本运行框架，并将当前 `ChatFlow` 中最核心的知识库检索和问答功能封装为第一个 `FunctionTool`。此阶段完成后，Agent 应能通过调用此工具回答基于现有知识库的问题，基本复现当前核心 RAG 对话能力。

**详细步骤**：

1.  **创建新的 Agent 服务层 (`backend/app/rag/agent_service.py`)**:
    *   此类将负责接收前端请求，初始化并运行 `ReActAgent`。
    *   它会处理用户消息、管理聊天历史（复用现有 `ChatMemoryBuffer` 或类似机制），并调用 Agent 执行。
    *   它将处理 Agent 返回的响应流（包括中间步骤和最终答案），并适配到现有的前端流式协议 (`ChatEvent`)。
    *   **依据**: 参考现有 `chat_service.py` 的职责，但将 `ChatFlow` 替换为 Agent。

2.  **设计核心 RAG 工具 (`KnowledgeBaseQueryTool`)**:
    *   **位置**: `backend/app/rag/tools/kb_query_tool.py`
    *   **功能**: 封装当前 `ChatFlow` 中的以下核心逻辑：
        *   接收用户原始问题 (或 Agent 提炼后的问题)。
        *   执行向量检索（复用 `_search_relevance_chunks` 的核心逻辑）。
        *   （可选，初期可简化）执行重排序（复用 `get_reranker` 的逻辑）。
        *   使用检索到的上下文和问题，通过 LLM 合成答案（复用 `_generate_answer` 的核心逻辑，特别是 `ResponseSynthesizer` 的使用）。
    *   **接口** (`FunctionTool` 规范):
        *   `name`: `"knowledge_base_query"`
        *   `description`: "当需要根据已加载的知识库内容回答用户问题时使用此工具。输入用户的问题，它会从知识库中检索相关信息并生成答案。" (此描述对 ReAct Agent 至关重要)
        *   `fn_schema`: 使用 Pydantic 定义输入模型，例如 `class KBQueryInput(BaseModel): query: str = Field(..., description="用户的问题")`。
        *   `_run(**kwargs)`: 实现工具的核心逻辑。
            *   调用现有的检索和答案生成代码模块（可能需要从 `ChatFlow` 中重构出来，放到 `backend/app/rag/retrievers/` 和 `backend/app/rag/response_synthesis/` 等辅助模块中，以便工具调用）。
            *   返回结构化的答案，例如包含答案文本和来源文档的 Pydantic 模型，或直接返回 LlamaIndex 的 `Response` 对象（工具内部可以将其转换为字符串或适合 Agent 的格式）。
    *   **配置**: 此工具需要能访问通过 `ChatEngineConfig` (或新的 Agent 配置) 定义的知识库、LLM、reranker 等。在实例化工具时传入必要的配置。
    *   **依据**: LlamaIndex `FunctionTool` 文档。将 `ChatFlow` 中分散的步骤整合为一个面向 Agent 的原子能力。

3.  **实现基础 `ReActAgent`**:
    *   **位置**: 在新的 `AgentService` 中进行初始化。
    *   **LLM**: 使用通过 `ChatEngineConfig` (或新配置) 指定的 LLM。
    *   **Tools**: 初始化时传入 `[KnowledgeBaseQueryTool(...)]`。
    *   **Memory**: 集成聊天历史记录 (`ChatMemoryBuffer`)。
    *   **System Prompt**: 设计一个初始的系统提示，指导 Agent 的行为，例如："你是一个乐于助人的AI助手。你可以使用提供的工具来回答关于特定知识库的问题。"
    *   **`agent.chat()` / `agent.stream_chat()`**: `AgentService` 将调用这些方法与 Agent 交互。
    *   **依据**: LlamaIndex `ReActAgent` 文档。

4.  **改造 `ChatEngineConfig` (或引入新的 `AgentEngineConfig`)**:
    *   **当前阶段**: 主要复用现有 `ChatEngineConfig` 加载 LLM、知识库等资源的逻辑。
    *   **未来演进**: `ChatEngineConfig` 需要演变为能够定义 Agent 类型、可用工具列表及其各自配置。
    *   **前端表单 (`CreateChatEngineForm`)**: 暂时不需要大改，用户选择的“引擎”在后端会被映射到这个基础的 ReAct Agent + KBQueryTool 的配置。

5.  **API 层面改造 (`backend/app/api/routes/chat.py` - 假设有此文件)**:
    *   修改处理聊天请求的 API 端点，使其调用新的 `AgentService` 而不是旧的 `ChatFlow` 逻辑。
    *   确保请求参数（如 `engine_name`, 用户消息）能正确传递给 `AgentService`。
    *   确保从 `AgentService` 返回的流能被正确处理并发送给前端。
    *   **依据**: FastAPI 路由和请求处理。

6.  **前端适配**:
    *   `ChatController` (`chat-controller.ts`) 调用后端 API 的方式基本不变。
    *   重点在于处理可能新增的流式事件类型。初期，如果 Agent 只返回最终答案（通过 `KnowledgeBaseQueryTool`），前端可能不需要大改。但为了未来的扩展性，可以开始考虑如何处理 Agent 的中间步骤（如 "Thought:", "Action: ToolName", "Observation: ToolOutput"）。
    *   **依据**: Vercel AI SDK stream G约定，LlamaIndex Agent 的流式输出格式。

**此阶段完成后的可验证状态**：

*   用户可以在前端选择一个（经过后台配置映射的）“引擎”。
*   用户发送消息后，后端 `ReActAgent` 被激活。
*   Agent 根据其系统提示和对 `KnowledgeBaseQueryTool` 的描述，决定调用该工具。
*   `KnowledgeBaseQueryTool` 执行知识库检索和答案生成。
*   Agent 将工具的结果作为最终答案返回给用户。
*   聊天体验应与当前核心 RAG 功能类似，但底层已替换为 Agent 架构。
*   通过 `verbose=True` (或 Langfuse) 可以观察到 Agent 的 ReAct 循环。

---

**第二阶段：集成现有高级工具 (SQL 查询与 BOM 成本查询)**

**目标**：将项目已有的 `SQLQueryTool` 和 `BomMaterialCostTool` 集成到 `ReActAgent` 的可用工具集中，使 Agent 能够根据用户意图选择调用这些工具。

**详细步骤**：

1.  **适配并注册 `SQLQueryTool`**:
    *   **位置**: `backend/app/rag/tools/sql_query_tool.py` (已存在)。
    *   **确认兼容性**: 确保其基类或实现方式与 `ReActAgent` 期望的 `FunctionTool` 接口一致。它已经继承自 `BaseTool`，这很好。
    *   **实例化与配置**: 在 `AgentService` 中，当初始化 Agent 时，如果当前引擎配置启用了数据库查询并链接了数据库，则实例化 `SQLQueryTool`，并传入从 `ChatEngineConfig` (或新 Agent 配置) 中获取的数据库配置、LLM 等。
    *   **Description 优化**: 确保 `SQLQueryTool` 的 `description` 清晰地告知 Agent 何时应使用它，以及它能做什么。例如：“当用户的问题需要从结构化数据库（如订单信息、用户信息表）中查询数据时使用此工具。例如‘查询用户X的最新订单’或‘统计上个月的产品销量’”。
    *   **依据**: `SQLQueryTool` 现有代码，LlamaIndex Agent 对工具的要求。

2.  **适配并注册 `BomMaterialCostTool`**:
    *   **位置**: `backend/app/rag/agent/tools/web/bom_cost.py` (已存在)。
    *   **确认兼容性**: 同上，确保其与 `FunctionTool` 接口兼容。
    *   **实例化与配置**: 如果需要，允许通过 Agent 引擎配置来启用/禁用此工具或配置其参数（如环境选择，尽管目前是输入参数）。
    *   **Description 优化**: 例如：“当用户需要查询特定产品的BOM（物料清单）成本时使用此工具。你需要提供产品编码。”
    *   **安全考虑**: 再次强调 `externalToken` 的安全管理。
    *   **依据**: `BomMaterialCostTool` 现有代码。

3.  **更新 Agent 初始化**:
    *   在 `AgentService` 中，根据选择的引擎配置，动态构建传递给 `ReActAgent` 的工具列表。现在可能包含 `[KnowledgeBaseQueryTool, SQLQueryTool, BomMaterialCostTool]` (视配置而定)。

4.  **增强 Agent 的 System Prompt**:
    *   系统提示需要更新，以告知 Agent 它现在拥有了查询知识库、查询结构化数据库和查询BOM成本的能力，并指导它如何根据用户问题选择合适的工具。
    *   例如：“你是一个多功能AI助手。你可以：1. 使用'knowledge_base_query'工具回答关于[知识库主题]的问题。2. 使用'sql_query_tool'查询结构化数据库以获取具体数据。3. 使用'bom_material_cost'工具查询产品BOM成本。请仔细分析用户问题，选择最合适的工具。”

5.  **前端展示 (可选增强)**:
    *   如果 Agent 调用了 `SQLQueryTool` 或 `BomMaterialCostTool`，前端可以考虑如何展示这些工具的使用情况和结果。`ChatController` 中已有的 `tool_call` 和 `tool_result` 事件处理逻辑可以用于此目的。
    *   例如，可以显示 Agent 正在“查询数据库...”或“正在获取BOM成本...”，并将工具返回的结构化数据以合适的方式展示给用户（除了 LLM 合成的自然语言答案外）。

**此阶段完成后的可验证状态**：

*   Agent 能够根据用户问题，在 `KnowledgeBaseQueryTool`、`SQLQueryTool` 和 `BomMaterialCostTool` 之间做出选择。
    *   例如，提问“公司最新的财报数据怎么样了？”（假设财报在知识库中），Agent 使用 `KnowledgeBaseQueryTool`。
    *   提问“查询用户ID为X001的客户的订单历史”（假设有订单数据库），Agent 使用 `SQLQueryTool`。
    *   提问“产品ABC的BOM成本是多少？”，Agent 使用 `BomMaterialCostTool`。
*   Agent 能够正确地将用户问题或其一部分传递给所选工具。
*   Agent 能够将工具返回的结果用于生成最终回复。
*   （如果实现）前端能够展示 Agent 调用不同工具的过程。

---

**第三阶段：工具化其他 RAG 功能与引入混合查询**

**目标**：将 `ChatFlow` 中剩余的 RAG 相关功能（如知识图谱查询、问题精炼、澄清）封装成工具，并实现混合查询能力，允许 Agent 结合多个工具的结果来回答复杂问题。

**详细步骤**：

1.  **创建知识图谱查询工具 (`KnowledgeGraphQueryTool`)**:
    *   **位置**: `backend/app/rag/tools/kg_query_tool.py`
    *   **功能**: 封装 `_search_knowledge_graph` 的逻辑。
        *   接收实体、关系或自然语言问题。
        *   将其转换为图查询。
        *   执行查询并返回结果（可能是子图、路径或文本描述）。
    *   **Description**: 例如：“当需要探索实体之间的关系、查询知识图谱中的事实或进行基于图的推理时使用此工具。”
    *   **配置**: 需要访问知识图谱的连接和配置（来自 `ChatEngineConfig` 的 `KnowledgeGraphOption`）。

2.  **创建问题处理工具 (可选，可作为 Agent 核心能力或高级工具的一部分)**:
    *   **问题精炼工具 (`QuestionRefinementTool`)**: 封装 `_refine_user_question` 的逻辑。
        *   **Description**: “当用户问题比较模糊或需要结合上下文进一步优化时，可以使用此工具对问题进行精炼。”
    *   **问题澄清工具 (`QuestionClarificationTool`)**: 封装 `_clarify_question` 的逻辑。
        *   **Description**: “如果用户问题意图不明确，使用此工具生成澄清性问题向用户提问。”
    *   **思考**: 这些功能有时也可以通过精心设计的 Agent System Prompt 或 ReAct 的多轮次思考来实现，而不一定需要独立的工具。但如果逻辑复杂且通用，工具化是好的选择。

3.  **增强 Agent 处理复杂查询和混合结果的能力**:
    *   **System Prompt**: 进一步指导 Agent 如何处理需要调用多个工具或组合工具结果的查询。
    *   **Agent 逻辑**: `ReActAgent` 的 ReAct 循环天然支持多步推理。Agent 在得到一个工具的结果后，可以“思考”是否需要调用另一个工具来补充信息，或者如何将多个工具的输出结合起来形成答案。
    *   **响应合成**: 如果 Agent 调用了多个工具，它需要将这些信息汇总并生成一个连贯的最终答案。这可能需要一个专门的“最终答案合成”步骤，或者依赖 Agent LLM 的总结能力。

4.  **实现混合查询 (示例：结合 RAG 和 SQL)**:
    *   用户提问：“告诉我知识库中关于产品X的最新用户反馈，并结合数据库中该产品的上月销量数据。”
    *   Agent 的决策流程可能如下：
        1.  **Thought**: 问题需要两部分信息：知识库的用户反馈和数据库的销量。
        2.  **Action**: `knowledge_base_query`, Input: "产品X的最新用户反馈"
        3.  **Observation**: (来自KB的反馈文本)
        4.  **Thought**: 已获得反馈，现在需要销量数据。
        5.  **Action**: `sql_query_tool`, Input: "产品X上月销量"
        6.  **Observation**: (销量数据)
        7.  **Thought**: 已获得所有信息，可以生成答案。
        8.  **Answer**: (LLM基于两条Observation生成最终回复)

5.  **`query_dispatcher.py` 的演进**:
    *   分析 `query_dispatcher.py` 的现有逻辑。
    *   如果它的功能是初步判断查询类型并路由到粗粒度的处理流程（如“这是个KB问题” vs “这是个SQL问题”），那么它的部分职责会被 Agent 的工具选择机制取代。
    *   但如果它包含了一些有价值的预处理或查询分类逻辑，可以考虑将其封装成一个“元工具” (`MetaQueryClassifierTool`)，Agent 可以先调用它来获取关于查询类型的提示，然后再选择更具体的工具。

6.  **`backend/dspy_program.py` 的集成/替代**:
    *   **分析**: 深入理解 DSPy 程序在当前系统中的具体作用。
        *   它是否编译了一个完整的端到端 RAG 流程？
        *   它是否用于优化特定的子模块（如 Prompt 生成、模型选择）？
    *   **集成方案**:
        *   **方案 A (黑盒工具)**: 如果 DSPy 程序实现了一个完整的、优化的 RAG 查询流程（例如，从问题到答案，包含检索、合成），可以将这个编译后的 DSPy 程序封装成一个 `FunctionTool`。Agent 在判断问题适合标准 RAG 处理时，直接调用此工具。
        *   **方案 B (细粒度组件)**: 如果 DSPy 用于优化特定组件（例如，一个特别高效的 DSPy 检索模块或 DSPy 答案生成模块），那么这些优化后的组件可以被我们之前设计的 `KnowledgeBaseQueryTool` 或其他新工具在内部使用。Agent 依然调用如 `KnowledgeBaseQueryTool` 这样的业务逻辑工具。
        *   **方案 C (Agent 取代编排)**: 如果 DSPy 主要用于定义和连接 RAG 流程中的各个步骤，那么 Agent 的引入（尤其是 ReAct Agent 的动态决策能力）可能会自然地取代 DSPy 的这部分编排角色。Agent 会动态地“连接”各个工具。
    *   选择哪种方案取决于 DSPy 的具体应用和您希望 Agent 的灵活性。如果 DSPy 提供了显著的性能或质量优化，方案 A 或 B 可能是初期较好的选择。

**此阶段完成后的可验证状态**：

*   Agent 能够使用新增的 `KnowledgeGraphQueryTool` (以及可选的 `QuestionRefinementTool`, `QuestionClarificationTool`)。
*   Agent 能够处理需要调用多个不同工具（如先查KB，再查SQL）的复杂问题，并能综合信息给出答案。
*   与 DSPy 的集成方式明确，并且 Agent 能够按预期与之协作或取代其部分功能。

---

**第四阶段：工具管理、前端适配与“深度研究”雏形**

**目标**：初步实现工具的前端可管理性，进一步适配前端以展示 Agent 行为，并为“深度研究”功能打下基础。

**详细步骤**：

1.  **设计工具管理机制**:
    *   **后端**:
        *   需要一种方式来注册和发现可用的工具（`@register_tool` 装饰器是一个好的开始）。
        *   `ChatEngineConfig` (或新的 `AgentEngineConfig`) 需要能够配置哪些工具对特定的“Agent引擎”实例是可用的，以及这些工具的特定参数（例如，`SQLQueryTool` 使用哪些数据库连接，`KnowledgeBaseQueryTool` 关联哪些知识库）。
        *   可以考虑在数据库中存储工具的元数据（名称、描述、参数模式），以便前端动态加载和展示。
    *   **前端**:
        *   在 `CreateChatEngineForm` (或新的Agent配置界面) 中，允许用户：
            *   查看当前 Agent 引擎可用的工具列表。
            *   启用/禁用某些工具。
            *   （高级）配置某些工具的特定参数，例如为一个RAG工具选择它应该查询哪些知识库。
    *   **依据**: 可插拔的系统设计，许多 AI Agent 框架都有类似工具管理功能。

2.  **增强前端对 Agent 行为的展示**:
    *   利用 `ChatController` 已有的 `tool_call`, `tool_result` 事件处理。
    *   在前端UI中清晰地展示 Agent 的思考过程（如果Agent的流式输出包含"Thought:"）、正在调用的工具名称、工具的输入参数（可以简化显示），以及工具返回的观察结果（也可以简化或摘要显示）。
    *   这对于用户理解 Agent 为何会给出某个答案，以及调试 Agent 行为至关重要。
    *   **依据**: Perplexity AI 等产品的用户体验，它们会展示部分信息检索过程。

3.  **“深度研究”功能初步设计与 Agent 实现**:
    *   **定义**: "深度研究" 可以被看作是一个需要 Agent 执行一个相对复杂计划，调用多个工具（可能包括 Web 搜索、多次数据库/知识库查询、信息交叉验证、内容总结）才能完成的任务。
    *   **Agent 驱动**: `ReActAgent` 通过其多轮次的“思考-行动-观察”循环，天然具备执行这种多步任务的潜力。
    *   **关键工具**:
        *   **Web 搜索工具**: 我们在 `backend/app/rag/agent/tools/web/` 下看到了 `bom_cost.py`。如果需要通用的 Web 搜索，需要引入或实现一个通用 Web 搜索工具（例如，使用 Tavily API, SearxNG, 或基于 Playwright 的网页抓取工具）。可以将其也放在 `agent/tools/web/` 目录下。
        *   **内容提取/总结工具**: 可能需要一个工具来从网页内容或长文档中提取关键信息或进行总结。这可以是一个调用 LLM 进行总结的 `FunctionTool`。
    *   **触发**: 用户可能会通过特定的指令（例如，“深入研究一下关于X公司最新动态”）或者 Agent 在判断用户问题需要广泛信息收集时自行启动“深度研究”模式（这需要更高级的 System Prompt 和 Agent 规划能力）。
    *   **System Prompt**: 为执行深度研究任务的 Agent (或同一 Agent 在特定模式下) 设计专门的系统提示，指导其规划步骤、信息来源选择和结果汇总。
    *   **示例流程 (Agent 内部)**:
        1.  用户：“深入研究AI在医疗诊断领域的最新进展和主要公司。”
        2.  Agent (Thought): 需要进行Web搜索获取最新进展，然后可能需要查询知识库或数据库获取公司信息。
        3.  Agent (Action): `web_search_tool`, Input: "AI医疗诊断最新进展 2024"
        4.  Agent (Observation): (返回搜索结果列表)
        5.  Agent (Thought): 需要查看几个主要链接的内容。
        6.  Agent (Action): `web_scrape_tool` (假设有此工具), Input: URL1
        7.  Agent (Observation): (URL1 的内容)
        8.  Agent (Action): `text_summarization_tool`, Input: (URL1 的内容)
        9.  Agent (Observation): (URL1 的摘要)
        10. ... (对其他URL重复此过程) ...
        11. Agent (Thought): 已收集主要进展，现在查找主要公司。
        12. Agent (Action): `knowledge_base_query` (或 `sql_query_tool` 如果公司信息在DB), Input: "AI医疗诊断领域的主要公司"
        13. Agent (Observation): (公司列表和信息)
        14. Agent (Thought): 已收集所有信息，进行总结。
        15. Agent (Answer): (综合总结所有发现)

**此阶段完成后的可验证状态**：

*   用户可以通过前端界面（至少是管理员界面）查看和配置特定 Agent 引擎可用的工具。
*   前端聊天界面能够更清晰地展示 Agent 的思考步骤和工具使用情况。
*   Agent 能够使用新增的 Web 搜索工具（或其他为深度研究准备的工具）。
*   对于需要多步骤、多工具协作才能回答的复杂问题（“深度研究”的雏形），Agent 能够展现出初步的规划和执行能力。

---

**通用考虑事项 (贯穿所有阶段)**：

*   **错误处理与容错**: 每个工具和 Agent 本身都需要有健壮的错误处理机制。Agent 需要能够处理工具执行失败的情况，并决定下一步如何做（例如，尝试另一个工具，或者告知用户无法完成请求）。
*   **安全性**:
    *   对于调用外部API的工具（如 `BomMaterialCostTool` 或 Web 搜索），管理好 API 密钥。
    *   对于 `SQLQueryTool`，严格遵守 `DatabaseOption` 中定义的权限（只读、允许的表等），防止潜在的恶意查询。Agent 生成的 SQL 或传递给 NLSQL 引擎的自然语言也需要被审视，以防注入。
*   **可观察性 (Observability)**:
    *   继续并加强 Langfuse 的集成。追踪 Agent 的每一步思考、工具调用、输入输出。
    *   详细的日志记录。
*   **迭代与评估**: 每个阶段完成后，进行实际测试。评估 Agent 的决策是否合理，工具是否按预期工作，回复质量如何。根据测试结果迭代优化 Agent 的 System Prompt、工具的 Description、或工具本身的逻辑。
*   **LLM 依赖**: 虽然我们希望不依赖特定大模型，但 `ReActAgent` 的表现通常与 LLM 的推理能力强相关。在选择 LLM 时需要考虑到这一点。工具的 Prompt（如图数据库查询的 Prompt）也可能需要针对不同 LLM 进行微调。