"""
RAG 服务模块

作为 RAG 流程的编排层，负责消息保存、聊天历史加载、
对话标题自动设置，以及流式 RAG 回答的生成与状态跟踪。
"""

import json
import logging
import uuid
from typing import AsyncGenerator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.rag.graph import stream_rag_answer
from app.services.chat_service import save_message, get_chat_history, update_conversation_title

logger = logging.getLogger(__name__)


class StreamState:
    """流式回答的状态跟踪，供外部消费者在生成器被中断时保存已生成内容"""

    def __init__(self):
        self.full_answer = ""
        self.sources = None
        self.stopped = False
        self.conversation_id = None


async def stream_chat(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    user_message: str,
    request: Request = None,
    stream_state: StreamState = None,
    remaining_info: dict = None,
) -> AsyncGenerator[str, None]:
    """流式聊天主流程

    流程：
    1. 保存用户消息到数据库
    2. 加载聊天历史用于多轮对话上下文
    3. 根据首条消息自动设置对话标题
    4. 调用 RAG 流式生成回答，同时跟踪流状态
    5. 检测客户端断开时标记停止状态
    6. 正常完成时发送 done 事件（含剩余提问次数）
    """
    # 保存用户消息
    await save_message(db, conversation_id, "user", user_message)
    await db.commit()

    # 加载聊天历史，用于多轮对话上下文
    chat_history = await get_chat_history(db, conversation_id, limit=10)

    # 根据用户首条消息自动设置对话标题
    if len(chat_history) <= 1:
        title = user_message[:20].replace("\n", " ")
        if len(user_message) > 20:
            title += "..."
        await update_conversation_title(db, conversation_id, title)
        await db.commit()

    # 初始化流状态跟踪
    if stream_state is not None:
        stream_state.conversation_id = conversation_id

    import sys
    chunk_count = 0
    print(f"[DEBUG stream_chat] 开始迭代 stream_rag_answer", file=sys.stderr, flush=True)
    try:
        async for chunk in stream_rag_answer(user_message, db, chat_history):
            chunk_count += 1
            # 检查客户端是否已断开连接
            if request and await request.is_disconnected():
                print(f"[DEBUG] 检测到客户端断开，已生成内容长度: {len(stream_state.full_answer) if stream_state else 'N/A'}", file=sys.stderr, flush=True)
                logger.info(f"检测到客户端断开，已生成内容长度: {len(stream_state.full_answer) if stream_state else 'N/A'}")
                if stream_state is not None:
                    stream_state.stopped = True
                break

            # 解析 SSE 事件并更新流状态
            if chunk.startswith("event: token"):
                data_start = chunk.index("data: ") + 6
                data = json.loads(chunk[data_start:chunk.index("\n\n", data_start)])
                content = data.get("content", "")
                if stream_state is not None:
                    stream_state.full_answer += content
                yield chunk
            elif chunk.startswith("event: sources"):
                data_start = chunk.index("data: ") + 6
                data = json.loads(chunk[data_start:chunk.index("\n\n", data_start)])
                if stream_state is not None:
                    stream_state.sources = data.get("chunks", [])
                yield chunk
            elif chunk.startswith("event: done"):
                pass
    except GeneratorExit:
        print(f"[DEBUG stream_chat] GeneratorExit! chunk_count={chunk_count}, full_answer长度={len(stream_state.full_answer) if stream_state else 'N/A'}", file=sys.stderr, flush=True)
        raise
    except Exception as e:
        print(f"[DEBUG stream_chat] 异常: {type(e).__name__}: {e}", file=sys.stderr, flush=True)
        raise

    # 正常完成时的 done 事件（被中断时不会执行到这里，由外部 finally 处理保存）
    print(f"[DEBUG] stream_chat 结束: chunk_count={chunk_count}, full_answer长度={len(stream_state.full_answer) if stream_state else 'N/A'}, stopped={stream_state.stopped if stream_state else 'N/A'}", file=sys.stderr, flush=True)
    done_data = {}
    if remaining_info:
        done_data["remaining"] = remaining_info
    yield f"event: done\ndata: {json.dumps(done_data)}\n\n"
