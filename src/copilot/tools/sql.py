"""Read-only SQL over the warehouse database.

Defense in depth, so a confused or manipulated agent cannot change data:
1. the database is opened in SQLite read-only mode (`mode=ro`);
2. an authorizer callback rejects every operation that is not a read
   (INSERT/UPDATE/DELETE, DDL, ATTACH, PRAGMA, ...);
3. one statement per call, at most MAX_ROWS rows, at most TIMEOUT_S seconds.
Errors are returned as data, so the agent can read them and fix its query.
"""

import sqlite3
import time
from pathlib import Path

from copilot.config import DC_DB_PATH
from copilot.observability import traceable
from copilot.synthetic.catalog import SIM_NOW

MAX_ROWS = 100
TIMEOUT_S = 5.0

_ALLOWED = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION,
            sqlite3.SQLITE_RECURSIVE}

COLUMN_NOTES = {
    "skus": {
        "is_hazmat": "1 if a DOT hazardous material",
        "limited_quantity": "1 = shipped as limited quantity (consumer packs), 0 = fully regulated",
        "hazard_class": "DOT class/division, e.g. '2.1', '3', '5.1', '8'",
        "storage_zone": "home zone, see zones table",
        "channel": "'retail' or 'professional'",
    },
    "shipments": {
        "status": "'planned' | 'loading' | 'departed'",
        "trailer_id": "NULL if no trailer assigned yet",
        "planned_departure": "local time 'YYYY-MM-DD HH:MM'",
        "hazmat_on_board": "1 if any line is a hazmat SKU",
    },
    "inventory": {"status": "'available' | 'allocated' | 'hold' | 'quarantine'",
                  "pallet_sscc": "18-digit GS1 SSCC"},
    "inbound_receipts": {"status": "'expected' | 'received' | 'received_with_exceptions'"},
    "exceptions": {
        "type": "e.g. MISSING_SSCC, LATE_CARRIER, HAZMAT_SEGREGATION, LEAK_SPILL",
        "severity": "'low' | 'medium' | 'high'",
        "status": "'open' | 'resolved'",
        "reference_type": "'receipt' | 'shipment' | 'sku' | 'zone'",
        "incident_report_id": "INC-xxxx document for medium/high exceptions",
    },
    "carriers": {"hazmat_endorsed": "1 if allowed to haul fully regulated hazmat"},
}


def _authorizer(action, *_):
    return sqlite3.SQLITE_OK if action in _ALLOWED else sqlite3.SQLITE_DENY


def connect(path: Path = DC_DB_PATH, guarded: bool = True) -> sqlite3.Connection:
    """Read-only connection. `guarded` adds the authorizer: always on for agent-written SQL;
    off only for trusted internal queries (schema introspection uses PRAGMA functions)."""
    if not path.exists():
        raise FileNotFoundError(f"{path} not found - run: uv run python -m copilot.synthetic.build_wms")
    con = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True, check_same_thread=False)
    if guarded:
        con.set_authorizer(_authorizer)
    return con


@traceable(run_type="tool", name="sql_query")
def sql_query(query: str, db_path: Path = DC_DB_PATH) -> dict:
    """Run ONE read-only SQL SELECT against the warehouse database."""
    con = connect(db_path)
    deadline = time.monotonic() + TIMEOUT_S
    con.set_progress_handler(lambda: int(time.monotonic() > deadline), 10_000)
    try:
        cur = con.execute(query)
        rows = cur.fetchmany(MAX_ROWS + 1)
        columns = [d[0] for d in cur.description or []]
        return {
            "columns": columns,
            "rows": [list(r) for r in rows[:MAX_ROWS]],
            "row_count": min(len(rows), MAX_ROWS),
            "truncated": len(rows) > MAX_ROWS,
        }
    except (sqlite3.Error, sqlite3.Warning) as exc:
        msg = str(exc)
        if "not authorized" in msg:
            msg += " (this tool is read-only: only SELECT queries are allowed)"
        elif "interrupted" in msg:
            msg = f"query exceeded {TIMEOUT_S:.0f}s - add filters or a LIMIT"
        return {"error": msg}
    finally:
        con.close()


@traceable(run_type="tool", name="describe_schema")
def describe_schema(db_path: Path = DC_DB_PATH) -> str:
    """Tables, columns and value conventions - given to the agent so it writes valid SQL."""
    con = connect(db_path, guarded=False)
    try:
        tables = [r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")]
        lines = [f"SQLite warehouse database. Current time in this simulation: {SIM_NOW}.", ""]
        for t in tables:
            cols = con.execute(f'SELECT name, type FROM pragma_table_info("{t}")').fetchall()
            lines.append(f"{t}(" + ", ".join(f"{n} {typ}" for n, typ in cols) + ")")
            for col, note in COLUMN_NOTES.get(t, {}).items():
                lines.append(f"  - {col}: {note}")
        return "\n".join(lines)
    finally:
        con.close()
