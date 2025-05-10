import os
import sys

# 添加项目根目录到PYTHONPATH
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(backend_dir)

# 导入TiFlash补丁，确保在创建向量索引时自动设置TiFlash副本
try:
    import tiflash_patch

    print("TiFlash补丁已加载，向量索引将自动设置TiFlash副本")
except ImportError:
    print("警告: 未能导入TiFlash补丁模块，向量索引功能可能受到影响")

import app.logger  # 导入应用日志配置
import sentry_sdk  # 导入Sentry错误追踪SDK

from dotenv import load_dotenv  # 导入环境变量加载工具
from contextlib import asynccontextmanager  # 导入异步上下文管理器
from fastapi import FastAPI, Request, Response  # 导入FastAPI核心组件
from fastapi.routing import APIRoute  # 导入API路由组件
from starlette.middleware.cors import CORSMiddleware  # 导入CORS中间件
from app.api.main import api_router  # 导入API路由配置
from app.core.config import settings  # 导入应用配置
from app.site_settings import SiteSetting  # 导入站点设置
from app.utils.uuid6 import uuid7  # 导入UUID7工具函数


# 加载环境变量
load_dotenv()


def custom_generate_unique_id(route: APIRoute) -> str:
    """
    为API路由生成唯一ID

    参数:
        route: API路由对象

    返回:
        格式为"{标签}-{名称}"的唯一标识符
    """
    return f"{route.tags[0]}-{route.name}"


# 如果配置了Sentry并且不是本地环境，则初始化Sentry
if settings.SENTRY_DSN and settings.ENVIRONMENT != "local":
    sentry_sdk.init(
        dsn=str(settings.SENTRY_DSN),
        enable_tracing=True,  # 启用追踪
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,  # 设置追踪采样率
        profiles_sample_rate=settings.SENTRY_PROFILES_SAMPLE_RATE,  # 设置性能分析采样率
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理函数

    在应用启动时更新站点设置缓存

    参数:
        app: FastAPI应用实例
    """
    SiteSetting.update_db_cache()
    yield


# 创建FastAPI应用实例
app = FastAPI(
    title=settings.PROJECT_NAME,  # 设置应用标题
    openapi_url=f"{settings.API_V1_STR}/openapi.json",  # 设置OpenAPI文档URL
    generate_unique_id_function=custom_generate_unique_id,  # 设置唯一ID生成函数
    lifespan=lifespan,  # 设置生命周期管理函数
)


# 设置CORS策略
# 如果配置了后端CORS源，则添加CORS中间件
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            str(origin).strip("/") for origin in settings.BACKEND_CORS_ORIGINS
        ],  # 允许的源
        allow_credentials=True,  # 允许凭证
        allow_methods=["*"],  # 允许所有HTTP方法
        allow_headers=["*"],  # 允许所有HTTP头
    )


@app.middleware("http")
async def identify_browser(request: Request, call_next):
    """
    HTTP中间件：识别浏览器并管理浏览器ID

    参数:
        request: HTTP请求对象
        call_next: 下一个处理函数

    返回:
        处理后的HTTP响应
    """
    # 从Cookie中获取浏览器ID
    browser_id = request.cookies.get(settings.BROWSER_ID_COOKIE_NAME)
    has_browser_id = bool(browser_id)
    # 如果没有浏览器ID，则创建一个新的
    if not browser_id:
        browser_id = uuid7()
    # 将浏览器ID存储在请求状态中
    request.state.browser_id = browser_id
    # 调用下一个处理函数
    response: Response = await call_next(request)
    # 如果之前没有浏览器ID，则在响应中设置Cookie
    if not has_browser_id:
        response.set_cookie(
            settings.BROWSER_ID_COOKIE_NAME,
            browser_id,
            max_age=settings.BROWSER_ID_COOKIE_MAX_AGE,
        )
    return response


# 包含API路由，并设置前缀
app.include_router(api_router, prefix=settings.API_V1_STR)
