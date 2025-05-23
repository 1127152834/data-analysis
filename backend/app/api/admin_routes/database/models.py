"""
数据库连接API模型模块

定义用于API请求和响应的数据模型
"""

from datetime import datetime
from typing import Dict, List, Optional, Any

from pydantic import BaseModel, Field, validator

from app.models.database_connection import DatabaseType, ConnectionStatus


class DatabaseConnectionCreate(BaseModel):
    """
    创建数据库连接请求模型
    
    用于创建新数据库连接的请求数据结构
    """
    name: str = Field(..., min_length=1, max_length=256, description="连接名称")
    description: str = Field(..., min_length=1, max_length=512, description="连接描述")
    database_type: DatabaseType = Field(..., description="数据库类型")
    config: Dict[str, Any] = Field(..., description="连接配置")
    read_only: bool = Field(True, description="是否只读模式")
    test_connection: bool = Field(False, description="是否测试连接")
    
    @validator('config')
    def validate_config(cls, v, values):
        """验证配置必须包含所需的字段"""
        db_type = values.get('database_type')
        if not db_type:
            return v
            
        required_fields = {'host', 'port', 'user', 'database'}  # 移除'password'，使其成为可选项
        
        # 对MongoDB需要单独处理，它只需要connection_string
        if db_type == DatabaseType.MONGODB:
            required_fields = {'connection_string'}
            
        missing_fields = required_fields - set(v.keys())
        
        if missing_fields:
            raise ValueError(f"配置缺少必需字段: {', '.join(missing_fields)}")
        
        return v


class DatabaseConnectionUpdate(BaseModel):
    """
    更新数据库连接请求模型
    
    用于部分更新数据库连接的请求数据结构
    """
    name: Optional[str] = Field(None, min_length=1, max_length=256, description="连接名称")
    description: Optional[str] = Field(None, min_length=1, max_length=512, description="连接描述")
    config: Optional[Dict[str, Any]] = Field(None, description="连接配置")
    read_only: Optional[bool] = Field(None, description="是否只读模式")
    test_connection: bool = Field(False, description="是否测试连接")
    database_type: Optional[DatabaseType] = Field(None, description="数据库类型")
    table_descriptions: Optional[Dict[str, str]] = Field(None, description="表描述信息，格式: {table_name: description}")
    column_descriptions: Optional[Dict[str, str]] = Field(None, description="列描述信息，格式: {table_name.column_name: description}")
    accessible_roles: Optional[List[str]] = Field(None, description="可访问此数据库的角色列表，例如: ['admin', 'user']")


class DatabaseConnectionDetail(BaseModel):
    """
    数据库连接详情响应模型
    
    用于返回数据库连接详细信息的响应数据结构
    """
    id: int
    name: str
    description: str
    database_type: DatabaseType
    config: Dict[str, Any]  # 敏感字段如密码会被移除
    read_only: bool
    connection_status: ConnectionStatus
    last_connected_at: Optional[datetime]
    metadata_updated_at: Optional[datetime]
    metadata_summary: Dict[str, Any] = Field(
        default_factory=lambda: {
            'database': '',
            'table_count': 0,
            'tables': [],
            'has_more_tables': False
        }
    )  # 元数据摘要信息，使用default_factory提供默认值
    table_descriptions: Dict[str, str] = Field(default_factory=dict, description="表描述信息")
    column_descriptions: Dict[str, str] = Field(default_factory=dict, description="列描述信息")
    accessible_roles: List[str] = Field(default_factory=lambda: ["admin"], description="可访问此数据库的角色列表")
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    
    class Config:
        orm_mode = True
        
    @classmethod
    def from_orm(cls, obj):
        """从ORM对象创建响应模型，并处理敏感信息"""
        # 创建一个没有敏感信息的配置副本
        sanitized_config = {}
        if hasattr(obj, 'config') and obj.config:
            sanitized_config = obj.config.copy()
            # 移除密码字段
            for key in list(sanitized_config.keys()):
                if 'password' in key.lower() or 'secret' in key.lower() or 'key' in key.lower():
                    sanitized_config[key] = '******'  # 用星号替换敏感信息
        
        # 创建元数据摘要 - 使用默认空对象
        metadata_summary = {
            'database': '',
            'table_count': 0,
            'tables': [],
            'has_more_tables': False
        }
        
        # 尝试从缓存生成摘要
        if hasattr(obj, 'metadata_cache') and obj.metadata_cache:
            try:
                metadata_summary = {
                    'database': obj.metadata_cache.get('database', ''),
                    'table_count': obj.metadata_cache.get('table_count', 0),
                    'tables': list(obj.metadata_cache.get('tables', {}).keys())[:10],  # 只显示前10个表
                    'has_more_tables': len(obj.metadata_cache.get('tables', {})) > 10,
                }
            except Exception:
                # 如果解析失败，使用错误信息
                metadata_summary = {'error': 'Failed to parse metadata'}
        
        # 创建新对象并设置属性
        instance = super().from_orm(obj)
        instance.config = sanitized_config
        instance.metadata_summary = metadata_summary  # 确保总是设置metadata_summary
        if obj.table_descriptions is None:
            instance.table_descriptions = {}
        if obj.column_descriptions is None:
            instance.column_descriptions = {}
        if obj.accessible_roles is None:
            instance.accessible_roles = ["admin"]
        return instance


class DatabaseConnectionList(BaseModel):
    """
    数据库连接列表项响应模型
    
    用于列表显示的简化数据库连接信息
    """
    id: int
    name: str
    description: str
    database_type: DatabaseType
    config: Dict[str, Any]  # 添加config字段，确保与前端期望的结构一致
    connection_status: ConnectionStatus
    read_only: bool
    last_connected_at: Optional[datetime]
    created_at: Optional[datetime]
    
    class Config:
        orm_mode = True


class ConnectionTestResponse(BaseModel):
    """
    连接测试响应模型
    
    用于返回连接测试结果的响应数据结构
    """
    success: bool
    message: str
    details: Optional[Dict[str, Any]] = None


class DatabaseMetadataResponse(BaseModel):
    """
    数据库元数据响应模型
    
    用于返回数据库元数据的响应数据结构
    """
    database: str
    tables: Dict[str, Any]
    table_count: int
    updated_at: Optional[datetime]
    
    class Config:
        orm_mode = True 