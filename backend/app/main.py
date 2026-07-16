"""
FastAPI 应用入口模块

初始化 FastAPI 应用实例，配置 CORS 中间件、路由注册、
静态文件挂载，以及请求参数校验错误的中文翻译处理。
"""

from contextlib import asynccontextmanager
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.core.config import get_settings
from app.core.database import engine, Base
from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.user import router as user_router


settings = get_settings()

# 字段校验错误的中文翻译映射表
FIELD_ERROR_MAP = {
    "username": {
        "min_length": "用户名至少需要3个字符",
        "max_length": "用户名不能超过50个字符",
        "pattern": "用户名只能包含字母、数字、下划线和中文",
        "required": "请输入用户名",
    },
    "password": {
        "min_length": "密码至少需要6个字符",
        "max_length": "密码不能超过72个字符",
        "required": "请输入密码",
    },
}


def translate_validation_error(error: dict) -> str:
    """将 Pydantic 校验错误翻译为中文提示信息

    根据错误字段和错误类型，从 FIELD_ERROR_MAP 中查找对应的中文提示，
    找不到时返回默认的"请求参数错误"。
    """
    loc = error.get("loc", [])
    # 取 loc 路径的最后一个元素作为字段名
    field = loc[-1] if loc else None
    err_type = error.get("type", "")
    field_messages = FIELD_ERROR_MAP.get(field, {})
    if err_type in ("string_too_short", "missing") and "min_length" in field_messages:
        return field_messages["min_length"]
    if err_type == "string_too_short" and "min_length" in field_messages:
        return field_messages["min_length"]
    if err_type == "string_too_long" and "max_length" in field_messages:
        return field_messages["max_length"]
    if err_type == "missing" and "required" in field_messages:
        return field_messages["required"]
    if err_type == "string_pattern_mismatch" and "pattern" in field_messages:
        return field_messages["pattern"]
    return "请求参数错误"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理：启动时初始化数据库表、上传目录和 Embedding 模型"""
    # 自动创建所有数据库表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # 确保上传目录存在
    upload_dir = os.path.abspath(settings.UPLOAD_DIR)
    os.makedirs(upload_dir, exist_ok=True)
    # 预加载 Embedding 模型
    from app.rag.embedding import init_embedding_model
    await init_embedding_model()
    yield


app = FastAPI(
    title="BYD RAG ChatBot API",
    description="基于 RAG 向量检索增强的比亚迪 AI 问答系统",
    version="1.0.0",
    lifespan=lifespan,
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """全局请求参数校验异常处理器，将第一个校验错误翻译为中文后返回"""
    errors = exc.errors()
    detail = translate_validation_error(errors[0]) if errors else "请求参数错误"
    return JSONResponse(status_code=422, content={"detail": detail})

# 配置 CORS 中间件，仅允许前端开发服务器访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册各业务模块路由
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(user_router)

# 挂载静态文件目录，用于提供上传文件的访问
app.mount("/uploads", StaticFiles(directory=os.path.abspath(settings.UPLOAD_DIR)), name="uploads")


@app.get("/health")
async def health_check():
    """健康检查接口，用于确认服务是否正常运行"""
    return {"status": "ok"}
