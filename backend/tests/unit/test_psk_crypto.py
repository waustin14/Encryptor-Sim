"""Unit tests for PSK encryption service (Story 4.2, Task 2)."""

import os

import pytest

os.environ.setdefault("APP_PSK_ENCRYPTION_KEY", "test-key-for-testing-32bytes1")
os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-for-jwt-testing")

from backend.app.services.psk_crypto import decrypt_psk, encrypt_psk


class TestPSKCrypto:
    """Test PSK encryption and decryption."""

    def test_encrypt_decrypt_roundtrip(self) -> None:
        """Verify PSK can be encrypted and decrypted."""
        original_psk = "my-super-secret-psk-12345"

        encrypted = encrypt_psk(original_psk)
        decrypted = decrypt_psk(encrypted)

        assert decrypted == original_psk
        assert encrypted != original_psk
        assert len(encrypted) > len(original_psk)

    def test_encrypted_psk_is_different_each_time(self) -> None:
        """Verify encryption produces different ciphertext each time (Fernet uses random IV)."""
        psk = "test-psk"

        encrypted1 = encrypt_psk(psk)
        encrypted2 = encrypt_psk(psk)

        # Fernet uses random IV, so ciphertext differs
        assert encrypted1 != encrypted2
        # But both decrypt to same plaintext
        assert decrypt_psk(encrypted1) == psk
        assert decrypt_psk(encrypted2) == psk

    def test_encrypt_empty_psk_roundtrip(self) -> None:
        """Verify empty string can be encrypted and decrypted."""
        psk = ""
        encrypted = encrypt_psk(psk)
        assert decrypt_psk(encrypted) == psk

    def test_encrypt_long_psk_roundtrip(self) -> None:
        """Verify long PSK can be encrypted and decrypted."""
        psk = "a" * 256
        encrypted = encrypt_psk(psk)
        assert decrypt_psk(encrypted) == psk

    def test_encrypt_special_chars_roundtrip(self) -> None:
        """Verify PSK with special characters roundtrips correctly."""
        psk = "p@$$w0rd!#%^&*()_+-=[]{}|;':\",./<>?"
        encrypted = encrypt_psk(psk)
        assert decrypt_psk(encrypted) == psk

    def test_encrypted_output_is_string(self) -> None:
        """Verify encrypt_psk returns a string (suitable for database storage)."""
        result = encrypt_psk("test")
        assert isinstance(result, str)

    def test_decrypt_invalid_ciphertext_raises(self) -> None:
        """Verify decrypting invalid data raises an error."""
        with pytest.raises(Exception):
            decrypt_psk("not-valid-encrypted-data")

    def test_encrypt_unicode_psk_roundtrip(self) -> None:
        """Verify PSK with unicode characters roundtrips correctly."""
        psk = "test-key-\u2603-\u00e9\u00e8"
        encrypted = encrypt_psk(psk)
        assert decrypt_psk(encrypted) == psk
