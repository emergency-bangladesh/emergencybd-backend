from datetime import datetime

from ..core.security import (
    Encrypted,
    decrypt_data,
    encrypt_data,
    verify_encrypted_data,
)


def encrypt_dob(plain_dob: datetime):
    return encrypt_data(plain_dob.isoformat())


def decrypt_dob(enc_dob: Encrypted) -> bytes:
    return decrypt_data(enc_dob)


def verify_dob(plain_dob: datetime, enc_dob: Encrypted) -> bool:
    return verify_encrypted_data(plain_dob.isoformat(), enc_dob)
