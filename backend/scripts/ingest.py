# 将后端根目录加入 sys.path，确保能正确导入 app 包
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.rag.chunking import chunk_pdf
from app.rag.embedding import embed_texts
from app.rag.retriever import store_chunks, get_existing_chunk_count

settings = get_settings()

# 默认 PDF 路径：项目根目录下的 originData/BYD-QZJ05.pdf
PDF_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "originData", "BYD-QZJ05.pdf")


async def ingest_pdf(pdf_path: str = PDF_PATH):
    """将 PDF 文档解析、分块、向量化后存入数据库的入库流程"""
    pdf_path = os.path.abspath(pdf_path)
    if not os.path.exists(pdf_path):
        print(f"PDF 文件不存在: {pdf_path}")
        return

    document_name = os.path.basename(pdf_path)
    print(f"开始处理文档: {document_name}")

    # 检查该文档是否已入库，避免重复写入
    async with AsyncSessionLocal() as db:
        existing_count = await get_existing_chunk_count(db, document_name)
        if existing_count > 0:
            print(f"文档已有 {existing_count} 个块, 跳过入库(如需重新入库请先清空)")
            return

    # 第一步：解析 PDF 并按配置的 token 上限和重叠量进行分块
    print("正在解析 PDF 并分块...")
    chunks = chunk_pdf(
        pdf_path,
        max_tokens=settings.CHUNK_MAX_TOKENS,
        overlap_tokens=settings.CHUNK_OVERLAP_TOKENS,
    )
    print(f"共生成 {len(chunks)} 个文本块")

    # 第二步：对文本块进行批量向量化，按 EMBEDDING_BATCH_SIZE 分批调用
    print("正在向量化文本块...")
    texts = [chunk.content for chunk in chunks]
    embeddings = []
    batch_size = settings.EMBEDDING_BATCH_SIZE

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        batch_embeddings = await embed_texts(batch)
        embeddings.extend(batch_embeddings)
        progress = min(i + batch_size, len(texts))
        print(f"  向量化进度: {progress}/{len(texts)}")

    # 第三步：将文本块及其向量写入数据库并提交事务
    print("正在写入数据库...")
    async with AsyncSessionLocal() as db:
        count = await store_chunks(db, document_name, chunks, embeddings)
        await db.commit()
        print(f"成功入库 {count} 个文本块")


if __name__ == "__main__":
    asyncio.run(ingest_pdf())
