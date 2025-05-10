import enum

from typing import List
from pydantic import BaseModel


class LLMProvider(str, enum.Enum):
    OPENAI = "openai"
    GEMINI = "gemini"
    VERTEX_AI = "vertex_ai"
    ANTHROPIC_VERTEX = "anthropic_vertex"  # Deprecated, use VERTEX_AI instead
    OPENAI_LIKE = "openai_like"
    BEDROCK = "bedrock"
    OLLAMA = "ollama"
    GITEEAI = "giteeai"
    AZURE_OPENAI = "azure_openai"


class LLMProviderOption(BaseModel):
    provider: LLMProvider
    provider_display_name: str | None = None
    provider_description: str | None = None
    provider_url: str | None = None
    default_llm_model: str
    llm_model_description: str
    default_config: dict = {}
    config_description: str = ""
    default_credentials: str | dict = ""
    credentials_display_name: str
    credentials_description: str
    credentials_type: str = "str"


llm_provider_options: List[LLMProviderOption] = [
    LLMProviderOption(
        provider=LLMProvider.OPENAI,
        provider_display_name="OpenAI",
        provider_description="OpenAI API为开发者提供了一个简单的接口，使他们能够在应用程序中创建智能层，由OpenAI的最先进模型提供支持。",
        provider_url="https://platform.openai.com",
        default_llm_model="gpt-4o",
        llm_model_description="",
        credentials_display_name="OpenAI API密钥",
        credentials_description="OpenAI的API密钥，可以在https://platform.openai.com/api-keys找到",
        credentials_type="str",
        default_credentials="sk-****",
    ),
    LLMProviderOption(
        provider=LLMProvider.OPENAI_LIKE,
        provider_display_name="OpenAI兼容接口",
        default_llm_model="",
        llm_model_description="",
        default_config={
            "api_base": "https://openrouter.ai/api/v1/",
            "is_chat_model": True,
        },
        config_description=(
            "`api_base`是第三方OpenAI兼容服务的API基础URL，例如OpenRouter；"
            "`is_chat_model`表示模型是否为聊天模型；"
            "`context_window`是输入令牌和输出令牌的最大数量；"
        ),
        credentials_display_name="API密钥",
        credentials_description="第三方OpenAI兼容服务的API密钥，例如OpenRouter，可以在其官方网站找到",
        credentials_type="str",
        default_credentials="sk-****",
    ),
    LLMProviderOption(
        provider=LLMProvider.GEMINI,
        provider_display_name="Gemini",
        provider_description="Gemini API和Google AI Studio帮助您开始使用Google的最新模型。访问整个Gemini模型系列，将您的想法转化为可扩展的实际应用。",
        provider_url="https://ai.google.dev/gemini-api",
        default_llm_model="models/gemini-2.0-flash",
        llm_model_description="在https://ai.google.dev/gemini-api/docs/models/gemini查找模型代码",
        credentials_display_name="Google API密钥",
        credentials_description="Google AI Studio的API密钥，可以在https://aistudio.google.com/app/apikey找到",
        credentials_type="str",
        default_credentials="AIza****",
    ),
    LLMProviderOption(
        provider=LLMProvider.VERTEX_AI,
        provider_display_name="Vertex AI",
        provider_description="Vertex AI是一个完全托管的、统一的AI开发平台，用于构建和使用生成式AI。",
        provider_url="https://cloud.google.com/vertex-ai",
        default_llm_model="gemini-1.5-flash",
        llm_model_description="在https://cloud.google.com/model-garden查找更多信息",
        credentials_display_name="Google凭证JSON",
        credentials_description="Google凭证的JSON对象，参考https://cloud.google.com/docs/authentication/provide-credentials-adc#on-prem",
        credentials_type="dict",
        default_credentials={
            "type": "service_account",
            "project_id": "****",
            "private_key_id": "****",
        },
    ),
    LLMProviderOption(
        provider=LLMProvider.OLLAMA,
        provider_display_name="Ollama",
        provider_description="Ollama是一个轻量级框架，用于构建和运行大型语言模型。",
        provider_url="https://ollama.com",
        default_llm_model="llama3.2",
        llm_model_description="在https://ollama.com/library查找更多信息",
        default_config={
            "base_url": "http://localhost:11434",
            "context_window": 8192,
            "request_timeout": 60 * 10,
        },
        config_description=(
            "`base_url`是Ollama服务器的基础URL，确保从此服务器可以访问；"
            "`context_window`是输入令牌和输出令牌的最大数量；"
            "`request_timeout`是等待生成响应的最长时间。"
        ),
        credentials_display_name="Ollama API密钥",
        credentials_description="Ollama不需要API密钥，在这里设置一个虚拟字符串即可",
        credentials_type="str",
        default_credentials="dummy",
    ),
    LLMProviderOption(
        provider=LLMProvider.GITEEAI,
        provider_display_name="Gitee AI",
        provider_description="Gitee AI是一个第三方模型提供商，为AI开发者提供现成可用的前沿模型API。",
        provider_url="https://ai.gitee.com",
        default_llm_model="Qwen2.5-72B-Instruct",
        default_config={
            "is_chat_model": True,
            "context_window": 131072,
        },
        config_description=(
            "`is_chat_model`表示模型是否为聊天模型；"
            "`context_window`是输入令牌和输出令牌的最大数量；"
        ),
        llm_model_description="在https://ai.gitee.com/serverless-api查找更多信息",
        credentials_display_name="Gitee AI API密钥",
        credentials_description="Gitee AI的API密钥，可以在https://ai.gitee.com/dashboard/settings/tokens找到",
        credentials_type="str",
        default_credentials="****",
    ),
    LLMProviderOption(
        provider=LLMProvider.BEDROCK,
        provider_display_name="Bedrock",
        provider_description="Amazon Bedrock是一项完全托管的基础模型服务。",
        provider_url="https://docs.aws.amazon.com/bedrock/",
        default_llm_model="anthropic.claude-3-7-sonnet-20250219-v1:0",
        llm_model_description="",
        credentials_display_name="AWS Bedrock凭证JSON",
        credentials_description="AWS凭证的JSON对象，参考https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html#cli-configure-files-global",
        credentials_type="dict",
        default_credentials={
            "aws_access_key_id": "****",
            "aws_secret_access_key": "****",
            "aws_region_name": "us-west-2",
        },
    ),
    LLMProviderOption(
        provider=LLMProvider.AZURE_OPENAI,
        provider_display_name="Azure OpenAI",
        provider_description="Azure OpenAI是一种基于云的AI服务，提供对OpenAI先进语言模型的访问。",
        provider_url="https://azure.microsoft.com/en-us/products/ai-services/openai-service",
        default_llm_model="gpt-4o",
        llm_model_description="",
        config_description="参考此文档https://learn.microsoft.com/en-us/azure/ai-services/openai/quickstart以获取有关Azure OpenAI API的更多信息。",
        default_config={
            "azure_endpoint": "https://<your-resource-name>.openai.azure.com/",
            "api_version": "<your-api-version>",
            "engine": "<your-deployment-name>",
        },
        credentials_display_name="Azure OpenAI API密钥",
        credentials_description="Azure OpenAI的API密钥",
        credentials_type="str",
        default_credentials="****",
    ),
]
