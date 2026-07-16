"""
文档分块 ORM 模型模块

定义 DocumentChunk 模型，存储 PDF 文档经分块和向量化后的
文本片段及其 embedding 向量，用于 RAG 检索。
"""

import uuid
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, func, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DocumentChunk(Base):
    """文档分块模型：存储单个文本块及其向量表示"""

    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_name: Mapped[str] = mapped_column(String(200), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # pgvector 向量字段，存储文本的 embedding
    embedding: Mapped[str | None] = mapped_column(nullable=True)
    # 分块元数据（页码、章节标题等），列名映射为 metadata
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
