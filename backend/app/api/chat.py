"""
对话 API 路由模块

提供对话的 CRUD 接口和消息发送接口。
消息发送采用 SSE 流式响应，使用 BackgroundTask 保证
客户端中断时也能保存已生成的助手回答。
"""

import logging
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
    update_conversation, delete_conversation, save_message,
)
from app.services.rag_service import stream_chat, StreamState
from starlette.background import BackgroundTask

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["对话"])


@router.get("/conversations", response_model=list[ConversationResponse])
async def list_conversations(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户的对话列表

    支持分页，按置顶优先、更新时间倒序排列。
    """
    conversations = await get_conversations(db, current_user.id, skip, limit)
    return conversations


@router.post("/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def new_conversation(
    data: ConversationCreate = ConversationCreate(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建新对话，默认标题为"新对话" """
    conversation = await create_conversation(db, current_user.id, data)
    return conversation


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取对话详情，包含该对话下的所有消息"""
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
    """更新对话信息（标题、置顶状态）"""
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
    """软删除对话（标记 is_deleted=True）"""
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
    """发送消息并流式返回 RAG 生成的回答

    使用独立的数据库会话，避免 get_db 在 StreamingResponse 消费前关闭。
    通过 StreamState 跟踪流内容，BackgroundTask 保证客户端中断时也能保存助手回答。
    """
    # 先用 get_db 验证对话是否存在
    async with AsyncSessionLocal() as check_db:
        conversation = await get_conversation_detail(check_db, conversation_id, current_user.id)
        if not conversation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="对话不存在")

    # 流式响应使用独立 session
    state = StreamState()
    db = AsyncSessionLocal()

    async def save_assistant_message():
        """后台任务：保存已生成的助手回答（正常完成或客户端中断都会执行）"""
        import sys
        print(f"[DEBUG] BackgroundTask 执行: full_answer长度={len(state.full_answer)}, stopped={state.stopped}, conversation_id={state.conversation_id}", file=sys.stderr, flush=True)
        logger.info(f"BackgroundTask 执行: full_answer长度={len(state.full_answer)}, stopped={state.stopped}, conversation_id={state.conversation_id}")
        if state.full_answer:
            # 客户端中断时追加停止标记
            answer = state.full_answer + "\n\n*[对话已停止]*" if state.stopped else state.full_answer
            try:
                await save_message(
                    db, state.conversation_id, "assistant", answer,
                    {"chunks": state.sources} if state.sources else None,
                )
                await db.commit()
                logger.info(f"助手消息已保存, 内容长度: {len(answer)}")
                print(f"[DEBUG] 助手消息已保存, 内容长度: {len(answer)}", file=sys.stderr, flush=True)
            except Exception as e:
                logger.error(f"保存助手消息失败: {e}")
                print(f"[DEBUG] 保存助手消息失败: {e}", file=sys.stderr, flush=True)
                await db.rollback()
        else:
            print(f"[DEBUG] full_answer 为空，跳过保存", file=sys.stderr, flush=True)
        await db.close()

    async def stream_with_db():
        """包装流式生成器，用于捕获异常和调试日志"""
        import sys
        chunk_idx = 0
        try:
            async for chunk in stream_chat(db, conversation_id, data.content, request=request, stream_state=state):
                chunk_idx += 1
                if chunk_idx <= 3:
                    print(f"[DEBUG stream_with_db] yield chunk #{chunk_idx}, full_answer长度={len(state.full_answer)}", file=sys.stderr, flush=True)
                yield chunk
        except GeneratorExit:
            print(f"[DEBUG stream_with_db] GeneratorExit! chunk_idx={chunk_idx}, full_answer长度={len(state.full_answer)}", file=sys.stderr, flush=True)
            raise
        except Exception as e:
            print(f"[DEBUG stream_with_db] 异常: {type(e).__name__}: {e}", file=sys.stderr, flush=True)
            raise
        finally:
            print(f"[DEBUG stream_with_db] 结束: chunk_idx={chunk_idx}, full_answer长度={len(state.full_answer)}", file=sys.stderr, flush=True)

    return StreamingResponse(
        stream_with_db(),
        media_type="text/event-stream",
        background=BackgroundTask(save_assistant_message),
    )
