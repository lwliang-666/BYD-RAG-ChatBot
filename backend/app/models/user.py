"""
用户 ORM 模型模块

定义 User 模型，存储用户的基本信息（用户名、显示名称、
密码哈希、头像等），支持软删除，用户名在未删除记录中唯一。
"""

import uuid
from datetime import datetime

from sqlalchemy import String, Boolean, DateTime, func, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class User(Base):
    """用户模型：存储系统用户信息"""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(50), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, onupdate=func.now())

    __table_args__ = (
        # 部分唯一索引：仅在未删除的记录中保证用户名唯一
        Index("ix_users_username_active", "username", unique=True, postgresql_where=(is_deleted == False)),
    )
