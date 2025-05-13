from fastapi import FastAPI, Request, Depends, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging
import os
import time
from typing import Optional, List

from app.api.routes import router as api_router
from app.api.auth import get_current_user
from app.core.config import settings
from app.core.database import init_db
from app.core.initialize import initialize_system
from app.models.user import User

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="AutoFlow API",
    description="AutoFlow API服务",
    version="1.0.0",
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加请求处理时间中间件
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# 包含API路由
app.include_router(api_router)

# 系统启动事件处理
@app.on_event("startup")
def on_startup():
    """应用启动时执行的操作"""
    logger.info("应用启动中...")
    
    # 初始化数据库
    init_db()
    
    # 初始化系统组件
    initialize_system()
    
    logger.info("应用启动完成")

# 主健康检查接口
@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "ok", "version": settings.VERSION}

# 运行应用
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    ) 