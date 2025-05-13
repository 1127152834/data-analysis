"""
数据库管理模块

提供数据库连接和操作的核心功能
"""

from typing import Optional

from app.models.database_connection import DatabaseConnection, DatabaseType
from app.rag.database.base import BaseConnector


def get_connector(connection: DatabaseConnection) -> Optional[BaseConnector]:
    """
    获取数据库连接器
    
    根据数据库连接配置创建适当的连接器实例
    
    参数:
        connection: 数据库连接配置
        
    返回:
        BaseConnector: 数据库连接器实例
        
    异常:
        ValueError: 如果数据库类型不支持
    """
    # 根据数据库类型动态导入相应的连接器
    if connection.database_type == DatabaseType.MYSQL:
        from app.rag.database.connectors.mysql import MySQLConnector
        return MySQLConnector(connection)
    elif connection.database_type == DatabaseType.POSTGRESQL:
        from app.rag.database.connectors.postgresql import PostgreSQLConnector
        return PostgreSQLConnector(connection)
    elif connection.database_type == DatabaseType.MONGODB:
        from app.rag.database.connectors.mongodb import MongoDBConnector
        return MongoDBConnector(connection)
    elif connection.database_type == DatabaseType.SQLSERVER:
        from app.rag.database.connectors.sqlserver import SQLServerConnector
        return SQLServerConnector(connection)
    elif connection.database_type == DatabaseType.ORACLE:
        from app.rag.database.connectors.oracle import OracleConnector
        return OracleConnector(connection)
    elif connection.database_type == DatabaseType.SQLITE:
        from app.rag.database.connectors.sqlite import SQLiteConnector
        return SQLiteConnector(connection)
    else:
        raise ValueError(f"Unsupported database type: {connection.database_type}") 