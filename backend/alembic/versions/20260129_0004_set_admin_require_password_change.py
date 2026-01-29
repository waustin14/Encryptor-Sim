"""set admin requirePasswordChange to TRUE

Revision ID: 20260129_0004
Revises: 20260128_0003
Create Date: 2026-01-29 00:00:04.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260129_0004"
down_revision = "20260128_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Set requirePasswordChange=TRUE for default admin user."""
    op.execute(
        sa.text(
            "UPDATE users "
            "SET requirePasswordChange = TRUE "
            "WHERE username = :username "
            "AND requirePasswordChange = FALSE"
        ).bindparams(username="admin")
    )


def downgrade() -> None:
    """Revert requirePasswordChange for admin user."""
    op.execute(
        sa.text(
            "UPDATE users "
            "SET requirePasswordChange = FALSE "
            "WHERE username = :username "
            "AND requirePasswordChange = TRUE"
        ).bindparams(username="admin")
    )
