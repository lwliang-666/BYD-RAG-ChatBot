import json
import uuid
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.rag.embedding import embed_query

settings = get_settings()


async def store_chunks(
    db: AsyncSession,
    document_name: str,
    chunks: list,
    embeddings: list[list[float]],
) -> int:
    count = 0
    for chunk, embedding in zip(chunks, embeddings):
        embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"
        metadata = json.dumps({
            "page_number": chunk.page_number,
            "section_title": chunk.section_title,
        }, ensure_ascii=False)

        await db.execute(
            text("""
                INSERT INTO document_chunks (id, document_name, chunk_index, content, embedding, metadata)
                VALUES (:id, :doc_name, :chunk_idx, :content, CAST(:embedding AS vector), CAST(:metadata AS jsonb))
            """),
            {
                "id": str(uuid.uuid4()),
                "doc_name": document_name,
                "chunk_idx": chunk.chunk_index,
                "content": chunk.content,
                "embedding": embedding_str,
                "metadata": metadata,
            },
        )
        count += 1
    return count


async def search_similar(
    db: AsyncSession,
    query: str,
    top_k: Optional[int] = None,
) -> list[dict]:
    if top_k is None:
        top_k = settings.RAG_TOP_K

    query_embedding = await embed_query(query)
    embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

    result = await db.execute(
        text("""
            SELECT
                id, document_name, chunk_index, content, metadata,
                1 - (embedding <=> CAST(:query_embedding AS vector)) AS similarity
            FROM document_chunks
            ORDER BY embedding <=> CAST(:query_embedding AS vector)
            LIMIT :top_k
        """),
        {
            "query_embedding": embedding_str,
            "top_k": top_k,
        },
    )

    rows = result.fetchall()
    return [
        {
            "id": str(row[0]),
            "document_name": row[1],
            "chunk_index": row[2],
            "content": row[3],
            "metadata": row[4] if isinstance(row[4], dict) else json.loads(row[4]) if row[4] else {},
            "similarity": float(row[5]),
        }
        for row in rows
    ]


async def get_existing_chunk_count(db: AsyncSession, document_name: str) -> int:
    result = await db.execute(
        text("SELECT COUNT(*) FROM document_chunks WHERE document_name = :doc_name"),
        {"doc_name": document_name},
    )
    return result.scalar() or 0
