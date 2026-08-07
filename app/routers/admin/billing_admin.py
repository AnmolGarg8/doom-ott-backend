import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_admin, get_db
from app.models.billing import Coupon, SubscriptionPlan
from app.models.user import AdminUser
from app.schemas.billing import (
    CouponCreate,
    CouponResponse,
    SubscriptionPlanCreate,
    SubscriptionPlanResponse,
    SubscriptionPlanUpdate,
)

router = APIRouter(prefix="/admin", tags=["Admin Billing & Subscription Management"])


@router.post(
    "/plans",
    response_model=SubscriptionPlanResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a subscription plan (Admin)",
)
async def create_plan(
    body: SubscriptionPlanCreate,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    plan = SubscriptionPlan(
        name=body.name,
        price=body.price,
        duration_days=body.duration_days,
        features=body.features,
        is_active=body.is_active,
    )
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return plan


@router.patch(
    "/plans/{plan_id}",
    response_model=SubscriptionPlanResponse,
    summary="Update a subscription plan (Admin)",
)
async def update_plan(
    plan_id: uuid.UUID,
    body: SubscriptionPlanUpdate,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(select(SubscriptionPlan).where(SubscriptionPlan.id == plan_id))
    plan = res.scalars().first()
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription plan not found.",
        )

    for field, val in body.model_dump(exclude_unset=True).items():
        setattr(plan, field, val)

    await db.commit()
    await db.refresh(plan)
    return plan


@router.post(
    "/coupons",
    response_model=CouponResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a coupon (Admin)",
)
async def create_coupon(
    body: CouponCreate,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(select(Coupon).where(Coupon.code == body.code.upper()))
    if res.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Coupon code already exists.",
        )

    coupon = Coupon(
        code=body.code.upper(),
        discount_type=body.discount_type,
        value=body.value,
        expiry=body.expiry,
        usage_limit=body.usage_limit,
        times_used=0,
    )
    db.add(coupon)
    await db.commit()
    await db.refresh(coupon)
    return coupon


@router.get(
    "/coupons",
    response_model=List[CouponResponse],
    summary="List all coupons (Admin)",
)
async def list_coupons(
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(select(Coupon).order_by(Coupon.code.asc()))
    return res.scalars().all()
