"""create peers table

Revision ID: 20260125_0001
Revises: 
Create Date: 2026-01-25 00:00:01.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260125_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "peers",
        sa.Column("peerId", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("pskEncrypted", sa.LargeBinary(), nullable=False),
        sa.Column("pskNonce", sa.LargeBinary(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("peers")
