from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta

from sqlmodel import select, Session, desc, or_, col

from app.models.database_query_history import DatabaseQueryHistory
from app.repositories.base_repo import BaseRepo

"""
数据库查询历史仓库模块

提供对数据库查询历史的存储、检索和分析功能
"""


class DatabaseQueryHistoryRepo(BaseRepo):
    """
    数据库查询历史仓库
    
    管理数据库查询历史的各种操作，包括存储、检索和分析
    """
    model_cls = DatabaseQueryHistory
    
    def create(self, session: Session, history: DatabaseQueryHistory) -> DatabaseQueryHistory:
        """
        创建新的查询历史记录
        
        Args:
            session: 数据库会话
            history: 查询历史对象
            
        Returns:
            DatabaseQueryHistory: 已创建的查询历史对象
        """
        session.add(history)
        session.commit()
        session.refresh(history)
        return history
    
    def get_by_chat_id(
        self, 
        session: Session, 
        chat_id: UUID, 
        limit: int = 20, 
        offset: int = 0
    ) -> List[DatabaseQueryHistory]:
        """
        获取指定对话的查询历史
        
        Args:
            session: 数据库会话
            chat_id: 对话ID
            limit: 返回结果数量限制
            offset: 分页偏移量
            
        Returns:
            List[DatabaseQueryHistory]: 查询历史列表
        """
        return session.exec(
            select(DatabaseQueryHistory)
            .where(DatabaseQueryHistory.chat_id == chat_id)
            .order_by(desc(DatabaseQueryHistory.executed_at))
            .offset(offset)
            .limit(limit)
        ).all()
    
    def get_by_user_id(
        self, 
        session: Session, 
        user_id: UUID, 
        limit: int = 20, 
        offset: int = 0
    ) -> List[DatabaseQueryHistory]:
        """
        获取用户的查询历史
        
        Args:
            session: 数据库会话
            user_id: 用户ID
            limit: 返回结果数量限制
            offset: 分页偏移量
            
        Returns:
            List[DatabaseQueryHistory]: 查询历史列表
        """
        return session.exec(
            select(DatabaseQueryHistory)
            .where(DatabaseQueryHistory.user_id == user_id)
            .order_by(desc(DatabaseQueryHistory.executed_at))
            .offset(offset)
            .limit(limit)
        ).all()
    
    def get_recent_queries_in_chat(
        self, 
        session: Session, 
        chat_id: UUID, 
        hours: int = 24,
        limit: int = 5,
        since: Optional[datetime] = None
    ) -> List[DatabaseQueryHistory]:
        """
        获取对话中最近的查询记录
        
        Args:
            session: 数据库会话
            chat_id: 对话ID
            hours: 查询时间范围（小时）
            limit: 返回结果数量限制
            since: 指定开始时间（可选，如果提供则优先于hours参数）
            
        Returns:
            List[DatabaseQueryHistory]: 查询历史列表
        """
        time_threshold = since if since else datetime.now() - timedelta(hours=hours)
        return session.exec(
            select(DatabaseQueryHistory)
            .where(
                DatabaseQueryHistory.chat_id == chat_id,
                DatabaseQueryHistory.executed_at >= time_threshold
            )
            .order_by(desc(DatabaseQueryHistory.executed_at))
            .limit(limit)
        ).all()
    
    def get_by_database_connection(
        self, 
        session: Session, 
        connection_id: int, 
        limit: int = 20, 
        offset: int = 0
    ) -> List[DatabaseQueryHistory]:
        """
        获取指定数据库连接的查询历史
        
        Args:
            session: 数据库会话
            connection_id: 数据库连接ID
            limit: 返回结果数量限制
            offset: 分页偏移量
            
        Returns:
            List[DatabaseQueryHistory]: 查询历史列表
        """
        return session.exec(
            select(DatabaseQueryHistory)
            .where(DatabaseQueryHistory.connection_id == connection_id)
            .order_by(desc(DatabaseQueryHistory.executed_at))
            .offset(offset)
            .limit(limit)
        ).all()
    
    def search_by_content(
        self, 
        session: Session, 
        search_term: str, 
        limit: int = 20, 
        offset: int = 0
    ) -> List[DatabaseQueryHistory]:
        """
        根据内容搜索查询历史
        
        Args:
            session: 数据库会话
            search_term: 搜索关键词
            limit: 返回结果数量限制
            offset: 分页偏移量
            
        Returns:
            List[DatabaseQueryHistory]: 查询历史列表
        """
        return session.exec(
            select(DatabaseQueryHistory)
            .where(
                or_(
                    col(DatabaseQueryHistory.question).contains(search_term),
                    col(DatabaseQueryHistory.query).contains(search_term),
                    col(DatabaseQueryHistory.connection_name).contains(search_term)
                )
            )
            .order_by(desc(DatabaseQueryHistory.executed_at))
            .offset(offset)
            .limit(limit)
        ).all()
    
    def get_query_stats_by_chat(
        self, 
        session: Session, 
        chat_id: UUID
    ) -> Dict[str, Any]:
        """
        获取对话的查询统计信息
        
        Args:
            session: 数据库会话
            chat_id: 对话ID
            
        Returns:
            Dict[str, Any]: 统计信息
        """
        # 查询总次数
        total_queries = self.count_queries_by_chat(session, chat_id)
        
        # 成功查询次数
        successful_queries = session.exec(
            select(DatabaseQueryHistory)
            .where(
                DatabaseQueryHistory.chat_id == chat_id,
                DatabaseQueryHistory.is_successful == True
            )
        ).count()
        
        # 获取使用的数据库列表
        db_connections = session.exec(
            select(
                DatabaseQueryHistory.connection_id,
                DatabaseQueryHistory.connection_name
            )
            .where(DatabaseQueryHistory.chat_id == chat_id)
            .distinct()
        ).all()
        
        databases_used = [{"id": db[0], "name": db[1]} for db in db_connections]
        
        return {
            "total_queries": total_queries,
            "successful_queries": successful_queries,
            "success_rate": (successful_queries / total_queries) if total_queries > 0 else 0,
            "databases_used": databases_used
        }
    
    def count_queries_by_chat(
        self,
        session: Session,
        chat_id: UUID
    ) -> int:
        """
        计算指定对话中的查询总数
        
        Args:
            session: 数据库会话
            chat_id: 对话ID
            
        Returns:
            int: 查询总数
        """
        result = session.exec(
            select(DatabaseQueryHistory)
            .where(DatabaseQueryHistory.chat_id == chat_id)
        )
        return len(result.all())
    
    def update_user_feedback(
        self, 
        session: Session, 
        query_id: int, 
        feedback_score: int, 
        feedback_comments: Optional[str] = None
    ) -> Optional[DatabaseQueryHistory]:
        """
        更新用户对查询结果的反馈
        
        Args:
            session: 数据库会话
            query_id: 查询历史ID
            feedback_score: 反馈评分(1-5)
            feedback_comments: 反馈评论
            
        Returns:
            Optional[DatabaseQueryHistory]: 更新后的查询历史对象
        """
        history = session.get(DatabaseQueryHistory, query_id)
        if not history:
            return None
        
        history.user_feedback = feedback_score
        history.user_feedback_comments = feedback_comments
        
        session.add(history)
        session.commit()
        session.refresh(history)
        
        return history 