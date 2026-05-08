"""Skill ABC and registry.

A Skill is an atomic operation the agent can call as a tool. Skills register
themselves via `@register_skill` and are exposed to the LLM through
`SkillRegistry.tools_for()` which produces Anthropic tool-use schemas.
"""
from __future__ import annotations

import abc
from threading import RLock
from typing import Any

from pydantic import BaseModel


class SkillResult(BaseModel):
    ok: bool
    data: dict[str, Any] | None = None
    error: str | None = None
    error_code: str | None = None


class Skill(abc.ABC):
    name: str
    description: str
    input_schema: dict[str, Any]
    timeout_seconds: int = 30
    idempotent: bool = False

    @abc.abstractmethod
    async def execute(self, **kwargs: Any) -> SkillResult: ...

    def to_tool_schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }


class SkillRegistry:
    def __init__(self) -> None:
        self._lock = RLock()
        self._skills: dict[str, Skill] = {}

    def register(self, skill: Skill) -> Skill:
        with self._lock:
            if skill.name in self._skills:
                raise ValueError(f"skill already registered: {skill.name}")
            self._skills[skill.name] = skill
        return skill

    def get(self, name: str) -> Skill:
        with self._lock:
            try:
                return self._skills[name]
            except KeyError as exc:
                raise KeyError(f"unknown skill: {name}") from exc

    def has(self, name: str) -> bool:
        with self._lock:
            return name in self._skills

    def names(self) -> list[str]:
        with self._lock:
            return sorted(self._skills.keys())

    def tools_for(self, names: list[str]) -> list[dict[str, Any]]:
        return [self.get(n).to_tool_schema() for n in names]

    def clear(self) -> None:
        with self._lock:
            self._skills.clear()


_global_registry: SkillRegistry | None = None


def get_skill_registry() -> SkillRegistry:
    global _global_registry
    if _global_registry is None:
        _global_registry = SkillRegistry()
        _register_builtins(_global_registry)
    return _global_registry


def reset_skill_registry() -> None:
    global _global_registry
    _global_registry = None


def _register_builtins(registry: SkillRegistry) -> None:
    """Import-time registration of all built-in skills.

    Imported lazily to avoid a circular import (skills depend on this module).
    """
    from xenia.skills import bigquery, hubspot, slack

    for skill in (
        *hubspot.all_skills(),
        *slack.all_skills(),
        *bigquery.all_skills(),
    ):
        registry.register(skill)
