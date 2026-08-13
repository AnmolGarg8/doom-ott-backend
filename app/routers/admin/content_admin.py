import math
import os
import uuid
from typing import List, Optional, Tuple
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.dependencies import get_current_admin, get_db
from app.models.content import Content, Episode, Review, VideoAsset
from app.models.enums import ContentStatus, ContentType, VideoAssetStatus
from app.models.user import AdminUser
from app.providers.image import get_image_provider
from app.providers.video import get_video_provider
from app.schemas.admin_content import (
    AdminContentDetailResponse,
    ChecklistItem,
    ContentCreateRequest,
    ContentUpdateRequest,
    EpisodeCreateRequest,
    EpisodeUpdateRequest,
    EpisodeVideoUploadResponse,
    ImageUploadResponse,
    PublishChecklistResponse,
    VideoUploadResponse,
    VideoWebhookPayload,
)
from app.schemas.content import ContentResponse, EpisodeResponse, PaginatedContentResponse

router = APIRouter(prefix="/admin", tags=["Admin Content & Video Pipeline"])


# --- Helper Function for Publish Readiness Checklist ---

async def compute_publish_checklist(content: Content, db: AsyncSession) -> Tuple[bool, List[dict]]:
    checks = []

    # 1. Title & synopsis filled in
    title_ok = bool(content.title and content.title.strip())
    synopsis_ok = bool(content.synopsis and content.synopsis.strip())
    checks.append({
        "label": "Title and synopsis filled in",
        "passed": bool(title_ok and synopsis_ok),
    })

    # 2. Poster image uploaded
    checks.append({
        "label": "Poster image uploaded",
        "passed": bool(content.poster_url and content.poster_url.strip()),
    })

    # 3. Backdrop image uploaded
    checks.append({
        "label": "Backdrop image uploaded",
        "passed": bool(content.backdrop_url and content.backdrop_url.strip()),
    })

    # 4. Genre selected
    checks.append({
        "label": "Genre selected",
        "passed": bool(content.genre and len(content.genre) > 0),
    })

    # 5. Video readiness
    if content.type == ContentType.MOVIE:
        res_v = await db.execute(
            select(VideoAsset).where(
                VideoAsset.content_id == content.id,
                VideoAsset.status == VideoAssetStatus.READY,
            )
        )
        ready_asset = res_v.scalars().first()
        checks.append({
            "label": "Video ready",
            "passed": ready_asset is not None,
        })
    else:
        # Series: check all episodes have ready video
        res_ep = await db.execute(
            select(Episode).where(Episode.series_id == content.id)
        )
        episodes = res_ep.scalars().all()
        if not episodes:
            checks.append({
                "label": "All episodes have video ready",
                "passed": False,
            })
        else:
            ep_ids = [ep.id for ep in episodes]
            res_v = await db.execute(
                select(VideoAsset.episode_id).where(
                    VideoAsset.episode_id.in_(ep_ids),
                    VideoAsset.status == VideoAssetStatus.READY,
                )
            )
            ready_ep_ids = set(res_v.scalars().all())
            all_ready = len(episodes) > 0 and all(ep.id in ready_ep_ids for ep in episodes)
            checks.append({
                "label": "All episodes have video ready",
                "passed": all_ready,
            })

    can_publish = all(c["passed"] for c in checks)
    return can_publish, checks


# --- Content Admin Endpoints ---

@router.get(
    "/content",
    response_model=PaginatedContentResponse,
    summary="Get paginated list of ALL content regardless of status (Admin)",
)
async def list_admin_content(
    status_filter: Optional[ContentStatus] = Query(None, alias="status", description="Filter by status (draft/published/archived)"),
    type_filter: Optional[ContentType] = Query(None, alias="type", description="Filter by content type (movie/series)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    query = select(Content)
    if status_filter:
        query = query.where(Content.status == status_filter)
    if type_filter:
        query = query.where(Content.type == type_filter)

    res = await db.execute(query.order_by(Content.created_at.desc()))
    all_content = res.scalars().all()

    total = len(all_content)
    total_pages = math.ceil(total / page_size) if total > 0 else 1
    offset = (page - 1) * page_size
    page_items = all_content[offset : offset + page_size]

    page_content_ids = [c.id for c in page_items]
    avg_ratings_map = {}
    if page_content_ids:
        rating_query = (
            select(Review.content_id, func.avg(Review.rating))
            .where(Review.content_id.in_(page_content_ids))
            .group_by(Review.content_id)
        )
        rating_res = await db.execute(rating_query)
        for cid, avg_val in rating_res.all():
            if avg_val is not None:
                avg_ratings_map[cid] = round(float(avg_val), 1)

    for item in page_items:
        setattr(item, "avg_rating", avg_ratings_map.get(item.id))

    return PaginatedContentResponse(
        items=[ContentResponse.model_validate(item) for item in page_items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post(
    "/content",
    response_model=ContentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new draft content record (Admin)",
)
async def create_draft_content(
    body: ContentCreateRequest,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    content = Content(
        title=body.title,
        type=body.type,
        synopsis=body.synopsis,
        cast=body.cast,
        genre=body.genre,
        language=body.language,
        content_rating=body.content_rating,
        release_year=body.release_year,
        duration_minutes=body.duration_minutes,
        duration_seconds=body.duration_seconds,
        poster_url=body.poster_url,
        backdrop_url=body.backdrop_url,
        status=ContentStatus.DRAFT,
    )
    db.add(content)
    await db.commit()
    await db.refresh(content)
    return content


@router.get(
    "/content/{content_id}",
    response_model=AdminContentDetailResponse,
    summary="Get full content details including video asset status for admin edit screen (Admin)",
)
async def get_admin_content_detail(
    content_id: uuid.UUID,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Content)
        .options(selectinload(Content.episodes))
        .where(Content.id == content_id)
    )
    content = result.scalars().first()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content record not found.",
        )

    res_v = await db.execute(
        select(VideoAsset).where(VideoAsset.content_id == content_id)
    )
    video_assets = res_v.scalars().all()
    setattr(content, "video_assets", video_assets)

    res_rating = await db.execute(
        select(func.avg(Review.rating)).where(Review.content_id == content_id)
    )
    avg_val = res_rating.scalar()
    setattr(content, "avg_rating", round(float(avg_val), 1) if avg_val is not None else None)

    return content


@router.patch(
    "/content/{content_id}",
    response_model=ContentResponse,
    summary="Update content metadata (Admin)",
)
async def update_content_metadata(
    content_id: uuid.UUID,
    body: ContentUpdateRequest,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(select(Content).where(Content.id == content_id))
    content = res.scalars().first()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content record not found.",
        )

    for field, val in body.model_dump(exclude_unset=True).items():
        setattr(content, field, val)

    await db.commit()
    await db.refresh(content)

    res_rating = await db.execute(
        select(func.avg(Review.rating)).where(Review.content_id == content_id)
    )
    avg_val = res_rating.scalar()
    setattr(content, "avg_rating", round(float(avg_val), 1) if avg_val is not None else None)

    return content


@router.delete(
    "/content/{content_id}",
    response_model=ContentResponse,
    summary="Soft delete content by archiving status (Admin)",
)
async def delete_admin_content(
    content_id: uuid.UUID,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(select(Content).where(Content.id == content_id))
    content = res.scalars().first()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content record not found.",
        )

    content.status = ContentStatus.ARCHIVED
    await db.commit()
    await db.refresh(content)

    res_rating = await db.execute(
        select(func.avg(Review.rating)).where(Review.content_id == content_id)
    )
    avg_val = res_rating.scalar()
    setattr(content, "avg_rating", round(float(avg_val), 1) if avg_val is not None else None)

    return content


# --- Image Upload Endpoint ---

@router.post(
    "/content/{content_id}/upload-image",
    response_model=ImageUploadResponse,
    summary="Upload poster or backdrop image for content (Admin)",
)
async def upload_content_image(
    content_id: uuid.UUID,
    image_type: str = Form(..., description="Image type: 'poster' or 'backdrop'"),
    file: UploadFile = File(..., description="Image file (JPG, PNG, WEBP, max 5MB)"),
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    image_type_lower = image_type.lower().strip()
    if image_type_lower not in ("poster", "backdrop"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image_type. Must be 'poster' or 'backdrop'.",
        )

    res = await db.execute(select(Content).where(Content.id == content_id))
    content = res.scalars().first()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content record not found.",
        )

    filename = file.filename or "image.png"
    _, ext = os.path.splitext(filename)
    allowed_exts = {".jpg", ".jpeg", ".png", ".webp"}
    content_type = file.content_type or ""
    if ext.lower() not in allowed_exts and not content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Allowed formats: JPG, PNG, WEBP.",
        )

    file_bytes = await file.read()
    max_bytes = 5 * 1024 * 1024  # 5MB limit
    if len(file_bytes) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image size exceeds 5MB limit.",
        )

    provider = get_image_provider()
    public_url = await provider.upload_image(file_bytes, filename)

    if image_type_lower == "poster":
        content.poster_url = public_url
    else:
        content.backdrop_url = public_url

    await db.commit()
    await db.refresh(content)

    return ImageUploadResponse(
        content_id=content.id,
        image_type=image_type_lower,
        url=public_url,
        message=f"{image_type_lower.capitalize()} image uploaded successfully.",
    )


# --- Video Upload & Webhook Endpoints ---

@router.post(
    "/content/{content_id}/video-upload",
    response_model=VideoUploadResponse,
    summary="Request video upload URL from provider for movie content (Admin)",
)
async def request_video_upload(
    content_id: uuid.UUID,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result_c = await db.execute(select(Content).where(Content.id == content_id))
    content = result_c.scalars().first()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content record not found.",
        )

    provider = get_video_provider()
    upload_info = await provider.create_upload(content.title)

    video_asset = VideoAsset(
        content_id=content.id,
        provider_video_id=upload_info["provider_video_id"],
        provider=settings.VIDEO_PROVIDER,
        status=VideoAssetStatus.UPLOADING,
    )
    db.add(video_asset)
    await db.commit()
    await db.refresh(video_asset)

    return VideoUploadResponse(
        content_id=content.id,
        video_asset_id=video_asset.id,
        provider_video_id=video_asset.provider_video_id,
        upload_url=upload_info["upload_url"],
        status=video_asset.status,
    )


@router.post(
    "/webhooks/video-status",
    summary="Webhook endpoint for video provider status updates",
)
async def video_status_webhook(
    payload: VideoWebhookPayload,
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(VideoAsset).where(VideoAsset.provider_video_id == payload.provider_video_id)
    )
    video_asset = res.scalars().first()
    if not video_asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video asset not found.",
        )

    video_asset.status = payload.status
    await db.commit()
    return {"message": "Status updated successfully."}


@router.post(
    "/dev/mark-video-ready/{video_asset_id}",
    summary="Dev endpoint: Manually mark video asset as READY for mock testing",
)
async def dev_mark_video_ready(
    video_asset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(select(VideoAsset).where(VideoAsset.id == video_asset_id))
    video_asset = res.scalars().first()
    if not video_asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video asset not found.",
        )

    video_asset.status = VideoAssetStatus.READY
    await db.commit()
    await db.refresh(video_asset)
    return {"message": f"Video asset {video_asset_id} status updated to READY.", "status": video_asset.status}


# --- Episode Management Endpoints ---

@router.get(
    "/content/{series_id}/episodes",
    response_model=List[EpisodeResponse],
    summary="List all episodes for a series ordered by season and episode_no (Admin)",
)
async def list_series_episodes(
    series_id: uuid.UUID,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    res_c = await db.execute(select(Content).where(Content.id == series_id))
    content = res_c.scalars().first()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Series content record not found.",
        )

    if content.type != ContentType.SERIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Content record is not a series.",
        )

    res_ep = await db.execute(
        select(Episode)
        .where(Episode.series_id == series_id)
        .order_by(Episode.season.asc(), Episode.episode_no.asc())
    )
    return res_ep.scalars().all()


@router.post(
    "/content/{series_id}/episodes",
    response_model=EpisodeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new episode for a series (Admin)",
)
async def create_episode(
    series_id: uuid.UUID,
    body: EpisodeCreateRequest,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    res_c = await db.execute(select(Content).where(Content.id == series_id))
    content = res_c.scalars().first()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Series content record not found.",
        )

    if content.type != ContentType.SERIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Content record is not a series.",
        )

    episode = Episode(
        series_id=series_id,
        season=body.season,
        episode_no=body.episode_no,
        title=body.title,
        duration_minutes=body.duration_minutes or 0,
    )
    db.add(episode)
    await db.commit()
    await db.refresh(episode)
    return episode


@router.patch(
    "/episodes/{episode_id}",
    response_model=EpisodeResponse,
    summary="Update episode metadata (Admin)",
)
async def update_episode(
    episode_id: uuid.UUID,
    body: EpisodeUpdateRequest,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(select(Episode).where(Episode.id == episode_id))
    episode = res.scalars().first()
    if not episode:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Episode record not found.",
        )

    for field, val in body.model_dump(exclude_unset=True).items():
        if val is not None:
            setattr(episode, field, val)

    await db.commit()
    await db.refresh(episode)
    return episode


@router.delete(
    "/episodes/{episode_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an episode (Admin)",
)
async def delete_episode(
    episode_id: uuid.UUID,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(select(Episode).where(Episode.id == episode_id))
    episode = res.scalars().first()
    if not episode:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Episode record not found.",
        )

    await db.delete(episode)
    await db.commit()
    return None


@router.post(
    "/episodes/{episode_id}/video-upload",
    response_model=EpisodeVideoUploadResponse,
    summary="Request video upload URL from provider for a specific episode (Admin)",
)
async def request_episode_video_upload(
    episode_id: uuid.UUID,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(select(Episode).where(Episode.id == episode_id))
    episode = res.scalars().first()
    if not episode:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Episode record not found.",
        )

    provider = get_video_provider()
    upload_info = await provider.create_upload(f"{episode.title} (S{episode.season}E{episode.episode_no})")

    video_asset = VideoAsset(
        episode_id=episode.id,
        provider_video_id=upload_info["provider_video_id"],
        provider=settings.VIDEO_PROVIDER,
        status=VideoAssetStatus.UPLOADING,
    )
    db.add(video_asset)
    await db.commit()
    await db.refresh(video_asset)

    episode.video_asset_id = video_asset.id
    await db.commit()

    return EpisodeVideoUploadResponse(
        episode_id=episode.id,
        video_asset_id=video_asset.id,
        provider_video_id=video_asset.provider_video_id,
        upload_url=upload_info["upload_url"],
        status=video_asset.status,
    )


# --- Publish Readiness & Publishing Endpoints ---

@router.get(
    "/content/{content_id}/publish-checklist",
    response_model=PublishChecklistResponse,
    summary="Get publish-readiness checklist for content (Admin)",
)
async def get_publish_checklist(
    content_id: uuid.UUID,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(select(Content).where(Content.id == content_id))
    content = res.scalars().first()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content record not found.",
        )

    can_publish, checks = await compute_publish_checklist(content, db)
    return PublishChecklistResponse(
        can_publish=can_publish,
        checks=[ChecklistItem(**c) for c in checks],
    )


@router.post(
    "/content/{content_id}/publish",
    response_model=ContentResponse,
    summary="Publish content after validating publish-readiness checklist (Admin)",
)
async def publish_content(
    content_id: uuid.UUID,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(select(Content).where(Content.id == content_id))
    content = res.scalars().first()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content record not found.",
        )

    can_publish, checks = await compute_publish_checklist(content, db)
    if not can_publish:
        failed_checks = [c["label"] for c in checks if not c["passed"]]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Content is not ready to be published.",
                "failed_checks": failed_checks,
            },
        )

    content.status = ContentStatus.PUBLISHED
    await db.commit()
    await db.refresh(content)

    res_rating = await db.execute(
        select(func.avg(Review.rating)).where(Review.content_id == content_id)
    )
    avg_val = res_rating.scalar()
    setattr(content, "avg_rating", round(float(avg_val), 1) if avg_val is not None else None)

    return content
