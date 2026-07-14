from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.core.database import engine, Base
from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.user import router as user_router


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    upload_dir = os.path.abspath(settings.UPLOAD_DIR)
    os.makedirs(upload_dir, exist_ok=True)
    yield


app = FastAPI(
    title="BYD RAG ChatBot API",
    description="基于 RAG 向量检索增强的比亚迪 AI 问答系统",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(user_router)

app.mount("/uploads", StaticFiles(directory=os.path.abspath(settings.UPLOAD_DIR)), name="uploads")


@app.get("/health")
async def health_check():
    return {"status": "ok"}
