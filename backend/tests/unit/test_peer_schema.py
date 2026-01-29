from backend.app.schemas.peer import PeerRead


def test_peer_read_schema_excludes_psk() -> None:
    peer = PeerRead(peerId=1, name="peer-1")

    data = peer.model_dump()

    assert "psk" not in data
