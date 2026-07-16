import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, AsyncSessionLocal
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.chat import (
    ConversationCreate, ConversationUpdate,
    ConversationResponse, ConversationDetail,
    MessageCreate, MessageResponse,
)
from app.services.chat_service import (
    create_conversation, get_conversations, get_conversation_detail,
    update_conversation, delete_conversation,
)
from app.services.rag_service import stream_chat

router = APIRouter(prefix="/api/chat", tags=["对话"])


@router.get("/conversations", response_model=list[ConversationResponse])
async def list_conversations(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conversations = await get_conversations(db, current_user.id, skip, limit)
    return conversations


@router.post("/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def new_conversation(
    data: ConversationCreate = ConversationCreate(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conversation = await create_conversation(db, current_user.id, data)
    return conversation


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conversation = await get_conversation_detail(db, conversation_id, current_user.id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="对话不存在")
    return conversation


@router.put("/conversations/{conversation_id}", response_model=ConversationResponse)
async def update_conversation_api(
    conversation_id: uuid.UUID,
    data: ConversationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conversation = await update_conversation(db, conversation_id, current_user.id, data)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="对话不存在")
    return conversation


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation_api(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    success = await delete_conversation(db, conversation_id, current_user.id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="对话不存在")


@router.post("/conversations/{conversation_id}/messages")
async def send_message(
    request: Request,
    conversation_id: uuid.UUID,
    data: MessageCreate,
    current_user: User = Depends(get_current_user),
):
    # 使用独立的 session，避免 get_db 在 StreamingResponse 消费前关闭
    # 先用 get_db 验证对话是否存在
    async with AsyncSessionLocal() as check_db:
        conversation = await get_conversation_detail(check_db, conversation_id, current_user.id)
        if not conversation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="对话不存在")

    # 流式响应使用独立 session，在 stream_chat 中管理生命周期
    async def stream_with_db():
        async with AsyncSessionLocal() as db:
            try:
                async for chunk in stream_chat(db, conversation_id, data.content, request=request):
                    yield chunk
                await db.commit()
            except Exception:
                await db.rollback()
                raise

    return StreamingResponse(
        stream_with_db(),
        media_type="text/event-stream",
    )
