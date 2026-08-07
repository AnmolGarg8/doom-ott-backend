"""create initial schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-08-07 13:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('phone', sa.String(), nullable=True),
        sa.Column('email', sa.String(), nullable=True),
        sa.Column('password_hash', sa.String(), nullable=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column(
            'auth_provider',
            sa.Enum('PHONE', 'EMAIL', 'GOOGLE', 'APPLE', name='auth_provider_enum'),
            nullable=False,
        ),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_users_phone', 'users', ['phone'], unique=True)
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # Profiles table
    op.create_table(
        'profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('avatar_key', sa.String(), nullable=False),
        sa.Column('is_kids_profile', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_profiles_user_id', 'profiles', ['user_id'])

    # Roles table
    op.create_table(
        'roles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('permissions', sa.JSON(), nullable=False),
    )

    # Admin users table
    op.create_table(
        'admin_users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('password_hash', sa.String(), nullable=False),
        sa.Column('role_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('roles.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_admin_users_email', 'admin_users', ['email'], unique=True)
    op.create_index('ix_admin_users_role_id', 'admin_users', ['role_id'])

    # Content table
    op.create_table(
        'content',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            'type',
            sa.Enum('MOVIE', 'SHORT', 'SERIES', name='content_type_enum'),
            nullable=False,
        ),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('synopsis', sa.Text(), nullable=False),
        sa.Column('cast', sa.JSON(), nullable=False),
        sa.Column('genre', sa.JSON(), nullable=False),
        sa.Column('language', sa.String(), nullable=False),
        sa.Column('content_rating', sa.String(), nullable=False),
        sa.Column('release_year', sa.Integer(), nullable=False),
        sa.Column('duration_minutes', sa.Integer(), nullable=True),
        sa.Column('poster_url', sa.String(), nullable=False),
        sa.Column('backdrop_url', sa.String(), nullable=False),
        sa.Column(
            'status',
            sa.Enum('DRAFT', 'PUBLISHED', 'ARCHIVED', name='content_status_enum'),
            server_default='DRAFT',
            nullable=False,
        ),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_content_type', 'content', ['type'])
    op.create_index('ix_content_status', 'content', ['status'])

    # Episodes table
    op.create_table(
        'episodes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('series_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('content.id', ondelete='CASCADE'), nullable=False),
        sa.Column('season', sa.Integer(), nullable=False),
        sa.Column('episode_no', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('video_asset_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('duration_minutes', sa.Integer(), nullable=False),
    )
    op.create_index('ix_episodes_series_id', 'episodes', ['series_id'])
    op.create_index('ix_episodes_video_asset_id', 'episodes', ['video_asset_id'])

    # Video assets table
    op.create_table(
        'video_assets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('content_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('content.id', ondelete='SET NULL'), nullable=True),
        sa.Column('episode_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('episodes.id', ondelete='SET NULL'), nullable=True),
        sa.Column('provider_video_id', sa.String(), nullable=False),
        sa.Column('provider', sa.String(), nullable=False),
        sa.Column(
            'status',
            sa.Enum('UPLOADING', 'PROCESSING', 'READY', 'FAILED', name='video_asset_status_enum'),
            nullable=False,
        ),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('thumbnail_url', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_video_assets_content_id', 'video_assets', ['content_id'])
    op.create_index('ix_video_assets_episode_id', 'video_assets', ['episode_id'])

    # Add FK constraint for episodes.video_asset_id -> video_assets.id
    op.create_foreign_key('fk_episodes_video_asset_id', 'episodes', 'video_assets', ['video_asset_id'], ['id'])

    # Categories table
    op.create_table(
        'categories',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('slug', sa.String(), nullable=False),
    )
    op.create_index('ix_categories_slug', 'categories', ['slug'], unique=True)

    # Subscription plans table
    op.create_table(
        'subscription_plans',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('price', sa.Numeric(10, 2), nullable=False),
        sa.Column('duration_days', sa.Integer(), nullable=False),
        sa.Column('features', sa.JSON(), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
    )

    # Subscriptions table
    op.create_table(
        'subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('plan_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('subscription_plans.id'), nullable=False),
        sa.Column(
            'status',
            sa.Enum('ACTIVE', 'EXPIRED', 'CANCELLED', name='subscription_status_enum'),
            nullable=False,
        ),
        sa.Column('start_date', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('end_date', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_subscriptions_user_id', 'subscriptions', ['user_id'])
    op.create_index('ix_subscriptions_plan_id', 'subscriptions', ['plan_id'])

    # Transactions table
    op.create_table(
        'transactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('plan_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('subscription_plans.id', ondelete='SET NULL'), nullable=True),
        sa.Column('amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('gateway_ref', sa.String(), nullable=True),
        sa.Column(
            'status',
            sa.Enum('PENDING', 'SUCCESS', 'FAILED', 'REFUNDED', name='transaction_status_enum'),
            nullable=False,
        ),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_transactions_user_id', 'transactions', ['user_id'])
    op.create_index('ix_transactions_plan_id', 'transactions', ['plan_id'])

    # Coupons table
    op.create_table(
        'coupons',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('code', sa.String(), nullable=False),
        sa.Column(
            'discount_type',
            sa.Enum('PERCENTAGE', 'FLAT', name='coupon_discount_type_enum'),
            nullable=False,
        ),
        sa.Column('value', sa.Numeric(10, 2), nullable=False),
        sa.Column('expiry', sa.Date(), nullable=False),
        sa.Column('usage_limit', sa.Integer(), nullable=False),
        sa.Column('times_used', sa.Integer(), server_default='0', nullable=False),
    )
    op.create_index('ix_coupons_code', 'coupons', ['code'], unique=True)

    # Watchlist table
    op.create_table(
        'watchlist',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('content_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('content.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('added_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_watchlist_user_id', 'watchlist', ['user_id'])
    op.create_index('ix_watchlist_content_id', 'watchlist', ['content_id'])

    # Watch progress table
    op.create_table(
        'watch_progress',
        sa.Column('profile_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('profiles.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('content_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('content.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('position_seconds', sa.Integer(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_watch_progress_profile_id', 'watch_progress', ['profile_id'])
    op.create_index('ix_watch_progress_content_id', 'watch_progress', ['content_id'])

    # Reviews table
    op.create_table(
        'reviews',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('content_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('content.id', ondelete='CASCADE'), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_reviews_user_id', 'reviews', ['user_id'])
    op.create_index('ix_reviews_content_id', 'reviews', ['content_id'])

    # Notifications table
    op.create_table(
        'notifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('target_segment', sa.String(), nullable=False),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('notifications')
    op.drop_index('ix_reviews_content_id', table_name='reviews')
    op.drop_index('ix_reviews_user_id', table_name='reviews')
    op.drop_table('reviews')
    op.drop_index('ix_watch_progress_content_id', table_name='watch_progress')
    op.drop_index('ix_watch_progress_profile_id', table_name='watch_progress')
    op.drop_table('watch_progress')
    op.drop_index('ix_watchlist_content_id', table_name='watchlist')
    op.drop_index('ix_watchlist_user_id', table_name='watchlist')
    op.drop_table('watchlist')
    op.drop_index('ix_coupons_code', table_name='coupons')
    op.drop_table('coupons')
    op.drop_index('ix_transactions_plan_id', table_name='transactions')
    op.drop_index('ix_transactions_user_id', table_name='transactions')
    op.drop_table('transactions')
    op.drop_index('ix_subscriptions_plan_id', table_name='subscriptions')
    op.drop_index('ix_subscriptions_user_id', table_name='subscriptions')
    op.drop_table('subscriptions')
    op.drop_table('subscription_plans')
    op.drop_index('ix_categories_slug', table_name='categories')
    op.drop_table('categories')
    op.drop_constraint('fk_episodes_video_asset_id', 'episodes', type_='foreignkey')
    op.drop_index('ix_video_assets_episode_id', table_name='video_assets')
    op.drop_index('ix_video_assets_content_id', table_name='video_assets')
    op.drop_table('video_assets')
    op.drop_index('ix_episodes_video_asset_id', table_name='episodes')
    op.drop_index('ix_episodes_series_id', table_name='episodes')
    op.drop_table('episodes')
    op.drop_index('ix_content_status', table_name='content')
    op.drop_index('ix_content_type', table_name='content')
    op.drop_table('content')
    op.drop_index('ix_admin_users_role_id', table_name='admin_users')
    op.drop_index('ix_admin_users_email', table_name='admin_users')
    op.drop_table('admin_users')
    op.drop_table('roles')
    op.drop_index('ix_profiles_user_id', table_name='profiles')
    op.drop_table('profiles')
    op.drop_index('ix_users_email', table_name='users')
    op.drop_index('ix_users_phone', table_name='users')
    op.drop_table('users')
