"""
SQL查询工具适配器模块

提供将现有SQLQueryTool封装为符合Agent工具格式的适配器
"""

import logging
import uuid
from typing import Dict, List, Optional, Any

from llama_index.core.tools.types import BaseTool, ToolMetadata, ToolOutput
from sqlmodel import Session

from app.rag.chat.config import ChatEngineConfig
from app.rag.agent.tools.sql_query_tool import SQLQueryTool

logger = logging.getLogger(__name__)

class SQLQueryToolAdapter(BaseTool):
    """
    SQL查询工具适配器
    
    封装现有SQLQueryTool，使其符合Agent工具格式
    """
    
    def __init__(
        self,
        db_session: Session,
        engine_config: ChatEngineConfig,
        description: str = "通过SQL查询数据库并返回结果，能够将自然语言转换为SQL",
    ):
        """
        初始化SQL查询工具适配器
        
        参数:
            db_session: 数据库会话对象
            engine_config: 聊天引擎配置
            description: 工具描述
        """
        self.db_session = db_session
        self.engine_config = engine_config
        
        # 初始化原始工具
        self.sql_tool = SQLQueryTool(
            db_session=db_session,
            config=engine_config,
            llm=engine_config.get_llama_llm(db_session),
        )
        
        # 直接设置元数据
        self._metadata = ToolMetadata(name="sql_query", description=description)
    
    @property
    def metadata(self) -> ToolMetadata:
        """返回工具的元数据信息"""
        return self._metadata
    
    def _format_sql_result(self, sql_result: Dict) -> Dict:
        """
        格式化SQL查询结果为前端友好格式
        
        参数:
            sql_result: 原始SQL查询结果
            
        返回:
            Dict: 格式化后的结果
        """
        # 如果结果是字符串，则是文本格式的结果
        if isinstance(sql_result, str):
            return {
                "result": sql_result,
                "format": "text",
                "query_id": str(uuid.uuid4()),
                "success": True
            }
        
        # 如果是NodeWithScore列表，则提取文档内容
        if hasattr(sql_result, "__iter__") and hasattr(sql_result[0], "node"):
            content = sql_result[0].node.text if sql_result else ""
            return {
                "result": content,
                "format": "text",
                "query_id": str(uuid.uuid4()),
                "success": True
            }
        
        # 默认返回原始结果
        return {
            "result": sql_result,
            "format": "unknown",
            "query_id": str(uuid.uuid4()),
            "success": True
        }
    
    def __call__(self, input_text: str, page: int = 1, page_size: int = 100, format_type: str = "markdown") -> ToolOutput:
        """
        执行SQL查询
        
        参数:
            input_text: 用户输入文本/问题
            page: 页码
            page_size: 每页大小
            format_type: 输出格式类型
            
        返回:
            ToolOutput: SQL查询结果的工具输出对象
        """
        logger.info(f"执行SQL查询: {input_text}")
        try:
            # 调用原始工具
            result = self.sql_tool(
                input_text=input_text,
                page=page,
                page_size=page_size,
                format_type=format_type
            )
            
            # 格式化结果
            formatted_result = self._format_sql_result(result)
            
            # 记录用户输入
            input_params = {
                "input_text": input_text,
                "page": page,
                "page_size": page_size,
                "format_type": format_type
            }
            
            # 返回ToolOutput对象
            return ToolOutput(
                content=str(formatted_result.get("result", "")),
                tool_name=self.metadata.name,
                raw_output=formatted_result,
                raw_input=input_params
            )
        except Exception as e:
            logger.error(f"SQL查询失败: {str(e)}")
            error_result = {
                "result": f"SQL查询时出错: {str(e)}",
                "format": "text",
                "error": str(e),
                "query_id": str(uuid.uuid4()),
                "success": False
            }
            
            # 记录用户输入
            input_params = {
                "input_text": input_text,
                "page": page,
                "page_size": page_size,
                "format_type": format_type
            }
            
            # 错误情况也返回ToolOutput对象
            return ToolOutput(
                content=f"SQL查询时出错: {str(e)}",
                tool_name=self.metadata.name,
                raw_output=error_result,
                raw_input=input_params
            )