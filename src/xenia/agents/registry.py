"""Agent registry — loads and validates YAML definitions from disk."""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from threading import RLock
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from xenia.agents.definition import AgentDefinition


class AgentNotFoundError(KeyError):
    """Raised when an unknown agent id is requested."""


class AgentValidationError(ValueError):
    """Raised when a YAML definition fails schema or Pydantic validation."""


class AgentRegistry:
    """In-memory cache of agent definitions, keyed by id.

    Thread-safe. Reload re-reads the directory; otherwise definitions are stable.
    Pass ttl_seconds=0 to disable auto-reload.
    """

    def __init__(self, agents_dir: Path, *, ttl_seconds: int = 300) -> None:
        self._agents_dir = agents_dir
        self._ttl_seconds = ttl_seconds
        self._lock = RLock()
        self._agents: dict[str, AgentDefinition] = {}
        self._yaml_content: dict[str, str] = {}
        self._yaml_hash: dict[str, str] = {}
        self._loaded_at: float = 0.0
        self._schema_validator: Draft202012Validator | None = None

    def _get_validator(self) -> Draft202012Validator:
        if self._schema_validator is None:
            schema_path = self._agents_dir / "_schema.json"
            with schema_path.open() as fp:
                schema = json.load(fp)
            self._schema_validator = Draft202012Validator(schema)
        return self._schema_validator

    def load(self) -> None:
        """Reload all YAML definitions from disk."""
        with self._lock:
            self._agents.clear()
            self._yaml_content.clear()
            self._yaml_hash.clear()
            validator = self._get_validator()

            for path in sorted(self._agents_dir.glob("*.yaml")):
                if path.name == "_schema.json" or path.name.startswith("_"):
                    continue
                self._load_one(path, validator)

            self._loaded_at = time.time()

    def _load_one(self, path: Path, validator: Draft202012Validator) -> None:
        raw = path.read_text(encoding="utf-8")
        try:
            data: dict[str, Any] = yaml.safe_load(raw)
        except yaml.YAMLError as exc:
            raise AgentValidationError(f"{path.name}: invalid YAML — {exc}") from exc

        errors = sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path))
        if errors:
            messages = "; ".join(
                f"{'/'.join(str(p) for p in err.absolute_path) or '<root>'}: {err.message}"
                for err in errors
            )
            raise AgentValidationError(f"{path.name}: schema errors — {messages}")

        try:
            definition = AgentDefinition.model_validate(data)
        except Exception as exc:
            raise AgentValidationError(f"{path.name}: {exc}") from exc

        if definition.id in self._agents:
            raise AgentValidationError(
                f"{path.name}: duplicate agent id {definition.id!r}"
            )

        self._agents[definition.id] = definition
        self._yaml_content[definition.id] = raw
        self._yaml_hash[definition.id] = hashlib.sha256(raw.encode()).hexdigest()

    def _maybe_reload(self) -> None:
        if self._ttl_seconds <= 0:
            return
        if time.time() - self._loaded_at > self._ttl_seconds:
            self.load()

    def get(self, agent_id: str) -> AgentDefinition:
        with self._lock:
            self._maybe_reload()
            try:
                return self._agents[agent_id]
            except KeyError as exc:
                raise AgentNotFoundError(agent_id) from exc

    def list_all(self) -> list[AgentDefinition]:
        with self._lock:
            self._maybe_reload()
            return list(self._agents.values())

    def yaml_content(self, agent_id: str) -> str:
        with self._lock:
            return self._yaml_content[agent_id]

    def yaml_hash(self, agent_id: str) -> str:
        with self._lock:
            return self._yaml_hash[agent_id]


_global_registry: AgentRegistry | None = None


def get_registry(agents_dir: Path | None = None) -> AgentRegistry:
    """Return the global registry. First call performs initial load."""
    global _global_registry
    if _global_registry is None:
        from xenia.config import get_settings

        directory = agents_dir or get_settings().agents_dir
        registry = AgentRegistry(directory)
        registry.load()
        _global_registry = registry
    return _global_registry


def reset_registry() -> None:
    """Test helper — drop the global registry."""
    global _global_registry
    _global_registry = None
