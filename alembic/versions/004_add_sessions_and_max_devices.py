"""add sessions table and max_devices to subscription_plans

Revision ID: 004_add_sessions_and_max_devices
Revises: 003_add_duration_seconds
Create Date: 2026-08-09 19:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "004_add_sessions_and_max_devices"
down_revision = "003_add_duration_seconds"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "subscription_plans",
        sa.Column("max_devices", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("device_id", sa.String(), nullable=False, index=True),
        sa.Column("device_name", sa.String(), nullable=False),
        sa.Column("refresh_token_hash", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "last_active_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("sessions")
    op.drop_column("subscription_plans", "max_devices")
