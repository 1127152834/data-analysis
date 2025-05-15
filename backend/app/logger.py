import logging  # 导入日志模块
from logging.config import dictConfig  # 导入字典配置工具
from app.core.config import settings  # 导入应用配置

# 创建API服务器日志记录器
logger = logging.getLogger("api_server")


# 配置日志系统
dictConfig(
    {
        "version": 1,  # 日志配置版本
        "disable_existing_loggers": False,  # 不禁用现有的日志记录器
        "formatters": {
            "default": {
                # 定义默认日志格式：时间 - 名称:行号 - 日志级别 - 消息
                "format": "%(asctime)s - %(name)s:%(lineno)d - %(levelname)s - %(message)s",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",  # 使用控制台处理器
                "formatter": "default",  # 使用默认格式化器
            },
        },
        "root": {
            "level": settings.LOG_LEVEL,  # 设置根日志记录器级别
            "handlers": ["console"],  # 使用控制台处理器
        },
        "loggers": {
            "uvicorn.error": {
                "level": "ERROR",  # uvicorn错误日志级别
                "handlers": ["console"],
                "propagate": False,  # 不传播到父级记录器
            },
            "uvicorn.access": {
                "level": "WARNING",  # 修改uvicorn访问日志级别为WARNING，减少API请求日志
                "handlers": ["console"],
                "propagate": False,
            },
            "httpx": {
                "level": "WARNING",  # 添加httpx日志级别为WARNING，减少HTTP请求日志
                "handlers": ["console"],
                "propagate": False,
            },
            "sqlalchemy.engine": {
                "level": settings.SQLALCHEMY_LOG_LEVEL,  # 数据库引擎日志级别
                "handlers": ["console"],
                "propagate": False,
            },
            "knowledge_base": {
                "level": "DEBUG",  # 知识库日志级别
                "handlers": ["console"],
                "propagate": False,
            },
            "chat_engine": {
                "level": "DEBUG",  # 聊天引擎日志级别
                "handlers": ["console"],
                "propagate": False,
            },
        },
    }
)
