---
name: byd-backend
description: BYD-RAG-ChatBot 后端开发规范和模式指导。当用户在后端添加新 API 接口、修改 service/schema/model、处理 FastAPI 路由、SQLAlchemy 异步查询、JWT 认证、SSE 流式响应等后端相关开发时触发。也适用于 "添加接口"、"新增 API"、"后端功能"、"FastAPI 路由" 等场景。提供项目已有的分层架构模式（api → service → schema/model）和代码风格参考。
---

# BYD-RAG-ChatBot 后端开发规范

## 分层架构

```
backend/app/
  api/          ← 路由层：HTTP 请求处理，依赖注入
  schemas/      ← 数据层：Pydantic 请求/响应模型
  services/     ← 业务层：核心逻辑，操作数据库
  models/       ← 模型层：SQLAlchemy ORM 定义
  core/         ← 基础层：配置、安全、数据库连接、依赖注入
  rag/          ← RAG 管道：分块、嵌入、检索、生成
```

**调用方向**: api → services → (schemas + models)，禁止反向依赖。

## 新增 API 标准流程

1. **定义 Schema** (`backend/app/schemas/`) — 请求体和响应体
2. **添加/修改 Model** (`backend/app/models/`) — 如需新表
3. **实现 Service** (`backend/app/services/`) — 业务逻辑
4. **添加路由** (`backend/app/api/`) — HTTP 端点
5. **注册路由** (`backend/app/main.py`) — `app.include_router()`
6. **更新建表 SQL** (`docker/init.sql`) — 如有新表

## 关键模式

### 路由层 (api/)

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/xxx", tags=["标签"])

@router.get("/items", response_model=list[ItemResponse])
async def list_items(
    current_user: User = Depends(get_current_user),  # 需认证
    db: AsyncSession = Depends(get_db),
):
    items = await get_items(db, current_user.id)
    return items
```

### Schema 层 (schemas/)

```python
from pydantic import BaseModel, Field
import uuid
from datetime import datetime
from typing import Optional

class XxxCreate(BaseModel):
    """创建请求体"""
    name: str = Field(..., min_length=1, max_length=200)

class XxxResponse(BaseModel):
    """响应体"""
    id: uuid.UUID
    name: str
    created_at: datetime
    model_config = {"from_attributes": True}  # 启用 ORM 模式
```

### Service 层 (services/)

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

async def get_items(db: AsyncSession, user_id: uuid.UUID) -> list[Item]:
    result = await db.execute(
        select(Item).where(Item.user_id == user_id, Item.is_deleted == False)
    )
    return result.scalars().all()
```

### Model 层 (models/)

```python
import uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base

class Item(Base):
    __tablename__ = "items"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
```

## JWT 认证

- 依赖: `Depends(get_current_user)` 返回 `User` 对象
- 双令牌: access_token (30min) + refresh_token (7d)
- Token 类型通过 payload 中的 `type` 字段区分

## SSE 流式响应

聊天接口使用的模式：

```python
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask
from app.core.database import AsyncSessionLocal

@router.post("/conversations/{id}/messages")
async def send_message(...):
    # 使用独立 session，避免 get_db 在流完成前关闭
    db = AsyncSessionLocal()
    state = StreamState()

    async def save_assistant_message():
        """后台任务：客户端中断时也能保存已生成内容"""
        if state.full_answer:
            await save_message(db, ...)
        await db.close()

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        background=BackgroundTask(save_assistant_message),
    )
```

SSE 事件格式：
```
event: token\ndata: {"content": "部分内容"}\n\n
event: sources\ndata: {"chunks": [...]} \n\n
event: done\ndata: {"message_id": "uuid"}\n\n
```

## 错误处理

Service 层抛 `ValueError`，API 层映射为 `HTTPException`：

```python
try:
    user = await authenticate_user(db, username, password)
except ValueError as e:
    raise HTTPException(status_code=401, detail=str(e))
```

## 代码风格

- 注释使用中文，文件编码 UTF-8
- 类型注解：函数参数和返回值都标注类型
- 异步优先：所有数据库操作使用 `async/await`
- 软删除：`is_deleted` 字段，查询时过滤 `WHERE is_deleted = FALSE`
- UUID 主键：`id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)`
