"""Integration tests for OpenAPI automation readiness (Story 5.5, Task 5).

Tests verify monitoring endpoints are discoverable in OpenAPI and that
security schemes are properly applied.
"""

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("APP_PSK_ENCRYPTION_KEY", "test-key-for-testing-32bytes1")
os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-for-jwt-testing")


@pytest.fixture
def client():
    from backend.main import app
    return TestClient(app)


@pytest.fixture
def openapi_spec(client):
    """Fetch and parse the OpenAPI spec."""
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    return resp.json()


@pytest.fixture
def api_reference_markdown() -> str:
    repo_root = Path(__file__).resolve().parents[3]
    return (repo_root / "docs" / "api-reference.md").read_text(encoding="utf-8")


class TestMonitoringEndpointsDiscoverable:
    """Verify new monitoring endpoints appear in OpenAPI spec (AC: #9, Task 5.1)."""

    def test_tunnels_endpoint_in_openapi(self, openapi_spec):
        paths = openapi_spec.get("paths", {})
        assert "/api/v1/monitoring/tunnels" in paths
        assert "get" in paths["/api/v1/monitoring/tunnels"]

    def test_interfaces_endpoint_in_openapi(self, openapi_spec):
        paths = openapi_spec.get("paths", {})
        assert "/api/v1/monitoring/interfaces" in paths
        assert "get" in paths["/api/v1/monitoring/interfaces"]

    def test_tunnels_endpoint_tagged(self, openapi_spec):
        """Verify endpoint has a tag for grouping in docs."""
        path = openapi_spec["paths"]["/api/v1/monitoring/tunnels"]["get"]
        assert "tags" in path
        assert len(path["tags"]) > 0

    def test_interfaces_endpoint_tagged(self, openapi_spec):
        """Verify endpoint has a tag for grouping in docs."""
        path = openapi_spec["paths"]["/api/v1/monitoring/interfaces"]["get"]
        assert "tags" in path
        assert len(path["tags"]) > 0

    def test_tunnels_response_schema_referenced(self, openapi_spec):
        """Verify tunnel endpoint references a response schema."""
        path = openapi_spec["paths"]["/api/v1/monitoring/tunnels"]["get"]
        responses = path.get("responses", {})
        assert "200" in responses
        success_resp = responses["200"]
        # Should have content with application/json schema
        assert "content" in success_resp
        assert "application/json" in success_resp["content"]

    def test_interfaces_response_schema_referenced(self, openapi_spec):
        """Verify interface endpoint references a response schema."""
        path = openapi_spec["paths"]["/api/v1/monitoring/interfaces"]["get"]
        responses = path.get("responses", {})
        assert "200" in responses
        success_resp = responses["200"]
        assert "content" in success_resp
        assert "application/json" in success_resp["content"]

    def test_monitoring_schemas_in_components(self, openapi_spec):
        """Verify monitoring schemas are registered in components."""
        schemas = openapi_spec.get("components", {}).get("schemas", {})
        assert "TunnelTelemetryEnvelope" in schemas
        assert "InterfaceStatsEnvelope" in schemas
        assert "TunnelTelemetryEntry" in schemas
        assert "InterfaceStatsEntry" in schemas


class TestSecuritySchemeApplication:
    """Verify security schemes are applied to monitoring endpoints (AC: #9, Task 5.2)."""

    def test_openapi_has_security_scheme(self, openapi_spec):
        """Verify BearerAuth security scheme exists."""
        security_schemes = (
            openapi_spec.get("components", {}).get("securitySchemes", {})
        )
        assert len(security_schemes) > 0
        # Should have a Bearer-type scheme
        bearer_found = any(
            scheme.get("type") == "http" and scheme.get("scheme") == "bearer"
            for scheme in security_schemes.values()
        )
        assert bearer_found, f"No bearer security scheme found in {security_schemes}"

    def test_tunnels_endpoint_requires_auth(self, client):
        """Verify GET /monitoring/tunnels returns 401/403 without token."""
        resp = client.get("/api/v1/monitoring/tunnels")
        assert resp.status_code in (401, 403)

    def test_interfaces_endpoint_requires_auth(self, client):
        """Verify GET /monitoring/interfaces returns 401/403 without token."""
        resp = client.get("/api/v1/monitoring/interfaces")
        assert resp.status_code in (401, 403)

    def test_existing_peer_endpoints_still_in_openapi(self, openapi_spec):
        """Regression: existing endpoints remain in spec."""
        paths = openapi_spec.get("paths", {})
        assert "/api/v1/peers" in paths
        assert "/api/v1/routes" in paths
        assert "/api/v1/interfaces" in paths


class TestApiReferenceContract:
    """Verify docs and OpenAPI remain aligned for automation consumers."""

    def test_api_reference_mentions_required_runtime_paths(self, api_reference_markdown):
        required_paths = [
            "/api/v1/auth/login",
            "/api/v1/auth/refresh",
            "/api/v1/auth/logout",
            "/api/v1/auth/change-password",
            "/api/v1/auth/me",
            "/api/v1/system/health",
            "/api/v1/system/isolation-status",
            "/api/v1/interfaces",
            "/api/v1/interfaces/{name}",
            "/api/v1/interfaces/{name}/configure",
            "/api/v1/peers",
            "/api/v1/peers/{peer_id}",
            "/api/v1/peers/{peer_id}/initiate",
            "/api/v1/routes",
            "/api/v1/routes/{route_id}",
            "/api/v1/monitoring/tunnels",
            "/api/v1/monitoring/interfaces",
            "/api/v1/ws",
        ]
        for path in required_paths:
            assert path in api_reference_markdown, f"Missing API path in docs: {path}"

    def test_api_reference_mentions_openapi_and_examples(self, api_reference_markdown):
        for token in [
            "/openapi.json",
            "/docs",
            "examples/curl_examples.sh",
            "examples/python_api_client.py",
        ]:
            assert token in api_reference_markdown, (
                f"Missing OpenAPI/examples reference in docs: {token}"
            )

    def test_required_route_groups_exist_in_openapi(self, openapi_spec):
        paths = openapi_spec.get("paths", {})
        required_prefixes = [
            "/api/v1/auth/",
            "/api/v1/system/",
            "/api/v1/interfaces",
            "/api/v1/peers",
            "/api/v1/routes",
            "/api/v1/monitoring/",
        ]
        for prefix in required_prefixes:
            assert any(path.startswith(prefix) for path in paths), (
                f"No OpenAPI paths found for group: {prefix}"
            )

    def test_protected_paths_require_auth_in_openapi(self, openapi_spec):
        paths = openapi_spec.get("paths", {})

        protected = [
            ("/api/v1/system/health", "get"),
            ("/api/v1/system/isolation-status", "get"),
            ("/api/v1/interfaces", "get"),
            ("/api/v1/interfaces/{name}", "get"),
            ("/api/v1/interfaces/{name}/configure", "post"),
            ("/api/v1/peers", "get"),
            ("/api/v1/peers", "post"),
            ("/api/v1/peers/{peer_id}", "get"),
            ("/api/v1/peers/{peer_id}", "put"),
            ("/api/v1/peers/{peer_id}", "delete"),
            ("/api/v1/peers/{peer_id}/initiate", "post"),
            ("/api/v1/routes", "get"),
            ("/api/v1/routes", "post"),
            ("/api/v1/routes/{route_id}", "get"),
            ("/api/v1/routes/{route_id}", "put"),
            ("/api/v1/routes/{route_id}", "delete"),
            ("/api/v1/monitoring/tunnels", "get"),
            ("/api/v1/monitoring/interfaces", "get"),
        ]
        for path, method in protected:
            operation = paths[path][method]
            assert operation.get("security"), f"{method.upper()} {path} missing security"

        public = [
            ("/api/v1/auth/login", "post"),
            ("/api/v1/auth/refresh", "post"),
        ]
        for path, method in public:
            operation = paths[path][method]
            assert not operation.get("security"), (
                f"{method.upper()} {path} should be public in OpenAPI"
            )
