"""Authentication schemas for request/response validation.

Defines Pydantic models for login requests and token responses.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    """Login credentials request."""

    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1, max_length=72)  # Max 72 to prevent argon2 DoS


class TokenData(BaseModel):
    """JWT tokens data."""

    accessToken: str = Field(..., description="Short-lived access token (1 hour)")
    refreshToken: str = Field(..., description="Long-lived refresh token (7 days)")
    tokenType: str = Field(default="bearer", description="Token type")


class TokenResponse(BaseModel):
    """JWT tokens response with envelope."""

    data: TokenData
    meta: dict[str, Any] = Field(default_factory=dict)


class UserResponse(BaseModel):
    """User information (never includes password)."""

    userId: int
    username: str
    requirePasswordChange: bool
    createdAt: datetime
    lastLogin: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class UserData(BaseModel):
    """User data for response envelope."""

    user: UserResponse


class MeResponse(BaseModel):
    """Current user response with envelope."""

    data: UserResponse
    meta: dict[str, Any] = Field(default_factory=dict)


class RefreshTokenRequest(BaseModel):
    """Refresh token request for obtaining a new access token."""

    refreshToken: str = Field(..., min_length=1)


class RefreshTokenData(BaseModel):
    """New access token data returned from refresh."""

    accessToken: str = Field(..., description="New short-lived access token (1 hour)")


class RefreshTokenResponse(BaseModel):
    """Refresh token response with envelope."""

    data: RefreshTokenData
    meta: dict[str, Any] = Field(default_factory=dict)


class ChangePasswordRequest(BaseModel):
    """Password change request."""

    currentPassword: str = Field(..., min_length=1, max_length=72)
    newPassword: str = Field(..., min_length=1, max_length=72)


class ChangePasswordData(BaseModel):
    """Password change success data."""

    message: str
    requirePasswordChange: bool


class ChangePasswordResponse(BaseModel):
    """Password change response with envelope."""

    data: ChangePasswordData
    meta: dict[str, Any] = Field(default_factory=dict)
