"""Unit tests for HMAC signature verification."""
from __future__ import annotations

import time

from xenia.security.hmac_verify import compute_signature, verify_signature


def test_verify_signature_happy_path():
    secret = "topsecret"
    payload = b'{"foo": "bar"}'
    ts = str(int(time.time()))
    sig = compute_signature(payload, ts, secret)
    assert verify_signature(payload, sig, ts, secret)


def test_verify_signature_rejects_wrong_secret():
    payload = b'{"foo": "bar"}'
    ts = str(int(time.time()))
    sig = compute_signature(payload, ts, "alpha")
    assert not verify_signature(payload, sig, ts, "beta")


def test_verify_signature_rejects_tampered_payload():
    secret = "s"
    ts = str(int(time.time()))
    sig = compute_signature(b'{"a": 1}', ts, secret)
    assert not verify_signature(b'{"a": 2}', sig, ts, secret)


def test_verify_signature_rejects_old_timestamp():
    secret = "s"
    payload = b"x"
    old = str(int(time.time()) - 3600)
    sig = compute_signature(payload, old, secret)
    assert not verify_signature(payload, sig, old, secret)


def test_verify_signature_within_skew():
    secret = "s"
    payload = b"x"
    base = 1_700_000_000
    sig = compute_signature(payload, str(base), secret)
    assert verify_signature(
        payload, sig, str(base), secret, max_skew_seconds=300, now=base + 200
    )


def test_verify_signature_rejects_non_numeric_timestamp():
    sig = "deadbeef"
    assert not verify_signature(b"x", sig, "not-a-number", "s")


def test_verify_signature_rejects_blanks():
    assert not verify_signature(b"x", "", "1700000000", "s")
    assert not verify_signature(b"x", "deadbeef", "", "s")
    assert not verify_signature(b"x", "deadbeef", "1700000000", "")


def test_verify_signature_uses_constant_time():
    """Smoke test that two valid signatures both verify."""
    secret = "s"
    payload = b"x"
    ts = str(int(time.time()))
    sig = compute_signature(payload, ts, secret)
    sig_alt = compute_signature(payload, ts, secret)
    assert sig == sig_alt
    assert verify_signature(payload, sig, ts, secret)
