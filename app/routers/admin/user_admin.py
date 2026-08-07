import uuid
import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_admin, get_db, get_redis
from app.models.billing import Subscription, Transaction
from app.models.content import Content, WatchProgress
from app.models.enums import SubscriptionStatus, TransactionStatus
from app.models.notification import Notification
from app.models.user import AdminUser, User
from app.services.auth_service import redis_delete
from app.schemas.admin import (
    NotificationBroadcastRequest,
    NotificationBroadcastResponse,
    PaginatedUserAdminResponse,
    ReportsOverviewResponse,
    TopContentReport,
    UserAdminResponse,
    UserBlockToggleRequest,
)

logger = logging.getLogger("doom_ott.admin.notifications")

router = APIRouter(prefix="/admin", tags=["Admin User Management & Overview Reports"])


@router.get(
    "/users",
    response_model=PaginatedUserAdminResponse,
    summary="Paginated user list with filters (Admin)",
)
async def list_users_admin(
    search: Optional[str] = Query(None, description="Search by phone, email, or name"),
    is_blocked: Optional[bool] = Query(None, description="Filter by blocked status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    query = select(User)
    count_query = select(func.count(User.id))

    if search:
        s = f"%{search}%"
        filter_clause = or_(User.email.ilike(s), User.phone.ilike(s), User.name.ilike(s))
        query = query.where(filter_clause)
        count_query = count_query.where(filter_clause)

    if is_blocked is not None:
        query = query.where(User.is_blocked == is_blocked)
        count_query = count_query.where(User.is_blocked == is_blocked)

    total_res = await db.execute(count_query)
    total = total_res.scalar() or 0

    offset = (page - 1) * page_size
    query = query.order_by(User.created_at.desc()).offset(offset).limit(page_size)
    users_res = await db.execute(query)
    users = users_res.scalars().all()

    now = datetime.now(timezone.utc)
    items = []
    for u in users:
        # Check active sub
        sub_res = await db.execute(
            select(Subscription).where(
                Subscription.user_id == u.id,
                Subscription.status == SubscriptionStatus.ACTIVE,
                Subscription.end_date > now,
            )
        )
        has_active_sub = bool(sub_res.scalars().first())
        items.append(
            UserAdminResponse(
                id=u.id,
                name=u.name,
                email=u.email,
                phone=u.phone,
                auth_provider=u.auth_provider.value if hasattr(u.auth_provider, "value") else str(u.auth_provider),
                is_blocked=u.is_blocked,
                created_at=u.created_at,
                has_active_subscription=has_active_sub,
            )
        )

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return PaginatedUserAdminResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.patch(
    "/users/{user_id}/block",
    response_model=UserAdminResponse,
    summary="Toggle user blocked status (Admin)",
)
async def toggle_user_block(
    user_id: uuid.UUID,
    body: UserBlockToggleRequest,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    res = await db.execute(select(User).where(User.id == user_id))
    user = res.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    user.is_blocked = body.is_blocked
    await db.commit()
    await db.refresh(user)

    if user.is_blocked:
        # Revoke refresh token if stored in Redis
        await redis_delete(redis, f"refresh_token:{user.id}")

    now = datetime.now(timezone.utc)
    sub_res = await db.execute(
        select(Subscription).where(
            Subscription.user_id == user.id,
            Subscription.status == SubscriptionStatus.ACTIVE,
            Subscription.end_date > now,
        )
    )
    has_active_sub = bool(sub_res.scalars().first())

    return UserAdminResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        phone=user.phone,
        auth_provider=user.auth_provider.value if hasattr(user.auth_provider, "value") else str(user.auth_provider),
        is_blocked=user.is_blocked,
        created_at=user.created_at,
        has_active_subscription=has_active_sub,
    )


@router.get(
    "/reports/overview",
    response_model=ReportsOverviewResponse,
    summary="Aggregate system stats & reports overview for Admin Dashboard (Admin)",
)
async def get_reports_overview(
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    # Total Users
    total_users_res = await db.execute(select(func.count(User.id)))
    total_users = total_users_res.scalar() or 0

    # Active Subscriptions
    now = datetime.now(timezone.utc)
    active_subs_res = await db.execute(
        select(func.count(Subscription.id)).where(
            Subscription.status == SubscriptionStatus.ACTIVE,
            Subscription.end_date > now,
        )
    )
    active_subscriptions = active_subs_res.scalar() or 0

    # Revenue This Month
    first_day_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    rev_res = await db.execute(
        select(func.sum(Transaction.amount)).where(
            Transaction.status == TransactionStatus.SUCCESS,
            Transaction.created_at >= first_day_of_month,
        )
    )
    revenue_this_month = float(rev_res.scalar() or 0.0)

    # Top Content (Top 10 by watch progress record count)
    top_content_query = (
        select(
            Content.id.label("content_id"),
            Content.title.label("title"),
            Content.type.label("type"),
            func.count(WatchProgress.content_id).label("watch_count"),
        )
        .join(WatchProgress, Content.id == WatchProgress.content_id)
        .group_by(Content.id, Content.title, Content.type)
        .order_by(func.count(WatchProgress.content_id).desc())
        .limit(10)
    )
    top_content_res = await db.execute(top_content_query)
    top_content_rows = top_content_res.all()

    top_content_list = [
        TopContentReport(
            content_id=row.content_id,
            title=row.title,
            type=row.type.value if hasattr(row.type, "value") else str(row.type),
            watch_count=row.watch_count,
        )
        for row in top_content_rows
    ]

    return ReportsOverviewResponse(
        total_users=total_users,
        active_subscriptions=active_subscriptions,
        revenue_this_month=revenue_this_month,
        top_content=top_content_list,
    )


@router.post(
    "/notifications/broadcast",
    response_model=NotificationBroadcastResponse,
    summary="Broadcast push notification to users (Admin)",
)
async def broadcast_notification(
    body: NotificationBroadcastRequest,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    # Fetch target users
    users_res = await db.execute(select(User).where(User.is_blocked == False))
    target_users = users_res.scalars().all()

    # Create broadcast notification record
    now = datetime.now(timezone.utc)
    notification = Notification(
        title=body.title,
        body=body.body,
        target_segment=body.target_segment or "all",
        sent_at=now,
    )
    db.add(notification)
    await db.commit()
    await db.refresh(notification)

    # TODO: Wire real FCM (Firebase Cloud Messaging) / APNs push notification SDK when credentials exist.
    logger.info(
        f"[FCM TODO] Would send FCM Push Notification: title='{body.title}', body='{body.body}', target_segment='{body.target_segment}', total_recipients={len(target_users)}"
    )

    return NotificationBroadcastResponse(
        notifications_created=len(target_users),
        message=f"Broadcast created for {len(target_users)} active users. [FCM TODO logged to console]",
    )
