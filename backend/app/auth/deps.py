"""
认证依赖模块

提供API路由中使用的认证和授权相关依赖项
"""

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.models.auth import User
from app.core.db import get_db_session
from sqlmodel import Session, select


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/token")


async def get_current_user(
    token: str = Depends(oauth2_scheme), session: Session = Depends(get_db_session)
) -> User:
    """
    获取当前用户

    验证token并返回当前用户信息

    参数:
        token: 访问令牌
        session: 数据库会话

    返回:
        User: 当前用户

    异常:
        HTTPException: 认证失败时抛出
    """
    # 这里应有实际的token验证逻辑
    # 简化示例，实际应使用JWT或其他认证机制
    user = session.exec(select(User).where(User.api_key == token)).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    获取当前管理员用户

    验证用户是否为管理员并返回

    参数:
        current_user: 当前用户

    返回:
        User: 当前管理员用户

    异常:
        HTTPException: 用户不是管理员时抛出
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied. Admin privileges required",
        )

    return current_user


def get_optional_user(
    token: Optional[str] = Depends(oauth2_scheme),
    session: Session = Depends(get_db_session),
) -> Optional[User]:
    """
    获取可选的当前用户

    如果有token则验证并返回用户，如果没有token则返回None

    参数:
        token: 可选的访问令牌
        session: 数据库会话

    返回:
        Optional[User]: 当前用户或None
    """
    if not token:
        return None

    try:
        return get_current_user(token, session)
    except HTTPException:
        return None
