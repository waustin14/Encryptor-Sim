"""create users table with default admin

Revision ID: 20260128_0003
Revises: 20260126_0002
Create Date: 2026-01-28 00:00:03.000000
"""

from alembic import op
import sqlalchemy as sa
from argon2 import PasswordHasher


revision = "20260128_0003"
down_revision = "20260126_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        "users",
        sa.Column("userId", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("username", sa.String(length=50), nullable=False, unique=True),
        sa.Column("passwordHash", sa.String(length=255), nullable=False),
        sa.Column("requirePasswordChange", sa.Boolean(), nullable=False, default=False),
        sa.Column(
            "createdAt",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("lastLogin", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    # Seed default admin user with hashed password (idempotent)
    ph = PasswordHasher()
    admin_password_hash = ph.hash("changeme")

    # Check if admin user already exists before inserting
    conn = op.get_bind()
    result = conn.execute(
        sa.text("SELECT COUNT(*) FROM users WHERE username = :username").bindparams(
            username="admin"
        )
    )
    admin_exists = result.scalar() > 0

    if not admin_exists:
        op.execute(
            sa.text(
                "INSERT INTO users (username, passwordHash, requirePasswordChange) "
                "VALUES (:username, :passwordHash, :requirePasswordChange)"
            ).bindparams(
                username="admin",
                passwordHash=admin_password_hash,
                requirePasswordChange=False,
            )
        )


def downgrade() -> None:
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
