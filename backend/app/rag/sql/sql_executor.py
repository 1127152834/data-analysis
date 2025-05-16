"""SQL执行器模块，用于执行SQL查询"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel
import logging
from sqlalchemy.orm import Session
from llama_index.core.llms import LLM

from app.rag.types import SQLExecutionConfig

logger = logging.getLogger("app.rag.sql.sql_executor")

class SQLExecutionResult(BaseModel):
    """SQL执行结果"""
    success: bool = True
    sql: Optional[str] = None
    execution_result: Optional[Any] = None
    message: Optional[str] = None
    error: Optional[str] = None

class SQLExecutor:
    """SQL执行器类，用于执行SQL查询"""
    
    def __init__(self, db_session: Session, config: SQLExecutionConfig, llm: LLM = None):
        """初始化SQL执行器
        
        参数:
            db_session: 数据库会话
            config: SQL执行配置
            llm: 大语言模型实例
        """
        self.db_session = db_session
        self.config = config
        self.llm = llm
        self.logger = logger
    
    def execute(self, query: str, context: Optional[str] = None) -> SQLExecutionResult:
        """执行SQL查询
        
        参数:
            query: 自然语言查询
            context: 上下文信息
            
        返回:
            SQL执行结果
        """
        try:
            # 简单实现，实际应使用LLM转换自然语言为SQL
            sql = self._convert_to_sql(query, context)
            
            # 执行SQL
            if sql:
                result = self._execute_sql(sql)
                return SQLExecutionResult(
                    success=True,
                    sql=sql,
                    execution_result=result,
                    message="查询成功执行"
                )
            else:
                return SQLExecutionResult(
                    success=False,
                    message="无法转换为有效的SQL查询"
                )
                
        except Exception as e:
            self.logger.error(f"执行SQL查询出错: {str(e)}", exc_info=True)
            return SQLExecutionResult(
                success=False,
                message=f"执行SQL查询出错: {str(e)}",
                error=str(e)
            )
    
    def execute_with_database_id(self, query: str, database_id: str, context: Optional[str] = None) -> SQLExecutionResult:
        """使用指定数据库执行SQL查询
        
        参数:
            query: 自然语言查询
            database_id: 数据库ID
            context: 上下文信息
            
        返回:
            SQL执行结果
        """
        try:
            # 简单实现，实际应使用LLM转换自然语言为SQL
            sql = self._convert_to_sql(query, context)
            
            # 执行SQL
            if sql:
                # 这里应该根据database_id连接相应的数据库
                result = self._execute_sql(sql, database_id)
                return SQLExecutionResult(
                    success=True,
                    sql=sql,
                    execution_result=result,
                    message=f"在数据库 {database_id} 中成功执行查询"
                )
            else:
                return SQLExecutionResult(
                    success=False,
                    message="无法转换为有效的SQL查询"
                )
                
        except Exception as e:
            self.logger.error(f"在数据库 {database_id} 中执行SQL查询出错: {str(e)}", exc_info=True)
            return SQLExecutionResult(
                success=False,
                message=f"在数据库 {database_id} 中执行SQL查询出错: {str(e)}",
                error=str(e)
            )
    
    def _convert_to_sql(self, query: str, context: Optional[str] = None) -> Optional[str]:
        """将自然语言查询转换为SQL
        
        参数:
            query: 自然语言查询
            context: 上下文信息
            
        返回:
            SQL查询语句
        """
        # 这里应使用LLM将自然语言转换为SQL
        # 简单实现，实际项目中应使用LLM
        if self.llm and hasattr(self.llm, "complete"):
            # 构建提示模板
            prompt = f"""将以下自然语言查询转换为SQL查询：
            
查询：{query}

"""
            if context:
                prompt += f"""
上下文信息：
{context}
"""
            
            # 使用LLM生成SQL
            try:
                response = self.llm.complete(prompt)
                sql = self._extract_sql_from_response(response.text)
                return sql
            except Exception as e:
                self.logger.error(f"使用LLM转换SQL失败: {str(e)}", exc_info=True)
                # 简易回退
                return f"SELECT * FROM table WHERE description LIKE '%{query}%' LIMIT 10"
        else:
            # 简易回退
            return f"SELECT * FROM table WHERE description LIKE '%{query}%' LIMIT 10"
    
    def _extract_sql_from_response(self, response: str) -> Optional[str]:
        """从LLM响应中提取SQL
        
        参数:
            response: LLM响应文本
            
        返回:
            提取的SQL
        """
        # 简单实现，提取SQL代码块
        if "```sql" in response:
            # 从Markdown代码块中提取SQL
            parts = response.split("```sql")
            if len(parts) > 1:
                sql_parts = parts[1].split("```")
                if sql_parts:
                    return sql_parts[0].strip()
        
        # 如果没有明确的SQL代码块，假设整个响应就是SQL
        return response.strip()
    
    def _execute_sql(self, sql: str, database_id: Optional[str] = None) -> Any:
        """执行SQL语句
        
        参数:
            sql: SQL语句
            database_id: 数据库ID
            
        返回:
            执行结果
        """
        # 实际项目中应使用指定的数据库连接执行SQL
        # 这里返回一个示例结果
        from sqlalchemy import text
        
        try:
            # 使用SQLAlchemy执行SQL
            result = self.db_session.execute(text(sql))
            
            # 转换为可序列化的结果
            if result.returns_rows:
                columns = result.keys()
                rows = []
                for row in result:
                    row_dict = {}
                    for i, column in enumerate(columns):
                        row_dict[column] = row[i]
                    rows.append(row_dict)
                return rows
            else:
                return {"affected_rows": result.rowcount}
                
        except Exception as e:
            self.logger.error(f"执行SQL语句出错: {str(e)}", exc_info=True)
            raise 