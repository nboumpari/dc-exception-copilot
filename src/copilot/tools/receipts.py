"""Inbound receipt briefing: what receiving should watch out for, decided in code.

Applies SOP-REC-001 (receiving) and SOP-REC-002 §6 (enhanced inspection): a supplier
with two or more label exceptions in a rolling 30-day window - or named in the SOP - is
on the enhanced inspection list. Evaluation showed the agent omitted the supplier's label
history in 7 of 10 runs when it had to assemble this from SQL itself.
"""

from datetime import datetime, timedelta
from pathlib import Path

from copilot.config import DC_DB_PATH
from copilot.observability import traceable
from copilot.synthetic.catalog import SIM_NOW
from copilot.tools.sql import connect

LABEL_EXCEPTIONS = ("MISSING_SSCC", "UNREADABLE_LABEL")
ENHANCED_THRESHOLD = 2  # label exceptions in the window (SOP-REC-001 §3.2, SOP-REC-002 §6)
WINDOW_DAYS = 30
NAMED_IN_SOP = {"S-014": "listed until further notice (SOP-REC-002 §6)"}


@traceable(run_type="tool", name="assess_inbound_receipt")
def assess_inbound_receipt(receipt_id: str, db_path: Path = DC_DB_PATH, now: str = SIM_NOW) -> dict:
    """Receipt details, the supplier's recent exception history, enhanced-inspection status
    and a receiving checklist with SOP citations."""
    since = (datetime.strptime(now, "%Y-%m-%d %H:%M") - timedelta(days=WINDOW_DAYS)).strftime(
        "%Y-%m-%d %H:%M")
    con = connect(db_path)
    try:
        row = con.execute(
            """SELECT r.receipt_id, r.asn_id, r.status, r.expected_at, r.door, r.pallets_expected,
                      s.supplier_id, s.name, s.type
               FROM inbound_receipts r JOIN suppliers s USING (supplier_id)
               WHERE r.receipt_id = ?""", (receipt_id,)).fetchone()
        if row is None:
            return {"error": f"receipt {receipt_id} not found"}
        receipt = dict(zip(["receipt_id", "asn_id", "status", "expected_at", "door",
                            "pallets_expected", "supplier_id", "supplier", "supplier_type"], row))
        lines = [dict(zip(["sku", "description", "cases_expected", "pallets", "hazard_class",
                           "un_number", "limited_quantity"], r)) for r in con.execute(
            """SELECT l.sku, k.description, l.cases_expected, l.pallets, k.hazard_class,
                      k.un_number, k.limited_quantity
               FROM receipt_lines l JOIN skus k USING (sku) WHERE l.receipt_id = ?""",
            (receipt_id,))]
        history = con.execute(
            """SELECT e.type, COUNT(*) FROM exceptions e
               JOIN inbound_receipts r ON r.receipt_id = e.reference_id
               WHERE e.reference_type = 'receipt' AND r.supplier_id = ? AND e.created_at >= ?
               GROUP BY e.type ORDER BY COUNT(*) DESC""",
            (receipt["supplier_id"], since)).fetchall()
        recent_label = [dict(zip(["exception_id", "type", "created_at", "receipt_id", "description"], r))
                        for r in con.execute(
            f"""SELECT e.exception_id, e.type, e.created_at, e.reference_id, e.description
               FROM exceptions e JOIN inbound_receipts r ON r.receipt_id = e.reference_id
               WHERE e.reference_type = 'receipt' AND r.supplier_id = ? AND e.created_at >= ?
                 AND e.type IN ({','.join('?' * len(LABEL_EXCEPTIONS))})
               ORDER BY e.created_at DESC LIMIT 5""",
            (receipt["supplier_id"], since, *LABEL_EXCEPTIONS))]
    finally:
        con.close()

    counts = dict(history)
    label_count = sum(counts.get(t, 0) for t in LABEL_EXCEPTIONS)
    reasons = []
    if label_count >= ENHANCED_THRESHOLD:
        reasons.append(f"{label_count} label exceptions in the last {WINDOW_DAYS} days "
                       f"(threshold {ENHANCED_THRESHOLD}, SOP-REC-001 §3.2; SOP-REC-002 §6)")
    if receipt["supplier_id"] in NAMED_IN_SOP:
        reasons.append(NAMED_IN_SOP[receipt["supplier_id"]])
    enhanced = bool(reasons)

    checklist = []
    if enhanced:
        checklist.append({
            "check": "Enhanced inspection: scan the SSCC of EVERY pallet; missing or unreadable "
                     "labels go to the zone D exception lane, never to putaway",
            "citation": "SOP-REC-002 §3-4"})
    hazmat = [ln for ln in lines if ln["hazard_class"]]
    if hazmat:
        checklist.append({"check": "Assign a hazmat-trained receiver",
                          "citation": "SOP-REC-001 §3"})
        checklist.append({"check": "Inspect the trailer for leaks, odor or damage before unloading; "
                                   "suspected leak -> stop and follow SOP-HAZ-004",
                          "citation": "SOP-REC-001 §4"})
    if any(ln["limited_quantity"] for ln in hazmat):
        checklist.append({"check": "Confirm the limited quantity mark is visible on every LQ "
                                   "overpack; log MISSING_HAZMAT_MARKING if not",
                          "citation": "SOP-HAZ-003 §4"})
    checklist.append({"check": "Receive the physical count and reconcile against the ASN",
                      "citation": "SOP-REC-001 §5"})

    return {
        "receipt": receipt,
        "lines": lines,
        "supplier_history_30d": {"label_exceptions": label_count, "by_type": counts,
                                 "recent_label_exceptions": recent_label},
        "enhanced_inspection": enhanced,
        "enhanced_inspection_reasons": reasons,
        "checklist": checklist,
        "citation": "SOP-REC-001; SOP-REC-002 §6",
    }
