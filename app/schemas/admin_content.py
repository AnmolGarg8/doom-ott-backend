import uuid
from typing import List, Optional
from pydantic import BaseModel, Field
from app.models.enums import ContentType, VideoAssetStatus


class ContentCreateRequest(BaseModel):
    title: str = Field(..., example="Doom: Legacy")
    type: ContentType = Field(..., example=ContentType.MOVIE)
    synopsis: str = Field(..., example="A warrior embarks on a mission...")
    cast: List[str] = Field(default_factory=list, example=["Actor 1", "Actor 2"])
    genre: List[str] = Field(default_factory=list, example=["Action", "Sci-Fi"])
    language: str = Field(default="English", example="English")
    content_rating: str = Field(default="PG-13", example="PG-13")
    release_year: int = Field(..., example=2025)
    duration_minutes: Optional[int] = Field(None, example=120)
    poster_url: str = Field(..., example="https://example.com/poster.jpg")
    backdrop_url: str = Field(..., example="https://example.com/backdrop.jpg")


class ContentUpdateRequest(BaseModel):
    title: Optional[str] = None
    synopsis: Optional[str] = None
    cast: Optional[List[str]] = None
    genre: Optional[List[str]] = None
    language: Optional[str] = None
    content_rating: Optional[str] = None
    release_year: Optional[int] = None
    duration_minutes: Optional[int] = None
    poster_url: Optional[str] = None
    backdrop_url: Optional[str] = None


class VideoUploadResponse(BaseModel):
    content_id: uuid.UUID
    video_asset_id: uuid.UUID
    provider_video_id: str
    upload_url: str
    status: VideoAssetStatus


class VideoWebhookPayload(BaseModel):
    provider_video_id: str
    status: VideoAssetStatus


class PlaybackUrlResponse(BaseModel):
    content_id: uuid.UUID
    playback_url: str
    expiry_seconds: int = 3600
