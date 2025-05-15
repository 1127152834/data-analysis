### LlamaIndex KnowledgeGraphRAGQueryEngine 最佳实践

**核心功能**:
*   `KnowledgeGraphRAGQueryEngine` (知识图谱检索增强生成查询引擎) 结合了知识图谱查询与传统向量存储 RAG 的能力，以提供更丰富、更上下文感知的答案。
*   它首先使用自然语言查询知识图谱 (KG) 以提取相关实体、关系和子图作为结构化上下文。
*   然后，它利用从 KG 中提取的信息 (例如实体名称) 来查询一个或多个向量索引 ( Retriever / RAG )，以获取相关的非结构化文本块。
*   最后，将来自知识图谱的结构化信息和来自向量索引的非结构化文本块结合起来，共同送给大语言模型 (LLM) 生成最终答案。

**主要应用场景**:
*   当需要回答不仅依赖于图谱中明确的关系，还依赖于与图中实体相关的详细文本描述的问题时。
*   例如："告诉我关于[从知识图谱中识别出的特定电影]的评论摘要，并列出其主要演员[来自知识图谱]。"
*   需要深入理解实体，而不仅仅是实体间的连接。

**核心组件与实施流程**:
1.  **数据准备与索引构建**:
    *   **知识图谱 (`KnowledgeGraphIndex`)**: 
        *   构建或加载一个 `KnowledgeGraphIndex`，确保其包含实体和关系。
        *   **关键**: 在构建 `KnowledgeGraphIndex` 时，通常建议设置 `include_embeddings=True`，这样实体可以用于后续的向量检索增强。
    *   **向量索引 (`VectorStoreIndex` 或其他 RAG 设置)**:
        *   准备与知识图谱中实体相关的非结构化文本文档 (例如，电影的剧情摘要、产品描述、人物传记等)。
        *   为这些文档构建一个或多个 `VectorStoreIndex`。

2.  **初始化 `KnowledgeGraphRAGQueryEngine`**:
    *   通过 `KnowledgeGraphIndex` 的 `as_query_engine()` 方法创建，并指定 `retriever_mode="knowledge_graph_rag"`。
    *   **关键参数**:
        *   `graph_retriever`: (可选) 自定义知识图谱检索器。默认情况下，它会从 `KnowledgeGraphIndex` 创建一个。
        *   `graph_retriever_similarity_top_k`: 从图谱检索器返回的初始节点数量。
        *   `vector_retriever`: (可选) 自定义向量检索器。如果 `KnowledgeGraphIndex` 构建时 `include_embeddings=True`，并且有 `VectorStoreIndex` 与 `StorageContext` 关联，引擎可以自动使用它。否则需要显式提供。
        *   `response_synthesizer`: (可选) 自定义响应合成器。
        *   `max_knowledge_sequence`: 从知识图谱中提取并传递给 LLM 的三元组 (或文本块) 的最大数量。
        *   `verbose` (布尔值): 设置为 `True` 以查看中间步骤和生成的查询。

3.  **查询执行流程**:
    *   用户发出自然语言查询。
    *   **步骤 1 (知识图谱查询)**: 引擎首先将查询转换为图查询 (如 Cypher)，在知识图谱中执行，提取相关的实体、关系和上下文。这可能涉及关键词提取和子图检索。
    *   **步骤 2 (向量检索增强)**: 从图谱查询结果中提取关键信息 (如实体名称)，然后使用这些信息去查询向量索引，获取相关的非结构化文本块。
    *   **步骤 3 (响应合成)**: 将从知识图谱获得的结构化信息和从向量索引获得的非结构化文本块一起提供给 LLM，生成最终的综合答案。

**重要注意事项与最佳实践**:
*   **实体链接**: 确保知识图谱中的实体能够有效地与向量索引中的文档对应起来是至关重要的。元数据或一致的命名约定会有所帮助。
*   **上下文融合**: LLM 需要能够有效地融合来自两种不同来源 (结构化图谱数据和非结构化文本) 的信息。
*   **检索策略 (`retriever_mode`, `graph_retriever_similarity_top_k`)**: 
    *   `"knowledge_graph_rag"` 模式是此引擎的核心。
    *   调整 `graph_retriever_similarity_top_k` 和向量检索器的 `similarity_top_k` 来平衡召回率和精度，避免信息过载。
*   **Prompt 工程**: 与其他复杂查询引擎类似，可以通过定制 Prompt (如 `text_qa_template`, `refine_template`) 来优化 LLM 对融合信息的理解和答案生成。
*   **模块化与可配置性**: 引擎设计允许替换或自定义各个组件 (如 `graph_retriever`, `vector_retriever`, `response_synthesizer`)，以适应特定需求。
*   **性能考量**: 查询涉及多个步骤 (图查询、向量查询、LLM 合成)，可能会比单一查询引擎慢。需要针对具体应用进行性能测试和优化。
*   **知识图谱深度与广度**: 图谱的结构和内容会影响第一阶段的检索效果，进而影响后续的 RAG 过程。

**与 `KnowledgeGraphQueryEngine` 的区别**:
*   `KnowledgeGraphQueryEngine` 主要侧重于直接从图谱中回答问题，其输出直接基于图查询结果。
*   `KnowledgeGraphRAGQueryEngine` 则更进一步，使用图谱作为初步探索和上下文获取的手段，然后用这些信息来增强对外部非结构化文本的检索，最终答案是两者的结合。
