"""Password hashing for Spendify.

Passwords are stored as salted PBKDF2-SHA256 hashes in the format
    pbkdf2_sha256$<iterations>$<salt>$<hash>

The first version of Spendify stored unsalted SHA-256 hashes. verify_password still accepts
those so older accounts can log in, and needs_rehash tells the caller to upgrade them.
"""

import hashlib
import hmac
import secrets

ALGORITHM = "pbkdf2_sha256"
ITERATIONS = 600_000


def hash_password(password, iterations=ITERATIONS):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), iterations).hex()
    return f"{ALGORITHM}${iterations}${salt}${digest}"


def _is_legacy(stored_hash):
    return "$" not in stored_hash


def verify_password(password, stored_hash):
    if not stored_hash:
        return False

    if _is_legacy(stored_hash):
        legacy = hashlib.sha256(password.encode()).hexdigest()
        return hmac.compare_digest(legacy, stored_hash)

    try:
        algorithm, iterations, salt, expected = stored_hash.split("$")
        iterations = int(iterations)
    except ValueError:
        return False
    if algorithm != ALGORITHM:
        return False

    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), iterations).hex()
    return hmac.compare_digest(digest, expected)


def needs_rehash(stored_hash):
    return _is_legacy(stored_hash) or not stored_hash.startswith(f"{ALGORITHM}${ITERATIONS}$")
