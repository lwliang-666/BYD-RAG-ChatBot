import uuid
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.chat import Conversation, Message
from app.schemas.chat import ConversationCreate, ConversationUpdate


async def create_conversation(db: AsyncSession, user_id: uuid.UUID, data: ConversationCreate) -> Conversation:
    conversation = Conversation(
        user_id=user_id,
        title=data.title,
    )
    db.add(conversation)
    await db.flush()
    return conversation


async def get_conversations(
    db: AsyncSession,
    user_id: uuid.UUID,
    skip: int = 0,
    limit: int = 50,
) -> list[Conversation]:
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user_id, Conversation.is_deleted == False)
        .order_by(Conversation.is_pinned.desc(), Conversation.updated_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_conversation_detail(db: AsyncSession, conversation_id: uuid.UUID, user_id: uuid.UUID) -> Optional[Conversation]:
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
    return conversation


async def delete_conversation(db: AsyncSession, conversation_id: uuid.UUID, user_id: uuid.UUID) -> bool:
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
    message = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        sources=sources,
    )
    db.add(message)
    await db.flush()
    return message


async def get_chat_history(db: AsyncSession, conversation_id: uuid.UUID, limit: int = 10) -> list[dict]:
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    messages = list(reversed(result.scalars().all()))
    return [{"role": m.role, "content": m.content} for m in messages]
