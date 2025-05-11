"""
数据库查询模块

该模块负责基于用户问题生成SQL/NoSQL查询，并执行这些查询
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union
from pydantic import BaseModel

from sqlmodel import Session
from llama_index.core.llms import LLM
from llama_index.core.prompts.rich import RichPromptTemplate

from app.rag.chat.config import ChatEngineConfig
from app.repositories.database_connection import DatabaseConnectionRepo
from app.models.database_connection import DatabaseConnection, DatabaseType
from app.rag.database import get_connector

logger = logging.getLogger(__name__)


class DatabaseQueryResult(BaseModel):
    """数据库查询结果模型"""
    connection_id: int
    connection_name: str
    database_type: DatabaseType
    query: str
    result: List[Dict[str, Any]]
    error: Optional[str] = None
    executed_at: datetime = datetime.now()
    
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


class DatabaseQueryManager:
    """数据库查询管理器"""
    
    def __init__(
        self,
        db_session: Session,
        engine_config: ChatEngineConfig,
        llm: LLM,
    ):
        self.db_session = db_session
        self.engine_config = engine_config
        self.llm = llm
        self.repo = DatabaseConnectionRepo()
        
    def query_databases(self, user_question: str) -> List[DatabaseQueryResult]:
        """对所有连接的数据库执行查询"""
        db_option = self.engine_config.database
        if not db_option.enabled or not db_option.linked_database_connections:
            logger.debug("数据库查询功能未启用或未配置连接")
            return []
            
        results = []
        # 获取链接的数据库连接
        connection_ids = [conn.id for conn in db_option.linked_database_connections]
        connections = self.repo.get_by_ids(self.db_session, connection_ids)
        
        for conn in connections:
            try:
                query_result = self._query_single_database(conn, user_question)
                results.append(query_result)
            except Exception as e:
                logger.error(f"查询数据库 {conn.name} (ID: {conn.id}) 时出错: {str(e)}")
                results.append(
                    DatabaseQueryResult(
                        connection_id=conn.id,
                        connection_name=conn.name,
                        database_type=conn.database_type,
                        query="",
                        result=[],
                        error=str(e)
                    )
                )
                
        return results
        
    def _query_single_database(
        self, 
        connection: DatabaseConnection, 
        user_question: str
    ) -> DatabaseQueryResult:
        """查询单个数据库"""
        # 1. 获取数据库元数据
        metadata = connection.metadata_cache
        if not metadata:
            try:
                # 尝试获取最新元数据
                connector = get_connector(connection)
                if connector:
                    metadata = connector.get_metadata()
                    # 更新元数据缓存
                    self.repo.update_metadata(
                        self.db_session, 
                        connection.id, 
                        metadata
                    )
            except Exception as e:
                logger.error(f"获取数据库 {connection.name} 元数据时出错: {str(e)}")
                
        if not metadata:
            return DatabaseQueryResult(
                connection_id=connection.id,
                connection_name=connection.name,
                database_type=connection.database_type,
                query="",
                result=[],
                error="无法获取数据库元数据"
            )
            
        # 2. 格式化元数据为文本
        schema_text = self._format_schema_info(connection.database_type, metadata)
        
        # 3. 使用LLM生成查询
        query = self._generate_query(user_question, schema_text, connection.database_type)
        if not query or query == "无法生成查询":
            return DatabaseQueryResult(
                connection_id=connection.id,
                connection_name=connection.name,
                database_type=connection.database_type,
                query=query,
                result=[],
                error="无法基于用户问题生成查询"
            )
            
        # 4. 执行查询
        try:
            connector = get_connector(connection)
            if not connector:
                return DatabaseQueryResult(
                    connection_id=connection.id,
                    connection_name=connection.name,
                    database_type=connection.database_type,
                    query=query,
                    result=[],
                    error="无法创建数据库连接器"
                )
                
            # 确保是只读查询
            if self.engine_config.database.read_only:
                # 对SQL类型数据库，拒绝非SELECT查询
                if connection.database_type in [
                    DatabaseType.MYSQL, 
                    DatabaseType.POSTGRESQL, 
                    DatabaseType.SQLSERVER, 
                    DatabaseType.ORACLE
                ]:
                    if not query.strip().upper().startswith("SELECT"):
                        return DatabaseQueryResult(
                            connection_id=connection.id,
                            connection_name=connection.name,
                            database_type=connection.database_type,
                            query=query,
                            result=[],
                            error="只允许执行SELECT查询"
                        )
                # 对MongoDB，拒绝带更新操作的查询
                elif connection.database_type == DatabaseType.MONGODB:
                    forbidden_ops = [
                        "insert", "update", "delete", "remove", "drop", 
                        "createIndex", "createCollection"
                    ]
                    if any(op in query.lower() for op in forbidden_ops):
                        return DatabaseQueryResult(
                            connection_id=connection.id,
                            connection_name=connection.name,
                            database_type=connection.database_type,
                            query=query,
                            result=[],
                            error="只允许执行读取操作"
                        )
                        
            # 执行查询并限制结果数量
            result, error = connector.execute_query(
                query, 
                limit=self.engine_config.database.max_results
            )
            
            # 更新数据库连接状态
            self.repo.update_status(
                self.db_session, 
                connection.id, 
                "connected",
                datetime.now()
            )
            
            if error:
                return DatabaseQueryResult(
                    connection_id=connection.id,
                    connection_name=connection.name,
                    database_type=connection.database_type,
                    query=query,
                    result=[],
                    error=error
                )
                
            return DatabaseQueryResult(
                connection_id=connection.id,
                connection_name=connection.name,
                database_type=connection.database_type,
                query=query,
                result=result,
                error=None
            )
                
        except Exception as e:
            logger.error(f"执行查询 {query} 时出错: {str(e)}")
            return DatabaseQueryResult(
                connection_id=connection.id,
                connection_name=connection.name,
                database_type=connection.database_type,
                query=query,
                result=[],
                error=str(e)
            )
    
    def _generate_query(
        self, 
        user_question: str, 
        schema_info: str,
        database_type: DatabaseType
    ) -> str:
        """使用LLM生成查询语句"""
        prompt_template = RichPromptTemplate(
            self.engine_config.llm.database_query_prompt
        )
        
        query = self.llm.predict(
            prompt_template,
            database_schema=schema_info,
            user_question=user_question,
            database_type=database_type.value
        )
        
        return query.strip()
        
    def _format_schema_info(
        self, 
        database_type: DatabaseType, 
        metadata: Dict[str, Any]
    ) -> str:
        """将元数据格式化为文本表示"""
        if not metadata or not metadata.get("tables"):
            return "数据库模式信息不可用"
            
        schema_info = []
        database_name = metadata.get("database", "未知数据库")
        schema_info.append(f"数据库: {database_name}")
        
        tables = metadata.get("tables", {})
        for table_name, table_info in tables.items():
            # 表格信息
            schema_info.append(f"\n表名: {table_name}")
            
            # 列信息
            columns = table_info.get("columns", {})
            if columns:
                cols_info = []
                for col_name, col_info in columns.items():
                    data_type = col_info.get("type", "未知")
                    nullable = "NULL" if col_info.get("nullable", True) else "NOT NULL"
                    primary = "主键" if col_info.get("primary_key", False) else ""
                    foreign = f"外键->{col_info.get('foreign_key')}" if col_info.get("foreign_key") else ""
                    
                    col_desc = f"  - {col_name} ({data_type}, {nullable}"
                    if primary:
                        col_desc += f", {primary}"
                    if foreign:
                        col_desc += f", {foreign}"
                    col_desc += ")"
                    
                    cols_info.append(col_desc)
                
                schema_info.append("列:")
                schema_info.extend(cols_info)
                
            # 索引信息
            indexes = table_info.get("indexes", [])
            if indexes:
                schema_info.append("索引:")
                for idx in indexes:
                    idx_name = idx.get("name", "未命名")
                    idx_cols = ", ".join(idx.get("columns", []))
                    idx_unique = "唯一" if idx.get("unique", False) else ""
                    schema_info.append(f"  - {idx_name}: ({idx_cols}) {idx_unique}")
        
        return "\n".join(schema_info) 