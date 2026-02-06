"""IPsec peer schemas for request/response validation.

Defines Pydantic models for peer configuration API.
"""

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PeerCreateRequest(BaseModel):
    """Request schema for creating a peer."""

    name: str = Field(..., min_length=1, max_length=100, description="Unique peer name")
    remoteIp: str = Field(..., description="Remote IPv4 address")
    psk: str = Field(..., min_length=1, description="Pre-shared key")
    ikeVersion: str = Field(..., description="IKE version (ikev1 or ikev2)")
    enabled: bool = Field(default=True, description="Whether peer is enabled")
    dpdAction: Optional[str] = Field(
        default="restart", description="DPD action (clear, hold, restart)"
    )
    dpdDelay: Optional[int] = Field(default=30, description="DPD delay in seconds")
    dpdTimeout: Optional[int] = Field(
        default=150, description="DPD timeout in seconds"
    )
    rekeyTime: Optional[int] = Field(
        default=3600, description="Rekey time in seconds"
    )


class PeerUpdateRequest(BaseModel):
    """Request schema for updating a peer. All fields optional."""

    name: Optional[str] = Field(
        default=None, min_length=1, max_length=100, description="Peer name"
    )
    remoteIp: Optional[str] = Field(default=None, description="Remote IPv4 address")
    psk: Optional[str] = Field(
        default=None, min_length=1, description="Pre-shared key"
    )
    ikeVersion: Optional[str] = Field(
        default=None, description="IKE version (ikev1 or ikev2)"
    )
    enabled: Optional[bool] = Field(default=None, description="Whether peer is enabled")
    dpdAction: Optional[str] = Field(
        default=None, description="DPD action (clear, hold, restart)"
    )
    dpdDelay: Optional[int] = Field(default=None, description="DPD delay in seconds")
    dpdTimeout: Optional[int] = Field(
        default=None, description="DPD timeout in seconds"
    )
    rekeyTime: Optional[int] = Field(
        default=None, description="Rekey time in seconds"
    )


class PeerResponse(BaseModel):
    """Response schema for a single peer (PSK excluded)."""

    peerId: int
    name: str
    remoteIp: str
    ikeVersion: str
    enabled: bool
    dpdAction: Optional[str] = None
    dpdDelay: Optional[int] = None
    dpdTimeout: Optional[int] = None
    rekeyTime: Optional[int] = None
    createdAt: datetime
    updatedAt: datetime
    operationalStatus: Literal["ready", "incomplete"]

    model_config = ConfigDict(from_attributes=True)

    @field_validator("operationalStatus")
    @classmethod
    def validate_operational_status(cls, v: str) -> str:
        """Ensure operationalStatus is one of allowed values."""
        allowed = {"ready", "incomplete"}
        if v not in allowed:
            raise ValueError(f"operationalStatus must be one of {allowed}")
        return v


class PeerEnvelope(BaseModel):
    """Envelope response for a single peer."""

    data: PeerResponse
    meta: dict[str, Any] = Field(default_factory=dict)


class PeerListEnvelope(BaseModel):
    """Envelope response for peer list."""

    data: list[PeerResponse]
    meta: dict[str, Any] = Field(default_factory=dict)
