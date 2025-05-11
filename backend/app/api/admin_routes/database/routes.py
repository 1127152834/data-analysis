"""
数据库连接API路由模块

定义用于管理数据库连接的API端点
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from app.models.database_connection import DatabaseConnection, DatabaseType, ConnectionStatus
from app.repositories.database_connection import DatabaseConnectionRepo
from app.core.db import get_db_session
from app.auth.deps import get_current_admin_user
from app.models.auth import User
from app.parameters.database_connection import (
    BaseDatabaseParameters,
    MySQLParameters,
    PostgreSQLParameters,
    MongoDBParameters,
    SQLServerParameters,
    OracleParameters,
)
from app.utils.crypto import encrypt_dict_values
from app.rag.database import get_connector

from .models import (
    DatabaseConnectionCreate,
    DatabaseConnectionUpdate,
    DatabaseConnectionDetail,
    DatabaseConnectionList,
    ConnectionTestResponse,
    DatabaseMetadataResponse,
)


router = APIRouter()

# 依赖项
SessionDep = Depends(get_db_session)
CurrentAdminUserDep = Depends(get_current_admin_user)


@router.get("/admin/database/types", response_model=List[str])
def list_database_types(user: User = CurrentAdminUserDep):
    """
    列出支持的数据库类型
    
    返回系统支持的所有数据库类型
    """
    return [db_type.value for db_type in DatabaseType]


@router.get("/admin/database/connections", response_model=List[DatabaseConnectionList])
def list_database_connections(
    session: Session = SessionDep,
    user: User = CurrentAdminUserDep,
    query: Optional[str] = Query(None, description="搜索关键词"),
    database_type: Optional[str] = Query(None, description="数据库类型"),
    status: Optional[str] = Query(None, description="连接状态"),
    skip: int = Query(0, ge=0, description="分页起始位置"),
    limit: int = Query(100, ge=1, le=500, description="分页条数"),
):
    """
    列出数据库连接
    
    返回符合条件的数据库连接列表
    """
    # 转换状态字符串为枚举（如果有）
    connection_status = None
    if status:
        try:
            connection_status = ConnectionStatus(status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid connection status: {status}"
            )
    
    # 使用仓库查询数据
    repo = DatabaseConnectionRepo()
    connections = repo.search(
        session=session,
        query=query,
        database_type=database_type,
        status=connection_status,
        skip=skip,
        limit=limit,
    )
    
    return connections


@router.post("/admin/database/connections", response_model=DatabaseConnectionDetail)
def create_database_connection(
    connection_create: DatabaseConnectionCreate,
    session: Session = SessionDep,
    user: User = CurrentAdminUserDep,
):
    """
    创建数据库连接
    
    创建新的数据库连接
    """
    # 检查名称是否已存在
    repo = DatabaseConnectionRepo()
    existing = repo.get_by_name(session, connection_create.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Database connection with name '{connection_create.name}' already exists"
        )
    
    # 获取参数类
    params_class = _get_params_class_for_type(connection_create.database_type)
    
    # 加密敏感字段
    encrypted_config = encrypt_dict_values(
        connection_create.config,
        params_class.SENSITIVE_FIELDS
    )
    
    # 创建新连接
    new_connection = DatabaseConnection(
        name=connection_create.name,
        description=connection_create.description,
        database_type=connection_create.database_type,
        config=encrypted_config,
        read_only=connection_create.read_only,
        user_id=user.id,
        connection_status=ConnectionStatus.DISCONNECTED,
    )
    
    # 保存到数据库
    connection = repo.create(session, new_connection)
    
    # 如果请求测试连接，则执行连接测试
    if connection_create.test_connection:
        _test_and_update_connection(connection.id, session)
    
    return connection


@router.get("/admin/database/connections/{connection_id}", response_model=DatabaseConnectionDetail)
def get_database_connection(
    connection_id: int,
    session: Session = SessionDep,
    user: User = CurrentAdminUserDep,
):
    """
    获取数据库连接详情
    
    返回指定ID的数据库连接详细信息
    """
    repo = DatabaseConnectionRepo()
    connection = repo.get(session, connection_id)
    
    if not connection or connection.deleted_at:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Database connection with ID {connection_id} not found"
        )
    
    return connection


@router.put("/admin/database/connections/{connection_id}", response_model=DatabaseConnectionDetail)
def update_database_connection(
    connection_id: int,
    connection_update: DatabaseConnectionUpdate,
    session: Session = SessionDep,
    user: User = CurrentAdminUserDep,
):
    """
    更新数据库连接
    
    更新指定ID的数据库连接信息
    """
    repo = DatabaseConnectionRepo()
    connection = repo.get(session, connection_id)
    
    if not connection or connection.deleted_at:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Database connection with ID {connection_id} not found"
        )
    
    # 检查名称是否已存在（如果要更新名称）
    if connection_update.name and connection_update.name != connection.name:
        existing = repo.get_by_name(session, connection_update.name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Database connection with name '{connection_update.name}' already exists"
            )
    
    # 更新基本字段
    if connection_update.name is not None:
        connection.name = connection_update.name
        
    if connection_update.description is not None:
        connection.description = connection_update.description
        
    if connection_update.read_only is not None:
        connection.read_only = connection_update.read_only
    
    # 更新配置（如果有）
    if connection_update.config:
        # 获取参数类
        params_class = _get_params_class_for_type(connection.database_type)
        
        # 加密敏感字段
        encrypted_config = encrypt_dict_values(
            connection_update.config,
            params_class.SENSITIVE_FIELDS
        )
        
        # 更新配置
        connection.config.update(encrypted_config)
    
    # 保存更新
    session.add(connection)
    session.commit()
    session.refresh(connection)
    
    # 如果请求测试连接，则执行连接测试
    if connection_update.test_connection:
        _test_and_update_connection(connection.id, session)
    
    return connection


@router.delete("/admin/database/connections/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_database_connection(
    connection_id: int,
    session: Session = SessionDep,
    user: User = CurrentAdminUserDep,
):
    """
    删除数据库连接
    
    软删除指定ID的数据库连接
    """
    repo = DatabaseConnectionRepo()
    success = repo.soft_delete(session, connection_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Database connection with ID {connection_id} not found"
        )


@router.post("/admin/database/connections/{connection_id}/test", response_model=ConnectionTestResponse)
def test_database_connection(
    connection_id: int,
    session: Session = SessionDep,
    user: User = CurrentAdminUserDep,
):
    """
    测试数据库连接
    
    测试指定ID的数据库连接并返回结果
    """
    return _test_and_update_connection(connection_id, session)


@router.post("/admin/database/connections/{connection_id}/metadata", response_model=DatabaseMetadataResponse)
def get_database_metadata(
    connection_id: int,
    force_refresh: bool = Query(False, description="是否强制刷新元数据"),
    session: Session = SessionDep,
    user: User = CurrentAdminUserDep,
):
    """
    获取数据库元数据
    
    获取指定ID的数据库元数据信息
    """
    repo = DatabaseConnectionRepo()
    connection = repo.get(session, connection_id)
    
    if not connection or connection.deleted_at:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Database connection with ID {connection_id} not found"
        )
    
    # 如果有缓存且不强制刷新，则使用缓存
    if connection.metadata_cache and not force_refresh:
        # 转换时间戳为datetime
        updated_at = connection.metadata_updated_at
        if 'updated_at' in connection.metadata_cache:
            try:
                timestamp = connection.metadata_cache['updated_at']
                updated_at = datetime.fromtimestamp(timestamp)
            except (ValueError, TypeError):
                pass
            
        return DatabaseMetadataResponse(
            database=connection.metadata_cache.get('database', ''),
            tables=connection.metadata_cache.get('tables', {}),
            table_count=connection.metadata_cache.get('table_count', 0),
            updated_at=updated_at,
        )
    
    # 否则，获取新的元数据
    connector = get_connector(connection)
    if not connector:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create connector for database type: {connection.database_type}"
        )
    
    # 获取元数据
    try:
        metadata = connector.get_metadata()
        
        # 更新元数据缓存
        repo.update_metadata(session, connection_id, metadata)
        
        # 转换时间戳为datetime
        updated_at = datetime.utcnow()
        if 'updated_at' in metadata:
            try:
                timestamp = metadata['updated_at']
                updated_at = datetime.fromtimestamp(timestamp)
            except (ValueError, TypeError):
                pass
        
        return DatabaseMetadataResponse(
            database=metadata.get('database', ''),
            tables=metadata.get('tables', {}),
            table_count=metadata.get('table_count', 0),
            updated_at=updated_at,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get metadata: {str(e)}"
        )
    finally:
        # 确保连接被关闭
        connector.close()


@router.post("/admin/database/connections/{connection_id}/query")
def execute_database_query(
    connection_id: int,
    query: str,
    session: Session = SessionDep,
    user: User = CurrentAdminUserDep,
):
    """
    执行数据库查询
    
    在指定的数据库连接上执行SQL查询
    """
    repo = DatabaseConnectionRepo()
    connection = repo.get(session, connection_id)
    
    if not connection or connection.deleted_at:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Database connection with ID {connection_id} not found"
        )
    
    # 获取连接器
    connector = get_connector(connection)
    if not connector:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create connector for database type: {connection.database_type}"
        )
    
    # 执行查询
    try:
        results, error = connector.execute_query(query)
        
        if error:
            return {"success": False, "error": error, "results": []}
        
        return {"success": True, "results": results}
    except Exception as e:
        return {"success": False, "error": str(e), "results": []}
    finally:
        # 确保连接被关闭
        connector.close()


# 辅助函数

def _get_params_class_for_type(database_type: DatabaseType) -> type:
    """
    根据数据库类型获取参数类
    
    参数:
        database_type: 数据库类型
        
    返回:
        type: 参数类
        
    异常:
        ValueError: 如果数据库类型不支持
    """
    if database_type == DatabaseType.MYSQL:
        return MySQLParameters
    elif database_type == DatabaseType.POSTGRESQL:
        return PostgreSQLParameters
    elif database_type == DatabaseType.MONGODB:
        return MongoDBParameters
    elif database_type == DatabaseType.SQLSERVER:
        return SQLServerParameters
    elif database_type == DatabaseType.ORACLE:
        return OracleParameters
    else:
        raise ValueError(f"Unsupported database type: {database_type}")


def _test_and_update_connection(connection_id: int, session: Session) -> ConnectionTestResponse:
    """
    测试数据库连接并更新连接状态
    
    参数:
        connection_id: 数据库连接ID
        session: 数据库会话
        
    返回:
        ConnectionTestResponse: 连接测试结果
        
    异常:
        HTTPException: 如果连接不存在
    """
    repo = DatabaseConnectionRepo()
    connection = repo.get(session, connection_id)
    
    if not connection or connection.deleted_at:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Database connection with ID {connection_id} not found"
        )
    
    # 获取连接器
    connector = get_connector(connection)
    if not connector:
        repo.update_status(session, connection_id, ConnectionStatus.ERROR)
        return ConnectionTestResponse(
            success=False,
            message=f"Failed to create connector for database type: {connection.database_type}",
        )
    
    # 测试连接
    try:
        test_result = connector.test_connection()
        
        # 更新连接状态
        new_status = ConnectionStatus.CONNECTED if test_result.success else ConnectionStatus.ERROR
        repo.update_status(session, connection_id, new_status)
        
        return ConnectionTestResponse(
            success=test_result.success,
            message=test_result.message,
            details=test_result.details,
        )
    finally:
        # 确保连接被关闭
        connector.close() 