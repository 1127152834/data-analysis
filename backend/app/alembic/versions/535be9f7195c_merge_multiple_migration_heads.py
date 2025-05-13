"""Merge multiple migration heads

Revision ID: 535be9f7195c
Revises: a5dc883f0e8c, add_database_descriptions, chat_meta_table, modify_description_for_llm_to_text
Create Date: 2025-05-13 03:04:13.537989

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from tidb_vector.sqlalchemy import VectorType


# revision identifiers, used by Alembic.
revision = '535be9f7195c'
down_revision = ('a5dc883f0e8c', 'add_database_descriptions', 'chat_meta_table', 'modify_description_for_llm_to_text')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
