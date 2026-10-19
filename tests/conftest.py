"""Test-wide setup: tests must never send traces to LangSmith, even if .env enables it."""

import os

os.environ["LANGSMITH_TRACING"] = "false"

import pytest

from copilot.config import settings


@pytest.fixture(autouse=True)
def _no_tracing(monkeypatch):
    monkeypatch.setattr(settings, "langsmith_tracing", False)
    monkeypatch.setenv("LANGSMITH_TRACING", "false")


@pytest.fixture(autouse=True)
def log_dir(tmp_path, monkeypatch):
    """Tests write app and audit logs to a temporary folder, never to the real logs/."""
    import logging

    from copilot import logs

    monkeypatch.setattr(logs, "LOG_DIR", tmp_path / "logs")
    yield tmp_path / "logs"
    root = logging.getLogger("copilot")  # drop handlers setup_logging() added in this test
    for h in [h for h in root.handlers if getattr(h, "_copilot", False)]:
        root.removeHandler(h)
        h.close()
