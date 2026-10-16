"""Shipment-level checks built on the warehouse database.

- check_shipment_compliance: hazmat segregation + chemical rule + carrier endorsement
- assess_departure_risk:     the at-risk rules from SOP-OUT-002 §3

Both read the DB with the guarded read-only connection and return structured findings
with citations, so the agent can explain them without deciding them.
"""

from datetime import datetime, timedelta
from pathlib import Path

from copilot.config import DC_DB_PATH
from copilot.observability import traceable
from copilot.synthetic.catalog import SIM_NOW
from copilot.tools.segregation import LoadItem, check_load
from copilot.tools.sql import connect

ON_TIME_GRACE_MIN = 60  # SOP-OUT-002 §2: on time = departs <= 60 min after plan
ON_TIME_THRESHOLD = 0.85  # SOP-OUT-002 §3.2
EARLY_DEPARTURE_HOUR = 8  # SOP-OUT-002 §3.1
LOOKBACK_DAYS = 30


def _shipment(con, shipment_id: str) -> dict | None:
    row = con.execute(
        """SELECT s.shipment_id, s.status, s.planned_departure, s.actual_departure, s.trailer_id,
                  s.door, s.pallets, c.customer_id, c.name AS customer, c.city,
                  k.carrier_id, k.name AS carrier, k.hazmat_endorsed
           FROM shipments s JOIN customers c USING (customer_id) JOIN carriers k USING (carrier_id)
           WHERE s.shipment_id = ?""", (shipment_id,)).fetchone()
    if row is None:
        return None
    cols = ["shipment_id", "status", "planned_departure", "actual_departure", "trailer_id", "door",
            "pallets", "customer_id", "customer", "city", "carrier_id", "carrier", "hazmat_endorsed"]
    return dict(zip(cols, row))


def _lines(con, shipment_id: str) -> list[dict]:
    rows = con.execute(
        """SELECT l.sku, k.description, l.pallets, k.hazard_class, k.un_number, k.limited_quantity
           FROM shipment_lines l JOIN skus k USING (sku) WHERE l.shipment_id = ?""",
        (shipment_id,)).fetchall()
    return [dict(zip(["sku", "description", "pallets", "hazard_class", "un_number",
                      "limited_quantity"], r)) for r in rows]


@traceable(run_type="tool", name="check_shipment_compliance")
def check_shipment_compliance(shipment_id: str, db_path: Path = DC_DB_PATH) -> dict:
    """Hazmat compliance of one shipment: segregation, chemical rules, carrier endorsement."""
    con = connect(db_path)
    try:
        shp = _shipment(con, shipment_id)
        if shp is None:
            return {"error": f"shipment {shipment_id} not found"}
        lines = _lines(con, shipment_id)
    finally:
        con.close()

    items = [LoadItem(ln["sku"], ln["description"], ln["hazard_class"], ln["un_number"],
                      bool(ln["limited_quantity"])) for ln in lines]
    result = check_load(items)
    regulated = [i.sku for i in items if i.regulated]
    if regulated and not shp["hazmat_endorsed"]:
        result["findings"].append({
            "severity": "violation",
            "rule": "Fully regulated hazmat assigned to a carrier without hazmat endorsement",
            "citation": "SOP-HAZ-002 §4 step 4; SOP-OUT-002 §3.3",
            "items": regulated,
            "detail": f"{shp['carrier']} is not hazmat-endorsed. Reassign to an endorsed carrier.",
        })
        result["compliant"] = False
    return {"shipment": shp, "lines": lines, **result}


def carrier_on_time_rate(con, carrier_id: str, now: datetime) -> tuple[float | None, int]:
    since = (now - timedelta(days=LOOKBACK_DAYS)).strftime("%Y-%m-%d %H:%M")
    rows = con.execute(
        """SELECT planned_departure, actual_departure FROM shipments
           WHERE carrier_id = ? AND status = 'departed' AND planned_departure >= ?""",
        (carrier_id, since)).fetchall()
    if not rows:
        return None, 0
    fmt = "%Y-%m-%d %H:%M"
    on_time = sum(datetime.strptime(a, fmt) <= datetime.strptime(p, fmt)
                  + timedelta(minutes=ON_TIME_GRACE_MIN) for p, a in rows)
    return on_time / len(rows), len(rows)


@traceable(run_type="tool", name="assess_departure_risk")
def assess_departure_risk(shipment_id: str, db_path: Path = DC_DB_PATH, now: str = SIM_NOW) -> dict:
    """Is a planned shipment at risk of leaving late? Applies SOP-OUT-002 §3."""
    current = datetime.strptime(now, "%Y-%m-%d %H:%M")
    con = connect(db_path)
    try:
        shp = _shipment(con, shipment_id)
        if shp is None:
            return {"error": f"shipment {shipment_id} not found"}
        rate, n = carrier_on_time_rate(con, shp["carrier_id"], current)
    finally:
        con.close()
    if shp["status"] == "departed":
        return {"shipment": shp, "at_risk": False, "reasons": [],
                "note": "already departed", "citation": "SOP-OUT-002"}

    planned = datetime.strptime(shp["planned_departure"], "%Y-%m-%d %H:%M")
    reasons = []
    if not shp["trailer_id"] and planned.hour < EARLY_DEPARTURE_HOUR and planned - current < timedelta(hours=24):
        reasons.append({"rule": "No trailer assigned for an early departure (before 08:00)",
                        "citation": "SOP-OUT-002 §3.1"})
    if rate is not None and rate < ON_TIME_THRESHOLD:
        reasons.append({"rule": f"Carrier on-time rate {rate:.0%} over the last {LOOKBACK_DAYS} days "
                                f"is below {ON_TIME_THRESHOLD:.0%}",
                        "citation": "SOP-OUT-002 §3.2"})
    compliance = check_shipment_compliance(shipment_id, db_path)
    if any("endorsement" in f["rule"] for f in compliance.get("findings", [])):
        reasons.append({"rule": "Carrier not hazmat-endorsed for a fully regulated load "
                                "(compliance issue - reassign immediately)",
                        "citation": "SOP-OUT-002 §3.3"})
    return {
        "shipment": shp,
        "at_risk": bool(reasons),
        "reasons": reasons,
        "carrier_on_time_30d": None if rate is None else round(rate, 3),
        "carrier_departures_30d": n,
        "hours_until_departure": round((planned - current).total_seconds() / 3600, 1),
        "recommended_actions": [
            "Call the carrier to confirm trailer and driver ETA",
            "If not confirmed within 1 hour, book a backup carrier (hazmat-endorsed if needed)",
            "Notify the customer if the new ETA is more than 2 hours late",
        ] if reasons else [],
        "citation": "SOP-OUT-002 §3-4",
    }
