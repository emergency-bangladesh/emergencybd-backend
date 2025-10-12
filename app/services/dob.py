from dataclasses import dataclass
from datetime import datetime

from ..core.security import decrypt, encrypt, generate_hmac, verify_encryption


@dataclass
class EncDOB:
    nonce: bytes
    cipher: bytes


def encrypt_dob(plain_dob: datetime) -> EncDOB:
    encrypted_dob = encrypt(plain_dob.isoformat())
    return EncDOB(nonce=encrypted_dob[0], cipher=encrypted_dob[1])


def decrypt_dob(enc_dob: EncDOB) -> bytes:
    return decrypt(enc_dob.nonce, enc_dob.cipher)


def verify_dob(plain_dob: datetime, enc_dob: EncDOB) -> bool:
    return verify_encryption(plain_dob.isoformat(), enc_dob.nonce, enc_dob.cipher)


def generate_dob_hmac(plain_dob: datetime) -> bytes:
    return generate_hmac(plain_dob.isoformat())
