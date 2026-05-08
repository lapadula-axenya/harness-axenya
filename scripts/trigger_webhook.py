#!/usr/bin/env python3
"""CLI helper that signs and POSTs a webhook to a local xenia-api.

Usage:
    python scripts/trigger_webhook.py exemplo_eco '{"foo": "bar"}'
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import httpx
import yaml

from xenia.security.hmac_verify import compute_signature

ROOT = Path(__file__).resolve().parent.parent


def _load_secret_env_for(agent_id: str) -> str:
    yaml_path = ROOT / "agents" / f"{agent_id}.yaml"
    if not yaml_path.exists():
        sys.exit(f"agent definition not found: {yaml_path}")
    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    env_name = data.get("webhook_secret_env")
    if not env_name:
        sys.exit(f"agent {agent_id!r} has no webhook_secret_env")
    secret = os.environ.get(env_name)
    if not secret:
        sys.exit(f"env var {env_name!r} not set; export it before running")
    return secret


def main() -> None:
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)

    agent_id = sys.argv[1]
    payload_str = sys.argv[2]
    base_url = os.environ.get("XENIA_API_URL", "http://localhost:8080")

    try:
        payload = json.loads(payload_str)
    except json.JSONDecodeError as exc:
        sys.exit(f"invalid JSON payload: {exc}")

    secret = _load_secret_env_for(agent_id)
    body_bytes = json.dumps(payload, separators=(",", ":")).encode()
    ts = str(int(time.time()))
    sig = compute_signature(body_bytes, ts, secret)

    url = f"{base_url}/v1/webhooks/{agent_id}"
    response = httpx.post(
        url,
        content=body_bytes,
        headers={
            "Content-Type": "application/json",
            "X-Xenia-Signature": sig,
            "X-Xenia-Timestamp": ts,
        },
        timeout=10.0,
    )
    print(f"POST {url} -> {response.status_code}")
    print(response.text)


if __name__ == "__main__":
    main()
