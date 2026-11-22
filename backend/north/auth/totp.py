"""Time-based one-time passwords (RFC 6238: SHA-1, 6 digits, 30 s), as authenticator apps use.

Small enough to keep in-house; the QR code is drawn by segno (no network, no JavaScript).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time
import urllib.parse

import segno

STEP = 30
DIGITS = 6
# Accept the previous and the next step too (clock drift of the phone).
WINDOW = 1


def new_secret() -> str:
    """160 random bits in base32 without padding (the RFC 4226 recommended length)."""
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")


def _key(secret: str) -> bytes:
    s = secret.strip().replace(" ", "").upper()
    return base64.b32decode(s + "=" * (-len(s) % 8))


def code_at(secret: str, step: int) -> str:
    digest = hmac.new(_key(secret), struct.pack(">Q", step), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    number = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(number % 10**DIGITS).zfill(DIGITS)


def current_step(now: float | None = None) -> int:
    return int((time.time() if now is None else now) // STEP)


def verify(secret: str, code: str, *, last_step: int | None = None,
           now: float | None = None) -> int | None:
    """The matching time step, or None. A step at or before last_step is refused (replay)."""
    code = code.strip().replace(" ", "")
    if len(code) != DIGITS or not code.isdigit():
        return None
    here = current_step(now)
    for step in range(here - WINDOW, here + WINDOW + 1):
        if last_step is not None and step <= last_step:
            continue
        if hmac.compare_digest(code_at(secret, step), code):
            return step
    return None


def provisioning_uri(secret: str, username: str, issuer: str) -> str:
    label = urllib.parse.quote(f"{issuer}:{username}")
    query = urllib.parse.urlencode({"secret": secret, "issuer": issuer, "algorithm": "SHA1",
                                    "digits": DIGITS, "period": STEP})
    return f"otpauth://totp/{label}?{query}"


def qr_svg_data_uri(uri: str) -> str:
    """The provisioning URI as an SVG data: URI (the CSP allows img-src data:)."""
    return segno.make(uri, error="m").svg_data_uri(scale=5, border=2)
