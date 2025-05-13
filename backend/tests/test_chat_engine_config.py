import pytest
from unittest.mock import MagicMock, patch
from sqlmodel import Session

from app.rag.chat.config import ChatEngineConfig
from app.models.database_connection import DatabaseConnection, DatabaseType
from app.models.chat_engine import ChatEngine


def create_mock_db_connection(id=1, name="Test DB", deleted_at=None):
    """创建模拟的数据库连接对象"""
    db_conn = MagicMock(spec=DatabaseConnection)
    db_conn.id = id
    db_conn.name = name
    db_conn.database_type = DatabaseType.SQLITE
    db_conn.deleted_at = deleted_at
    db_conn.config = {"file_path": ":memory:"}
    db_conn.table_descriptions = {"users": "用户表"}
    db_conn.column_descriptions = {"users": {"id": "用户ID", "name": "用户名"}}
    return db_conn


def create_mock_chat_engine(engine_options=None):
    """创建模拟的聊天引擎对象"""
    chat_engine = MagicMock(spec=ChatEngine)
    chat_engine.name = "test_engine"
    chat_engine.engine_options = engine_options or {}
    return chat_engine


class TestChatEngineConfig:
    """测试ChatEngineConfig类"""

    @patch("app.repositories.chat_engine_repo.get_engine_by_name")
    @patch("app.repositories.database_connection_repo.get")
    def test_load_from_db_with_database_connections(self, mock_db_conn_get, mock_get_engine_by_name):
        """测试从数据库加载ChatEngineConfig并关联数据库连接"""
        # 设置模拟聊天引擎
        engine_options = {
            "database_connection_ids": [1, 2, 3]  # 测试三个ID
        }
        mock_chat_engine = create_mock_chat_engine(engine_options)
        mock_get_engine_by_name.return_value = mock_chat_engine

        # 设置模拟数据库连接
        # 第一个连接正常
        db_conn1 = create_mock_db_connection(id=1, name="DB 1")
        # 第二个连接已删除，应该被过滤
        db_conn2 = create_mock_db_connection(id=2, name="DB 2", deleted_at="2023-01-01")
        # 第三个连接正常
        db_conn3 = create_mock_db_connection(id=3, name="DB 3")

        # 配置mock_db_conn_get返回不同的数据库连接
        def get_side_effect(session, conn_id):
            if conn_id == 1:
                return db_conn1
            elif conn_id == 2:
                return db_conn2
            elif conn_id == 3:
                return db_conn3
            return None

        mock_db_conn_get.side_effect = get_side_effect

        # 创建模拟会话
        mock_session = MagicMock(spec=Session)

        # 调用load_from_db方法
        config = ChatEngineConfig.load_from_db(mock_session, "test_engine")

        # 验证结果
        assert len(config.active_database_connections) == 2  # 应该只有2个活跃的连接
        assert config.active_database_connections[0].id == 1
        assert config.active_database_connections[1].id == 3
        # DB 2不应该在列表中，因为它已被删除

        # 验证调用
        mock_get_engine_by_name.assert_called_once_with(mock_session, "test_engine")
        assert mock_db_conn_get.call_count == 3  # 应该调用3次get方法

    @patch("app.repositories.chat_engine_repo.get_engine_by_name")
    def test_load_from_db_without_database_connections(self, mock_get_engine_by_name):
        """测试从数据库加载ChatEngineConfig但没有数据库连接ID"""
        # 设置模拟聊天引擎
        engine_options = {}  # 空选项，没有数据库连接ID
        mock_chat_engine = create_mock_chat_engine(engine_options)
        mock_get_engine_by_name.return_value = mock_chat_engine

        # 创建模拟会话
        mock_session = MagicMock(spec=Session)

        # 调用load_from_db方法
        config = ChatEngineConfig.load_from_db(mock_session, "test_engine")

        # 验证结果
        assert len(config.active_database_connections) == 0  # 应该没有活跃的连接

        # 验证调用
        mock_get_engine_by_name.assert_called_once_with(mock_session, "test_engine") 