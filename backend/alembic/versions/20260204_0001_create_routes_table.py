"""create routes table

Revision ID: 20260204_0001
Revises: 20260203_0001
Create Date: 2026-02-04 00:00:01.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260204_0001"
down_revision = "20260203_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "routes",
        sa.Column("routeId", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "peerId",
            sa.Integer(),
            sa.ForeignKey("peers.peerId", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("destinationCidr", sa.String(length=18), nullable=False),
        sa.Column(
            "createdAt",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updatedAt",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_index("idx_routes_peerId", "routes", ["peerId"])


def downgrade() -> None:
    op.drop_index("idx_routes_peerId", table_name="routes")
    op.drop_table("routes")
