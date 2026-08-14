from datetime import date, datetime, timedelta, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.limiter import limiter
from app.dependencies import get_current_user, get_db
from app.models.billing import Coupon, Subscription, SubscriptionPlan, Transaction
from app.models.enums import CouponDiscountType, SubscriptionStatus, TransactionStatus
from app.models.user import User
from app.providers.payment import get_payment_provider
from app.schemas.billing import (
    CheckoutRequest,
    CheckoutResponse,
    PaymentVerifyRequest,
    TransactionResponse,
)

router = APIRouter(prefix="/payment", tags=["Payments & Checkout"])


@router.post(
    "/checkout",
    response_model=CheckoutResponse,
    summary="Initiate payment checkout for a subscription plan (Auth Required)",
)
@limiter.limit("10/hour")
async def checkout_payment(
    request: Request,
    body: CheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    res_plan = await db.execute(
        select(SubscriptionPlan).where(
            SubscriptionPlan.id == body.plan_id, SubscriptionPlan.is_active == True
        )
    )
    plan = res_plan.scalars().first()
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription plan not found or inactive.",
        )

    final_amount = float(plan.price)

    # Coupon validation if code provided
    if body.coupon_code:
        res_coupon = await db.execute(
            select(Coupon).where(Coupon.code == body.coupon_code.upper())
        )
        coupon = res_coupon.scalars().first()
        if not coupon:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid coupon code.",
            )

        if coupon.expiry < date.today():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Coupon code has expired.",
            )

        if coupon.times_used >= coupon.usage_limit:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Coupon code usage limit exceeded.",
            )

        if coupon.discount_type == CouponDiscountType.PERCENTAGE:
            discount = final_amount * (float(coupon.value) / 100.0)
        else:
            discount = float(coupon.value)

        final_amount = max(0.0, final_amount - discount)
        coupon.times_used += 1

    final_amount = round(final_amount, 2)

    # Call payment provider to create order
    provider = get_payment_provider()
    order_info = await provider.create_order(amount=final_amount, currency="INR")

    # Create transaction record
    transaction = Transaction(
        user_id=current_user.id,
        plan_id=plan.id,
        amount=final_amount,
        gateway_ref=order_info["order_id"],
        status=TransactionStatus.PENDING,
    )
    db.add(transaction)
    await db.commit()
    await db.refresh(transaction)

    return CheckoutResponse(
        transaction_id=transaction.id,
        plan_id=plan.id,
        plan_name=plan.name,
        original_amount=float(plan.price),
        discount_amount=round(float(plan.price) - final_amount, 2),
        final_amount=final_amount,
        payment_provider=settings.PAYMENT_PROVIDER,
        gateway_order_id=order_info["order_id"],
    )


@router.post(
    "/verify",
    summary="Verify payment signature & activate subscription (Auth Required)",
)
@limiter.limit("10/hour")
async def verify_payment(
    request: Request,
    body: PaymentVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    res_tx = await db.execute(
        select(Transaction).where(
            Transaction.id == body.transaction_id, Transaction.user_id == current_user.id
        )
    )
    transaction = res_tx.scalars().first()
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction record not found.",
        )

    provider = get_payment_provider()
    is_valid = await provider.verify_payment(
        order_id=transaction.gateway_ref or "",
        payment_id=body.payment_id,
        signature=body.signature,
    )

    if not is_valid:
        transaction.status = TransactionStatus.FAILED
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment verification failed.",
        )

    # On successful verification
    transaction.status = TransactionStatus.SUCCESS
    transaction.gateway_ref = body.payment_id

    # Create or extend subscription
    res_plan = await db.execute(
        select(SubscriptionPlan).where(SubscriptionPlan.id == transaction.plan_id)
    )
    plan = res_plan.scalars().first()
    duration = plan.duration_days if plan else 30

    now = datetime.now(timezone.utc)
    res_sub = await db.execute(
        select(Subscription).where(
            Subscription.user_id == current_user.id,
            Subscription.status == SubscriptionStatus.ACTIVE,
            Subscription.end_date > now,
        )
    )
    existing_sub = res_sub.scalars().first()

    if existing_sub:
        existing_sub.end_date = existing_sub.end_date + timedelta(days=duration)
    else:
        new_sub = Subscription(
            user_id=current_user.id,
            plan_id=transaction.plan_id,
            status=SubscriptionStatus.ACTIVE,
            start_date=now,
            end_date=now + timedelta(days=duration),
        )
        db.add(new_sub)

    await db.commit()
    return {
        "message": "Payment verified successfully. Subscription activated.",
        "status": "success",
    }


@router.get(
    "/history",
    response_model=List[TransactionResponse],
    summary="Get user's payment & transaction history (Auth Required)",
)
async def get_payment_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Transaction)
        .where(Transaction.user_id == current_user.id)
        .order_by(Transaction.created_at.desc())
    )
    return result.scalars().all()
