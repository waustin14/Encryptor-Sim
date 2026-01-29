"""Unit tests for password hashing utilities.

Tests argon2id password hashing and verification.
"""

import pytest


class TestPasswordHashing:
    """Tests for password hashing functions."""

    def test_hash_password_returns_argon2id_hash(self):
        """Test password hashing produces argon2id hash."""
        from backend.app.auth.password import hash_password

        hashed = hash_password("admin")
        assert hashed.startswith("$argon2id$")

    def test_hash_password_different_for_same_input(self):
        """Test that hashing same password produces different hashes (salted)."""
        from backend.app.auth.password import hash_password

        hash1 = hash_password("admin")
        hash2 = hash_password("admin")
        assert hash1 != hash2

    def test_verify_password_correct(self):
        """Test password verification succeeds with correct password."""
        from backend.app.auth.password import hash_password, verify_password

        hashed = hash_password("admin")
        assert verify_password("admin", hashed) is True

    def test_verify_password_incorrect(self):
        """Test password verification fails with incorrect password."""
        from backend.app.auth.password import hash_password, verify_password

        hashed = hash_password("admin")
        assert verify_password("wrong", hashed) is False

    def test_verify_password_empty_password(self):
        """Test password verification fails with empty password."""
        from backend.app.auth.password import hash_password, verify_password

        hashed = hash_password("admin")
        assert verify_password("", hashed) is False

    def test_needs_rehash_returns_boolean(self):
        """Test needs_rehash returns a boolean."""
        from backend.app.auth.password import hash_password, needs_rehash

        hashed = hash_password("admin")
        result = needs_rehash(hashed)
        assert isinstance(result, bool)
