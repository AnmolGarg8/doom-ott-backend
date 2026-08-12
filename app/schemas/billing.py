import uuid
from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from app.models.enums import CouponDiscountType, SubscriptionStatus, TransactionStatus


class SubscriptionPlanResponse(BaseModel):
    id: uuid.UUID
    name: str
    price: float
    duration_days: int
    max_devices: int = 1
    features: List[str] = []
    is_active: bool

    class Config:
        from_attributes = True


class SubscriptionPlanCreate(BaseModel):
    name: str = Field(..., example="Standard HD")
    price: float = Field(..., ge=0, example=199.00)
    duration_days: int = Field(..., ge=1, example=30)
    max_devices: int = Field(1, ge=1, example=2)
    features: List[str] = Field(default_factory=list, example=["Full HD", "2 Devices"])
    is_active: bool = Field(True)


class SubscriptionPlanUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    duration_days: Optional[int] = None
    max_devices: Optional[int] = None
    features: Optional[List[str]] = None
    is_active: Optional[bool] = None


class CouponResponse(BaseModel):
    id: uuid.UUID
    code: str
    discount_type: CouponDiscountType
    value: float
    expiry: date
    usage_limit: int
    times_used: int

    class Config:
        from_attributes = True


class CouponCreate(BaseModel):
    code: str = Field(..., example="WELCOME50")
    discount_type: CouponDiscountType = Field(..., example=CouponDiscountType.PERCENTAGE)
    value: float = Field(..., ge=0, example=50.0)
    expiry: date = Field(..., example="2026-12-31")
    usage_limit: int = Field(..., ge=1, example=100)


class CheckoutRequest(BaseModel):
    plan_id: uuid.UUID
    coupon_code: Optional[str] = Field(None, example="WELCOME50")


class CheckoutResponse(BaseModel):
    transaction_id: uuid.UUID
    plan_id: uuid.UUID
    plan_name: str
    original_amount: float
    discount_amount: float
    final_amount: float
    payment_provider: str
    gateway_order_id: str


class PaymentVerifyRequest(BaseModel):
    transaction_id: uuid.UUID
    payment_id: str = Field(..., example="pay_mock_12345")
    signature: str = Field(..., example="sig_mock_12345")


class SubscriptionResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    plan_id: uuid.UUID
    status: SubscriptionStatus
    start_date: datetime
    end_date: datetime
    plan: Optional[SubscriptionPlanResponse] = None

    class Config:
        from_attributes = True


class TransactionResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    plan_id: Optional[uuid.UUID]
    amount: float
    status: TransactionStatus
    created_at: datetime
    gateway_ref: Optional[str] = None

    class Config:
        from_attributes = True
