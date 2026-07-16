"""
用户相关 Schema 模块

定义用户资料的查询响应、更新请求和用户名修改请求的数据结构。
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class UserProfileResponse(BaseModel):
    """用户资料响应体"""
    id: uuid.UUID
    username: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class UserProfileUpdate(BaseModel):
    """用户资料更新请求体，目前仅支持修改显示名称"""
    display_name: Optional[str] = Field(None, max_length=50)


class UsernameUpdate(BaseModel):
    """用户名修改请求体"""
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_一-龥]+$")
