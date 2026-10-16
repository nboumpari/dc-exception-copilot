"""LangSmith tracing setup.

The LangSmith SDK reads its configuration from environment variables, while the rest of
the project reads `.env` through `copilot.config.settings`. `setup_tracing()` bridges the
two and is called once at the start of every entry point (CLI, notebook, API).

Tracing is off unless LANGSMITH_TRACING=true AND a LANGSMITH_API_KEY is set, so tests and
offline runs never send data anywhere.
"""

import os

from langsmith import traceable

from copilot.config import settings

__all__ = ["setup_tracing", "traceable", "tracing_enabled"]


def tracing_enabled() -> bool:
    return settings.langsmith_tracing and bool(settings.langsmith_api_key)


def setup_tracing(project: str | None = None) -> bool:
    """Export LangSmith settings to the environment. Returns True if tracing is on."""
    if not tracing_enabled():
        os.environ["LANGSMITH_TRACING"] = "false"
        return False
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
    os.environ["LANGSMITH_PROJECT"] = project or settings.langsmith_project
    os.environ["LANGSMITH_ENDPOINT"] = settings.langsmith_endpoint
    return True
