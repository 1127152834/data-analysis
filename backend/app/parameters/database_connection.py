"""
数据库连接参数模块

定义了各种数据库连接的参数类，用于管理数据库连接的配置信息
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, ClassVar, List

from app.parameters import BaseParameters


@dataclass
class BaseDatabaseParameters(BaseParameters):
    """
    数据库连接参数基类
    
    所有数据库连接参数类的基类，提供基本的连接参数管理功能
    """
    host: str  # 主机地址
    user: str  # 用户名
    database: str  # 数据库名称
    port: int  # 端口号
    password: str = ""  # 密码，可选，默认为空字符串
    
    # 指定哪些字段应该加密存储
    SENSITIVE_FIELDS: ClassVar[List[str]] = ["password"]
    
    def get_connection_string(self) -> str:
        """
        获取数据库连接字符串
        
        由子类实现具体的连接字符串生成逻辑
        
        返回:
            str: 数据库连接字符串
        """
        raise NotImplementedError("子类必须实现此方法")
    
    def get_connection_args(self) -> Dict[str, Any]:
        """
        获取数据库连接参数
        
        返回用于建立数据库连接的参数字典
        
        返回:
            Dict[str, Any]: 连接参数字典
        """
        return {
            "host": self.host,
            "port": self.port,
            "user": self.user,
            "password": self.password,
            "database": self.database,
        }


@dataclass
class MySQLParameters(BaseDatabaseParameters):
    """
    MySQL数据库连接参数
    
    管理MySQL数据库连接的配置信息
    """
    host: str  # 主机地址
    user: str  # 用户名
    database: str  # 数据库名称
    port: int = 3306  # MySQL默认端口
    password: str = ""  # 密码，可选，默认为空字符串
    charset: str = "utf8mb4"  # 默认字符集
    pool_size: int = 5  # 连接池大小
    pool_recycle: int = 300  # 连接回收时间（秒）
    ssl_mode: Optional[str] = None  # SSL模式
    
    def get_connection_string(self) -> str:
        """
        获取MySQL连接字符串
        
        生成用于连接MySQL数据库的连接字符串
        
        返回:
            str: MySQL连接字符串
        """
        connection_str = f"mysql+pymysql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
        if self.charset:
            connection_str += f"?charset={self.charset}"
        return connection_str


@dataclass
class PostgreSQLParameters(BaseDatabaseParameters):
    """
    PostgreSQL数据库连接参数
    
    管理PostgreSQL数据库连接的配置信息
    """
    host: str  # 主机地址
    user: str  # 用户名
    database: str  # 数据库名称 
    port: int = 5432  # PostgreSQL默认端口
    password: str = ""  # 密码，可选，默认为空字符串
    schema: Optional[str] = None  # 模式名
    pool_size: int = 5  # 连接池大小
    pool_recycle: int = 300  # 连接回收时间（秒）
    sslmode: Optional[str] = None  # SSL模式
    
    def get_connection_string(self) -> str:
        """
        获取PostgreSQL连接字符串
        
        生成用于连接PostgreSQL数据库的连接字符串
        
        返回:
            str: PostgreSQL连接字符串
        """
        connection_str = f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
        params = []
        if self.schema:
            params.append(f"options=-csearch_path={self.schema}")
        if self.sslmode:
            params.append(f"sslmode={self.sslmode}")
        
        if params:
            connection_str += "?" + "&".join(params)
        return connection_str


@dataclass
class MongoDBParameters(BaseDatabaseParameters):
    """
    MongoDB数据库连接参数
    
    管理MongoDB数据库连接的配置信息
    """
    host: str  # 主机地址
    user: str  # 用户名
    database: str  # 数据库名称
    port: int = 27017  # MongoDB默认端口
    password: str = ""  # 密码，可选，默认为空字符串
    auth_source: Optional[str] = None  # 认证数据库
    auth_mechanism: Optional[str] = None  # 认证机制
    ssl: bool = False  # 是否使用SSL
    
    def get_connection_string(self) -> str:
        """
        获取MongoDB连接字符串
        
        生成用于连接MongoDB数据库的连接字符串
        
        返回:
            str: MongoDB连接字符串
        """
        auth_part = f"{self.user}:{self.password}@" if self.user else ""
        connection_str = f"mongodb://{auth_part}{self.host}:{self.port}/{self.database}"
        
        params = []
        if self.auth_source:
            params.append(f"authSource={self.auth_source}")
        if self.auth_mechanism:
            params.append(f"authMechanism={self.auth_mechanism}")
        if self.ssl:
            params.append("ssl=true")
            
        if params:
            connection_str += "?" + "&".join(params)
        return connection_str


@dataclass
class SQLServerParameters(BaseDatabaseParameters):
    """
    SQL Server数据库连接参数
    
    管理SQL Server数据库连接的配置信息
    """
    host: str  # 主机地址
    user: str  # 用户名
    database: str  # 数据库名称
    port: int = 1433  # SQL Server默认端口
    password: str = ""  # 密码，可选，默认为空字符串
    driver: str = "ODBC Driver 17 for SQL Server"  # 默认驱动
    trust_server_certificate: bool = False  # 是否信任服务器证书
    encrypt: bool = True  # 是否加密连接
    
    def get_connection_string(self) -> str:
        """
        获取SQL Server连接字符串
        
        生成用于连接SQL Server数据库的连接字符串
        
        返回:
            str: SQL Server连接字符串
        """
        connection_str = f"mssql+pyodbc://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
        
        params = [f"driver={self.driver}"]
        if self.trust_server_certificate:
            params.append("TrustServerCertificate=yes")
        if not self.encrypt:
            params.append("encrypt=no")
            
        connection_str += "?" + "&".join(params)
        return connection_str


@dataclass
class OracleParameters(BaseDatabaseParameters):
    """
    Oracle数据库连接参数
    
    管理Oracle数据库连接的配置信息
    """
    host: str  # 主机地址
    user: str  # 用户名
    database: str  # 数据库名称
    port: int = 1521  # Oracle默认端口
    password: str = ""  # 密码，可选，默认为空字符串
    service_name: Optional[str] = None  # 服务名
    sid: Optional[str] = None  # SID
    mode: Optional[str] = None  # 连接模式
    encoding: str = "UTF-8"  # 编码
    
    def get_connection_string(self) -> str:
        """
        获取Oracle连接字符串
        
        生成用于连接Oracle数据库的连接字符串
        
        返回:
            str: Oracle连接字符串
        """
        dsn_part = ""
        if self.service_name:
            dsn_part = f"?service_name={self.service_name}"
        elif self.sid:
            dsn_part = f"?sid={self.sid}"
            
        connection_str = f"oracle+cx_oracle://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}{dsn_part}"
        
        params = []
        if self.mode:
            params.append(f"mode={self.mode}")
        if self.encoding:
            params.append(f"encoding={self.encoding}")
            
        if params:
            if dsn_part:
                connection_str += "&" + "&".join(params)
            else:
                connection_str += "?" + "&".join(params)
                
        return connection_str 