"""merge_heads

Revision ID: a5dc883f0e8c
Revises: modify_desc_text, 211f3c5aa125, add_database_connections
Create Date: 2025-05-13 02:10:29.305249

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from tidb_vector.sqlalchemy import VectorType


# revision identifiers, used by Alembic.
revision = 'a5dc883f0e8c'
down_revision = ('modify_desc_text', '211f3c5aa125', 'add_database_connections')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
