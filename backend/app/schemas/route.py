"""Route schemas for request/response validation.

Defines Pydantic models for route configuration API.
"""

import ipaddress
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RouteCreateRequest(BaseModel):
    """Request schema for creating a route."""

    peerId: int = Field(..., description="ID of the peer to associate the route with")
    destinationCidr: str = Field(..., description="Destination CIDR (e.g., 192.168.1.0/24)")

    @field_validator("destinationCidr")
    @classmethod
    def validate_cidr(cls, v: str) -> str:
        """Validate and normalize CIDR format."""
        try:
            network = ipaddress.ip_network(v, strict=False)
            if network.version != 4:
                raise ValueError("Only IPv4 CIDRs are supported")
            return str(network)
        except ValueError as e:
            raise ValueError(f"Invalid CIDR format: {v} ({e})")


class RouteUpdateRequest(BaseModel):
    """Request schema for updating a route. Only destinationCidr can be changed."""

    destinationCidr: Optional[str] = Field(
        default=None, description="Updated destination CIDR"
    )

    @field_validator("destinationCidr")
    @classmethod
    def validate_cidr(cls, v: Optional[str]) -> Optional[str]:
        """Validate and normalize CIDR format."""
        if v is None:
            return v
        try:
            network = ipaddress.ip_network(v, strict=False)
            if network.version != 4:
                raise ValueError("Only IPv4 CIDRs are supported")
            return str(network)
        except ValueError as e:
            raise ValueError(f"Invalid CIDR format: {v} ({e})")


class RouteResponse(BaseModel):
    """Response schema for a single route."""

    routeId: int
    peerId: int
    peerName: str
    destinationCidr: str
    createdAt: datetime
    updatedAt: datetime

    model_config = ConfigDict(from_attributes=True)


class RouteEnvelope(BaseModel):
    """Envelope response for a single route."""

    data: RouteResponse
    meta: dict[str, Any] = Field(default_factory=dict)


class RouteListEnvelope(BaseModel):
    """Envelope response for route list."""

    data: list[RouteResponse]
    meta: dict[str, Any] = Field(default_factory=dict)
