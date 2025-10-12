from dataclasses import dataclass

from ..core.security import decrypt, encrypt, generate_hmac, verify_encryption


@dataclass
class EncNID:
    nonce: bytes
    cipher: bytes


def encrypt_nid(plain_nid: str | int | bytes) -> EncNID:
    encrypted_nid = encrypt(plain_nid)
    return EncNID(nonce=encrypted_nid[0], cipher=encrypted_nid[1])


def decrypt_nid(enc_nid: EncNID) -> bytes:
    return decrypt(enc_nid.nonce, enc_nid.cipher)


def verify_nid(plain_nid: str | int | bytes, enc_nid: EncNID) -> bool:
    return verify_encryption(plain_nid, enc_nid.nonce, enc_nid.cipher)


def generate_nid_hmac(plain_nid: str | int | bytes) -> bytes:
    return generate_hmac(str(plain_nid) if isinstance(plain_nid, int) else plain_nid)
