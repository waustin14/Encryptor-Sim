"""JWT token utilities for authentication.

Provides JWT access and refresh token generation and validation
using HS256 algorithm.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt

from backend.app.config import get_settings

_settings = get_settings()
SECRET_KEY = _settings.secret_key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # 1 hour (NFR18)
REFRESH_TOKEN_EXPIRE_DAYS = 7  # 7 days (NFR18)


def create_access_token(user_id: int) -> str:
    """Generate JWT access token.

    Args:
        user_id: The user ID to encode in the token.

    Returns:
        Encoded JWT access token string.
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id: int) -> str:
    """Generate JWT refresh token.

    Args:
        user_id: The user ID to encode in the token.

    Returns:
        Encoded JWT refresh token string.
    """
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh",
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str, expected_type: str = "access") -> Optional[int]:
    """Verify JWT token and return user_id.

    Args:
        token: The JWT token to verify.
        expected_type: Expected token type ("access" or "refresh").

    Returns:
        User ID if token is valid, None otherwise.
    """
    if not token:
        return None

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        token_type = payload.get("type")
        if token_type != expected_type:
            return None
        user_id = int(payload.get("sub"))
        return user_id
    except (jwt.InvalidTokenError, ValueError, TypeError):
        return None
