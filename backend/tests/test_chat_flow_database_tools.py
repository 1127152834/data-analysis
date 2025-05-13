import pytest
from unittest.mock import MagicMock, patch
import asyncio

from app.rag.chat.chat_flow import ChatFlow
from app.rag.types import ChatEventType, ChatMessageSate
from app.models.database_connection import DatabaseConnection, DatabaseType
from llama_index.core.base.llms.types import ChatMessage, MessageRole


def create_test_user():
    """创建测试用户"""
    user = MagicMock()
    user.id = 1
    user.email = "test@example.com"
    return user


def create_test_db_session():
    """创建测试数据库会话"""
    db_session = MagicMock()
    return db_session


def create_test_chat_message():
    """创建测试聊天消息"""
    return ChatMessage(role=MessageRole.USER, content="测试查询用户表中的所有用户")


def create_test_database_connection():
    """创建测试数据库连接对象"""
    db_conn = MagicMock(spec=DatabaseConnection)
    db_conn.id = 1
    db_conn.name = "测试数据库"
    db_conn.database_type = DatabaseType.SQLITE
    db_conn.config = {"file_path": ":memory:"}
    db_conn.description_for_llm = "测试用SQLite数据库"
    db_conn.table_descriptions = {
        "users": "用户表，存储系统用户信息",
        "orders": "订单表，存储用户订单信息"
    }
    db_conn.column_descriptions = {
        "users": {
            "id": "用户ID，主键",
            "name": "用户名",
            "email": "电子邮件",
            "created_at": "创建时间"
        },
        "orders": {
            "id": "订单ID，主键",
            "user_id": "用户ID，外键关联users表",
            "amount": "订单金额",
            "created_at": "创建时间"
        }
    }
    return db_conn


def create_test_llm():
    """创建测试LLM对象"""
    llm = MagicMock()
    llm.class_name.return_value = "openai_llm"
    llm.model = "gpt-3.5-turbo"
    llm.max_tokens = 2048
    llm.api_key = "test_api_key"
    llm.api_base = "https://api.openai.com/v1"
    return llm


@pytest.fixture
def patch_dspy_lm():
    """修补DSPy LM创建"""
    with patch("app.rag.llms.dspy.dspy.LM") as mock_dspy_lm:
        mock_dspy_instance = MagicMock()
        mock_dspy_lm.return_value = mock_dspy_instance
        yield mock_dspy_instance


class TestChatFlowDatabaseTools:
    """测试ChatFlow中的数据库工具集成"""
    
    @patch("app.rag.chat.config.ChatEngineConfig.load_from_db")
    @patch("app.repositories.chat_repo.create")
    @patch("app.rag.chat.chat_flow.create_database_connection_tools")
    def test_chat_flow_init_with_database_tools(
        self, 
        mock_create_tools,
        mock_create_chat,
        mock_load_config,
        patch_dspy_lm
    ):
        """测试ChatFlow初始化时创建数据库工具"""
        # 设置模拟对象
        db_session = create_test_db_session()
        user = create_test_user()
        
        # 模拟LLM
        mock_llm = create_test_llm()
        mock_fast_llm = create_test_llm()
        
        # 模拟配置和数据库连接
        mock_engine_config = MagicMock()
        mock_engine_config.is_external_engine = False
        mock_db_chat_engine = MagicMock()
        mock_engine_config.get_db_chat_engine.return_value = mock_db_chat_engine
        mock_engine_config.get_llama_llm.return_value = mock_llm
        mock_engine_config.get_fast_llama_llm.return_value = mock_fast_llm
        mock_engine_config.get_knowledge_bases.return_value = []
        
        # 模拟数据库连接
        test_db_conn = create_test_database_connection()
        mock_engine_config.active_database_connections = [test_db_conn]
        
        # 设置模拟返回值
        mock_load_config.return_value = mock_engine_config
        mock_chat_obj = MagicMock()
        mock_create_chat.return_value = mock_chat_obj
        
        # 模拟数据库工具
        mock_tool = MagicMock()
        mock_create_tools.return_value = [mock_tool]
        
        # 创建ChatFlow对象
        chat_flow = ChatFlow(
            db_session=db_session,
            user=user,
            browser_id="test_browser_id",
            origin="http://localhost",
            chat_messages=[create_test_chat_message()],
            engine_name="default"
        )
        
        # 验证数据库工具是否已创建
        assert chat_flow.db_tools == [mock_tool]
        assert chat_flow.agent is not None
        mock_create_tools.assert_called_once_with(
            mock_engine_config.active_database_connections,
            mock_llm
        )
    
    @patch("app.rag.chat.config.ChatEngineConfig.load_from_db")
    @patch("app.repositories.chat_repo.create")
    @patch("app.rag.chat.chat_flow.ReActAgent")
    def test_should_use_database_tools(
        self,
        mock_react_agent,
        mock_create_chat,
        mock_load_config,
        patch_dspy_lm
    ):
        """测试判断是否应该使用数据库工具的方法"""
        # 设置模拟对象
        db_session = create_test_db_session()
        user = create_test_user()
        
        # 模拟LLM
        mock_llm = create_test_llm()
        mock_fast_llm = create_test_llm()
        
        # 模拟配置
        mock_engine_config = MagicMock()
        mock_engine_config.is_external_engine = False
        mock_db_chat_engine = MagicMock()
        mock_engine_config.get_db_chat_engine.return_value = mock_db_chat_engine
        mock_engine_config.get_llama_llm.return_value = mock_llm
        mock_engine_config.get_fast_llama_llm.return_value = mock_fast_llm
        mock_engine_config.get_knowledge_bases.return_value = []
        
        # 设置模拟返回值
        mock_load_config.return_value = mock_engine_config
        mock_chat_obj = MagicMock()
        mock_create_chat.return_value = mock_chat_obj
        
        # 模拟代理
        mock_agent = MagicMock()
        mock_react_agent.from_tools.return_value = mock_agent
        
        # 创建ChatFlow对象
        chat_flow = ChatFlow(
            db_session=db_session,
            user=user,
            browser_id="test_browser_id",
            origin="http://localhost",
            chat_messages=[create_test_chat_message()],
            engine_name="default"
        )
        
        # 设置工具和代理
        chat_flow.db_tools = [MagicMock()]
        chat_flow.agent = mock_agent
        
        # 测试包含数据库关键词的问题
        relevant_chunks = [MagicMock()]
        relevant_chunks[0].score = 0.8
        
        # 测试各种关键词触发
        test_cases = [
            ("查询所有用户", True),
            ("统计销售额", True),
            ("计算平均值", True),
            ("表格中的数据", True),
            ("SQL语句", True),
            ("请问今天天气怎么样", False),
            ("如何使用这个软件", False),
        ]
        
        for question, expected in test_cases:
            result = chat_flow._should_use_database_tools(question, relevant_chunks)
            assert result == expected, f"问题 '{question}' 应该返回 {expected}"
            
        # 测试相关度低的情况
        low_score_chunks = [MagicMock()]
        low_score_chunks[0].score = 0.5
        assert chat_flow._should_use_database_tools("如何使用这个软件", low_score_chunks) == True
        
        # 测试没有相关文档的情况
        assert chat_flow._should_use_database_tools("如何使用这个软件", []) == True
        
    @patch("app.rag.chat.config.ChatEngineConfig.load_from_db")
    @patch("app.repositories.chat_repo.create")
    @patch("app.rag.chat.chat_flow.ReActAgent")
    def test_autonomous_tool_mode(
        self,
        mock_react_agent,
        mock_create_chat,
        mock_load_config,
        patch_dspy_lm
    ):
        """测试自主工具调用模式"""
        # 设置模拟对象
        db_session = create_test_db_session()
        user = create_test_user()
        
        # 模拟LLM和配置
        mock_llm = create_test_llm()
        mock_fast_llm = create_test_llm()
        
        # 模拟配置，配置autonomous模式
        mock_engine_config = MagicMock()
        mock_engine_config.is_external_engine = False
        mock_engine_config.get_db_chat_engine.return_value = MagicMock()
        mock_engine_config.get_llama_llm.return_value = mock_llm
        mock_engine_config.get_fast_llama_llm.return_value = mock_fast_llm
        mock_engine_config.get_knowledge_bases.return_value = []
        
        # 配置autonomous模式
        mock_database_config = MagicMock()
        mock_database_config.tool_mode = "autonomous"
        mock_engine_config.database = mock_database_config
        
        # 设置模拟返回值
        mock_load_config.return_value = mock_engine_config
        mock_create_chat.return_value = MagicMock()
        
        # 模拟代理
        mock_agent = MagicMock()
        mock_react_agent.from_tools.return_value = mock_agent
        
        # 创建ChatFlow对象
        chat_flow = ChatFlow(
            db_session=db_session,
            user=user,
            browser_id="test_browser_id",
            origin="http://localhost",
            chat_messages=[create_test_chat_message()],
            engine_name="default"
        )
        
        # 设置工具和代理
        chat_flow.db_tools = [MagicMock()]
        chat_flow.agent = mock_agent
        
        # 准备测试数据
        relevant_chunks = [MagicMock()]
        relevant_chunks[0].score = 0.9  # 高相关度
        
        # 测试不同类型的问题，在autonomous模式下都应该返回True
        test_questions = [
            "请问今天天气怎么样",  # 无关数据库的问题
            "如何使用这个软件",    # 一般知识问题
            "讲个笑话",           # 娱乐问题
            "Python怎么安装",     # 技术问题
        ]
        
        for question in test_questions:
            result = chat_flow._should_use_database_tools(question, relevant_chunks)
            assert result == True, f"autonomous模式下，问题 '{question}' 应该返回 True" 