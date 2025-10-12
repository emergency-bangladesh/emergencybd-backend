from dataclasses import dataclass

from ..core.security import decrypt, encrypt, generate_hmac, verify_encryption


@dataclass
class EncBRN:
    nonce: bytes
    cipher: bytes


def encrypt_brn(plain_brn: str | int | bytes) -> EncBRN:
    encrypted_brn = encrypt(plain_brn)
    return EncBRN(nonce=encrypted_brn[0], cipher=encrypted_brn[1])


def decrypt_brn(enc_brn: EncBRN) -> bytes:
    return decrypt(enc_brn.nonce, enc_brn.cipher)


def verify_brn(plain_brn: str | int | bytes, enc_brn: EncBRN) -> bool:
    return verify_encryption(plain_brn, enc_brn.nonce, enc_brn.cipher)


def generate_brn_hmac(plain_brn: str | int | bytes) -> bytes:
    return generate_hmac(str(plain_brn) if isinstance(plain_brn, int) else plain_brn)
