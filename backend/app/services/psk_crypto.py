"""PSK encryption service using Fernet symmetric encryption.

Encrypts pre-shared keys before database storage and decrypts
them only when needed for daemon communication.
"""

import base64
import hashlib

from cryptography.fernet import Fernet

from backend.app.config import get_settings


def _get_fernet() -> Fernet:
    """Get Fernet instance using the configured encryption key.

    The PSK_ENCRYPTION_KEY from settings is hashed to produce
    a valid 32-byte Fernet key.
    """
    raw_key = get_settings().psk_encryption_key.encode("utf-8")
    # Derive a 32-byte key via SHA-256, then base64-encode for Fernet
    derived = hashlib.sha256(raw_key).digest()
    fernet_key = base64.urlsafe_b64encode(derived)
    return Fernet(fernet_key)


def encrypt_psk(plaintext: str) -> str:
    """Encrypt a PSK for database storage.

    Args:
        plaintext: The raw pre-shared key.

    Returns:
        Base64-encoded encrypted string.
    """
    f = _get_fernet()
    return f.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_psk(ciphertext: str) -> str:
    """Decrypt a PSK from database storage.

    Args:
        ciphertext: The encrypted PSK string from the database.

    Returns:
        The original plaintext PSK.
    """
    f = _get_fernet()
    return f.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
