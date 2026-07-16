"""
对话与消息 ORM 模型模块

定义 Conversation（对话）和 Message（消息）两个数据库模型，
包含对话的标题、置顶、软删除等字段，以及消息的角色、内容和引用来源。
"""

import uuid
from datetime import datetime

from sqlalchemy import String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Conversation(Base):
    """对话模型：存储用户的对话会话信息"""

    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), default="新对话")
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, onupdate=func.now())

    # 对话下的消息列表，按创建时间排序
    messages: Mapped[list["Message"]] = relationship("Message", back_populates="conversation", order_by="Message.created_at")


class Message(Base):
    """消息模型：存储对话中的单条消息（用户提问或助手回答）"""

    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(nullable=False)
    # RAG 检索引用的文档片段信息，JSON 格式存储
    sources: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # 所属对话的反向引用
    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="messages")
