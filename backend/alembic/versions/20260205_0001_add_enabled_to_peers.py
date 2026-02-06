"""add enabled column to peers table

Revision ID: 20260205_0001
Revises: 20260204_0001
Create Date: 2026-02-05 00:00:01.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260205_0001"
down_revision = "20260204_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add enabled column to peers table with default True
    # Using server_default to ensure existing rows get the default value
    op.add_column(
        "peers",
        sa.Column(
            "enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("1")  # SQLite uses 1 for True
        )
    )

    # Backfill existing rows to explicitly set enabled = True
    # This ensures consistency even if server_default doesn't apply
    conn = op.get_bind()
    conn.execute(sa.text("UPDATE peers SET enabled = 1 WHERE enabled IS NULL"))


def downgrade() -> None:
    op.drop_column("peers", "enabled")
