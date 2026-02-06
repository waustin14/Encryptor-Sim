"""Integration tests for API authentication for automation clients (Story 3.4).

Tests verify JWT authentication works correctly for non-browser automation
clients, covering login, bearer token access, token refresh, and error cases.
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


@pytest.fixture
def admin_tokens(client):
    """Login as admin and return tokens dict with accessToken and refreshToken."""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "changeme"},
    )
    assert response.status_code == 200
    return response.json()["data"]


@pytest.fixture
def admin_access_token(admin_tokens):
    """Return admin access token string."""
    return admin_tokens["accessToken"]


# ---------------------------------------------------------------------------
# Task 1: Verify API authentication endpoint (AC: #1, #2)
# ---------------------------------------------------------------------------


class TestAPILoginEndpoint:
    """Verify POST /api/v1/auth/login for automation clients (Task 1)."""

    def test_login_accepts_username_password_json(self, client):
        """1.1 Verify POST /api/v1/auth/login accepts username/password JSON."""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "changeme"},
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

    def test_login_returns_access_and_refresh_tokens(self, client):
        """1.2 Verify endpoint returns JWT access token and refresh token."""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "changeme"},
        )
        data = response.json()["data"]

        assert "accessToken" in data
        assert "refreshToken" in data
        assert isinstance(data["accessToken"], str)
        assert isinstance(data["refreshToken"], str)

        # Tokens should be valid JWT format (three base64 parts)
        assert len(data["accessToken"].split(".")) == 3
        assert len(data["refreshToken"].split(".")) == 3

    def test_login_same_credentials_as_web_ui(self, client):
        """1.3 Verify same credentials work for both Web UI and API clients.

        The API login endpoint uses the same user database and password
        validation as the Web UI, so identical credentials must work.
        """
        # API-style login (automation client)
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "changeme"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert "accessToken" in data

        # Token can be used to access /me endpoint (same as Web UI would)
        me_response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {data['accessToken']}"},
        )
        assert me_response.status_code == 200
        assert me_response.json()["data"]["username"] == "admin"

    def test_login_rejects_incorrect_password(self, client):
        """1.4 Verify login rejects incorrect credentials with 401.

        Note: The login endpoint validates credentials match the stored hash.
        Password complexity (8+ chars) is enforced at password change time,
        not during login attempts.
        """
        # Incorrect password is rejected with 401
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "wrongpassword"},
        )
        assert response.status_code == 401

    def test_login_returns_envelope_format(self, client):
        """Verify login response follows { data, meta } envelope pattern."""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "changeme"},
        )
        body = response.json()
        assert "data" in body
        assert "meta" in body

    def test_login_invalid_credentials_returns_401(self, client):
        """Verify invalid credentials return 401 with RFC 7807 error."""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "wrongpassword"},
        )
        assert response.status_code == 401
        error = response.json()["detail"]
        assert error["status"] == 401
        assert error["type"] == "about:blank"


# ---------------------------------------------------------------------------
# Task 2: Verify Bearer token authentication for protected endpoints (AC: #3, #4)
# ---------------------------------------------------------------------------


class TestBearerTokenAuthentication:
    """Verify Bearer token authentication for protected endpoints (Task 2)."""

    def test_bearer_token_grants_access(self, client, admin_access_token):
        """2.1 Verify Authorization header with Bearer token grants access."""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {admin_access_token}"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["username"] == "admin"

    def test_missing_token_returns_401(self, client):
        """2.2 Verify missing token returns 401 Unauthorized."""
        response = client.get("/api/v1/auth/me")
        # Expect 401 for missing authentication
        assert response.status_code == 401

    def test_invalid_token_returns_401(self, client):
        """2.3 Verify invalid token returns 401 Unauthorized."""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid.token.value"},
        )
        assert response.status_code == 401

    def test_expired_token_returns_401(self, client):
        """2.3b Verify expired token returns 401 Unauthorized."""
        import time
        import jwt
        from backend.app.config import get_settings

        # Create a token that expired 1 hour ago
        # This simulates an expired token without waiting
        settings = get_settings()
        expired_payload = {
            "sub": "1",
            "type": "access",
            "exp": int(time.time()) - 3600,  # Expired 1 hour ago
            "iat": int(time.time()) - 7200,  # Issued 2 hours ago
        }
        expired_token = jwt.encode(expired_payload, settings.secret_key, algorithm="HS256")

        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert response.status_code == 401

    def test_all_protected_endpoints_accept_bearer(self, client, admin_access_token):
        """2.4 Verify all protected endpoints accept Bearer authentication."""
        headers = {"Authorization": f"Bearer {admin_access_token}"}

        # /me endpoint
        me_resp = client.get("/api/v1/auth/me", headers=headers)
        assert me_resp.status_code == 200

        # /system/health endpoint
        health_resp = client.get("/api/v1/system/health", headers=headers)
        assert health_resp.status_code == 200

        # /logout endpoint
        logout_resp = client.post("/api/v1/auth/logout", headers=headers)
        assert logout_resp.status_code == 200

    def test_token_refresh_flow(self, client, admin_tokens):
        """2.5 Test token refresh flow with refresh token."""
        refresh_token = admin_tokens["refreshToken"]

        # Use refresh token to get new access token
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refreshToken": refresh_token},
        )
        assert response.status_code == 200
        new_data = response.json()["data"]
        assert "accessToken" in new_data

        # New access token should work for protected endpoints
        me_response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {new_data['accessToken']}"},
        )
        assert me_response.status_code == 200
        assert me_response.json()["data"]["username"] == "admin"


# ---------------------------------------------------------------------------
# Task 3: Comprehensive API authentication tests for automation (AC: #1-5)
# ---------------------------------------------------------------------------


class TestAutomationClientAuthentication:
    """Comprehensive integration tests for automation clients (Task 3)."""

    def test_api_login_valid_credentials_returns_tokens(self, client):
        """3.1 Integration test: API login with valid credentials returns tokens."""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "changeme"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert "accessToken" in data
        assert "refreshToken" in data
        assert data["tokenType"] == "bearer"
        # Tokens are non-trivial length
        assert len(data["accessToken"]) > 50
        assert len(data["refreshToken"]) > 50

    def test_api_login_invalid_credentials_returns_401(self, client):
        """3.2 Integration test: API login with invalid credentials returns 401."""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "WrongPassword123!"},
        )
        assert response.status_code == 401
        error = response.json()["detail"]
        assert error["status"] == 401

    def test_protected_endpoint_with_valid_bearer_token(self, client, admin_access_token):
        """3.3 Integration test: Protected endpoint access with valid Bearer token."""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {admin_access_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["username"] == "admin"
        assert "userId" in data

    def test_protected_endpoint_without_token_returns_401(self, client):
        """3.4 Integration test: Protected endpoint access without token returns 401."""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401

    def test_token_refresh_for_long_running_automation(self, client):
        """3.5 Integration test: Token refresh flow for long-running automation."""
        # Step 1: Login to get initial tokens
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "changeme"},
        )
        assert login_response.status_code == 200
        tokens = login_response.json()["data"]

        # Step 2: Refresh to simulate token rotation in long-running automation
        refresh_response = client.post(
            "/api/v1/auth/refresh",
            json={"refreshToken": tokens["refreshToken"]},
        )
        assert refresh_response.status_code == 200
        new_access_token = refresh_response.json()["data"]["accessToken"]

        # Step 3: New access token works
        me_response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {new_access_token}"},
        )
        assert me_response.status_code == 200
        assert me_response.json()["data"]["username"] == "admin"

    def test_concurrent_web_ui_and_api_authentication(self, client):
        """3.6 Integration test: Same user authenticates via both Web UI and API."""
        # Simulate Web UI login
        web_response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "changeme"},
        )
        web_token = web_response.json()["data"]["accessToken"]

        # Simulate separate API/automation login
        api_response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "changeme"},
        )
        api_token = api_response.json()["data"]["accessToken"]

        # Both tokens work independently
        web_me = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {web_token}"},
        )
        api_me = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {api_token}"},
        )
        assert web_me.status_code == 200
        assert api_me.status_code == 200
        assert web_me.json()["data"]["username"] == "admin"
        assert api_me.json()["data"]["username"] == "admin"
