"""Unit tests for peer enabled field in schemas.

Tests that enabled field is properly included in all peer schemas.
"""

import pytest
from pydantic import ValidationError


class TestPeerEnabledSchema:
    """Tests for enabled field in peer schemas."""

    def test_peer_create_request_accepts_enabled(self):
        """Test PeerCreateRequest accepts enabled field."""
        from backend.app.schemas.ipsec_peer import PeerCreateRequest

        # Should accept enabled=True
        peer_data = {
            "name": "test-peer",
            "remoteIp": "10.0.0.1",
            "psk": "test-psk",
            "ikeVersion": "ikev2",
            "enabled": True
        }
        peer = PeerCreateRequest(**peer_data)
        assert peer.enabled is True

        # Should accept enabled=False
        peer_data["enabled"] = False
        peer = PeerCreateRequest(**peer_data)
        assert peer.enabled is False

    def test_peer_create_request_enabled_defaults_to_true(self):
        """Test PeerCreateRequest enabled defaults to True when not provided."""
        from backend.app.schemas.ipsec_peer import PeerCreateRequest

        peer_data = {
            "name": "test-peer",
            "remoteIp": "10.0.0.1",
            "psk": "test-psk",
            "ikeVersion": "ikev2"
        }
        peer = PeerCreateRequest(**peer_data)
        assert peer.enabled is True

    def test_peer_update_request_accepts_enabled(self):
        """Test PeerUpdateRequest accepts enabled field."""
        from backend.app.schemas.ipsec_peer import PeerUpdateRequest

        # Should accept enabled=True
        peer = PeerUpdateRequest(enabled=True)
        assert peer.enabled is True

        # Should accept enabled=False
        peer = PeerUpdateRequest(enabled=False)
        assert peer.enabled is False

        # Should accept None (no update)
        peer = PeerUpdateRequest()
        assert peer.enabled is None

    def test_peer_response_includes_enabled(self):
        """Test PeerResponse includes enabled field."""
        from backend.app.schemas.ipsec_peer import PeerResponse
        from datetime import datetime

        response_data = {
            "peerId": 1,
            "name": "test-peer",
            "remoteIp": "10.0.0.1",
            "ikeVersion": "ikev2",
            "enabled": True,
            "createdAt": datetime.now(),
            "updatedAt": datetime.now(),
            "operationalStatus": "ready"
        }
        response = PeerResponse(**response_data)
        assert response.enabled is True
        assert hasattr(response, "enabled")
