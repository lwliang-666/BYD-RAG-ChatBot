"""
对话与消息相关 Schema 模块

定义对话的创建、更新、响应数据结构，以及消息的创建和响应数据结构。
ConversationDetail 包含对话下的消息列表。
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    """创建对话请求体，默认标题为"新对话" """
    title: str = Field(default="新对话", max_length=200)


class ConversationUpdate(BaseModel):
    """更新对话请求体，所有字段可选"""
    title: Optional[str] = Field(None, max_length=200)
    is_pinned: Optional[bool] = None


class ConversationResponse(BaseModel):
    """对话响应体，用于列表展示"""
    id: uuid.UUID
    title: str
    is_pinned: bool
    is_deleted: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class MessageCreate(BaseModel):
    """发送消息请求体"""
    content: str = Field(..., min_length=1)


class MessageResponse(BaseModel):
    """消息响应体"""
    id: uuid.UUID
    role: str
    content: str
    sources: Optional[dict] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationDetail(ConversationResponse):
    """对话详情响应体，包含该对话下的所有消息"""
    messages: list[MessageResponse] = []
