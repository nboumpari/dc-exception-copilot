"""Application logs and the approval audit trail.

Two local, append-only JSON Lines files (one JSON object per line, easy to grep or load
into pandas), complementing LangSmith tracing:

    logs/app.jsonl    what happened in the system: requests, answers, tool calls, guardrail
                      events, errors. Never contains question text or secrets - only ids,
                      sizes, names and timings (question text lives in LangSmith).
    logs/audit.jsonl  who approved or rejected which proposed email/ticket, and when.
                      Written on every decision, whether or not `setup_logging()` ran.

LangSmith answers "why did the AI say that?"; these logs answer "what happened, when, and
who decided?" - and keep working when LangSmith is off or out of quota. Every line carries
the conversation `thread_id`, and answers also carry the LangSmith `run_id`, so a log line
leads straight to its trace.
"""

import json
import logging
import sys
import threading
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler

from copilot.config import PROJECT_ROOT

LOG_DIR = PROJECT_ROOT / "logs"
APP_LOG = "app.jsonl"
AUDIT_LOG = "audit.jsonl"

_events = logging.getLogger("copilot.events")
_audit_lock = threading.Lock()
# silent unless an entry point calls setup_logging() (otherwise Python prints warnings to
# stderr, e.g. into notebook outputs)
logging.getLogger("copilot").addHandler(logging.NullHandler())


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        line = {"ts": _now(), "level": record.levelname, "logger": record.name,
                "event": record.getMessage(), **getattr(record, "fields", {})}
        if record.exc_info:
            line["error"] = self.formatException(record.exc_info)
        return json.dumps(line, ensure_ascii=False, default=str)


class ConsoleFormatter(logging.Formatter):
    """Short human-readable lines for the terminal: `12:00:01 INFO agent.answer tools=2`."""

    def format(self, record: logging.LogRecord) -> str:
        fields = " ".join(f"{k}={v}" for k, v in getattr(record, "fields", {}).items())
        text = f"{datetime.now():%H:%M:%S} {record.levelname} {record.getMessage()} {fields}"
        return text.rstrip() + (f"\n{self.formatException(record.exc_info)}" if record.exc_info else "")


def setup_logging(console: bool = True) -> None:
    """Send `copilot.*` logs to logs/app.jsonl (rotated at 5 MB) and, optionally, the
    console. Safe to call more than once."""
    root = logging.getLogger("copilot")
    if any(getattr(h, "_copilot", False) for h in root.handlers):
        return
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    handlers: list[logging.Handler] = [
        RotatingFileHandler(LOG_DIR / APP_LOG, maxBytes=5_000_000, backupCount=3, encoding="utf-8")]
    handlers[0].setFormatter(JsonFormatter())
    if console:
        handlers.append(logging.StreamHandler(sys.stderr))
        handlers[1].setFormatter(ConsoleFormatter())
    for h in handlers:
        h._copilot = True
        root.addHandler(h)
    root.setLevel(logging.INFO)


def log_event(event: str, level: int = logging.INFO, **fields) -> None:
    """One structured event, e.g. log_event("tool.call", tool="sql_query", duration_ms=12)."""
    _events.log(level, event, extra={"fields": fields})


def audit(**record) -> None:
    """Append one decision to the audit trail (never rotated or rewritten)."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    line = json.dumps({"ts": _now(), **record}, ensure_ascii=False, default=str)
    with _audit_lock, (LOG_DIR / AUDIT_LOG).open("a", encoding="utf-8") as f:
        f.write(line + "\n")
