"""Password hashing with Argon2id (OWASP recommendation) and the password policy."""

from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

# argon2-cffi defaults: Argon2id, time cost 3, 64 MiB, parallelism 4 (RFC 9106 second choice).
_hasher = PasswordHasher()

MIN_LENGTH = 12
MAX_LENGTH = 256  # bounds the hashing cost of a hostile request

# Verified against when the username does not exist, so both paths take the same time.
_DUMMY_HASH = _hasher.hash("north-dummy-password-for-timing")


class WeakPassword(ValueError):
    pass


def check_policy(password: str, *, username: str = "") -> None:
    """Length is what matters (NIST SP 800-63B): 12 to 256 characters, not the username."""
    if len(password) < MIN_LENGTH:
        raise WeakPassword(f"at least {MIN_LENGTH} characters")
    if len(password) > MAX_LENGTH:
        raise WeakPassword(f"at most {MAX_LENGTH} characters")
    if username and username.lower() in password.lower():
        raise WeakPassword("must not contain the username")
    if len(set(password)) < 5:
        raise WeakPassword("too few distinct characters")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(stored_hash: str | None, password: str) -> tuple[bool, bool]:
    """(matches, needs_rehash). A missing hash is checked against a dummy to keep timing flat."""
    if len(password) > MAX_LENGTH:
        return False, False
    try:
        _hasher.verify(stored_hash or _DUMMY_HASH, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False, False
    if stored_hash is None:
        return False, False
    return True, _hasher.check_needs_rehash(stored_hash)
