"""Unit tests for monitoring Pydantic schemas (Story 5.5, Task 1.4).

Tests verify tunnel telemetry and interface stats schema validation,
default values, and serialization.
"""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from backend.app.schemas.monitoring import (
    InterfaceStatsEntry,
    InterfaceStatsEnvelope,
    TunnelTelemetryEntry,
    TunnelTelemetryEnvelope,
)


class TestTunnelTelemetryEntry:
    """Tests for TunnelTelemetryEntry schema."""

    def test_valid_full_entry(self):
        entry = TunnelTelemetryEntry(
            peerId=1,
            peerName="site-a",
            status="up",
            establishedSec=3600,
            bytesIn=1024,
            bytesOut=2048,
            packetsIn=10,
            packetsOut=20,
            isPassingTraffic=True,
            lastTrafficAt="2026-02-06T12:00:00+00:00",
            timestamp="2026-02-06T12:00:00+00:00",
        )
        assert entry.peerId == 1
        assert entry.peerName == "site-a"
        assert entry.status == "up"
        assert entry.establishedSec == 3600
        assert entry.bytesIn == 1024
        assert entry.bytesOut == 2048
        assert entry.packetsIn == 10
        assert entry.packetsOut == 20
        assert entry.isPassingTraffic is True
        assert entry.lastTrafficAt == "2026-02-06T12:00:00+00:00"

    def test_defaults_for_optional_fields(self):
        entry = TunnelTelemetryEntry(
            peerId=2,
            peerName="site-b",
            status="down",
            timestamp="2026-02-06T12:00:00+00:00",
        )
        assert entry.establishedSec == 0
        assert entry.bytesIn == 0
        assert entry.bytesOut == 0
        assert entry.packetsIn == 0
        assert entry.packetsOut == 0
        assert entry.isPassingTraffic is None
        assert entry.lastTrafficAt is None

    def test_nullable_traffic_fields(self):
        entry = TunnelTelemetryEntry(
            peerId=3,
            peerName="site-c",
            status="up",
            isPassingTraffic=None,
            lastTrafficAt=None,
            timestamp="2026-02-06T12:00:00+00:00",
        )
        assert entry.isPassingTraffic is None
        assert entry.lastTrafficAt is None

    def test_missing_required_fields_raises(self):
        with pytest.raises(ValidationError):
            TunnelTelemetryEntry(peerId=1, peerName="x")  # missing status, timestamp

    def test_serialization_includes_all_fields(self):
        entry = TunnelTelemetryEntry(
            peerId=1,
            peerName="site-a",
            status="up",
            timestamp="2026-02-06T12:00:00+00:00",
        )
        data = entry.model_dump()
        expected_keys = {
            "peerId", "peerName", "status", "establishedSec",
            "bytesIn", "bytesOut", "packetsIn", "packetsOut",
            "isPassingTraffic", "lastTrafficAt", "timestamp",
        }
        assert set(data.keys()) == expected_keys


class TestTunnelTelemetryEnvelope:
    """Tests for TunnelTelemetryEnvelope schema."""

    def test_envelope_structure(self):
        entry = TunnelTelemetryEntry(
            peerId=1, peerName="site-a", status="up",
            timestamp="2026-02-06T12:00:00+00:00",
        )
        envelope = TunnelTelemetryEnvelope(
            data=[entry],
            meta={"count": 1, "daemonAvailable": True},
        )
        assert len(envelope.data) == 1
        assert envelope.meta["count"] == 1
        assert envelope.meta["daemonAvailable"] is True

    def test_empty_data_list(self):
        envelope = TunnelTelemetryEnvelope(data=[], meta={"count": 0})
        assert envelope.data == []

    def test_meta_defaults_to_empty_dict(self):
        envelope = TunnelTelemetryEnvelope(data=[])
        assert envelope.meta == {}


class TestInterfaceStatsEntry:
    """Tests for InterfaceStatsEntry schema."""

    def test_valid_full_entry(self):
        entry = InterfaceStatsEntry(
            interface="CT",
            bytesRx=1000,
            bytesTx=2000,
            packetsRx=50,
            packetsTx=100,
            errorsRx=1,
            errorsTx=2,
            timestamp="2026-02-06T12:00:00+00:00",
        )
        assert entry.interface == "CT"
        assert entry.bytesRx == 1000
        assert entry.bytesTx == 2000
        assert entry.packetsRx == 50
        assert entry.packetsTx == 100
        assert entry.errorsRx == 1
        assert entry.errorsTx == 2

    def test_defaults_for_counter_fields(self):
        entry = InterfaceStatsEntry(
            interface="PT",
            timestamp="2026-02-06T12:00:00+00:00",
        )
        assert entry.bytesRx == 0
        assert entry.bytesTx == 0
        assert entry.packetsRx == 0
        assert entry.packetsTx == 0
        assert entry.errorsRx == 0
        assert entry.errorsTx == 0

    def test_missing_required_fields_raises(self):
        with pytest.raises(ValidationError):
            InterfaceStatsEntry()  # missing interface, timestamp

    def test_serialization_includes_all_fields(self):
        entry = InterfaceStatsEntry(
            interface="MGMT",
            timestamp="2026-02-06T12:00:00+00:00",
        )
        data = entry.model_dump()
        expected_keys = {
            "interface", "bytesRx", "bytesTx", "packetsRx", "packetsTx",
            "errorsRx", "errorsTx", "timestamp",
        }
        assert set(data.keys()) == expected_keys


class TestInterfaceStatsEnvelope:
    """Tests for InterfaceStatsEnvelope schema."""

    def test_envelope_structure(self):
        entry = InterfaceStatsEntry(
            interface="CT", timestamp="2026-02-06T12:00:00+00:00",
        )
        envelope = InterfaceStatsEnvelope(
            data=[entry],
            meta={"count": 1, "daemonAvailable": True},
        )
        assert len(envelope.data) == 1
        assert envelope.meta["count"] == 1

    def test_empty_data_list(self):
        envelope = InterfaceStatsEnvelope(data=[], meta={"count": 0})
        assert envelope.data == []

    def test_meta_defaults_to_empty_dict(self):
        envelope = InterfaceStatsEnvelope(data=[])
        assert envelope.meta == {}
