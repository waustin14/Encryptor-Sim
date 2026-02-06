"""Unit tests for IPsec peer validation service (Story 4.2, Task 3)."""

import os

os.environ.setdefault("APP_PSK_ENCRYPTION_KEY", "test-key-for-testing-32bytes1")
os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-for-jwt-testing")

from unittest.mock import MagicMock

from backend.app.models.peer import Peer
from backend.app.services.ipsec_peer_service import (
    cascade_delete_routes,
    validate_dpd_params,
    validate_ike_version,
    validate_peer_config,
    validate_rekey_time,
    validate_remote_ip,
)


class TestRemoteIpValidation:
    """Tests for remote IP address validation (Task 3.1)."""

    def test_valid_private_ip_accepted(self) -> None:
        valid, _ = validate_remote_ip("10.1.1.100")
        assert valid is True

    def test_valid_172_range_accepted(self) -> None:
        valid, _ = validate_remote_ip("172.16.0.1")
        assert valid is True

    def test_valid_192_range_accepted(self) -> None:
        valid, _ = validate_remote_ip("192.168.1.1")
        assert valid is True

    def test_invalid_ip_format_rejected(self) -> None:
        valid, msg = validate_remote_ip("999.999.999.999")
        assert valid is False
        assert "Invalid IP address" in msg

    def test_non_numeric_ip_rejected(self) -> None:
        valid, msg = validate_remote_ip("not-an-ip")
        assert valid is False
        assert "Invalid IP address" in msg

    def test_unspecified_ip_rejected(self) -> None:
        valid, msg = validate_remote_ip("0.0.0.0")
        assert valid is False
        assert "Reserved" in msg

    def test_broadcast_ip_rejected(self) -> None:
        valid, msg = validate_remote_ip("255.255.255.255")
        assert valid is False
        assert "Broadcast" in msg

    def test_loopback_ip_rejected(self) -> None:
        valid, msg = validate_remote_ip("127.0.0.1")
        assert valid is False
        assert "Loopback" in msg

    def test_empty_string_rejected(self) -> None:
        valid, msg = validate_remote_ip("")
        assert valid is False


class TestIkeVersionValidation:
    """Tests for IKE version validation (Task 3.2)."""

    def test_ikev1_accepted(self) -> None:
        valid, _ = validate_ike_version("ikev1")
        assert valid is True

    def test_ikev2_accepted(self) -> None:
        valid, _ = validate_ike_version("ikev2")
        assert valid is True

    def test_case_insensitive_ikev2(self) -> None:
        valid, _ = validate_ike_version("IKEv2")
        assert valid is True

    def test_case_insensitive_ikev1(self) -> None:
        valid, _ = validate_ike_version("IKEV1")
        assert valid is True

    def test_ikev3_rejected(self) -> None:
        valid, msg = validate_ike_version("ikev3")
        assert valid is False
        assert "Invalid IKE version" in msg

    def test_empty_rejected(self) -> None:
        valid, msg = validate_ike_version("")
        assert valid is False

    def test_arbitrary_string_rejected(self) -> None:
        valid, msg = validate_ike_version("foobar")
        assert valid is False


class TestDpdValidation:
    """Tests for DPD parameter validation (Task 3.3)."""

    def test_valid_dpd_params_accepted(self) -> None:
        valid, _ = validate_dpd_params("restart", 30, 150)
        assert valid is True

    def test_all_dpd_actions_accepted(self) -> None:
        for action in ("clear", "hold", "restart"):
            valid, _ = validate_dpd_params(action, 30, 150)
            assert valid is True, f"Action {action} should be valid"

    def test_invalid_dpd_action_rejected(self) -> None:
        valid, msg = validate_dpd_params("invalid", 30, 150)
        assert valid is False
        assert "DPD action" in msg

    def test_dpd_delay_too_small_rejected(self) -> None:
        valid, msg = validate_dpd_params("restart", 5, 150)
        assert valid is False
        assert "DPD delay" in msg

    def test_dpd_delay_too_large_rejected(self) -> None:
        valid, msg = validate_dpd_params("restart", 500, 600)
        assert valid is False
        assert "DPD delay" in msg

    def test_dpd_timeout_too_small_rejected(self) -> None:
        valid, msg = validate_dpd_params("restart", 30, 5)
        assert valid is False
        assert "DPD timeout" in msg

    def test_dpd_timeout_must_exceed_delay(self) -> None:
        valid, msg = validate_dpd_params("restart", 30, 30)
        assert valid is False
        assert "greater than" in msg

    def test_none_params_accepted(self) -> None:
        valid, _ = validate_dpd_params(None, None, None)
        assert valid is True


class TestRekeyValidation:
    """Tests for rekey time validation (Task 3.4)."""

    def test_valid_rekey_time_accepted(self) -> None:
        valid, _ = validate_rekey_time(3600)
        assert valid is True

    def test_min_rekey_time_accepted(self) -> None:
        valid, _ = validate_rekey_time(300)
        assert valid is True

    def test_max_rekey_time_accepted(self) -> None:
        valid, _ = validate_rekey_time(86400)
        assert valid is True

    def test_rekey_too_small_rejected(self) -> None:
        valid, msg = validate_rekey_time(100)
        assert valid is False
        assert "Rekey time" in msg

    def test_rekey_too_large_rejected(self) -> None:
        valid, msg = validate_rekey_time(100000)
        assert valid is False
        assert "Rekey time" in msg

    def test_none_rekey_accepted(self) -> None:
        valid, _ = validate_rekey_time(None)
        assert valid is True


class TestPeerConfigValidation:
    """Tests for combined peer config validation."""

    def test_valid_full_config_accepted(self) -> None:
        valid, _ = validate_peer_config(
            remote_ip="10.1.1.100",
            ike_version="ikev2",
            dpd_action="restart",
            dpd_delay=30,
            dpd_timeout=150,
            rekey_time=3600,
        )
        assert valid is True

    def test_invalid_ip_fails_full_validation(self) -> None:
        valid, msg = validate_peer_config(
            remote_ip="999.999.999.999",
            ike_version="ikev2",
        )
        assert valid is False
        assert "IP address" in msg

    def test_invalid_ike_fails_full_validation(self) -> None:
        valid, msg = validate_peer_config(
            remote_ip="10.1.1.100",
            ike_version="ikev3",
        )
        assert valid is False
        assert "IKE version" in msg


class TestOperationalStatus:
    """Tests for Peer.operationalStatus computed property (Story 4.6, Task 1)."""

    def _make_peer(self, **overrides) -> Peer:
        """Create a Peer instance with default valid fields."""
        defaults = {
            "name": "test-peer",
            "remoteIp": "10.1.1.100",
            "psk": "encrypted-psk-value",
            "ikeVersion": "ikev2",
        }
        defaults.update(overrides)
        return Peer(**defaults)

    def test_ready_when_all_required_fields_valid(self) -> None:
        """Verify 'ready' when name, remoteIp, psk, ikeVersion all valid."""
        peer = self._make_peer()
        assert peer.operationalStatus == "ready"

    def test_incomplete_when_name_empty(self) -> None:
        """Verify 'incomplete' when name is empty string."""
        peer = self._make_peer(name="")
        assert peer.operationalStatus == "incomplete"

    def test_incomplete_when_name_whitespace_only(self) -> None:
        """Verify 'incomplete' when name is whitespace only."""
        peer = self._make_peer(name="   ")
        assert peer.operationalStatus == "incomplete"

    def test_incomplete_when_name_none(self) -> None:
        """Verify 'incomplete' when name is None."""
        peer = self._make_peer(name=None)
        assert peer.operationalStatus == "incomplete"

    def test_incomplete_when_remote_ip_empty(self) -> None:
        """Verify 'incomplete' when remoteIp is empty string."""
        peer = self._make_peer(remoteIp="")
        assert peer.operationalStatus == "incomplete"

    def test_incomplete_when_remote_ip_invalid_format(self) -> None:
        """Verify 'incomplete' when remoteIp is not a valid IP."""
        peer = self._make_peer(remoteIp="not-an-ip")
        assert peer.operationalStatus == "incomplete"

    def test_incomplete_when_remote_ip_none(self) -> None:
        """Verify 'incomplete' when remoteIp is None."""
        peer = self._make_peer(remoteIp=None)
        assert peer.operationalStatus == "incomplete"

    def test_incomplete_when_psk_none(self) -> None:
        """Verify 'incomplete' when psk is None."""
        peer = self._make_peer(psk=None)
        assert peer.operationalStatus == "incomplete"

    def test_incomplete_when_psk_empty(self) -> None:
        """Verify 'incomplete' when psk is empty string."""
        peer = self._make_peer(psk="")
        assert peer.operationalStatus == "incomplete"

    def test_incomplete_when_ike_version_invalid(self) -> None:
        """Verify 'incomplete' when ikeVersion is not ikev1/ikev2."""
        peer = self._make_peer(ikeVersion="ikev3")
        assert peer.operationalStatus == "incomplete"

    def test_incomplete_when_ike_version_none(self) -> None:
        """Verify 'incomplete' when ikeVersion is None."""
        peer = self._make_peer(ikeVersion=None)
        assert peer.operationalStatus == "incomplete"

    def test_incomplete_when_ike_version_empty(self) -> None:
        """Verify 'incomplete' when ikeVersion is empty string."""
        peer = self._make_peer(ikeVersion="")
        assert peer.operationalStatus == "incomplete"

    def test_ready_with_ikev1(self) -> None:
        """Verify 'ready' with ikeVersion='ikev1'."""
        peer = self._make_peer(ikeVersion="ikev1")
        assert peer.operationalStatus == "ready"

    def test_ready_with_ikev2(self) -> None:
        """Verify 'ready' with ikeVersion='ikev2'."""
        peer = self._make_peer(ikeVersion="ikev2")
        assert peer.operationalStatus == "ready"


class TestCascadeDeleteRoutes:
    """Tests for cascade route deletion (Story 4.3, Task 2)."""

    def test_cascade_returns_zero_when_no_route_model(self) -> None:
        """Verify cascade deletion returns 0 when Route model doesn't exist."""
        session = MagicMock()
        result = cascade_delete_routes(session, 1)
        assert result == 0
