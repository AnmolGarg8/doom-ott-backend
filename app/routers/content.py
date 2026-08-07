import math
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import get_current_user, get_db
from app.models.content import (
    Category,
    Content,
    Episode,
    Watchlist,
    WatchProgress,
)
from app.models.enums import ContentStatus, ContentType
from app.models.user import Profile, User
from app.schemas.content import (
    CategoryResponse,
    ContentDetailResponse,
    ContentResponse,
    PaginatedContentResponse,
    WatchlistResponse,
    WatchProgressResponse,
    WatchProgressUpsert,
)

router = APIRouter(tags=["Content Catalog & Watch Tracking"])


# --- Public Content Browsing ---

@router.get(
    "/content",
    response_model=PaginatedContentResponse,
    summary="List published content catalog with filters and pagination",
)
async def list_content(
    type: Optional[ContentType] = Query(None, description="Filter by content type (movie, short, series)"),
    genre: Optional[str] = Query(None, description="Filter by genre"),
    language: Optional[str] = Query(None, description="Filter by language"),
    min_rating: Optional[float] = Query(None, description="Minimum content rating"),
    search: Optional[str] = Query(None, description="Search query matching title"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
):
    query = select(Content).where(Content.status == ContentStatus.PUBLISHED)

    if type:
        query = query.where(Content.type == type)
    if language:
        query = query.where(func.lower(Content.language) == language.lower())
    if search:
        query = query.where(Content.title.ilike(f"%{search}%"))

    # Execute query to fetch candidates
    result = await db.execute(query.order_by(Content.created_at.desc()))
    all_content = result.scalars().all()

    # In-memory genre / min_rating filter for JSON field compatibility
    filtered = []
    for c in all_content:
        if genre and genre.lower() not in [g.lower() for g in (c.genre or [])]:
            continue
        filtered.append(c)

    total = len(filtered)
    total_pages = math.ceil(total / page_size) if total > 0 else 1
    offset = (page - 1) * page_size
    page_items = filtered[offset : offset + page_size]

    return PaginatedContentResponse(
        items=[ContentResponse.model_validate(item) for item in page_items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/content/{content_id}",
    response_model=ContentDetailResponse,
    summary="Get full content details including episodes if series",
)
async def get_content_detail(
    content_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Content)
        .options(selectinload(Content.episodes))
        .where(Content.id == content_id, Content.status == ContentStatus.PUBLISHED)
    )
    content = result.scalars().first()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content not found or not published.",
        )

    # Sort episodes if series
    if content.episodes:
        content.episodes.sort(key=lambda ep: (ep.season, ep.episode_no))

    return content


@router.get(
    "/content/{content_id}/similar",
    response_model=List[ContentResponse],
    summary="Get similar content recommendations based on genre overlap",
)
async def get_similar_content(
    content_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Content).where(Content.id == content_id))
    target = result.scalars().first()
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target content not found.",
        )

    target_genres = [g.lower() for g in (target.genre or [])]

    # Fetch other published content
    res = await db.execute(
        select(Content).where(
            Content.id != content_id, Content.status == ContentStatus.PUBLISHED
        )
    )
    others = res.scalars().all()

    # Score by number of overlapping genres
    scored = []
    for item in others:
        item_genres = [g.lower() for g in (item.genre or [])]
        overlap = len(set(target_genres).intersection(item_genres))
        if overlap > 0:
            scored.append((overlap, item))

    scored.sort(key=lambda x: x[0], reverse=True)
    similar_items = [item for _, item in scored[:10]]
    return similar_items


@router.get(
    "/categories",
    response_model=List[CategoryResponse],
    summary="List all categories/genres",
)
async def list_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Category).order_by(Category.name.asc()))
    return result.scalars().all()


# --- Watchlist Endpoints ---

@router.get(
    "/watchlist",
    response_model=List[WatchlistResponse],
    summary="Get current user's watchlist",
)
async def get_user_watchlist(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Watchlist).where(Watchlist.user_id == current_user.id).order_by(Watchlist.added_at.desc())
    )
    items = result.scalars().all()

    # Load associated content for each item
    response_list = []
    for item in items:
        res = await db.execute(select(Content).where(Content.id == item.content_id))
        content_obj = res.scalars().first()
        response_list.append(
            WatchlistResponse(
                user_id=item.user_id,
                content_id=item.content_id,
                added_at=item.added_at,
                content=ContentResponse.model_validate(content_obj) if content_obj else None,
            )
        )
    return response_list


@router.post(
    "/watchlist/{content_id}",
    response_model=WatchlistResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add content to user's watchlist",
)
async def add_to_watchlist(
    content_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    res_c = await db.execute(select(Content).where(Content.id == content_id))
    content_obj = res_c.scalars().first()
    if not content_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content not found.",
        )

    res_w = await db.execute(
        select(Watchlist).where(Watchlist.user_id == current_user.id, Watchlist.content_id == content_id)
    )
    existing = res_w.scalars().first()
    if existing:
        return WatchlistResponse(
            user_id=existing.user_id,
            content_id=existing.content_id,
            added_at=existing.added_at,
            content=ContentResponse.model_validate(content_obj),
        )

    watchlist_item = Watchlist(user_id=current_user.id, content_id=content_id)
    db.add(watchlist_item)
    await db.commit()
    await db.refresh(watchlist_item)

    return WatchlistResponse(
        user_id=watchlist_item.user_id,
        content_id=watchlist_item.content_id,
        added_at=watchlist_item.added_at,
        content=ContentResponse.model_validate(content_obj),
    )


@router.delete(
    "/watchlist/{content_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove content from user's watchlist",
)
async def remove_from_watchlist(
    content_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    res_w = await db.execute(
        select(Watchlist).where(Watchlist.user_id == current_user.id, Watchlist.content_id == content_id)
    )
    existing = res_w.scalars().first()
    if existing:
        await db.delete(existing)
        await db.commit()
    return None


# --- Watch Progress Endpoints ---

@router.get(
    "/watch-progress",
    response_model=List[WatchProgressResponse],
    summary="Get profile's continue watching list sorted by most recent",
)
async def get_watch_progress(
    profile_id: Optional[uuid.UUID] = Query(None, description="Profile ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify profile belongs to user if profile_id provided, otherwise get all user profiles
    res_p = await db.execute(select(Profile.id).where(Profile.user_id == current_user.id))
    user_profile_ids = [p for p in res_p.scalars().all()]

    if profile_id:
        if profile_id not in user_profile_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to requested profile.",
            )
        target_profile_ids = [profile_id]
    else:
        target_profile_ids = user_profile_ids

    if not target_profile_ids:
        return []

    result = await db.execute(
        select(WatchProgress)
        .where(WatchProgress.profile_id.in_(target_profile_ids))
        .order_by(WatchProgress.updated_at.desc())
    )
    items = result.scalars().all()

    response_list = []
    for item in items:
        res_c = await db.execute(select(Content).where(Content.id == item.content_id))
        content_obj = res_c.scalars().first()
        response_list.append(
            WatchProgressResponse(
                profile_id=item.profile_id,
                content_id=item.content_id,
                position_seconds=item.position_seconds,
                updated_at=item.updated_at,
                content=ContentResponse.model_validate(content_obj) if content_obj else None,
            )
        )
    return response_list


@router.put(
    "/watch-progress/{content_id}",
    response_model=WatchProgressResponse,
    summary="Upsert watch progress position for a profile",
)
async def upsert_watch_progress(
    content_id: uuid.UUID,
    body: WatchProgressUpsert,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify profile belongs to current user
    res_p = await db.execute(
        select(Profile).where(Profile.id == body.profile_id, Profile.user_id == current_user.id)
    )
    profile = res_p.scalars().first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Profile not found or access denied.",
        )

    res_c = await db.execute(select(Content).where(Content.id == content_id))
    content_obj = res_c.scalars().first()
    if not content_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content not found.",
        )

    res_wp = await db.execute(
        select(WatchProgress).where(
            WatchProgress.profile_id == body.profile_id, WatchProgress.content_id == content_id
        )
    )
    existing = res_wp.scalars().first()
    if existing:
        existing.position_seconds = body.position_seconds
        wp_item = existing
    else:
        wp_item = WatchProgress(
            profile_id=body.profile_id,
            content_id=content_id,
            position_seconds=body.position_seconds,
        )
        db.add(wp_item)

    await db.commit()
    await db.refresh(wp_item)

    return WatchProgressResponse(
        profile_id=wp_item.profile_id,
        content_id=wp_item.content_id,
        position_seconds=wp_item.position_seconds,
        updated_at=wp_item.updated_at,
        content=ContentResponse.model_validate(content_obj),
    )
