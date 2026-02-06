import base64
import hashlib
from cryptography.fernet import Fernet


def _derive_key(master_key: str) -> bytes:
    digest = hashlib.sha256(master_key.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def encrypt_value(value: str, master_key: str) -> str:
    fernet = Fernet(_derive_key(master_key))
    return fernet.encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_value(value: str, master_key: str) -> str:
    fernet = Fernet(_derive_key(master_key))
    return fernet.decrypt(value.encode("utf-8")).decode("utf-8")
