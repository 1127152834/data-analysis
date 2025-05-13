"""add_database_descriptions

为DatabaseConnection模型添加LLM描述相关字段

Revision ID: add_database_descriptions
Revises: dfee070b8abd
Create Date: 2023-12-01 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = 'add_database_descriptions'
down_revision: Union[str, None] = 'dfee070b8abd'  # 请根据实际情况修改上一个版本ID
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    添加与LLM相关的字段到数据库连接表:
    1. description_for_llm: 用于LLM的业务描述
    2. table_descriptions: 表描述的JSON字段
    3. column_descriptions: 列描述的JSON字段
    同时创建索引以优化查询性能
    """
    # 添加业务描述字段
    op.add_column('database_connections',
                  sa.Column('description_for_llm', sa.Text(), nullable=True,
                           comment='用于LLM的业务场景描述'))
    
    # 添加表描述JSON字段
    op.add_column('database_connections',
                  sa.Column('table_descriptions', mysql.JSON(), nullable=True,
                           comment='表描述信息，格式: {table_name: description}'))
    
    # 添加列描述JSON字段
    op.add_column('database_connections',
                  sa.Column('column_descriptions', mysql.JSON(), nullable=True,
                           comment='列描述信息，格式: {table_name: {column_name: description}}'))
    
    # 创建索引以优化查询 - 使用前缀索引以避免超过最大键长度限制
    op.create_index('ix_database_connections_description_for_llm',
                    'database_connections', ['description_for_llm(255)'], unique=False)


def downgrade() -> None:
    """
    回滚操作，移除添加的字段和索引
    """
    # 移除索引
    op.drop_index('ix_database_connections_description_for_llm', table_name='database_connections')
    
    # 移除字段
    op.drop_column('database_connections', 'column_descriptions')
    op.drop_column('database_connections', 'table_descriptions')
    op.drop_column('database_connections', 'description_for_llm') 