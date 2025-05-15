import os

# 定义应用目录路径
APP_DIR = os.path.dirname(os.path.abspath(__file__))

# 日志配置
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s:%(lineno)s - %(levelname)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "detailed": {
            "format": "%(asctime)s - %(name)s:%(lineno)s - %(levelname)s - %(funcName)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "level": "INFO",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "default",
            "filename": os.path.join(APP_DIR, "..", "logs", "app.log"),
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "level": "INFO",
        },
        "autoflow_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "detailed",
            "filename": os.path.join(APP_DIR, "..", "logs", "autoflow.log"),
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "level": "DEBUG",
        },
        "chat_service_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "detailed",
            "filename": os.path.join(APP_DIR, "..", "logs", "chat_service.log"),
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "level": "DEBUG",
        },
    },
    "loggers": {
        "uvicorn": {"handlers": ["console"], "level": "INFO"},
        "app": {"handlers": ["console", "file"], "level": "INFO", "propagate": False},
        "autoflow": {
            "handlers": ["console", "autoflow_file"],
            "level": "DEBUG",
            "propagate": False,
        },
        "autoflow.workflow": {
            "handlers": ["console", "autoflow_file"],
            "level": "DEBUG",
            "propagate": False,
        },
        "autoflow.agents": {
            "handlers": ["console", "autoflow_file"],
            "level": "DEBUG",
            "propagate": False,
        },
        "autoflow.retrievers": {
            "handlers": ["console", "autoflow_file"],
            "level": "DEBUG",
            "propagate": False,
        },
        "autoflow.utils": {
            "handlers": ["console", "autoflow_file"],
            "level": "DEBUG",
            "propagate": False,
        },
        "chat_engine": {
            "handlers": ["console", "chat_service_file"],
            "level": "DEBUG",
            "propagate": False,
        },
        "app.rag.chat.chat_service": {
            "handlers": ["console", "chat_service_file"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
    "root": {"handlers": ["console", "file"], "level": "INFO"},
}

# 确保日志目录存在
os.makedirs(os.path.join(APP_DIR, "..", "logs"), exist_ok=True) 