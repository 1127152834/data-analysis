"""modify_desc_to_text

将description_for_llm字段改为TEXT类型

Revision ID: modify_desc_text
Revises: check_database_descriptions
Create Date: 2023-12-06 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = 'modify_desc_text'  # 注意：较短的ID名称
down_revision: Union[str, None] = 'check_database_descriptions'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    该迁移脚本只更新版本号，实际修改已由前一个脚本完成
    """
    print("修改description_for_llm字段类型已经完成，仅更新版本记录")


def downgrade() -> None:
    """
    不执行任何实际操作
    """
    pass 