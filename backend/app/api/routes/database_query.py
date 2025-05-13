"""
数据库查询API路由模块

提供与数据库查询相关的API端点，包括获取可用数据库列表、
查询历史记录和提交用户反馈等功能
"""

import logging
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Query, HTTPException, status
from datetime import datetime, timedelta

from app.api.deps import SessionDep, CurrentUserDep, OptionalUserDep
from app.repositories.database_connection import DatabaseConnectionRepo
from app.repositories.database_query_history import DatabaseQueryHistoryRepo
from app.models.database_connection import DatabaseConnection
from app.models.database_query_history import DatabaseQueryHistory
from app.rag.chat.chat_service import user_can_view_chat

# 响应模型
from pydantic import BaseModel, Field

router = APIRouter()
logger = logging.getLogger(__name__)


class DatabaseConnectionResponse(BaseModel):
    """数据库连接响应模型"""
    id: int
    name: str
    description: Optional[str] = None
    database_type: str
    read_only: bool = True


class DatabaseQueryHistoryResponse(BaseModel):
    """数据库查询历史响应模型"""
    id: int
    chat_id: UUID
    connection_name: str
    database_type: str
    question: str
    query: str
    is_successful: bool
    result_summary: dict = Field(default={})
    result_sample: List[dict] = Field(default=[])
    execution_time_ms: int
    rows_returned: int
    user_feedback: Optional[int] = None
    executed_at: datetime


class DatabaseQueryFeedbackRequest(BaseModel):
    """数据库查询反馈请求模型"""
    feedback_score: int = Field(..., ge=1, le=5, description="反馈评分(1-5)")
    feedback_comments: Optional[str] = None


class QueryStatisticsResponse(BaseModel):
    """查询统计响应模型"""
    total_queries: int
    successful_queries: int
    success_rate: float
    databases_used: List[dict]


@router.get("/database/connections", response_model=List[DatabaseConnectionResponse])
def list_available_databases(
    session: SessionDep,
    user: OptionalUserDep,
):
    """
    获取当前用户可用的数据库列表
    
    返回用户有权访问的数据库连接列表
    """
    try:
        repo = DatabaseConnectionRepo()
        
        # 获取所有活跃的数据库连接
        connections = repo.list_active(session)
        
        # 如果没有活跃的数据库连接，返回空列表
        if not connections:
            return []
        
        # 根据用户角色过滤可访问的数据库连接
        filtered_connections = []
        user_roles = []
        
        # 确定用户角色
        if user:
            if user.is_superuser:
                user_roles.append("admin")
            user_roles.append("user")  # 所有登录用户至少是普通用户
        
        # 如果用户未登录或没有任何角色，则无法访问任何数据库
        if not user_roles:
            return []
        
        # 过滤出用户有权限访问的数据库连接
        for conn in connections:
            # 检查用户角色是否有权限访问
            if conn.accessible_roles and any(role in conn.accessible_roles for role in user_roles):
                filtered_connections.append(conn)
        
        logger.debug(f"用户 {user.id if user else 'anonymous'} 可访问 {len(filtered_connections)} 个数据库连接")
        return filtered_connections
    except Exception as e:
        logger.error(f"获取可用数据库列表失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取数据库列表时发生错误"
        )


@router.get(
    "/chats/{chat_id}/database/queries", 
    response_model=List[DatabaseQueryHistoryResponse]
)
def get_chat_database_queries(
    chat_id: UUID,
    session: SessionDep,
    user: OptionalUserDep,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """
    获取指定聊天的数据库查询历史
    
    返回特定聊天会话中执行的数据库查询历史记录
    """
    from app.repositories import chat_repo
    
    try:
        # 获取聊天对象并检查访问权限
        chat = chat_repo.get(session, chat_id)
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"聊天 {chat_id} 不存在"
            )
            
        if not user_can_view_chat(chat, user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权访问此聊天的查询历史"
            )
            
        # 获取查询历史
        history_repo = DatabaseQueryHistoryRepo()
        query_histories = history_repo.get_by_chat_id(
            session=session,
            chat_id=chat_id,
            limit=limit,
            offset=offset
        )
        
        return query_histories
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取聊天 {chat_id} 的数据库查询历史失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取数据库查询历史时发生错误"
        )


@router.get(
    "/database/queries/recent", 
    response_model=List[DatabaseQueryHistoryResponse]
)
def get_recent_database_queries(
    session: SessionDep,
    user: CurrentUserDep,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """
    获取当前用户最近的数据库查询历史
    
    返回当前用户在所有聊天中执行的最近数据库查询
    """
    try:
        # 获取用户最近的查询历史
        history_repo = DatabaseQueryHistoryRepo()
        query_histories = history_repo.get_by_user_id(
            session=session,
            user_id=user.id,
            limit=limit,
            offset=offset
        )
        
        return query_histories
    except Exception as e:
        logger.error(f"获取用户 {user.id} 的最近数据库查询历史失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取最近数据库查询历史时发生错误"
        )


@router.get(
    "/chats/{chat_id}/database/statistics", 
    response_model=QueryStatisticsResponse
)
def get_chat_database_statistics(
    chat_id: UUID,
    session: SessionDep,
    user: OptionalUserDep,
):
    """
    获取指定聊天的数据库查询统计信息
    
    返回特定聊天会话中数据库查询的统计数据，包括总查询数、成功率等
    """
    from app.repositories import chat_repo
    
    try:
        # 获取聊天对象并检查访问权限
        chat = chat_repo.get(session, chat_id)
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"聊天 {chat_id} 不存在"
            )
            
        if not user_can_view_chat(chat, user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权访问此聊天的查询统计"
            )
            
        # 获取查询统计信息
        history_repo = DatabaseQueryHistoryRepo()
        statistics = history_repo.get_query_stats_by_chat(
            session=session,
            chat_id=chat_id
        )
        
        return statistics
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取聊天 {chat_id} 的数据库查询统计失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取数据库查询统计时发生错误"
        )


@router.put(
    "/database/queries/{query_id}/feedback", 
    status_code=status.HTTP_200_OK
)
def update_query_feedback(
    query_id: int,
    feedback: DatabaseQueryFeedbackRequest,
    session: SessionDep,
    user: CurrentUserDep,
):
    """
    更新数据库查询的用户反馈
    
    允许用户提交对特定数据库查询结果的反馈评分和评论
    """
    try:
        # 获取查询历史记录
        history_repo = DatabaseQueryHistoryRepo()
        query_history = session.get(DatabaseQueryHistory, query_id)
        
        if not query_history:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"查询 {query_id} 不存在"
            )
            
        # 检查用户是否有权更新此查询的反馈
        # 简化实现：只允许原始查询用户或管理员提交反馈
        if query_history.user_id != user.id and not user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权为此查询提交反馈"
            )
            
        # 更新反馈
        updated_history = history_repo.update_user_feedback(
            session=session,
            query_id=query_id,
            feedback_score=feedback.feedback_score,
            feedback_comments=feedback.feedback_comments
        )
        
        if not updated_history:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"更新查询 {query_id} 的反馈失败"
            )
            
        return {"message": "反馈已更新"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新查询 {query_id} 的反馈失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新查询反馈时发生错误"
        ) 