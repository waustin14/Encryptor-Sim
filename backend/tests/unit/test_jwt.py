"""Unit tests for JWT token generation and validation.

Tests JWT access and refresh token functionality.
"""

import os
import time
import pytest

# Set test environment variable before importing jwt module
os.environ.setdefault("APP_PSK_ENCRYPTION_KEY", "test-key-for-testing-32bytes1")
os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-for-jwt-testing")


class TestJWTTokens:
    """Tests for JWT token generation and validation."""

    def test_create_access_token(self):
        """Test access token generation."""
        from backend.app.auth.jwt import create_access_token

        token = create_access_token(user_id=1)
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_refresh_token(self):
        """Test refresh token generation."""
        from backend.app.auth.jwt import create_refresh_token

        token = create_refresh_token(user_id=1)
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_verify_access_token_valid(self):
        """Test access token verification with valid token."""
        from backend.app.auth.jwt import create_access_token, verify_token

        token = create_access_token(user_id=42)
        user_id = verify_token(token, expected_type="access")
        assert user_id == 42

    def test_verify_refresh_token_valid(self):
        """Test refresh token verification with valid token."""
        from backend.app.auth.jwt import create_refresh_token, verify_token

        token = create_refresh_token(user_id=42)
        user_id = verify_token(token, expected_type="refresh")
        assert user_id == 42

    def test_verify_token_wrong_type(self):
        """Test token verification fails with wrong token type."""
        from backend.app.auth.jwt import create_access_token, verify_token

        token = create_access_token(user_id=1)
        # Try to verify access token as refresh token
        user_id = verify_token(token, expected_type="refresh")
        assert user_id is None

    def test_verify_token_invalid(self):
        """Test token verification fails with invalid token."""
        from backend.app.auth.jwt import verify_token

        user_id = verify_token("invalid.token.here", expected_type="access")
        assert user_id is None

    def test_verify_token_empty(self):
        """Test token verification fails with empty token."""
        from backend.app.auth.jwt import verify_token

        user_id = verify_token("", expected_type="access")
        assert user_id is None

    def test_access_token_contains_correct_type(self):
        """Test access token payload contains type='access'."""
        import jwt
        from backend.app.auth.jwt import create_access_token, SECRET_KEY, ALGORITHM

        token = create_access_token(user_id=1)
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload.get("type") == "access"

    def test_refresh_token_contains_correct_type(self):
        """Test refresh token payload contains type='refresh'."""
        import jwt
        from backend.app.auth.jwt import create_refresh_token, SECRET_KEY, ALGORITHM

        token = create_refresh_token(user_id=1)
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload.get("type") == "refresh"

    def test_token_contains_user_id_in_sub(self):
        """Test token payload contains user_id in 'sub' claim."""
        import jwt
        from backend.app.auth.jwt import create_access_token, SECRET_KEY, ALGORITHM

        token = create_access_token(user_id=123)
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload.get("sub") == "123"

    def test_token_contains_expiration(self):
        """Test token payload contains expiration claim."""
        import jwt
        from backend.app.auth.jwt import create_access_token, SECRET_KEY, ALGORITHM

        token = create_access_token(user_id=1)
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert "exp" in payload
        assert payload["exp"] > time.time()

    def test_token_contains_issued_at(self):
        """Test token payload contains issued at claim."""
        import jwt
        from backend.app.auth.jwt import create_access_token, SECRET_KEY, ALGORITHM

        token = create_access_token(user_id=1)
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert "iat" in payload
        assert payload["iat"] <= time.time()
