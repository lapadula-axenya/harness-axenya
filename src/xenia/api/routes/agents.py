"""Agent registry HTTP API."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from xenia.agents.registry import AgentNotFoundError, AgentRegistry
from xenia.api.deps import get_agent_registry, require_scope
from xenia.api.schemas import AgentDetail, AgentSummary, AgentToggleRequest

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_model=list[AgentSummary])
async def list_agents(
    registry: Annotated[AgentRegistry, Depends(get_agent_registry)],
) -> list[AgentSummary]:
    return [
        AgentSummary(
            id=a.id,
            nome=a.nome,
            descricao=a.descricao,
            enabled=a.enabled,
            skills=list(a.skills),
            model=a.llm.model,
        )
        for a in registry.list_all()
    ]


@router.get("/{agent_id}", response_model=AgentDetail)
async def get_agent(
    agent_id: str,
    registry: Annotated[AgentRegistry, Depends(get_agent_registry)],
) -> AgentDetail:
    try:
        a = registry.get(agent_id)
    except AgentNotFoundError:
        raise HTTPException(status_code=404, detail=f"agent {agent_id!r} not found") from None
    return AgentDetail(
        id=a.id,
        nome=a.nome,
        descricao=a.descricao,
        enabled=a.enabled,
        skills=list(a.skills),
        model=a.llm.model,
        yaml_hash=registry.yaml_hash(agent_id),
        system_prompt=a.system_prompt,
        input_schema=a.input_schema,
    )


@router.post(
    "/reload",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_scope("agents:reload"))],
)
async def reload_agents(
    registry: Annotated[AgentRegistry, Depends(get_agent_registry)],
) -> None:
    registry.load()
    return None


@router.patch(
    "/{agent_id}",
    response_model=AgentSummary,
    dependencies=[Depends(require_scope("agents:write"))],
)
async def patch_agent(
    agent_id: str,
    body: AgentToggleRequest,
    registry: Annotated[AgentRegistry, Depends(get_agent_registry)],
) -> AgentSummary:
    try:
        a = registry.get(agent_id)
    except AgentNotFoundError:
        raise HTTPException(status_code=404, detail=f"agent {agent_id!r} not found") from None
    a.enabled = body.enabled
    return AgentSummary(
        id=a.id,
        nome=a.nome,
        descricao=a.descricao,
        enabled=a.enabled,
        skills=list(a.skills),
        model=a.llm.model,
    )
