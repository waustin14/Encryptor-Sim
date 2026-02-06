"""Unit tests for background polling tasks (Story 5.1, Task 4)."""

import asyncio
import os

os.environ.setdefault("APP_PSK_ENCRYPTION_KEY", "test-key-for-testing-32bytes1")
os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-for-jwt-testing")

from unittest.mock import AsyncMock, MagicMock, patch
from types import SimpleNamespace

from backend.app.ws.background_tasks import poll_interface_stats, poll_tunnel_status


class TestPollTunnelStatus:
    """Tests for poll_tunnel_status background task (AC: #8, #9)."""

    def test_emits_event_on_status_change(self) -> None:
        """Verify tunnel.status_changed event is emitted when status changes."""
        call_count = 0
        broadcast_calls = []

        mock_manager = MagicMock()

        async def mock_broadcast(msg):
            broadcast_calls.append(msg)

        mock_manager.broadcast = mock_broadcast

        def mock_send_command(cmd):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {"result": {"1": {
                    "status": "up",
                    "establishedSec": 100,
                    "bytesIn": 1024,
                    "bytesOut": 2048,
                    "packetsIn": 10,
                    "packetsOut": 20,
                }}}
            return {"result": {"1": {
                "status": "up",
                "establishedSec": 100,
                "bytesIn": 1024,
                "bytesOut": 2048,
                "packetsIn": 10,
                "packetsOut": 20,
            }}}

        async def run_poll():
            nonlocal call_count
            peers = [SimpleNamespace(peerId=1, name="site-a")]
            with (
                patch("backend.app.ws.background_tasks.send_command", side_effect=mock_send_command),
                patch("backend.app.ws.background_tasks.get_monitoring_ws_manager", return_value=mock_manager),
                patch("backend.app.ws.background_tasks._load_peers", return_value=peers),
                patch("backend.app.ws.background_tasks.asyncio.sleep", side_effect=[None, asyncio.CancelledError]),
            ):
                try:
                    await poll_tunnel_status()
                except asyncio.CancelledError:
                    pass

        asyncio.run(run_poll())

        # First poll should emit event (no previous state)
        assert len(broadcast_calls) >= 1
        assert broadcast_calls[0]["type"] == "tunnel.status_changed"
        assert broadcast_calls[0]["data"]["peerId"] == 1
        assert broadcast_calls[0]["data"]["peerName"] == "site-a"
        assert broadcast_calls[0]["data"]["status"] == "up"
        assert broadcast_calls[0]["data"]["establishedSec"] == 100
        assert broadcast_calls[0]["data"]["bytesIn"] == 1024

    def test_does_not_emit_when_status_unchanged(self) -> None:
        """Verify no event when tunnel status hasn't changed."""
        call_count = 0
        broadcast_calls = []

        mock_manager = MagicMock()

        async def mock_broadcast(msg):
            broadcast_calls.append(msg)

        mock_manager.broadcast = mock_broadcast

        def mock_send_command(cmd):
            return {"result": {"1": {
                "status": "up",
                "establishedSec": 100,
                "bytesIn": 1024,
                "bytesOut": 2048,
                "packetsIn": 10,
                "packetsOut": 20,
            }}}

        sleep_count = 0

        async def mock_sleep(n):
            nonlocal sleep_count
            sleep_count += 1
            if sleep_count >= 3:
                raise asyncio.CancelledError

        async def run_poll():
            peers = [SimpleNamespace(peerId=1, name="site-a")]
            with (
                patch("backend.app.ws.background_tasks.send_command", side_effect=mock_send_command),
                patch("backend.app.ws.background_tasks.get_monitoring_ws_manager", return_value=mock_manager),
                patch("backend.app.ws.background_tasks._load_peers", return_value=peers),
                patch("backend.app.ws.background_tasks.asyncio.sleep", side_effect=mock_sleep),
            ):
                try:
                    await poll_tunnel_status()
                except asyncio.CancelledError:
                    pass

        asyncio.run(run_poll())

        # Only first iteration should emit (status goes from None to "up")
        assert len(broadcast_calls) == 1

    def test_detects_traffic_flow_from_counter_deltas(self) -> None:
        """Verify isPassingTraffic is true when byte/packet counters increase (AC: #4, Task 2.2)."""
        call_count = 0
        broadcast_calls = []

        mock_manager = MagicMock()

        async def mock_broadcast(msg):
            broadcast_calls.append(msg)

        mock_manager.broadcast = mock_broadcast

        def mock_send_command(cmd):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {"result": {"1": {
                    "status": "up",
                    "establishedSec": 100,
                    "bytesIn": 1024,
                    "bytesOut": 2048,
                    "packetsIn": 10,
                    "packetsOut": 20,
                }}}
            # Second poll: counters increased
            return {"result": {"1": {
                "status": "up",
                "establishedSec": 110,
                "bytesIn": 2048,  # +1024
                "bytesOut": 4096,  # +2048
                "packetsIn": 20,  # +10
                "packetsOut": 40,  # +20
            }}}

        async def run_poll():
            peers = [SimpleNamespace(peerId=1, name="site-a")]
            with (
                patch("backend.app.ws.background_tasks.send_command", side_effect=mock_send_command),
                patch("backend.app.ws.background_tasks.get_monitoring_ws_manager", return_value=mock_manager),
                patch("backend.app.ws.background_tasks._load_peers", return_value=peers),
                patch("backend.app.ws.background_tasks.asyncio.sleep", side_effect=[None, asyncio.CancelledError]),
            ):
                try:
                    await poll_tunnel_status()
                except asyncio.CancelledError:
                    pass

        asyncio.run(run_poll())

        # Second poll should detect traffic (counters increased)
        assert len(broadcast_calls) >= 2
        second_event = broadcast_calls[1]
        assert second_event["data"]["isPassingTraffic"] is True
        assert second_event["data"]["lastTrafficAt"] is not None

    def test_detects_idle_tunnel_when_counters_unchanged(self) -> None:
        """Verify isPassingTraffic is false when counters don't change (AC: #4)."""
        call_count = 0
        broadcast_calls = []

        mock_manager = MagicMock()

        async def mock_broadcast(msg):
            broadcast_calls.append(msg)

        mock_manager.broadcast = mock_broadcast

        def mock_send_command(cmd):
            # Same counters every poll
            return {"result": {"1": {
                "status": "up",
                "establishedSec": 100,
                "bytesIn": 1024,
                "bytesOut": 2048,
                "packetsIn": 10,
                "packetsOut": 20,
            }}}

        async def run_poll():
            peers = [SimpleNamespace(peerId=1, name="site-a")]
            with (
                patch("backend.app.ws.background_tasks.send_command", side_effect=mock_send_command),
                patch("backend.app.ws.background_tasks.get_monitoring_ws_manager", return_value=mock_manager),
                patch("backend.app.ws.background_tasks._load_peers", return_value=peers),
                patch("backend.app.ws.background_tasks.asyncio.sleep", side_effect=[None, asyncio.CancelledError]),
            ):
                try:
                    await poll_tunnel_status()
                except asyncio.CancelledError:
                    pass

        asyncio.run(run_poll())

        # Second poll should NOT detect traffic (counters unchanged)
        # Only first poll emits (status change from None to "up")
        assert len(broadcast_calls) == 1

    def test_lastTrafficAt_persists_across_polls(self) -> None:
        """Verify lastTrafficAt timestamp persists when traffic stops (AC: #4, Task 2.3)."""
        call_count = 0
        broadcast_calls = []

        mock_manager = MagicMock()

        async def mock_broadcast(msg):
            broadcast_calls.append(msg)

        mock_manager.broadcast = mock_broadcast

        def mock_send_command(cmd):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {"result": {"1": {
                    "status": "up",
                    "establishedSec": 100,
                    "bytesIn": 1024,
                    "bytesOut": 2048,
                    "packetsIn": 10,
                    "packetsOut": 20,
                }}}
            elif call_count == 2:
                # Traffic flowing
                return {"result": {"1": {
                    "status": "up",
                    "establishedSec": 110,
                    "bytesIn": 2048,
                    "bytesOut": 4096,
                    "packetsIn": 20,
                    "packetsOut": 40,
                }}}
            elif call_count == 3:
                # Status changed to down
                return {"result": {"1": {
                    "status": "down",
                    "establishedSec": 0,
                    "bytesIn": 2048,
                    "bytesOut": 4096,
                    "packetsIn": 20,
                    "packetsOut": 40,
                }}}
            # Traffic stopped (counters unchanged)
            return {"result": {"1": {
                "status": "down",
                "establishedSec": 0,
                "bytesIn": 2048,
                "bytesOut": 4096,
                "packetsIn": 20,
                "packetsOut": 40,
            }}}

        sleep_count = 0

        async def mock_sleep(n):
            nonlocal sleep_count
            sleep_count += 1
            if sleep_count >= 4:
                raise asyncio.CancelledError

        async def run_poll():
            peers = [SimpleNamespace(peerId=1, name="site-a")]
            with (
                patch("backend.app.ws.background_tasks.send_command", side_effect=mock_send_command),
                patch("backend.app.ws.background_tasks.get_monitoring_ws_manager", return_value=mock_manager),
                patch("backend.app.ws.background_tasks._load_peers", return_value=peers),
                patch("backend.app.ws.background_tasks.asyncio.sleep", side_effect=mock_sleep),
            ):
                try:
                    await poll_tunnel_status()
                except asyncio.CancelledError:
                    pass

        asyncio.run(run_poll())

        # Find event with traffic detected
        traffic_event = next((e for e in broadcast_calls if e["data"].get("isPassingTraffic")), None)
        assert traffic_event is not None
        last_traffic_timestamp = traffic_event["data"]["lastTrafficAt"]

        # Find later event (status changed to down)
        down_event = next((e for e in broadcast_calls if e["data"]["status"] == "down"), None)
        assert down_event is not None
        # lastTrafficAt should still be present (persists)
        assert down_event["data"]["lastTrafficAt"] == last_traffic_timestamp

    def test_telemetry_fields_included_in_events(self) -> None:
        """Verify all telemetry fields are included in events (AC: #5, #6)."""
        broadcast_calls = []

        mock_manager = MagicMock()

        async def mock_broadcast(msg):
            broadcast_calls.append(msg)

        mock_manager.broadcast = mock_broadcast

        def mock_send_command(cmd):
            return {"result": {"1": {
                "status": "up",
                "establishedSec": 3600,
                "bytesIn": 10240,
                "bytesOut": 20480,
                "packetsIn": 100,
                "packetsOut": 200,
            }}}

        async def run_poll():
            peers = [SimpleNamespace(peerId=1, name="site-a")]
            with (
                patch("backend.app.ws.background_tasks.send_command", side_effect=mock_send_command),
                patch("backend.app.ws.background_tasks.get_monitoring_ws_manager", return_value=mock_manager),
                patch("backend.app.ws.background_tasks._load_peers", return_value=peers),
                patch("backend.app.ws.background_tasks.asyncio.sleep", side_effect=[asyncio.CancelledError]),
            ):
                try:
                    await poll_tunnel_status()
                except asyncio.CancelledError:
                    pass

        asyncio.run(run_poll())

        assert len(broadcast_calls) >= 1
        event = broadcast_calls[0]
        assert event["type"] == "tunnel.status_changed"
        data = event["data"]
        assert data["status"] == "up"
        assert data["establishedSec"] == 3600
        assert data["bytesIn"] == 10240
        assert data["bytesOut"] == 20480
        assert data["packetsIn"] == 100
        assert data["packetsOut"] == 200
        assert "isPassingTraffic" in data
        assert "lastTrafficAt" in data
        assert "timestamp" in data

    def test_handles_daemon_errors_gracefully(self) -> None:
        """Verify task continues when daemon IPC fails."""
        sleep_count = 0

        async def mock_sleep(n):
            nonlocal sleep_count
            sleep_count += 1
            if sleep_count >= 2:
                raise asyncio.CancelledError

        def mock_send_command(cmd):
            raise RuntimeError("Daemon not available")

        async def run_poll():
            with (
                patch("backend.app.ws.background_tasks.send_command", side_effect=mock_send_command),
                patch("backend.app.ws.background_tasks.asyncio.sleep", side_effect=mock_sleep),
            ):
                try:
                    await poll_tunnel_status()
                except asyncio.CancelledError:
                    pass

        # Should not raise
        asyncio.run(run_poll())
        assert sleep_count >= 2

    def test_falls_back_to_status_when_telemetry_empty(self) -> None:
        """Verify status still updates when telemetry command returns empty (AC: #8)."""
        broadcast_calls = []

        mock_manager = MagicMock()

        async def mock_broadcast(msg):
            broadcast_calls.append(msg)

        mock_manager.broadcast = mock_broadcast

        def mock_send_command(cmd):
            if cmd == "get_tunnel_telemetry":
                return {"result": {}}
            if cmd == "get_tunnel_status":
                return {"result": {"1": "up"}}
            return {"result": {}}

        async def run_poll():
            peers = [SimpleNamespace(peerId=1, name="site-a")]
            with (
                patch("backend.app.ws.background_tasks.send_command", side_effect=mock_send_command),
                patch("backend.app.ws.background_tasks.get_monitoring_ws_manager", return_value=mock_manager),
                patch("backend.app.ws.background_tasks._load_peers", return_value=peers),
                patch("backend.app.ws.background_tasks.asyncio.sleep", side_effect=[asyncio.CancelledError]),
            ):
                try:
                    await poll_tunnel_status()
                except asyncio.CancelledError:
                    pass

        asyncio.run(run_poll())

        assert len(broadcast_calls) == 1
        event = broadcast_calls[0]
        assert event["type"] == "tunnel.status_changed"
        assert event["data"]["status"] == "up"
        assert event["data"]["establishedSec"] == 0
        assert event["data"]["bytesIn"] == 0


class TestPollInterfaceStats:
    """Tests for poll_interface_stats background task (AC: #8)."""

    def test_emits_stats_for_all_interfaces(self) -> None:
        """Verify interface.stats_updated events emitted for each interface."""
        broadcast_calls = []

        mock_manager = MagicMock()

        async def mock_broadcast(msg):
            broadcast_calls.append(msg)

        mock_manager.broadcast = mock_broadcast

        def mock_send_command(cmd):
            return {
                "result": {
                    "CT": {"bytesRx": 100, "bytesTx": 200, "packetsRx": 10, "packetsTx": 20, "errorsRx": 0, "errorsTx": 0},
                    "PT": {"bytesRx": 300, "bytesTx": 400, "packetsRx": 30, "packetsTx": 40, "errorsRx": 0, "errorsTx": 0},
                    "MGMT": {"bytesRx": 50, "bytesTx": 60, "packetsRx": 5, "packetsTx": 6, "errorsRx": 0, "errorsTx": 0},
                }
            }

        async def run_poll():
            with (
                patch("backend.app.ws.background_tasks.send_command", side_effect=mock_send_command),
                patch("backend.app.ws.background_tasks.get_monitoring_ws_manager", return_value=mock_manager),
                patch("backend.app.ws.background_tasks.asyncio.sleep", side_effect=[asyncio.CancelledError]),
            ):
                try:
                    await poll_interface_stats()
                except asyncio.CancelledError:
                    pass

        asyncio.run(run_poll())

        # Should emit 3 events (one per interface)
        assert len(broadcast_calls) == 3
        interfaces = {call["data"]["interface"] for call in broadcast_calls}
        assert interfaces == {"CT", "PT", "MGMT"}

    def test_event_format_includes_timestamp(self) -> None:
        """Verify stats events include timestamp."""
        broadcast_calls = []

        mock_manager = MagicMock()

        async def mock_broadcast(msg):
            broadcast_calls.append(msg)

        mock_manager.broadcast = mock_broadcast

        def mock_send_command(cmd):
            return {
                "result": {
                    "CT": {"bytesRx": 0, "bytesTx": 0, "packetsRx": 0, "packetsTx": 0, "errorsRx": 0, "errorsTx": 0},
                }
            }

        async def run_poll():
            with (
                patch("backend.app.ws.background_tasks.send_command", side_effect=mock_send_command),
                patch("backend.app.ws.background_tasks.get_monitoring_ws_manager", return_value=mock_manager),
                patch("backend.app.ws.background_tasks.asyncio.sleep", side_effect=[asyncio.CancelledError]),
            ):
                try:
                    await poll_interface_stats()
                except asyncio.CancelledError:
                    pass

        asyncio.run(run_poll())

        assert len(broadcast_calls) == 1
        assert broadcast_calls[0]["type"] == "interface.stats_updated"
        assert "timestamp" in broadcast_calls[0]["data"]

    def test_handles_daemon_errors_gracefully(self) -> None:
        """Verify task continues when daemon IPC fails."""
        sleep_count = 0

        async def mock_sleep(n):
            nonlocal sleep_count
            sleep_count += 1
            if sleep_count >= 2:
                raise asyncio.CancelledError

        def mock_send_command(cmd):
            raise RuntimeError("Daemon not available")

        async def run_poll():
            with (
                patch("backend.app.ws.background_tasks.send_command", side_effect=mock_send_command),
                patch("backend.app.ws.background_tasks.asyncio.sleep", side_effect=mock_sleep),
            ):
                try:
                    await poll_interface_stats()
                except asyncio.CancelledError:
                    pass

        asyncio.run(run_poll())
        assert sleep_count >= 2
