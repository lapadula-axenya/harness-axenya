"""JWT authentication for internal API endpoints."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import jwt
from pydantic import BaseModel, Field

PrincipalType = Literal["user", "service", "engineer"]


class JWTError(Exception):
    """Raised on token validation failure."""


class Principal(BaseModel):
    sub: str
    type: PrincipalType
    scopes: list[str] = Field(default_factory=list)

    def has_scope(self, scope: str) -> bool:
        return scope in self.scopes


def issue_token(
    *,
    sub: str,
    principal_type: PrincipalType,
    scopes: list[str],
    secret: str,
    algorithm: str = "HS256",
    ttl_seconds: int = 3600,
) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": sub,
        "type": principal_type,
        "scopes": scopes,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=ttl_seconds)).timestamp()),
    }
    return jwt.encode(payload, secret, algorithm=algorithm)


def decode_token(token: str, secret: str, algorithm: str = "HS256") -> Principal:
    try:
        payload = jwt.decode(token, secret, algorithms=[algorithm])
    except jwt.PyJWTError as exc:
        raise JWTError(str(exc)) from exc
    try:
        return Principal(
            sub=payload["sub"],
            type=payload["type"],
            scopes=list(payload.get("scopes", [])),
        )
    except (KeyError, ValueError) as exc:
        raise JWTError(f"malformed token: {exc}") from exc
