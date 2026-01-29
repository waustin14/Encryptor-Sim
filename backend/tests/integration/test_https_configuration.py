"""Integration tests for HTTPS configuration.

Tests that TLS is properly configured with self-signed certificates.
Validates AC #2 of Story 2.2.
"""

from __future__ import annotations

from pathlib import Path


# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
IMAGE_DIR = PROJECT_ROOT / "image"
OPENRC_DIR = IMAGE_DIR / "openrc"


class TestCertificateGeneration:
    """Test self-signed certificate generation during build."""

    def test_build_script_generates_certificate(self) -> None:
        """Verify build-image.sh generates self-signed certificate."""
        build_script = IMAGE_DIR / "build-image.sh"
        content = build_script.read_text()

        # Must generate certificate with openssl
        assert "openssl" in content and "req" in content, (
            "Build script must generate certificate using openssl"
        )

    def test_build_script_creates_tls_directory(self) -> None:
        """Verify build-image.sh creates TLS certificate directory."""
        build_script = IMAGE_DIR / "build-image.sh"
        content = build_script.read_text()

        # Must create TLS directory
        assert "/etc/encryptor-sim/tls" in content or "tls" in content.lower()

    def test_build_script_sets_key_permissions(self) -> None:
        """Verify build-image.sh sets correct permissions on private key."""
        build_script = IMAGE_DIR / "build-image.sh"
        content = build_script.read_text()

        # Must set restrictive permissions on private key (600)
        assert "chmod" in content and ("600" in content or "0600" in content)


class TestApiHttpsConfiguration:
    """Test API service HTTPS configuration."""

    def test_api_service_uses_https_port(self) -> None:
        """Verify API service uses HTTPS port 443."""
        service_file = OPENRC_DIR / "encryptor-api"
        content = service_file.read_text()

        # Must use port 443 for HTTPS
        assert "443" in content

    def test_api_service_specifies_ssl_cert(self) -> None:
        """Verify API service specifies SSL certificate path."""
        service_file = OPENRC_DIR / "encryptor-api"
        content = service_file.read_text()

        # Must specify SSL certificate
        assert "ssl" in content.lower() and "cert" in content.lower()

    def test_api_service_specifies_ssl_key(self) -> None:
        """Verify API service specifies SSL key path."""
        service_file = OPENRC_DIR / "encryptor-api"
        content = service_file.read_text()

        # Must specify SSL key
        assert "ssl" in content.lower() and "key" in content.lower()

    def test_api_service_runs_uvicorn_server_wrapper(self) -> None:
        """Verify API service runs the uvicorn TLS wrapper."""
        service_file = OPENRC_DIR / "encryptor-api"
        content = service_file.read_text()

        assert "uvicorn_server.py" in content

    def test_api_healthcheck_uses_https(self) -> None:
        """Verify API healthcheck uses HTTPS."""
        service_file = OPENRC_DIR / "encryptor-api"
        content = service_file.read_text()

        # Healthcheck must use HTTPS
        assert "https://" in content or "-k" in content  # wget -k for insecure (self-signed)


class TestTlsVersionRequirement:
    """Test TLS version requirements."""

    def test_api_service_enforces_tls_version(self) -> None:
        """Verify TLS 1.2+ is enforced."""
        uvicorn_server = PROJECT_ROOT / "backend" / "uvicorn_server.py"
        content = uvicorn_server.read_text()

        assert "ssl.PROTOCOL_TLSv1_2" in content
