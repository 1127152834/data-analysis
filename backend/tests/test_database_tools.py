import pytest
from unittest.mock import MagicMock, patch
import sqlalchemy

from app.models.database_connection import DatabaseConnection, DatabaseType
from app.rag.tools.database_tools import (
    create_llama_sql_database_from_connection,
    create_database_function_tool,
    check_database_connection,
    create_database_connection_tools
)


def create_test_db_connection(db_type=DatabaseType.SQLITE, include_descriptions=True):
    """创建测试用的数据库连接对象"""
    db_conn = MagicMock(spec=DatabaseConnection)
    db_conn.id = 1
    db_conn.name = "测试数据库"
    db_conn.database_type = db_type
    
    # 根据数据库类型设置不同的配置
    if db_type == DatabaseType.SQLITE:
        db_conn.config = {"file_path": ":memory:"}
    elif db_type == DatabaseType.MYSQL:
        db_conn.config = {
            "user": "test_user",
            "password": "test_password",
            "host": "localhost",
            "port": 3306,
            "database": "test_db"
        }
    elif db_type == DatabaseType.POSTGRESQL:
        db_conn.config = {
            "user": "test_user",
            "password": "test_password",
            "host": "localhost",
            "port": 5432,
            "database": "test_db"
        }
    
    # 设置表和列描述
    if include_descriptions:
        db_conn.table_descriptions = {
            "users": "用户表",
            "orders": "订单表"
        }
        db_conn.column_descriptions = {
            "users": {
                "id": "用户ID",
                "name": "用户名",
                "email": "电子邮件"
            },
            "orders": {
                "id": "订单ID",
                "user_id": "用户ID",
                "price": "价格"
            }
        }
        db_conn.description_for_llm = "这是一个用于测试的数据库"
    else:
        db_conn.table_descriptions = {}
        db_conn.column_descriptions = {}
        db_conn.description_for_llm = None
    
    return db_conn


class TestDatabaseTools:
    """数据库工具测试类"""
    
    @patch("app.rag.tools.database_tools.create_engine")
    def test_create_llama_sql_database_sqlite(self, mock_create_engine):
        """测试使用SQLite创建SQLDatabase"""
        # 设置模拟对象
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        
        # 创建测试数据库连接
        db_conn = create_test_db_connection(db_type=DatabaseType.SQLITE)
        
        # 调用被测试的函数
        with patch("app.rag.tools.database_tools.SQLDatabase") as mock_sql_database:
            create_llama_sql_database_from_connection(db_conn)
            
            # 验证调用
            mock_create_engine.assert_called_once_with("sqlite:///:memory:")
            mock_sql_database.assert_called_once_with(
                mock_engine, 
                include_tables=["users", "orders"]
            )
    
    @patch("app.rag.tools.database_tools.create_engine")
    def test_create_llama_sql_database_mysql(self, mock_create_engine):
        """测试使用MySQL创建SQLDatabase"""
        # 设置模拟对象
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        
        # 创建测试数据库连接
        db_conn = create_test_db_connection(db_type=DatabaseType.MYSQL)
        
        # 调用被测试的函数
        with patch("app.rag.tools.database_tools.SQLDatabase") as mock_sql_database:
            create_llama_sql_database_from_connection(db_conn)
            
            # 验证调用
            mock_create_engine.assert_called_once_with(
                "mysql+mysqlconnector://test_user:test_password@localhost:3306/test_db"
            )
            mock_sql_database.assert_called_once_with(
                mock_engine, 
                include_tables=["users", "orders"]
            )
    
    @patch("app.rag.tools.database_tools.create_engine")
    def test_create_llama_sql_database_postgresql(self, mock_create_engine):
        """测试使用PostgreSQL创建SQLDatabase"""
        # 设置模拟对象
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        
        # 创建测试数据库连接
        db_conn = create_test_db_connection(db_type=DatabaseType.POSTGRESQL)
        
        # 调用被测试的函数
        with patch("app.rag.tools.database_tools.SQLDatabase") as mock_sql_database:
            create_llama_sql_database_from_connection(db_conn)
            
            # 验证调用
            mock_create_engine.assert_called_once_with(
                "postgresql://test_user:test_password@localhost:5432/test_db"
            )
            mock_sql_database.assert_called_once_with(
                mock_engine, 
                include_tables=["users", "orders"]
            )
    
    def test_create_llama_sql_database_unsupported(self):
        """测试不支持的数据库类型"""
        # 创建测试数据库连接
        db_conn = create_test_db_connection()
        db_conn.database_type = "unsupported_type"
        
        # 验证异常
        with pytest.raises(NotImplementedError):
            create_llama_sql_database_from_connection(db_conn)
    
    @patch("app.rag.tools.database_tools.create_query_engine_for_database")
    def test_create_database_function_tool(self, mock_create_query_engine):
        """测试创建数据库函数工具"""
        # 设置模拟对象
        mock_query_engine = MagicMock()
        mock_create_query_engine.return_value = mock_query_engine
        
        # 创建测试数据库连接和LLM
        db_conn = create_test_db_connection()
        mock_llm = MagicMock()
        
        # 调用被测试的函数
        tool = create_database_function_tool(db_conn, mock_llm)
        
        # 验证结果
        assert tool.metadata.name == "query_测试数据库_1"
        assert "查询'测试数据库'数据库(sqlite)" in tool.metadata.description
        assert "用于查询：这是一个用于测试的数据库" in tool.metadata.description
        assert "表'users'：用户表" in tool.metadata.description
        assert "表'orders'：订单表" in tool.metadata.description
        
        # 验证函数被正确创建
        assert callable(tool.fn)
    
    @patch("app.rag.tools.database_tools.create_llama_sql_database_from_connection")
    def test_check_database_connection_success(self, mock_create_db):
        """测试数据库连接测试成功的情况"""
        # 设置模拟对象
        mock_sql_db = MagicMock()
        mock_create_db.return_value = mock_sql_db
        
        # 模拟连接
        mock_conn = MagicMock()
        mock_sql_db.engine.connect.return_value.__enter__.return_value = mock_conn
        
        # 创建测试数据库连接
        db_conn = create_test_db_connection()
        
        # 调用被测试的函数
        result = check_database_connection(db_conn)
        
        # 验证结果
        assert result is True
        mock_conn.execute.assert_called_once_with("SELECT 1")
    
    @patch("app.rag.tools.database_tools.create_llama_sql_database_from_connection")
    def test_check_database_connection_failure(self, mock_create_db):
        """测试数据库连接测试失败的情况"""
        # 设置模拟对象
        mock_create_db.side_effect = Exception("Connection failed")
        
        # 创建测试数据库连接
        db_conn = create_test_db_connection()
        
        # 调用被测试的函数
        result = check_database_connection(db_conn)
        
        # 验证结果
        assert result is False
    
    @patch("app.rag.tools.database_tools.check_database_connection")
    @patch("app.rag.tools.database_tools.create_database_function_tool")
    def test_create_database_connection_tools(self, mock_create_tool, mock_check_conn):
        """测试为多个数据库连接创建工具"""
        # 设置模拟对象
        mock_check_conn.side_effect = [True, False, True]  # 第一个和第三个连接成功，第二个失败
        
        mock_tool1 = MagicMock()
        mock_tool2 = MagicMock()
        mock_create_tool.side_effect = [mock_tool1, mock_tool2]
        
        # 创建测试数据库连接
        db_conn1 = create_test_db_connection()
        db_conn1.id = 1
        db_conn1.name = "DB1"
        
        db_conn2 = create_test_db_connection()
        db_conn2.id = 2
        db_conn2.name = "DB2"
        
        db_conn3 = create_test_db_connection()
        db_conn3.id = 3
        db_conn3.name = "DB3"
        
        db_connections = [db_conn1, db_conn2, db_conn3]
        mock_llm = MagicMock()
        
        # 调用被测试的函数
        tools = create_database_connection_tools(db_connections, mock_llm)
        
        # 验证结果
        assert len(tools) == 2
        assert tools[0] == mock_tool1
        assert tools[1] == mock_tool2
        
        # 验证调用
        assert mock_check_conn.call_count == 3
        mock_create_tool.assert_any_call(db_conn1, mock_llm)
        mock_create_tool.assert_any_call(db_conn3, mock_llm)
        assert mock_create_tool.call_count == 2 