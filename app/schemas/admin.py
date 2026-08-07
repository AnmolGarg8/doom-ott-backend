import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class UserAdminResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    auth_provider: str
    is_blocked: bool
    created_at: datetime
    has_active_subscription: bool = False

    class Config:
        from_attributes = True


class PaginatedUserAdminResponse(BaseModel):
    items: List[UserAdminResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class UserBlockToggleRequest(BaseModel):
    is_blocked: bool = Field(..., example=True)


class TopContentReport(BaseModel):
    content_id: uuid.UUID
    title: str
    type: str
    watch_count: int


class ReportsOverviewResponse(BaseModel):
    total_users: int
    active_subscriptions: int
    revenue_this_month: float
    top_content: List[TopContentReport]


class NotificationBroadcastRequest(BaseModel):
    title: str = Field(..., example="New Movie Released!")
    body: str = Field(..., example="Watch Doom: End of Days now streaming on DOOM OTT.")
    target_segment: Optional[str] = Field("all", example="all")


class NotificationBroadcastResponse(BaseModel):
    notifications_created: int
    message: str
