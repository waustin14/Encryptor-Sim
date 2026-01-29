"""Authentication dependencies for FastAPI.

Provides dependencies for protecting routes with JWT authentication.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from backend.app.auth.jwt import verify_token
from backend.app.db.deps import get_db_session
from backend.app.models.user import User

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db_session),
) -> User:
    """Validate JWT token and return current user.

    Args:
        credentials: HTTP Bearer token from Authorization header.
        db: Database session.

    Returns:
        User object for the authenticated user.

    Raises:
        HTTPException: 401 if token is invalid or user not found.
    """
    token = credentials.credentials
    user_id = verify_token(token, expected_type="access")

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "type": "about:blank",
                "title": "Invalid Token",
                "status": 401,
                "detail": "Could not validate credentials",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.userId == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "type": "about:blank",
                "title": "User Not Found",
                "status": 401,
                "detail": "User no longer exists",
            },
        )

    return user


def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        HTTPBearer(auto_error=False)
    ),
    db: Session = Depends(get_db_session),
) -> User | None:
    """Return user if token valid, None otherwise.

    Args:
        credentials: HTTP Bearer token from Authorization header (optional).
        db: Database session.

    Returns:
        User object if authenticated, None otherwise.
    """
    if credentials is None:
        return None

    token = credentials.credentials
    user_id = verify_token(token, expected_type="access")

    if user_id is None:
        return None

    user = db.query(User).filter(User.userId == user_id).first()
    return user
