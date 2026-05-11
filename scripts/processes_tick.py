#!/usr/bin/env python3
"""Foreground scheduler loop — dispatches due processes.

Runs forever. Every ``poll_interval`` seconds it picks all active processes
whose ``next_run_at`` is in the past, dispatches them (target_kind-specific),
and updates ``last_run_at`` / ``next_run_at``.

Usage:
    uv run python scripts/processes_tick.py [--once] [--interval 30]

This is intentionally a script (not Celery beat) so dev can run it ad-hoc.
Cloud Run jobs / Celery beat picks this up in a later phase.
"""
from __future__ import annotations

import argparse
import asyncio
import logging
from datetime import UTC, datetime
from decimal import Decimal

from xenia.processes.repository import ProcessRepository
from xenia.storage.db import session_scope
from xenia.storage.models import (
    Process,
    ProcessLastStatus,
    ProcessTargetKind,
)

log = logging.getLogger("processes_tick")


async def _dispatch(p: Process) -> ProcessLastStatus:
    """Hand a due process off to the right runtime path.

    For now this is a stub that just logs. Wiring:
      * ``agent`` → POST internal run on agent registry id
      * ``mission`` → create / re-run a mission
      * ``worker`` → enqueue a Celery task on the worker queue

    Returns the outcome status. Stays optimistic until real adapters land.
    """
    log.info(
        "dispatching process",
        extra={
            "process_id": str(p.id),
            "target_kind": p.target_kind.value,
            "target_ref": p.target_ref,
        },
    )
    if p.target_kind == ProcessTargetKind.agent:
        # TODO: invoke executor.dispatch.get_dispatcher().dispatch_now(...)
        return ProcessLastStatus.ok
    if p.target_kind == ProcessTargetKind.mission:
        # TODO: missions.repository.create_run_from_template(...)
        return ProcessLastStatus.ok
    # worker
    return ProcessLastStatus.ok


async def tick_once() -> int:
    now = datetime.now(UTC)
    fired = 0
    async with session_scope() as session:
        repo = ProcessRepository(session)
        due = await repo.due(now=now)
        for p in due:
            status = await _dispatch(p)
            # Recompute success_rate_30d as a rolling proxy: weighted average.
            new_rate = p.success_rate_30d
            if status == ProcessLastStatus.ok and p.runs_30d:
                new_rate = (
                    p.success_rate_30d * p.runs_30d + Decimal("100")
                ) / (p.runs_30d + 1)
            elif status == ProcessLastStatus.failed and p.runs_30d:
                new_rate = (
                    p.success_rate_30d * p.runs_30d
                ) / (p.runs_30d + 1)
            await repo.record_run(
                p.id,
                last_run_id=None,
                last_run_status=status,
                ran_at=now,
                runs_30d_delta=1,
                success_rate_30d=new_rate.quantize(Decimal("0.01")),
            )
            fired += 1
    if fired:
        log.info("tick fired %d processes", fired)
    return fired


async def loop(interval: float) -> None:
    while True:
        try:
            await tick_once()
        except Exception:
            log.exception("tick failed")
        await asyncio.sleep(interval)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="run a single tick and exit")
    parser.add_argument("--interval", type=float, default=30.0, help="poll interval in seconds")
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    if args.once:
        fired = asyncio.run(tick_once())
        print(f"fired {fired} processes")
        return
    asyncio.run(loop(args.interval))


if __name__ == "__main__":
    main()
