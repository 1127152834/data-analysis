from typing import Dict, List, Optional, Any, Literal
from pydantic import BaseModel, Field
import logging
import asyncio
import json

from ..tools.base import BaseTool, ToolParameters, ToolResult

class DatabaseQueryParameters(ToolParameters):
    """数据库查询工具参数"""
    query: str
    database_id: Optional[str] = None
    context: Optional[str] = None
    # 新增：查询模式选项
    query_mode: Optional[Literal["regular", "auto_vector", "router"]] = "regular"
    # 新增：向量查询相关参数
    vector_search: Optional[bool] = False
    
class DatabaseQueryResult(ToolResult):
    """数据库查询工具结果"""
    context: str = ""
    data: Any = None
    sql: Optional[str] = None
    
class DatabaseQueryTool(BaseTool[DatabaseQueryParameters, DatabaseQueryResult]):
    """数据库查询工具，用于执行SQL查询"""
    
    def __init__(self, db_session=None, engine_config=None):
        super().__init__(
            name="database_query_tool",
            description="查询数据库并返回结果。能够结合结构化数据(SQL)和非结构化数据(向量搜索)来回答复杂问题。",
            parameter_type=DatabaseQueryParameters,
            result_type=DatabaseQueryResult
        )
        self.db_session = db_session
        self.engine_config = engine_config
        self._vector_indices = {}  # 缓存向量索引
        self._query_engines = {}   # 缓存查询引擎
        
    async def execute(self, parameters: DatabaseQueryParameters) -> DatabaseQueryResult:
        """执行数据库查询"""
        self.logger.info(f"执行数据库查询: {parameters.query[:50]}... 模式: {parameters.query_mode}")
        
        try:
            # 检查数据库查询是否启用
            if not self.engine_config or not hasattr(self.engine_config, "db_query") or not self.engine_config.db_query.enabled:
                self.logger.info("数据库查询未启用")
                return DatabaseQueryResult(
                    success=True,
                    context="数据库查询功能未启用，无法执行数据库查询。",
                    data=None
                )
            
            # 根据查询模式选择不同的执行方法
            if parameters.query_mode == "auto_vector":
                return await self._execute_auto_vector_query(parameters)
            elif parameters.query_mode == "router":
                return await self._execute_router_query(parameters)
            else:
                # 默认使用常规SQL查询
                return await self._execute_regular_query(parameters)
            
        except Exception as e:
            self.logger.error(f"数据库查询出错: {str(e)}", exc_info=True)
            return DatabaseQueryResult(
                success=False,
                error_message=f"数据库查询出错: {str(e)}"
            )
    
    async def _execute_regular_query(self, parameters: DatabaseQueryParameters) -> DatabaseQueryResult:
        """执行常规SQL查询"""
        # 导入必要的模块
        from app.rag.sql.sql_executor import SQLExecutor
        from app.rag.types import SQLExecutionConfig
        
        # 获取LLM
        llm = self.engine_config.get_llama_llm(self.db_session)
        
        # 创建SQL执行器
        config = SQLExecutionConfig(
            llm=self.engine_config.llm.llm,
            max_tokens=self.engine_config.db_query.max_tokens,
            temperature=self.engine_config.db_query.temperature,
            top_p=self.engine_config.db_query.top_p,
            model_name=self.engine_config.db_query.model_name,
            debug=self.engine_config.db_query.debug
        )
        
        executor = SQLExecutor(
            db_session=self.db_session,
            config=config,
            llm=llm
        )
        
        # 执行查询
        if parameters.database_id:
            # 使用指定的数据库执行查询
            result = await self._run_async(
                executor.execute_with_database_id,
                parameters.query,
                parameters.database_id,
                parameters.context
            )
        else:
            # 使用默认数据库执行查询
            result = await self._run_async(
                executor.execute,
                parameters.query,
                parameters.context
            )
        
        # 创建上下文
        context = ""
        if result and result.execution_result:
            # 添加SQL查询语句
            if result.sql:
                context += f"执行的SQL查询：\n```sql\n{result.sql}\n```\n\n"
            
            # 添加查询结果
            execution_result = result.execution_result
            if isinstance(execution_result, str):
                # 尝试解析JSON结果
                try:
                    data = json.loads(execution_result)
                    if isinstance(data, list) and len(data) > 0:
                        context += "查询结果：\n"
                        # 表格形式呈现结果
                        if len(data) <= 10:
                            context += self._format_table(data)
                        else:
                            context += self._format_table(data[:10])
                            context += f"\n（结果过多，只显示前10条，共{len(data)}条记录）\n"
                    else:
                        context += f"查询结果：\n{execution_result}\n"
                except:
                    context += f"查询结果：\n{execution_result}\n"
            else:
                context += f"查询结果：\n{str(execution_result)}\n"
            
            # 添加执行消息
            if result.message:
                context += f"\n{result.message}\n"
        
        # 返回结果
        return DatabaseQueryResult(
            success=True if result and result.success else False,
            context=context,
            data=result.execution_result if result else None,
            sql=result.sql if result else None,
            error_message=None if (result and result.success) else (result.message if result else "查询执行失败")
        )
    
    async def _execute_auto_vector_query(self, parameters: DatabaseQueryParameters) -> DatabaseQueryResult:
        """执行SQL与向量混合查询"""
        try:
            # 导入需要的LlamaIndex组件
            from llama_index.core import VectorStoreIndex
            from llama_index.core.schema import MetadataInfo, Document
            from llama_index.core.query_engine import SQLAutoVectorQueryEngine
            from llama_index.core.vector_stores import VectorStoreInfo
            from llama_index.core.indices.struct_store import SQLStructStoreIndex
            from llama_index.core.objects import SQLTableSchema, ObjectIndex
            from llama_index.core.objects import SQLTableNodeMapping
            from llama_index.core import SQLDatabase
            
            # 获取数据库连接
            db_connection = None
            if parameters.database_id:
                # 根据ID获取数据库连接
                from app.repositories import database_connection_repo
                db_connection = database_connection_repo.get_by_id(self.db_session, parameters.database_id)
                if not db_connection:
                    return DatabaseQueryResult(
                        success=False,
                        error_message=f"找不到ID为{parameters.database_id}的数据库连接"
                    )
            else:
                # 获取默认数据库连接
                from app.repositories import database_connection_repo
                default_connections = database_connection_repo.get_default_connections(self.db_session)
                if default_connections:
                    db_connection = default_connections[0]
                else:
                    return DatabaseQueryResult(
                        success=False,
                        error_message="未找到默认数据库连接"
                    )
            
            # 从连接字符串创建SQLDatabase
            from sqlalchemy import create_engine
            engine = create_engine(db_connection.connection_string)
            sql_database = SQLDatabase(engine)
            
            # 获取或创建向量索引
            vector_index_key = f"vector_index_{db_connection.id}"
            vector_index = self._vector_indices.get(vector_index_key)
            
            if not vector_index:
                # 获取与数据库相关的知识文档
                from app.rag.retrievers.chunk.fusion_retriever import ChunkFusionRetriever
                from app.rag.retrievers.chunk.schema import ChunkRetrieverConfig
                
                # 通过向量检索获取与数据库相关的文档
                retriever = ChunkFusionRetriever(
                    db_session=self.db_session,
                    knowledge_base_ids=[int(db_connection.id)],
                    config=ChunkRetrieverConfig(top_k=10)
                )
                
                docs = await self._run_async(
                    retriever.retrieve,
                    parameters.query
                )
                
                # 为文档添加元数据
                processed_docs = []
                for doc in docs:
                    doc_obj = Document(
                        text=doc.content,
                        metadata={
                            "source": doc.source,
                            "table_name": doc.metadata.get("table_name", ""),
                            "database_id": db_connection.id
                        }
                    )
                    processed_docs.append(doc_obj)
                
                # 创建向量索引
                from app.rag.llms.resolver import get_default_embedding
                vector_index = VectorStoreIndex.from_documents(
                    processed_docs,
                    embed_model=get_default_embedding()
                )
                self._vector_indices[vector_index_key] = vector_index
            
            # 获取数据库表信息
            tables = sql_database.get_usable_table_names()
            
            # 创建VectorStoreInfo
            vector_store_info = VectorStoreInfo(
                content_info="关于数据库中表和列的语义信息、业务含义和用途",
                metadata_info=[
                    MetadataInfo(
                        name="source",
                        type="str",
                        description="文档来源"
                    ),
                    MetadataInfo(
                        name="table_name",
                        type="str",
                        description="相关表名"
                    ),
                    MetadataInfo(
                        name="database_id",
                        type="str",
                        description="数据库ID"
                    )
                ]
            )
            
            # 选择主要表名（如果有多个表）
            main_table = tables[0] if tables else None
            
            # 创建SQLAutoVectorQueryEngine
            llm = self.engine_config.get_llama_llm(self.db_session)
            query_engine = SQLAutoVectorQueryEngine.from_args(
                sql_database=sql_database,
                vector_index=vector_index,
                table_name=main_table,
                vector_store_info=vector_store_info,
                llm=llm
            )
            
            # 执行查询
            response = await self._run_async(
                query_engine.query,
                parameters.query
            )
            
            # 提取执行的SQL（如果有）
            sql_queries = []
            source_nodes = getattr(response, 'source_nodes', [])
            for node in source_nodes:
                if hasattr(node, 'metadata') and 'sql_query' in node.metadata:
                    sql_queries.append(node.metadata['sql_query'])
            
            sql_text = "\n".join(sql_queries) if sql_queries else None
            
            # 构建结果
            context = ""
            if sql_text:
                context += f"执行的SQL查询：\n```sql\n{sql_text}\n```\n\n"
            
            context += f"查询结果：\n{response.response}\n"
            
            return DatabaseQueryResult(
                success=True,
                context=context,
                data=response.response,
                sql=sql_text
            )
            
        except Exception as e:
            self.logger.error(f"执行SQL自动向量查询出错: {str(e)}", exc_info=True)
            return DatabaseQueryResult(
                success=False,
                error_message=f"执行SQL自动向量查询出错: {str(e)}"
            )
    
    async def _execute_router_query(self, parameters: DatabaseQueryParameters) -> DatabaseQueryResult:
        """执行SQL路由查询（自动选择SQL或向量查询）"""
        try:
            # 导入需要的LlamaIndex组件
            from llama_index.core import VectorStoreIndex
            from llama_index.core.tools import QueryEngineTool
            from llama_index.core.query_engine import RouterQueryEngine
            from llama_index.core.selectors import LLMSingleSelector
            from llama_index.core import SQLDatabase
            from llama_index.core.query_engine import NLSQLTableQueryEngine
            
            # 获取数据库连接
            db_connection = None
            if parameters.database_id:
                from app.repositories import database_connection_repo
                db_connection = database_connection_repo.get_by_id(self.db_session, parameters.database_id)
                if not db_connection:
                    return DatabaseQueryResult(
                        success=False,
                        error_message=f"找不到ID为{parameters.database_id}的数据库连接"
                    )
            else:
                from app.repositories import database_connection_repo
                default_connections = database_connection_repo.get_default_connections(self.db_session)
                if default_connections:
                    db_connection = default_connections[0]
                else:
                    return DatabaseQueryResult(
                        success=False,
                        error_message="未找到默认数据库连接"
                    )
            
            # 构建查询引擎缓存键
            engine_key = f"router_engine_{db_connection.id}"
            query_engine = self._query_engines.get(engine_key)
            
            if not query_engine:
                # 从连接字符串创建SQLDatabase
                from sqlalchemy import create_engine
                engine = create_engine(db_connection.connection_string)
                sql_database = SQLDatabase(engine)
                
                # 获取表信息并构建表的描述
                tables = sql_database.get_usable_table_names()
                table_descriptions = {}
                
                for table in tables:
                    # 获取表结构
                    table_info = sql_database.get_table_info(table)
                    table_descriptions[table] = f"表'{table}'包含以下字段：{table_info}"
                
                # 创建SQL查询引擎
                llm = self.engine_config.get_llama_llm(self.db_session)
                sql_query_engines = {}
                
                for table in tables:
                    engine = NLSQLTableQueryEngine(
                        sql_database=sql_database,
                        tables=[table],
                        llm=llm
                    )
                    sql_query_engines[table] = engine
                
                # 创建向量查询引擎
                # 获取与数据库相关的知识文档
                from app.rag.retrievers.chunk.fusion_retriever import ChunkFusionRetriever
                from app.rag.retrievers.chunk.schema import ChunkRetrieverConfig
                
                # 通过向量检索获取与数据库相关的文档
                retriever = ChunkFusionRetriever(
                    db_session=self.db_session,
                    knowledge_base_ids=[int(db_connection.id)],
                    config=ChunkRetrieverConfig(top_k=10)
                )
                
                docs = await self._run_async(
                    retriever.retrieve,
                    parameters.query
                )
                
                # 为文档添加元数据
                from llama_index.core.schema import Document
                processed_docs = []
                for doc in docs:
                    doc_obj = Document(
                        text=doc.content,
                        metadata={
                            "source": doc.source,
                            "table_name": doc.metadata.get("table_name", ""),
                            "database_id": db_connection.id
                        }
                    )
                    processed_docs.append(doc_obj)
                
                # 创建向量索引
                from app.rag.llms.resolver import get_default_embedding
                vector_index = VectorStoreIndex.from_documents(
                    processed_docs,
                    embed_model=get_default_embedding()
                )
                vector_query_engine = vector_index.as_query_engine()
                
                # 将所有查询引擎封装为工具
                query_engine_tools = []
                
                # 添加SQL工具
                for table, engine in sql_query_engines.items():
                    description = f"用于将自然语言查询转换为对'{table}'表的SQL查询。{table_descriptions.get(table, '')}"
                    tool = QueryEngineTool.from_defaults(
                        query_engine=engine,
                        description=description,
                        name=f"sql_{table}"
                    )
                    query_engine_tools.append(tool)
                
                # 添加向量工具
                vector_tool = QueryEngineTool.from_defaults(
                    query_engine=vector_query_engine,
                    description=f"用于回答关于数据库及其表结构的语义问题，提供表和列的业务含义、使用场景等信息",
                    name="vector_semantic"
                )
                query_engine_tools.append(vector_tool)
                
                # 创建LLM选择器
                selector = LLMSingleSelector.from_defaults(llm=llm)
                
                # 创建RouterQueryEngine
                query_engine = RouterQueryEngine(
                    selector=selector,
                    query_engine_tools=query_engine_tools
                )
                
                # 缓存查询引擎
                self._query_engines[engine_key] = query_engine
            
            # 执行查询
            response = await self._run_async(
                query_engine.query,
                parameters.query
            )
            
            # 尝试从源节点提取SQL查询
            sql_query = None
            if hasattr(response, 'metadata') and response.metadata:
                if 'sql_query' in response.metadata:
                    sql_query = response.metadata['sql_query']
            
            context = ""
            if sql_query:
                context += f"执行的SQL查询：\n```sql\n{sql_query}\n```\n\n"
            
            context += f"查询结果：\n{response.response}\n"
            
            return DatabaseQueryResult(
                success=True,
                context=context,
                data=response.response,
                sql=sql_query
            )
            
        except Exception as e:
            self.logger.error(f"执行SQL路由查询出错: {str(e)}", exc_info=True)
            return DatabaseQueryResult(
                success=False,
                error_message=f"执行SQL路由查询出错: {str(e)}"
            )
    
    def _format_table(self, data):
        """将数据格式化为表格样式的字符串"""
        if not data or not isinstance(data, list) or len(data) == 0:
            return "无数据"
        
        # 获取所有字段名
        headers = []
        for item in data:
            if isinstance(item, dict):
                for key in item.keys():
                    if key not in headers:
                        headers.append(key)
        
        if not headers:
            return "数据结构不是表格格式"
        
        # 格式化表头
        table = "| " + " | ".join(headers) + " |\n"
        table += "| " + " | ".join(["---"] * len(headers)) + " |\n"
        
        # 格式化数据行
        for item in data:
            if isinstance(item, dict):
                row = []
                for header in headers:
                    cell = str(item.get(header, ""))
                    # 处理长字段，防止表格变形
                    if len(cell) > 50:
                        cell = cell[:47] + "..."
                    row.append(cell)
                table += "| " + " | ".join(row) + " |\n"
        
        return table
    
    async def _run_async(self, func, *args, **kwargs):
        """异步执行同步函数"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs)) 