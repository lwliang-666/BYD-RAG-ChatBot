"""
向量检索与存储模块

提供文档分块的向量存储和相似度检索功能。
使用 pgvector 扩展进行向量存储和余弦距离检索，
支持按 top_k 返回最相似的文档片段。
"""

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
    """将文档分块及其向量批量写入数据库

    将每个分块的内容、向量、元数据插入 document_chunks 表，
    返回成功写入的分块数量。
    """
    count = 0
    for chunk, embedding in zip(chunks, embeddings):
        # 将向量列表转换为 pgvector 可识别的字符串格式
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
    """基于向量相似度检索与查询最相关的文档片段

    使用 pgvector 的余弦距离操作符 <=> 进行排序，
    返回 top_k 个最相似的文档片段及其相似度分数。
    """
    if top_k is None:
        top_k = settings.RAG_TOP_K

    # 对查询文本生成向量
    query_embedding = await embed_query(query)
    embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

    # 使用 pgvector 余弦距离检索最相似的文档片段
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
            # metadata 可能是 dict 或 JSON 字符串，统一处理为 dict
            "metadata": row[4] if isinstance(row[4], dict) else json.loads(row[4]) if row[4] else {},
            "similarity": float(row[5]),
        }
        for row in rows
    ]


async def get_existing_chunk_count(db: AsyncSession, document_name: str) -> int:
    """查询指定文档名在数据库中已有的分块数量，用于避免重复入库"""
    result = await db.execute(
        text("SELECT COUNT(*) FROM document_chunks WHERE document_name = :doc_name"),
        {"doc_name": document_name},
    )
    return result.scalar() or 0
