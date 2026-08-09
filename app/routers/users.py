import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from redis.asyncio import Redis
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import get_current_user, get_db, get_redis
from app.models.user import Profile, Session, User
from app.schemas.users import (
    ProfileCreate,
    ProfileResponse,
    ProfileUpdate,
    SessionResponse,
    UserDetailResponse,
)
from app.services.auth_service import redis_delete

router = APIRouter(prefix="/users", tags=["User Profiles & Sessions"])


@router.get("/me", response_model=UserDetailResponse, summary="Get current user details with profiles")
async def get_my_details(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).options(selectinload(User.profiles)).where(User.id == current_user.id)
    )
    user = result.scalars().first()
    return user


# --- Session Management Endpoints ---

@router.get(
    "/sessions",
    response_model=List[SessionResponse],
    summary="List active sessions for current user (Auth Required)",
)
async def get_user_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Session)
        .where(Session.user_id == current_user.id)
        .order_by(Session.last_active_at.desc())
    )
    return result.scalars().all()


@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke a specific active session (Auth Required)",
)
async def revoke_session(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: Optional[Redis] = Depends(get_redis),
):
    result = await db.execute(
        select(Session).where(Session.id == session_id, Session.user_id == current_user.id)
    )
    session = result.scalars().first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or access denied.",
        )

    # Invalidate session refresh token in Redis
    await redis_delete(redis, f"refresh_token:{current_user.id}")

    await db.delete(session)
    await db.commit()
    return None


# --- Profile Endpoints ---

@router.post(
    "/profiles",
    response_model=List[ProfileResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new profile (max 4 per user). Auto-creates a companion Kids profile on first profile creation.",
)
async def create_profile(
    body: ProfileCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Enforce maximum 4 profiles per user
    result = await db.execute(
        select(func.count(Profile.id)).where(Profile.user_id == current_user.id)
    )
    count = result.scalar() or 0
    if count >= 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum profile limit reached. Users can have at most 4 profiles.",
        )

    is_first_profile = (count == 0)

    profile = Profile(
        user_id=current_user.id,
        name=body.name,
        avatar_key=body.avatar_key,
        is_kids_profile=body.is_kids_profile,
    )
    db.add(profile)
    created_profiles = [profile]

    if is_first_profile:
        kids_profile = Profile(
            user_id=current_user.id,
            name="Kids",
            avatar_key="kids_default",
            is_kids_profile=True,
        )
        db.add(kids_profile)
        created_profiles.append(kids_profile)

    await db.commit()
    for p in created_profiles:
        await db.refresh(p)
    return created_profiles


@router.patch(
    "/profiles/{profile_id}",
    response_model=ProfileResponse,
    summary="Update a profile",
)
async def update_profile(
    profile_id: uuid.UUID,
    body: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Profile).where(Profile.id == profile_id, Profile.user_id == current_user.id)
    )
    profile = result.scalars().first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found or access denied.",
        )

    if body.name is not None:
        profile.name = body.name
    if body.avatar_key is not None:
        profile.avatar_key = body.avatar_key
    if body.is_kids_profile is not None:
        profile.is_kids_profile = body.is_kids_profile

    await db.commit()
    await db.refresh(profile)
    return profile


@router.delete(
    "/profiles/{profile_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a profile",
)
async def delete_profile(
    profile_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Profile).where(Profile.id == profile_id, Profile.user_id == current_user.id)
    )
    profile = result.scalars().first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found or access denied.",
        )

    await db.delete(profile)
    await db.commit()
    return None
