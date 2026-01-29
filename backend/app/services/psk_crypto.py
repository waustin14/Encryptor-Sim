from __future__ import annotations

import base64
import binascii
import os
from functools import lru_cache

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from backend.app.config import get_settings

NONCE_SIZE = 12
KEY_SIZE = 32


def _looks_like_hex(value: str) -> bool:
    if len(value) % 2 != 0:
        return False
    return all(char in "0123456789abcdefABCDEF" for char in value)


def parse_psk_key(key_value: str) -> bytes:
    if _looks_like_hex(key_value):
        try:
            decoded = bytes.fromhex(key_value)
            if len(decoded) == KEY_SIZE:
                return decoded
        except ValueError:
            pass
    try:
        decoded = base64.b64decode(key_value, validate=True)
    except binascii.Error:
        decoded = bytes.fromhex(key_value)
    if len(decoded) != KEY_SIZE:
        raise ValueError("PSK encryption key must be 32 bytes after decoding")
    return decoded


@lru_cache(maxsize=1)
def get_psk_key() -> bytes:
    settings = get_settings()
    return parse_psk_key(settings.psk_encryption_key)


def encrypt_psk(psk: str, key: bytes) -> tuple[bytes, bytes]:
    nonce = os.urandom(NONCE_SIZE)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, psk.encode("utf-8"), None)
    return ciphertext, nonce


def decrypt_psk(ciphertext: bytes, nonce: bytes, key: bytes) -> str:
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return plaintext.decode("utf-8")
