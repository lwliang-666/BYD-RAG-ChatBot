import asyncio
import logging

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# 模型单例：全局只加载一次，避免重复加载占用内存
_embedding_model = None
# 标记模型是否加载失败，失败后不再重试，直接走 API 降级路径
_model_load_failed = False


def _load_model():
    """同步加载本地 SentenceTransformer 模型，供 asyncio.to_thread 在子线程中调用"""
    global _embedding_model, _model_load_failed

    if _embedding_model is not None or _model_load_failed:
        return

    try:
        from sentence_transformers import SentenceTransformer
        logger.info("正在加载 Embedding 模型: %s", settings.EMBEDDING_MODEL_PATH)
        # local_files_only=True 确保只使用本地已下载的模型，不触发网络下载
        _embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL_PATH, local_files_only=True)
        logger.info("Embedding 模型加载完成")
    except Exception as e:
        _model_load_failed = True
        _embedding_model = None
        logger.warning("Embedding 模型加载失败，将使用 API 方式: %s", e)


async def init_embedding_model():
    """应用启动时预加载模型，在子线程中执行以避免阻塞事件循环"""
    await asyncio.to_thread(_load_model)


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """对一组文本生成向量，优先使用本地模型，失败时降级为 API 调用"""
    # 懒加载：首次调用时在子线程中加载模型，不阻塞事件循环
    if _embedding_model is None and not _model_load_failed:
        await asyncio.to_thread(_load_model)

    if _embedding_model is not None:
        # 本地模型推理在子线程中执行，避免 CPU 密集计算阻塞事件循环
        result = await asyncio.to_thread(_embedding_model.encode, texts, batch_size=settings.EMBEDDING_BATCH_SIZE)
        return result.tolist() if hasattr(result, "tolist") else result

    # 本地模型不可用时，降级为远程 API 调用
    return await _embed_via_api(texts)


async def _embed_via_api(texts: list[str]) -> list[list[float]]:
    """通过 OpenAI 兼容的 Embedding API 生成向量（本地模型不可用时的降级方案）"""
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
        # API 返回的 data 可能乱序，按 index 排序确保向量与输入文本一一对应
        sorted_data = sorted(data["data"], key=lambda x: x["index"])
        return [item["embedding"] for item in sorted_data]


async def embed_query(text: str) -> list[float]:
    """对单条查询文本生成向量，用于检索时的 query embedding"""
    result = await embed_texts([text])
    return result[0]
