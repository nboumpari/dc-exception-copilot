"""Agent tools, tested against a fresh synthetic database built in a temp dir."""

import pytest

from copilot.config import RAW_DIR
from copilot.synthetic.build_wms import Generator, write_db
from copilot.tools import sql
from copilot.tools.hazmat import build_reference_db, lookup_hazmat
from copilot.tools.search import choose_mode
from copilot.tools.segregation import LoadItem, _classes, check_load, pair_code
from copilot.tools.shipments import assess_departure_risk, check_shipment_compliance

needs_corpus = pytest.mark.skipif(
    not (RAW_DIR / "hmr_177_848").exists(), reason="corpus not downloaded")


@pytest.fixture(scope="module")
def dc(tmp_path_factory):
    gen = Generator(seed=42)
    scenarios = gen.run()
    path = tmp_path_factory.mktemp("db") / "dc.db"
    write_db(gen, path)
    return path, scenarios


# ---------- read-only SQL ----------
def test_sql_select_works(dc):
    path, _ = dc
    r = sql.sql_query("SELECT COUNT(*) AS n FROM skus", db_path=path)
    assert r["columns"] == ["n"] and r["rows"][0][0] > 0


@pytest.mark.parametrize("query", [
    "DELETE FROM shipments",
    "UPDATE skus SET is_hazmat = 0",
    "INSERT INTO carriers VALUES ('X', 'X', 1)",
    "DROP TABLE skus",
    "CREATE TABLE t (x)",
    "ATTACH DATABASE 'other.db' AS other",
    "PRAGMA writable_schema = 1",
])
def test_sql_rejects_anything_but_reads(dc, query):
    path, _ = dc
    assert "not authorized" in sql.sql_query(query, db_path=path)["error"]
    assert sql.sql_query("SELECT COUNT(*) FROM shipments", db_path=path)["rows"][0][0] > 0


def test_sql_rejects_stacked_statements(dc):
    path, _ = dc
    assert "error" in sql.sql_query("SELECT 1; DELETE FROM skus", db_path=path)


def test_sql_row_limit_and_timeout(dc, monkeypatch):
    path, _ = dc
    r = sql.sql_query("SELECT * FROM shipment_lines", db_path=path)
    assert r["row_count"] == sql.MAX_ROWS and r["truncated"]
    monkeypatch.setattr(sql, "TIMEOUT_S", 0.2)
    endless = "WITH RECURSIVE n(i) AS (SELECT 1 UNION ALL SELECT i + 1 FROM n) SELECT COUNT(*) FROM n"
    assert "exceeded" in sql.sql_query(endless, db_path=path)["error"]


def test_schema_description_has_tables_and_conventions(dc):
    path, _ = dc
    text = sql.describe_schema(db_path=path)
    assert "shipments(" in text and "limited_quantity" in text and "2026-10-16 18:00" in text


# ---------- hazmat table ----------
HEADER = "<TH>h</TH>" * 14  # real table uses header cells, which the parser ignores
EMPTY_12 = "<TD></TD>" * 12
HAZMAT_XML = f"""<?xml version="1.0"?><DIV8><TABLE><CAPTION>§ 172.101 Hazardous Materials Table</CAPTION>
<TR>{HEADER}</TR>
<TR><TD></TD><TD>Hypochlorite solutions</TD><TD>8</TD><TD>UN1791</TD><TD>II</TD><TD>8</TD><TD>IB2</TD>
<TD>154</TD><TD>202</TD><TD>242</TD><TD>1 L</TD><TD>30 L</TD><TD>B</TD><TD>26</TD></TR>
<TR><TD></TD><TD></TD><TD></TD><TD></TD><TD>III</TD><TD>8</TD><TD>IB3</TD>
<TD>154</TD><TD>203</TD><TD>241</TD><TD>5 L</TD><TD>60 L</TD><TD>B</TD><TD>26</TD></TR>
<TR><TD></TD><TD>Bleach, see Hypochlorite solutions</TD>{EMPTY_12}</TR>
</TABLE></DIV8>"""


def test_hazmat_parser_fills_continuation_rows_and_skips_references(tmp_path):
    xml = tmp_path / "t.xml"
    xml.write_text(HAZMAT_XML, encoding="utf-8")
    db = tmp_path / "ref.db"
    assert build_reference_db(db, source=xml) == 2
    r = lookup_hazmat("1791", db_path=db)  # bare number is normalized to UN1791
    assert [(e["packing_group"], e["qty_passenger_aircraft_rail"]) for e in r["entries"]] == [
        ("II", "1 L"), ("III", "5 L")]
    assert r["entries"][1]["proper_shipping_name"] == "Hypochlorite solutions"
    assert lookup_hazmat(name="bleach", db_path=db)["found"] == 0


# ---------- segregation ----------
def test_class_label_normalization():
    assert _classes("1.1 and 1.2") == ["1.1", "1.2"]
    assert _classes("2.3", "Poisonous gas Zone B") == ["2.3B"]
    assert _classes("8 liquids only") == ["8"]


@needs_corpus
@pytest.mark.parametrize(("a", "b", "code"), [
    ("3", "5.1", "O"), ("5.1", "8", "O"), ("8", "5.1", "O"), ("2.1", "5.1", ""),
    ("2.1", "3", ""), ("1.1", "3", "X"), ("4.3", "8", "O"),
])
def test_segregation_table_cells(a, b, code):
    assert pair_code(a, b) == code


@needs_corpus
def test_check_load_excludes_limited_quantities():
    peroxide = LoadItem("A", "peroxide drum", "5.1", "UN2014", limited_quantity=False)
    drain_lq = LoadItem("B", "drain opener 1 L", "8", "UN1824", limited_quantity=True)
    caustic = LoadItem("C", "caustic drum", "8", "UN1824", limited_quantity=False)
    assert check_load([peroxide, drain_lq])["compliant"] is True
    result = check_load([peroxide, caustic])
    assert result["compliant"] is False
    assert any(f["table_value"] == "O" for f in result["findings"] if f["severity"] == "violation")


@needs_corpus
def test_check_load_flags_hypochlorite_with_tcca_even_as_limited_quantity():
    shock = LoadItem("A", "pool shock 454 g", "5.1", "UN2880", limited_quantity=True)
    tcca = LoadItem("B", "TCCA pail", "5.1", "UN2468", limited_quantity=False)
    findings = check_load([shock, tcca])["findings"]
    assert any(f["severity"] == "requirement" and "TCCA" in f["rule"] for f in findings)


# ---------- shipment tools on the planted scenarios ----------
@needs_corpus
def test_planted_segregation_conflict_is_caught(dc):
    path, sc = dc
    r = check_shipment_compliance(sc["seg_conflict_tomorrow"], db_path=path)
    assert r["compliant"] is False and r["regulated_classes"] == ["5.1", "8"]


@needs_corpus
def test_limited_quantity_load_is_not_a_false_alarm(dc):
    path, sc = dc
    r = check_shipment_compliance(sc["lq_no_conflict"], db_path=path)
    assert r["compliant"] is True and r["regulated_classes"] == []


@needs_corpus
def test_non_endorsed_carrier_is_caught(dc):
    path, sc = dc
    r = check_shipment_compliance(sc["carrier_not_hazmat"], db_path=path)
    rules = [f["rule"] for f in r["findings"]]
    assert r["compliant"] is False
    assert any("endorsement" in x for x in rules) and any("TCCA" in x for x in rules)


@needs_corpus
def test_early_departure_without_trailer_and_bad_carrier_is_at_risk(dc):
    path, sc = dc
    r = assess_departure_risk(sc["at_risk_departure"], db_path=path)
    cites = {x["citation"] for x in r["reasons"]}
    assert r["at_risk"] and {"SOP-OUT-002 §3.1", "SOP-OUT-002 §3.2"} <= cites
    assert r["carrier_on_time_30d"] < 0.85


@needs_corpus
def test_reliable_planned_shipment_is_not_at_risk(dc):
    path, sc = dc
    assert assess_departure_risk(sc["lq_no_conflict"], db_path=path)["at_risk"] is False


def test_unknown_shipment_returns_error(dc):
    path, _ = dc
    assert "error" in check_shipment_compliance("SHP-99999", db_path=path)


# ---------- search mode routing ----------
@pytest.mark.parametrize(("query", "mode"), [
    ("What is SHP-01209?", "hybrid"), ("rules for UN2014", "hybrid"),
    ("explain 177.848", "hybrid"), ("how often is forklift training", "vector"),
])
def test_search_mode_routing(query, mode):
    assert choose_mode(query) == mode
