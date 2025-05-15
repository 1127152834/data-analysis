# LlamaIndex Metadata Extraction 最佳实践

本节总结了 LlamaIndex 中元数据提取 (Metadata Extraction) 的最佳实践，基于 "Metadata Extraction" O'Reilly 课程手册示例。核心目标是通过自动提取结构化元数据来增强节点的上下文，从而提升检索和问答的质量。

### 1. 元数据提取的核心价值

*   **增强节点信息**: 为文本块 (Nodes) 附加结构化的元数据，例如摘要、关键词、问题列表、实体等。
*   **提升检索精度**: 可以在查询时利用这些元数据进行过滤或更精确的匹配，而不仅仅依赖文本内容的向量相似性。
*   **改进问答能力**: 元数据可以为LLM提供更丰富的上下文，帮助其生成更相关、更准确的答案。

### 2. 元数据提取器 (Metadata Extractors)

LlamaIndex 提供了多种内置的元数据提取器，可以在节点解析 (Node Parsing) 阶段或之后应用。

*   **`SummaryExtractor`**: 从每个节点生成一个简洁的摘要。
    *   需要指定一个LLM用于生成摘要。
    *   摘要会存入节点的 `metadata["section_summary"]` 或 `metadata["document_summary"]`。
*   **`QuestionsAnsweredExtractor`**: 为每个节点生成一系列该节点内容可以回答的问题。
    *   需要指定一个LLM。
    *   问题列表会存入节点的 `metadata["questions_this_excerpt_can_answer"]`。
    *   这对于后续构建"问题路由器"或FAQ类型的应用非常有用。
*   **`KeywordExtractor`**: 从每个节点提取一组关键词。
    *   需要指定一个LLM。
    *   关键词列表会存入节点的 `metadata["excerpt_keywords"]`。
*   **`TitleExtractor`**: 尝试从节点内容中提取标题。
*   **`EntityExtractor`**: 提取节点中的命名实体（例如人名、地名、组织名）。需要配置 `label_entities=True` 以便将实体及其类型存储到元数据中。
    *   会存入节点的 `metadata["entities"]`。

### 3. 在节点解析时集成元数据提取

*   **`IngestionPipeline` 或 `SimpleNodeParser`**: 在配置节点解析器时，可以将元数据提取器列表传递给 `metadata_extractors` 参数。
    ```python
    from llama_index.core.node_parser import SimpleNodeParser
    from llama_index.core.extractors import (
        SummaryExtractor,
        QuestionsAnsweredExtractor,
        # KeywordExtractor, TitleExtractor, EntityExtractor
    )
    from llama_index.llms.openai import OpenAI # 或其他LLM

    # llm = OpenAI(model="gpt-3.5-turbo")

    # metadata_extractors = [
    #     SummaryExtractor(llms=[llm]), # 可以传入多个LLM进行选择或并行
    #     QuestionsAnsweredExtractor(questions=5, llm=llm, metadata_mode=" zowel"), # questions 参数指定生成问题数量
    # ]

    # node_parser = SimpleNodeParser.from_defaults(
    #     chunk_size=1024,
    #     metadata_extractors=metadata_extractors
    # )
    ```
*   **处理流程**: 当文档被加载并通过节点解析器时，每个生成的节点都会依次通过指定的元数据提取器进行处理，提取出的元数据会自动填充到该节点的 `metadata` 字典中。

### 4. 处理节点 (Processing Nodes)

*   **`get_nodes_from_documents`**: 当使用节点解析器从文档生成节点时，元数据提取会自动执行。
    ```python
    # from llama_index.core import SimpleDirectoryReader
    # documents = SimpleDirectoryReader(input_files=["path/to/your/doc.txt"]).load_data()
    # nodes = node_parser.get_nodes_from_documents(documents)
    ```
*   **直接处理现有节点 (`process_nodes`)**: 如果已经有一批节点，也可以使用元数据提取器列表对它们进行后处理。
    ```python
    # # 假设 orig_nodes 是一批已有的节点
    # processed_nodes = node_parser.metadata_extractors[0].process_nodes(orig_nodes) # 单个提取器
    # # 或者使用 IngestionPipeline.run(nodes=orig_nodes)
    ```

### 5. 使用 PydanticProgramExtractor 进行高级结构化提取

*   **目的**: 当需要从文本中提取具有特定结构（模式）的复杂信息，并希望以 Pydantic 模型对象的形式输出时，`PydanticProgramExtractor` 非常有用。
*   **优势**: 可以在一次 LLM 调用中提取多个字段或实体，而不是像单一元数据提取器那样通常只关注一种元数据。
*   **步骤**:
    1.  **定义 Pydantic 模型 (`BaseModel`)**: 定义你希望提取的数据结构，包括字段名、类型和描述 (Field descriptions)。描述对于指导 LLM 非常重要。
        ```python
        from pydantic import BaseModel, Field
        from typing import List

        # class NodeMetadata(BaseModel):
        #     """Node metadata."""
        #     entities: List[str] = Field(..., description="Unique entities in this text chunk.")
        #     summary: str = Field(..., description="A concise summary of this text chunk.")
        ```
    2.  **设置提取器 (`PydanticProgramExtractor`)**: 
        *   需要一个 `OpenAIPydanticProgram` (或其他 LLM 对应的 Program) 实例。
        *   `OpenAIPydanticProgram.from_defaults` 需要 `output_cls` (你的 Pydantic 模型) 和 `prompt_template_str` (或 `extract_template_str`)。
        *   `extract_template_str` 通常包含占位符 `{context_str}` (原始文本) 和 `{class_name}` (Pydantic 模型类名)。
        ```python
        # from llama_index.program.openai import OpenAIPydanticProgram
        # from llama_index.core.extractors import PydanticProgramExtractor

        # EXTRACT_TEMPLATE_STR = """\
        # Here is the content of the section:
        # ----------------
        # {context_str}
        # ----------------
        # Given the contextual information, extract out a {class_name} object.\
        # """

        # openai_program = OpenAIPydanticProgram.from_defaults(
        #     output_cls=NodeMetadata, # 你的 Pydantic 模型
        #     prompt_template_str="{input}", # 通常保持为 "{input}"
        #     extract_template_str=EXTRACT_TEMPLATE_STR,
        #     llm=llm # 指定 LLM
        # )

        # metadata_extractor = PydanticProgramExtractor(
        #     program=openai_program,
        #     input_key="input", # 通常与 openai_program 的 prompt_template_str 一致
        #     show_progress=True
        # )
        ```
    3.  **提取元数据**: 使用 `metadata_extractor.extract(nodes)` 或 `metadata_extractor.process_nodes(nodes)`。
        *   `extract()` 返回一个字典列表，每个字典对应一个节点的提取结果。
        *   `process_nodes()` 则直接将提取的元数据更新到节点对象的 `metadata` 字段中。

### 6. 构建索引和查询

*   **使用包含元数据的节点构建索引**: 无论是 `VectorStoreIndex` 还是其他类型的索引，都可以直接使用这些经过元数据增强的节点。
*   **在查询时利用元数据**: 
    *   **元数据过滤**: 许多向量存储支持在检索时根据元数据字段进行过滤 (例如，`MetadataFilters`)。
    *   **LLM 利用**: 即使不显式过滤，检索到的节点如果包含丰富的元数据，LLM 在生成答案时也能利用这些额外信息。
    *   **自定义检索策略**: 可以设计更复杂的检索策略，优先考虑那些元数据与查询意图高度匹配的节点。

### 7. 注意事项

*   **LLM 成本与延迟**: 元数据提取，尤其是涉及 LLM 调用的提取器，会增加数据处理的成本和时间。需要根据应用需求进行权衡。
*   **Prompt 工程**: 对于 `SummaryExtractor`, `QuestionsAnsweredExtractor` 等，以及 `PydanticProgramExtractor`，LLM 的表现很大程度上取决于内部或自定义的 Prompt。可能需要进行调整以获得最佳效果。
*   **`metadata_mode`**: 一些提取器（如 `QuestionsAnsweredExtractor`）有 `metadata_mode` 参数，可以控制提取的信息是嵌入到文本中还是仅存入元数据，这会影响后续的 Embedding 和检索。
*   **选择合适的提取器组合**: 根据下游任务的需求选择最合适的元数据提取器组合。并非所有提取器都适用于所有场景。

---
