"""HMAC SHA-256 webhook signature verification with timestamp skew protection."""
from __future__ import annotations

import hashlib
import hmac
import time


class SignatureError(Exception):
    """Raised when a webhook signature fails verification."""


def compute_signature(payload: bytes, timestamp: str, secret: str) -> str:
    """Compute hex SHA-256 HMAC over `{timestamp}.{payload}`."""
    signed = timestamp.encode() + b"." + payload
    return hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()


def verify_signature(
    payload: bytes,
    signature: str,
    timestamp: str,
    secret: str,
    *,
    max_skew_seconds: int = 300,
    now: float | None = None,
) -> bool:
    """Verify HMAC signature.

    Returns True only if:
      - timestamp parses as int and is within max_skew_seconds of `now`
      - HMAC signature matches (constant-time compare)
    """
    if not signature or not timestamp or not secret:
        return False
    try:
        ts = int(timestamp)
    except ValueError:
        return False

    current = time.time() if now is None else now
    if abs(current - ts) > max_skew_seconds:
        return False

    expected = compute_signature(payload, timestamp, secret)
    return hmac.compare_digest(expected, signature)
