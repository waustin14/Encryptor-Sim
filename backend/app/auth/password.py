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


def validate_password_complexity(password: str) -> tuple[bool, str]:
    """Validate password meets complexity requirements.

    Requirements (NFR16/NFR-S6):
    - Minimum 8 characters

    Args:
        password: Plaintext password to validate.

    Returns:
        Tuple of (is_valid, error_message). Empty string if valid.
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters"

    return True, ""


def validate_password_not_reused(
    new_password: str, current_hash: str
) -> tuple[bool, str]:
    """Check if new password is different from current password.

    Args:
        new_password: Plaintext new password.
        current_hash: argon2id hash of current password.

    Returns:
        Tuple of (is_valid, error_message). Empty string if valid.
    """
    if verify_password(new_password, current_hash):
        return False, "New password must be different from current password"

    return True, ""


def needs_rehash(password_hash: str) -> bool:
    """Check if password hash needs rehashing (algorithm updated).

    Args:
        password_hash: Argon2id hash to check.

    Returns:
        True if hash should be rehashed with current parameters.
    """
    return ph.check_needs_rehash(password_hash)
