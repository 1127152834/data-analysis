"""
数据库连接仓库模块

提供对数据库连接模型的数据访问操作
"""

from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlmodel import Session, select, or_, and_

from app.models.database_connection import DatabaseConnection, ConnectionStatus
from app.repositories.base_repo import BaseRepo


class DatabaseConnectionRepo(BaseRepo):
    """
    数据库连接仓库

    提供对数据库连接模型的CRUD操作和高级查询
    """

    model_cls = DatabaseConnection

    def list_active(self, session: Session) -> List[DatabaseConnection]:
        """
        列出所有活跃（未删除）的数据库连接

        参数:
            session: 数据库会话

        返回:
            List[DatabaseConnection]: 活跃的数据库连接列表
        """
        return session.exec(
            select(DatabaseConnection).where(DatabaseConnection.deleted_at.is_(None))
        ).all()

    def get_by_ids(self, session: Session, ids: List[int]) -> List[DatabaseConnection]:
        """
        通过ID列表获取数据库连接

        参数:
            session: 数据库会话
            ids: 数据库连接ID列表

        返回:
            List[DatabaseConnection]: 找到的数据库连接列表
        """
        if not ids:
            return []

        return session.exec(
            select(DatabaseConnection).where(
                and_(
                    DatabaseConnection.id.in_(ids),
                    DatabaseConnection.deleted_at.is_(None),
                )
            )
        ).all()

    def get_by_name(self, session: Session, name: str) -> Optional[DatabaseConnection]:
        """
        通过名称获取数据库连接

        参数:
            session: 数据库会话
            name: 数据库连接名称

        返回:
            Optional[DatabaseConnection]: 找到的数据库连接，如果不存在则返回None
        """
        return session.exec(
            select(DatabaseConnection).where(
                and_(
                    DatabaseConnection.name == name,
                    DatabaseConnection.deleted_at.is_(None),
                )
            )
        ).first()

    def update_status(
        self,
        session: Session,
        connection_id: int,
        status: ConnectionStatus,
        last_connected_at: Optional[datetime] = None,
    ) -> Optional[DatabaseConnection]:
        """
        更新数据库连接状态

        参数:
            session: 数据库会话
            connection_id: 数据库连接ID
            status: 新状态
            last_connected_at: 最后连接时间

        返回:
            Optional[DatabaseConnection]: 更新后的数据库连接，如果不存在则返回None
        """
        connection = session.get(DatabaseConnection, connection_id)
        if not connection or connection.deleted_at:
            return None

        connection.connection_status = status
        if last_connected_at:
            connection.last_connected_at = last_connected_at
        elif status == ConnectionStatus.CONNECTED:
            connection.last_connected_at = datetime.utcnow()

        session.add(connection)
        session.commit()
        session.refresh(connection)
        return connection

    def update_metadata(
        self, session: Session, connection_id: int, metadata: Dict[str, Any]
    ) -> Optional[DatabaseConnection]:
        """
        更新数据库元数据缓存

        参数:
            session: 数据库会话
            connection_id: 数据库连接ID
            metadata: 元数据信息

        返回:
            Optional[DatabaseConnection]: 更新后的数据库连接，如果不存在则返回None
        """
        connection = session.get(DatabaseConnection, connection_id)
        if not connection or connection.deleted_at:
            return None

        connection.metadata_cache = metadata
        connection.metadata_updated_at = datetime.utcnow()

        session.add(connection)
        session.commit()
        session.refresh(connection)
        return connection

    def soft_delete(self, session: Session, connection_id: int) -> bool:
        """
        软删除数据库连接

        标记数据库连接为已删除，而不是物理删除

        参数:
            session: 数据库会话
            connection_id: 数据库连接ID

        返回:
            bool: 删除是否成功
        """
        connection = session.get(DatabaseConnection, connection_id)
        if not connection or connection.deleted_at:
            return False

        connection.deleted_at = datetime.utcnow()
        session.add(connection)
        session.commit()
        return True

    def search(
        self,
        session: Session,
        query: str = "",
        database_type: Optional[str] = None,
        status: Optional[ConnectionStatus] = None,
        user_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[DatabaseConnection]:
        """
        搜索数据库连接

        根据条件搜索数据库连接

        参数:
            session: 数据库会话
            query: 搜索关键词（匹配名称和描述）
            database_type: 数据库类型
            status: 连接状态
            user_id: 用户ID
            skip: 跳过的记录数
            limit: 返回的最大记录数

        返回:
            List[DatabaseConnection]: 符合条件的数据库连接列表
        """
        statement = select(DatabaseConnection).where(
            DatabaseConnection.deleted_at.is_(None)
        )

        # 添加搜索条件
        if query:
            statement = statement.where(
                or_(
                    DatabaseConnection.name.contains(query),
                    DatabaseConnection.description.contains(query),
                )
            )

        if database_type:
            statement = statement.where(
                DatabaseConnection.database_type == database_type
            )

        if status:
            statement = statement.where(DatabaseConnection.connection_status == status)

        if user_id:
            statement = statement.where(DatabaseConnection.user_id == user_id)

        # 添加分页
        statement = statement.offset(skip).limit(limit)

        return session.exec(statement).all()
