"""
数据库连接API路由模块

定义用于管理数据库连接的API端点
"""

from datetime import datetime
from typing import List, Optional, Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from app.models.database_connection import DatabaseConnection, DatabaseType, ConnectionStatus
from app.repositories.database_connection import DatabaseConnectionRepo
from app.core.db import get_db_session
from app.api.deps import SessionDep, CurrentSuperuserDep
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


@router.get("/admin/database/types", response_model=List[str])
def list_database_types(user: User = CurrentSuperuserDep):
    """
    列出支持的数据库类型
    
    返回系统支持的所有数据库类型
    """
    return [db_type.value for db_type in DatabaseType]


@router.get("/admin/database/connections", response_model=List[DatabaseConnectionList])
def list_database_connections(
    session: Annotated[Session, Depends(get_db_session)],
    user: User = CurrentSuperuserDep,
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
                detail=f"无效的连接状态: {status}"
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
    session: Annotated[Session, Depends(get_db_session)],
    user: User = CurrentSuperuserDep,
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
            detail=f"数据库连接名称 '{connection_create.name}' 已存在"
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
        user_id=user.id,  # 确保这里传入的是UUID值而不是字符串表达式
        connection_status=ConnectionStatus.DISCONNECTED,
    )
    
    # 添加调试日志
    print(f"DEBUG: user.id类型: {type(user.id)}, 值: {user.id}")
    
    # 保存到数据库
    connection = repo.create(session, new_connection)
    
    # 如果请求测试连接，则执行连接测试
    if connection_create.test_connection:
        _test_and_update_connection(connection.id, session)
    
    return connection


@router.get("/admin/database/connections/{connection_id}", response_model=DatabaseConnectionDetail)
def get_database_connection(
    connection_id: int,
    session: Annotated[Session, Depends(get_db_session)],
    user: User = CurrentSuperuserDep,
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
            detail=f"未找到ID为 {connection_id} 的数据库连接"
        )
    
    return connection


@router.put("/admin/database/connections/{connection_id}", response_model=DatabaseConnectionDetail)
def update_database_connection(
    connection_id: int,
    connection_update: DatabaseConnectionUpdate,
    session: Annotated[Session, Depends(get_db_session)],
    user: User = CurrentSuperuserDep,
):
    """
    更新数据库连接
    
    更新指定ID的数据库连接信息
    """
    # 添加请求体的日志记录
    print(f"收到更新数据库连接请求，ID: {connection_id}, 数据: {connection_update.dict(exclude_unset=True)}")
    
    repo = DatabaseConnectionRepo()
    connection = repo.get(session, connection_id)
    
    if not connection or connection.deleted_at:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"未找到ID为 {connection_id} 的数据库连接"
        )
    
    # 检查名称是否已存在（如果要更新名称）
    if connection_update.name and connection_update.name != connection.name:
        existing = repo.get_by_name(session, connection_update.name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"数据库连接名称 '{connection_update.name}' 已存在"
            )
    
    # 更新基本字段
    if connection_update.name is not None:
        connection.name = connection_update.name
    
    if connection_update.description is not None:
        connection.description = connection_update.description
    
    if connection_update.read_only is not None:
        connection.read_only = connection_update.read_only
    
    # 处理表描述信息
    if connection_update.table_descriptions is not None:
        print(f"更新表描述信息: {connection_update.table_descriptions}")
        connection.table_descriptions = connection_update.table_descriptions
    
    # 处理列描述信息
    if connection_update.column_descriptions is not None:
        print(f"更新列描述信息: {connection_update.column_descriptions}")
        connection.column_descriptions = connection_update.column_descriptions
    
    # 处理可访问角色
    if connection_update.accessible_roles is not None:
        print(f"更新可访问角色: {connection_update.accessible_roles}")
        connection.accessible_roles = connection_update.accessible_roles
    
    # 更新数据库类型和配置（如果提供）
    if connection_update.database_type:
        # 如果更改了数据库类型，则需要重置配置
        if connection_update.database_type != connection.database_type:
            connection.database_type = connection_update.database_type
            # 清空原有配置
            if connection_update.config is None:
                connection.config = {}
    
    # 更新配置（如果提供）
    if connection_update.config is not None:
        # 如果提供了新配置，则与现有配置合并
        # 获取参数类
        params_class = _get_params_class_for_type(connection.database_type)
        
        # 合并配置，现有配置优先
        merged_config = {**connection.config}
        # 更新/添加新配置
        for key, value in connection_update.config.items():
            merged_config[key] = value
        
        # 加密敏感字段
        encrypted_config = encrypt_dict_values(
            merged_config,
            params_class.SENSITIVE_FIELDS
        )
        
        connection.config = encrypted_config
    
    # 更新并保存
    connection.updated_at = datetime.utcnow()
    session.add(connection)
    session.commit()
    session.refresh(connection)
    
    # 如果请求测试连接，则执行连接测试
    if connection_update.test_connection:
        _test_and_update_connection(connection.id, session)
    
    # 打印更新后的连接信息
    print(f"数据库连接更新成功，ID: {connection_id}")
    
    return connection


@router.delete("/admin/database/connections/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_database_connection(
    connection_id: int,
    session: Annotated[Session, Depends(get_db_session)],
    user: User = CurrentSuperuserDep,
):
    """
    删除数据库连接
    
    软删除指定ID的数据库连接
    """
    repo = DatabaseConnectionRepo()
    connection = repo.get(session, connection_id)
    
    if not connection or connection.deleted_at:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"未找到ID为 {connection_id} 的数据库连接"
        )
    
    # 软删除
    repo.soft_delete(session, connection)


@router.post("/admin/database/connections/{connection_id}/test", response_model=ConnectionTestResponse)
def test_database_connection(
    connection_id: int,
    session: Annotated[Session, Depends(get_db_session)],
    user: User = CurrentSuperuserDep,
):
    """
    测试数据库连接
    
    测试指定ID的数据库连接是否可用
    """
    return _test_and_update_connection(connection_id, session)


@router.post("/admin/database/connections/{connection_id}/metadata", response_model=DatabaseMetadataResponse)
def get_database_metadata(
    connection_id: int,
    session: Annotated[Session, Depends(get_db_session)],
    user: User = CurrentSuperuserDep,
    force_refresh: bool = Query(False, description="是否强制刷新元数据"),
):
    """
    获取数据库元数据
    
    获取指定ID的数据库连接的元数据（模式、表、列等）
    可选择是否强制刷新缓存的元数据
    """
    repo = DatabaseConnectionRepo()
    connection = repo.get(session, connection_id)
    
    if not connection or connection.deleted_at:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"未找到ID为 {connection_id} 的数据库连接"
        )
    
    # 如果已有缓存且未要求强制刷新，则直接返回缓存
    if connection.metadata_cache and not force_refresh:
        return DatabaseMetadataResponse(
            metadata=connection.metadata_cache,
            last_updated=connection.metadata_updated_at,
            is_cached=True
        )
    
    # 获取连接器
    try:
        connector = get_connector(connection)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建数据库连接器失败: {str(e)}"
        )
    
    # 获取元数据
    try:
        metadata = connector.get_metadata()
        
        # 更新元数据缓存
        connection.metadata_cache = metadata
        connection.metadata_updated_at = datetime.utcnow()
        connection.updated_at = datetime.utcnow()
        session.add(connection)
        session.commit()
        
        return DatabaseMetadataResponse(
            metadata=metadata,
            last_updated=connection.metadata_updated_at,
            is_cached=False
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取数据库元数据失败: {str(e)}"
        )
    finally:
        connector.close()


@router.post("/admin/database/connections/{connection_id}/query")
def execute_database_query(
    connection_id: int,
    query: str,
    session: Annotated[Session, Depends(get_db_session)],
    user: User = CurrentSuperuserDep,
):
    """
    执行数据库查询
    
    在指定ID的数据库连接上执行SQL查询
    注意：此API仅支持SELECT语句，且仅在read_only=False的连接上支持非SELECT语句
    """
    repo = DatabaseConnectionRepo()
    connection = repo.get(session, connection_id)
    
    if not connection or connection.deleted_at:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"未找到ID为 {connection_id} 的数据库连接"
        )
    
    # 检查是否为只读模式，如果是只读模式且查询不是SELECT，则拒绝执行
    if connection.read_only and not query.strip().upper().startswith("SELECT"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只读连接仅允许执行SELECT语句"
        )
    
    # 获取连接器
    try:
        connector = get_connector(connection)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建数据库连接器失败: {str(e)}"
        )
    
    # 执行查询
    try:
        result = connector.execute_query(query)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询执行失败: {str(e)}"
        )
    finally:
        connector.close()


@router.post("/admin/database/connections/test-config", response_model=ConnectionTestResponse)
def test_database_connection_config(
    connection_config: DatabaseConnectionCreate,
    session: Annotated[Session, Depends(get_db_session)],
    user: User = CurrentSuperuserDep,
):
    """
    测试数据库连接配置
    
    测试未保存的数据库连接配置是否可用
    """
    try:
        # 获取参数类
        params_class = _get_params_class_for_type(connection_config.database_type)
        
        # 创建临时连接对象
        temp_connection = DatabaseConnection(
            id=-1,  # 临时ID
            name=connection_config.name,
            description=connection_config.description,
            database_type=connection_config.database_type,
            config=connection_config.config,
            read_only=connection_config.read_only,
            user_id=user.id,
            connection_status=ConnectionStatus.DISCONNECTED,
        )
        
        # 获取连接器
        connector = get_connector(temp_connection)
        
        # 测试连接并获取结果
        test_result = connector.test_connection()
        
        return ConnectionTestResponse(
            success=test_result.success,
            message=test_result.message,
            details=test_result.details
        )
    except Exception as e:
        # 返回错误详情
        error_message = str(e)
        return ConnectionTestResponse(
            success=False,
            message=f"连接失败: {error_message}",
            details={"error": error_message}
        )
    finally:
        # 如果创建了连接器，确保关闭
        if 'connector' in locals():
            connector.close()


def _get_params_class_for_type(database_type: DatabaseType) -> type:
    """
    根据数据库类型获取对应的参数类
    
    参数:
        database_type: 数据库类型
        
    返回:
        对应的参数类
        
    异常:
        ValueError: 如果没有找到对应的参数类
    """
    type_to_class = {
        DatabaseType.MYSQL: MySQLParameters,
        DatabaseType.POSTGRESQL: PostgreSQLParameters,
        DatabaseType.MONGODB: MongoDBParameters,
        DatabaseType.SQLSERVER: SQLServerParameters,
        DatabaseType.ORACLE: OracleParameters,
    }
    
    if database_type not in type_to_class:
        raise ValueError(f"未找到数据库类型对应的参数类: {database_type}")
    
    return type_to_class[database_type]


def _test_and_update_connection(connection_id: int, session: Session) -> ConnectionTestResponse:
    """
    测试连接并更新连接状态
    
    内部函数，用于测试连接并更新数据库中的连接状态
    
    参数:
        connection_id: 数据库连接ID
        session: 数据库会话
        
    返回:
        ConnectionTestResponse: 测试结果
    """
    repo = DatabaseConnectionRepo()
    connection = repo.get(session, connection_id)
    
    if not connection or connection.deleted_at:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"未找到ID为 {connection_id} 的数据库连接"
        )
    
    try:
        # 获取连接器
        connector = get_connector(connection)
        
        # 测试连接并获取结果
        test_result = connector.test_connection()
        
        # 根据测试结果更新连接状态
        if test_result.success:
            connection.connection_status = ConnectionStatus.CONNECTED
            connection.last_connected_at = datetime.utcnow()
        else:
            connection.connection_status = ConnectionStatus.ERROR
        
        connection.updated_at = datetime.utcnow()
        session.add(connection)
        session.commit()
        
        # 返回测试结果
        return ConnectionTestResponse(
            success=test_result.success,
            message=test_result.message,
            details=test_result.details
        )
    except Exception as e:
        # 更新连接状态为错误
        connection.connection_status = ConnectionStatus.ERROR
        connection.updated_at = datetime.utcnow()
        session.add(connection)
        session.commit()
        
        # 返回错误详情
        error_message = str(e)
        return ConnectionTestResponse(
            success=False,
            message=f"连接失败: {error_message}",
            details={"error": error_message}
        )
    finally:
        # 如果创建了连接器，确保关闭
        if 'connector' in locals():
            connector.close() 