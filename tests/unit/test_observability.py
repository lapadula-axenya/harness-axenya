"""Unit tests for Langfuse tracer + metrics sink (no-op when unconfigured)."""
from __future__ import annotations

import uuid

from xenia.observability.langfuse_tracer import LangfuseTracer
from xenia.observability.metrics import (
    Counter,
    MetricSink,
    runs_created,
    webhook_auth_failures,
)


def test_langfuse_disabled_when_keys_missing():
    tracer = LangfuseTracer(public_key="", secret_key="", host="")
    assert tracer.enabled is False
    # Calls are safe no-ops
    assert tracer.trace_run(uuid.uuid4(), "agent") is None
    tracer.log_llm_call(
        trace_id=None, model="m", prompt=[], response_text="", tokens_input=0, tokens_output=0
    )
    tracer.log_tool_call(
        trace_id=None, skill_name="s", tool_input={}, tool_output={}, ok=True
    )
    tracer.flush()  # no-op


def test_counter_inc_and_value():
    c = Counter("test/counter")
    c.inc("agent_a", "webhook")
    c.inc("agent_a", "webhook", by=2)
    c.inc("agent_b", "api")
    assert c.value("agent_a", "webhook") == 3
    assert c.value("agent_b", "api") == 1
    assert c.value("agent_c", "anything") == 0


def test_counter_publishes_to_sink():
    seen: list[tuple[str, tuple[str, ...], int]] = []

    class _Recorder(MetricSink):
        def publish(self, name, labels, value):  # type: ignore[no-untyped-def]
            seen.append((name, labels, value))

    c = Counter("xenia/test/x")
    c.attach(_Recorder())
    c.inc("a", by=2)
    c.inc("a", "b")
    assert seen == [
        ("xenia/test/x", ("a",), 2),
        ("xenia/test/x", ("a", "b"), 1),
    ]


def test_module_level_counters_exist():
    # Just ensure the module-level counters from SPEC.md § Observability are wired.
    runs_created.inc("agent_a", "api")
    webhook_auth_failures.inc("agent_a")
    assert runs_created.value("agent_a", "api") >= 1
    assert webhook_auth_failures.value("agent_a") >= 1
