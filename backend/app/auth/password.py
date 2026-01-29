"""Password hashing utilities using argon2id.

Provides secure password hashing and verification using the Argon2id
algorithm, which is memory-hard and side-channel resistant.
"""

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

# Use library defaults (secure parameters)
ph = PasswordHasher()


def hash_password(password: str) -> str:
    """Hash password using argon2id.

    Args:
        password: Plaintext password to hash.

    Returns:
        Argon2id hash string.
    """
    return ph.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify password against argon2id hash.

    Args:
        password: Plaintext password to verify.
        password_hash: Argon2id hash to verify against.

    Returns:
        True if password matches, False otherwise.
    """
    try:
        ph.verify(password_hash, password)
        return True
    except VerifyMismatchError:
        return False


def needs_rehash(password_hash: str) -> bool:
    """Check if password hash needs rehashing (algorithm updated).

    Args:
        password_hash: Argon2id hash to check.

    Returns:
        True if hash should be rehashed with current parameters.
    """
    return ph.check_needs_rehash(password_hash)
