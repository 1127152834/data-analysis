"""
SQL查询工具模块

提供与数据库交互的工具类，支持多数据库智能路由和查询执行
"""

import logging
import time
from typing import Dict, List, Optional, Any, Tuple, Union
from sqlmodel import Session

from llama_index.core.schema import Document, NodeWithScore
from llama_index.core.tools.types import BaseTool
from llama_index.core.llms.llm import LLM
from llama_index.core.query_engine import NLSQLTableQueryEngine, RouterQueryEngine
from llama_index.core import SQLDatabase
from sqlalchemy import create_engine, MetaData, Table, inspect
from llama_index.core.selectors import LLMSingleSelector

from app.models.database_connection import DatabaseConnection
from app.rag.database import get_connector
from app.rag.database.base import BaseConnector
from app.rag.chat.config import ChatEngineConfig, LinkedDatabaseConfig

logger = logging.getLogger(__name__)

class SQLQueryResult:
    """
    SQL查询结果类
    
    封装SQL查询的结果数据，包括查询文本、结果集和元数据
    """
    def __init__(
        self, 
        sql: str, 
        results: List[Dict[str, Any]], 
        column_names: List[str],
        execution_time: float,
        error: Optional[str] = None,
        truncated: bool = False,
        database_name: str = ""
    ):
        self.sql = sql
        self.results = results
        self.column_names = column_names
        self.execution_time = execution_time
        self.error = error
        self.truncated = truncated
        self.database_name = database_name
    
    def to_document(self) -> Document:
        """
        将查询结果转换为文档对象
        
        用于集成到检索结果中
        
        返回:
            Document: 包含查询结果的文档对象
        """
        # 构建结果表格的文本表示
        content = f"查询: {self.sql}\n\n"
        
        if self.error:
            content += f"错误: {self.error}\n"
            return Document(
                text=content,
                metadata={
                    "source": "database_query",
                    "database": self.database_name,
                    "query": self.sql,
                    "error": self.error
                }
            )
        
        # 添加表头
        header = " | ".join(self.column_names)
        separator = "-" * len(header)
        content += f"{header}\n{separator}\n"
        
        # 添加数据行
        for row in self.results:
            row_values = [str(row.get(col, "")) for col in self.column_names]
            content += " | ".join(row_values) + "\n"
        
        if self.truncated:
            content += "\n注意: 结果已被截断，只显示部分数据。\n"
        
        content += f"\n执行时间: {self.execution_time:.2f}秒"
        
        return Document(
            text=content,
            metadata={
                "source": "database_query",
                "database": self.database_name,
                "query": self.sql,
                "execution_time": self.execution_time,
                "row_count": len(self.results),
                "truncated": self.truncated
            }
        )

class EnhancedSQLQueryResult(SQLQueryResult):
    """
    增强的SQL查询结果类
    
    提供更丰富的结果格式化和处理能力
    """
    def __init__(
        self, 
        sql: str, 
        results: List[Dict[str, Any]], 
        column_names: List[str],
        execution_time: float,
        error: Optional[str] = None,
        truncated: bool = False,
        database_name: str = "",
        total_rows: Optional[int] = None,
        page: int = 1,
        page_size: int = 100
    ):
        super().__init__(
            sql=sql,
            results=results,
            column_names=column_names,
            execution_time=execution_time,
            error=error,
            truncated=truncated,
            database_name=database_name
        )
        self.total_rows = total_rows or len(results)
        self.page = page
        self.page_size = page_size
        
    def to_document(self, format_type: str = "text") -> Document:
        """
        将查询结果转换为文档对象，支持多种格式
        
        参数:
            format_type: 格式类型，支持"text"、"markdown"、"json"
            
        返回:
            Document: 包含查询结果的文档对象
        """
        if format_type == "markdown":
            return self._to_markdown_document()
        elif format_type == "json":
            return self._to_json_document()
        else:
            return super().to_document()  # 默认文本格式
            
    def _to_markdown_document(self) -> Document:
        """生成Markdown格式的文档"""
        # 构建结果表格的Markdown表示
        content = f"## 查询\n```sql\n{self.sql}\n```\n\n"
        
        if self.error:
            content += f"### 错误\n{self.error}\n"
            return Document(
                text=content,
                metadata={
                    "source": "database_query",
                    "database": self.database_name,
                    "query": self.sql,
                    "error": self.error,
                    "format": "markdown"
                }
            )
        
        # 添加表头
        content += "### 查询结果\n\n"
        content += "| " + " | ".join(self.column_names) + " |\n"
        content += "| " + " | ".join(["---"] * len(self.column_names)) + " |\n"
        
        # 添加数据行
        for row in self.results:
            row_values = [str(row.get(col, "")) for col in self.column_names]
            content += "| " + " | ".join(row_values) + " |\n"
        
        if self.truncated:
            content += "\n*注意: 结果已被截断，只显示部分数据。*\n"
        
        content += f"\n执行时间: {self.execution_time:.2f}秒"
        
        # 添加分页信息
        if self.total_rows > len(self.results):
            content += f"\n\n当前显示: 第{self.page}页, 共{self.total_rows}行 (每页{self.page_size}行)"
        
        return Document(
            text=content,
            metadata={
                "source": "database_query",
                "database": self.database_name,
                "query": self.sql,
                "execution_time": self.execution_time,
                "row_count": len(self.results),
                "total_rows": self.total_rows,
                "page": self.page,
                "truncated": self.truncated,
                "format": "markdown"
            }
        )
        
    def _to_json_document(self) -> Document:
        """生成JSON格式的文档，便于前端处理"""
        # 构建JSON结构
        result_json = {
            "query": self.sql,
            "database": self.database_name,
            "execution_time": self.execution_time,
            "columns": self.column_names,
            "rows": self.results,
            "total_rows": self.total_rows,
            "page": self.page,
            "page_size": self.page_size,
            "truncated": self.truncated
        }
        
        if self.error:
            result_json["error"] = self.error
            
        # 将JSON转为字符串
        import json
        content = json.dumps(result_json, indent=2, ensure_ascii=False)
        
        return Document(
            text=content,
            metadata={
                "source": "database_query",
                "database": self.database_name,
                "query": self.sql,
                "format": "json",
                "content_type": "application/json"
            }
        )

class SQLQueryTool(BaseTool):
    """
    SQL查询工具类
    
    提供数据库查询功能，支持自然语言转SQL和多数据库智能路由
    两种模式：
    1. 使用内置LLM+模板生成SQL (原始方式)
    2. 使用LlamaIndex的NLSQLTableQueryEngine (增强方式)
    """
    
    def __init__(
        self,
        db_session: Session,
        config: ChatEngineConfig,
        llm: LLM,
        description: str = "通过SQL查询数据库并返回结果",
        use_llama_index: bool = True  # 是否使用LlamaIndex引擎
    ):
        """
        初始化SQL查询工具
        
        参数:
            db_session: 数据库会话对象
            config: 聊天引擎配置
            llm: 语言模型实例
            description: 工具描述
            use_llama_index: 是否使用LlamaIndex的NLSQLTableQueryEngine
        """
        self.db_session = db_session
        self.config = config
        self.llm = llm
        self.cache = {}  # 简单的表结构缓存
        self.connectors: Dict[int, BaseConnector] = {}  # 连接器缓存
        self.llama_index_engines: Dict[int, NLSQLTableQueryEngine] = {}  # LlamaIndex引擎缓存
        self.sqlalchemy_engines: Dict[int, Tuple[Any, str]] = {}  # SQLAlchemy引擎缓存 (engine, url)
        self.use_llama_index = use_llama_index
        
        super().__init__(name="sql_query", description=description)
    
    def _get_connector(self, connection: DatabaseConnection) -> BaseConnector:
        """
        获取或创建数据库连接器
        
        参数:
            connection: 数据库连接对象
            
        返回:
            BaseConnector: 数据库连接器
        """
        if connection.id in self.connectors:
            return self.connectors[connection.id]
        
        # 创建新的连接器
        connector = get_connector(connection)
        self.connectors[connection.id] = connector
        return connector
    
    def _get_sqlalchemy_engine(self, connection: DatabaseConnection) -> Tuple[Any, str]:
        """
        获取或创建SQLAlchemy引擎
        为LlamaIndex的SQLDatabase提供支持
        
        参数:
            connection: 数据库连接对象
            
        返回:
            Tuple[Engine, str]: SQLAlchemy引擎和连接URL
        """
        if connection.id in self.sqlalchemy_engines:
            return self.sqlalchemy_engines[connection.id]
        
        # 根据数据库类型创建引擎
        if connection.database_type == "mysql":
            from app.parameters.database_connection import MySQLParameters
            config = connection.config
            params = MySQLParameters.from_dict(config)
            url = params.get_connection_string()
            engine = create_engine(url)
            self.sqlalchemy_engines[connection.id] = (engine, url)
            return engine, url
        elif connection.database_type == "postgresql":
            from app.parameters.database_connection import PostgreSQLParameters
            config = connection.config
            params = PostgreSQLParameters.from_dict(config)
            url = params.get_connection_string()
            engine = create_engine(url)
            self.sqlalchemy_engines[connection.id] = (engine, url)
            return engine, url
        elif connection.database_type == "sqlite":
            from app.parameters.database_connection import SQLiteParameters
            config = connection.config
            params = SQLiteParameters.from_dict(config)
            url = params.get_connection_string()
            engine = create_engine(url, connect_args={"check_same_thread": False})
            self.sqlalchemy_engines[connection.id] = (engine, url)
            return engine, url
        else:
            # 对于不支持的类型，使用原始连接器
            logger.warning(f"Database type {connection.database_type} is not directly supported by LlamaIndex. Using default mode.")
            return None, ""
    
    def _build_table_info(self, connection: DatabaseConnection, db_config: LinkedDatabaseConfig) -> Dict[str, Any]:
        """
        构建增强的表信息结构，优化描述信息的注入逻辑
        
        参数:
            connection: 数据库连接对象
            db_config: 数据库配置对象
            
        返回:
            Dict[str, Any]: 包含表信息的字典
        """
        connector = self._get_connector(connection)
        
        # 获取表列表（支持表白名单过滤）
        all_tables = connector.get_tables()
        allowed_tables = db_config.allowed_tables or all_tables
        
        # 应用表过滤规则
        if db_config.allowed_tables:
            # 只使用白名单中的表
            tables = [t for t in all_tables if t in allowed_tables]
        elif db_config.forbidden_tables:
            # 排除黑名单中的表
            tables = [t for t in all_tables if t not in db_config.forbidden_tables]
        else:
            tables = all_tables
        
        # 构建增强的表信息
        table_info = {}
        for table_name in tables:
            columns = connector.get_table_columns(table_name)
            
            # 获取表描述，如果没有则尝试自动生成一个简单描述
            table_desc = connection.table_descriptions.get(table_name, "")
            if not table_desc:
                # 简单的表描述推断
                table_desc = f"Table containing {table_name} data"
            
            # 过滤敏感列
            filtered_columns = []
            for column in columns:
                col_name = column["name"]
                
                # 检查列是否在黑名单中
                col_key = f"{table_name}.{col_name}"
                if db_config.forbidden_columns and col_key in db_config.forbidden_columns:
                    continue
                    
                # 检查是否是敏感列
                is_sensitive = self._is_sensitive_column(col_name, db_config)
                if is_sensitive and db_config.mask_sensitive_data:
                    # 标记为敏感列，但仍然包含它以保持schema完整性
                    column["is_sensitive"] = True
                
                # 获取列描述
                col_desc = connection.column_descriptions.get(table_name, {}).get(col_name, "")
                if col_desc:
                    column["description"] = col_desc
                    
                filtered_columns.append(column)
            
            # 保存表信息，包含更丰富的元数据
            table_info[table_name] = {
                "description": table_desc,
                "columns": filtered_columns,
                "sample_data": self._get_sample_data(connection, table_name, db_config),
                "primary_keys": self._get_primary_keys(connection, table_name)
            }
        
        return table_info

    def _is_sensitive_column(self, column_name: str, db_config: LinkedDatabaseConfig) -> bool:
        """判断列是否敏感"""
        # 使用配置中的敏感列模式
        patterns = (db_config.sensitive_column_patterns_override or 
                    self.config.database.sensitive_column_patterns)
        
        for pattern in patterns:
            if pattern.lower() in column_name.lower():
                return True
        return False

    def _get_sample_data(self, connection: DatabaseConnection, table_name: str, db_config: LinkedDatabaseConfig, limit: int = 3) -> List[Dict]:
        """获取表的示例数据，用于增强理解"""
        connector = self._get_connector(connection)
        sample_query = f"SELECT * FROM {table_name} LIMIT {limit}"
        try:
            results, _ = connector.execute_query(sample_query, {"timeout": 5})
            return results
        except Exception as e:
            logger.warning(f"获取{table_name}示例数据失败: {str(e)}")
            return []
        
    def _get_primary_keys(self, connection: DatabaseConnection, table_name: str) -> List[str]:
        """获取表的主键信息"""
        try:
            # 通过SQLAlchemy获取主键信息
            engine, _ = self._get_sqlalchemy_engine(connection)
            if not engine:
                return []
            
            inspector = inspect(engine)
            pk_constraint = inspector.get_pk_constraint(table_name)
            return pk_constraint.get('constrained_columns', [])
        except Exception as e:
            logger.warning(f"获取{table_name}主键信息失败: {str(e)}")
            return []
    
    def _get_llama_index_engine(self, connection: DatabaseConnection, db_config: LinkedDatabaseConfig) -> Optional[NLSQLTableQueryEngine]:
        """
        获取增强的LlamaIndex NLSQLTableQueryEngine
        
        参数:
            connection: 数据库连接对象
            db_config: 数据库配置对象
            
        返回:
            NLSQLTableQueryEngine: LlamaIndex查询引擎
        """
        if connection.id in self.llama_index_engines:
            return self.llama_index_engines[connection.id]
        
        # 获取SQLAlchemy引擎
        engine, url = self._get_sqlalchemy_engine(connection)
        if engine is None:
            logger.warning(f"无法为数据库 {connection.name} 创建SQLAlchemy引擎，将使用默认模式")
            return None
        
        try:
            # 构建增强的表信息
            table_info_dict = self._build_table_info(connection, db_config)
            
            # 获取表关系信息
            table_relationships = self._get_table_relationships(connection)
            
            # 获取业务描述
            business_desc = db_config.business_description_override or connection.description_for_llm or ""
            
            # 增强的业务上下文
            enhanced_context = {
                "database_type": connection.database_type,
                "business_description": business_desc,
                "table_count": len(table_info_dict),
                "relationships": table_relationships
            }
            
            # 创建SQLDatabase，注入表信息和采样数据
            sql_database = SQLDatabase(
                engine=engine,
                include_tables=list(table_info_dict.keys()),
                sample_rows_in_table_info=3
            )
            
            # 创建增强的提示词模板
            from llama_index.core.prompts import PromptTemplate
            
            text_to_sql_prompt = None
            if hasattr(self.config.llm, 'text_to_sql_prompt') and self.config.llm.text_to_sql_prompt:
                # 增强提示词模板，注入表关系信息和业务上下文
                enhanced_template = self.config.llm.text_to_sql_prompt
                
                # 替换特殊标记，注入更多信息
                if "{business_context}" in enhanced_template:
                    enhanced_template = enhanced_template.replace(
                        "{business_context}", 
                        f"业务背景：{business_desc}\n表关系：{self._format_relationships(table_relationships)}"
                    )
                    
                text_to_sql_prompt = PromptTemplate(enhanced_template)
            
            response_synthesis_prompt = None
            if hasattr(self.config.llm, 'response_synthesis_prompt') and self.config.llm.response_synthesis_prompt:
                response_synthesis_prompt = PromptTemplate(self.config.llm.response_synthesis_prompt)
            
            # 创建增强的NLSQLTableQueryEngine
            query_engine = NLSQLTableQueryEngine(
                sql_database=sql_database,
                tables=list(table_info_dict.keys()),
                llm=self.llm,
                text_to_sql_prompt=text_to_sql_prompt,
                response_synthesis_prompt=response_synthesis_prompt,
                synthesize_response=True,
                context=enhanced_context  # 注入额外上下文
            )
            
            # 缓存引擎
            self.llama_index_engines[connection.id] = query_engine
            return query_engine
        except Exception as e:
            logger.error(f"创建LlamaIndex查询引擎失败: {str(e)}")
            return None

    def _get_table_relationships(self, connection: DatabaseConnection) -> List[Dict]:
        """获取表之间的关系信息（外键）"""
        try:
            # 获取SQLAlchemy引擎
            engine, _ = self._get_sqlalchemy_engine(connection)
            if not engine:
                return []
            
            inspector = inspect(engine)
            relationships = []
            
            # 获取所有表
            tables = inspector.get_table_names()
            
            # 遍历所有表，获取外键关系
            for table in tables:
                fks = inspector.get_foreign_keys(table)
                for fk in fks:
                    relationships.append({
                        "from_table": table,
                        "from_columns": fk.get("constrained_columns", []),
                        "to_table": fk.get("referred_table", ""),
                        "to_columns": fk.get("referred_columns", [])
                    })
            
            return relationships
        except Exception as e:
            logger.warning(f"获取表关系信息失败: {str(e)}")
            return []
        
    def _format_relationships(self, relationships: List[Dict]) -> str:
        """格式化表关系信息为文本描述"""
        if not relationships:
            return "无表关系信息"
        
        result = []
        for rel in relationships:
            from_cols = ", ".join(rel["from_columns"])
            to_cols = ", ".join(rel["to_columns"])
            result.append(
                f"{rel['from_table']}({from_cols}) 关联到 {rel['to_table']}({to_cols})"
            )
        
        return "\n".join(result)
    
    def _get_table_schema(self, connection: DatabaseConnection, db_config: LinkedDatabaseConfig) -> str:
        """
        获取数据库表结构描述
        
        参数:
            connection: 数据库连接对象
            db_config: 数据库配置对象
            
        返回:
            str: 表结构描述文本
        """
        cache_key = f"schema_{connection.id}"
        cache_ttl = self.config.database.table_schema_cache_ttl
        
        # 检查缓存
        if cache_key in self.cache and cache_ttl > 0:
            cache_time, schema = self.cache[cache_key]
            if time.time() - cache_time < cache_ttl:
                return schema
        
        # 获取连接器
        connector = self._get_connector(connection)
        
        # 获取表结构
        tables = connector.get_tables()
        
        # 构建表结构描述
        schema_text = f"数据库类型: {connection.database_type}\n"
        
        # 添加业务描述（优先使用配置中的覆盖描述）
        business_desc = db_config.business_description_override or connection.description_for_llm or ""
        if business_desc:
            schema_text += f"业务描述: {business_desc}\n\n"
        
        # 添加表描述
        schema_text += "数据库表结构:\n\n"
        
        for table_name in tables:
            table_columns = connector.get_table_columns(table_name)
            
            # 添加表描述
            table_desc = connection.table_descriptions.get(table_name, "")
            schema_text += f"表名: {table_name}"
            if table_desc:
                schema_text += f"\n表描述: {table_desc}"
            schema_text += "\n列:\n"
            
            # 添加列信息
            for column in table_columns:
                col_name = column["name"]
                col_type = column["type"]
                col_desc = connection.column_descriptions.get(table_name, {}).get(col_name, "")
                
                schema_text += f"- {col_name} ({col_type})"
                if col_desc:
                    schema_text += f": {col_desc}"
                schema_text += "\n"
            
            schema_text += "\n"
        
        # 更新缓存
        if cache_ttl > 0:
            self.cache[cache_key] = (time.time(), schema_text)
        
        return schema_text
    
    def _generate_sql(self, question: str, db_schema: str) -> str:
        """
        使用LLM生成SQL查询
        
        参数:
            question: 用户问题
            db_schema: 数据库结构描述
            
        返回:
            str: 生成的SQL查询语句
        """
        # 使用配置中的SQL提示词模板
        prompt_template = self.config.llm.text_to_sql_prompt
        
        # 替换模板变量（适配现有变量名）
        prompt = prompt_template.replace("{schema}", db_schema)
        prompt = prompt.replace("{query_str}", question)
        prompt = prompt.replace("{dialect}", self.connection_config.database_type if hasattr(self, 'connection_config') else "sql")
        
        # 使用LLM生成SQL
        sql = self.llm.complete(prompt).text.strip()
        
        # 去除可能包含的```sql和```标记
        sql = sql.replace("```sql", "").replace("```", "").strip()
        
        return sql
    
    def _execute_sql(
        self, 
        connection: DatabaseConnection, 
        db_config: LinkedDatabaseConfig,
        sql: str,
        page: int = 1,
        page_size: int = 100
    ) -> EnhancedSQLQueryResult:
        """
        执行SQL查询，支持分页
        
        参数:
            connection: 数据库连接对象
            db_config: 数据库配置对象
            sql: SQL查询语句
            page: 页码（从1开始）
            page_size: 每页行数
            
        返回:
            EnhancedSQLQueryResult: 查询结果对象
        """
        # 获取连接器
        connector = self._get_connector(connection)
        
        # 检查只读模式
        read_only = db_config.read_only if db_config.read_only is not None else self.config.database.read_only
        if read_only and not sql.strip().lower().startswith("select"):
            return EnhancedSQLQueryResult(
                sql=sql,
                results=[],
                column_names=[],
                execution_time=0,
                error="只读模式下只允许SELECT查询",
                database_name=connection.name
            )
        
        # 执行查询
        start_time = time.time()
        
        try:
            # 处理分页
            # 注意：这里使用简单方法，实际应用中可能需要根据数据库类型优化
            is_select = sql.strip().lower().startswith("select")
            count_sql = None
            paginated_sql = sql
            
            if is_select and page_size > 0:
                # 构建计数SQL（用于获取总行数）
                count_sql = f"SELECT COUNT(*) as total_count FROM ({sql}) as count_query"
                
                # 构建分页SQL
                offset = (page - 1) * page_size
                
                # 根据数据库类型构建分页SQL
                if connection.database_type in ("mysql", "postgresql", "sqlite"):
                    paginated_sql = f"{sql} LIMIT {page_size} OFFSET {offset}"
                elif connection.database_type == "sqlserver":
                    # SQL Server分页语法（需要ORDER BY子句）
                    if " order by " not in sql.lower():
                        # 添加一个默认排序（实际应用中应当确保原始SQL有ORDER BY）
                        paginated_sql = f"{sql} ORDER BY (SELECT NULL) OFFSET {offset} ROWS FETCH NEXT {page_size} ROWS ONLY"
                    else:
                        paginated_sql = f"{sql} OFFSET {offset} ROWS FETCH NEXT {page_size} ROWS ONLY"
            
            # 获取总行数（如果需要）
            total_rows = None
            if count_sql:
                count_result, count_error = connector.execute_query(
                    count_sql, 
                    params={"timeout": self.config.database.query_timeout}
                )
                if not count_error and count_result and len(count_result) > 0:
                    total_rows = count_result[0].get("total_count", 0)
            
            # 执行分页查询
            result_tuple = connector.execute_query(
                paginated_sql, 
                params={
                    "timeout": self.config.database.query_timeout,
                    "max_rows": page_size
                }
            )
            
            # 解包结果
            if isinstance(result_tuple, tuple) and len(result_tuple) == 2:
                rows, error = result_tuple
                if error:
                    raise Exception(error)
                    
                # 获取列名
                if rows and isinstance(rows[0], dict):
                    columns = list(rows[0].keys())
                else:
                    columns = []
                    
                result = {"rows": rows, "columns": columns}
            else:
                # 如果不是元组，假设它已经是结构化的结果
                result = result_tuple
            
            execution_time = time.time() - start_time
            
            # 创建增强的查询结果
            return EnhancedSQLQueryResult(
                sql=sql,
                results=result["rows"],
                column_names=result["columns"],
                execution_time=execution_time,
                truncated=False,  # 使用分页后不再需要截断
                database_name=connection.name,
                total_rows=total_rows,
                page=page,
                page_size=page_size
            )
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"SQL执行错误: {str(e)}, SQL: {sql}")
            return EnhancedSQLQueryResult(
                sql=sql,
                results=[],
                column_names=[],
                execution_time=execution_time,
                error=str(e),
                database_name=connection.name
            )
    
    def _query_with_llama_index(
        self, 
        question: str, 
        connection: DatabaseConnection, 
        db_config: LinkedDatabaseConfig
    ) -> Document:
        """
        使用LlamaIndex的NLSQLTableQueryEngine执行查询
        
        参数:
            question: 用户问题
            connection: 数据库连接对象
            db_config: 数据库配置对象
            
        返回:
            Document: 包含查询结果的文档对象
        """
        start_time = time.time()
        
        try:
            # 获取或创建LlamaIndex引擎
            engine = self._get_llama_index_engine(connection, db_config)
            if engine is None:
                # 如果引擎创建失败，回退到默认模式
                logger.warning(f"LlamaIndex引擎不可用，回退到传统SQL生成模式")
                return self._query_with_traditional_method(question, connection, db_config)
            
            # 执行查询
            response = engine.query(question)
            
            # 提取SQL和结果
            # LlamaIndex响应可能包含SQL和结果信息
            sql = ""
            result_text = ""
            
            # 尝试从响应中提取SQL
            if hasattr(response, 'metadata') and response.metadata:
                if 'sql_query' in response.metadata:
                    sql = response.metadata['sql_query']
                    
            # 如果响应是字符串，直接使用
            response_text = str(response)
            
            # 计算执行时间
            execution_time = time.time() - start_time
            
            # 创建一个包含响应的Document对象
            return Document(
                text=f"查询: {sql}\n\n{response_text}\n\n执行时间: {execution_time:.2f}秒",
                metadata={
                    "source": "database_query",
                    "database": connection.name,
                    "query": sql,
                    "execution_time": execution_time,
                    "engine": "llama_index"
                }
            )
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"LlamaIndex查询错误: {str(e)}")
            
            # 创建错误文档
            return Document(
                text=f"查询数据库时出错: {str(e)}",
                metadata={
                    "source": "database_query",
                    "database": connection.name,
                    "error": str(e),
                    "execution_time": execution_time,
                    "engine": "llama_index"
                }
            )
    
    def _query_with_traditional_method(self, question: str, connection: DatabaseConnection, db_config: LinkedDatabaseConfig) -> Document:
        """
        使用传统方法（自定义LLM+模板生成SQL）执行查询
        
        参数:
            question: 用户问题
            connection: 数据库连接对象
            db_config: 数据库配置对象
            
        返回:
            Document: 包含查询结果的文档对象
        """
        # 获取表结构描述
        db_schema = self._get_table_schema(connection, db_config)
        
        # 生成SQL
        sql = self._generate_sql(question, db_schema)
        
        # 执行SQL
        result = self._execute_sql(connection, db_config, sql)
        
        # 转换为文档
        return result.to_document()
    
    def _select_database(self, question: str, connections: List[DatabaseConnection]) -> Tuple[DatabaseConnection, LinkedDatabaseConfig]:
        """
        选择最适合回答问题的数据库
        
        参数:
            question: 用户问题
            connections: 可用的数据库连接列表
            
        返回:
            Tuple[DatabaseConnection, LinkedDatabaseConfig]: 选中的数据库连接和配置
        """
        # 如果只有一个数据库连接，直接返回
        if len(connections) == 1:
            connection = connections[0]
            db_config = self.config.get_database_connection_config(connection.id)
            return connection, db_config
        
        # 如果设置了自动选择数据库
        if self.config.database.auto_select_database:
            # TODO: 实现更智能的数据库选择逻辑，可以使用LLM进行选择
            # 当前简单使用第一个按优先级排序的连接
            connection = connections[0]
            db_config = self.config.get_database_connection_config(connection.id)
            return connection, db_config
        
        # 默认使用第一个连接
        connection = connections[0]
        db_config = self.config.get_database_connection_config(connection.id)
        return connection, db_config
    
    def _build_router_query_engine(self, question: str, connections: List[DatabaseConnection]) -> RouterQueryEngine:
        """
        构建数据库路由查询引擎
        
        使用LlamaIndex的Router组件，根据问题选择最合适的数据库
        """
        # 初始化查询引擎和描述的字典
        query_engines = {}
        descriptions = {}
        
        # 为每个数据库连接创建查询引擎
        for connection in connections:
            db_config = self.config.get_database_connection_config(connection.id)
            
            # 获取或创建LlamaIndex引擎
            engine = self._get_llama_index_engine(connection, db_config)
            if engine is None:
                continue
            
            # 使用连接名作为键
            key = connection.name
            query_engines[key] = engine
            
            # 构建数据库描述
            business_desc = db_config.business_description_override or connection.description_for_llm or ""
            descriptions[key] = f"数据库: {connection.name}\n类型: {connection.database_type}\n描述: {business_desc}\n表: {', '.join(self._get_connector(connection).get_tables())}"
        
        # 创建选择器和路由引擎
        selector = LLMSingleSelector.from_defaults(self.llm)
        router = RouterQueryEngine(
            selector=selector,
            query_engines=query_engines,
            descriptions=descriptions,
            select_by="查询内容确定应该使用哪个数据库回答问题。根据问题内容和表结构选择最合适的单个数据库。"
        )
        
        return router
    
    def __call__(self, input_text: str, page: int = 1, page_size: int = 100, format_type: str = "text") -> Union[str, List[NodeWithScore]]:
        """
        处理用户查询并返回结果，支持分页和格式化
        
        参数:
            input_text: 用户查询文本
            page: 页码（从1开始）
            page_size: 每页行数
            format_type: 结果格式类型 ("text", "markdown", "json")
            
        返回:
            Union[str, List[NodeWithScore]]: 查询结果
        """
        # 检查数据库功能是否启用
        if not self.config.database.enabled:
            return "数据库查询功能未启用"
        
        # 获取关联的数据库连接
        connections = self.config.get_linked_database_connections(self.db_session)
        if not connections:
            return "未配置数据库连接"
        
        # 选择合适的数据库
        connection, db_config = self._select_database(input_text, connections)
        
        # 如果开启了智能路由且有多个数据库连接
        if self.config.database.auto_select_database and len(connections) > 1:
            router = self._build_router_query_engine(input_text, connections)
            try:
                response = router.query(input_text)
                # 转换为Document格式
                doc = Document(
                    text=str(response),
                    metadata={
                        "source": "database_query",
                        "engine": "router"
                    }
                )
                return [NodeWithScore(node=doc, score=1.0)]
            except Exception as e:
                logger.error(f"路由查询引擎错误: {str(e)}")
                # 出错时回退到传统方式
                if self.use_llama_index and connection.database_type in ("mysql", "postgresql", "sqlite"):
                    doc = self._query_with_llama_index(input_text, connection, db_config)
                else:
                    doc = self._query_with_traditional_method(input_text, connection, db_config)
                return [NodeWithScore(node=doc, score=1.0)]
        else:
            # 执行查询（使用LlamaIndex或传统方法）
            if self.use_llama_index and connection.database_type in ("mysql", "postgresql", "sqlite"):
                doc = self._query_with_llama_index(input_text, connection, db_config)
            else:
                # 使用增强的传统方法（支持分页和格式化）
                sql = self._generate_sql(input_text, self._get_table_schema(connection, db_config))
                result = self._execute_sql(connection, db_config, sql, page, page_size)
                doc = result.to_document(format_type=format_type)
            
            # 返回结果
            return [NodeWithScore(node=doc, score=1.0)] 