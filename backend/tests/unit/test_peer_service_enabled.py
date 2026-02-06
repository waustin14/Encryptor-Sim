"""Unit tests for peer service enabled field support.

Tests that create_peer and update_peer properly handle the enabled field.
"""

import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Set test environment variables
os.environ.setdefault("APP_PSK_ENCRYPTION_KEY", "test-key-for-testing-32bytes1")
os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-for-jwt-testing")

from backend.app.db.base import Base
from backend.app.models.peer import Peer
from backend.app.services.ipsec_peer_service import create_peer, update_peer


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class TestPeerServiceEnabled:
    """Tests for enabled field in peer service functions."""

    def test_create_peer_with_enabled_true(self, db_session):
        """Test creating a peer with enabled=True."""
        peer = create_peer(
            session=db_session,
            name="test-peer-enabled",
            remote_ip="10.0.0.1",
            psk_plaintext="test-psk",
            ike_version="ikev2",
            enabled=True
        )

        assert peer.enabled is True
        assert peer.name == "test-peer-enabled"

    def test_create_peer_with_enabled_false(self, db_session):
        """Test creating a peer with enabled=False."""
        peer = create_peer(
            session=db_session,
            name="test-peer-disabled",
            remote_ip="10.0.0.2",
            psk_plaintext="test-psk",
            ike_version="ikev2",
            enabled=False
        )

        assert peer.enabled is False
        assert peer.name == "test-peer-disabled"

    def test_create_peer_defaults_to_enabled_true(self, db_session):
        """Test that create_peer defaults to enabled=True when not specified."""
        peer = create_peer(
            session=db_session,
            name="test-peer-default",
            remote_ip="10.0.0.3",
            psk_plaintext="test-psk",
            ike_version="ikev2"
        )

        assert peer.enabled is True

    def test_update_peer_can_disable(self, db_session):
        """Test updating a peer to set enabled=False."""
        # Create an enabled peer
        peer = create_peer(
            session=db_session,
            name="test-peer",
            remote_ip="10.0.0.4",
            psk_plaintext="test-psk",
            ike_version="ikev2",
            enabled=True
        )

        assert peer.enabled is True

        # Disable the peer
        updated_peer = update_peer(
            session=db_session,
            peer=peer,
            enabled=False
        )

        assert updated_peer.enabled is False
        assert updated_peer.peerId == peer.peerId

    def test_update_peer_can_enable(self, db_session):
        """Test updating a peer to set enabled=True."""
        # Create a disabled peer
        peer = create_peer(
            session=db_session,
            name="test-peer-2",
            remote_ip="10.0.0.5",
            psk_plaintext="test-psk",
            ike_version="ikev2",
            enabled=False
        )

        assert peer.enabled is False

        # Enable the peer
        updated_peer = update_peer(
            session=db_session,
            peer=peer,
            enabled=True
        )

        assert updated_peer.enabled is True
        assert updated_peer.peerId == peer.peerId

    def test_update_peer_enabled_none_does_not_change(self, db_session):
        """Test that update_peer with enabled=None does not change the enabled state."""
        # Create an enabled peer
        peer = create_peer(
            session=db_session,
            name="test-peer-3",
            remote_ip="10.0.0.6",
            psk_plaintext="test-psk",
            ike_version="ikev2",
            enabled=True
        )

        # Update other fields but not enabled
        updated_peer = update_peer(
            session=db_session,
            peer=peer,
            name="updated-peer-3"
        )

        assert updated_peer.enabled is True
        assert updated_peer.name == "updated-peer-3"
