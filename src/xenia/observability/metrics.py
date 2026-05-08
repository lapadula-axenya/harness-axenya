"""Metrics — in-memory counters + optional Cloud Monitoring shipping.

Phase 1 used in-memory counters only. Phase 4 adds a `CloudMonitoringSink`
that flushes counter increments to GCP custom metrics under the
`xenia/...` namespace. The sink is opt-in (`GCP_PROJECT_ID` set), so dev
and tests stay zero-dependency.

Counters defined here mirror SPEC.md § Observability:

  * xenia/runs/created
  * xenia/runs/duration_seconds
  * xenia/runs/cost_usd
  * xenia/runs/tokens
  * xenia/skills/calls
  * xenia/queue/depth
  * xenia/webhook/auth_failures
"""
from __future__ import annotations

import logging
import os
import threading
from collections import defaultdict
from typing import Any

logger = logging.getLogger(__name__)


class Counter:
    def __init__(self, name: str) -> None:
        self.name = name
        self._lock = threading.Lock()
        self._values: dict[tuple[str, ...], int] = defaultdict(int)
        self._sink: MetricSink | None = None

    def attach(self, sink: MetricSink) -> None:
        self._sink = sink

    def inc(self, *labels: str, by: int = 1) -> None:
        with self._lock:
            self._values[labels] += by
        if self._sink is not None:
            self._sink.publish(self.name, labels, by)

    def value(self, *labels: str) -> int:
        with self._lock:
            return self._values[labels]

    def snapshot(self) -> dict[tuple[str, ...], int]:
        with self._lock:
            return dict(self._values)


class MetricSink:
    """Backend that receives counter increments."""

    def publish(
        self, metric_name: str, labels: tuple[str, ...], value: int
    ) -> None:  # pragma: no cover
        ...


class CloudMonitoringSink(MetricSink):
    """Ship counter increments to GCP Cloud Monitoring as custom metrics."""

    def __init__(self, project_id: str) -> None:
        self.project_id = project_id
        self._client: Any = None

    def _ensure_client(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            from google.cloud import monitoring_v3

            self._client = monitoring_v3.MetricServiceClient()
            self._monitoring_v3 = monitoring_v3
        except Exception as exc:  # noqa: BLE001
            logger.warning("Cloud Monitoring client init failed: %s", exc)
            self._client = None
        return self._client

    def publish(
        self, metric_name: str, labels: tuple[str, ...], value: int
    ) -> None:
        client = self._ensure_client()
        if client is None:
            return
        try:
            from google.api import metric_pb2 as ga_metric  # noqa: F401

            series = self._monitoring_v3.TimeSeries()
            series.metric.type = f"custom.googleapis.com/{metric_name}"
            for idx, label_value in enumerate(labels):
                series.metric.labels[f"label_{idx}"] = label_value
            series.resource.type = "global"

            now = self._monitoring_v3.types.TimeInterval(
                end_time={"seconds": _now_seconds()}
            )
            point = self._monitoring_v3.Point(
                interval=now, value={"int64_value": value}
            )
            series.points = [point]
            client.create_time_series(
                name=f"projects/{self.project_id}", time_series=[series]
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "failed to publish %s %s: %s", metric_name, labels, exc
            )


def _now_seconds() -> int:
    import time

    return int(time.time())


# ── Counters defined in SPEC.md § Observability ────────────────────────────

webhook_auth_failures = Counter("xenia/webhook/auth_failures")
runs_created = Counter("xenia/runs/created")
skills_calls = Counter("xenia/skills/calls")
runs_tokens = Counter("xenia/runs/tokens")
runs_cost_usd = Counter("xenia/runs/cost_usd")
queue_depth = Counter("xenia/queue/depth")


def configure_sink() -> None:
    """Attach a CloudMonitoringSink to all counters when GCP_PROJECT_ID is set."""
    project_id = (
        os.environ.get("GCP_PROJECT_ID")
        or os.environ.get("GOOGLE_CLOUD_PROJECT")
    )
    if not project_id:
        return
    sink = CloudMonitoringSink(project_id)
    for counter in (
        webhook_auth_failures,
        runs_created,
        skills_calls,
        runs_tokens,
        runs_cost_usd,
        queue_depth,
    ):
        counter.attach(sink)
