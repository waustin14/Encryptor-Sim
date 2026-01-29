from sqlalchemy.orm import Session

from backend.app.models.peer import Peer
from backend.app.schemas.peer import PeerCreate, PeerRead
from backend.app.services.psk_crypto import decrypt_psk, encrypt_psk, get_psk_key


def create_peer(session: Session, peer_in: PeerCreate, key: bytes | None = None) -> Peer:
    resolved_key = key or get_psk_key()
    encrypted, nonce = encrypt_psk(peer_in.psk, resolved_key)
    peer = Peer(name=peer_in.name, pskEncrypted=encrypted, pskNonce=nonce)
    session.add(peer)
    session.commit()
    session.refresh(peer)
    return peer


def to_peer_read(peer: Peer) -> PeerRead:
    return PeerRead(peerId=peer.peerId, name=peer.name)


def reveal_psk(peer: Peer, key: bytes | None = None) -> str:
    resolved_key = key or get_psk_key()
    return decrypt_psk(peer.pskEncrypted, peer.pskNonce, resolved_key)
