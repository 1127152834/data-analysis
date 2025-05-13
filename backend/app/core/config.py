import enum
from typing import Annotated, Any
from urllib.parse import quote
import os

from pydantic import (
    AnyUrl,
    BeforeValidator,
    HttpUrl,
    MySQLDsn,
    SecretStr,
    computed_field,
    model_validator,
)
from pydantic_core import MultiHostUrl
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing_extensions import Self


def parse_cors(v: Any) -> list[str] | str:
    """
    解析CORS配置值

    将逗号分隔的字符串转换为列表，方便在应用中使用

    参数:
        v: 输入的CORS配置值，可以是字符串或列表

    返回:
        解析后的CORS列表或原字符串

    异常:
        ValueError: 如果输入值无法解析为有效的CORS配置
    """
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",")]
    elif isinstance(v, list | str):
        return v
    raise ValueError(v)


class Environment(str, enum.Enum):
    """
    应用环境枚举类

    定义了应用可能运行的不同环境类型
    """

    LOCAL = "local"  # 本地开发环境
    STAGING = "staging"  # 预发布/测试环境
    PRODUCTION = "production"  # 生产环境


class Settings(BaseSettings):
    """
    应用配置设置类

    管理所有应用配置参数，支持从环境变量和.env文件加载配置
    """

    model_config = SettingsConfigDict(
        env_file=".env", env_ignore_empty=True, extra="ignore"
    )
    API_V1_STR: str = "/api/v1"  # API路径前缀
    SECRET_KEY: str  # 应用密钥，用于各种加密操作
    DOMAIN: str = "localhost"  # 应用域名
    ENVIRONMENT: Environment = Environment.LOCAL  # 运行环境
    LOG_LEVEL: str = "INFO"  # 日志级别
    SQLALCHEMY_LOG_LEVEL: str = "WARNING"  # SQLAlchemy日志级别

    SESSION_COOKIE_NAME: str = "session"  # 会话Cookie名称
    # 90天过期时间
    SESSION_COOKIE_MAX_AGE: int = 3600 * 24 * 90  # 会话Cookie最大寿命（秒）
    SESSION_COOKIE_SECURE: bool = False  # 是否仅在HTTPS下发送Cookie

    BROWSER_ID_COOKIE_NAME: str = "bid"  # 浏览器ID Cookie名称
    BROWSER_ID_COOKIE_MAX_AGE: int = (
        3600 * 24 * 365 * 2
    )  # 浏览器ID Cookie最大寿命（2年）

    @computed_field  # type: ignore[misc]
    @property
    def server_host(self) -> str:
        """
        获取服务器主机URL

        根据环境自动选择HTTP或HTTPS协议

        返回:
            完整的服务器主机URL
        """
        # 非本地环境使用HTTPS
        if self.ENVIRONMENT == Environment.LOCAL:
            return f"http://{self.DOMAIN}"
        return f"https://{self.DOMAIN}"

    BACKEND_CORS_ORIGINS: Annotated[
        list[AnyUrl] | str, BeforeValidator(parse_cors)
    ] = []  # 后端CORS允许的源

    PROJECT_NAME: str = "TiDB.AI"  # 项目名称
    SENTRY_DSN: HttpUrl | None = None  # Sentry错误追踪DSN
    SENTRY_TRACES_SAMPLE_RATE: float = 1.0  # Sentry追踪采样率
    SENTRY_PROFILES_SAMPLE_RATE: float = 1.0  # Sentry性能分析采样率

    @model_validator(mode="after")
    def _validate_sentry_sample_rate(self) -> Self:
        """
        验证Sentry采样率配置

        确保采样率在有效范围内（0到1之间）

        返回:
            验证后的设置对象

        异常:
            ValueError: 如果采样率无效
        """
        if not self.SENTRY_DSN:
            return self
        if self.SENTRY_TRACES_SAMPLE_RATE < 0 or self.SENTRY_TRACES_SAMPLE_RATE > 1:
            raise ValueError("SENTRY_TRACES_SAMPLE_RATE must be between 0 and 1")
        if self.SENTRY_PROFILES_SAMPLE_RATE < 0 or self.SENTRY_PROFILES_SAMPLE_RATE > 1:
            raise ValueError("SENTRY_PROFILES_SAMPLE_RATE must be between 0 and 1")
        return self

    TIDB_HOST: str = "127.0.0.1"  # TiDB数据库主机
    TIDB_PORT: int = 4000  # TiDB数据库端口
    TIDB_USER: str = "root"  # TiDB数据库用户名
    TIDB_PASSWORD: str = ""  # TiDB数据库密码
    TIDB_DATABASE: str  # TiDB数据库名称
    TIDB_SSL: bool = False  # 是否使用SSL连接TiDB

    ENABLE_QUESTION_CACHE: bool = False  # 是否启用问题缓存

    # 使用项目根目录下的data目录
    LOCAL_FILE_STORAGE_PATH: str = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
        "data",
    )  # 本地文件存储路径

    CELERY_BROKER_URL: str = "redis://127.0.0.1:6379/0"  # Celery消息代理URL
    CELERY_RESULT_BACKEND: str = "redis://127.0.0.1:6379/0"  # Celery结果后端URL

    # TODO: 将以下配置移至`option`表，使其可以通过控制台由管理员配置
    TIDB_AI_CHAT_ENDPOINT: str = "https://localhost:3001/api/v1/chats"  # TiDB.AI聊天API端点
    TIDB_AI_API_KEY: SecretStr | None = None  # TiDB.AI API密钥

    COMPLIED_INTENT_ANALYSIS_PROGRAM_PATH: str | None = None  # 意图分析程序路径
    COMPLIED_PREREQUISITE_ANALYSIS_PROGRAM_PATH: str | None = (
        None  # 前提条件分析程序路径
    )

    # 注意: EMBEDDING_DIMS和EMBEDDING_MAX_TOKENS已废弃
    # 将在未来移除
    EMBEDDING_DIMS: int = 1536  # 嵌入向量维度
    EMBEDDING_MAX_TOKENS: int = 2048  # 嵌入最大令牌数

    EVALUATION_OPENAI_API_KEY: str | None = None  # 评估用的OpenAI API密钥

    @computed_field  # type: ignore[misc]
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> MySQLDsn:
        """
        构建SQLAlchemy同步数据库URI

        返回:
            完整的数据库连接URI
        """
        return MultiHostUrl.build(
            scheme="mysql+pymysql",
            username=self.TIDB_USER,
            # TODO: 在以下问题修复后移除quote:
            # https://github.com/pydantic/pydantic/issues/8061
            password=quote(self.TIDB_PASSWORD),
            host=self.TIDB_HOST,
            port=self.TIDB_PORT,
            path=self.TIDB_DATABASE,
            query="ssl_verify_cert=true&ssl_verify_identity=true"
            if self.TIDB_SSL
            else None,
        )

    @computed_field  # type: ignore[misc]
    @property
    def SQLALCHEMY_ASYNC_DATABASE_URI(self) -> MySQLDsn:
        """
        构建SQLAlchemy异步数据库URI

        返回:
            完整的异步数据库连接URI
        """
        return MultiHostUrl.build(
            scheme="mysql+asyncmy",
            username=self.TIDB_USER,
            password=quote(self.TIDB_PASSWORD),
            host=self.TIDB_HOST,
            port=self.TIDB_PORT,
            path=self.TIDB_DATABASE,
        )

    @model_validator(mode="after")
    def _validate_secrets(self) -> Self:
        """
        验证安全密钥配置

        确保SECRET_KEY已设置且长度足够

        返回:
            验证后的设置对象

        异常:
            ValueError: 如果密钥未设置或长度不足
        """
        secret = self.SECRET_KEY
        if not secret:
            raise ValueError(
                "Please set a secret key using the SECRET_KEY environment variable."
            )

        min_length = 32
        if len(secret.encode()) < min_length:
            message = (
                "The SECRET_KEY is too short, "
                f"please use a longer secret, at least {min_length} characters."
            )
            raise ValueError(message)
        return self


settings = Settings()  # type: ignore  # 创建全局配置实例
