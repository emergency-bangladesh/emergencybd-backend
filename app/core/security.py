import base64
import os
import re

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from cryptography.hazmat.primitives import hashes, hmac
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .config import config

argon2_hasher = PasswordHasher(time_cost=2, memory_cost=32000, parallelism=1)
key = base64.b64decode(config.app_key)
acgm = AESGCM(key)


def hash_password(plain_password: str) -> str:
    return argon2_hasher.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return argon2_hasher.verify(hashed_password, plain_password)
    except VerifyMismatchError:
        return False


def validate_password(password: str):
    if len(password) < config.password_min_len:
        raise ValueError("Password must be at least 8 characters long")
    if not re.search(r"[a-z]", password):
        raise ValueError("Password must contain at least one lowercase letter")
    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r"[0-9]", password):
        raise ValueError("Password must contain at least one digit")
    if not re.search(r"[!@#$%^&*()]", password):
        raise ValueError("Password must contain at least one special character")
    return password


def encrypt(plain: str | int | bytes) -> tuple[bytes, bytes]:
    nid_bytes = (
        str(plain).encode()
        if isinstance(plain, int)
        else plain.encode()
        if isinstance(plain, str)
        else plain
    )
    nonce = os.urandom(12)
    return nonce, acgm.encrypt(nonce=nonce, data=nid_bytes, associated_data=None)


def decrypt(nonce: bytes, cipher: bytes) -> bytes:
    return acgm.decrypt(nonce=nonce, data=cipher, associated_data=None)


def verify_encryption(plain: str | int | bytes, nonce: bytes, cipher: bytes) -> bool:
    nid_bytes = (
        str(plain).encode()
        if isinstance(plain, int)
        else plain.encode()
        if isinstance(plain, str)
        else plain
    )
    try:
        decrypted = decrypt(nonce, cipher)
        return decrypted == nid_bytes
    except Exception:
        return False


def generate_hmac(data: str | bytes):
    nid_bytes = data.encode() if isinstance(data, str) else data
    h = hmac.HMAC(key, hashes.SHA256())
    h.update(nid_bytes)
    return h.finalize()
