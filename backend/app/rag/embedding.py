import asyncio
import logging

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

_embedding_model = None
_model_load_failed = False


def _load_model():
    """同步加载模型，供 asyncio.to_thread 调用"""
    global _embedding_model, _model_load_failed

    if _embedding_model is not None or _model_load_failed:
        return

    try:
        from sentence_transformers import SentenceTransformer
        logger.info("正在加载 Embedding 模型: %s", settings.EMBEDDING_MODEL_PATH)
        _embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL_PATH, local_files_only=True)
        logger.info("Embedding 模型加载完成")
    except Exception as e:
        _model_load_failed = True
        _embedding_model = None
        logger.warning("Embedding 模型加载失败，将使用 API 方式: %s", e)


async def init_embedding_model():
    """应用启动时预加载模型"""
    await asyncio.to_thread(_load_model)


async def embed_texts(texts: list[str]) -> list[list[float]]:
    # 首次调用时懒加载模型（在线程中执行，不阻塞事件循环）
    if _embedding_model is None and not _model_load_failed:
        await asyncio.to_thread(_load_model)

    if _embedding_model is not None:
        result = await asyncio.to_thread(_embedding_model.encode, texts, batch_size=settings.EMBEDDING_BATCH_SIZE)
        return result.tolist() if hasattr(result, "tolist") else result

    return await _embed_via_api(texts)


async def _embed_via_api(texts: list[str]) -> list[list[float]]:
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{settings.LLM_BASE_URL}/embeddings",
            headers={
                "Authorization": f"Bearer {settings.LLM_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.EMBEDDING_MODEL_PATH,
                "input": texts,
            },
        )
        response.raise_for_status()
        data = response.json()
        sorted_data = sorted(data["data"], key=lambda x: x["index"])
        return [item["embedding"] for item in sorted_data]


async def embed_query(text: str) -> list[float]:
    result = await embed_texts([text])
    return result[0]
