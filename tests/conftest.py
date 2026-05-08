"""Shared pytest fixtures."""
from __future__ import annotations

import asyncio
import os
import socket
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio

# Ensure dev defaults are set BEFORE importing settings.
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://xenia:xenia@localhost:5432/xenia"
)
os.environ.setdefault(
    "DATABASE_URL_SYNC", "postgresql+psycopg://xenia:xenia@localhost:5432/xenia"
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("AGENTS_DIR", str(Path(__file__).resolve().parent.parent / "agents"))
os.environ.setdefault("WEBHOOK_SECRET_EXEMPLO_ECO", "test-secret")
os.environ.setdefault("WEBHOOK_SECRET_TRIAGEM_LEAD", "test-secret")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret")


def _postgres_reachable(host: str = "localhost", port: int = 5432) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


POSTGRES_AVAILABLE = _postgres_reachable()


def pytest_collection_modifyitems(config, items):  # type: ignore[no-untyped-def]
    if POSTGRES_AVAILABLE:
        return
    skip = pytest.mark.skip(reason="postgres not reachable on localhost:5432")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(scope="session")
def event_loop():  # type: ignore[no-untyped-def]
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator:
    """Async session bound to a transaction that is rolled back at fixture teardown."""
    if not POSTGRES_AVAILABLE:
        pytest.skip("postgres not reachable")

    from xenia.storage.db import get_engine, reset_engine

    engine = get_engine()
    # Tests assume `alembic upgrade head` was run before pytest.
    from sqlalchemy.ext.asyncio import async_sessionmaker

    sm = async_sessionmaker(engine, expire_on_commit=False)
    async with sm() as session:
        yield session
        await session.rollback()
    await reset_engine()


@pytest.fixture
def agents_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "agents"


@pytest.fixture(autouse=True)
def reset_global_registries():
    from xenia.agents.registry import reset_registry
    from xenia.skills.base import reset_skill_registry

    reset_registry()
    reset_skill_registry()
    yield
    reset_registry()
    reset_skill_registry()
