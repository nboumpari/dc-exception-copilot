"""Test-wide setup: tests must never send traces to LangSmith, even if .env enables it."""

import os

os.environ["LANGSMITH_TRACING"] = "false"

import pytest

from copilot.config import settings


@pytest.fixture(autouse=True)
def _no_tracing(monkeypatch):
    monkeypatch.setattr(settings, "langsmith_tracing", False)
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
