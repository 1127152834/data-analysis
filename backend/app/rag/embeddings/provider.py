import enum

from typing import List
from pydantic import BaseModel


class EmbeddingProvider(str, enum.Enum):
    OPENAI = "openai"
    JINA = "jina"
    COHERE = "cohere"
    BEDROCK = "bedrock"
    OLLAMA = "ollama"
    GITEEAI = "giteeai"
    LOCAL = "local"
    OPENAI_LIKE = "openai_like"
    AZURE_OPENAI = "azure_openai"


class EmbeddingProviderOption(BaseModel):
    provider: EmbeddingProvider
    provider_display_name: str | None = None
    provider_description: str | None = None
    provider_url: str | None = None
    default_embedding_model: str
    embedding_model_description: str
    default_config: dict = {}
    config_description: str = ""
    default_credentials: str | dict = ""
    credentials_display_name: str
    credentials_description: str
    credentials_type: str = "str"


embedding_provider_options: List[EmbeddingProviderOption] = [
    EmbeddingProviderOption(
        provider=EmbeddingProvider.OPENAI,
        provider_display_name="OpenAI",
        provider_description="OpenAI API 为开发者提供了一个简单的接口，用于在其应用程序中创建智能层，由 OpenAI 的最先进模型提供支持。",
        provider_url="https://platform.openai.com",
        default_embedding_model="text-embedding-3-small",
        embedding_model_description="在 https://platform.openai.com/docs/guides/embeddings 查找有关 OpenAI Embedding 的更多信息",
        credentials_display_name="OpenAI API 密钥",
        credentials_description="OpenAI 的 API 密钥，您可以在 https://platform.openai.com/api-keys 找到它",
        credentials_type="str",
        default_credentials="sk-****",
    ),
    EmbeddingProviderOption(
        provider=EmbeddingProvider.JINA,
        provider_display_name="JinaAI",
        provider_description="Jina AI 提供多模态、双语长上下文嵌入，用于搜索和 RAG",
        provider_url="https://jina.ai/embeddings/",
        default_embedding_model="jina-embeddings-v2-base-en",
        embedding_model_description="在 https://jina.ai/embeddings/ 查找有关 Jina AI Embeddings 的更多信息",
        credentials_display_name="Jina API 密钥",
        credentials_description="Jina 的 API 密钥，您可以在 https://jina.ai/embeddings/ 找到它",
        credentials_type="str",
        default_credentials="jina_****",
    ),
    EmbeddingProviderOption(
        provider=EmbeddingProvider.COHERE,
        provider_display_name="Cohere",
        provider_description="Cohere 提供行业领先的大型语言模型 (LLM) 和 RAG 功能，专为满足解决现实世界问题的企业用例需求而定制。",
        provider_url="https://cohere.com/embeddings",
        default_embedding_model="embed-multilingual-v3.0",
        embedding_model_description="文档：https://docs.cohere.com/docs/cohere-embed",
        credentials_display_name="Cohere API 密钥",
        credentials_description="您可以从 https://dashboard.cohere.com/api-keys 获取一个",
        credentials_type="str",
        default_credentials="*****",
    ),
    EmbeddingProviderOption(
        provider=EmbeddingProvider.BEDROCK,
        provider_display_name="Bedrock",
        provider_description="Amazon Bedrock 是一个完全托管的基础模型服务。",
        provider_url="https://docs.aws.amazon.com/bedrock/",
        default_embedding_model="amazon.titan-embed-text-v2:0",
        embedding_model_description="",
        credentials_display_name="AWS Bedrock 凭证 JSON",
        credentials_description="AWS 凭证的 JSON 对象，参考 https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html#cli-configure-files-global",
        credentials_type="dict",
        default_credentials={
            "aws_access_key_id": "****",
            "aws_secret_access_key": "****",
            "aws_region_name": "us-west-2",
        },
    ),
    EmbeddingProviderOption(
        provider=EmbeddingProvider.OLLAMA,
        provider_display_name="Ollama",
        provider_description="Ollama 是一个用于构建和运行大型语言模型和嵌入模型的轻量级框架。",
        provider_url="https://ollama.com",
        default_embedding_model="nomic-embed-text",
        embedding_model_description="文档：https://ollama.com/blog/embedding-models",
        default_config={
            "api_base": "http://localhost:11434",
        },
        config_description="api_base 是 Ollama 服务器的基本 URL，确保它可以从此服务器访问。",
        credentials_display_name="Ollama API 密钥",
        credentials_description="Ollama 不需要 API 密钥，在这里设置一个虚拟字符串即可",
        credentials_type="str",
        default_credentials="dummy",
    ),
    EmbeddingProviderOption(
        provider=EmbeddingProvider.OPENAI_LIKE,
        provider_display_name="OpenAI Like",
        provider_description="OpenAI Like 是一组提供类似于 OpenAI 的文本嵌入的平台。例如智谱 AI。",
        provider_url="https://open.bigmodel.cn/dev/api/vector/embedding-3",
        default_embedding_model="embedding-3",
        embedding_model_description="",
        credentials_display_name="OpenAI Like API 密钥",
        credentials_description="OpenAI Like 的 API 密钥。对于智谱 AI，您可以在 https://open.bigmodel.cn/usercenter/apikeys 找到它",
        credentials_type="str",
        default_credentials="dummy",
    ),
    EmbeddingProviderOption(
        provider=EmbeddingProvider.GITEEAI,
        provider_display_name="Gitee AI",
        provider_description="Gitee AI 是一个第三方模型提供商，为 AI 开发者提供即用型的前沿模型 API。",
        provider_url="https://ai.gitee.com",
        default_embedding_model="bge-large-zh-v1.5",
        embedding_model_description="在 https://ai.gitee.com/docs/openapi/v1#tag/%E7%89%B9%E5%BE%81%E6%8A%BD%E5%8F%96/POST/embeddings 查找有关 Gitee AI Embeddings 的更多信息",
        credentials_display_name="Gitee AI API 密钥",
        credentials_description="Gitee AI 的 API 密钥，您可以在 https://ai.gitee.com/dashboard/settings/tokens 找到它",
        credentials_type="str",
        default_credentials="****",
    ),
    EmbeddingProviderOption(
        provider=EmbeddingProvider.AZURE_OPENAI,
        provider_display_name="Azure OpenAI",
        provider_description="Azure OpenAI 是一种基于云的 AI 服务，提供一套 AI 模型和工具，供开发人员构建智能应用程序。",
        provider_url="https://azure.microsoft.com/en-us/products/ai-services/openai-service",
        default_embedding_model="text-embedding-3-small",
        embedding_model_description="在使用此选项之前，您需要部署 Azure OpenAI API 和模型，参见 https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/create-resource。",
        default_config={
            "azure_endpoint": "https://<your-resource-name>.openai.azure.com/",
            "api_version": "<your-api-version>",
        },
        credentials_display_name="Azure OpenAI API 密钥",
        credentials_description="Azure OpenAI 的 API 密钥",
        credentials_type="str",
        default_credentials="****",
    ),
    EmbeddingProviderOption(
        provider=EmbeddingProvider.LOCAL,
        provider_display_name="本地嵌入",
        provider_description="Autoflow 的本地嵌入服务器，部署在您自己的基础设施上，由 sentence-transformers 提供支持。",
        default_embedding_model="BAAI/bge-m3",
        embedding_model_description="在 huggingface 中查找更多模型。",
        default_config={
            "api_url": "http://local-embedding-reranker:5001/api/v1/embedding",
        },
        config_description="api_url 是由 autoflow 本地嵌入服务器提供服务的嵌入端点 url。",
        credentials_display_name="本地嵌入 API 密钥",
        credentials_description="本地嵌入服务器不需要 API 密钥，在这里设置一个虚拟字符串即可。",
        credentials_type="str",
        default_credentials="dummy",
    ),
]
