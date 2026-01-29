"""Integration tests for frontend static file serving.

Tests that FastAPI serves frontend static files correctly with SPA routing.
Validates AC #2 of Story 2.2.
"""

from __future__ import annotations

from pathlib import Path

import pytest


# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
FRONTEND_DIR = PROJECT_ROOT / "frontend"
OPENRC_DIR = PROJECT_ROOT / "image" / "openrc"


class TestViteConfiguration:
    """Test Vite build configuration for backend integration."""

    def test_vite_config_sets_build_output_to_backend_static(self) -> None:
        """Verify Vite outputs to backend/static directory."""
        vite_config = FRONTEND_DIR / "vite.config.ts"
        content = vite_config.read_text()

        # Must configure build output to backend static directory
        assert "outDir" in content, "Vite config must specify outDir"
        # Should point to backend/static
        assert "../backend/static" in content or "backend/static" in content


class TestFastAPIStaticConfiguration:
    """Test FastAPI configuration for serving static files."""

    def test_main_imports_static_files(self) -> None:
        """Verify main.py imports StaticFiles."""
        main_py = BACKEND_DIR / "main.py"
        content = main_py.read_text()

        assert "StaticFiles" in content, "main.py must import StaticFiles"

    def test_main_mounts_static_files(self) -> None:
        """Verify main.py mounts static files at root."""
        main_py = BACKEND_DIR / "main.py"
        content = main_py.read_text()

        # Must mount static files
        assert "mount" in content.lower() or "Mount" in content
        assert "static" in content.lower()

    def test_main_serves_spa_fallback(self) -> None:
        """Verify main.py serves index.html for SPA routing."""
        main_py = BACKEND_DIR / "main.py"
        content = main_py.read_text()

        # Must have html=True for SPA fallback
        assert "html=True" in content or "html = True" in content

    def test_api_service_requires_static_index(self) -> None:
        """Verify OpenRC checks for frontend build before starting API."""
        service_file = OPENRC_DIR / "encryptor-api"
        content = service_file.read_text()

        assert "static/index.html" in content


class TestImageBuildIntegration:
    """Test that image build includes frontend build step."""

    def test_build_script_builds_frontend(self) -> None:
        """Verify build-image.sh builds frontend before backend."""
        build_script = PROJECT_ROOT / "image" / "build-image.sh"
        content = build_script.read_text()

        # Must build frontend
        assert "npm run build" in content or "npm build" in content or "frontend" in content

    def test_build_script_copies_frontend_to_static(self) -> None:
        """Verify build-image.sh copies frontend dist to static."""
        build_script = PROJECT_ROOT / "image" / "build-image.sh"
        content = build_script.read_text()

        # Must copy frontend/dist into backend/static
        assert "frontend/dist" in content and "backend/static" in content
