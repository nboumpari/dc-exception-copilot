"""Hazardous Materials Table (49 CFR 172.101) as a queryable reference table.

The table is parsed from the downloaded eCFR XML into data/reference.db, so hazard
classes, packing groups and quantity limits come from the regulation itself - never
from the LLM's memory.

Table layout: 14 columns. An entry with several packing groups continues on following
rows whose name/class/UN cells are blank; those are filled from the row above.
"Name, see Other name" cross-reference rows (no class) are skipped.
"""

import re
import sqlite3
from pathlib import Path

from lxml import etree

from copilot.config import RAW_DIR, REFERENCE_DB_PATH
from copilot.observability import traceable

SOURCE_XML = RAW_DIR / "hmr_172_101" / "hmr_172_101.xml"
CITATION = "49 CFR 172.101"
COLUMNS = (
    "symbols", "proper_shipping_name", "hazard_class", "un_number", "packing_group",
    "label_codes", "special_provisions", "pkg_exceptions", "pkg_non_bulk", "pkg_bulk",
    "qty_passenger_aircraft_rail", "qty_cargo_aircraft", "vessel_location", "vessel_other",
)


def _clean(el) -> str:
    return re.sub(r"\s+", " ", "".join(el.itertext())).strip()


def parse_hazmat_table(path: Path = SOURCE_XML) -> list[dict]:
    root = etree.parse(str(path)).getroot()
    def caption(t) -> str:
        c = t.find("CAPTION")
        return _clean(c) if c is not None else ""

    table = next(t for t in root.iter("TABLE") if "Hazardous Materials Table" in caption(t))
    entries, last = [], None
    for tr in table.iter("TR"):
        cells = [_clean(td) for td in tr if td.tag == "TD"]
        if len(cells) != len(COLUMNS):
            continue
        row = dict(zip(COLUMNS, cells))
        if not row["proper_shipping_name"] and last:  # continuation row: next packing group
            for k in ("symbols", "proper_shipping_name", "hazard_class", "un_number"):
                row[k] = last[k]
        if not row["hazard_class"] or not row["un_number"]:  # "see ..." cross-references
            continue
        entries.append(row)
        last = row
    return entries


def build_reference_db(path: Path = REFERENCE_DB_PATH, source: Path = SOURCE_XML) -> int:
    entries = parse_hazmat_table(source)
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.execute("DROP TABLE IF EXISTS hazmat_table")
    con.execute(f"CREATE TABLE hazmat_table ({', '.join(f'{c} TEXT' for c in COLUMNS)})")
    con.executemany(f"INSERT INTO hazmat_table VALUES ({','.join('?' * len(COLUMNS))})",
                    [tuple(e[c] for c in COLUMNS) for e in entries])
    con.execute("CREATE INDEX idx_un ON hazmat_table(un_number)")
    con.commit()
    con.close()
    return len(entries)


def _connect(path: Path) -> sqlite3.Connection:
    if not path.exists():
        build_reference_db(path)
    con = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


@traceable(run_type="tool", name="lookup_hazmat")
def lookup_hazmat(un_number: str | None = None, name: str | None = None, limit: int = 10,
                  db_path: Path = REFERENCE_DB_PATH) -> dict:
    """Look up official hazmat entries by UN/NA number (e.g. 'UN1950') or by name text."""
    if not un_number and not name:
        return {"error": "give un_number or name"}
    con = _connect(db_path)
    try:
        if un_number:
            un = un_number.strip().upper().replace(" ", "")
            if re.fullmatch(r"\d{4}", un):
                un = "UN" + un
            rows = con.execute("SELECT * FROM hazmat_table WHERE un_number = ? LIMIT ?",
                               (un, limit)).fetchall()
        else:
            rows = con.execute(
                "SELECT * FROM hazmat_table WHERE proper_shipping_name LIKE ? LIMIT ?",
                (f"%{name.strip()}%", limit)).fetchall()
        return {"citation": CITATION, "entries": [dict(r) for r in rows],
                "found": len(rows)}
    finally:
        con.close()


def main() -> None:
    n = build_reference_db()
    print(f"{n} Hazardous Materials Table entries -> {REFERENCE_DB_PATH}")


if __name__ == "__main__":
    main()
