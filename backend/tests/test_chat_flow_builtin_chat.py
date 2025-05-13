import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio

from app.rag.chat.chat_flow import ChatFlow
from app.rag.types import ChatEventType, ChatMessageSate
from app.models.database_connection import DatabaseConnection, DatabaseType
from llama_index.core.base.llms.types import ChatMessage, MessageRole
from llama_index.core.tools import ToolOutput


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


def create_test_chat_message(content="测试查询用户表中的所有用户"):
    """创建测试聊天消息"""
    return ChatMessage(role=MessageRole.USER, content=content)


def create_test_llm():
    """创建测试LLM对象"""
    llm = MagicMock()
    llm.class_name.return_value = "openai_llm"
    llm.model = "gpt-3.5-turbo"
    llm.max_tokens = 2048
    return llm


def create_mock_chat_event(event_type=None, payload=None):
    """创建模拟的ChatEvent对象"""
    mock_event = MagicMock()
    mock_event.event_type = event_type or MagicMock()
    mock_event.payload = payload or MagicMock()
    return mock_event


@pytest.fixture
def patch_dspy_lm():
    """修补DSPy LM创建"""
    with patch("app.rag.llms.dspy.dspy.LM") as mock_dspy_lm:
        mock_dspy_instance = MagicMock()
        mock_dspy_lm.return_value = mock_dspy_instance
        yield mock_dspy_instance


class MockAgentStep:
    """模拟代理步骤对象"""
    def __init__(self, step_type, **kwargs):
        self.step_type = step_type
        for key, value in kwargs.items():
            setattr(self, key, value)


class TestChatFlowBuiltinChat:
    """测试ChatFlow._builtin_chat方法"""
    
    # 定义一个辅助方法来创建模拟生成器
    def _create_mock_generator(self, result=None):
        def mock_generator():
            yield create_mock_chat_event()
            return result
        return mock_generator()
    
    @patch("app.rag.chat.config.ChatEngineConfig.load_from_db")
    @patch("app.repositories.chat_repo.create")
    @patch("app.rag.chat.chat_flow.ReActAgent")
    def test_builtin_chat_with_database_tools(
        self,
        mock_react_agent,
        mock_create_chat,
        mock_load_config,
        patch_dspy_lm
    ):
        """测试_builtin_chat调用数据库工具的情况"""
        # 设置模拟对象
        db_session = create_test_db_session()
        user = create_test_user()
        
        # 模拟LLM
        mock_llm = create_test_llm()
        mock_fast_llm = create_test_llm()
        
        # 模拟配置
        mock_engine_config = MagicMock()
        mock_engine_config.is_external_engine = False
        mock_engine_config.database = MagicMock()
        mock_engine_config.database.tool_mode = "autonomous"
        mock_engine_config.get_db_chat_engine.return_value = MagicMock()
        mock_engine_config.get_llama_llm.return_value = mock_llm
        mock_engine_config.get_fast_llama_llm.return_value = mock_fast_llm
        mock_engine_config.get_knowledge_bases.return_value = []
        mock_engine_config.clarify_question = False
        
        # 模拟数据库工具
        mock_db_tool = MagicMock()
        mock_db_tool.name = "query_testdb"
        
        # 设置模拟返回值
        mock_load_config.return_value = mock_engine_config
        mock_chat_obj = MagicMock()
        mock_create_chat.return_value = mock_chat_obj
        
        # 模拟代理
        mock_agent = MagicMock()
        
        # 模拟代理流式响应步骤
        thinking_step = MockAgentStep("thinking", thinking="正在思考如何查询数据库")
        tool_call_step = MockAgentStep(
            "tool_call", 
            tool_call=MagicMock(
                tool_name="query_testdb",
                tool_input={"natural_language_query": "查询所有用户"}
            )
        )
        tool_output_step = MockAgentStep(
            "tool_output",
            tool_output=ToolOutput(
                content="生成的SQL: SELECT * FROM users\n\n结果: 找到5个用户记录",
                tool_name="query_testdb",
                raw_input={"natural_language_query": "查询所有用户"},
                raw_output="SELECT * FROM users LIMIT 100"
            )
        )
        response_step = MockAgentStep(
            "response",
            response="数据库中有5个用户记录",
            delta="数据库中有5个用户记录"
        )
        
        # 设置代理stream_chat的返回值
        mock_agent.stream_chat.return_value = [
            thinking_step,
            tool_call_step,
            tool_output_step,
            response_step
        ]
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
        
        # 设置数据库工具和代理
        chat_flow.db_tools = [mock_db_tool]
        chat_flow.agent = mock_agent
        
        # 创建生成器模拟函数
        def mock_generator(result=None):
            yield create_mock_chat_event()
            return result
        
        # 模拟_chat_start方法
        mock_user_message = MagicMock()
        mock_assistant_message = MagicMock()
        chat_flow._chat_start = MagicMock(return_value=mock_generator((mock_user_message, mock_assistant_message)))
        
        # 模拟_search_knowledge_graph方法
        mock_kg = MagicMock()
        chat_flow._search_knowledge_graph = MagicMock(return_value=mock_generator((mock_kg, "")))
        
        # 模拟_refine_user_question方法
        chat_flow._refine_user_question = MagicMock(return_value=mock_generator("优化后的问题：查询所有用户"))
        
        # 模拟_search_relevance_chunks方法
        chat_flow._search_relevance_chunks = MagicMock(return_value=mock_generator([]))
        
        # 模拟_chat_finish方法
        chat_flow._chat_finish = MagicMock(return_value=mock_generator(None))
        
        # 模拟_trace_manager以避免langfuse相关错误
        mock_span = MagicMock()
        mock_span_context = MagicMock()
        mock_span_context.__enter__.return_value = mock_span
        mock_span_context.__exit__.return_value = None
        
        mock_trace_manager = MagicMock()
        mock_trace_manager.span.return_value = mock_span_context
        chat_flow._trace_manager = mock_trace_manager
        
        # 执行_builtin_chat
        events = list(chat_flow._builtin_chat())
        
        # 验证调用
        chat_flow._chat_start.assert_called_once()
        chat_flow._search_knowledge_graph.assert_called_once()
        chat_flow._refine_user_question.assert_called_once()
        chat_flow._search_relevance_chunks.assert_called_once()
        
        # 验证代理stream_chat被调用
        mock_agent.stream_chat.assert_called_once()
        
        # 验证_chat_finish被调用
        chat_flow._chat_finish.assert_called_once()

    @patch("app.rag.chat.config.ChatEngineConfig.load_from_db")
    @patch("app.repositories.chat_repo.create")
    @patch("app.rag.chat.chat_flow.ReActAgent")
    def test_builtin_chat_fallback_to_rag(
        self,
        mock_react_agent,
        mock_create_chat,
        mock_load_config,
        patch_dspy_lm
    ):
        """测试_builtin_chat在代理处理失败时回退到RAG的情况"""
        # 设置模拟对象
        db_session = create_test_db_session()
        user = create_test_user()
        
        # 模拟LLM和配置
        mock_llm = create_test_llm()
        mock_fast_llm = create_test_llm()
        mock_engine_config = MagicMock()
        mock_engine_config.is_external_engine = False
        mock_engine_config.database = MagicMock()
        mock_engine_config.database.tool_mode = "autonomous"
        mock_engine_config.get_db_chat_engine.return_value = MagicMock()
        mock_engine_config.get_llama_llm.return_value = mock_llm
        mock_engine_config.get_fast_llama_llm.return_value = mock_fast_llm
        mock_engine_config.get_knowledge_bases.return_value = []
        mock_engine_config.clarify_question = False
        
        # 设置模拟返回值
        mock_load_config.return_value = mock_engine_config
        mock_create_chat.return_value = MagicMock()
        
        # 模拟代理
        mock_agent = MagicMock()
        mock_agent.stream_chat.side_effect = Exception("模拟代理失败")
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
        
        # 设置数据库工具和代理
        chat_flow.db_tools = [MagicMock()]
        chat_flow.agent = mock_agent
        
        # 使用辅助方法创建生成器模拟
        def mock_generator(result=None):
            yield create_mock_chat_event()
            return result
            
        # 模拟方法
        mock_user_message = MagicMock()
        mock_assistant_message = MagicMock()
        chat_flow._chat_start = MagicMock(return_value=mock_generator((mock_user_message, mock_assistant_message)))
        mock_kg = MagicMock()
        chat_flow._search_knowledge_graph = MagicMock(return_value=mock_generator((mock_kg, "")))
        chat_flow._refine_user_question = MagicMock(return_value=mock_generator("优化后的问题"))
        chat_flow._search_relevance_chunks = MagicMock(return_value=mock_generator([]))
        chat_flow._fallback_to_rag = MagicMock(return_value=mock_generator(("回退答案", [])))
        chat_flow._chat_finish = MagicMock(return_value=mock_generator(None))
        
        # 模拟_trace_manager以避免langfuse相关错误
        mock_span = MagicMock()
        mock_span_context = MagicMock()
        mock_span_context.__enter__.return_value = mock_span
        mock_span_context.__exit__.return_value = None
        
        mock_trace_manager = MagicMock()
        mock_trace_manager.span.return_value = mock_span_context
        chat_flow._trace_manager = mock_trace_manager
        
        # 执行_builtin_chat
        list(chat_flow._builtin_chat())
        
        # 验证调用
        mock_agent.stream_chat.assert_called_once()
        chat_flow._fallback_to_rag.assert_called_once()
        chat_flow._chat_finish.assert_called_once()
        
    @patch("app.rag.chat.config.ChatEngineConfig.load_from_db")
    @patch("app.repositories.chat_repo.create")
    def test_builtin_chat_without_database_tools(
        self,
        mock_create_chat,
        mock_load_config,
        patch_dspy_lm
    ):
        """测试_builtin_chat不使用数据库工具的情况"""
        # 设置模拟对象
        db_session = create_test_db_session()
        user = create_test_user()
        
        # 模拟LLM和配置
        mock_llm = create_test_llm()
        mock_fast_llm = create_test_llm()
        mock_engine_config = MagicMock()
        mock_engine_config.is_external_engine = False
        mock_engine_config.get_db_chat_engine.return_value = MagicMock()
        mock_engine_config.get_llama_llm.return_value = mock_llm
        mock_engine_config.get_fast_llama_llm.return_value = mock_fast_llm
        mock_engine_config.get_knowledge_bases.return_value = []
        mock_engine_config.clarify_question = False
        
        # 设置模拟返回值
        mock_load_config.return_value = mock_engine_config
        mock_create_chat.return_value = MagicMock()
        
        # 创建ChatFlow对象
        chat_flow = ChatFlow(
            db_session=db_session,
            user=user,
            browser_id="test_browser_id",
            origin="http://localhost",
            chat_messages=[create_test_chat_message("这是一个一般问题")],
            engine_name="default"
        )
        
        # 没有设置数据库工具和代理
        chat_flow.db_tools = []
        chat_flow.agent = None
        
        # 使用辅助方法创建生成器模拟
        def mock_generator(result=None):
            yield create_mock_chat_event()
            return result
        
        # 模拟方法
        mock_user_message = MagicMock()
        mock_assistant_message = MagicMock()
        chat_flow._chat_start = MagicMock(return_value=mock_generator((mock_user_message, mock_assistant_message)))
        mock_kg = MagicMock()
        chat_flow._search_knowledge_graph = MagicMock(return_value=mock_generator((mock_kg, "")))
        chat_flow._refine_user_question = MagicMock(return_value=mock_generator("优化后的问题"))
        chat_flow._search_relevance_chunks = MagicMock(return_value=mock_generator([]))
        chat_flow._generate_answer = MagicMock(return_value=mock_generator(("标准RAG答案", [])))
        chat_flow._chat_finish = MagicMock(return_value=mock_generator(None))
        
        # 模拟_trace_manager以避免langfuse相关错误
        mock_span = MagicMock()
        mock_span_context = MagicMock()
        mock_span_context.__enter__.return_value = mock_span
        mock_span_context.__exit__.return_value = None
        
        mock_trace_manager = MagicMock()
        mock_trace_manager.span.return_value = mock_span_context
        chat_flow._trace_manager = mock_trace_manager
        
        # 执行_builtin_chat
        list(chat_flow._builtin_chat())
        
        # 验证调用
        chat_flow._generate_answer.assert_called_once()
        chat_flow._chat_finish.assert_called_once() 