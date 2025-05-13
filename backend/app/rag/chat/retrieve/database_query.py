"""
数据库查询模块

该模块负责基于用户问题生成SQL/NoSQL查询，并执行这些查询
"""

import logging
from datetime import datetime, timedelta
import re
import time
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import UUID
from pydantic import BaseModel

from sqlmodel import Session
from llama_index.core.llms import LLM

from app.rag.chat.config import ChatEngineConfig, DatabaseRoutingStrategy
from app.repositories.database_connection import DatabaseConnectionRepo
from app.repositories.database_query_history import DatabaseQueryHistoryRepo
from app.models.database_connection import DatabaseConnection, DatabaseType
from app.models.database_query_history import DatabaseQueryHistory

logger = logging.getLogger(__name__)


class DatabaseQueryResult(BaseModel):
    """数据库查询结果模型"""
    connection_id: int
    connection_name: str
    database_type: DatabaseType
    question: str  # 添加原始问题字段
    query: str
    result: List[Dict[str, Any]]
    error: Optional[str] = None
    executed_at: datetime = datetime.now()
    routing_score: Optional[float] = None
    execution_time_ms: Optional[int] = None  # 添加执行时间字段
    rows_returned: Optional[int] = None  # 添加返回行数字段
    
    def to_context_str(self) -> str:
        """转换为文本上下文"""
        if self.error:
            return f"从【{self.connection_name}】数据库查询失败: {self.error}"
            
        result_str = ""
        if len(self.result) > 0:
            # 首行输出列名
            cols = list(self.result[0].keys())
            header = " | ".join(cols)
            separator = "-" * len(header)
            rows = [header, separator]
            
            # 添加行数据
            for row in self.result:
                row_str = " | ".join([str(row.get(col, "")) for col in cols])
                rows.append(row_str)
                
            result_str = "\n".join(rows)
        else:
            result_str = "查询未返回任何结果"
            
        context = f"""
从【{self.connection_name}】数据库查询:
```sql
{self.query}
```

查询结果:
```
{result_str}
```
"""
        return context

    def to_query_history(
        self, 
        chat_id: UUID, 
        user_id: Optional[UUID] = None,
        chat_message_id: Optional[int] = None,
        routing_context: Optional[Dict] = None
    ) -> DatabaseQueryHistory:
        """将查询结果转换为历史记录模型"""
        # 创建结果摘要
        result_summary = None
        result_sample = None
        
        if not self.error and self.result and len(self.result) > 0:
            # 创建结果摘要
            result_summary = {
                "columns": list(self.result[0].keys()),
                "row_count": len(self.result)
            }
            
            # 获取结果样本 (最多10行)
            sample_size = min(10, len(self.result))
            result_sample = self.result[:sample_size]
        
        # 创建查询历史记录
        history = DatabaseQueryHistory(
            chat_id=chat_id,
            chat_message_id=chat_message_id,
            user_id=user_id,
            connection_id=self.connection_id,
            connection_name=self.connection_name,
            database_type=self.database_type,
            question=self.question,
            query=self.query,
            is_successful=self.error is None,
            error_message=self.error,
            result_summary=result_summary,
            result_sample=result_sample,
            execution_time_ms=self.execution_time_ms,
            rows_returned=len(self.result) if self.result else 0,
            routing_score=self.routing_score,
            routing_context=routing_context,
            executed_at=self.executed_at
        )
        
        return history


class DatabaseQueryManager:
    """数据库查询管理器
    
    负责管理数据库查询相关的操作，包括查询生成、执行和结果处理。
    """
    
    def __init__(
        self,
        db_session: Session, 
        engine_config: ChatEngineConfig,
        llm: Optional[LLM] = None,
    ):
        """
        初始化数据库查询管理器
        
        Args:
            db_session: 数据库会话
            engine_config: 引擎配置
            llm: 语言模型（可选）
        """
        self.db_session = db_session
        self.engine_config = engine_config
        self.llm = llm
        self.db_repo = DatabaseConnectionRepo()
        self.history_repo = DatabaseQueryHistoryRepo()
        
    def query_databases(
        self, 
        question: str, 
        chat_id: UUID,
        user_id: Optional[UUID] = None,
        chat_message_id: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> List[DatabaseQueryResult]:
        """
        查询多个数据库
        
        Args:
            question: 用户问题
            chat_id: 聊天ID
            user_id: 用户ID
            chat_message_id: 聊天消息ID
            context: 对话上下文（可选）
            
        Returns:
            List[DatabaseQueryResult]: 查询结果列表
        """
        # 简化实现，后续填充完整功能
        logger.info(f"收到数据库查询请求: 问题={question}, 聊天ID={chat_id}, 用户ID={user_id}")
        results = []
        
        try:
            # 确保数据库功能已启用
            if not hasattr(self.engine_config, 'database') or not self.engine_config.database.enabled:
                logger.info("数据库查询功能未启用")
                return []
            
            # 获取配置的数据库连接
            if not self.engine_config.database.linked_database_configs:
                logger.info("没有配置的数据库连接")
                return []
            
            # 执行空查询逻辑，返回示例结果
            # 实际项目中，这里应该实现查询路由、SQL生成和执行功能
            start_time = time.time()
            
            # 查询路由策略
            routing_strategy = self.engine_config.database.routing_strategy or DatabaseRoutingStrategy.FIRST_AVAILABLE
            routing_context = {"strategy": routing_strategy.value, "question": question}
            
            # 模拟查询执行
            result = DatabaseQueryResult(
                connection_id=1,
                connection_name="示例数据库",
                database_type=DatabaseType.MYSQL,
                question=question,  # 保存原始问题
                query="SELECT 'Hello' as message",
                result=[{"message": "数据库查询功能正在构建中"}],
                routing_score=1.0,
                execution_time_ms=int((time.time() - start_time) * 1000),
                rows_returned=1
            )
            
            # 保存查询历史
            query_history = result.to_query_history(
                chat_id=chat_id,
                user_id=user_id,
                chat_message_id=chat_message_id,
                routing_context=routing_context
            )
            self.history_repo.create(self.db_session, query_history)
            
            results.append(result)
            return results
            
        except Exception as e:
            logger.error(f"数据库查询过程出错: {str(e)}")
            
            # 记录错误的查询历史
            error_result = DatabaseQueryResult(
                connection_id=-1,
                connection_name="查询出错",
                database_type=DatabaseType.UNKNOWN,
                question=question,
                query="",
                result=[],
                error=str(e),
                execution_time_ms=0,
                rows_returned=0
            )
            
            # 保存错误查询历史
            query_history = error_result.to_query_history(
                chat_id=chat_id,
                user_id=user_id,
                chat_message_id=chat_message_id
            )
            self.history_repo.create(self.db_session, query_history)
            
            return []
            
    def get_recent_queries(
        self, 
        chat_id: UUID, 
        limit: int = 5,
        time_window: Optional[timedelta] = None
    ) -> List[DatabaseQueryResult]:
        """
        获取最近的查询历史
        
        Args:
            chat_id: 聊天ID
            limit: 返回结果数量限制
            time_window: 时间窗口（可选，例如最近30分钟的查询）
            
        Returns:
            List[DatabaseQueryResult]: 查询结果列表
        """
        try:
            # 从数据库获取最近的查询历史
            query_histories = self.history_repo.get_recent_queries_in_chat(
                self.db_session, 
                chat_id=chat_id, 
                limit=limit,
                since=datetime.now() - time_window if time_window else None
            )
            
            # 转换为DatabaseQueryResult对象
            results = []
            for history in query_histories:
                # 从历史记录中还原结果
                result_list = []
                if history.is_successful and history.result_sample:
                    result_list = history.result_sample
                
                result = DatabaseQueryResult(
                    connection_id=history.connection_id,
                    connection_name=history.connection_name,
                    database_type=history.database_type,
                    question=history.question,
                    query=history.query,
                    result=result_list,
                    error=history.error_message,
                    executed_at=history.executed_at,
                    routing_score=history.routing_score,
                    execution_time_ms=history.execution_time_ms,
                    rows_returned=history.rows_returned
                )
                results.append(result)
                
            return results
        except Exception as e:
            logger.error(f"获取最近查询历史出错: {str(e)}")
            return []
    
    def get_query_statistics(self, chat_id: UUID) -> Dict[str, Any]:
        """
        获取聊天的查询统计信息
        
        Args:
            chat_id: 聊天ID
            
        Returns:
            Dict: 统计信息字典
        """
        try:
            return self.history_repo.get_query_stats_by_chat(self.db_session, chat_id)
        except Exception as e:
            logger.error(f"获取查询统计信息出错: {str(e)}")
            return {
                "total_queries": 0,
                "successful_queries": 0,
                "success_rate": 0,
                "databases_used": []
            } 