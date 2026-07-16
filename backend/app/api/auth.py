"""
认证 API 路由模块

提供用户注册、登录和 Token 刷新三个接口，
负责请求参数校验、调用认证服务并返回 JWT 令牌。
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, RefreshRequest
from app.services.auth_service import register_user, authenticate_user, create_tokens, refresh_access_token

router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """用户注册接口

    创建新用户并返回访问令牌和刷新令牌。
    用户名重复时返回 409，密码过长时返回 422。
    """
    try:
        user = await register_user(db, request)
        return create_tokens(user.id)
    except ValueError as e:
        msg = str(e)
        if "密码过长" in msg or "72 bytes" in msg:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="密码过长，最多支持72个字节")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=msg)
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="用户名已存在")


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """用户登录接口

    验证用户名和密码，成功后返回访问令牌和刷新令牌。
    认证失败时返回 401。
    """
    try:
        user = await authenticate_user(db, request.username, request.password)
        return create_tokens(user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Token 刷新接口

    使用刷新令牌换取新的访问令牌和刷新令牌。
    令牌无效或过期时返回 401。
    """
    try:
        return await refresh_access_token(db, request.refresh_token)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
