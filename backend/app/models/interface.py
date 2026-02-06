"""Interface model for network interface configuration.

Stores IP configuration for CT, PT, and MGMT interfaces.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from backend.app.db.base import Base


class Interface(Base):
    """Network interface configuration model."""

    __tablename__ = "interfaces"

    interfaceId: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    ipAddress: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    netmask: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    gateway: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    namespace: Mapped[str] = mapped_column(String(50), nullable=False)
    device: Mapped[str] = mapped_column(String(50), nullable=False)
    createdAt: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updatedAt: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<Interface(interfaceId={self.interfaceId}, name={self.name})>"
