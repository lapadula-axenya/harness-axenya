"""Unit tests for the Secret Manager adapter."""
from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from xenia.security.secrets import SecretNotFoundError, read_secret, reset_cache


@pytest.fixture(autouse=True)
def _reset_cache():
    reset_cache()
    yield
    reset_cache()


def test_reads_from_env(monkeypatch):
    monkeypatch.setenv("MY_TEST_SECRET", "abc123")
    assert read_secret("my_test_secret") == "abc123"


def test_returns_none_when_missing_and_not_required():
    assert read_secret("does_not_exist") is None


def test_raises_when_required_and_missing():
    with pytest.raises(SecretNotFoundError):
        read_secret("nope_definitely_missing", required=True)


def test_falls_back_to_secret_manager_when_project_id_set(monkeypatch):
    monkeypatch.setenv("GCP_PROJECT_ID", "fake-project")
    monkeypatch.delenv("MY_SECRET", raising=False)

    fake_response = type("R", (), {"payload": type("P", (), {"data": b"from-sm"})()})()

    class FakeClient:
        def secret_version_path(self, project, name, version):
            return f"projects/{project}/secrets/{name}/versions/{version}"

        def access_secret_version(self, name):
            return fake_response

    fake_module = type(
        "M", (), {"SecretManagerServiceClient": lambda *_a, **_kw: FakeClient()}
    )

    with (
        patch.dict(os.sys.modules, {"google.cloud.secretmanager": fake_module}),
        patch("google.cloud.secretmanager", fake_module, create=True),
    ):
        assert read_secret("my_secret") == "from-sm"
