import os
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding


class AESCipher:
    """
    AES加密解密工具类

    使用AES算法和CFB模式实现字符串的加密和解密功能
    支持PKCS7填充以处理不完整的数据块
    """

    def __init__(self, key: bytes) -> None:
        """
        初始化AES加密器

        参数:
            key: 加密密钥，必须是16、24或32字节(对应AES-128, AES-192或AES-256)
        """
        self.key = key
        self.backend = default_backend()

    def encrypt(self, plain_text: str) -> bytes:
        """
        加密明文字符串

        使用AES-CFB模式加密文本，并添加PKCS7填充

        参数:
            plain_text: 要加密的明文字符串

        返回:
            bytes: 加密后的字节序列，包含IV(初始化向量)和加密数据
        """
        # 生成随机初始化向量
        iv = os.urandom(16)
        cipher = Cipher(algorithms.AES(self.key), modes.CFB(iv), backend=self.backend)
        encryptor = cipher.encryptor()

        # 使用填充处理最后一个数据块
        padder = padding.PKCS7(algorithms.AES.block_size).padder()
        padded_data = padder.update(plain_text.encode()) + padder.finalize()
        encrypted = encryptor.update(padded_data) + encryptor.finalize()
        return iv + encrypted

    def decrypt(self, encrypted_text: bytes) -> str:
        """
        解密加密的字节数据

        使用AES-CFB模式解密数据，并移除PKCS7填充

        参数:
            encrypted_text: 加密的字节数据，包含IV和加密内容

        返回:
            str: 解密后的明文字符串
        """
        # 提取初始化向量和加密数据
        iv = encrypted_text[:16]
        encrypted_data = encrypted_text[16:]

        cipher = Cipher(algorithms.AES(self.key), modes.CFB(iv), backend=self.backend)
        decryptor = cipher.decryptor()

        # 移除填充
        decrypted_padded = decryptor.update(encrypted_data) + decryptor.finalize()
        unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
        decrypted = unpadder.update(decrypted_padded) + unpadder.finalize()
        return decrypted.decode()
