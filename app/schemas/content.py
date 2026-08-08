import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class CategoryResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str

    class Config:
        from_attributes = True


class EpisodeResponse(BaseModel):
    id: uuid.UUID
    series_id: uuid.UUID
    season: int
    episode_no: int
    title: str
    video_asset_id: Optional[uuid.UUID] = None
    duration_minutes: int

    class Config:
        from_attributes = True


class ContentResponse(BaseModel):
    id: uuid.UUID
    type: str
    title: str
    synopsis: str
    cast: List[str] = []
    genre: List[str] = []
    language: str
    content_rating: str
    release_year: int
    duration_minutes: Optional[int] = None
    duration_seconds: Optional[int] = None
    poster_url: str
    backdrop_url: str
    status: str
    created_at: datetime
    avg_rating: Optional[float] = None

    class Config:
        from_attributes = True


class ContentDetailResponse(ContentResponse):
    episodes: List[EpisodeResponse] = []


class PaginatedContentResponse(BaseModel):
    items: List[ContentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class WatchlistResponse(BaseModel):
    user_id: uuid.UUID
    content_id: uuid.UUID
    added_at: datetime
    content: Optional[ContentResponse] = None

    class Config:
        from_attributes = True


class WatchProgressUpsert(BaseModel):
    profile_id: uuid.UUID
    position_seconds: int = Field(..., ge=0)


class WatchProgressResponse(BaseModel):
    profile_id: uuid.UUID
    content_id: uuid.UUID
    position_seconds: int
    updated_at: datetime
    content: Optional[ContentResponse] = None

    class Config:
        from_attributes = True
