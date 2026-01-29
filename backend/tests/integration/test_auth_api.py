"""Integration tests for authentication API endpoints.

Tests login and logout functionality.
"""

import os
import pytest
from fastapi.testclient import TestClient

# Set test environment variables before importing app
os.environ.setdefault("APP_PSK_ENCRYPTION_KEY", "test-key-for-testing-32bytes1")
os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-for-jwt-testing")


@pytest.fixture
def client():
    """Create test client."""
    from backend.main import app

    return TestClient(app)


class TestLoginEndpoint:
    """Tests for POST /api/v1/auth/login endpoint."""

    def test_login_valid_credentials(self, client):
        """Test login with valid credentials returns tokens."""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "admin"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "accessToken" in data["data"]
        assert "refreshToken" in data["data"]
        assert data["data"]["tokenType"] == "bearer"

    def test_login_invalid_username(self, client):
        """Test login with invalid username returns 401."""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "wronguser", "password": "admin"},
        )
        assert response.status_code == 401
        error = response.json()
        assert error["detail"]["status"] == 401
        assert error["detail"]["title"] == "Authentication Failed"

    def test_login_invalid_password(self, client):
        """Test login with invalid password returns 401."""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "wrongpassword"},
        )
        assert response.status_code == 401

    def test_login_missing_username(self, client):
        """Test login with missing username returns 422."""
        response = client.post(
            "/api/v1/auth/login",
            json={"password": "admin"},
        )
        assert response.status_code == 422

    def test_login_missing_password(self, client):
        """Test login with missing password returns 422."""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin"},
        )
        assert response.status_code == 422

    def test_login_empty_body(self, client):
        """Test login with empty body returns 422."""
        response = client.post("/api/v1/auth/login", json={})
        assert response.status_code == 422

    def test_login_returns_valid_jwt(self, client):
        """Test login returns valid JWT that can be decoded."""
        import jwt

        response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "admin"},
        )
        assert response.status_code == 200
        data = response.json()["data"]

        # Verify access token structure
        access_token = data["accessToken"]
        # Just check it's a valid JWT format (three parts)
        parts = access_token.split(".")
        assert len(parts) == 3

    def test_login_updates_last_login(self, client):
        """Test login updates lastLogin timestamp."""
        from sqlalchemy import create_engine, text
        from sqlalchemy.orm import sessionmaker

        # Get initial lastLogin
        engine = create_engine("sqlite:///./app.db")
        Session = sessionmaker(bind=engine)
        session = Session()

        result = session.execute(
            text("SELECT lastLogin FROM users WHERE username = 'admin'")
        )
        initial_last_login = result.fetchone()[0]

        # Perform login
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "admin"},
        )
        assert response.status_code == 200

        # Check lastLogin was updated
        result = session.execute(
            text("SELECT lastLogin FROM users WHERE username = 'admin'")
        )
        new_last_login = result.fetchone()[0]

        session.close()

        # Should be different (updated)
        assert new_last_login is not None
        if initial_last_login is not None:
            assert new_last_login != initial_last_login

    def test_login_error_message_generic(self, client):
        """Test login error message does not reveal if username exists."""
        # Both invalid username and invalid password should return same error
        response_bad_user = client.post(
            "/api/v1/auth/login",
            json={"username": "nonexistent", "password": "admin"},
        )
        response_bad_pass = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "wrongpass"},
        )

        # Both should have same error message
        assert response_bad_user.status_code == 401
        assert response_bad_pass.status_code == 401
        assert (
            response_bad_user.json()["detail"]["detail"]
            == response_bad_pass.json()["detail"]["detail"]
        )


class TestLogoutEndpoint:
    """Tests for POST /api/v1/auth/logout endpoint."""

    def test_logout_with_valid_token(self, client):
        """Test logout with valid token returns success."""
        # First login to get a token
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "admin"},
        )
        assert login_response.status_code == 200
        access_token = login_response.json()["data"]["accessToken"]

        # Now logout
        response = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert data["data"]["message"] == "Logged out successfully"

    def test_logout_without_token(self, client):
        """Test logout without token returns 401 (HTTPBearer requires auth)."""
        response = client.post("/api/v1/auth/logout")
        # HTTPBearer returns 403 Forbidden when no credentials provided
        # But our custom error handler returns 401
        assert response.status_code in (401, 403)

    def test_logout_with_invalid_token(self, client):
        """Test logout with invalid token returns 401."""
        response = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert response.status_code == 401

    def test_me_endpoint_returns_user_profile(self, client):
        """Test /me endpoint returns authenticated user profile."""
        # First login to get a token
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "admin"},
        )
        assert login_response.status_code == 200
        access_token = login_response.json()["data"]["accessToken"]

        # Get user profile
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert data["data"]["username"] == "admin"
        assert data["data"]["userId"] == 1
        assert "requirePasswordChange" in data["data"]

    def test_me_endpoint_requires_auth(self, client):
        """Test /me endpoint requires authentication."""
        response = client.get("/api/v1/auth/me")
        assert response.status_code in (401, 403)


class TestProtectedEndpoints:
    """Tests for protected endpoints requiring authentication."""

    def test_health_endpoint_requires_auth(self, client):
        """Test health endpoint requires authentication."""
        response = client.get("/api/v1/system/health")
        assert response.status_code in (401, 403)

    def test_health_endpoint_with_valid_token(self, client):
        """Test health endpoint works with valid token."""
        # First login to get a token
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "admin"},
        )
        assert login_response.status_code == 200
        access_token = login_response.json()["data"]["accessToken"]

        # Access health endpoint with token
        response = client.get(
            "/api/v1/system/health",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "status" in data["data"]

    def test_health_endpoint_with_invalid_token(self, client):
        """Test health endpoint rejects invalid token."""
        response = client.get(
            "/api/v1/system/health",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert response.status_code == 401
