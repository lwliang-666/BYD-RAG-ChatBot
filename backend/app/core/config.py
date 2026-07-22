"""
应用配置模块

使用 pydantic-settings 管理所有配置项，支持从 .env 文件和环境变量读取。
配置项涵盖数据库连接、JWT 认证、LLM 接入、Embedding 模型、
RAG 参数和文件上传等。
"""

import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """应用全局配置类

    所有配置项均有默认值，可通过 .env 文件或环境变量覆盖。
    """

    # 数据库连接字符串
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/byd_rag"

    # JWT 令牌配置
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # LLM 大语言模型配置
    LLM_MODEL_ID: str = "astron-code-latest"
    LLM_BASE_URL: str = "https://maas-coding-api.cn-huabei-1.xf-yun.com/v2"
    LLM_API_KEY: str = os.getenv("XFXC_API_KEY", "")

    # Embedding 向量模型配置
    EMBEDDING_MODEL_PATH: str = "BAAI/bge-large-zh-v1.5"
    EMBEDDING_DIMENSION: int = 1024
    EMBEDDING_BATCH_SIZE: int = 64

    # RAG 检索与分块配置
    RAG_TOP_K: int = 5
    CHUNK_MAX_TOKENS: int = 800
    CHUNK_OVERLAP_TOKENS: int = 50

    # 文件上传配置
    UPLOAD_DIR: str = "./uploads"
    MAX_AVATAR_SIZE_MB: int = 2

    # 提问次数限制配置
    USER_DAILY_QUESTION_LIMIT: int = 20   # 每个用户每天最多提问次数
    GLOBAL_DAILY_QUESTION_LIMIT: int = 300  # 全局每天最多提问次数

    # 讯飞语音听写配置
    XFYUN_APP_ID: str = ""
    XFYUN_API_KEY: str = ""
    XFYUN_API_SECRET: str = ""

    model_config = {
        # 先加载 .env（公共配置），再加载 .env.secrets（密钥），后者覆盖前者
        "env_file": [".env", ".env.secrets"],
        "env_file_encoding": "utf-8",
    }


@lru_cache()
def get_settings() -> Settings:
    """获取全局配置单例（带缓存，避免重复读取 .env 文件）"""
    return Settings()
