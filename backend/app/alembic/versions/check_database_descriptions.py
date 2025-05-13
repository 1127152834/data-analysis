"""check_database_descriptions

安全检查并添加LLM描述相关字段（如果不存在）

Revision ID: check_database_descriptions
Revises: dfee070b8abd
Create Date: 2023-12-05 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects import mysql
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = 'check_database_descriptions'
down_revision: Union[str, None] = 'dfee070b8abd'  # 请根据实际情况修改上一个版本ID
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    安全地检查并添加LLM相关字段（如果不存在）:
    1. 检查description_for_llm是否存在，不存在则添加
    2. 检查table_descriptions是否存在，不存在则添加  
    3. 检查column_descriptions是否存在，不存在则添加
    4. 检查相关索引是否存在，不存在则添加
    """
    # 获取数据库连接
    conn = op.get_bind()
    
    # 检查列是否存在
    has_description_for_llm = False
    has_table_descriptions = False
    has_column_descriptions = False
    
    # 查询表结构
    result = conn.execute(text(
        "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
        "WHERE TABLE_NAME = 'database_connections' AND TABLE_SCHEMA = DATABASE()"
    ))
    existing_columns = [row[0] for row in result]
    
    has_description_for_llm = 'description_for_llm' in existing_columns
    has_table_descriptions = 'table_descriptions' in existing_columns
    has_column_descriptions = 'column_descriptions' in existing_columns
    
    # 添加不存在的列
    if not has_description_for_llm:
        op.add_column('database_connections',
                      sa.Column('description_for_llm', sa.Text(), nullable=True,
                               comment='用于LLM的业务场景描述'))
    
    if not has_table_descriptions:
        op.add_column('database_connections',
                      sa.Column('table_descriptions', mysql.JSON(), nullable=True,
                               comment='表描述信息，格式: {table_name: description}'))
    
    if not has_column_descriptions:
        op.add_column('database_connections',
                      sa.Column('column_descriptions', mysql.JSON(), nullable=True,
                               comment='列描述信息，格式: {table_name: {column_name: description}}'))
    
    # 检查索引是否存在
    result = conn.execute(text(
        "SELECT INDEX_NAME FROM INFORMATION_SCHEMA.STATISTICS "
        "WHERE TABLE_NAME = 'database_connections' AND TABLE_SCHEMA = DATABASE()"
    ))
    existing_indexes = [row[0] for row in result]
    
    # 添加索引（如果不存在）
    if 'ix_database_connections_description_for_llm' not in existing_indexes:
        # 创建索引 - VARCHAR类型需要使用正确的语法
        try:
            op.execute(text(
                "CREATE INDEX ix_database_connections_description_for_llm "
                "ON database_connections (description_for_llm(255))"
            ))
        except Exception as e:
            print(f"创建索引时发生错误: {str(e)}")
            # 尝试不使用前缀索引直接创建 
            try:
                op.create_index('ix_database_connections_description_for_llm',
                                'database_connections', ['description_for_llm'], unique=False)
            except Exception as e2:
                print(f"尝试创建无前缀索引也失败: {str(e2)}")
                # 报错但继续执行，不要阻断迁移


def downgrade() -> None:
    """
    回滚操作，移除添加的字段和索引
    注意：由于是条件添加，回滚时不确定哪些列已添加，所以尝试删除所有可能的列
    """
    # 尝试删除索引（如果存在）
    try:
        op.drop_index('ix_database_connections_description_for_llm', table_name='database_connections')
    except Exception:
        pass
    
    # 尝试删除列（如果存在）
    try:
        op.drop_column('database_connections', 'column_descriptions')
    except Exception:
        pass
    
    try:
        op.drop_column('database_connections', 'table_descriptions')
    except Exception:
        pass
    
    try:
        op.drop_column('database_connections', 'description_for_llm')
    except Exception:
        pass 