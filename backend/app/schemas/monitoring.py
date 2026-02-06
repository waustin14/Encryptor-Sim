"""Monitoring schemas for tunnel telemetry and interface statistics.

Defines Pydantic models for the monitoring REST API responses.
"""

from typing import Any, Optional

from pydantic import BaseModel, Field


class TunnelTelemetryEntry(BaseModel):
    """Telemetry data for a single tunnel/peer."""

    peerId: int
    peerName: str
    status: str
    establishedSec: int = 0
    bytesIn: int = 0
    bytesOut: int = 0
    packetsIn: int = 0
    packetsOut: int = 0
    isPassingTraffic: Optional[bool] = None
    lastTrafficAt: Optional[str] = None
    timestamp: str


class TunnelTelemetryEnvelope(BaseModel):
    """Envelope response for tunnel telemetry list."""

    data: list[TunnelTelemetryEntry]
    meta: dict[str, Any] = Field(default_factory=dict)


class InterfaceStatsEntry(BaseModel):
    """Statistics for a single network interface."""

    interface: str
    bytesRx: int = 0
    bytesTx: int = 0
    packetsRx: int = 0
    packetsTx: int = 0
    errorsRx: int = 0
    errorsTx: int = 0
    timestamp: str


class InterfaceStatsEnvelope(BaseModel):
    """Envelope response for interface statistics list."""

    data: list[InterfaceStatsEntry]
    meta: dict[str, Any] = Field(default_factory=dict)
