"""Tests for app.core.security: passwords are hashed, never stored in clear."""

from app.core.security import hash_password, verify_password


def test_hash_password_never_returns_the_plaintext() -> None:
    plaintext = "correct horse battery staple"

    password_hash = hash_password(plaintext)

    assert password_hash != plaintext
    assert plaintext not in password_hash
    assert password_hash.startswith("$argon2")


def test_verify_password_accepts_the_right_password() -> None:
    password_hash = hash_password("s3cret-passphrase")

    assert verify_password("s3cret-passphrase", password_hash) is True


def test_verify_password_rejects_the_wrong_password() -> None:
    password_hash = hash_password("s3cret-passphrase")

    assert verify_password("not-the-password", password_hash) is False


def test_verify_password_is_case_sensitive() -> None:
    password_hash = hash_password("PassWord")

    assert verify_password("password", password_hash) is False


def test_hash_password_salts_each_hash() -> None:
    first = hash_password("same-password")
    second = hash_password("same-password")

    assert first != second
