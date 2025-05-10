from http import HTTPStatus
from uuid import UUID

from fastapi import HTTPException

# Common（通用异常）


class InternalServerError(HTTPException):
    """内部服务器错误，表示系统内部发生了未预期的错误"""

    def __init__(self):
        super().__init__(HTTPStatus.INTERNAL_SERVER_ERROR)


# Chat（聊天相关异常）


class ChatException(HTTPException):
    """聊天功能相关异常的基类"""

    pass


class ChatNotFound(ChatException):
    """聊天记录未找到异常，当请求的聊天ID不存在时抛出"""

    status_code = 404

    def __init__(self, chat_id: UUID):
        self.detail = f"chat #{chat_id} is not found"


class ChatMessageNotFound(ChatException):
    """聊天消息未找到异常，当请求的消息ID不存在时抛出"""

    status_code = 404

    def __init__(self, message_id: int):
        self.detail = f"chat message #{message_id} is not found"


# LLM（大语言模型相关异常）


class LLMException(HTTPException):
    """大语言模型相关异常的基类"""

    pass


class LLMNotFound(LLMException):
    """大语言模型未找到异常，当请求的LLM ID不存在时抛出"""

    status_code = 404

    def __init__(self, llm_id: int):
        self.detail = f"llm #{llm_id} is not found"


class DefaultLLMNotFound(LLMException):
    """默认大语言模型未找到异常，当系统未配置默认LLM时抛出"""

    status_code = 404

    def __init__(self):
        self.detail = "default llm is not found"


# Embedding model（嵌入模型相关异常）


class EmbeddingModelException(HTTPException):
    """嵌入模型相关异常的基类"""

    pass


class EmbeddingModelNotFound(EmbeddingModelException):
    """嵌入模型未找到异常，当请求的嵌入模型ID不存在时抛出"""

    status_code = 404

    def __init__(self, model_id: int):
        self.detail = f"embedding model with id {model_id} not found"


class DefaultEmbeddingModelNotFound(EmbeddingModelException):
    """默认嵌入模型未找到异常，当系统未配置默认嵌入模型时抛出"""

    status_code = 404

    def __init__(self):
        self.detail = "default embedding model is not found"


# Reranker model（重排模型相关异常）


class RerankerModelException(HTTPException):
    """重排模型相关异常的基类"""

    pass


class RerankerModelNotFound(RerankerModelException):
    """重排模型未找到异常，当请求的重排模型ID不存在时抛出"""

    status_code = 404

    def __init__(self, model_id: int):
        self.detail = f"reranker model #{model_id} not found"


class DefaultRerankerModelNotFound(RerankerModelException):
    """默认重排模型未找到异常，当系统未配置默认重排模型时抛出"""

    status_code = 404

    def __init__(self):
        self.detail = "default reranker model is not found"


# Knowledge base（知识库相关异常）


class KBException(HTTPException):
    """知识库相关异常的基类"""

    pass


class KBNotFound(KBException):
    """知识库未找到异常，当请求的知识库ID不存在时抛出"""

    status_code = 404

    def __init__(self, knowledge_base_id: int):
        self.detail = f"knowledge base #{knowledge_base_id} is not found"


class KBDataSourceNotFound(KBException):
    """知识库数据源未找到异常，当请求的数据源ID在指定知识库中不存在时抛出"""

    status_code = 404

    def __init__(self, kb_id: int, data_source_id: int):
        self.detail = (
            f"data source #{data_source_id} is not found in knowledge base #{kb_id}"
        )


class KBNoLLMConfigured(KBException):
    """知识库未配置LLM异常，当知识库未配置大语言模型时抛出"""

    status_code = 500

    def __init__(self):
        self.detail = "must configured a LLM for knowledge base"


class KBNoEmbedModelConfigured(KBException):
    """知识库未配置嵌入模型异常，当知识库未配置嵌入模型时抛出"""

    status_code = 500

    def __init__(self):
        self.detail = "must configured a embedding model for knowledge base"


class KBNoVectorIndexConfigured(KBException):
    """知识库未配置向量索引异常，当知识库未将向量索引配置为索引方法之一时抛出"""

    status_code = 500

    def __init__(self):
        self.detail = "must configured vector index as one of the index method for knowledge base, which is required for now"


class KBNotAllowedUpdateEmbedModel(KBException):
    """知识库不允许更新嵌入模型异常，一旦知识库创建完成，就不允许更改嵌入模型"""

    status_code = 500

    def __init__(self):
        self.detail = "update embedding model is not allowed once the knowledge base has been created"


class KBIsUsedByChatEngines(KBException):
    """知识库被聊天引擎使用异常，当知识库被聊天引擎使用时，不允许删除"""

    status_code = 500

    def __init__(self, kb_id, chat_engines_num: int):
        self.detail = f"knowledge base #{kb_id} is used by {chat_engines_num} chat engines, please unlink them before deleting"


# Document（文档相关异常）


class DocumentException(HTTPException):
    """文档相关异常的基类"""

    pass


class DocumentNotFound(DocumentException):
    """文档未找到异常，当请求的文档ID不存在时抛出"""

    status_code = 404

    def __init__(self, document_id: int):
        self.detail = f"document #{document_id} is not found"


# Chat engine（聊天引擎相关异常）


class ChatEngineException(HTTPException):
    """聊天引擎相关异常的基类"""

    pass


class ChatEngineNotFound(ChatEngineException):
    """聊天引擎未找到异常，当请求的聊天引擎ID不存在时抛出"""

    status_code = 404

    def __init__(self, chat_engine_id: int):
        self.detail = f"chat engine #{chat_engine_id} is not found"


class DefaultChatEngineCannotBeDeleted(ChatEngineException):
    """默认聊天引擎不能删除异常，系统默认的聊天引擎不允许被删除"""

    status_code = 400

    def __init__(self, chat_engine_id: int):
        self.detail = f"default chat engine #{chat_engine_id} cannot be deleted"
