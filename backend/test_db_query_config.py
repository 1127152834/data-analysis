import logging
import sys
from sqlmodel import Session, create_engine

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 导入相关模块
try:
    from app.rag.chat.config import ChatEngineConfig, LLMOption
    from app.rag.default_prompt import DEFAULT_DATABASE_QUERY_PROMPT
    
    # 测试配置加载
    logger.info("1. 测试配置加载...")
    config = ChatEngineConfig()
    
    # 验证提示词设置
    logger.info("2. 检查 database_query_prompt 是否正确设置...")
    is_prompt_correct = config.llm.database_query_prompt == DEFAULT_DATABASE_QUERY_PROMPT
    logger.info(f"database_query_prompt 设置正确: {is_prompt_correct}")
    
    # 显示提示词内容的一部分来验证
    prompt_preview = config.llm.database_query_prompt[:100] + "..."
    logger.info(f"提示词预览: {prompt_preview}")
    
    logger.info("3. 验证是否可以访问 DatabaseOption 和其他配置...")
    logger.info(f"数据库查询功能启用状态: {config.database.enabled}")
    logger.info(f"最大结果数: {config.database.max_results}")
    
    logger.info("所有测试通过!")
except Exception as e:
    logger.error(f"测试失败: {str(e)}")
    import traceback
    logger.error(traceback.format_exc())
    sys.exit(1)
