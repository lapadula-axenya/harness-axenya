"""Metrics — Phase 4 wires Cloud Monitoring; Phase 1 keeps in-memory counters."""
from __future__ import annotations

import threading
from collections import defaultdict


class Counter:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._values: dict[tuple[str, ...], int] = defaultdict(int)

    def inc(self, *labels: str, by: int = 1) -> None:
        with self._lock:
            self._values[labels] += by

    def value(self, *labels: str) -> int:
        with self._lock:
            return self._values[labels]


webhook_auth_failures = Counter()
runs_created = Counter()
skills_calls = Counter()
