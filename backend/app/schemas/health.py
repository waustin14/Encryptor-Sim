"""Health check response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ServiceStatus(BaseModel):
    """Status of a single service."""

    namespaces: str
    daemon: str
    api: str
    database: str
    isolation: str
    webUi: str


class MgmtInterfaceStatus(BaseModel):
    """Status of the MGMT network interface including DHCP state."""

    interface: str
    ip: str | None
    netmask: str | None  # Added for static config (Story 2.4)
    gateway: str | None  # Added for static config (Story 2.4)
    method: str  # dhcp, static, or unknown
    leaseStatus: str  # obtained, failed, static, or unknown
    status: str  # up, down, unknown, or error


class HealthData(BaseModel):
    """Health check data."""

    status: str
    bootDuration: float | None  # None if boot timestamps unavailable (Story 2.5)
    bootTarget: bool | None  # True if boot duration < target; None if unavailable (Story 2.5)
    bootTargetSeconds: float
    bootWithinTarget: bool | None  # Deprecated: use bootTarget (kept for compatibility)
    services: ServiceStatus
    mgmtInterface: MgmtInterfaceStatus
    timestamp: datetime


class HealthResponse(BaseModel):
    """Health check API response following { data, meta } envelope."""

    data: HealthData
    meta: dict[str, Any]
