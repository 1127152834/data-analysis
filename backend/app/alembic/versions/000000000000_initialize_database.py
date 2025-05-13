"""initialize_database

Revision ID: 000000000000
Revises: 
Create Date: 2025-05-13 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from tidb_vector.sqlalchemy import VectorType

# revision identifiers, used by Alembic.
revision = '000000000000'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """
    这个脚本作为初始化脚本，创建数据库中所有表的创建语句。
    根据test_struct.sql文件中的表结构生成。
    """
    # 在这里添加检查，如果表已存在，则跳过创建
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    
    # 以下是所有表的创建语句
    
    # 用户表
    if 'users' not in tables:
        op.create_table(
            'users',
            sa.Column('id', sqlmodel.sql.sqltypes.GUID(), nullable=False),
            sa.Column('email', sa.String(length=255), nullable=False),
            sa.Column('hashed_password', sa.String(length=255), nullable=False),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
            sa.Column('is_superuser', sa.Boolean(), nullable=False, server_default=sa.text('0')),
            sa.Column('is_verified', sa.Boolean(), nullable=False, server_default=sa.text('0')),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_users_email', 'users', ['email'], unique=True)
        op.create_index('ix_users_id', 'users', ['id'], unique=False)
    
    # API密钥表
    if 'api_keys' not in tables:
        op.create_table(
            'api_keys',
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('description', sa.String(length=100), nullable=False),
            sa.Column('hashed_secret', sa.String(length=255), nullable=False),
            sa.Column('api_key_display', sa.String(length=100), nullable=False),
            sa.Column('is_active', sa.Boolean(), nullable=False),
            sa.Column('user_id', sqlmodel.sql.sqltypes.GUID(), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_1'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('hashed_secret', 'api_keys', ['hashed_secret'], unique=True)
    
    # 聊天引擎表
    if 'llms' not in tables:
        op.create_table(
            'llms',
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('name', sa.String(length=64), nullable=False),
            sa.Column('provider', sa.String(length=32), nullable=False),
            sa.Column('model', sa.String(length=256), nullable=False),
            sa.Column('config', sa.JSON(), nullable=True),
            sa.Column('credentials', sa.BLOB(), nullable=True),
            sa.Column('is_default', sa.Boolean(), nullable=False),
            sa.PrimaryKeyConstraint('id')
        )
    
    if 'reranker_models' not in tables:
        op.create_table(
            'reranker_models',
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
            sa.Column('name', sa.String(length=64), nullable=False),
            sa.Column('provider', sa.String(length=32), nullable=False),
            sa.Column('model', sa.String(length=256), nullable=False),
            sa.Column('top_n', sa.Integer(), nullable=False),
            sa.Column('config', sa.JSON(), nullable=True),
            sa.Column('is_default', sa.Boolean(), nullable=False),
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('credentials', sa.BLOB(), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        
    if 'chat_engines' not in tables:
        op.create_table(
            'chat_engines',
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('name', sa.String(length=256), nullable=False),
            sa.Column('engine_options', sa.JSON(), nullable=True),
            sa.Column('is_default', sa.Boolean(), nullable=False),
            sa.Column('deleted_at', sa.DateTime(), nullable=True),
            sa.Column('llm_id', sa.Integer(), nullable=True),
            sa.Column('fast_llm_id', sa.Integer(), nullable=True),
            sa.Column('reranker_id', sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(['fast_llm_id'], ['llms.id'], name='fk_1'),
            sa.ForeignKeyConstraint(['llm_id'], ['llms.id'], name='fk_2'),
            sa.ForeignKeyConstraint(['reranker_id'], ['reranker_models.id'], name='fk_3'),
            sa.PrimaryKeyConstraint('id')
        )
    
    # 聊天表
    if 'chats' not in tables:
        op.create_table(
            'chats',
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
            sa.Column('id', sqlmodel.sql.sqltypes.GUID(), nullable=False),
            sa.Column('title', sa.String(length=256), nullable=False),
            sa.Column('engine_id', sa.Integer(), nullable=True),
            sa.Column('engine_options', sa.JSON(), nullable=True),
            sa.Column('deleted_at', sa.DateTime(), nullable=True),
            sa.Column('user_id', sqlmodel.sql.sqltypes.GUID(), nullable=True),
            sa.Column('browser_id', sa.String(length=50), nullable=True),
            sa.Column('origin', sa.String(length=256), nullable=True),
            sa.Column('visibility', sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(['engine_id'], ['chat_engines.id'], name='fk_1'),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_2'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_chats_id', 'chats', ['id'], unique=False)
    
    # 聊天消息表
    if 'chat_messages' not in tables:
        op.create_table(
            'chat_messages',
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('ordinal', sa.Integer(), nullable=False),
            sa.Column('role', sa.String(length=64), nullable=False),
            sa.Column('content', sa.Text(), nullable=True),
            sa.Column('error', sa.Text(), nullable=True),
            sa.Column('sources', sa.JSON(), nullable=True),
            sa.Column('trace_url', sa.String(length=512), nullable=True),
            sa.Column('finished_at', sa.DateTime(), nullable=True),
            sa.Column('chat_id', sqlmodel.sql.sqltypes.GUID(), nullable=False),
            sa.Column('user_id', sqlmodel.sql.sqltypes.GUID(), nullable=True),
            sa.Column('graph_data', sa.JSON(), nullable=True),
            sa.Column('post_verification_result_url', sa.String(length=512), nullable=True),
            sa.Column('meta', sa.JSON(), nullable=True),
            sa.Column('is_best_answer', sa.Boolean(), nullable=False, server_default=sa.text('0')),
            sa.ForeignKeyConstraint(['chat_id'], ['chats.id'], name='fk_1'),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_2'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_chat_message_is_best_answer', 'chat_messages', ['is_best_answer'], unique=False)
    
    # 聊天元数据表
    if 'chat_meta' not in tables:
        op.create_table(
            'chat_meta',
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('chat_id', sqlmodel.sql.sqltypes.GUID(), nullable=False),
            sa.Column('key', sa.String(length=256), nullable=False),
            sa.Column('value', sa.Text(), nullable=True),
            sa.Column('expires_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['chat_id'], ['chats.id'], name='fk_1'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_chat_meta_chat_id', 'chat_meta', ['chat_id'], unique=False)
        op.create_index('ix_chat_meta_chat_id_key', 'chat_meta', ['chat_id', 'key'], unique=True)
        op.create_index('ix_chat_meta_key', 'chat_meta', ['key'], unique=False)
    
    # 推荐问题表
    if 'recommend_questions' not in tables:
        op.create_table(
            'recommend_questions',
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('questions', sa.JSON(), nullable=True),
            sa.Column('chat_message_id', sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(['chat_message_id'], ['chat_messages.id'], name='fk_1'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_recommend_questions_chat_message_id', 'recommend_questions', ['chat_message_id'], unique=False)
    
    # 反馈表
    if 'feedbacks' not in tables:
        op.create_table(
            'feedbacks',
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
            sa.Column('feedback_type', sa.Enum('LIKE', 'DISLIKE', native_enum=False), nullable=False),
            sa.Column('comment', sa.String(length=500), nullable=False),
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('chat_id', sqlmodel.sql.sqltypes.GUID(), nullable=False),
            sa.Column('chat_message_id', sa.Integer(), nullable=False),
            sa.Column('user_id', sqlmodel.sql.sqltypes.GUID(), nullable=True),
            sa.Column('origin', sa.String(length=256), nullable=True),
            sa.ForeignKeyConstraint(['chat_id'], ['chats.id'], name='fk_1'),
            sa.ForeignKeyConstraint(['chat_message_id'], ['chat_messages.id'], name='fk_2'),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_3'),
            sa.PrimaryKeyConstraint('id')
        )
    
    # 数据库连接表
    if 'database_connections' not in tables:
        op.create_table(
            'database_connections',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('name', sa.String(length=256), nullable=False),
            sa.Column('description', sa.String(length=512), nullable=False),
            sa.Column('description_for_llm', sa.Text(), nullable=True),
            sa.Column('table_descriptions', sa.JSON(), nullable=True, comment='表描述信息，格式: {table_name: description}'),
            sa.Column('column_descriptions', sa.JSON(), nullable=True, comment='列描述信息，格式: {table_name: {column_name: description}}'),
            sa.Column('accessible_roles', sa.JSON(), nullable=True),
            sa.Column('database_type', sa.String(length=32), nullable=False),
            sa.Column('config', sa.JSON(), nullable=True),
            sa.Column('user_id', sqlmodel.sql.sqltypes.GUID(), nullable=True),
            sa.Column('read_only', sa.Boolean(), nullable=False, server_default=sa.text('1')),
            sa.Column('connection_status', sa.String(length=32), nullable=False, server_default=sa.text('disconnected')),
            sa.Column('last_connected_at', sa.DateTime(), nullable=True),
            sa.Column('metadata_cache', sa.JSON(), nullable=True),
            sa.Column('metadata_updated_at', sa.DateTime(), nullable=True),
            sa.Column('deleted_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_1'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_database_connections_id', 'database_connections', ['id'], unique=False)
    
    # 数据库查询历史表
    if 'database_query_history' not in tables:
        op.create_table(
            'database_query_history',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('chat_id', sqlmodel.sql.sqltypes.GUID(), nullable=False),
            sa.Column('chat_message_id', sa.Integer(), nullable=True),
            sa.Column('user_id', sqlmodel.sql.sqltypes.GUID(), nullable=True),
            sa.Column('connection_id', sa.Integer(), nullable=False),
            sa.Column('connection_name', sa.String(length=256), nullable=False),
            sa.Column('database_type', sa.String(length=32), nullable=False),
            sa.Column('question', sa.Text(), nullable=False),
            sa.Column('query', sa.Text(), nullable=False),
            sa.Column('is_successful', sa.Boolean(), nullable=False, server_default=sa.text('1')),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('result_summary', sa.JSON(), nullable=True),
            sa.Column('result_sample', sa.JSON(), nullable=True),
            sa.Column('execution_time_ms', sa.Integer(), nullable=False, server_default=sa.text('0')),
            sa.Column('rows_returned', sa.Integer(), nullable=False, server_default=sa.text('0')),
            sa.Column('routing_score', sa.Float(), nullable=True),
            sa.Column('routing_context', sa.JSON(), nullable=True),
            sa.Column('user_feedback', sa.Integer(), nullable=True),
            sa.Column('user_feedback_comments', sa.Text(), nullable=True),
            sa.Column('meta', sa.JSON(), nullable=True),
            sa.Column('executed_at', sa.DateTime(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.ForeignKeyConstraint(['chat_id'], ['chats.id'], name='fk_1'),
            sa.ForeignKeyConstraint(['chat_message_id'], ['chat_messages.id'], name='fk_2'),
            sa.ForeignKeyConstraint(['connection_id'], ['database_connections.id'], name='fk_3'),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_4'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_database_query_history_chat_id', 'database_query_history', ['chat_id'], unique=False)
        op.create_index('ix_database_query_history_chat_message_id', 'database_query_history', ['chat_message_id'], unique=False)
        op.create_index('ix_database_query_history_connection_id', 'database_query_history', ['connection_id'], unique=False)
        op.create_index('ix_database_query_history_user_id', 'database_query_history', ['user_id'], unique=False)
        op.create_index('ix_database_query_history_executed_at', 'database_query_history', ['executed_at'], unique=False)
        op.create_index('ix_db_query_history_chat_id_executed_at', 'database_query_history', ['chat_id', 'executed_at'], unique=False)
        op.create_index('ix_db_query_history_connection_id_executed_at', 'database_query_history', ['connection_id', 'executed_at'], unique=False)
    
    # 嵌入模型表
    if 'embedding_models' not in tables:
        op.create_table(
            'embedding_models',
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('name', sa.String(length=64), nullable=False),
            sa.Column('provider', sa.String(length=32), nullable=False),
            sa.Column('model', sa.String(length=256), nullable=False),
            sa.Column('config', sa.JSON(), nullable=True),
            sa.Column('credentials', sa.BLOB(), nullable=True),
            sa.Column('is_default', sa.Boolean(), nullable=False),
            sa.Column('vector_dimension', sa.Integer(), nullable=False),
            sa.PrimaryKeyConstraint('id')
        )
    
    # 知识库表
    if 'knowledge_bases' not in tables:
        op.create_table(
            'knowledge_bases',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('name', sa.String(length=255), nullable=False),
            sa.Column('description', sa.Text(length=16777215), nullable=True),
            sa.Column('index_methods', sa.JSON(), nullable=True),
            sa.Column('llm_id', sa.Integer(), nullable=True),
            sa.Column('embedding_model_id', sa.Integer(), nullable=True),
            sa.Column('documents_total', sa.Integer(), nullable=False),
            sa.Column('data_sources_total', sa.Integer(), nullable=False),
            sa.Column('created_by', sqlmodel.sql.sqltypes.GUID(), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
            sa.Column('updated_by', sqlmodel.sql.sqltypes.GUID(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
            sa.Column('deleted_by', sqlmodel.sql.sqltypes.GUID(), nullable=True),
            sa.Column('deleted_at', sa.DateTime(), nullable=True),
            sa.Column('chunking_config', sa.JSON(), nullable=True),
            sa.ForeignKeyConstraint(['created_by'], ['users.id'], name='fk_1'),
            sa.ForeignKeyConstraint(['deleted_by'], ['users.id'], name='fk_2'),
            sa.ForeignKeyConstraint(['embedding_model_id'], ['embedding_models.id'], name='fk_3'),
            sa.ForeignKeyConstraint(['llm_id'], ['llms.id'], name='fk_4'),
            sa.ForeignKeyConstraint(['updated_by'], ['users.id'], name='fk_5'),
            sa.PrimaryKeyConstraint('id')
        )
    
    # 数据源表
    if 'data_sources' not in tables:
        op.create_table(
            'data_sources',
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('name', sa.String(length=256), nullable=False),
            sa.Column('description', sa.String(length=512), nullable=False),
            sa.Column('data_source_type', sa.String(length=256), nullable=False),
            sa.Column('config', sa.JSON(), nullable=True),
            sa.Column('build_kg_index', sa.Boolean(), nullable=False),
            sa.Column('user_id', sqlmodel.sql.sqltypes.GUID(), nullable=True),
            sa.Column('llm_id', sa.Integer(), nullable=True),
            sa.Column('deleted_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['llm_id'], ['llms.id'], name='fk_2'),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_1'),
            sa.PrimaryKeyConstraint('id')
        )
    
    # 知识库数据源关联表
    if 'knowledge_base_datasources' not in tables:
        op.create_table(
            'knowledge_base_datasources',
            sa.Column('knowledge_base_id', sa.Integer(), nullable=False),
            sa.Column('data_source_id', sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(['data_source_id'], ['data_sources.id'], name='fk_1'),
            sa.ForeignKeyConstraint(['knowledge_base_id'], ['knowledge_bases.id'], name='fk_2'),
            sa.PrimaryKeyConstraint('knowledge_base_id', 'data_source_id')
        )
    
    # 文档表
    if 'documents' not in tables:
        op.create_table(
            'documents',
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('hash', sa.String(length=32), nullable=False),
            sa.Column('name', sa.String(length=256), nullable=False),
            sa.Column('content', sa.Text(length=16777215), nullable=True),
            sa.Column('mime_type', sa.String(length=128), nullable=False),
            sa.Column('source_uri', sa.String(length=512), nullable=False),
            sa.Column('meta', sa.JSON(), nullable=True),
            sa.Column('last_modified_at', sa.DateTime(), nullable=True),
            sa.Column('index_status', sa.Enum('NOT_STARTED', 'PENDING', 'RUNNING', 'COMPLETED', 'FAILED', native_enum=False), nullable=False),
            sa.Column('index_result', sa.Text(), nullable=True),
            sa.Column('data_source_id', sa.Integer(), nullable=True),
            sa.Column('knowledge_base_id', sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(['data_source_id'], ['data_sources.id'], name='fk_d_on_data_source_id'),
            sa.ForeignKeyConstraint(['knowledge_base_id'], ['knowledge_bases.id'], name='fk_d_on_knowledge_base_id'),
            sa.PrimaryKeyConstraint('id')
        )
    
    # 语义缓存表
    if 'semantic_cache' not in tables:
        op.create_table(
            'semantic_cache',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('query', sa.Text(), nullable=True),
            sa.Column('query_vec', VectorType(1536), nullable=True, comment='hnsw(distance=cosine)'),
            sa.Column('value', sa.Text(), nullable=True),
            sa.Column('value_vec', VectorType(1536), nullable=True, comment='hnsw(distance=cosine)'),
            sa.Column('meta', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
    
    # 站点设置表
    if 'site_settings' not in tables:
        op.create_table(
            'site_settings',
            sa.Column('created_at', sa.DateTime(precision=6), server_default=sa.text('CURRENT_TIMESTAMP(6)'), nullable=True),
            sa.Column('updated_at', sa.DateTime(precision=6), server_default=sa.text("CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6)"), nullable=True),
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('name', sa.String(length=256), nullable=False),
            sa.Column('data_type', sa.String(length=256), nullable=False),
            sa.Column('value', sa.JSON(), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('name', 'site_settings', ['name'], unique=True)
    
    # 管理员操作日志表
    if 'staff_action_logs' not in tables:
        op.create_table(
            'staff_action_logs',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('action', sa.String(length=255), nullable=False),
            sa.Column('action_time', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
            sa.Column('target_type', sa.String(length=255), nullable=False),
            sa.Column('target_id', sa.Integer(), nullable=False),
            sa.Column('before', sa.JSON(), nullable=True),
            sa.Column('after', sa.JSON(), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
    
    # 上传文件表
    if 'uploads' not in tables:
        op.create_table(
            'uploads',
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('name', sa.String(length=255), nullable=False),
            sa.Column('size', sa.Integer(), nullable=False),
            sa.Column('path', sa.String(length=255), nullable=False),
            sa.Column('mime_type', sa.String(length=128), nullable=False),
            sa.Column('user_id', sqlmodel.sql.sqltypes.GUID(), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_1'),
            sa.PrimaryKeyConstraint('id')
        )
    
    # 用户会话表
    if 'user_sessions' not in tables:
        op.create_table(
            'user_sessions',
            sa.Column('token', sa.String(length=43), nullable=False),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
            sa.Column('user_id', sqlmodel.sql.sqltypes.GUID(), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_1'),
            sa.PrimaryKeyConstraint('token')
        )
    
    # 评估数据集表
    if 'evaluation_datasets' not in tables:
        op.create_table(
            'evaluation_datasets',
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('name', sa.String(length=255), nullable=False),
            sa.Column('user_id', sqlmodel.sql.sqltypes.GUID(), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_1'),
            sa.PrimaryKeyConstraint('id')
        )
    
    # 评估数据集项目表
    if 'evaluation_dataset_items' not in tables:
        op.create_table(
            'evaluation_dataset_items',
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('query', sa.Text(), nullable=True),
            sa.Column('reference', sa.Text(), nullable=True),
            sa.Column('retrieved_contexts', sa.JSON(), nullable=True),
            sa.Column('extra', sa.JSON(), nullable=True),
            sa.Column('evaluation_dataset_id', sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(['evaluation_dataset_id'], ['evaluation_datasets.id'], name='fk_1'),
            sa.PrimaryKeyConstraint('id')
        )
    
    # 评估任务表
    if 'evaluation_tasks' not in tables:
        op.create_table(
            'evaluation_tasks',
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('name', sa.String(length=255), nullable=False),
            sa.Column('user_id', sqlmodel.sql.sqltypes.GUID(), nullable=True),
            sa.Column('dataset_id', sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_1'),
            sa.PrimaryKeyConstraint('id')
        )
    
    # 评估任务项目表
    if 'evaluation_task_items' not in tables:
        op.create_table(
            'evaluation_task_items',
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('chat_engine', sa.String(length=255), nullable=False),
            sa.Column('status', sa.String(length=32), nullable=False),
            sa.Column('query', sa.Text(), nullable=True),
            sa.Column('reference', sa.Text(), nullable=True),
            sa.Column('response', sa.Text(), nullable=True),
            sa.Column('retrieved_contexts', sa.JSON(), nullable=True),
            sa.Column('extra', sa.JSON(), nullable=True),
            sa.Column('error_msg', sa.Text(), nullable=True),
            sa.Column('factual_correctness', sa.Float(), nullable=True),
            sa.Column('semantic_similarity', sa.Float(), nullable=True),
            sa.Column('evaluation_task_id', sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(['evaluation_task_id'], ['evaluation_tasks.id'], name='fk_1'),
            sa.PrimaryKeyConstraint('id')
        )
    
    # 注意：以下三个表使用了向量类型，可能需要在实际环境中根据具体的向量数据库实现进行调整
    # 对于entities_60001, chunks_60001, relationships_60001这种特殊表，它们依赖于知识库ID
    # 实际中应该通过代码动态创建而不是在迁移脚本中创建
    
    # 到此为止，我们已经创建了所有的常规表


def downgrade():
    """
    这个降级函数不会实际删除表，因为这可能导致数据丢失。
    如果需要删除表结构，请使用单独的迁移脚本。
    """
    pass 