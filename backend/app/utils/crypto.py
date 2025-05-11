"""
加密工具模块

提供用于加密和解密敏感信息的函数
"""

import json
from typing import Dict, Any, Union, List

from app.utils.aes import AESCipher
from app.core.config import settings


def get_crypto_key() -> bytes:
    """
    获取加密密钥
    
    从应用设置中获取用于加密和解密的密钥
    
    返回:
        bytes: 加密密钥
    """
    return settings.SECRET_KEY.encode()[:32]


def encrypt_value(value: str) -> bytes:
    """
    加密单个值
    
    使用AES算法加密敏感信息
    
    参数:
        value: 要加密的值
        
    返回:
        bytes: 加密后的数据
    """
    if not value:
        return b""
    return AESCipher(get_crypto_key()).encrypt(value)


def decrypt_value(encrypted_value: bytes) -> str:
    """
    解密单个值
    
    使用AES算法解密敏感信息
    
    参数:
        encrypted_value: 加密的数据
        
    返回:
        str: 解密后的值
    """
    if not encrypted_value:
        return ""
    return AESCipher(get_crypto_key()).decrypt(encrypted_value)


def encrypt_dict_values(data: Dict[str, Any], sensitive_fields: List[str]) -> Dict[str, Any]:
    """
    加密字典中的敏感字段
    
    遍历字典，加密指定的敏感字段
    
    参数:
        data: 包含敏感信息的字典
        sensitive_fields: 需要加密的字段列表
        
    返回:
        Dict[str, Any]: 处理后的字典，敏感字段已加密
    """
    result = data.copy()
    for field in sensitive_fields:
        if field in result and result[field]:
            # 将加密后的字节转换为字符串以便存储在JSON中
            result[field + "_encrypted"] = encrypt_value(str(result[field])).hex()
            # 移除原始敏感字段
            del result[field]
    return result


def decrypt_dict_values(data: Dict[str, Any], sensitive_fields: List[str]) -> Dict[str, Any]:
    """
    解密字典中的敏感字段
    
    遍历字典，解密指定的敏感字段
    
    参数:
        data: 包含加密信息的字典
        sensitive_fields: 已加密的字段列表
        
    返回:
        Dict[str, Any]: 处理后的字典，敏感字段已解密
    """
    result = data.copy()
    for field in sensitive_fields:
        encrypted_field = field + "_encrypted"
        if encrypted_field in result and result[encrypted_field]:
            # 将十六进制字符串转换回字节，然后解密
            result[field] = decrypt_value(bytes.fromhex(result[encrypted_field]))
            # 移除加密字段
            del result[encrypted_field]
    return result 