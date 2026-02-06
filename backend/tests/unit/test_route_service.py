"""Unit tests for route service (Story 4.4).

Tests verify CIDR validation and route service operations.
"""

import os

import pytest

os.environ.setdefault("APP_PSK_ENCRYPTION_KEY", "test-key-for-testing-32bytes1")
os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-for-jwt-testing")

from backend.app.services.route_service import delete_route, validate_cidr


class TestCidrValidation:
    """Unit tests for CIDR validation logic (AC: #5)."""

    def test_valid_cidr_24(self):
        """Verify standard /24 CIDR is valid."""
        is_valid, error, normalized = validate_cidr("192.168.1.0/24")
        assert is_valid
        assert error == ""
        assert normalized == "192.168.1.0/24"

    def test_valid_cidr_normalizes_host_bits(self):
        """Verify host bits are cleared (strict=False)."""
        is_valid, error, normalized = validate_cidr("192.168.1.5/24")
        assert is_valid
        assert normalized == "192.168.1.0/24"

    def test_valid_cidr_slash_0(self):
        """Verify /0 (default route) is valid."""
        is_valid, error, normalized = validate_cidr("0.0.0.0/0")
        assert is_valid
        assert normalized == "0.0.0.0/0"

    def test_valid_cidr_slash_32(self):
        """Verify /32 (single host) is valid."""
        is_valid, error, normalized = validate_cidr("10.0.0.1/32")
        assert is_valid
        assert normalized == "10.0.0.1/32"

    def test_valid_cidr_slash_8(self):
        """Verify /8 CIDR is valid."""
        is_valid, error, normalized = validate_cidr("10.0.0.0/8")
        assert is_valid
        assert normalized == "10.0.0.0/8"

    def test_invalid_cidr_slash_33(self):
        """Verify /33 prefix is rejected."""
        is_valid, error, normalized = validate_cidr("192.168.1.0/33")
        assert not is_valid
        assert "Invalid CIDR" in error

    def test_invalid_cidr_no_prefix(self):
        """Verify address without prefix is still valid (treated as /32)."""
        is_valid, error, normalized = validate_cidr("192.168.1.1")
        assert is_valid
        assert normalized == "192.168.1.1/32"

    def test_invalid_cidr_not_an_address(self):
        """Verify non-address string is rejected."""
        is_valid, error, normalized = validate_cidr("not-a-cidr")
        assert not is_valid
        assert "Invalid CIDR" in error

    def test_invalid_cidr_empty_string(self):
        """Verify empty string is rejected."""
        is_valid, error, normalized = validate_cidr("")
        assert not is_valid

    def test_invalid_cidr_octets_out_of_range(self):
        """Verify IP with octets > 255 is rejected."""
        is_valid, error, normalized = validate_cidr("999.999.999.999/24")
        assert not is_valid

    def test_valid_cidr_172_16(self):
        """Verify 172.16.0.0/12 is valid."""
        is_valid, error, normalized = validate_cidr("172.16.0.0/12")
        assert is_valid
        assert normalized == "172.16.0.0/12"


class TestDeleteRoute:
    """Unit tests for delete_route service function (Story 4.5, Task 5.8)."""

    def test_delete_route_removes_from_db(self):
        """Verify delete_route removes route from database."""
        from backend.app.db.deps import get_db_session
        from backend.app.models.peer import Peer
        from backend.app.models.route import Route
        from backend.app.services.route_service import create_route, get_route_by_id

        gen = get_db_session()
        session = next(gen)
        try:
            # Clean up
            session.query(Route).delete()
            session.query(Peer).delete()
            session.commit()

            # Create peer and route
            peer = Peer(
                name="unit-test-peer",
                remoteIp="10.0.0.1",
                psk="encrypted-psk",
                ikeVersion="ikev2",
            )
            session.add(peer)
            session.commit()
            session.refresh(peer)

            route = create_route(session, peer.peerId, "192.168.1.0/24")
            route_id = route.routeId

            # Delete route
            peer_name, peer_id = delete_route(session, route_id)

            assert peer_name == "unit-test-peer"
            assert peer_id == peer.peerId
            assert get_route_by_id(session, route_id) is None
        finally:
            try:
                next(gen)
            except StopIteration:
                pass

    def test_delete_route_nonexistent_raises_error(self):
        """Verify delete_route raises ValueError for nonexistent route."""
        import pytest

        from backend.app.db.deps import get_db_session

        gen = get_db_session()
        session = next(gen)
        try:
            with pytest.raises(ValueError, match="not found"):
                delete_route(session, 99999)
        finally:
            try:
                next(gen)
            except StopIteration:
                pass

    def test_delete_route_returns_peer_info(self):
        """Verify delete_route returns peer name and ID."""
        from backend.app.db.deps import get_db_session
        from backend.app.models.peer import Peer
        from backend.app.models.route import Route
        from backend.app.services.route_service import create_route

        gen = get_db_session()
        session = next(gen)
        try:
            session.query(Route).delete()
            session.query(Peer).delete()
            session.commit()

            peer = Peer(
                name="info-peer",
                remoteIp="10.0.0.2",
                psk="encrypted-psk",
                ikeVersion="ikev2",
            )
            session.add(peer)
            session.commit()
            session.refresh(peer)

            route = create_route(session, peer.peerId, "10.0.0.0/8")
            peer_name, peer_id = delete_route(session, route.routeId)

            assert peer_name == "info-peer"
            assert peer_id == peer.peerId
        finally:
            try:
                next(gen)
            except StopIteration:
                pass
