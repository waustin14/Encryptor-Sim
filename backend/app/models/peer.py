from sqlalchemy import LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


class Peer(Base):
    __tablename__ = "peers"

    peerId: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    pskEncrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    pskNonce: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
