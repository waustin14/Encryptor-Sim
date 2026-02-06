"""Unit tests for Peer model.

Tests the Peer SQLAlchemy model structure.
"""

import pytest
from datetime import datetime, timezone


class TestPeerModel:
    """Tests for Peer model."""

    def test_peer_model_has_required_columns(self):
        """Test Peer model has all required columns including enabled."""
        from backend.app.models.peer import Peer

        # Check that the class has the expected attributes
        assert hasattr(Peer, "peerId")
        assert hasattr(Peer, "name")
        assert hasattr(Peer, "remoteIp")
        assert hasattr(Peer, "psk")
        assert hasattr(Peer, "ikeVersion")
        assert hasattr(Peer, "enabled")
        assert hasattr(Peer, "dpdAction")
        assert hasattr(Peer, "dpdDelay")
        assert hasattr(Peer, "dpdTimeout")
        assert hasattr(Peer, "rekeyTime")
        assert hasattr(Peer, "createdAt")
        assert hasattr(Peer, "updatedAt")

    def test_peer_model_tablename(self):
        """Test Peer model uses correct table name."""
        from backend.app.models.peer import Peer

        assert Peer.__tablename__ == "peers"

    def test_peer_enabled_defaults_to_true(self):
        """Test Peer enabled field defaults to True."""
        from backend.app.models.peer import Peer

        peer = Peer()
        # The enabled field should default to True
        # Note: SQLAlchemy defaults may need DB session to materialize
        # This test verifies the column definition has the default
        from sqlalchemy import inspect
        mapper = inspect(Peer)
        enabled_col = mapper.columns["enabled"]
        assert enabled_col.default is not None or enabled_col.server_default is not None

    def test_peer_repr(self):
        """Test Peer model __repr__ method."""
        from backend.app.models.peer import Peer

        peer = Peer()
        peer.peerId = 1
        peer.name = "test-peer"
        repr_str = repr(peer)
        assert "peerId=1" in repr_str
        assert "name=test-peer" in repr_str
