"""
对话服务模块

提供对话的 CRUD 操作、消息保存和聊天历史查询等业务逻辑。
对话删除采用软删除方式（标记 is_deleted=True）。
"""

import uuid
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.chat import Conversation, Message
from app.schemas.chat import ConversationCreate, ConversationUpdate


async def create_conversation(db: AsyncSession, user_id: uuid.UUID, data: ConversationCreate) -> Conversation:
    """创建新对话"""
    conversation = Conversation(
        user_id=user_id,
        title=data.title,
    )
    db.add(conversation)
    await db.flush()
    await db.refresh(conversation)
    return conversation


async def get_conversations(
    db: AsyncSession,
    user_id: uuid.UUID,
    skip: int = 0,
    limit: int = 50,
) -> list[Conversation]:
    """获取用户的对话列表

    按置顶优先、更新时间倒序排列，支持分页。
    """
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user_id, Conversation.is_deleted == False)
        .order_by(Conversation.is_pinned.desc(), Conversation.updated_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_conversation_detail(db: AsyncSession, conversation_id: uuid.UUID, user_id: uuid.UUID) -> Optional[Conversation]:
    """获取对话详情，预加载该对话下的所有消息"""
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
            Conversation.is_deleted == False,
        )
    )
    return result.scalar_one_or_none()


async def update_conversation(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    user_id: uuid.UUID,
    data: ConversationUpdate,
) -> Optional[Conversation]:
    """更新对话信息（标题、置顶状态），仅更新非 None 字段"""
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
            Conversation.is_deleted == False,
        )
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        return None

    if data.title is not None:
        conversation.title = data.title
    if data.is_pinned is not None:
        conversation.is_pinned = data.is_pinned

    await db.flush()
    await db.refresh(conversation)
    return conversation


async def delete_conversation(db: AsyncSession, conversation_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    """软删除对话（标记 is_deleted=True），返回是否成功"""
    result = await db.execute(
        update(Conversation)
        .where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
            Conversation.is_deleted == False,
        )
        .values(is_deleted=True)
    )
    return result.rowcount > 0


async def update_conversation_title(db: AsyncSession, conversation_id: uuid.UUID, title: str) -> None:
    """更新对话标题，用于根据首条消息自动设置标题"""
    result = await db.execute(
        update(Conversation)
        .where(Conversation.id == conversation_id)
        .values(title=title)
    )
    await db.flush()


async def save_message(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    role: str,
    content: str,
    sources: Optional[dict] = None,
) -> Message:
    """保存一条消息到数据库

    role 为 "user" 或 "assistant"，sources 为 RAG 检索引用信息。
    """
    message = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        sources=sources,
    )
    db.add(message)
    await db.flush()
    await db.refresh(message)
    return message


async def get_chat_history(db: AsyncSession, conversation_id: uuid.UUID, limit: int = 10) -> list[dict]:
    """获取对话的聊天历史

    按创建时间倒序查询后反转，返回最近 limit 条消息的
    role 和 content 字典列表，用于多轮对话上下文。
    """
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    # 倒序查询后反转为时间正序
    messages = list(reversed(result.scalars().all()))
    return [{"role": m.role, "content": m.content} for m in messages]
