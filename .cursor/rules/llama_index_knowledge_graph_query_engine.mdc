### LlamaIndex KnowledgeGraphQueryEngine 最佳实践

**核心功能**:
*   `KnowledgeGraphQueryEngine` 允许用户使用自然语言查询知识图谱 (Knowledge Graph)。
*   它将自然语言查询转换为特定图数据库的查询语言 (如 Cypher for Neo4j, 或 SPARQL)，在图谱上执行该查询，然后将结果合成为自然语言响应返回给用户。
*   支持多种图数据库后端，包括 NebulaGraph, Kuzu, Neo4j 等，通过 `KnowledgeGraphIndex` 进行集成。

**主要应用场景**:
*   当数据以实体和关系的形式存储在知识图谱中，并且需要通过自然语言进行复杂查询、推理和关系探索时。
*   例如："爱莉克丝和鲍勃有哪些共同的兴趣爱好？" 或 "哪些论文引用了关于图神经网络的最新研究？"

**核心组件与实施流程**:
1.  **构建 `KnowledgeGraphIndex`**:
    *   首先需要一个已经构建好的 `KnowledgeGraphIndex`。这个索引代表了与图数据库的连接和交互方式。
    *   索引的构建通常涉及连接到图数据库 (如提供 `graph_store` 参数，如 `Neo4jGraphStore`, `NebulaGraphStore` 等) 和可选的 `StorageContext`。
    *   在构建索引时，可以指定 `include_embeddings=True` 来为实体节点创建嵌入，这有助于后续的语义相似性查询或 RAG (Retrieval Augmented Generation)。

2.  **初始化 `KnowledgeGraphQueryEngine`**:
    *   通过 `KnowledgeGraphIndex` 的 `as_query_engine()` 方法创建查询引擎。
    *   **关键参数**:
        *   `retriever_mode`: 定义检索策略，如 `"keyword"` (基于关键词) 或 `"embedding"` (基于嵌入相似性) 用于从图中检索初始上下文。`"hybrid"` 则结合两者。
        *   `response_synthesizer`: 控制如何从检索到的上下文和图查询结果生成最终答案。
        *   `graph_store_query_depth` (整数, 默认为 2): 控制在图谱中探索的深度 (跳数)。
        *   `verbose` (布尔值): 设置为 `True` 可以打印出生成的图查询语句和中间步骤，便于调试。

3.  **查询执行**:
    *   调用查询引擎的 `query("自然语言问题")` 方法。
    *   引擎内部流程：
        1.  自然语言查询 -> 图查询语言 (如 Cypher)。
        2.  在图数据库中执行图查询。
        3.  (可选) 根据需要检索额外的上下文信息。
        4.  将图查询结果和上下文信息 -> 自然语言响应。

**重要注意事项与最佳实践**:
*   **图谱数据质量**: 知识图谱的质量（实体、关系、属性的准确性和完整性）直接影响查询结果的质量。
*   **Schema 理解**: LLM 需要能够理解图谱的 schema (节点标签、关系类型、属性) 才能生成有效的图查询。在 `KnowledgeGraphIndex` 构建或查询时，可以传入 `graph_schema_str` 来显式提供 schema 定义。
*   **查询复杂度与深度**: 过于复杂的自然语言查询可能难以准确转换为图查询。`graph_store_query_depth` 参数需要根据图谱结构和查询需求调整，过深可能导致性能问题或不相关结果。
*   **嵌入与关键词的选择 (`retriever_mode`)**: 
    *   若查询依赖精确的实体名称或术语，`"keyword"` 模式可能更优。
    *   若查询更侧重语义相似性或概念匹配，`"embedding"` 模式可能更合适。
    *   `"hybrid"` 模式通常能提供较好的平衡。
*   **Prompt 工程**: 可以通过定制 `query_keyword_extract_template` (用于关键词提取) 和 `refine_template` / `text_qa_template` (用于响应合成)来自定义 Prompt，以优化 LLM 在查询转换和答案生成方面的表现。
*   **LLM 选择**: 不同的 LLM 在理解自然语言和生成图查询方面的能力不同，选择合适的 LLM 很重要。

**示例场景 (简化)**:
*   图谱包含人物 (Person) 和兴趣 (Interest) 节点，以及 `HAS_INTEREST` 关系。
*   用户查询："Alice 有什么兴趣？"
*   引擎可能生成类似 Cypher 查询: `MATCH (p:Person {id: 'Alice'})-[:HAS_INTEREST]->(i:Interest) RETURN i.id`
*   然后将返回的兴趣列表转换为自然语言回答。
