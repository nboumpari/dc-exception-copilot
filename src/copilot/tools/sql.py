"""Read-only SQL over the warehouse database.

Defense in depth, so a confused or manipulated agent cannot change data:
1. the database is opened in SQLite read-only mode (`mode=ro`);
2. an authorizer callback rejects every operation that is not a read
   (INSERT/UPDATE/DELETE, DDL, ATTACH, PRAGMA, ...);
3. one statement per call, at most MAX_ROWS rows, at most TIMEOUT_S seconds.
Errors are returned as data, so the agent can read them and fix its query.
"""

import re
import sqlite3
import time
from pathlib import Path

from copilot.config import DC_DB_PATH
from copilot.observability import traceable
from copilot.synthetic.catalog import SIM_NOW

MAX_ROWS = 100
TIMEOUT_S = 5.0
MAX_ENUM_VALUES = 15  # list a TEXT column's values when it has at most this many
_FREE_TEXT = {"description", "root_cause", "corrective_action", "name", "proper_shipping_name",
              "pack_size", "lot", "city", "trailer_id", "pallet_sscc"}

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


_EQ_LITERAL = re.compile(r"=\s*'([^']{2,60})'")
_NAME_COLUMNS = (("customers", "name"), ("suppliers", "name"), ("carriers", "name"),
                 ("employees", "name"), ("skus", "description"))


def _empty_result_hints(con, query: str, rows: list) -> list[str]:
    """When a query finds nothing (no rows, or one row of zeros such as COUNT(*) = 0) and it
    compared a name with '=', check whether that name exists partially. Evaluation showed
    the agent sometimes reported "0" after WHERE name = 'ValueMart' (real name: 'ValueMart
    Regional DC') despite prompt rules - the tool now says so at the moment it matters."""
    looks_empty = not rows or (len(rows) == 1 and all(v in (0, None) for v in rows[0]))
    if not looks_empty:
        return []
    hints = []
    for literal in dict.fromkeys(_EQ_LITERAL.findall(query)):
        for table, col in _NAME_COLUMNS:
            matches = [r[0] for r in con.execute(
                f'SELECT "{col}" FROM "{table}" WHERE "{col}" LIKE ? AND "{col}" <> ? LIMIT 3',
                (f"%{literal}%", literal))]
            if matches:
                hints.append(f"'{literal}' matched nothing exactly, but {table}.{col} has "
                             f"{matches} - filter with LIKE '%{literal}%' or by ID.")
    return hints


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
        result = {
            "columns": columns,
            "rows": [list(r) for r in rows[:MAX_ROWS]],
            "row_count": min(len(rows), MAX_ROWS),
            "truncated": len(rows) > MAX_ROWS,
        }
        hints = _empty_result_hints(con, query, rows)
        if hints:
            result["hint"] = " ".join(hints)
        return result
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
            # Exact values of short categorical columns, read from the data: without them the
            # model guessed 'UNREADABLE_SSCC' for 'UNREADABLE_LABEL' and silently got no rows.
            for col, typ in cols:
                if typ != "TEXT" or col.endswith(("_id", "_at")) or col in _FREE_TEXT:
                    continue
                values = [r[0] for r in con.execute(
                    f'SELECT DISTINCT "{col}" FROM "{t}" WHERE "{col}" IS NOT NULL '
                    f"ORDER BY 1 LIMIT {MAX_ENUM_VALUES + 1}")]
                if 0 < len(values) <= MAX_ENUM_VALUES:
                    lines.append(f"  - {col} values: " + ", ".join(repr(v) for v in values))
        return "\n".join(lines)
    finally:
        con.close()
