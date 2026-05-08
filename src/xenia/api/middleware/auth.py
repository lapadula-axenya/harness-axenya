"""Auth helpers — JWT logic lives in `xenia.security.jwt_auth`.

This module exists for the import path called out in the spec; there's no
extra middleware to add in Phase 1 because per-route deps cover JWT enforcement.
"""
from __future__ import annotations

from xenia.security.jwt_auth import JWTError, Principal, decode_token, issue_token

__all__ = ["JWTError", "Principal", "decode_token", "issue_token"]
