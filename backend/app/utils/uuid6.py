r"""UUID草案版本对象（通用唯一标识符）。
本模块提供了生成UUID版本6和版本7的函数uuid6()和uuid7()，
按照https://github.com/uuid6/uuid6-ietf-draft中的规范实现。

仓库：https://github.com/oittaa/uuid6-python

复制自：https://github.com/jonra1993/fastapi-alembic-sqlmodel-async/blob/main/backend/app/app/utils/uuid6.py
"""

import secrets
import time
import uuid


class UUID(uuid.UUID):
    r"""UUID草案版本对象

    扩展标准uuid.UUID类，增加对UUID版本6和版本7的支持
    """

    def __init__(
        self,
        hex: str = None,
        bytes: bytes = None,
        bytes_le: bytes = None,
        fields: tuple[int, int, int, int, int, int] = None,
        int: int = None,
        version: int = None,
        *,
        is_safe=uuid.SafeUUID.unknown,
    ) -> None:
        r"""
        创建一个UUID对象

        参数:
            hex: 十六进制字符串表示的UUID
            bytes: 16字节表示的UUID
            bytes_le: 小端字节序表示的UUID
            fields: 包含6个整数的元组表示的UUID
            int: 整数表示的UUID
            version: UUID版本号(6或7)
            is_safe: 安全标识

        异常:
            ValueError: 当整数值超出范围或版本号非法时
        """

        if int is None or [hex, bytes, bytes_le, fields].count(None) != 4:
            super().__init__(
                hex=hex,
                bytes=bytes,
                bytes_le=bytes_le,
                fields=fields,
                int=int,
                version=version,
                is_safe=is_safe,
            )
        if not 0 <= int < 1 << 128:
            raise ValueError("int is out of range (need a 128-bit value)")
        if version is not None:
            if not 6 <= version <= 7:
                raise ValueError("illegal version number")
            # 设置变体为RFC 4122
            int &= ~(0xC000 << 48)
            int |= 0x8000 << 48
            # 设置版本号
            int &= ~(0xF000 << 64)
            int |= version << 76
        super().__init__(int=int, is_safe=is_safe)

    @property
    def subsec(self) -> int:
        """
        获取子秒部分

        返回UUID中表示时间戳亚毫秒部分的值

        返回:
            int: 子秒部分的值
        """
        return ((self.int >> 64) & 0x0FFF) << 8 | ((self.int >> 54) & 0xFF)

    @property
    def time(self) -> int:
        """
        获取时间戳

        根据UUID版本解析并返回时间戳值

        返回:
            int: 解析后的时间戳

        注意:
            版本6返回自UUID时代以来的100纳秒间隔数
            版本7返回自Unix纪元以来的毫秒数
        """
        if self.version == 6:
            return (
                (self.time_low << 28)
                | (self.time_mid << 12)
                | (self.time_hi_version & 0x0FFF)
            )
        if self.version == 7:
            return (self.int >> 80) * 10**6 + _subsec_decode(self.subsec)
        return super().time


def _subsec_decode(value: int) -> int:
    """
    解码子秒值为微秒

    将UUID中的子秒值转换为微秒

    参数:
        value: 子秒编码值

    返回:
        int: 对应的微秒值
    """
    return -(-value * 10**6 // 2**20)


def _subsec_encode(value: int) -> int:
    """
    编码微秒为子秒值

    将微秒值编码为UUID中的子秒格式

    参数:
        value: 微秒值

    返回:
        int: 编码后的子秒值
    """
    return value * 2**20 // 10**6


_last_v6_timestamp = None
_last_v7_timestamp = None


def uuid6(clock_seq: int = None) -> UUID:
    """
    生成UUID版本6

    UUID版本6是UUID版本1的字段兼容版本，重新排序以改善数据库局部性。
    预计UUID版本6将主要用于存在现有v1 UUID的上下文中。
    不涉及遗留UUIDv1的系统应考虑使用UUIDv7。

    参数:
        clock_seq: 时钟序列号，如果未提供则随机生成

    返回:
        UUID: 新生成的UUID版本6对象
    """

    global _last_v6_timestamp

    nanoseconds = time.time_ns()
    # 0x01b21dd213814000是UUID纪元1582-10-15 00:00:00和
    # Unix纪元1970-01-01 00:00:00之间的100纳秒间隔数。
    timestamp = nanoseconds // 100 + 0x01B21DD213814000
    if _last_v6_timestamp is not None and timestamp <= _last_v6_timestamp:
        timestamp = _last_v6_timestamp + 1
    _last_v6_timestamp = timestamp
    if clock_seq is None:
        clock_seq = secrets.randbits(14)  # 使用随机数代替稳定存储
    node = secrets.randbits(48)
    time_high_and_time_mid = (timestamp >> 12) & 0xFFFFFFFFFFFF
    time_low_and_version = timestamp & 0x0FFF
    uuid_int = time_high_and_time_mid << 80
    uuid_int |= time_low_and_version << 64
    uuid_int |= (clock_seq & 0x3FFF) << 48
    uuid_int |= node
    return UUID(int=uuid_int, version=6)


def uuid7() -> UUID:
    """
    生成UUID版本7

    UUID版本7具有基于广泛实现且众所周知的Unix纪元时间戳源的时序值字段，
    表示自1970年1月1日午夜UTC以来的毫秒数（不包括闰秒）。
    与版本1或6相比，具有更好的熵特性。

    如果可能，实现应优先使用UUID版本7而非版本1和6。

    返回:
        UUID: 新生成的UUID版本7对象
    """

    global _last_v7_timestamp

    nanoseconds = time.time_ns()
    if _last_v7_timestamp is not None and nanoseconds <= _last_v7_timestamp:
        nanoseconds = _last_v7_timestamp + 1
    _last_v7_timestamp = nanoseconds
    timestamp_ms, timestamp_ns = divmod(nanoseconds, 10**6)
    subsec = _subsec_encode(timestamp_ns)
    subsec_a = subsec >> 8
    subsec_b = subsec & 0xFF
    rand = secrets.randbits(54)
    uuid_int = (timestamp_ms & 0xFFFFFFFFFFFF) << 80
    uuid_int |= subsec_a << 64
    uuid_int |= subsec_b << 54
    uuid_int |= rand
    return UUID(int=uuid_int, version=7)
