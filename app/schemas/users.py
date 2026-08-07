import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class ProfileCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50, example="John")
    avatar_key: str = Field(..., example="avatar_1")
    is_kids_profile: bool = Field(False, example=False)


class ProfileUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=50, example="John Updated")
    avatar_key: Optional[str] = Field(None, example="avatar_2")
    is_kids_profile: Optional[bool] = Field(None, example=False)


class ProfileResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    avatar_key: str
    is_kids_profile: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserDetailResponse(BaseModel):
    id: uuid.UUID
    phone: Optional[str] = None
    email: Optional[str] = None
    name: str
    auth_provider: str
    profiles: List[ProfileResponse] = []

    class Config:
        from_attributes = True
