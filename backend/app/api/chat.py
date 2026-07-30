"""
对话 API 路由模块

提供对话的 CRUD 接口和消息发送接口。
消息发送采用 SSE 流式响应，使用 BackgroundTask 保证
客户端中断时也能保存已生成的助手回答。
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, AsyncSessionLocal
from app.core.deps import get_current_user
from app.models.user import User
from app.models.chat import Message
from app.schemas.chat import (
    ConversationCreate, ConversationUpdate,
    ConversationResponse, ConversationDetail,
    MessageCreate, MessageResponse,
)
from app.services.chat_service import (
    create_conversation, get_conversations, get_conversation_detail,
    update_conversation, delete_conversation, save_message, get_last_message,
)
from app.services.rag_service import stream_chat, StreamState
from app.services.rate_limit_service import check_rate_limit, increment_user_count
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
    包含提问次数限制检查，超限时返回 429 状态码。

    幂等性保证：如果该对话最后一条消息是 user 且无对应 assistant 回复，
    说明上次请求中断，后端已保存部分内容但前端未收到，直接返回已有回答。
    """
    # 验证对话是否存在
    async with AsyncSessionLocal() as check_db:
        conversation = await get_conversation_detail(check_db, conversation_id, current_user.id)
        if not conversation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="对话不存在")

        # 幂等性检查：如果最后一条是 user 消息且无对应 assistant 回复，说明上次请求中断
        last_msg = await get_last_message(check_db, conversation_id)
        if last_msg and last_msg.role == "user" and last_msg.content == data.content:
            # 检查是否已有 assistant 回复
            from sqlalchemy import select as sa_select
            result = await check_db.execute(
                sa_select(Message)
                .where(Message.conversation_id == conversation_id, Message.role == "assistant")
                .order_by(Message.created_at.desc())
                .limit(1)
            )
            assistant_msg = result.scalar_one_or_none()
            if assistant_msg:
                # 后端已有回答（可能是中断时保存的部分内容），直接通过 SSE 返回
                state = StreamState()
                state.conversation_id = conversation_id
                state.message_id = assistant_msg.id
                state.saved = True

                async def replay_existing_answer():
                    """重放已有回答的 SSE 事件流"""
                    import json as json_mod
                    # 发送 token 事件（一次性发送完整内容）
                    yield f"event: token\ndata: {json_mod.dumps({'content': assistant_msg.content}, ensure_ascii=False)}\n\n"
                    # 发送 sources 事件
                    if assistant_msg.sources:
                        yield f"event: sources\ndata: {json_mod.dumps({'chunks': assistant_msg.sources.get('chunks', [])}, ensure_ascii=False)}\n\n"
                    # 发送 done 事件
                    yield f"event: done\ndata: {json_mod.dumps({'message_id': str(assistant_msg.id)})}\n\n"

                return StreamingResponse(
                    replay_existing_answer(),
                    media_type="text/event-stream",
                )

    # 检查提问次数限制
    async with AsyncSessionLocal() as check_db:
        rate_info = await check_rate_limit(check_db, current_user.id)
        if not rate_info["allowed"]:
            remaining = min(rate_info["user_remaining"], rate_info["global_remaining"])
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "message": "今日提问次数已用完",
                    "user_remaining": rate_info["user_remaining"],
                    "global_remaining": rate_info["global_remaining"],
                },
            )
        # 递增提问计数
        await increment_user_count(check_db, current_user.id)
        await check_db.commit()

    # 流式响应使用独立 session
    state = StreamState()
    db = AsyncSessionLocal()

    # 保存剩余次数，用于在 done 事件中返回
    remaining_info = {
        "user_remaining": rate_info["user_remaining"] - 1,
        "global_remaining": rate_info["global_remaining"] - 1,
    }

    async def save_assistant_message():
        """后台任务：保存已生成的助手回答（正常完成或客户端中断都会执行）"""
        if state.saved:
            await db.close()
            return

        import sys
        print(f"[DEBUG] BackgroundTask 执行: full_answer长度={len(state.full_answer)}, stopped={state.stopped}, conversation_id={state.conversation_id}", file=sys.stderr, flush=True)
        logger.info(f"BackgroundTask 执行: full_answer长度={len(state.full_answer)}, stopped={state.stopped}, conversation_id={state.conversation_id}")
        if state.full_answer:
            # 客户端中断时追加停止标记
            answer = state.full_answer + "\n\n*[对话已停止]*" if state.stopped else state.full_answer
            try:
                msg = await save_message(
                    db, state.conversation_id, "assistant", answer,
                    {"chunks": state.sources} if state.sources else None,
                )
                await db.commit()
                state.message_id = msg.id
                state.saved = True
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
            async for chunk in stream_chat(db, conversation_id, data.content, request=request, stream_state=state, remaining_info=remaining_info):
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


@router.post("/speech-to-text")
async def speech_to_text_api(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """语音识别接口：接收音频文件，调用讯飞语音听写 API 返回识别文字

    支持的音频格式：webm、wav、mp3 等浏览器 MediaRecorder 输出的格式。
    音频大小限制 5MB。
    """
    # 检查文件大小（5MB 限制）
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="音频文件大小不能超过5MB",
        )

    # 将音频转为 PCM 16k 16bit 单声道
    pcm_data = await _convert_to_pcm(content, file.content_type or "")

    # 调用讯飞语音听写
    from app.services.speech_service import speech_to_text
    text = await speech_to_text(pcm_data)

    return {"text": text}


async def _convert_to_pcm(audio_data: bytes, content_type: str) -> bytes:
    """将音频数据转为 PCM 16k 16bit 单声道格式

    使用 ffmpeg 进行格式转换。如果转换失败，假设原始数据已是 PCM 格式。
    """
    import subprocess
    import tempfile
    import os

    # 写入临时文件
    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp_in:
        tmp_in.write(audio_data)
        tmp_in_path = tmp_in.name

    tmp_out_path = tmp_in_path + ".pcm"

    try:
        # 使用 ffmpeg 转换为 PCM 16k 16bit 单声道
        process = subprocess.run(
            [
                "ffmpeg", "-y", "-i", tmp_in_path,
                "-f", "s16le",           # PCM signed 16-bit little-endian
                "-acodec", "pcm_s16le",  # PCM 16-bit
                "-ar", "16000",           # 采样率 16k
                "-ac", "1",               # 单声道
                tmp_out_path,
            ],
            capture_output=True,
            timeout=10,
        )

        if process.returncode == 0 and os.path.exists(tmp_out_path):
            with open(tmp_out_path, "rb") as f:
                return f.read()
        else:
            logger.warning(f"ffmpeg 转换失败: {process.stderr.decode('utf-8', errors='ignore')[:200]}")
            return audio_data
    except FileNotFoundError:
        logger.warning("ffmpeg 未安装，无法转换音频格式")
        return audio_data
    except subprocess.TimeoutExpired:
        logger.warning("ffmpeg 转换超时")
        return audio_data
    finally:
        # 清理临时文件
        for path in [tmp_in_path, tmp_out_path]:
            if os.path.exists(path):
                os.unlink(path)
