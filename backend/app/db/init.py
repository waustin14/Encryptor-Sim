"""Database initialization for application startup.

Creates tables and seeds the default admin user and interfaces if not present.
"""

import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.auth.password import hash_password
from backend.app.config import get_settings
from backend.app.db.session import get_engine
from backend.app.models import Base

logger = logging.getLogger(__name__)

# Default network interfaces matching the alembic seed migration
_DEFAULT_INTERFACES = [
    {"name": "CT", "namespace": "ns_ct", "device": "eth1"},
    {"name": "PT", "namespace": "ns_pt", "device": "eth2"},
    {"name": "MGMT", "namespace": "ns_mgmt", "device": "eth0"},
]


def init_db() -> None:
    """Create database tables and seed default data.

    Safe to call on every startup — only creates missing tables
    and only inserts seed data if it doesn't already exist.
    """
    settings = get_settings()
    engine = get_engine(settings.database_url, connect_args={"check_same_thread": False})

    # Create any missing tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables verified")

    with Session(engine) as session:
        # Seed default admin user if not present
        result = session.execute(
            text("SELECT COUNT(*) FROM users WHERE username = :username"),
            {"username": "admin"},
        )
        if result.scalar() == 0:
            admin_hash = hash_password("changeme")
            session.execute(
                text(
                    "INSERT INTO users (username, passwordHash, requirePasswordChange) "
                    "VALUES (:username, :passwordHash, :requirePasswordChange)"
                ),
                {
                    "username": "admin",
                    "passwordHash": admin_hash,
                    "requirePasswordChange": True,
                },
            )
            logger.info("Default admin user created")

        # Seed default interfaces if not present
        result = session.execute(text("SELECT COUNT(*) FROM interfaces"))
        if result.scalar() == 0:
            for iface in _DEFAULT_INTERFACES:
                session.execute(
                    text(
                        "INSERT INTO interfaces (name, namespace, device) "
                        "VALUES (:name, :namespace, :device)"
                    ),
                    iface,
                )
            logger.info("Default interfaces created (CT, PT, MGMT)")

        session.commit()
