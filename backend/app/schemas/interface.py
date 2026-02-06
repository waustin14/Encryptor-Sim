"""Interface configuration schemas for request/response validation.

Defines Pydantic models for interface configuration API.
"""

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class InterfaceConfigRequest(BaseModel):
    """Request schema for configuring an interface."""

    ipAddress: str = Field(..., description="IPv4 address")
    netmask: str = Field(..., description="IPv4 netmask in dotted notation")
    gateway: str = Field(..., description="IPv4 gateway address")


class InterfaceConfigResponse(BaseModel):
    """Response schema for a single interface configuration."""

    interfaceId: int
    name: str
    ipAddress: Optional[str] = None
    netmask: Optional[str] = None
    gateway: Optional[str] = None
    namespace: str
    device: str

    model_config = ConfigDict(from_attributes=True)


class InterfaceConfigEnvelope(BaseModel):
    """Envelope response for a single interface."""

    data: InterfaceConfigResponse
    meta: dict[str, Any] = Field(default_factory=dict)


class InterfaceListEnvelope(BaseModel):
    """Envelope response for interface list."""

    data: list[InterfaceConfigResponse]
    meta: dict[str, Any] = Field(default_factory=dict)
