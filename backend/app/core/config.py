import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # 数据库
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/byd_rag"

    # JWT
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # LLM
    LLM_MODEL_ID: str = "astron-code-latest"
    LLM_BASE_URL: str = "https://maas-coding-api.cn-huabei-1.xf-yun.com/v2"
    LLM_API_KEY: str = os.getenv("XFXC_API_KEY")

    # Embedding
    EMBEDDING_MODEL_PATH: str = "BAAI/bge-large-zh-v1.5"
    EMBEDDING_DIMENSION: int = 1024
    EMBEDDING_BATCH_SIZE: int = 64

    # RAG
    RAG_TOP_K: int = 5
    CHUNK_MAX_TOKENS: int = 800
    CHUNK_OVERLAP_TOKENS: int = 50

    # 文件上传
    UPLOAD_DIR: str = "./uploads"
    MAX_AVATAR_SIZE_MB: int = 2

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


@lru_cache()
def get_settings() -> Settings:
    return Settings()
