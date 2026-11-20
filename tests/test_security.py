import hashlib

from security import hash_password, needs_rehash, verify_password


def test_hash_and_verify():
    stored = hash_password("budget2025")
    assert stored.startswith("pbkdf2_sha256$")
    assert verify_password("budget2025", stored)
    assert not verify_password("wrong", stored)


def test_same_password_gets_different_salts():
    assert hash_password("budget2025") != hash_password("budget2025")


def test_legacy_sha256_hashes_still_work_and_need_upgrade():
    legacy = hashlib.sha256(b"budget2025").hexdigest()
    assert verify_password("budget2025", legacy)
    assert not verify_password("wrong", legacy)
    assert needs_rehash(legacy)
    assert not needs_rehash(hash_password("budget2025"))


def test_garbage_hash_is_rejected():
    assert not verify_password("x", "")
    assert not verify_password("x", "pbkdf2_sha256$notanumber$salt$hash")
