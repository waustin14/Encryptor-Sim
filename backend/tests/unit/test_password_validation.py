"""Unit tests for password complexity validation.

Tests password validation rules (minimum length, reuse detection).
"""

import pytest

from backend.app.auth.password import (
    hash_password,
    validate_password_complexity,
    validate_password_not_reused,
)


class TestPasswordComplexity:
    """Tests for password complexity validation."""

    def test_valid_password_passes(self):
        """Test valid password passes complexity check."""
        is_valid, msg = validate_password_complexity("admin123")
        assert is_valid is True
        assert msg == ""

    def test_password_too_short_fails(self):
        """Test password under 8 characters fails."""
        is_valid, msg = validate_password_complexity("admin")
        assert is_valid is False
        assert "at least 8 characters" in msg

    def test_password_exactly_8_chars_passes(self):
        """Test password with exactly 8 characters passes."""
        is_valid, msg = validate_password_complexity("12345678")
        assert is_valid is True
        assert msg == ""

    def test_password_7_chars_fails(self):
        """Test password with 7 characters fails."""
        is_valid, msg = validate_password_complexity("1234567")
        assert is_valid is False

    def test_empty_password_fails(self):
        """Test empty password fails."""
        is_valid, msg = validate_password_complexity("")
        assert is_valid is False
        assert "at least 8 characters" in msg

    def test_long_password_passes(self):
        """Test long password passes."""
        is_valid, msg = validate_password_complexity("a" * 72)
        assert is_valid is True
        assert msg == ""


class TestPasswordNotReused:
    """Tests for password reuse detection."""

    def test_different_password_passes(self):
        """Test new password different from current passes."""
        current_hash = hash_password("oldpass123")
        is_valid, msg = validate_password_not_reused("newpass456", current_hash)
        assert is_valid is True
        assert msg == ""

    def test_same_password_fails(self):
        """Test reusing same password fails."""
        current_hash = hash_password("samepass123")
        is_valid, msg = validate_password_not_reused("samepass123", current_hash)
        assert is_valid is False
        assert "different from current" in msg
