"""modify_description_for_llm_to_text

将description_for_llm字段从VARCHAR(1024)修改为TEXT类型

Revision ID: modify_description_for_llm_to_text
Revises: check_database_descriptions
Create Date: 2023-12-06 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects import mysql
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = 'modify_description_for_llm_to_text'
down_revision: Union[str, None] = 'check_database_descriptions'  # 上一个迁移版本
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    将description_for_llm字段类型从VARCHAR(1024)修改为TEXT
    同时确保在索引存在的情况下处理索引
    """
    conn = op.get_bind()
    
    # 检查索引是否存在，存在则先删除
    result = conn.execute(text(
        "SELECT INDEX_NAME FROM INFORMATION_SCHEMA.STATISTICS "
        "WHERE TABLE_NAME = 'database_connections' AND TABLE_SCHEMA = DATABASE() "
        "AND COLUMN_NAME = 'description_for_llm'"
    ))
    existing_indexes = [row[0] for row in result]
    
    # 如果存在索引先删除
    for index_name in existing_indexes:
        try:
            op.drop_index(index_name, table_name='database_connections')
            print(f"成功删除索引: {index_name}")
        except Exception as e:
            print(f"删除索引失败: {str(e)}")
    
    # 修改字段类型
    try:
        op.alter_column('database_connections', 'description_for_llm',
                       existing_type=sa.String(1024),
                       type_=sa.Text(),
                       existing_nullable=True)
        print("字段类型成功从VARCHAR(1024)修改为TEXT")
    except Exception as e:
        print(f"修改字段类型失败: {str(e)}")
    
    # 重新创建前缀索引
    try:
        op.execute(text(
            "CREATE INDEX ix_database_connections_description_for_llm "
            "ON database_connections (description_for_llm(255))"
        ))
        print("成功重新创建索引")
    except Exception as e:
        print(f"重新创建索引失败: {str(e)}")


def downgrade() -> None:
    """
    将description_for_llm字段类型从TEXT还原为VARCHAR(1024)
    """
    conn = op.get_bind()
    
    # 检查并删除可能存在的索引
    result = conn.execute(text(
        "SELECT INDEX_NAME FROM INFORMATION_SCHEMA.STATISTICS "
        "WHERE TABLE_NAME = 'database_connections' AND TABLE_SCHEMA = DATABASE() "
        "AND COLUMN_NAME = 'description_for_llm'"
    ))
    existing_indexes = [row[0] for row in result]
    
    for index_name in existing_indexes:
        try:
            op.drop_index(index_name, table_name='database_connections')
        except Exception:
            pass
    
    # 还原字段类型
    try:
        op.alter_column('database_connections', 'description_for_llm',
                       existing_type=sa.Text(),
                       type_=sa.String(1024),
                       existing_nullable=True)
    except Exception:
        pass
    
    # 重新创建索引（如果需要）
    try:
        op.create_index('ix_database_connections_description_for_llm',
                       'database_connections', ['description_for_llm'], unique=False)
    except Exception:
        pass 