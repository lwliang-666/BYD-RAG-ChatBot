"""
认证服务模块

提供用户注册、登录认证、JWT 令牌创建和刷新等业务逻辑。
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password, get_password_hash, create_access_token, create_refresh_token
from app.models.user import User
from app.schemas.auth import RegisterRequest, TokenResponse


async def register_user(db: AsyncSession, request: RegisterRequest) -> User:
    """注册新用户

    检查用户名是否已存在，不存在则创建用户并写入数据库。
    用户名重复时抛出 ValueError。
    """
    result = await db.execute(select(User).where(User.username == request.username, User.is_deleted == False))
    existing = result.scalar_one_or_none()
    if existing:
        raise ValueError("用户名已存在")

    user = User(
        username=request.username,
        # 默认显示名称与用户名相同
        display_name=request.username,
        password_hash=get_password_hash(request.password),
    )
    db.add(user)
    await db.flush()
    return user


async def authenticate_user(db: AsyncSession, username: str, password: str) -> User:
    """验证用户登录凭据

    根据用户名查找用户并验证密码，认证失败时抛出 ValueError。
    """
    result = await db.execute(select(User).where(User.username == username, User.is_deleted == False))
    user = result.scalar_one_or_none()
    if not user:
        raise ValueError("用户名或密码错误")
    if not verify_password(password, user.password_hash):
        raise ValueError("用户名或密码错误")
    return user


def create_tokens(user_id: uuid.UUID) -> TokenResponse:
    """为指定用户创建访问令牌和刷新令牌"""
    data = {"sub": str(user_id)}
    return TokenResponse(
        access_token=create_access_token(data),
        refresh_token=create_refresh_token(data),
    )


async def refresh_access_token(db: AsyncSession, refresh_token: str) -> TokenResponse:
    """使用刷新令牌换取新的令牌对

    验证刷新令牌的有效性和类型，确认用户仍存在后重新生成令牌。
    令牌无效或用户不存在时抛出 ValueError。
    """
    from app.core.security import decode_token

    payload = decode_token(refresh_token)
    # 校验令牌类型必须为 refresh
    if payload is None or payload.get("type") != "refresh":
        raise ValueError("无效的刷新令牌")

    user_id = payload.get("sub")
    # 确认用户仍然存在且未删除
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id), User.is_deleted == False))
    user = result.scalar_one_or_none()
    if user is None:
        raise ValueError("用户不存在")

    return create_tokens(user.id)
