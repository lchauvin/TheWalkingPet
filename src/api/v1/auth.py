from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.dependencies import get_current_user, get_db
from src.schemas.user import (
    FcmTokenUpdate,
    GoogleAuthRequest,
    LogoutRequest,
    RefreshRequest,
    TokenResponse,
    UserLogin,
    UserOut,
    UserRegister,
)
from src.services import auth_service
from src.utils.rate_limit import limiter

router = APIRouter()


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.rate_limit_register)
async def register(
    request: Request,
    response: Response,
    data: UserRegister,
    db: AsyncSession = Depends(get_db),
):
    try:
        user = await auth_service.register_user(db, data.email, data.password, data.display_name)
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    return user


@router.post("/login", response_model=TokenResponse)
@limiter.limit(settings.rate_limit_login)
async def login(
    request: Request,
    response: Response,
    data: UserLogin,
    db: AsyncSession = Depends(get_db),
):
    try:
        user = await auth_service.authenticate_user(db, data.email, data.password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    return await auth_service.issue_tokens(db, user.id)


@router.post("/google", response_model=TokenResponse)
@limiter.limit(settings.rate_limit_login)
async def google_login(
    request: Request,
    response: Response,
    data: GoogleAuthRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await auth_service.google_auth(db, data.id_token)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit(settings.rate_limit_refresh)
async def refresh(
    request: Request,
    response: Response,
    data: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await auth_service.refresh_tokens(db, data.refresh_token)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    data: LogoutRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Revoke the presented refresh token, or every session when none is given."""
    await auth_service.logout(db, data.refresh_token if data else None, current_user.id)


@router.get("/me", response_model=UserOut)
async def me(current_user=Depends(get_current_user)):
    return current_user


@router.put("/fcm-token", status_code=status.HTTP_204_NO_CONTENT)
async def update_fcm_token(
    data: FcmTokenUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    current_user.fcm_token = data.fcm_token
    await db.commit()
