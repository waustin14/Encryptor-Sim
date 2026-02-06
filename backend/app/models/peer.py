"""IPsec peer model for tunnel configuration.

Stores peer configuration including encrypted PSK, IKE version,
DPD parameters, and rekeying settings.
"""

import ipaddress
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from backend.app.db.base import Base


class Peer(Base):
    """IPsec peer configuration model."""

    __tablename__ = "peers"

    peerId: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    remoteIp: Mapped[str] = mapped_column(String(45), nullable=False)
    psk: Mapped[str] = mapped_column(String(500), nullable=False)
    ikeVersion: Mapped[str] = mapped_column(String(10), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # DPD (Dead Peer Detection) parameters
    dpdAction: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, default="restart"
    )
    dpdDelay: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, default=30
    )
    dpdTimeout: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, default=150
    )

    # Rekeying parameters
    rekeyTime: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, default=3600
    )

    createdAt: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updatedAt: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    routes = relationship("Route", back_populates="peer", cascade="all, delete-orphan")

    @property
    def operationalStatus(self) -> str:
        """Compute peer operational status based on required field validation.

        Returns:
            "ready" if all required fields are valid.
            "incomplete" if any required field is missing or invalid.

        Note: Validation-only; does not check daemon connectivity.
        """
        if not self.name or not self.name.strip():
            return "incomplete"

        if not self.remoteIp or not self.remoteIp.strip():
            return "incomplete"

        if not self.psk:
            return "incomplete"

        if not self.ikeVersion:
            return "incomplete"

        # Validate remoteIp is a valid IP address
        try:
            ipaddress.ip_address(self.remoteIp.strip())
        except (ValueError, AttributeError):
            return "incomplete"

        # Validate ikeVersion is ikev1 or ikev2
        if self.ikeVersion.lower() not in ("ikev1", "ikev2"):
            return "incomplete"

        return "ready"

    def __repr__(self) -> str:
        return f"<Peer(peerId={self.peerId}, name={self.name})>"
