import json
import uuid
from typing import AsyncGenerator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.rag.graph import stream_rag_answer
from app.services.chat_service import save_message, get_chat_history, update_conversation_title


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
) -> AsyncGenerator[str, None]:
    await save_message(db, conversation_id, "user", user_message)
    await db.commit()

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

    async for chunk in stream_rag_answer(user_message, db, chat_history):
        # 检查客户端是否已断开连接
        if request and await request.is_disconnected():
            if stream_state is not None:
                stream_state.stopped = True
            break

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

    # 正常完成时的 done 事件（被中断时不会执行到这里，由外部 finally 处理保存）
    yield f"event: done\ndata: {{}}\n\n"
