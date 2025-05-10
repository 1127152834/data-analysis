import json
from uuid import UUID
from datetime import datetime
from typing import Optional
from sqlmodel import Field, DateTime, func, SQLModel
from sqlalchemy.types import TypeDecorator, LargeBinary, Integer

from app.utils.uuid6 import uuid7
from app.utils.aes import AESCipher
from app.core.config import settings

"""
数据库模型基类模块

提供所有数据库模型的公共基类和共享工具类，
包括UUID主键模型基类、可更新时间戳模型基类、
加密数据列类型和枚举类型处理器等
"""


class UUIDBaseModel(SQLModel):
    """
    UUID主键模型基类

    为模型提供UUID主键字段，默认使用UUID版本7生成
    所有需要UUID主键的模型都应继承此类
    """

    id: UUID = Field(
        default_factory=uuid7,  # 使用UUID7生成ID
        primary_key=True,  # 设为主键
        index=True,  # 创建索引
        nullable=False,  # 不允许为空
    )


class UpdatableBaseModel(SQLModel):
    """
    可更新时间戳模型基类

    为模型提供自动维护的创建时间和更新时间字段
    所有需要跟踪创建和更新时间的模型都应继承此类
    """

    # 使用sa_type而不是sa_column，参考 https://github.com/tiangolo/sqlmodel/discussions/743
    created_at: Optional[datetime] = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={"server_default": func.now()},  # 创建时自动设置为当前时间
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={
            "server_default": func.now(),
            "onupdate": func.now(),
        },  # 更新时自动更新为当前时间
    )


def get_aes_key() -> bytes:
    """
    获取AES加密密钥

    从应用配置的SECRET_KEY派生AES加密密钥

    返回:
        bytes: 长度为32字节的AES密钥
    """
    return settings.SECRET_KEY.encode()[:32]


class AESEncryptedColumn(TypeDecorator):
    """
    AES加密列类型

    用于在数据库中存储加密数据的列类型
    会自动对Python对象进行JSON序列化和AES加密存储，
    从数据库读取时会自动解密和反序列化为原始对象
    """

    impl = LargeBinary  # 底层实现为二进制数据类型

    def process_bind_param(self, value, dialect):
        """
        处理写入数据库的值

        将Python对象转换为加密的二进制数据

        参数:
            value: 要存储的Python对象
            dialect: 数据库方言

        返回:
            bytes: 加密后的二进制数据
        """
        if value is not None:
            json_str = json.dumps(value)
            return AESCipher(get_aes_key()).encrypt(json_str)
        return value

    def process_result_value(self, value, dialect):
        """
        处理从数据库读取的值

        将加密的二进制数据解密并转换为Python对象

        参数:
            value: 从数据库读取的加密二进制数据
            dialect: 数据库方言

        返回:
            任意Python对象: 解密并反序列化后的原始对象
        """
        if value is not None:
            json_str = AESCipher(get_aes_key()).decrypt(value)
            return json.loads(json_str)
        return value


class IntEnumType(TypeDecorator):
    """
    整数枚举类型

    处理数据库中的整数值与Python枚举类型之间的转换

    这替代了之前的SmallInteger实现，以解决Pydantic序列化警告问题。
    使用SmallInteger时，SQLAlchemy会从数据库返回原始整数（例如0或1），
    而Pydantic验证则期望适当的枚举类型，从而导致验证警告。
    """

    impl = Integer  # 底层实现为整数类型

    def __init__(self, enum_class, *args, **kwargs):
        """
        初始化整数枚举类型

        参数:
            enum_class: 要使用的枚举类
            *args, **kwargs: 传递给父类的参数
        """
        super().__init__(*args, **kwargs)
        self.enum_class = enum_class

    def process_bind_param(self, value, dialect):
        """
        处理写入数据库的值

        将枚举对象转换为整数值

        参数:
            value: 枚举对象
            dialect: 数据库方言

        返回:
            int: 对应的整数值

        异常:
            ValueError: 如果提供的值不是有效的枚举对象
        """
        # 枚举 -> 整数
        if isinstance(value, self.enum_class):
            return value.value
        elif value is None:
            return None
        raise ValueError(f"Invalid value for {self.enum_class}: {value}")

    def process_result_value(self, value, dialect):
        """
        处理从数据库读取的值

        将整数值转换为枚举对象

        参数:
            value: 整数值
            dialect: 数据库方言

        返回:
            枚举对象: 对应的枚举对象
        """
        # 整数 -> 枚举
        if value is not None:
            return self.enum_class(value)
        return None
