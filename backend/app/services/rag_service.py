import json
import uuid
from typing import AsyncGenerator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.rag.graph import stream_rag_answer
from app.services.chat_service import save_message, get_chat_history, update_conversation_title


async def stream_chat(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    user_message: str,
    request: Request = None,
) -> AsyncGenerator[str, None]:
    await save_message(db, conversation_id, "user", user_message)

    chat_history = await get_chat_history(db, conversation_id, limit=10)

    # 根据用户首条消息自动设置对话标题
    if len(chat_history) <= 1:
        title = user_message[:20].replace("\n", " ")
        if len(user_message) > 20:
            title += "..."
        await update_conversation_title(db, conversation_id, title)

    full_answer = ""
    sources = None
    stopped = False

    async for chunk in stream_rag_answer(user_message, db, chat_history):
        # 检查客户端是否已断开连接
        if request and await request.is_disconnected():
            stopped = True
            break

        if chunk.startswith("event: token"):
            data_start = chunk.index("data: ") + 6
            data = json.loads(chunk[data_start:chunk.index("\n\n", data_start)])
            full_answer += data.get("content", "")
            yield chunk
        elif chunk.startswith("event: sources"):
            data_start = chunk.index("data: ") + 6
            data = json.loads(chunk[data_start:chunk.index("\n\n", data_start)])
            sources = data.get("chunks", [])
            yield chunk
        elif chunk.startswith("event: done"):
            # 先保存消息，获取 message_id 后再发送 done 事件
            pass

    # 保存已生成的回答（被停止时追加停止标记）
    message_id = None
    if full_answer:
        answer = full_answer + "\n\n*[对话已停止]*" if stopped else full_answer
        message = await save_message(
            db, conversation_id, "assistant", answer,
            {"chunks": sources} if sources else None,
        )
        message_id = str(message.id)

    yield f"event: done\ndata: {json.dumps({'message_id': message_id}, ensure_ascii=False)}\n\n"
