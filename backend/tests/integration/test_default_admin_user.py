"""Integration tests for default admin user creation.

Verifies that the Alembic migration creates the default admin user
with properly hashed password.
"""

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from backend.app.auth.password import verify_password


class TestDefaultAdminUser:
    """Tests for default admin user creation."""

    @pytest.fixture
    def db_session(self):
        """Create a database session for testing."""
        engine = create_engine("sqlite:///./app.db")
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()

    def test_admin_user_exists(self, db_session):
        """Test that admin user exists in database."""
        result = db_session.execute(
            text("SELECT username FROM users WHERE username = 'admin'")
        )
        row = result.fetchone()
        assert row is not None
        assert row[0] == "admin"

    def test_admin_password_is_hashed(self, db_session):
        """Test that admin password is stored as argon2id hash."""
        result = db_session.execute(
            text("SELECT passwordHash FROM users WHERE username = 'admin'")
        )
        row = result.fetchone()
        assert row is not None
        password_hash = row[0]
        assert password_hash.startswith("$argon2id$")

    def test_admin_password_verifies(self, db_session):
        """Test that admin password 'changeme' verifies correctly."""
        result = db_session.execute(
            text("SELECT passwordHash FROM users WHERE username = 'admin'")
        )
        row = result.fetchone()
        assert row is not None
        password_hash = row[0]
        assert verify_password("changeme", password_hash) is True

    def test_wrong_password_fails(self, db_session):
        """Test that wrong password fails verification."""
        result = db_session.execute(
            text("SELECT passwordHash FROM users WHERE username = 'admin'")
        )
        row = result.fetchone()
        assert row is not None
        password_hash = row[0]
        assert verify_password("wrong", password_hash) is False

    def test_admin_require_password_change_is_true(self, db_session):
        """Test that requirePasswordChange is True for default admin after migration 0004."""
        result = db_session.execute(
            text("SELECT requirePasswordChange FROM users WHERE username = 'admin'")
        )
        row = result.fetchone()
        assert row is not None
        # SQLite stores boolean as 0/1
        assert row[0] == 1 or row[0] is True
