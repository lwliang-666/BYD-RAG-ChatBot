"""
用户服务模块

提供用户资料查询与修改、用户名修改和头像上传等业务逻辑。
头像上传将文件保存到本地 uploads 目录并更新数据库中的头像 URL。
"""

import os
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.user import User
from app.schemas.user import UserProfileUpdate, UsernameUpdate

settings = get_settings()


async def get_user_profile(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    """根据用户 ID 查询未删除的用户资料"""
    result = await db.execute(select(User).where(User.id == user_id, User.is_deleted == False))
    return result.scalar_one_or_none()


async def update_user_profile(db: AsyncSession, user_id: uuid.UUID, data: UserProfileUpdate) -> User | None:
    """更新用户资料（目前仅支持修改显示名称）"""
    result = await db.execute(select(User).where(User.id == user_id, User.is_deleted == False))
    user = result.scalar_one_or_none()
    if not user:
        return None

    if data.display_name is not None:
        user.display_name = data.display_name

    await db.flush()
    return user


async def update_username(db: AsyncSession, user_id: uuid.UUID, data: UsernameUpdate) -> User:
    """修改用户名

    先检查新用户名是否已被其他用户占用，再更新当前用户的用户名。
    用户名被占用时抛出 ValueError。
    """
    # 查询新用户名是否已被其他用户使用
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
    """上传用户头像

    将头像文件保存到 uploads 目录，文件名格式为 {user_id}.{ext}，
    同时更新数据库中的 avatar_url 字段，返回头像访问 URL。
    """
    upload_dir = os.path.abspath(settings.UPLOAD_DIR)
    os.makedirs(upload_dir, exist_ok=True)

    # 以用户 ID 命名头像文件，确保每个用户只有一个头像文件
    ext = os.path.splitext(filename)[1] or ".png"
    avatar_filename = f"{user_id}{ext}"
    avatar_path = os.path.join(upload_dir, avatar_filename)

    with open(avatar_path, "wb") as f:
        f.write(file_content)

    avatar_url = f"/uploads/{avatar_filename}"

    # 更新数据库中的头像 URL
    result = await db.execute(select(User).where(User.id == user_id, User.is_deleted == False))
    user = result.scalar_one_or_none()
    if user:
        user.avatar_url = avatar_url
        await db.flush()

    return avatar_url
