"""Criptografia de backup no agente (antes do upload).

AES-256-GCM com chave derivada de BACKUP_ENCRYPTION_KEY (passphrase).
Formato do arquivo: magic(8) + salt(16) + nonce(12) + ciphertext.
Sem chave configurada -> passthrough ("noop"), registrado no backend.

Descriptografar (restore): scripts/decrypt-backup.py
"""
import hashlib
import os
from typing import Optional, Tuple

MAGIC = b"TSBK0001"
SALT_SIZE = 16
NONCE_SIZE = 12
PBKDF2_ITERATIONS = 600_000


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", passphrase.encode("utf-8"), salt, PBKDF2_ITERATIONS, dklen=32)


def encrypt_backup(content: bytes, passphrase: Optional[str]) -> Tuple[bytes, str]:
    """Retorna (payload, provider_name). Sem passphrase -> passthrough."""
    if not passphrase:
        return content, "noop"
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    salt = os.urandom(SALT_SIZE)
    nonce = os.urandom(NONCE_SIZE)
    key = _derive_key(passphrase, salt)
    ciphertext = AESGCM(key).encrypt(nonce, content, MAGIC)
    return MAGIC + salt + nonce + ciphertext, "aes-256-gcm"


def decrypt_backup(payload: bytes, passphrase: str) -> bytes:
    if not payload.startswith(MAGIC):
        raise ValueError("Arquivo não está no formato TitoSoft (TSBK0001) — provavelmente não criptografado")
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    offset = len(MAGIC)
    salt = payload[offset : offset + SALT_SIZE]
    nonce = payload[offset + SALT_SIZE : offset + SALT_SIZE + NONCE_SIZE]
    ciphertext = payload[offset + SALT_SIZE + NONCE_SIZE :]
    key = _derive_key(passphrase, salt)
    return AESGCM(key).decrypt(nonce, ciphertext, MAGIC)
