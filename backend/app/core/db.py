import ssl
import contextlib
from typing import AsyncGenerator, Generator

from sqlmodel import create_engine, Session
from sqlalchemy import event
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings


# TiDB Serverless集群限制：如果5分钟内没有活动连接，集群将关闭并断开所有连接，
# 因此我们需要定期回收连接以保持活动状态
engine = create_engine(
    str(settings.SQLALCHEMY_DATABASE_URI),
    pool_size=20,  # 连接池大小
    max_overflow=40,  # 允许的最大连接溢出数
    pool_recycle=300,  # 连接回收时间（秒）
    pool_pre_ping=True,  # 使用前先ping测试连接是否有效
)

# 创建作用域会话，确保在多线程环境中，每个线程都有自己的会话实例
Scoped_Session = scoped_session(sessionmaker(bind=engine, class_=Session))


def get_ssl_context():
    """
    创建SSL上下文配置

    为数据库连接创建安全的SSL上下文，确保连接加密和安全

    返回:
        ssl.SSLContext: 配置好的SSL上下文对象
    """
    ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2  # 设置最低TLS版本为1.2
    ssl_context.check_hostname = True  # 启用主机名检查
    return ssl_context


# 创建异步数据库引擎
async_engine = create_async_engine(
    str(settings.SQLALCHEMY_ASYNC_DATABASE_URI),
    pool_recycle=300,  # 连接回收时间（秒）
    connect_args={
        # 注意：在URL中配置SSL似乎不起作用
        # 我们只能在connect_args中配置SSL
        "ssl": get_ssl_context(),
    }
    if settings.TIDB_SSL
    else {},
)


def prepare_db_connection(dbapi_connection, connection_record):
    """
    准备数据库连接的回调函数

    在连接建立时设置数据库连接参数，如时区等

    参数:
        dbapi_connection: 数据库API连接对象
        connection_record: 连接记录对象
    """
    cursor = dbapi_connection.cursor()
    # 在TiDB.AI中，我们使用UTC时区在数据库中存储日期时间。
    # 因此，需要将时区设置为'+00:00'。
    cursor.execute("SET time_zone = '+00:00'")
    cursor.close()


# 注册数据库连接事件监听器
event.listen(engine, "connect", prepare_db_connection)
event.listen(async_engine.sync_engine, "connect", prepare_db_connection)


def get_db_session() -> Generator[Session, None, None]:
    """
    获取同步数据库会话

    创建并yield一个同步数据库会话，用于依赖注入

    返回:
        Generator[Session, None, None]: 数据库会话生成器
    """
    with Session(engine, expire_on_commit=False) as session:
        yield session


async def get_db_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    获取异步数据库会话

    创建并yield一个异步数据库会话，用于异步依赖注入

    返回:
        AsyncGenerator[AsyncSession, None]: 异步数据库会话生成器
    """
    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        yield session


# 创建异步上下文管理器，方便在异步函数中使用
get_db_async_session_context = contextlib.asynccontextmanager(get_db_async_session)
