from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.billing import Subscription, SubscriptionPlan
from app.models.enums import SubscriptionStatus
from app.models.user import User
from app.schemas.billing import SubscriptionPlanResponse, SubscriptionResponse

router = APIRouter(prefix="/subscription", tags=["Subscriptions"])


@router.get(
    "/plans",
    response_model=List[SubscriptionPlanResponse],
    summary="List active subscription plans",
)
async def list_active_plans(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(SubscriptionPlan).where(SubscriptionPlan.is_active == True)
    )
    return result.scalars().all()


@router.get(
    "/current",
    response_model=Optional[SubscriptionResponse],
    summary="Get current user's active subscription (Auth Required)",
)
async def get_current_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(Subscription)
        .where(
            Subscription.user_id == current_user.id,
            Subscription.status == SubscriptionStatus.ACTIVE,
            Subscription.end_date > now,
        )
        .order_by(Subscription.end_date.desc())
    )
    sub = result.scalars().first()
    if not sub:
        return None

    # Load plan
    res_plan = await db.execute(
        select(SubscriptionPlan).where(SubscriptionPlan.id == sub.plan_id)
    )
    plan_obj = res_plan.scalars().first()

    return SubscriptionResponse(
        id=sub.id,
        user_id=sub.user_id,
        plan_id=sub.plan_id,
        status=sub.status,
        start_date=sub.start_date,
        end_date=sub.end_date,
        plan=SubscriptionPlanResponse.model_validate(plan_obj) if plan_obj else None,
    )
