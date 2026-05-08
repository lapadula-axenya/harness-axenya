"""Xenia Harness — minimal Streamlit dashboard.

Read-only consumer of the xenia-api HTTP API. Run with:

    uv sync --extra dashboard
    uv run streamlit run dashboard/app.py

Configuration is sidebar-driven: the API base URL defaults to
http://localhost:8080, and an engineer JWT is generated on-demand using the
JWT_SECRET from the local .env. In Phase 4 this page becomes part of the
real dashboard service with proper SSO; today it's a thin operator UI.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta

import httpx
import pandas as pd
import streamlit as st

# Ensure xenia.config picks up the same .env the API uses.
os.environ.setdefault("AGENTS_DIR", "agents")
from xenia.config import get_settings  # noqa: E402
from xenia.security.jwt_auth import issue_token  # noqa: E402

st.set_page_config(page_title="Xenia Harness", layout="wide")

DEFAULT_API_URL = os.environ.get("XENIA_API_URL", "http://localhost:8080")


def _engineer_token(secret: str) -> str:
    return issue_token(
        sub="dashboard",
        principal_type="engineer",
        scopes=[
            "runs:read",
            "runs:create",
            "runs:cancel",
            "agents:reload",
            "agents:write",
            "dashboard:read",
        ],
        secret=secret,
        ttl_seconds=3600,
    )


def _client(api_url: str, token: str) -> httpx.Client:
    return httpx.Client(
        base_url=api_url,
        headers={"Authorization": f"Bearer {token}"},
        timeout=10.0,
    )


# ── Sidebar ────────────────────────────────────────────────────────────────
st.sidebar.title("Xenia Harness")
api_url = st.sidebar.text_input("API URL", value=DEFAULT_API_URL)
settings = get_settings()
token = st.sidebar.text_area(
    "JWT (engineer)",
    value=_engineer_token(settings.jwt_secret),
    height=110,
    help="Auto-generated from JWT_SECRET. Replace with a real token in prod.",
)
page = st.sidebar.radio("Página", ["Resumo", "Agentes", "Runs"])

client = _client(api_url, token)


# ── Pages ──────────────────────────────────────────────────────────────────
def page_summary() -> None:
    st.header("Resumo (últimas 24h)")
    try:
        summary = client.get("/v1/dashboard/summary").json()
        per_agent = client.get("/v1/dashboard/agents").json()
    except httpx.HTTPError as exc:
        st.error(f"falha ao consultar API: {exc}")
        return

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Runs hoje", summary.get("runs_today", 0))
    col2.metric("Em execução", summary.get("runs_running", 0))
    col3.metric("Falhas (24h)", summary.get("runs_failed_24h", 0))
    col4.metric("Custo USD (hoje)", f"${summary.get('cost_usd_today', '0')}")

    failure_rate = float(summary.get("failure_rate_24h", 0)) * 100
    st.progress(min(failure_rate / 100, 1.0), text=f"Failure rate 24h: {failure_rate:.2f}%")

    if per_agent:
        st.subheader("Por agente (24h)")
        st.dataframe(pd.DataFrame(per_agent), hide_index=True, use_container_width=True)
    else:
        st.info("Nenhum run nas últimas 24h.")


def page_agents() -> None:
    st.header("Agentes")
    try:
        agents = client.get("/v1/agents").json()
    except httpx.HTTPError as exc:
        st.error(f"falha ao consultar API: {exc}")
        return

    if not agents:
        st.info("Nenhum agente registrado.")
        return

    for agent in agents:
        with st.expander(f"{agent['nome']} ({agent['id']})"):
            cols = st.columns([3, 1])
            cols[0].markdown(f"**Descrição:** {agent['descricao']}")
            cols[0].markdown(f"**Modelo:** `{agent['model']}`")
            cols[0].markdown(f"**Skills:** `{', '.join(agent['skills']) or '—'}`")
            status = "✅ Ativo" if agent["enabled"] else "⛔ Desativado"
            cols[1].markdown(f"**Status:** {status}")

            toggle_label = "Desativar" if agent["enabled"] else "Ativar"
            if cols[1].button(toggle_label, key=f"toggle-{agent['id']}"):
                resp = client.patch(
                    f"/v1/agents/{agent['id']}",
                    json={"enabled": not agent["enabled"]},
                )
                if resp.is_success:
                    st.rerun()
                else:
                    st.error(resp.text)


def page_runs() -> None:
    st.header("Runs")
    cols = st.columns(4)
    agent_filter = cols[0].text_input("agent_id", value="")
    status_filter = cols[1].multiselect(
        "status",
        ["queued", "running", "paused", "done", "failed", "cancelled"],
        default=[],
    )
    hours = cols[2].number_input("janela (horas)", min_value=1, max_value=168, value=24)
    limit = cols[3].number_input("limit", min_value=1, max_value=200, value=50)

    params: dict[str, object] = {
        "limit": int(limit),
        "since": (datetime.utcnow() - timedelta(hours=int(hours))).isoformat(),
    }
    if agent_filter.strip():
        params["agent_id"] = agent_filter.strip()
    if status_filter:
        params["status"] = status_filter

    try:
        runs = client.get("/v1/runs", params=params).json()
    except httpx.HTTPError as exc:
        st.error(f"falha ao consultar API: {exc}")
        return

    if not runs:
        st.info("Nenhum run no filtro.")
        return

    df = pd.DataFrame(
        [
            {
                "run_id": r["id"],
                "agent": r["agent_id"],
                "status": r["status"],
                "steps": r["steps_executed"],
                "tokens_in": r["tokens_input"],
                "tokens_out": r["tokens_output"],
                "triggered_by": r["triggered_by"],
                "created_at": r["created_at"],
            }
            for r in runs
        ]
    )
    st.dataframe(df, hide_index=True, use_container_width=True)

    selected = st.selectbox(
        "Detalhar run",
        options=[r["id"] for r in runs],
        format_func=lambda rid: f"{rid[:8]} — {next(r for r in runs if r['id'] == rid)['status']}",
    )
    if selected:
        run = next(r for r in runs if r["id"] == selected)
        st.subheader(f"Run {selected}")
        st.json(run)
        events = client.get(f"/v1/runs/{selected}/events").json()
        if events:
            st.subheader("Eventos")
            st.dataframe(pd.DataFrame(events), hide_index=True, use_container_width=True)


# ── Router ────────────────────────────────────────────────────────────────
if page == "Resumo":
    page_summary()
elif page == "Agentes":
    page_agents()
else:
    page_runs()
