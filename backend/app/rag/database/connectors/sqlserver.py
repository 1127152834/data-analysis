"""
SQLServer数据库连接器模块

提供SQLServer数据库的连接和操作功能
"""

import time
import logging
from typing import Dict, List, Optional, Tuple, Any
from contextlib import contextmanager

import pyodbc
from sqlalchemy import create_engine, inspect, MetaData, Table, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import QueuePool

from app.models.database_connection import DatabaseConnection
from app.parameters.database_connection import SQLServerParameters
from app.rag.database.base import BaseConnector, ConnectionTestResult
from app.utils.crypto import decrypt_dict_values


logger = logging.getLogger(__name__)


class SQLServerConnector(BaseConnector):
    """
    SQLServer数据库连接器

    提供与SQLServer数据库交互的功能
    """

    def __init__(self, connection: DatabaseConnection):
        """
        初始化SQLServer连接器

        参数:
            connection: 数据库连接配置
        """
        self.connection_config = connection
        self.engine: Optional[Engine] = None
        self.metadata: Optional[MetaData] = None
        self.tables: Dict[str, Table] = {}
        self.parameters: Optional[SQLServerParameters] = None

        # 初始化参数
        self._init_parameters()

    def _init_parameters(self) -> None:
        """
        初始化连接参数

        从连接配置中解析和解密参数
        """
        # 解密配置中的敏感字段
        config = decrypt_dict_values(
            self.connection_config.config, SQLServerParameters.SENSITIVE_FIELDS
        )

        # 创建参数对象
        self.parameters = SQLServerParameters.from_dict(config)

    def connect(self) -> bool:
        """
        建立数据库连接

        创建SQLAlchemy引擎并建立连接

        返回:
            bool: 连接是否成功
        """
        try:
            # 创建SQLAlchemy引擎
            if not self.parameters:
                self._init_parameters()

            connection_str = self.parameters.get_connection_string()
            self.engine = create_engine(
                connection_str,
                poolclass=QueuePool,
                pool_size=5,
                pool_recycle=300,
                pool_pre_ping=True,  # 连接前ping确保连接有效
            )

            # 测试连接
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))

            # 更新连接状态
            logger.info(
                f"Successfully connected to SQL Server database: {self.parameters.database}"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to connect to SQL Server database: {str(e)}")
            return False

    @contextmanager
    def get_connection(self):
        """
        获取数据库连接的上下文管理器

        返回一个上下文管理的数据库连接

        异常:
            Exception: 如果无法获取连接
        """
        if not self.engine:
            self.connect()

        if not self.engine:
            raise Exception("Failed to establish database connection")

        conn = self.engine.connect()
        try:
            yield conn
        finally:
            conn.close()

    def test_connection(self) -> ConnectionTestResult:
        """
        测试数据库连接

        测试与数据库的连接并返回详细结果

        返回:
            ConnectionTestResult: 连接测试结果
        """
        try:
            start_time = time.time()

            # 尝试连接
            if not self.engine:
                self.connect()

            if not self.engine:
                return ConnectionTestResult(
                    success=False,
                    message="Failed to create database engine",
                    details=None,
                )

            # 获取数据库版本和信息
            with self.get_connection() as conn:
                result = conn.execute(text("SELECT @@VERSION as version")).fetchone()
                version = result[0] if result else "Unknown"

                # 获取表数量
                tables_result = conn.execute(
                    text(
                        f"SELECT COUNT(*) as table_count FROM information_schema.tables "
                        f"WHERE table_type = 'BASE TABLE'"
                    )
                ).fetchone()
                table_count = tables_result[0] if tables_result else 0

            # 计算连接时间
            connection_time = time.time() - start_time

            return ConnectionTestResult(
                success=True,
                message=f"Successfully connected to SQL Server {version.split()[0] if version else 'Unknown'}",
                details={
                    "version": version,
                    "database": self.parameters.database,
                    "table_count": table_count,
                    "connection_time_ms": round(connection_time * 1000, 2),
                    "read_only": self.connection_config.read_only,
                },
            )
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return ConnectionTestResult(
                success=False, message=f"Connection failed: {str(e)}", details=None
            )

    def get_metadata(self) -> Dict[str, Any]:
        """
        获取数据库元数据

        获取数据库的表结构、列信息等

        返回:
            Dict[str, Any]: 数据库元数据
        """
        if not self.engine:
            self.connect()

        if not self.engine:
            return {"error": "Failed to connect to database"}

        try:
            # 创建元数据对象
            self.metadata = MetaData()
            inspector = inspect(self.engine)

            # 获取所有表信息
            tables_metadata = {}
            for schema in inspector.get_schema_names():
                # 过滤系统模式
                if schema in [
                    "sys",
                    "INFORMATION_SCHEMA",
                    "guest",
                    "db_owner",
                    "db_accessadmin",
                    "db_securityadmin",
                    "db_ddladmin",
                    "db_backupoperator",
                    "db_datareader",
                    "db_datawriter",
                    "db_denydatareader",
                    "db_denydatawriter",
                ]:
                    continue

                for table_name in inspector.get_table_names(schema=schema):
                    full_table_name = f"{schema}.{table_name}"
                    columns = []
                    for column in inspector.get_columns(table_name, schema=schema):
                        columns.append(
                            {
                                "name": column["name"],
                                "type": str(column["type"]),
                                "nullable": column.get("nullable", True),
                                "default": str(column.get("default", "")),
                                "autoincrement": column.get("autoincrement", False),
                                "primary_key": column.get("primary_key", False),
                            }
                        )

                    # 获取主键信息
                    pk = inspector.get_pk_constraint(table_name, schema=schema)
                    primary_keys = pk.get("constrained_columns", []) if pk else []

                    # 获取外键信息
                    foreign_keys = []
                    for fk in inspector.get_foreign_keys(table_name, schema=schema):
                        foreign_keys.append(
                            {
                                "name": fk.get("name", ""),
                                "referred_schema": fk.get("referred_schema", schema),
                                "referred_table": fk.get("referred_table", ""),
                                "referred_columns": fk.get("referred_columns", []),
                                "constrained_columns": fk.get(
                                    "constrained_columns", []
                                ),
                            }
                        )

                    # 获取索引信息
                    indexes = []
                    for idx in inspector.get_indexes(table_name, schema=schema):
                        indexes.append(
                            {
                                "name": idx.get("name", ""),
                                "unique": idx.get("unique", False),
                                "column_names": idx.get("column_names", []),
                            }
                        )

                    tables_metadata[full_table_name] = {
                        "schema": schema,
                        "name": table_name,
                        "columns": columns,
                        "primary_keys": primary_keys,
                        "foreign_keys": foreign_keys,
                        "indexes": indexes,
                    }

            return {
                "database": self.parameters.database,
                "tables": tables_metadata,
                "table_count": len(tables_metadata),
                "updated_at": time.time(),
            }
        except Exception as e:
            logger.error(f"Failed to get metadata: {str(e)}")
            return {"error": str(e)}

    def execute_query(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """
        执行SQL查询

        执行查询并返回结果和可能的错误

        参数:
            query: SQL查询字符串
            params: 查询参数

        返回:
            Tuple[List[Dict[str, Any]], Optional[str]]: 查询结果和错误信息
        """
        # 如果是只读模式，禁止执行非SELECT查询
        if self.connection_config.read_only:
            # 简单检查是否是SELECT查询（更完善的检查应使用SQL解析库）
            query_upper = query.strip().upper()
            if not (
                query_upper.startswith("SELECT")
                or query_upper.startswith("WITH")
                or query_upper.startswith("DECLARE")
                or query_upper.startswith("EXEC SP_")
                or query_upper.startswith("EXECUTE SP_")
            ):
                return [], "Write operations are not allowed in read-only mode"

        if not self.engine:
            self.connect()

        if not self.engine:
            return [], "Failed to connect to database"

        try:
            # 使用pyodbc直接执行查询以获取字典格式结果
            connection_str = f"DRIVER={{{self.parameters.driver}}};SERVER={self.parameters.host},{self.parameters.port};DATABASE={self.parameters.database};UID={self.parameters.user};PWD={self.parameters.password}"

            if self.parameters.trust_server_certificate:
                connection_str += ";TrustServerCertificate=yes"

            if not self.parameters.encrypt:
                connection_str += ";Encrypt=no"

            conn = pyodbc.connect(connection_str)
            conn.autocommit = False

            cursor = conn.cursor()

            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            # 对于查询操作，返回结果集
            if cursor.description is not None:
                columns = [column[0] for column in cursor.description]
                result_rows = cursor.fetchall()

                # 将结果转换为字典列表
                results = []
                for row in result_rows:
                    row_dict = {}
                    for i, value in enumerate(row):
                        row_dict[columns[i]] = value
                    results.append(row_dict)
            else:
                # 对于非查询操作，返回影响的行数
                results = [{"affected_rows": cursor.rowcount}]
                conn.commit()

            cursor.close()
            conn.close()
            return results, None
        except Exception as e:
            logger.error(f"Query execution failed: {str(e)}")
            return [], str(e)

    def close(self) -> None:
        """
        关闭数据库连接

        释放数据库连接资源
        """
        if self.engine:
            self.engine.dispose()
            self.engine = None
            self.metadata = None
            self.tables = {}
