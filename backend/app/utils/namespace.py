from typing import Optional

"""
命名空间工具模块

提供操作和格式化命名空间的工具函数
"""


def format_namespace(namespace: Optional[str] = None) -> str:
    """
    格式化命名空间字符串

    将命名空间中的连字符(-)替换为下划线(_)，使其符合Python变量命名规范

    参数:
        namespace: 需要格式化的命名空间字符串，如果为None则返回空字符串

    返回:
        str: 格式化后的命名空间字符串
    """
    return namespace.replace("-", "_") if namespace else ""
