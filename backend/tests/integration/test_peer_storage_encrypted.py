"""Integration test for PSK encryption at rest (Story 4.2, AC: #4).

Verifies PSK is encrypted in the database and not stored as plaintext.
"""

import os
import sqlite3

os.environ.setdefault("APP_PSK_ENCRYPTION_KEY", "test-key-for-testing-32bytes1")
os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-for-jwt-testing")

from backend.app.db.base import Base
from backend.app.db.session import create_session_factory, get_engine
from backend.app.services.ipsec_peer_service import create_peer, get_decrypted_psk
from backend.app.services.psk_crypto import decrypt_psk


def test_peer_psk_stored_encrypted_and_permissions(tmp_path) -> None:
    """Verify PSK is encrypted in database and DB file has 600 permissions."""
    db_path = tmp_path / "peers.db"
    db_url = f"sqlite+pysqlite:///{db_path}"
    engine = get_engine(db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)

    session_factory = create_session_factory(db_url)
    session = session_factory()

    plaintext_psk = "secret-psk-value"
    peer = create_peer(
        session,
        name="peer-encrypted",
        remote_ip="10.1.1.1",
        psk_plaintext=plaintext_psk,
        ike_version="ikev2",
    )

    # Query database directly to verify encryption
    raw_conn = sqlite3.connect(db_path)
    cursor = raw_conn.execute(
        "SELECT psk FROM peers WHERE \"peerId\" = ?",
        (peer.peerId,),
    )
    row = cursor.fetchone()
    raw_conn.close()

    assert row is not None
    stored_psk = row[0]

    # Verify stored PSK is NOT plaintext
    assert stored_psk != plaintext_psk
    assert len(stored_psk) > len(plaintext_psk)

    # Verify stored PSK can be decrypted back to original
    assert decrypt_psk(stored_psk) == plaintext_psk

    # Verify get_decrypted_psk service function works
    assert get_decrypted_psk(peer) == plaintext_psk

    # Verify DB file permissions
    file_mode = db_path.stat().st_mode & 0o777
    assert file_mode == 0o600
