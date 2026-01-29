"""Integration tests for password change API endpoint.

Tests POST /api/v1/auth/change-password endpoint.
"""

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Set test environment variables before importing app
os.environ.setdefault("APP_PSK_ENCRYPTION_KEY", "test-key-for-testing-32bytes1")
os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-for-jwt-testing")


@pytest.fixture
def client():
    """Create test client."""
    from backend.main import app

    return TestClient(app)


@pytest.fixture
def db_session():
    """Create database session for test cleanup."""
    from backend.app.auth.password import hash_password

    engine = create_engine("sqlite:///./app.db")
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    # Cleanup: Reset admin password to default state
    new_hash = hash_password("admin")
    session.execute(
        text(
            "UPDATE users SET passwordHash = :hash, requirePasswordChange = TRUE "
            "WHERE username = 'admin'"
        ).bindparams(hash=new_hash)
    )
    session.commit()
    session.close()


@pytest.fixture
def auth_token(client):
    """Get a valid auth token by logging in as admin."""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin"},
    )
    return response.json()["data"]["accessToken"]


class TestChangePasswordEndpoint:
    """Tests for POST /api/v1/auth/change-password endpoint."""

    def test_change_password_success(self, client, auth_token, db_session):
        """Test successful password change."""
        response = client.post(
            "/api/v1/auth/change-password",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"currentPassword": "admin", "newPassword": "newpass123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert data["data"]["message"] == "Password changed successfully"
        assert data["data"]["requirePasswordChange"] is False

        # Verify can login with new password
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "newpass123"},
        )
        assert login_response.status_code == 200
        # Cleanup handled by db_session fixture

    def test_change_password_wrong_current(self, client, auth_token):
        """Test change password fails with wrong current password."""
        response = client.post(
            "/api/v1/auth/change-password",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"currentPassword": "wrong", "newPassword": "newpass123"},
        )
        assert response.status_code == 401
        detail = response.json()["detail"]
        assert detail["detail"] == "Current password is incorrect"

    def test_change_password_too_short(self, client, auth_token):
        """Test change password fails when new password too short."""
        response = client.post(
            "/api/v1/auth/change-password",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"currentPassword": "admin", "newPassword": "short"},
        )
        assert response.status_code == 422

    def test_change_password_prevents_reuse(self, client, auth_token, db_session):
        """Test change password fails when new password equals current."""
        # First change to a password that meets complexity requirements
        response = client.post(
            "/api/v1/auth/change-password",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"currentPassword": "admin", "newPassword": "securepass1"},
        )
        assert response.status_code == 200

        # Get new token after password change
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "securepass1"},
        )
        new_token = login_response.json()["data"]["accessToken"]

        # Now try to "change" to the same password (reuse detection)
        response = client.post(
            "/api/v1/auth/change-password",
            headers={"Authorization": f"Bearer {new_token}"},
            json={"currentPassword": "securepass1", "newPassword": "securepass1"},
        )
        assert response.status_code == 422
        detail = response.json()["detail"]
        assert "different from current" in detail["detail"]
        # Cleanup handled by db_session fixture

    def test_change_password_requires_auth(self, client):
        """Test change password endpoint requires authentication."""
        response = client.post(
            "/api/v1/auth/change-password",
            json={"currentPassword": "admin", "newPassword": "newpass123"},
        )
        assert response.status_code in (401, 403)

    def test_change_password_with_invalid_token(self, client):
        """Test change password with invalid token returns 401."""
        response = client.post(
            "/api/v1/auth/change-password",
            headers={"Authorization": "Bearer invalid.token.here"},
            json={"currentPassword": "admin", "newPassword": "newpass123"},
        )
        assert response.status_code == 401

    def test_change_password_missing_current(self, client, auth_token):
        """Test change password fails when currentPassword missing."""
        response = client.post(
            "/api/v1/auth/change-password",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"newPassword": "newpass123"},
        )
        assert response.status_code == 422

    def test_change_password_missing_new(self, client, auth_token):
        """Test change password fails when newPassword missing."""
        response = client.post(
            "/api/v1/auth/change-password",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"currentPassword": "admin"},
        )
        assert response.status_code == 422


class TestLoginDetectsPasswordChangeRequired:
    """Tests for /me endpoint returning requirePasswordChange flag."""

    def test_me_returns_require_password_change_true(self, client, auth_token):
        """Test /me endpoint returns requirePasswordChange=true for admin."""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["requirePasswordChange"] is True
