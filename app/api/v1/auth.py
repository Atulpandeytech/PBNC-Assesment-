from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.dependencies import get_current_user
from app.core.config import settings
from app.db.models import User
from app.db.session import get_db
from app.schemas.auth import (
    RefreshTokenRequest,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    req: UserRegisterRequest,
    session: AsyncSession = Depends(get_db),
):
    """Register a new user account."""
    auth_service = AuthService(session)
    user = await auth_service.register(req)
    return user


@router.post("/login", response_model=TokenResponse)
async def login_user(
    req: UserLoginRequest,
    session: AsyncSession = Depends(get_db),
):
    """Authenticate with email and password to receive JWT access and refresh tokens."""
    auth_service = AuthService(session)
    user, access_token, refresh_token = await auth_service.login(req)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_access_token(
    req: RefreshTokenRequest,
    session: AsyncSession = Depends(get_db),
):
    """Exchange a valid refresh token for a new access and refresh token pair."""
    auth_service = AuthService(session)
    access_token, refresh_token = await auth_service.refresh(req.refresh_token)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
):
    """Retrieve profile and role of currently authenticated user."""
    return current_user
