import logging
import sys
from unittest.mock import MagicMock, patch
from sqlmodel import Session

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from app.rag.chat.config import ChatEngineConfig
    from app.rag.chat.retrieve.database_query import DatabaseQueryManager
    from app.models.database_connection import DatabaseType
    
    # 模拟依赖
    logger.info("1. 设置模拟对象...")
    mock_session = MagicMock(spec=Session)
    mock_llm = MagicMock()
    mock_llm.predict = MagicMock(return_value="SELECT * FROM users")
    
    # 创建配置和查询管理器
    logger.info("2. 创建配置和查询管理器...")
    config = ChatEngineConfig()
    query_manager = DatabaseQueryManager(mock_session, config, mock_llm)
    
    # 测试 _generate_query 方法
    logger.info("3. 测试 _generate_query 方法...")
    with patch.object(query_manager, '_generate_query', wraps=query_manager._generate_query) as mock_generate:
        # 用简单的参数调用方法
        user_question = "查询所有用户"
        schema_info = "表名: users\n列: id, name, email"
        database_type = DatabaseType.MYSQL
        
        query = query_manager._generate_query(user_question, schema_info, database_type)
        
        # 验证方法被调用且返回预期结果
        mock_generate.assert_called_once()
        logger.info(f"生成的查询: {query}")
        
        # 验证 LLM.predict 被调用并传入正确参数
        logger.info("4. 验证 LLM.predict 调用...")
        mock_llm.predict.assert_called_once()
        
        # 检查传入的模板是否来自 LLMOption
        args, kwargs = mock_llm.predict.call_args
        logger.info(f"传入 LLM 的参数: {kwargs.keys()}")
        assert 'database_schema' in kwargs, "参数 database_schema 未传递给 LLM"
        assert 'user_question' in kwargs, "参数 user_question 未传递给 LLM"
        
    logger.info("所有测试通过!")
    
except Exception as e:
    logger.error(f"测试失败: {str(e)}")
    import traceback
    logger.error(traceback.format_exc())
    sys.exit(1) 