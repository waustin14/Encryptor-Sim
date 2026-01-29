"""create isolation validation results table

Revision ID: 20260126_0002
Revises: 20260125_0001
Create Date: 2026-01-26 00:00:02.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260126_0002"
down_revision = "20260125_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "isolationValidationResults",
        sa.Column(
            "isolationValidationResultId", sa.Integer(), primary_key=True, autoincrement=True
        ),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("checks", sa.JSON(), nullable=False),
        sa.Column("failures", sa.JSON(), nullable=False),
        sa.Column("durationSeconds", sa.Float(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("isolationValidationResults")
