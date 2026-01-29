"""Unit tests for User model.

Tests the User SQLAlchemy model structure.
"""

import pytest
from datetime import datetime, timezone


class TestUserModel:
    """Tests for User model."""

    def test_user_model_has_required_columns(self):
        """Test User model has all required columns."""
        from backend.app.models.user import User

        # Check that the class has the expected attributes
        assert hasattr(User, "userId")
        assert hasattr(User, "username")
        assert hasattr(User, "passwordHash")
        assert hasattr(User, "requirePasswordChange")
        assert hasattr(User, "createdAt")
        assert hasattr(User, "lastLogin")

    def test_user_model_tablename(self):
        """Test User model uses correct table name."""
        from backend.app.models.user import User

        assert User.__tablename__ == "users"

    def test_user_repr(self):
        """Test User model __repr__ method."""
        from backend.app.models.user import User

        user = User()
        user.userId = 1
        user.username = "admin"
        repr_str = repr(user)
        assert "userId=1" in repr_str
        assert "username=admin" in repr_str
