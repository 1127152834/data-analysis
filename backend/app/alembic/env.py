from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel
from tidb_vector.sqlalchemy import VectorType

from app.core.config import settings
from app.models import *  # noqa
from app.models.knowledge_base_scoped.table_naming import (
    KB_CHUNKS_TABLE_PATTERN,
    KB_ENTITIES_TABLE_PATTERN,
    KB_RELATIONSHIPS_TABLE_PATTERN,
)

# 获取Alembic配置对象（对应alembic.ini文件）
config = context.config

# 配置日志系统（使用alembic.ini中的日志配置）
fileConfig(config.config_file_name)

# 重要配置：设置目标元数据对象
# 使用SQLModel的元数据来自动检测模型变化
target_metadata = SQLModel.metadata

def get_url():
    """获取数据库连接URL"""
    # 从应用配置中获取数据库URI
    return str(settings.SQLALCHEMY_DATABASE_URI)

def include_name(name, type_, parent_names):
    """
    表/列名称过滤函数，用于控制Alembic的检测范围
    参数：
        name: 对象名称
        type_: 对象类型（'table'/'column'等）
        parent_names: 父对象名称
    返回：
        bool: 是否包含该对象
    """
    if type_ == "table":
        # 排除知识库的动态表（由其他模块管理）
        return not any([
            bool(KB_CHUNKS_TABLE_PATTERN.match(name)),
            bool(KB_ENTITIES_TABLE_PATTERN.match(name)),
            bool(KB_RELATIONSHIPS_TABLE_PATTERN.match(name))
        ])
    return True  # 总是包含非表对象

def run_migrations_offline():
    """离线模式运行迁移（生成SQL脚本）"""
    # 配置迁移上下文
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        include_name=include_name,  # 应用表过滤
        literal_binds=True,         # 生成具体值而非参数化查询
        compare_type=True,          # 检测字段类型变化
    )

    # 在事务中执行迁移
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    """在线模式运行迁移（直接操作数据库）"""
    # 获取配置并设置数据库URL
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_url()
    
    # 创建数据库引擎（使用空连接池）
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        # 注册TiDB向量类型支持
        connection.dialect.ischema_names["vector"] = VectorType
        
        # 配置迁移上下文
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_name=include_name,  # 应用表过滤
            compare_type=True,          # 检测字段类型变化
        )

        # 在事务中执行迁移
        with context.begin_transaction():
            context.run_migrations()

# 根据运行模式选择迁移方式
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
