from typing import Optional
from fastapi import APIRouter, Depends, Request, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.limiter import limiter
from app.dependencies import get_current_user, get_db, get_redis
from app.models.enums import AuthProvider
from app.models.user import User
from app.schemas.auth import (
    AdminLoginRequest,
    EmailLoginRequest,
    EmailSignupRequest,
    MessageResponse,
    OTPSendRequest,
    OTPVerifyRequest,
    RefreshTokenRequest,
    SocialAuthRequest,
    TokenResponse,
    UserResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/otp/send",
    response_model=MessageResponse,
    summary="Send OTP to phone number",
    description="Generates a 6-digit OTP, stores it in Redis with 5-min TTL, rate-limits to 3 requests per 10 mins, and sends via SMS provider.",
)
async def send_otp(
    body: OTPSendRequest,
    db: AsyncSession = Depends(get_db),
    redis: Optional[Redis] = Depends(get_redis),
):
    return await AuthService.send_otp(body.phone, db, redis)


@router.post(
    "/otp/verify",
    response_model=TokenResponse,
    summary="Verify OTP & Login/Signup",
    description="Verifies OTP against Redis. On success, finds or creates User and returns JWT access + refresh tokens.",
)
async def verify_otp(
    body: OTPVerifyRequest,
    db: AsyncSession = Depends(get_db),
    redis: Optional[Redis] = Depends(get_redis),
):
    return await AuthService.verify_otp(body.phone, body.otp, body.device_id, body.device_name, db, redis)


@router.post(
    "/email/signup",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Email & Password Signup",
)
@limiter.limit("5/hour")
async def email_signup(
    request: Request,
    body: EmailSignupRequest,
    db: AsyncSession = Depends(get_db),
    redis: Optional[Redis] = Depends(get_redis),
):
    return await AuthService.email_signup(body.email, body.password, body.name, body.device_id, body.device_name, db, redis)


@router.post(
    "/email/login",
    response_model=TokenResponse,
    summary="Email & Password Login",
)
@limiter.limit("5/15minutes")
async def email_login(
    request: Request,
    body: EmailLoginRequest,
    db: AsyncSession = Depends(get_db),
    redis: Optional[Redis] = Depends(get_redis),
):
    return await AuthService.email_login(body.email, body.password, body.device_id, body.device_name, db, redis)


@router.post(
    "/admin/login",
    response_model=TokenResponse,
    summary="Admin Email & Password Login",
    tags=["Admin Auth"],
)
@limiter.limit("5/15minutes")
async def admin_login(
    request: Request,
    body: AdminLoginRequest,
    db: AsyncSession = Depends(get_db),
    redis: Optional[Redis] = Depends(get_redis),
):
    return await AuthService.admin_login(body.email, body.password, body.device_id, body.device_name, db, redis)


@router.post(
    "/social/google",
    response_model=TokenResponse,
    summary="Google Social Login/Signup",
)
async def social_google(
    body: SocialAuthRequest,
    db: AsyncSession = Depends(get_db),
    redis: Optional[Redis] = Depends(get_redis),
):
    return await AuthService.social_auth(body.id_token, AuthProvider.GOOGLE, body.device_id, body.device_name, db, redis)


@router.post(
    "/social/apple",
    response_model=TokenResponse,
    summary="Apple Social Login/Signup",
)
async def social_apple(
    body: SocialAuthRequest,
    db: AsyncSession = Depends(get_db),
    redis: Optional[Redis] = Depends(get_redis),
):
    return await AuthService.social_auth(body.id_token, AuthProvider.APPLE, body.device_id, body.device_name, db, redis)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh Access Token",
)
async def refresh_tokens(
    body: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
    redis: Optional[Redis] = Depends(get_redis),
):
    return await AuthService.refresh_tokens(body.refresh_token, body.device_id, body.device_name, db, redis)


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Logout & Revoke Tokens",
)
async def logout(
    current_user: User = Depends(get_current_user),
    redis: Optional[Redis] = Depends(get_redis),
):
    return await AuthService.logout(str(current_user.id), redis)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get Current Authenticated User (Protected Route Test)",
)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user
