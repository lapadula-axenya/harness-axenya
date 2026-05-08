#!/usr/bin/env python3
"""Seed the local Postgres with agent rows from the YAML registry.

Run after `alembic upgrade head` to populate the `agents` table so that the
foreign-key constraint from `runs` is satisfied.
"""
from __future__ import annotations

import asyncio

from xenia.agents.registry import get_registry
from xenia.storage.db import session_scope
from xenia.storage.repositories import AgentRepository


async def main() -> None:
    registry = get_registry()
    async with session_scope() as session:
        repo = AgentRepository(session)
        for definition in registry.list_all():
            await repo.upsert(
                agent_id=definition.id,
                nome=definition.nome,
                descricao=definition.descricao,
                yaml_hash=registry.yaml_hash(definition.id),
                yaml_content=registry.yaml_content(definition.id),
            )
            print(f"seeded agent {definition.id!r}")


if __name__ == "__main__":
    asyncio.run(main())
