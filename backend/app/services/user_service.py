import os
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.user import User
from app.schemas.user import UserProfileUpdate, UsernameUpdate

settings = get_settings()


async def get_user_profile(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id, User.is_deleted == False))
    return result.scalar_one_or_none()


async def update_user_profile(db: AsyncSession, user_id: uuid.UUID, data: UserProfileUpdate) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id, User.is_deleted == False))
    user = result.scalar_one_or_none()
    if not user:
        return None

    if data.display_name is not None:
        user.display_name = data.display_name

    await db.flush()
    return user


async def update_username(db: AsyncSession, user_id: uuid.UUID, data: UsernameUpdate) -> User:
    result = await db.execute(
        select(User).where(User.username == data.username, User.is_deleted == False, User.id != user_id)
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise ValueError("用户名已被占用")

    result = await db.execute(select(User).where(User.id == user_id, User.is_deleted == False))
    user = result.scalar_one_or_none()
    if not user:
        raise ValueError("用户不存在")

    user.username = data.username
    await db.flush()
    return user


async def update_avatar(db: AsyncSession, user_id: uuid.UUID, file_content: bytes, filename: str) -> str:
    upload_dir = os.path.abspath(settings.UPLOAD_DIR)
    os.makedirs(upload_dir, exist_ok=True)

    ext = os.path.splitext(filename)[1] or ".png"
    avatar_filename = f"{user_id}{ext}"
    avatar_path = os.path.join(upload_dir, avatar_filename)

    with open(avatar_path, "wb") as f:
        f.write(file_content)

    avatar_url = f"/uploads/{avatar_filename}"

    result = await db.execute(select(User).where(User.id == user_id, User.is_deleted == False))
    user = result.scalar_one_or_none()
    if user:
        user.avatar_url = avatar_url
        await db.flush()

    return avatar_url
