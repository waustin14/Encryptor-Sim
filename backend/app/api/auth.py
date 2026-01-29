"""Authentication API endpoints.

Provides login and logout functionality using JWT tokens.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.auth.deps import get_current_user
from backend.app.auth.jwt import create_access_token, create_refresh_token
from backend.app.auth.password import (
    hash_password,
    validate_password_complexity,
    validate_password_not_reused,
    verify_password,
)
from backend.app.db.deps import get_db_session
from backend.app.models.user import User
from backend.app.schemas.auth import (
    ChangePasswordData,
    ChangePasswordRequest,
    ChangePasswordResponse,
    LoginRequest,
    MeResponse,
    TokenData,
    TokenResponse,
    UserResponse,
)
from typing import Any

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _authenticate_user(username: str, password: str, db: Session) -> User | None:
    """Internal helper for user authentication.

    Args:
        username: The username to authenticate.
        password: The password to verify.
        db: Database session.

    Returns:
        User object if credentials valid, None otherwise.
    """
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.passwordHash):
        return None
    return user


@router.post("/login", response_model=TokenResponse)
def login(
    credentials: LoginRequest,
    db: Session = Depends(get_db_session),
) -> TokenResponse:
    """Authenticate user and return JWT tokens.

    Args:
        credentials: Login credentials (username and password).
        db: Database session.

    Returns:
        TokenResponse with access and refresh tokens.

    Raises:
        HTTPException: 401 if credentials are invalid.
    """
    user = _authenticate_user(credentials.username, credentials.password, db)

    if not user:
        raise HTTPException(
            status_code=401,
            detail={
                "type": "about:blank",
                "title": "Authentication Failed",
                "status": 401,
                "detail": "Invalid username or password",
            },
        )

    # Update last login timestamp
    user.lastLogin = datetime.now(timezone.utc)
    db.commit()

    # Generate tokens
    access_token = create_access_token(user.userId)
    refresh_token = create_refresh_token(user.userId)

    return TokenResponse(
        data=TokenData(
            accessToken=access_token,
            refreshToken=refresh_token,
            tokenType="bearer",
        ),
        meta={"timestamp": datetime.now(timezone.utc).isoformat()},
    )


@router.post("/logout")
def logout(
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Logout current user (client-side token invalidation).

    Note: For V1.0, logout is handled client-side by clearing tokens.
    Server-side token blacklist can be added in future releases.

    Args:
        current_user: The authenticated user from JWT token.

    Returns:
        Success response with message.
    """
    return {
        "data": {"message": "Logged out successfully"},
        "meta": {"timestamp": datetime.now(timezone.utc).isoformat()},
    }


@router.post("/change-password", response_model=ChangePasswordResponse)
def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> ChangePasswordResponse:
    """Change user password.

    Requires valid access token, current password verification,
    and new password complexity validation.

    Args:
        request: Password change request with current and new passwords.
        current_user: The authenticated user from JWT token.
        db: Database session.

    Returns:
        ChangePasswordResponse confirming password change.

    Raises:
        HTTPException: 401 if current password is wrong.
        HTTPException: 422 if new password fails validation.
    """
    # Verify current password
    if not verify_password(request.currentPassword, current_user.passwordHash):
        raise HTTPException(
            status_code=401,
            detail={
                "type": "about:blank",
                "title": "Authentication Failed",
                "status": 401,
                "detail": "Current password is incorrect",
            },
        )

    # Validate new password complexity
    is_valid, error_msg = validate_password_complexity(request.newPassword)
    if not is_valid:
        raise HTTPException(
            status_code=422,
            detail={
                "type": "about:blank",
                "title": "Validation Error",
                "status": 422,
                "detail": error_msg,
            },
        )

    # Ensure new password is different from current
    is_different, error_msg = validate_password_not_reused(
        request.newPassword, current_user.passwordHash
    )
    if not is_different:
        raise HTTPException(
            status_code=422,
            detail={
                "type": "about:blank",
                "title": "Validation Error",
                "status": 422,
                "detail": error_msg,
            },
        )

    # Hash new password and update user
    current_user.passwordHash = hash_password(request.newPassword)
    current_user.requirePasswordChange = False
    db.commit()

    return ChangePasswordResponse(
        data=ChangePasswordData(
            message="Password changed successfully",
            requirePasswordChange=False,
        ),
        meta={"timestamp": datetime.now(timezone.utc).isoformat()},
    )


@router.get("/me", response_model=MeResponse)
def get_current_user_profile(
    current_user: User = Depends(get_current_user),
) -> MeResponse:
    """Get current authenticated user profile.

    Args:
        current_user: The authenticated user from JWT token.

    Returns:
        MeResponse with user profile data.
    """
    user_data = UserResponse(
        userId=current_user.userId,
        username=current_user.username,
        requirePasswordChange=current_user.requirePasswordChange,
        createdAt=current_user.createdAt,
        lastLogin=current_user.lastLogin,
    )
    return MeResponse(
        data=user_data,
        meta={"timestamp": datetime.now(timezone.utc).isoformat()},
    )
