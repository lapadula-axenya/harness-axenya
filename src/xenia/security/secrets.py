"""Secret Manager adapter.

In production secrets live in GCP Secret Manager; in dev they come from
environment variables. Callers always call `read_secret(name)` and let
the adapter pick the right backend.

Naming: secret IDs are stored in Secret Manager as the env var name in
lower-snake-case (e.g. `hubspot_mcp_token`). The mapping is intentionally
1:1 with env vars so that local dev matches prod with zero translation.
"""
from __future__ import annotations

import logging
import os
from functools import lru_cache

from xenia.config import get_settings

logger = logging.getLogger(__name__)


class SecretNotFoundError(KeyError):
    """Raised when a secret can't be read from any backend."""


def _gcp_project_id() -> str | None:
    return (
        os.environ.get("GCP_PROJECT_ID")
        or os.environ.get("GOOGLE_CLOUD_PROJECT")
        or os.environ.get("PROJECT_ID")
    )


@lru_cache(maxsize=128)
def read_secret(name: str, *, required: bool = False) -> str | None:
    """Read a secret by `name`.

    Resolution order:
      1. `os.environ[name.upper()]` — dev path.
      2. GCP Secret Manager `projects/{project}/secrets/{name}/versions/latest`
         — when `GCP_PROJECT_ID` (or equivalent) is set in the env.

    `required=True` raises `SecretNotFoundError` if the secret isn't found.
    Otherwise returns `None`.
    """
    env_value = os.environ.get(name.upper())
    if env_value:
        return env_value

    settings = get_settings()
    if settings.is_dev and _gcp_project_id() is None:
        if required:
            raise SecretNotFoundError(f"secret {name!r} not in env (dev)")
        return None

    project_id = _gcp_project_id()
    if not project_id:
        if required:
            raise SecretNotFoundError(
                f"secret {name!r} requires GCP_PROJECT_ID for Secret Manager"
            )
        return None

    try:
        from google.cloud import secretmanager

        client = secretmanager.SecretManagerServiceClient()
        path = client.secret_version_path(project_id, name, "latest")
        response = client.access_secret_version(name=path)
        return str(response.payload.data.decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "failed to read %r from Secret Manager: %s", name, exc, exc_info=False
        )
        if required:
            raise SecretNotFoundError(f"secret {name!r}: {exc}") from exc
        return None


def reset_cache() -> None:
    """Clear the LRU cache (useful in tests after rotating env vars)."""
    read_secret.cache_clear()
