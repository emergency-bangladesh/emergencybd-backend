from ..core.security import (
    Encrypted,
    decrypt_data,
    encrypt_data,
    generate_hmac,
    verify_encrypted_data,
)


def encrypt_brn(plain_brn: str | int | bytes):
    return encrypt_data(plain_brn)


def decrypt_brn(enc_brn: Encrypted) -> bytes:
    return decrypt_data(enc_brn)


def verify_brn(plain_brn: str | int | bytes, enc_brn: Encrypted) -> bool:
    return verify_encrypted_data(plain_brn, enc_brn)


def generate_brn_hmac(plain_brn: str | int | bytes) -> bytes:
    return generate_hmac(str(plain_brn) if isinstance(plain_brn, int) else plain_brn)
