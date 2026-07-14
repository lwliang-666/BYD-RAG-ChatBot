import json
import os
from pathlib import Path
from typing import Optional

import httpx

from app.core.config import get_settings

settings = get_settings()

_embedding_model = None


def get_embedding_model():
    global _embedding_model
    if _embedding_model is not None:
        return _embedding_model

    try:
        from mlx_embeddings import EmbeddingModel
        model_path = os.path.expanduser(settings.EMBEDDING_MODEL_PATH)
        if Path(model_path).exists():
            _embedding_model = EmbeddingModel(model_path)
        else:
            _embedding_model = EmbeddingModel(settings.EMBEDDING_MODEL_PATH)
    except ImportError:
        _embedding_model = None

    return _embedding_model


async def embed_texts(texts: list[str]) -> list[list[float]]:
    model = get_embedding_model()

    if model is not None:
        embeddings = []
        batch_size = settings.EMBEDDING_BATCH_SIZE
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            result = model.encode(batch)
            embeddings.extend(result.tolist() if hasattr(result, "tolist") else result)
        return embeddings

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
