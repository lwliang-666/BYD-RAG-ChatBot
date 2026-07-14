import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    title: str = Field(default="新对话", max_length=200)


class ConversationUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    is_pinned: Optional[bool] = None


class ConversationResponse(BaseModel):
    id: uuid.UUID
    title: str
    is_pinned: bool
    is_deleted: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1)


class MessageResponse(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    sources: Optional[dict] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationDetail(ConversationResponse):
    messages: list[MessageResponse] = []
