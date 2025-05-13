"""
参数模块

包含各种配置参数类，用于管理系统不同部分的配置信息
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass
class BaseParameters:
    """
    基础参数类

    所有参数类的基类，提供基本的参数管理功能
    """

    def to_dict(self) -> Dict[str, Any]:
        """
        将参数转换为字典形式

        返回:
            Dict[str, Any]: 包含所有参数的字典
        """
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseParameters":
        """
        从字典创建参数对象

        参数:
            data: 参数字典

        返回:
            BaseParameters: 创建的参数对象
        """
        return cls(
            **{
                k: v
                for k, v in data.items()
                if not k.startswith("_") and k in cls.__annotations__
            }
        )
