from pydantic import BaseModel, Field


class PeerCreate(BaseModel):
    name: str = Field(min_length=1)
    psk: str = Field(min_length=1)


class PeerRead(BaseModel):
    peerId: int
    name: str
