"""add duration_seconds to content

Revision ID: 003_add_duration_seconds_to_content
Revises: 002_add_is_blocked_to_users
Create Date: 2026-08-08 13:45:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "003_add_duration_seconds"
down_revision = "002_add_is_blocked_to_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "content",
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("content", "duration_seconds")
