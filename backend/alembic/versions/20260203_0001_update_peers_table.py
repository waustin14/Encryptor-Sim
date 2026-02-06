"""update peers table with full ipsec peer fields

Revision ID: 20260203_0001
Revises: 20260131_0001
Create Date: 2026-02-03 00:00:01.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260203_0001"
down_revision = "20260131_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop old minimal peers table
    op.drop_table("peers")

    # Recreate with full schema
    op.create_table(
        "peers",
        sa.Column("peerId", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=100), unique=True, nullable=False),
        sa.Column("remoteIp", sa.String(length=45), nullable=False),
        sa.Column("psk", sa.String(length=500), nullable=False),
        sa.Column("ikeVersion", sa.String(length=10), nullable=False),
        sa.Column("dpdAction", sa.String(length=20), nullable=True),
        sa.Column("dpdDelay", sa.Integer(), nullable=True),
        sa.Column("dpdTimeout", sa.Integer(), nullable=True),
        sa.Column("rekeyTime", sa.Integer(), nullable=True),
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

    op.create_index("idx_peers_name", "peers", ["name"])
    op.create_index("idx_peers_remoteIp", "peers", ["remoteIp"])


def downgrade() -> None:
    op.drop_index("idx_peers_remoteIp", table_name="peers")
    op.drop_index("idx_peers_name", table_name="peers")
    op.drop_table("peers")

    # Restore old minimal table
    op.create_table(
        "peers",
        sa.Column("peerId", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("pskEncrypted", sa.LargeBinary(), nullable=False),
        sa.Column("pskNonce", sa.LargeBinary(), nullable=False),
    )
