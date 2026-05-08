"""Unit tests for the YAML agent registry."""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from xenia.agents.registry import AgentNotFoundError, AgentRegistry, AgentValidationError


@pytest.fixture
def tmp_agents_dir(tmp_path: Path, agents_dir: Path) -> Path:
    target = tmp_path / "agents"
    target.mkdir()
    shutil.copy(agents_dir / "_schema.json", target / "_schema.json")
    return target


def _write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def _valid_yaml(agent_id: str = "demo") -> str:
    return f"""
id: {agent_id}
nome: Demo
descricao: An agent
webhook_secret_env: WEBHOOK_SECRET_DEMO
input_schema:
  type: object
  required: [foo]
  properties:
    foo:
      type: string
llm:
  provider: anthropic
  model: claude-sonnet-4-6
  max_tokens: 256
  temperature: 0.0
skills: []
system_prompt: |
  hello
"""


def test_load_valid_yaml(tmp_agents_dir: Path):
    _write(tmp_agents_dir / "demo.yaml", _valid_yaml())
    registry = AgentRegistry(tmp_agents_dir, ttl_seconds=0)
    registry.load()
    agent = registry.get("demo")
    assert agent.id == "demo"
    assert agent.nome == "Demo"
    assert agent.llm.model == "claude-sonnet-4-6"


def test_get_unknown_agent_raises(tmp_agents_dir: Path):
    registry = AgentRegistry(tmp_agents_dir, ttl_seconds=0)
    registry.load()
    with pytest.raises(AgentNotFoundError):
        registry.get("ghost")


def test_invalid_id_rejected(tmp_agents_dir: Path):
    yaml_content = _valid_yaml().replace("id: demo", "id: NotSnakeCase")
    _write(tmp_agents_dir / "demo.yaml", yaml_content)
    registry = AgentRegistry(tmp_agents_dir, ttl_seconds=0)
    with pytest.raises(AgentValidationError):
        registry.load()


def test_missing_required_field_rejected(tmp_agents_dir: Path):
    bad = _valid_yaml().replace("nome: Demo", "")
    _write(tmp_agents_dir / "demo.yaml", bad)
    registry = AgentRegistry(tmp_agents_dir, ttl_seconds=0)
    with pytest.raises(AgentValidationError):
        registry.load()


def test_input_schema_must_be_object(tmp_agents_dir: Path):
    bad = _valid_yaml().replace("type: object", "type: array")
    _write(tmp_agents_dir / "demo.yaml", bad)
    registry = AgentRegistry(tmp_agents_dir, ttl_seconds=0)
    with pytest.raises(AgentValidationError):
        registry.load()


def test_extra_fields_rejected(tmp_agents_dir: Path):
    bad = _valid_yaml() + "\nbogus: 42\n"
    _write(tmp_agents_dir / "demo.yaml", bad)
    registry = AgentRegistry(tmp_agents_dir, ttl_seconds=0)
    with pytest.raises(AgentValidationError):
        registry.load()


def test_yaml_hash_stable(tmp_agents_dir: Path):
    _write(tmp_agents_dir / "demo.yaml", _valid_yaml())
    registry = AgentRegistry(tmp_agents_dir, ttl_seconds=0)
    registry.load()
    h1 = registry.yaml_hash("demo")
    registry.load()
    h2 = registry.yaml_hash("demo")
    assert h1 == h2 and len(h1) == 64


def test_list_all_returns_loaded_agents(tmp_agents_dir: Path):
    _write(tmp_agents_dir / "a.yaml", _valid_yaml("alpha"))
    _write(tmp_agents_dir / "b.yaml", _valid_yaml("beta"))
    registry = AgentRegistry(tmp_agents_dir, ttl_seconds=0)
    registry.load()
    ids = sorted(a.id for a in registry.list_all())
    assert ids == ["alpha", "beta"]


def test_real_agent_yamls_load(agents_dir: Path):
    """Sanity check: the bundled agents/*.yaml are valid."""
    registry = AgentRegistry(agents_dir, ttl_seconds=0)
    registry.load()
    ids = sorted(a.id for a in registry.list_all())
    assert "exemplo_eco" in ids
    assert "triagem_lead" in ids
