import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password, get_password_hash, create_access_token, create_refresh_token
from app.models.user import User
from app.schemas.auth import RegisterRequest, TokenResponse


async def register_user(db: AsyncSession, request: RegisterRequest) -> User:
    result = await db.execute(select(User).where(User.username == request.username, User.is_deleted == False))
    existing = result.scalar_one_or_none()
    if existing:
        raise ValueError("用户名已存在")

    user = User(
        username=request.username,
        display_name=request.username,
        password_hash=get_password_hash(request.password),
    )
    db.add(user)
    await db.flush()
    return user


async def authenticate_user(db: AsyncSession, username: str, password: str) -> User:
    result = await db.execute(select(User).where(User.username == username, User.is_deleted == False))
    user = result.scalar_one_or_none()
    if not user:
        raise ValueError("用户名或密码错误")
    if not verify_password(password, user.password_hash):
        raise ValueError("用户名或密码错误")
    return user


def create_tokens(user_id: uuid.UUID) -> TokenResponse:
    data = {"sub": str(user_id)}
    return TokenResponse(
        access_token=create_access_token(data),
        refresh_token=create_refresh_token(data),
    )


async def refresh_access_token(db: AsyncSession, refresh_token: str) -> TokenResponse:
    from app.core.security import decode_token

    payload = decode_token(refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise ValueError("无效的刷新令牌")

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id), User.is_deleted == False))
    user = result.scalar_one_or_none()
    if user is None:
        raise ValueError("用户不存在")

    return create_tokens(user.id)
