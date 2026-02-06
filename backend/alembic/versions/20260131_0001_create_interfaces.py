"""create interfaces table

Revision ID: 20260131_0001
Revises: 20260129_0004
Create Date: 2026-01-31 00:00:01.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260131_0001"
down_revision = "20260129_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "interfaces",
        sa.Column("interfaceId", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=50), unique=True, nullable=False),
        sa.Column("ipAddress", sa.String(length=45), nullable=True),
        sa.Column("netmask", sa.String(length=45), nullable=True),
        sa.Column("gateway", sa.String(length=45), nullable=True),
        sa.Column("namespace", sa.String(length=50), nullable=False),
        sa.Column("device", sa.String(length=50), nullable=False),
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

    # Create index on name for faster lookups
    op.create_index("idx_interfaces_name", "interfaces", ["name"])

    # Seed default interface entries for the three namespaces
    op.execute(
        sa.text(
            "INSERT INTO interfaces (name, namespace, device) VALUES "
            "(:name1, :ns1, :dev1)"
        ).bindparams(name1="CT", ns1="ns_ct", dev1="eth1")
    )
    op.execute(
        sa.text(
            "INSERT INTO interfaces (name, namespace, device) VALUES "
            "(:name2, :ns2, :dev2)"
        ).bindparams(name2="PT", ns2="ns_pt", dev2="eth2")
    )
    op.execute(
        sa.text(
            "INSERT INTO interfaces (name, namespace, device) VALUES "
            "(:name3, :ns3, :dev3)"
        ).bindparams(name3="MGMT", ns3="ns_mgmt", dev3="eth0")
    )


def downgrade() -> None:
    op.drop_index("idx_interfaces_name", table_name="interfaces")
    op.drop_table("interfaces")
