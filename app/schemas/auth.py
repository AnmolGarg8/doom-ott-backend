import uuid
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class OTPSendRequest(BaseModel):
    phone: str = Field(..., example="+1234567890", description="Phone number with country code")


class OTPVerifyRequest(BaseModel):
    phone: str = Field(..., example="+1234567890")
    otp: str = Field(..., min_length=6, max_length=6, example="123456")


class EmailSignupRequest(BaseModel):
    email: EmailStr = Field(..., example="user@example.com")
    password: str = Field(..., min_length=6, example="secret123")
    name: str = Field(..., example="John Doe")


class EmailLoginRequest(BaseModel):
    email: EmailStr = Field(..., example="user@example.com")
    password: str = Field(..., example="secret123")


class SocialAuthRequest(BaseModel):
    id_token: str = Field(..., example="mock_token_12345")


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(...)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class MessageResponse(BaseModel):
    message: str


class UserResponse(BaseModel):
    id: uuid.UUID
    phone: Optional[str] = None
    email: Optional[str] = None
    name: str
    auth_provider: str

    class Config:
        from_attributes = True
