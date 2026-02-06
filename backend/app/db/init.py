"""Database initialization for application startup.

Creates tables and seeds the default admin user if not present.
"""

import logging

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from backend.app.auth.password import hash_password
from backend.app.config import get_settings
from backend.app.db.session import get_engine
from backend.app.models import Base

logger = logging.getLogger(__name__)


def init_db() -> None:
    """Create database tables and seed default admin user.

    Safe to call on every startup — only creates missing tables
    and only inserts the admin user if it doesn't already exist.
    """
    settings = get_settings()
    engine = get_engine(settings.database_url, connect_args={"check_same_thread": False})

    # Create any missing tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables verified")

    # Seed default admin user if not present
    with Session(engine) as session:
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
            session.commit()
            logger.info("Default admin user created")
        else:
            logger.info("Admin user already exists")
