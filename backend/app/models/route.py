"""Route model for IPsec traffic selectors.

Stores route configurations (destination CIDRs) associated with peers.
Routes define which traffic is directed through IPsec tunnels.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from backend.app.db.base import Base


class Route(Base):
    """IPsec route configuration model."""

    __tablename__ = "routes"

    routeId: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    peerId: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("peers.peerId", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    destinationCidr: Mapped[str] = mapped_column(String(18), nullable=False)
    createdAt: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updatedAt: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationship
    peer = relationship("Peer", back_populates="routes")

    def __repr__(self) -> str:
        return f"<Route(routeId={self.routeId}, peerId={self.peerId}, destinationCidr={self.destinationCidr})>"
