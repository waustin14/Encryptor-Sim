"""Integration tests for HTTPS configuration.

Tests that TLS is properly configured with self-signed certificates.
Validates ACs #1, #2, #3, #4 of Story 3.3.
"""

from __future__ import annotations

import re
from pathlib import Path


# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
IMAGE_DIR = PROJECT_ROOT / "image"
OPENRC_DIR = IMAGE_DIR / "openrc"
BACKEND_DIR = PROJECT_ROOT / "backend"


class TestCertificateGeneration:
    """Test self-signed certificate generation during build (Task 1, AC: #2)."""

    def test_build_script_generates_certificate(self) -> None:
        """Verify build-image.sh generates self-signed certificate using openssl req -x509."""
        build_script = IMAGE_DIR / "build-image.sh"
        content = build_script.read_text()

        assert "openssl req -x509" in content, (
            "Build script must generate certificate using openssl req -x509"
        )

    def test_build_script_uses_rsa_4096(self) -> None:
        """Verify certificate uses RSA-4096 key size (AC: #2)."""
        build_script = IMAGE_DIR / "build-image.sh"
        content = build_script.read_text()

        assert "rsa:4096" in content, (
            "Certificate must use RSA-4096 for strong security"
        )

    def test_build_script_sets_10_year_validity(self) -> None:
        """Verify certificate validity is 10 years / 3650 days (AC: #2)."""
        build_script = IMAGE_DIR / "build-image.sh"
        content = build_script.read_text()

        assert "-days 3650" in content, (
            "Certificate validity must be 10 years (3650 days)"
        )

    def test_build_script_sets_correct_subject(self) -> None:
        """Verify certificate subject: CN=encryptor-sim, O=Encryptor Simulator, C=US."""
        build_script = IMAGE_DIR / "build-image.sh"
        content = build_script.read_text()

        assert "CN=encryptor-sim" in content
        assert "O=Encryptor Simulator" in content
        assert "C=US" in content

    def test_build_script_creates_tls_directory(self) -> None:
        """Verify build-image.sh creates /etc/encryptor-sim/tls directory."""
        build_script = IMAGE_DIR / "build-image.sh"
        content = build_script.read_text()

        assert "/etc/encryptor-sim/tls" in content

    def test_build_script_stores_cert_at_correct_path(self) -> None:
        """Verify certificate stored at /etc/encryptor-sim/tls/server.crt."""
        build_script = IMAGE_DIR / "build-image.sh"
        content = build_script.read_text()

        assert "/etc/encryptor-sim/tls/server.crt" in content

    def test_build_script_stores_key_at_correct_path(self) -> None:
        """Verify private key stored at /etc/encryptor-sim/tls/server.key."""
        build_script = IMAGE_DIR / "build-image.sh"
        content = build_script.read_text()

        assert "/etc/encryptor-sim/tls/server.key" in content

    def test_build_script_sets_key_permissions_0600(self) -> None:
        """Verify private key has 0600 permissions (root-only, AC: #2)."""
        build_script = IMAGE_DIR / "build-image.sh"
        content = build_script.read_text()

        assert re.search(r"chmod\s+0?600.*server\.key", content), (
            "Private key must have 0600 permissions (root-only)"
        )

    def test_build_script_sets_cert_permissions_0644(self) -> None:
        """Verify certificate has 0644 permissions (world-readable)."""
        build_script = IMAGE_DIR / "build-image.sh"
        content = build_script.read_text()

        assert re.search(r"chmod\s+0?644.*server\.crt", content), (
            "Certificate must have 0644 permissions (world-readable)"
        )

    def test_build_script_uses_nodes_flag(self) -> None:
        """Verify no passphrase on private key for automated startup."""
        build_script = IMAGE_DIR / "build-image.sh"
        content = build_script.read_text()

        assert "-nodes" in content, (
            "Certificate generation must use -nodes flag for automated startup"
        )


class TestUvicornHttpsWrapper:
    """Test uvicorn HTTPS wrapper script (Task 2, AC: #1, #3)."""

    def test_uvicorn_server_exists(self) -> None:
        """Verify backend/uvicorn_server.py exists."""
        uvicorn_script = BACKEND_DIR / "uvicorn_server.py"
        assert uvicorn_script.exists(), "uvicorn_server.py must exist"

    def test_uvicorn_configures_ssl_certfile(self) -> None:
        """Verify uvicorn uses ssl_certfile parameter."""
        uvicorn_script = BACKEND_DIR / "uvicorn_server.py"
        content = uvicorn_script.read_text()

        assert "ssl_certfile" in content

    def test_uvicorn_configures_ssl_keyfile(self) -> None:
        """Verify uvicorn uses ssl_keyfile parameter."""
        uvicorn_script = BACKEND_DIR / "uvicorn_server.py"
        content = uvicorn_script.read_text()

        assert "ssl_keyfile" in content

    def test_uvicorn_enforces_tls_1_2(self) -> None:
        """Verify TLS 1.2+ minimum is enforced (AC: #1)."""
        uvicorn_script = BACKEND_DIR / "uvicorn_server.py"
        content = uvicorn_script.read_text()

        assert "ssl.PROTOCOL_TLSv1_2" in content, (
            "Uvicorn must enforce TLS 1.2+ minimum"
        )

    def test_uvicorn_binds_to_all_interfaces(self) -> None:
        """Verify uvicorn binds to 0.0.0.0 for DHCP-assigned IPs."""
        uvicorn_script = BACKEND_DIR / "uvicorn_server.py"
        content = uvicorn_script.read_text()

        assert '"0.0.0.0"' in content or "'0.0.0.0'" in content, (
            "Uvicorn must bind to 0.0.0.0 to accept connections on any MGMT IP"
        )

    def test_uvicorn_uses_port_443(self) -> None:
        """Verify uvicorn uses HTTPS port 443 (AC: #3)."""
        uvicorn_script = BACKEND_DIR / "uvicorn_server.py"
        content = uvicorn_script.read_text()

        assert "port=443" in content, (
            "Uvicorn must bind to port 443 for HTTPS"
        )

    def test_uvicorn_supports_certfile_env_override(self) -> None:
        """Verify APP_SSL_CERTFILE environment variable override."""
        uvicorn_script = BACKEND_DIR / "uvicorn_server.py"
        content = uvicorn_script.read_text()

        assert "APP_SSL_CERTFILE" in content, (
            "Must support APP_SSL_CERTFILE environment variable override"
        )

    def test_uvicorn_supports_keyfile_env_override(self) -> None:
        """Verify APP_SSL_KEYFILE environment variable override."""
        uvicorn_script = BACKEND_DIR / "uvicorn_server.py"
        content = uvicorn_script.read_text()

        assert "APP_SSL_KEYFILE" in content, (
            "Must support APP_SSL_KEYFILE environment variable override"
        )


class TestOpenrcServiceConfiguration:
    """Test OpenRC service HTTPS configuration (Task 3, AC: #1, #3, #4)."""

    def test_service_sets_ssl_certfile_variable(self) -> None:
        """Verify service defines SSL_CERTFILE with correct path."""
        service_file = OPENRC_DIR / "encryptor-api"
        content = service_file.read_text()

        assert 'SSL_CERTFILE="/etc/encryptor-sim/tls/server.crt"' in content

    def test_service_sets_ssl_keyfile_variable(self) -> None:
        """Verify service defines SSL_KEYFILE with correct path."""
        service_file = OPENRC_DIR / "encryptor-api"
        content = service_file.read_text()

        assert 'SSL_KEYFILE="/etc/encryptor-sim/tls/server.key"' in content

    def test_service_exports_app_ssl_certfile(self) -> None:
        """Verify service exports APP_SSL_CERTFILE to environment."""
        service_file = OPENRC_DIR / "encryptor-api"
        content = service_file.read_text()

        assert "APP_SSL_CERTFILE" in content

    def test_service_exports_app_ssl_keyfile(self) -> None:
        """Verify service exports APP_SSL_KEYFILE to environment."""
        service_file = OPENRC_DIR / "encryptor-api"
        content = service_file.read_text()

        assert "APP_SSL_KEYFILE" in content

    def test_service_runs_uvicorn_server_wrapper(self) -> None:
        """Verify service executes uvicorn_server.py wrapper."""
        service_file = OPENRC_DIR / "encryptor-api"
        content = service_file.read_text()

        assert "uvicorn_server.py" in content

    def test_service_blocks_http_port_80(self) -> None:
        """Verify start_pre validates no HTTP listener on port 80 (AC: #4)."""
        service_file = OPENRC_DIR / "encryptor-api"
        content = service_file.read_text()

        assert ":80" in content, "Service must check for port 80"
        assert "eerror" in content or "return 1" in content, (
            "Service must fail if HTTP port 80 is in use"
        )

    def test_service_healthcheck_uses_https(self) -> None:
        """Verify health check uses HTTPS protocol with self-signed cert acceptance."""
        service_file = OPENRC_DIR / "encryptor-api"
        content = service_file.read_text()

        assert "https://" in content, "Health check must use HTTPS protocol"
        assert "--no-check-certificate" in content, (
            "Health check must accept self-signed certificate"
        )

    def test_service_verifies_port_443_listening(self) -> None:
        """Verify start_post checks that port 443 is listening."""
        service_file = OPENRC_DIR / "encryptor-api"
        content = service_file.read_text()

        assert ":443" in content, "Service must verify port 443 is listening"

    def test_service_uses_https_port(self) -> None:
        """Verify service configuration references port 443 (AC: #3)."""
        service_file = OPENRC_DIR / "encryptor-api"
        content = service_file.read_text()

        assert "443" in content

    def test_service_http_rejection_error_message(self) -> None:
        """Verify clear error message when HTTP port 80 is detected (AC: #4)."""
        service_file = OPENRC_DIR / "encryptor-api"
        content = service_file.read_text()

        assert "HTTP listener detected" in content or "port 80" in content.lower(), (
            "Service must provide clear error message about HTTP port 80 rejection"
        )


class TestHttpsEndToEndConfigChain:
    """E2E test: Verify complete HTTPS configuration chain (Task 6.6, AC: #1-#4).

    Validates that certificate paths, TLS settings, and port configuration
    are consistent across build script, service file, uvicorn wrapper,
    and frontend proxy.
    """

    CERT_PATH = "/etc/encryptor-sim/tls/server.crt"
    KEY_PATH = "/etc/encryptor-sim/tls/server.key"

    def test_cert_path_consistent_across_build_and_service(self) -> None:
        """Verify certificate path matches between build script and service."""
        build_content = (IMAGE_DIR / "build-image.sh").read_text()
        service_content = (OPENRC_DIR / "encryptor-api").read_text()

        assert self.CERT_PATH in build_content
        assert self.CERT_PATH in service_content

    def test_key_path_consistent_across_build_and_service(self) -> None:
        """Verify key path matches between build script and service."""
        build_content = (IMAGE_DIR / "build-image.sh").read_text()
        service_content = (OPENRC_DIR / "encryptor-api").read_text()

        assert self.KEY_PATH in build_content
        assert self.KEY_PATH in service_content

    def test_uvicorn_default_paths_match_build(self) -> None:
        """Verify uvicorn default cert/key paths match build-generated paths."""
        uvicorn_content = (BACKEND_DIR / "uvicorn_server.py").read_text()

        assert self.CERT_PATH in uvicorn_content
        assert self.KEY_PATH in uvicorn_content

    def test_service_env_vars_match_uvicorn_env_vars(self) -> None:
        """Verify service exports match uvicorn env var names."""
        service_content = (OPENRC_DIR / "encryptor-api").read_text()
        uvicorn_content = (BACKEND_DIR / "uvicorn_server.py").read_text()

        assert "APP_SSL_CERTFILE" in service_content
        assert "APP_SSL_CERTFILE" in uvicorn_content
        assert "APP_SSL_KEYFILE" in service_content
        assert "APP_SSL_KEYFILE" in uvicorn_content

    def test_https_port_consistent_across_all_components(self) -> None:
        """Verify port 443 is used consistently in uvicorn and service."""
        uvicorn_content = (BACKEND_DIR / "uvicorn_server.py").read_text()
        service_content = (OPENRC_DIR / "encryptor-api").read_text()

        assert "port=443" in uvicorn_content
        assert "443" in service_content

    def test_frontend_proxy_targets_https_443(self) -> None:
        """Verify frontend dev proxy targets HTTPS on port 443."""
        vite_config = (PROJECT_ROOT / "frontend" / "vite.config.ts").read_text()

        assert "https://localhost:443" in vite_config
        assert "secure: false" in vite_config

    def test_build_order_cert_before_service(self) -> None:
        """Verify build script generates cert before installing services."""
        build_content = (IMAGE_DIR / "build-image.sh").read_text()

        cert_pos = build_content.find("generate_tls_certificate")
        service_pos = build_content.find("install_openrc_services")

        # Both must exist
        assert cert_pos > 0, "generate_tls_certificate must be in build script"
        assert service_pos > 0, "install_openrc_services must be in build script"

        # Certificate generation must come before service installation in main()
        # Find positions within main() function
        main_pos = build_content.find("main()")
        main_section = build_content[main_pos:]
        cert_in_main = main_section.find("generate_tls_certificate")
        service_in_main = main_section.find("install_openrc_services")

        assert cert_in_main < service_in_main, (
            "Certificate generation must occur before service installation in build"
        )
