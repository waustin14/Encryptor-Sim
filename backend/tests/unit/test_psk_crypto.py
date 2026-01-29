import base64

import pytest

from backend.app import config as config_module
from backend.app.services.psk_crypto import (
    decrypt_psk,
    encrypt_psk,
    get_psk_key,
    parse_psk_key,
)


def test_parse_psk_key_rejects_invalid() -> None:
    with pytest.raises(ValueError):
        parse_psk_key("deadbeef")


def test_parse_psk_key_prefers_hex_over_base64_when_ambiguous() -> None:
    key = bytes(range(32))
    hex_key = key.hex()

    assert parse_psk_key(hex_key) == key


def test_encrypt_decrypt_round_trip() -> None:
    key = b"k" * 32
    key_b64 = base64.b64encode(key).decode("utf-8")
    parsed_key = parse_psk_key(key_b64)

    ciphertext, nonce = encrypt_psk("super-secret", parsed_key)
    plaintext = decrypt_psk(ciphertext, nonce, parsed_key)

    assert plaintext == "super-secret"


def test_get_psk_key_reads_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    key = b"s" * 32
    monkeypatch.setenv("APP_PSK_ENCRYPTION_KEY", base64.b64encode(key).decode("utf-8"))
    config_module.get_settings.cache_clear()

    assert get_psk_key() == key
