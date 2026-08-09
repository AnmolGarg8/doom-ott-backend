import uuid
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class OTPSendRequest(BaseModel):
    phone: str = Field(..., example="+1234567890", description="Phone number with country code")


class OTPVerifyRequest(BaseModel):
    phone: str = Field(..., example="+1234567890")
    otp: str = Field(..., min_length=6, max_length=6, example="123456")
    device_id: str = Field(default="unknown_device", example="device_abc123")
    device_name: str = Field(default="Unknown Device", example="Pixel 7")


class EmailSignupRequest(BaseModel):
    email: EmailStr = Field(..., example="user@example.com")
    password: str = Field(..., min_length=6, example="secret123")
    name: str = Field(..., example="John Doe")
    device_id: str = Field(default="unknown_device", example="device_abc123")
    device_name: str = Field(default="Unknown Device", example="Pixel 7")


class EmailLoginRequest(BaseModel):
    email: EmailStr = Field(..., example="user@example.com")
    password: str = Field(..., min_length=6, example="Secret123!")
    device_id: str = Field(default="unknown_device", example="device_abc123")
    device_name: str = Field(default="Unknown Device", example="Chrome Browser")


class AdminLoginRequest(BaseModel):
    email: EmailStr = Field(..., example="admin@doomott.com")
    password: str = Field(..., example="AdminPass123!")
    device_id: str = Field(default="unknown_device", example="device_abc123")
    device_name: str = Field(default="Unknown Device", example="Admin Dashboard")


class SocialAuthRequest(BaseModel):
    id_token: str = Field(..., example="mock_token_12345")
    device_id: str = Field(default="unknown_device", example="device_abc123")
    device_name: str = Field(default="Unknown Device", example="Mobile App")


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(...)
    device_id: str = Field(default="unknown_device", example="device_abc123")
    device_name: str = Field(default="Unknown Device", example="Mobile App")


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
