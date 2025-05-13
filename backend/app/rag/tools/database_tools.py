from sqlalchemy import create_engine
from llama_index.core import SQLDatabase
from llama_index.core.query_engine import NLSQLTableQueryEngine
from llama_index.core.tools import FunctionTool, ToolMetadata
from llama_index.core.llms.llm import LLM as LlamaLLM  # 避免命名冲突

from app.models.database_connection import DatabaseConnection, DatabaseType
import logging

logger = logging.getLogger(__name__)

def create_llama_sql_database_from_connection(db_conn: DatabaseConnection) -> SQLDatabase:
    """创建LlamaIndex SQLDatabase对象
    
    根据DatabaseConnection对象配置创建LlamaIndex SQLDatabase对象，
    用于自然语言到SQL的查询。
    
    参数:
        db_conn: 数据库连接对象
        
    返回:
        SQLDatabase对象
        
    异常:
        NotImplementedError: 不支持的数据库类型
    """
    try:
        # 根据数据库类型构建连接字符串
        if db_conn.database_type == DatabaseType.SQLITE:
            connection_string = f"sqlite:///{db_conn.config.get('file_path')}"
        elif db_conn.database_type == DatabaseType.MYSQL:
            user = db_conn.config.get('user')
            password = db_conn.config.get('password')  # 确保安全处理
            host = db_conn.config.get('host')
            port = db_conn.config.get('port')
            dbname = db_conn.config.get('database')
            connection_string = f"mysql+mysqlconnector://{user}:{password}@{host}:{port}/{dbname}"
        elif db_conn.database_type == DatabaseType.POSTGRESQL:
            user = db_conn.config.get('user')
            password = db_conn.config.get('password')
            host = db_conn.config.get('host')
            port = db_conn.config.get('port', 5432)
            dbname = db_conn.config.get('database')
            connection_string = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
        # 添加其他数据库类型支持...
        else:
            raise NotImplementedError(f"不支持的数据库类型: {db_conn.database_type}")
        
        engine = create_engine(connection_string)
        
        # 使用table_descriptions限定可访问的表
        include_tables = list(db_conn.table_descriptions.keys()) if db_conn.table_descriptions else None
        
        return SQLDatabase(engine, include_tables=include_tables)
    except Exception as e:
        logger.error(f"创建LlamaIndex SQLDatabase失败: {e}")
        raise
        
def create_query_engine_for_database(db_conn: DatabaseConnection, llm: LlamaLLM) -> NLSQLTableQueryEngine:
    """为特定数据库连接创建查询引擎
    
    参数:
        db_conn: 数据库连接对象
        llm: LlamaIndex语言模型
        
    返回:
        NLSQLTableQueryEngine对象
    """
    llama_sql_db = create_llama_sql_database_from_connection(db_conn)
    return NLSQLTableQueryEngine(
        sql_database=llama_sql_db,
        tables=list(db_conn.table_descriptions.keys()) if db_conn.table_descriptions else None,
        llm=llm  # 使用ChatFlow中的LLM
    )
    
def create_database_function_tool(db_conn: DatabaseConnection, llm: LlamaLLM) -> FunctionTool:
    """创建单个数据库查询工具
    
    参数:
        db_conn: 数据库连接对象
        llm: LlamaIndex语言模型
        
    返回:
        FunctionTool对象，可以被代理调用
    """
    query_engine = create_query_engine_for_database(db_conn, llm)
    
    # 内部函数，将被LLM调用
    def query_database(natural_language_query: str) -> str:
        """
        使用自然语言查询预配置的数据库。
        
        Args:
            natural_language_query: 用自然语言表达的数据库查询
            
        Returns:
            查询结果的文本表示，包括生成的SQL和执行结果
        """
        try:
            logger.info(f"执行数据库查询: {natural_language_query}")
            response = query_engine.query(natural_language_query)
            sql_query = response.metadata.get("sql_query", "未生成SQL")
            result = str(response)
            logger.info(f"查询完成，SQL: {sql_query}")
            
            # 返回结构化文本
            return f"数据库: {db_conn.name}\n生成的SQL: {sql_query}\n\n结果: {result}"
        except Exception as e:
            logger.error(f"数据库查询失败: {e}")
            return f"数据库查询失败: {str(e)}"
    
    # 构建丰富的工具描述
    description = f"查询'{db_conn.name}'数据库({db_conn.database_type.value})。"
    if db_conn.description_for_llm:
        description += f"用于查询：{db_conn.description_for_llm}。"
    
    if db_conn.table_descriptions:
        description += "包含以下表及其内容："
        for table, table_desc in db_conn.table_descriptions.items():
            description += f"\n  - 表'{table}'：{table_desc}。"
            if db_conn.column_descriptions and table in db_conn.column_descriptions:
                description += " 列包括：{"
                col_descs = []
                for col, col_desc in db_conn.column_descriptions[table].items():
                    col_descs.append(f"'{col}'：'{col_desc}'")
                description += "，".join(col_descs) + "}。"
    
    # 确保工具名称唯一
    tool_name = f"query_{db_conn.name.lower().replace(' ', '_')}_{db_conn.id}"
    
    # 创建工具元数据
    metadata = ToolMetadata(
        name=tool_name,
        description=description.strip()
    )
    
    # 创建并返回函数工具
    return FunctionTool(
        fn=query_database,
        metadata=metadata
    )

def check_database_connection(db_conn: DatabaseConnection) -> bool:
    """测试数据库连接是否可用
    
    参数:
        db_conn: 数据库连接对象
        
    返回:
        布尔值，表示连接是否可用
    """
    try:
        sql_db = create_llama_sql_database_from_connection(db_conn)
        with sql_db.engine.connect() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"数据库连接测试失败: {e}")
        return False

def create_database_connection_tools(db_connections: list[DatabaseConnection], llm: LlamaLLM) -> list[FunctionTool]:
    """为多个数据库连接创建查询工具
    
    参数:
        db_connections: 数据库连接对象列表
        llm: LlamaIndex语言模型
        
    返回:
        FunctionTool对象列表
    """
    tools = []
    for db_conn in db_connections:
        # 检查连接是否可用
        if check_database_connection(db_conn):
            try:
                tool = create_database_function_tool(db_conn, llm)
                tools.append(tool)
                logger.info(f"已创建数据库查询工具: {db_conn.name} (ID: {db_conn.id})")
            except Exception as e:
                logger.error(f"创建数据库工具失败 {db_conn.name}: {e}")
        else:
            logger.warning(f"数据库连接不可用，跳过创建工具: {db_conn.name} (ID: {db_conn.id})")
    return tools 