import uuid
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.rag.graph import stream_rag_answer
from app.services.chat_service import save_message, get_chat_history


async def stream_chat(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    user_message: str,
) -> AsyncGenerator[str, None]:
    await save_message(db, conversation_id, "user", user_message)

    chat_history = await get_chat_history(db, conversation_id, limit=10)

    full_answer = ""
    sources = None

    async for chunk in stream_rag_answer(user_message, db, chat_history):
        if chunk.startswith("event: token"):
            import json
            data_start = chunk.index("data: ") + 6
            data = json.loads(chunk[data_start:chunk.index("\n\n", data_start)])
            full_answer += data.get("content", "")
            yield chunk
        elif chunk.startswith("event: sources"):
            import json
            data_start = chunk.index("data: ") + 6
            data = json.loads(chunk[data_start:chunk.index("\n\n", data_start)])
            sources = data.get("chunks", [])
            yield chunk
        elif chunk.startswith("event: done"):
            yield chunk

    await save_message(db, conversation_id, "assistant", full_answer, {"chunks": sources} if sources else None)
