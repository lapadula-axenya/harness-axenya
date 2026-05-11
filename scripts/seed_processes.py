#!/usr/bin/env python3
"""Seed the local Postgres with the 8 example scheduled processes.

These mirror the rows shown in the Processos screen, plus realistic stats:
schedule, owner, success_rate_30d, runs_30d, last/next run times.

Run after ``alembic upgrade head``.
"""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import delete

from xenia.processes.scheduler import cron_describe
from xenia.storage.db import session_scope
from xenia.storage.models import (
    Process,
    ProcessLastStatus,
    ProcessStatus,
    ProcessTargetKind,
)

NOW = datetime.now(UTC)


def _hours_ago(n: int) -> datetime:
    return NOW - timedelta(hours=n)


def _days_ago(n: int) -> datetime:
    return NOW - timedelta(days=n)


def _hours_from_now(n: int) -> datetime:
    return NOW + timedelta(hours=n)


def _days_from_now(n: int) -> datetime:
    return NOW + timedelta(days=n)


SEED: list[dict] = [
    {
        "name": "Triagem matinal do inbox da Dra. Aline",
        "description": (
            "A cada 2 horas, das 8h às 18h em dias úteis, lê novos emails da "
            "caixa da Aline, classifica e cria missions de follow-up quando "
            "encontra solicitação clínica priorizada."
        ),
        "cron_expression": "0 8-18/2 * * 1-5",
        "schedule_human": "A cada 2h, 8h-18h, seg-sex",
        "target_kind": ProcessTargetKind.agent,
        "target_ref": "triagem_email_aline@v0.3.1",
        "target_label": "triagem_email_aline@v0.3.1",
        "owner_name": "Dra. Aline",
        "owner_initials": "AL",
        "status": ProcessStatus.active,
        "last_run_at": _hours_ago(9),
        "last_run_status": ProcessLastStatus.ok,
        "next_run_at": _hours_from_now(7),
        "runs_30d": 312,
        "success_rate_30d": Decimal("97.3"),
    },
    {
        "name": "Weekly report de sinistralidade",
        "description": (
            "Toda sexta-feira às 9h, gera PDF de sinistralidade por empresa "
            "cliente e envia DM no Slack para os Customer Success."
        ),
        "cron_expression": "0 9 * * 5",
        "schedule_human": "Sexta-feira às 9h",
        "target_kind": ProcessTargetKind.mission,
        "target_ref": "m_003",
        "target_label": "m_003 · weekly report",
        "owner_name": "Bia Costa",
        "owner_initials": "BC",
        "status": ProcessStatus.active,
        "last_run_at": _days_ago(3),
        "last_run_status": ProcessLastStatus.ok,
        "next_run_at": _days_from_now(4),
        "runs_30d": 4,
        "success_rate_30d": Decimal("100.0"),
    },
    {
        "name": "Sweep noturno de drift detection",
        "description": (
            "Às 2h da manhã, roda eval suites em sample de produção dos "
            "últimos 24h. Drift > 2σ cria mission de regressão automática."
        ),
        "cron_expression": "0 2 * * *",
        "schedule_human": "Diariamente às 2h",
        "target_kind": ProcessTargetKind.worker,
        "target_ref": "drift.sweep",
        "target_label": "todos os agentes ativos",
        "owner_name": "Sofia Lapadula",
        "owner_initials": "SL",
        "status": ProcessStatus.active,
        "last_run_at": _hours_ago(16),
        "last_run_status": ProcessLastStatus.partial,
        "next_run_at": _hours_from_now(8),
        "runs_30d": 30,
        "success_rate_30d": Decimal("90.0"),
    },
    {
        "name": "Sync de leads do HubSpot",
        "description": (
            "A cada 15 minutos, busca leads criados no HubSpot que ainda "
            "não foram processados pelo agente de triagem e enfileira run."
        ),
        "cron_expression": "*/15 * * * *",
        "schedule_human": "A cada 15min",
        "target_kind": ProcessTargetKind.agent,
        "target_ref": "triagem_lead@v1.4.2",
        "target_label": "triagem_lead@v1.4.2",
        "owner_name": "Bia Costa",
        "owner_initials": "BC",
        "status": ProcessStatus.active,
        "last_run_at": _hours_ago(8),
        "last_run_status": ProcessLastStatus.ok,
        "next_run_at": _hours_from_now(8),
        "runs_30d": 2880,
        "success_rate_30d": Decimal("99.1"),
    },
    {
        "name": "Backup de audit log para BigQuery",
        "description": (
            "Diariamente às 3h, exporta entradas de policy_decisions com mais "
            "de 90 dias para dataset frio no BigQuery, comprimindo histórico."
        ),
        "cron_expression": "0 3 * * *",
        "schedule_human": "Diariamente às 3h",
        "target_kind": ProcessTargetKind.worker,
        "target_ref": "bq.archive",
        "target_label": "bq.archive (worker)",
        "owner_name": "Estevão Lima",
        "owner_initials": "EL",
        "status": ProcessStatus.active,
        "last_run_at": _hours_ago(15),
        "last_run_status": ProcessLastStatus.ok,
        "next_run_at": _hours_from_now(9),
        "runs_30d": 30,
        "success_rate_30d": Decimal("100.0"),
    },
    {
        "name": "Lembrete de aprovações com SLA estourando",
        "description": (
            "A cada 4 horas, identifica aprovações que estão há mais de 75% "
            "do SLA e pinga o approver no Slack com link direto para o card."
        ),
        "cron_expression": "0 */4 * * *",
        "schedule_human": "A cada 4h",
        "target_kind": ProcessTargetKind.worker,
        "target_ref": "slack.dm",
        "target_label": "slack.dm",
        "owner_name": "Sofia Lapadula",
        "owner_initials": "SL",
        "status": ProcessStatus.active,
        "last_run_at": _hours_ago(10),
        "last_run_status": ProcessLastStatus.ok,
        "next_run_at": _hours_from_now(2),
        "runs_30d": 180,
        "success_rate_30d": Decimal("99.4"),
    },
    {
        "name": "Aderência de planos — mensal",
        "description": (
            "Todo dia 1 às 9h, identifica beneficiários sem check-up no mês "
            "anterior e dispara mission de outreach por canal preferido."
        ),
        "cron_expression": "0 9 1 * *",
        "schedule_human": "Dia 1 do mês, 9h",
        "target_kind": ProcessTargetKind.agent,
        "target_ref": "aderencia_planos@v0.1.0",
        "target_label": "aderencia_planos@v0.1.0",
        "owner_name": "Dra. Aline",
        "owner_initials": "AL",
        "status": ProcessStatus.active,
        "last_run_at": _days_ago(10),
        "last_run_status": ProcessLastStatus.ok,
        "next_run_at": _days_from_now(20),
        "runs_30d": 1,
        "success_rate_30d": Decimal("100.0"),
    },
    {
        "name": "Drenagem da fila de reembolso",
        "description": (
            "A cada 30 minutos em horário comercial, busca pedidos de "
            "reembolso pendentes no Ksenia e dispara processamento."
        ),
        "cron_expression": "*/30 9-18 * * 1-5",
        "schedule_human": "A cada 30min, 9h-18h, seg-sex",
        "target_kind": ProcessTargetKind.mission,
        "target_ref": "m_004",
        "target_label": "m_004 · reembolso",
        "owner_name": "Sofia Lapadula",
        "owner_initials": "SL",
        "status": ProcessStatus.paused,
        "last_run_at": _days_ago(2),
        "last_run_status": ProcessLastStatus.ok,
        "next_run_at": None,
        "runs_30d": 86,
        "success_rate_30d": Decimal("95.4"),
    },
]


async def main() -> None:
    async with session_scope() as session:
        await session.execute(delete(Process))
        for row in SEED:
            schedule_human = row.get("schedule_human") or cron_describe(
                row["cron_expression"]
            )
            p = Process(
                name=row["name"],
                description=row["description"],
                cron_expression=row["cron_expression"],
                schedule_human=schedule_human,
                target_kind=row["target_kind"],
                target_ref=row["target_ref"],
                target_label=row["target_label"],
                payload={},
                owner_name=row["owner_name"],
                owner_initials=row["owner_initials"],
                status=row["status"],
                last_run_at=row["last_run_at"],
                last_run_status=row["last_run_status"],
                next_run_at=row["next_run_at"],
                runs_30d=row["runs_30d"],
                success_rate_30d=row["success_rate_30d"],
            )
            session.add(p)
            print(f"seeded process {row['name']!r}")


if __name__ == "__main__":
    asyncio.run(main())
