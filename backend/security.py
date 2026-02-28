from __future__ import annotations

import base64
import hashlib
import hmac
import os

PBKDF2_ITERATIONS = 200_000


def hash_password(password: str, salt_b64: str | None = None) -> tuple[str, str]:
    salt = os.urandom(16) if not salt_b64 else base64.b64decode(salt_b64.encode("ascii"))
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return hashed.hex(), base64.b64encode(salt).decode("ascii")


def verify_password(password: str, stored_hash: str, stored_salt: str) -> bool:
    if not stored_hash or not stored_salt:
        return False
    candidate_hash, _ = hash_password(password, stored_salt)
    return hmac.compare_digest(candidate_hash, stored_hash)
