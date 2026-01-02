import base64
import os
import re
from dataclasses import dataclass

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from cryptography.hazmat.primitives import hashes, hmac
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .config import config

argon2_hasher = PasswordHasher(time_cost=2, memory_cost=32000, parallelism=1)
key = base64.b64decode(config.app_key)
enc = AESGCM(key)


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


@dataclass
class Encrypted:
    nonce: bytes
    cipher: bytes


def encrypt_data(plain: str | int | bytes) -> Encrypted:
    to_encrypt = (
        str(plain).encode()
        if isinstance(plain, int)
        else plain.encode()
        if isinstance(plain, str)
        else plain
    )
    nonce = os.urandom(12)
    return Encrypted(
        nonce, enc.encrypt(nonce=nonce, data=to_encrypt, associated_data=None)
    )


def decrypt_data(encrypted_data: Encrypted) -> bytes:
    return enc.decrypt(
        nonce=encrypted_data.nonce, data=encrypted_data.cipher, associated_data=None
    )


def verify_encrypted_data(plain: str | int | bytes, encrypted_data: Encrypted) -> bool:
    to_verity = (
        str(plain).encode()
        if isinstance(plain, int)
        else plain.encode()
        if isinstance(plain, str)
        else plain
    )
    decrypted = decrypt_data(encrypted_data)
    return decrypted == to_verity


def generate_hmac(data: str | bytes):
    data_bytes = data.encode() if isinstance(data, str) else data
    h = hmac.HMAC(key, hashes.SHA512())
    h.update(data_bytes)
    return h.finalize()
