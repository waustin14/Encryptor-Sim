import base64
import sqlite3

from backend.app.db.base import Base
from backend.app.db.session import create_session_factory, get_engine
from backend.app.schemas.peer import PeerCreate
from backend.app.services.peer_service import create_peer
from backend.app.services.psk_crypto import parse_psk_key


def test_peer_psk_stored_encrypted_and_permissions(tmp_path) -> None:
    db_path = tmp_path / "peers.db"
    db_url = f"sqlite+pysqlite:///{db_path}"
    engine = get_engine(db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)

    session_factory = create_session_factory(db_url)
    session = session_factory()

    key = b"A" * 32
    key_b64 = base64.b64encode(key).decode("utf-8")
    parsed_key = parse_psk_key(key_b64)

    peer = create_peer(session, PeerCreate(name="peer-a", psk="secret-psk"), parsed_key)

    raw_conn = sqlite3.connect(db_path)
    cursor = raw_conn.execute(
        "SELECT pskEncrypted, pskNonce FROM peers WHERE peerId = ?",
        (peer.peerId,),
    )
    row = cursor.fetchone()
    raw_conn.close()

    assert row is not None
    encrypted, nonce = row
    assert encrypted != b"secret-psk"
    assert b"secret-psk" not in encrypted
    assert nonce != b""

    file_mode = db_path.stat().st_mode & 0o777
    assert file_mode == 0o600
