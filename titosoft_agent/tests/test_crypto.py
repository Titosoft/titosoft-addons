import pytest

from titosoft_agent.crypto import decrypt_backup, encrypt_backup


def test_roundtrip():
    original = b"conteudo do backup do home assistant" * 100
    encrypted, provider = encrypt_backup(original, "minha-passphrase")
    assert provider == "aes-256-gcm"
    assert encrypted != original
    assert encrypted.startswith(b"TSBK0001")
    assert decrypt_backup(encrypted, "minha-passphrase") == original


def test_wrong_passphrase_fails():
    encrypted, _ = encrypt_backup(b"dados", "certa")
    with pytest.raises(Exception):
        decrypt_backup(encrypted, "errada")


def test_no_passphrase_is_noop():
    content = b"dados"
    payload, provider = encrypt_backup(content, None)
    assert provider == "noop"
    assert payload == content


def test_decrypt_rejects_plain_file():
    with pytest.raises(ValueError):
        decrypt_backup(b"nao criptografado", "x")
