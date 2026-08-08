import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.dependencies import get_current_admin, get_db
from app.models.content import Content, VideoAsset
from app.models.enums import ContentStatus, VideoAssetStatus
from app.models.user import AdminUser
from app.providers.video import get_video_provider
from app.schemas.admin_content import (
    ContentCreateRequest,
    ContentUpdateRequest,
    VideoUploadResponse,
    VideoWebhookPayload,
)
from app.schemas.content import ContentResponse

router = APIRouter(prefix="/admin", tags=["Admin Content & Video Pipeline"])


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


@router.post(
    "/content/{content_id}/video-upload",
    response_model=VideoUploadResponse,
    summary="Request video upload URL from provider (Admin)",
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
    return content


@router.post(
    "/content/{content_id}/publish",
    response_model=ContentResponse,
    summary="Publish draft content (Requires ready video asset) (Admin)",
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

    # Check if a video asset with status 'ready' exists for this content
    res_v = await db.execute(
        select(VideoAsset).where(
            VideoAsset.content_id == content_id, VideoAsset.status == VideoAssetStatus.READY
        )
    )
    ready_asset = res_v.scalars().first()
    if not ready_asset:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot publish content without a video asset in 'ready' status.",
        )

    content.status = ContentStatus.PUBLISHED
    await db.commit()
    await db.refresh(content)
    return content
