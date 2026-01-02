from ..core.security import (
    Encrypted,
    decrypt_data,
    encrypt_data,
    generate_hmac,
    verify_encrypted_data,
)


def encrypt_nid(plain_nid: str | int | bytes):
    return encrypt_data(plain_nid)


def decrypt_nid(encrypted_nid: Encrypted) -> bytes:
    return decrypt_data(encrypted_nid)


def verify_nid(plain_nid: str | int | bytes, encrypted_nid: Encrypted) -> bool:
    return verify_encrypted_data(plain_nid, encrypted_nid)


def generate_nid_hmac(plain_nid: str | int | bytes) -> bytes:
    return generate_hmac(str(plain_nid) if isinstance(plain_nid, int) else plain_nid)
