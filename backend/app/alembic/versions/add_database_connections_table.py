"""add_database_connections_table

创建数据库连接表的迁移脚本

Revision ID: add_database_connections
Revises: dfee070b8abd
Create Date: 2023-08-17 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = 'add_database_connections'
down_revision: Union[str, None] = 'dfee070b8abd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### 创建数据库连接表 ###
    op.create_table(
        'database_connections',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=256), nullable=False),
        sa.Column('description', sa.String(length=512), nullable=False),
        sa.Column('database_type', sa.String(length=32), nullable=False),
        sa.Column('config', mysql.JSON(), nullable=True),
        sa.Column('user_id', sa.CHAR(length=36), nullable=True),
        sa.Column('read_only', sa.Boolean(), nullable=False, default=True),
        sa.Column('connection_status', sa.String(length=32), nullable=False, 
                  default='disconnected'),
        sa.Column('last_connected_at', sa.DateTime(), nullable=True),
        sa.Column('metadata_cache', mysql.JSON(), nullable=True),
        sa.Column('metadata_updated_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), 
                  onupdate=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='database_connections_user_id_fkey'),
        sa.PrimaryKeyConstraint('id', name='database_connections_pkey')
    )
    op.create_index('ix_database_connections_id', 'database_connections', ['id'], unique=False)


def downgrade() -> None:
    # ### 删除数据库连接表 ###
    op.drop_index('ix_database_connections_id', table_name='database_connections')
    op.drop_table('database_connections') 