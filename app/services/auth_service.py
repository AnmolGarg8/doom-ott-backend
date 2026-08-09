import hashlib
import logging
import random
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.models.billing import Subscription, SubscriptionPlan
from app.models.enums import AuthProvider, SubscriptionStatus
from app.models.user import AdminUser, Profile, Session, User
from app.providers.sms import get_sms_provider
from app.schemas.auth import TokenResponse

logger = logging.getLogger("doom_ott.auth_service")

# Fallback in-memory store if Redis is unavailable during local dev without Docker
_in_memory_redis_fallback = {}


async def redis_set(redis: Optional[Redis], key: str, value: str, ex: Optional[int] = None):
    if redis:
        try:
            await redis.set(key, value, ex=ex)
            return
        except Exception as e:
            logger.warning(f"Redis unavailable, using memory fallback: {e}")
    _in_memory_redis_fallback[key] = value


async def redis_get(redis: Optional[Redis], key: str) -> Optional[str]:
    if redis:
        try:
            val = await redis.get(key)
            if val is not None:
                return str(val)
        except Exception as e:
            logger.warning(f"Redis unavailable, using memory fallback: {e}")
    return _in_memory_redis_fallback.get(key)


async def redis_delete(redis: Optional[Redis], key: str):
    if redis:
        try:
            await redis.delete(key)
        except Exception as e:
            logger.warning(f"Redis delete failed: {e}")
    _in_memory_redis_fallback.pop(key, None)


async def redis_incr(redis: Optional[Redis], key: str, ex: Optional[int] = None) -> int:
    if redis:
        try:
            val = await redis.incr(key)
            if val == 1 and ex:
                await redis.expire(key, ex)
            return val
        except Exception as e:
            logger.warning(f"Redis incr failed: {e}")
    current = int(_in_memory_redis_fallback.get(key, "0")) + 1
    _in_memory_redis_fallback[key] = str(current)
    return current


class AuthService:
    """Business logic service for Authentication, OTPs, JWT Tokens, and Session Tracking."""

    @staticmethod
    async def send_otp(phone: str, db: AsyncSession, redis: Optional[Redis]) -> dict:
        # Rate limit: max 3 requests per phone per 10 minutes (600 seconds)
        rate_key = f"rate:otp:{phone}"
        requests_count = await redis_incr(redis, rate_key, ex=600)
        if requests_count > 3:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many OTP requests for this phone number. Please wait 10 minutes.",
            )

        # Generate 6-digit random OTP
        otp = f"{random.randint(100000, 999999)}"

        # Store in Redis with 5-minute TTL (300 seconds)
        otp_key = f"otp:{phone}"
        await redis_set(redis, otp_key, otp, ex=300)

        # Reset attempt count
        attempt_key = f"attempts:otp:{phone}"
        await redis_delete(redis, attempt_key)

        # Send via configured SMS provider
        sms_provider = get_sms_provider()
        success = await sms_provider.send_otp(phone, otp)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send SMS. Please try again later.",
            )

        return {"message": "OTP sent successfully."}

    @staticmethod
    async def verify_otp(
        phone: str,
        otp: str,
        device_id: str,
        device_name: str,
        db: AsyncSession,
        redis: Optional[Redis],
    ):
        attempt_key = f"attempts:otp:{phone}"
        attempts = int(await redis_get(redis, attempt_key) or "0")
        if attempts >= 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Max verification attempts exceeded. Please request a new OTP.",
            )

        otp_key = f"otp:{phone}"
        stored_otp = await redis_get(redis, otp_key)
        if not stored_otp:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP expired or not found. Please request a new OTP.",
            )

        if stored_otp != otp and not (settings.SMS_PROVIDER == "mock" and otp == "123456"):
            await redis_incr(redis, attempt_key, ex=300)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid OTP.",
            )

        # On successful verification, delete OTP keys
        await redis_delete(redis, otp_key)
        await redis_delete(redis, attempt_key)

        # Find or create User record for this phone number
        result = await db.execute(select(User).where(User.phone == phone))
        user = result.scalars().first()
        if not user:
            user = User(
                phone=phone,
                name=f"User {phone[-4:]}" if len(phone) >= 4 else "User",
                auth_provider=AuthProvider.PHONE,
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)

        return await AuthService._handle_session_and_issue_tokens(
            user.id, device_id, device_name, db, redis
        )

    @staticmethod
    async def email_signup(
        email: str,
        password: str,
        name: str,
        device_id: str,
        device_name: str,
        db: AsyncSession,
        redis: Optional[Redis],
    ):
        result = await db.execute(select(User).where(User.email == email))
        existing_user = result.scalars().first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is already registered.",
            )

        password_hash = get_password_hash(password)
        user = User(
            email=email,
            password_hash=password_hash,
            name=name,
            auth_provider=AuthProvider.EMAIL,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        return await AuthService._handle_session_and_issue_tokens(
            user.id, device_id, device_name, db, redis
        )

    @staticmethod
    async def email_login(
        email: str,
        password: str,
        device_id: str,
        device_name: str,
        db: AsyncSession,
        redis: Optional[Redis],
    ):
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalars().first()
        if not user or not user.password_hash or not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )

        return await AuthService._handle_session_and_issue_tokens(
            user.id, device_id, device_name, db, redis
        )

    @staticmethod
    async def admin_login(
        email: str,
        password: str,
        device_id: str,
        device_name: str,
        db: AsyncSession,
        redis: Optional[Redis],
    ):
        result = await db.execute(select(AdminUser).where(AdminUser.email == email))
        admin = result.scalars().first()
        if not admin or not verify_password(password, admin.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid admin email or password.",
            )

        return await AuthService._handle_session_and_issue_tokens(
            admin.id, device_id, device_name, db, redis
        )

    @staticmethod
    async def social_auth(
        id_token: str,
        provider: AuthProvider,
        device_id: str,
        device_name: str,
        db: AsyncSession,
        redis: Optional[Redis],
    ):
        if id_token.startswith("mock_"):
            token_suffix = id_token[5:]
            fake_email = f"{provider.value}_{token_suffix}@mock.com"
            fake_name = f"Mock {provider.value.title()} User"
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid social token. (Use token starting with 'mock_' for development)",
            )

        result = await db.execute(select(User).where(User.email == fake_email))
        user = result.scalars().first()
        if not user:
            user = User(
                email=fake_email,
                name=fake_name,
                auth_provider=provider,
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)

        return await AuthService._handle_session_and_issue_tokens(
            user.id, device_id, device_name, db, redis
        )

    @staticmethod
    async def refresh_tokens(
        refresh_token: str,
        device_id: str,
        device_name: str,
        db: AsyncSession,
        redis: Optional[Redis],
    ):
        payload = decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token.",
            )

        user_id_str = payload.get("sub")
        if not user_id_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload.",
            )

        stored_hash = await redis_get(redis, f"refresh_token:{user_id_str}")
        if not stored_hash or not verify_password(refresh_token, stored_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token revoked or expired.",
            )

        import uuid
        user_id = uuid.UUID(user_id_str)
        return await AuthService._handle_session_and_issue_tokens(
            user_id, device_id, device_name, db, redis
        )

    @staticmethod
    async def logout(user_id: str, redis: Optional[Redis]) -> dict:
        await redis_delete(redis, f"refresh_token:{user_id}")
        return {"message": "Successfully logged out."}

    @staticmethod
    async def _handle_session_and_issue_tokens(
        user_id,
        device_id: str,
        device_name: str,
        db: AsyncSession,
        redis: Optional[Redis],
    ):
        now = datetime.now(timezone.utc)

        # 1. Determine user's max_devices limit from active subscription plan (default to 1 device if none)
        res_sub = await db.execute(
            select(SubscriptionPlan.max_devices)
            .join(Subscription, Subscription.plan_id == SubscriptionPlan.id)
            .where(
                Subscription.user_id == user_id,
                Subscription.status == SubscriptionStatus.ACTIVE,
                Subscription.end_date > now,
            )
        )
        max_devices = res_sub.scalar()
        if max_devices is None:
            max_devices = 1

        # 2. Get user's current active sessions
        res_sessions = await db.execute(
            select(Session)
            .where(Session.user_id == user_id)
            .order_by(Session.last_active_at.desc())
        )
        active_sessions = res_sessions.scalars().all()

        # 3. Check if device_id already has an active session
        existing_session = next((s for s in active_sessions if s.device_id == device_id), None)

        if not existing_session and len(active_sessions) >= max_devices:
            # Device limit reached & new device -> return 409 Conflict with active sessions list
            sessions_list = [
                {
                    "id": str(s.id),
                    "device_name": s.device_name,
                    "last_active_at": s.last_active_at.isoformat(),
                    "created_at": s.created_at.isoformat(),
                }
                for s in active_sessions
            ]
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={
                    "detail": f"Device limit reached. Your current plan allows up to {max_devices} active device(s). Please log out from another device.",
                    "active_sessions": sessions_list,
                },
            )

        # 4. Issue tokens
        user_id_str = str(user_id)
        access_token = create_access_token(
            subject=user_id_str, expires_delta=timedelta(minutes=15)
        )
        refresh_token = create_refresh_token(
            subject=user_id_str, expires_delta=timedelta(days=30)
        )
        refresh_hash = get_password_hash(refresh_token)

        # Store refresh token in Redis
        redis_key = f"refresh_token:{user_id_str}"
        await redis_set(redis, redis_key, refresh_hash, ex=30 * 86400)

        # 5. Create or update Session record
        if existing_session:
            existing_session.device_name = device_name
            existing_session.last_active_at = now
            existing_session.refresh_token_hash = refresh_hash
        else:
            new_session = Session(
                user_id=user_id,
                device_id=device_id,
                device_name=device_name,
                refresh_token_hash=refresh_hash,
                created_at=now,
                last_active_at=now,
            )
            db.add(new_session)

        await db.commit()

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
        )
