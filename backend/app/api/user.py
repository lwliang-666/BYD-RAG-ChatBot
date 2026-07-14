from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.user import UserProfileResponse, UserProfileUpdate, UsernameUpdate
from app.services.user_service import get_user_profile, update_user_profile, update_username, update_avatar

settings = get_settings()
router = APIRouter(prefix="/api/user", tags=["用户"])


@router.get("/profile", response_model=UserProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_user),
):
    return current_user


@router.put("/profile", response_model=UserProfileResponse)
async def update_profile(
    data: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user = await update_user_profile(db, current_user.id, data)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    return user


@router.put("/username", response_model=UserProfileResponse)
async def change_username(
    data: UsernameUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        user = await update_username(db, current_user.id, data)
        return user
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post("/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if file.content_type not in ["image/jpeg", "image/png", "image/gif", "image/webp"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="仅支持 jpg/png/gif/webp 格式",
        )

    file_content = await file.read()
    max_size = settings.MAX_AVATAR_SIZE_MB * 1024 * 1024
    if len(file_content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"头像大小不能超过 {settings.MAX_AVATAR_SIZE_MB}MB",
        )

    avatar_url = await update_avatar(db, current_user.id, file_content, file.filename or "avatar.png")
    return {"avatar_url": avatar_url}
