from datetime import datetime

from sqlalchemy import DateTime, Float, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


class IsolationValidationResult(Base):
    __tablename__ = "isolationValidationResults"

    isolationValidationResultId: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    checks: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False)
    failures: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    durationSeconds: Mapped[float] = mapped_column(Float, nullable=False)
