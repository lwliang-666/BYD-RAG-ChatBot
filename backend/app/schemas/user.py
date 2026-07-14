import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class UserProfileResponse(BaseModel):
    id: uuid.UUID
    username: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class UserProfileUpdate(BaseModel):
    display_name: Optional[str] = Field(None, max_length=50)


class UsernameUpdate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_\u4e00-\u9fa5]+$")
