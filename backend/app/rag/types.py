import enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

# # 事件类型到前端SSE事件名称的集中映射
# CHAT_EVENT_TYPE_TO_FRONTEND = {
#     # 核心事件类型
#     0: "text",
#     2: "data",
#     3: "error",
#     8: "message_annotations",
    
#     # 工具调用相关事件类型
#     10: "message_annotations",  # TOOL_START_PART -> 使用message_annotations展示
#     11: "message_annotations",  # TOOL_THINKING_PART -> 使用message_annotations展示
#     12: "tool_call",            # TOOL_CALL_PART -> 直接映射到tool_call
#     13: "tool_result",          # TOOL_RESULT_PART -> 直接映射到tool_result
#     14: "message_annotations",  # AGENT_THINKING_PART -> 使用message_annotations展示
    
#     # 确保包含所有可能用到的枚举值 
#     1: "text",            # 如果有ChatEventType值为1的情况，映射到text
#     4: "text",            # 如果有ChatEventType值为4的情况，映射到text 
#     5: "text",            # 如果有ChatEventType值为5的情况，映射到text
#     6: "text",            # 如果有ChatEventType值为6的情况，映射到text
#     7: "text",            # 如果有ChatEventType值为7的情况，映射到text
#     9: "text",            # 如果有ChatEventType值为9的情况，映射到text
#     15: "text",           # 可能的扩展枚举值
#     16: "text",           # 可能的扩展枚举值
#     # ...可根据需要扩展更多的映射
# }

# Langfuse needs an enum class for event types,
# but the CBEventType in llama-index does not have sufficient types.
class MyCBEventType(str, enum.Enum):
    CHUNKING = "chunking"
    NODE_PARSING = "node_parsing"
    EMBEDDING = "embedding"
    LLM = "llm"
    QUERY = "query"
    RETRIEVE = "retrieve"
    SYNTHESIZE = "synthesize"
    TREE = "tree"
    SUB_QUESTION = "sub_question"
    TEMPLATING = "templating"
    FUNCTION_CALL = "function_call"
    RERANKING = "reranking"
    EXCEPTION = "exception"
    AGENT_STEP = "agent_step"
    CLARIFYING_QUESTION = "clarifying_question"
    CONDENSE_QUESTION = "condense_question"
    REFINE_QUESTION = "refine_question"
    RETRIEVE_FROM_GRAPH = "retrieve_from_graph"
    INTENT_DECOMPOSITION = "intent_decomposition"
    GRAPH_SEMANTIC_SEARCH = "graph_semantic_search"
    SELECT_KNOWLEDGE_BASE = "select_knowledge_base"
    RUN_SUB_QUERIES = "run_sub_queries"


# Chat stream response event types
class ChatEventType(int, enum.Enum):
    # Following vercel ai sdk's event type
    # https://github.com/vercel/ai/blob/84871281ab5a2c080e3f8e18d02cd09c7e1691c4/packages/ui-utils/src/stream-parts.ts#L368
    TEXT_PART = 0
    DATA_PART = 2
    ERROR_PART = 3
    MESSAGE_ANNOTATIONS_PART = 8

    # @classmethod
    # def get_frontend_event_type(cls, event_type) -> str:
    #     """获取事件类型在前端使用的名称"""
    #     # 将任何类型的event_type转换为int
    #     try:
    #         event_type_int = int(event_type)
    #     except (ValueError, TypeError):
    #         import logging
    #         logger = logging.getLogger(__name__)
    #         logger.warning(f"非法的事件类型: {event_type}，类型: {type(event_type)}，回退到'text'")
    #         return "text"
        
    #     # 从映射中获取前端事件类型
    #     frontend_type = CHAT_EVENT_TYPE_TO_FRONTEND.get(event_type_int)
    #     if frontend_type is None:
    #         import logging
    #         logger = logging.getLogger(__name__)
    #         logger.warning(f"未知的事件类型: {event_type_int}，回退到'text'")
    #         return "text"
        
    #     return frontend_type


class ChatMessageSate(int, enum.Enum):
    TRACE = 0
    SOURCE_NODES = 1
    KG_RETRIEVAL = 2
    REFINE_QUESTION = 3
    SEARCH_RELATED_DOCUMENTS = 4
    DATABASE_QUERY = 5
    GENERATE_ANSWER = 6
    TOOL_CALL_PART = 7      # 工具调用
    TOOL_RESULT_PART =  8   # 工具调用结果
    FINISHED = 9
    QUERY_OPTIMIZATION = 10  # 查询优化阶段
    EXTERNAL_ENGINE_CALL = 11  # 外部引擎调用


# SQL执行配置类
class SQLExecutionConfig(BaseModel):
    """SQL执行配置"""
    llm: Optional[str] = "gpt-3.5-turbo"
    max_tokens: int = 4096
    temperature: float = 0.2
    top_p: float = 0.95
    model_name: Optional[str] = None
    debug: bool = False
