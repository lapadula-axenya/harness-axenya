"""Unit tests for JWT issuing/decoding."""
from __future__ import annotations

import time

import jwt
import pytest

from xenia.security.jwt_auth import JWTError, decode_token, issue_token


def test_issue_and_decode_round_trip():
    token = issue_token(
        sub="alice",
        principal_type="engineer",
        scopes=["runs:read", "runs:cancel"],
        secret="topsecret",
    )
    principal = decode_token(token, secret="topsecret")
    assert principal.sub == "alice"
    assert principal.type == "engineer"
    assert principal.has_scope("runs:read")
    assert not principal.has_scope("agents:reload")


def test_decode_rejects_wrong_secret():
    token = issue_token(
        sub="alice", principal_type="user", scopes=[], secret="alpha"
    )
    with pytest.raises(JWTError):
        decode_token(token, secret="beta")


def test_decode_rejects_expired_token():
    payload = {
        "sub": "x",
        "type": "user",
        "scopes": [],
        "iat": int(time.time()) - 7200,
        "exp": int(time.time()) - 3600,
    }
    token = jwt.encode(payload, "s", algorithm="HS256")
    with pytest.raises(JWTError):
        decode_token(token, secret="s")


def test_decode_rejects_malformed_payload():
    token = jwt.encode({"foo": "bar"}, "s", algorithm="HS256")
    with pytest.raises(JWTError):
        decode_token(token, secret="s")
