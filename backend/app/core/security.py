"""Password hashing: Argon2 only, never plaintext.

Passwords are hashed with Argon2 (a fresh random salt each time) and only the
hash is ever stored. Plaintext is never logged, returned or persisted.
"""

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_HASHER = PasswordHasher()


def hash_password(password: str) -> str:
    """Return an Argon2 hash for ``password``; each call uses a fresh salt."""
    return _HASHER.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Return True when ``password`` matches ``password_hash``, otherwise False.

    A malformed ``password_hash`` raises instead of returning False, so corrupt
    data fails loudly rather than silently rejecting a valid password.
    """
    try:
        _HASHER.verify(password_hash, password)
    except VerifyMismatchError:
        return False
    return True
