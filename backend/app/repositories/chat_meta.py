from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta

from sqlmodel import select, Session, or_, desc, update

from app.models.chat_meta import ChatMeta
from app.repositories.base_repo import BaseRepo

"""
聊天元数据仓库模块

提供对聊天元数据的存储、检索和管理功能
"""


class ChatMetaRepo(BaseRepo):
    """
    聊天元数据仓库
    
    管理聊天元数据的各种操作，包括存储、检索和更新
    """
    model_cls = ChatMeta
    
    def create(self, session: Session, meta: ChatMeta) -> ChatMeta:
        """
        创建新的聊天元数据记录
        
        Args:
            session: 数据库会话
            meta: 聊天元数据对象
            
        Returns:
            ChatMeta: 已创建的元数据对象
        """
        session.add(meta)
        session.commit()
        session.refresh(meta)
        return meta
    
    def get_by_chat_id_and_key(
        self, 
        session: Session, 
        chat_id: UUID, 
        key: str
    ) -> Optional[ChatMeta]:
        """
        获取指定聊天和键的元数据
        
        Args:
            session: 数据库会话
            chat_id: 聊天ID
            key: 元数据键名
            
        Returns:
            Optional[ChatMeta]: 找到的元数据对象，如果不存在则返回None
        """
        return session.exec(
            select(ChatMeta)
            .where(ChatMeta.chat_id == chat_id, ChatMeta.key == key)
            .limit(1)
        ).first()
    
    def get_by_chat_id(
        self, 
        session: Session, 
        chat_id: UUID,
        include_expired: bool = False
    ) -> List[ChatMeta]:
        """
        获取指定聊天的所有元数据
        
        Args:
            session: 数据库会话
            chat_id: 聊天ID
            include_expired: 是否包含已过期的元数据
            
        Returns:
            List[ChatMeta]: 元数据列表
        """
        query = select(ChatMeta).where(ChatMeta.chat_id == chat_id)
        
        # 如果不包含已过期记录，添加过期时间过滤条件
        if not include_expired:
            query = query.where(
                or_(
                    ChatMeta.expires_at.is_(None),
                    ChatMeta.expires_at > datetime.now()
                )
            )
            
        return session.exec(query).all()
    
    def update_value(
        self, 
        session: Session, 
        chat_id: UUID, 
        key: str, 
        value: str,
        expires_in: Optional[timedelta] = None
    ) -> ChatMeta:
        """
        更新或创建聊天元数据值
        
        Args:
            session: 数据库会话
            chat_id: 聊天ID
            key: 元数据键名
            value: 新的元数据值
            expires_in: 过期时间增量，如果提供，元数据将在当前时间加上此增量后过期
            
        Returns:
            ChatMeta: 更新或创建的元数据对象
        """
        # 计算过期时间
        expires_at = None
        if expires_in:
            expires_at = datetime.now() + expires_in
            
        # 查找现有记录
        meta = self.get_by_chat_id_and_key(session, chat_id, key)
        
        if meta:
            # 更新现有记录
            meta.value = value
            meta.expires_at = expires_at
            meta.updated_at = datetime.now()
            session.add(meta)
            session.commit()
            session.refresh(meta)
            return meta
        else:
            # 创建新记录
            new_meta = ChatMeta(
                chat_id=chat_id,
                key=key,
                value=value,
                expires_at=expires_at
            )
            return self.create(session, new_meta)
    
    def delete(
        self, 
        session: Session, 
        chat_id: UUID, 
        key: Optional[str] = None
    ) -> int:
        """
        删除聊天元数据
        
        Args:
            session: 数据库会话
            chat_id: 聊天ID
            key: 元数据键名，如果为None，则删除该聊天的所有元数据
            
        Returns:
            int: 删除的记录数
        """
        query = select(ChatMeta).where(ChatMeta.chat_id == chat_id)
        
        if key:
            query = query.where(ChatMeta.key == key)
            
        metas = session.exec(query).all()
        count = len(metas)
        
        for meta in metas:
            session.delete(meta)
            
        session.commit()
        return count
    
    def cleanup_expired(self, session: Session) -> int:
        """
        清理已过期的元数据记录
        
        Args:
            session: 数据库会话
            
        Returns:
            int: 删除的记录数
        """
        now = datetime.now()
        query = select(ChatMeta).where(
            ChatMeta.expires_at.is_not(None),
            ChatMeta.expires_at < now
        )
        
        expired_metas = session.exec(query).all()
        count = len(expired_metas)
        
        for meta in expired_metas:
            session.delete(meta)
            
        session.commit()
        return count 