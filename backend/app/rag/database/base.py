"""
数据库连接器基础模块

定义了所有数据库连接器共享的基类和接口
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass


@dataclass
class ConnectionTestResult:
    """
    连接测试结果
    
    存储连接测试的结果信息
    """
    success: bool  # 测试是否成功
    message: str  # 结果消息
    details: Optional[Dict[str, Any]] = None  # 详细信息（如版本、配置等）


class BaseConnector(ABC):
    """
    数据库连接器基类
    
    所有数据库连接器的抽象基类，定义了连接器必须实现的接口
    """
    
    @abstractmethod
    def connect(self) -> bool:
        """
        建立数据库连接
        
        尝试建立与数据库的连接
        
        返回:
            bool: 连接是否成功
        """
        pass
    
    @abstractmethod
    def test_connection(self) -> ConnectionTestResult:
        """
        测试数据库连接
        
        测试与数据库的连接并返回结果
        
        返回:
            ConnectionTestResult: 连接测试结果
        """
        pass
    
    @abstractmethod
    def get_metadata(self) -> Dict[str, Any]:
        """
        获取数据库元数据
        
        获取数据库的结构信息，如表、列、约束等
        
        返回:
            Dict[str, Any]: 数据库元数据
        """
        pass
    
    @abstractmethod
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """
        执行查询
        
        执行SQL查询并返回结果
        
        参数:
            query: SQL查询字符串
            params: 查询参数
            
        返回:
            Tuple[List[Dict[str, Any]], Optional[str]]: 查询结果和错误信息（如果有）
        """
        pass
    
    @abstractmethod
    def close(self) -> None:
        """
        关闭连接
        
        关闭与数据库的连接并释放资源
        """
        pass
    
    def __enter__(self):
        """
        上下文管理器进入方法
        
        实现上下文管理协议，允许使用with语句
        
        返回:
            BaseConnector: 连接器实例
        """
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        上下文管理器退出方法
        
        实现上下文管理协议，确保连接被正确关闭
        
        参数:
            exc_type: 异常类型
            exc_val: 异常值
            exc_tb: 异常回溯
        """
        self.close() 