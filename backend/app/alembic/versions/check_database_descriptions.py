"""check_database_descriptions

Revision ID: check_database_descriptions
Revises: add_accessible_roles
Create Date: 2024-05-13 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import json
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

# revision identifiers, used by Alembic.
revision = 'check_database_descriptions'
down_revision = 'add_accessible_roles'
branch_labels = None
depends_on = None


class DatabaseConnection(Base):
    __tablename__ = 'database_connections'
    
    id = sa.Column(sa.Integer, primary_key=True)
    table_descriptions = sa.Column(sa.JSON)
    column_descriptions = sa.Column(sa.JSON)


def upgrade():
    connection = op.get_bind()
    Session = sessionmaker(bind=connection)
    session = Session()
    
    # 获取所有数据库连接
    connections = session.query(DatabaseConnection).all()
    
    for conn in connections:
        # 初始化表描述和列描述（如果为None）
        if conn.table_descriptions is None:
            conn.table_descriptions = {}
        
        if conn.column_descriptions is None:
            conn.column_descriptions = {}
    
    # 提交更改
    session.commit()


def downgrade():
    # 无需降级操作
    pass 