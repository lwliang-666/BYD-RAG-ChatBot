"""
提问次数限制 ORM 模型模块

记录每个用户每天的提问次数，用于实现每日提问频率限制。
每条记录对应一个用户在某一天的提问计数，通过 user_id + date 联合唯一约束保证唯一性。
"""

import uuid
from datetime import date, datetime

from sqlalchemy import String, Integer, Boolean, DateTime, Date, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class QuestionRateLimit(Base):
    """提问次数限制模型：按用户按天记录提问计数"""

    __tablename__ = "question_rate_limits"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default="NOW()")

    __table_args__ = (
        # 联合唯一索引：每个用户每天只有一条记录
        Index("ix_rate_limit_user_date", "user_id", "date", unique=True),
    )
