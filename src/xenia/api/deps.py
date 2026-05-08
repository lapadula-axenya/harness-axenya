"""FastAPI dependency-injection helpers."""
from __future__ import annotations

import os
from collections.abc import AsyncIterator, Callable
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from xenia.agents.registry import AgentRegistry, get_registry
from xenia.config import Settings, get_settings
from xenia.security.jwt_auth import JWTError, Principal, decode_token
from xenia.skills.base import SkillRegistry, get_skill_registry
from xenia.storage.db import get_sessionmaker


async def get_db() -> AsyncIterator[AsyncSession]:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_settings_dep() -> Settings:
    return get_settings()


def get_agent_registry() -> AgentRegistry:
    return get_registry()


def get_skills() -> SkillRegistry:
    return get_skill_registry()


def get_webhook_secret(agent_secret_env: str) -> str | None:
    """Look up the webhook secret in the environment by env var name."""
    return os.environ.get(agent_secret_env)


def require_jwt(
    authorization: Annotated[str | None, Header()] = None,
    settings: Annotated[Settings, Depends(get_settings_dep)] = ...,  # type: ignore[assignment]
) -> Principal:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing bearer token",
        )
    token = authorization.split(" ", 1)[1].strip()
    try:
        return decode_token(
            token, secret=settings.jwt_secret, algorithm=settings.jwt_algorithm
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"invalid token: {exc}",
        ) from exc


def require_scope(scope: str) -> Callable[[Principal], Principal]:
    def _check(principal: Annotated[Principal, Depends(require_jwt)]) -> Principal:
        if not principal.has_scope(scope):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"missing scope: {scope}",
            )
        return principal

    return _check
