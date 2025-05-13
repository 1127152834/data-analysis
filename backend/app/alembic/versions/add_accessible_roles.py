"""Change access_level to accessible_roles

Revision ID: add_accessible_roles
Revises: 000000000000
Create Date: 2024-05-13 12:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_accessible_roles'
down_revision = '000000000000'
branch_labels = None
depends_on = None


def upgrade():
    # 将多语句SQL拆分为单独的语句执行
    # 更新管理员级别的连接
    op.execute(
        "UPDATE database_connections SET accessible_roles = JSON_ARRAY('admin', 'user') WHERE access_level = 'admin'"
    )
    
    # 更新普通用户级别的连接
    op.execute(
        "UPDATE database_connections SET accessible_roles = JSON_ARRAY('admin') WHERE access_level = 'user' OR access_level IS NULL"
    )


def downgrade():
    # 无需降级操作，因为我们不想恢复到旧格式
    pass 