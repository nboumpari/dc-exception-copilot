"""Exception types (the DC's 'playbook') and incident-report rendering.

Each exception type links to the SOP that governs it and to the real regulation
sections in the corpus, so incident reports, SOPs and regulations cross-reference.
"""

import random
from dataclasses import dataclass

from copilot.synthetic.catalog import DC


@dataclass(frozen=True)
class ExceptionType:
    title: str
    sop: str
    regulations: tuple[str, ...]
    root_causes: tuple[str, ...]
    actions: tuple[str, ...]


TYPES: dict[str, ExceptionType] = {
    "MISSING_SSCC": ExceptionType(
        "Inbound pallet(s) without SSCC barcode",
        "SOP-REC-002",
        ("GS1 Logistic Label Guideline", "GS1 General Specifications §2.2.1"),
        (
            "Supplier label printer ran out of ribbon mid-shift; pallets left the plant unlabeled.",
            "Supplier applied only a shipping label; logistic label step skipped during peak.",
            "Label applied to stretch-wrap and torn off during transit.",
            "Supplier's new WMS integration failed to generate SSCC numbers for split pallets.",
        ),
        (
            "Pallets quarantined at dock and relabeled with DC-generated SSCC after ASN reconciliation.",
            "Supplier quality notice issued; supplier asked for 8D corrective action report.",
            "Receiving lead verified case counts against ASN before relabeling.",
            "Added supplier to enhanced inbound inspection list for 30 days.",
        ),
    ),
    "UNREADABLE_LABEL": ExceptionType(
        "Inbound pallet label barcode unreadable",
        "SOP-REC-002",
        ("GS1 Logistic Label Guideline", "GS1 General Specifications §5.4"),
        (
            "Barcode printed with low contrast (worn print head).",
            "Label placed over a pallet wrap seam, causing wrinkles across the GS1-128 symbol.",
            "Label exposed to rain during trailer loading at origin; ink smeared.",
            "Barcode quiet zone violated by a supplier handwritten note.",
        ),
        (
            "SSCC keyed manually from human-readable text after two-person verification.",
            "Relabeled pallet with DC-printed GS1 logistic label.",
            "Shared GS1 label placement guidance with supplier.",
            "Barcode verifier grade logged and sent to supplier.",
        ),
    ),
    "DAMAGED_INBOUND": ExceptionType(
        "Damaged pallet on receipt",
        "SOP-REC-002",
        ("29 CFR 1910.176(b)",),
        (
            "Load shifted in transit due to missing load bars.",
            "Broken bottom deck board on supplier pallet.",
            "Pallet double-stacked at origin beyond rated load.",
        ),
        (
            "Damage photographed and noted on the bill of lading before driver release.",
            "Undamaged cases reworked onto a new pallet; damaged cases written off.",
            "Freight claim filed with carrier within 9 months as per terms.",
        ),
    ),
    "QTY_DISCREPANCY": ExceptionType(
        "Received quantity differs from ASN",
        "SOP-REC-001",
        (),
        (
            "Supplier shipped from wrong pick slot; case count short.",
            "ASN transmitted before final load was completed.",
            "Mixed pallet with two SKUs declared as one SKU.",
        ),
        (
            "Receipt adjusted to physical count; supplier notified with photos.",
            "Over-shipment held in dock staging pending purchase-order amendment.",
        ),
    ),
    "MISSING_HAZMAT_MARKING": ExceptionType(
        "Limited-quantity pallet missing LQ marking",
        "SOP-HAZ-003",
        ("49 CFR 172.315", "49 CFR 173.306"),
        (
            "Overpack stretch-wrap obscured the limited-quantity marks on the cases.",
            "Supplier omitted the LQ mark on the overpack.",
        ),
        (
            "Limited quantity mark applied to the outside of the overpack as required.",
            "Hazmat shipping clerk verified case markings before putaway.",
        ),
    ),
    "LATE_CARRIER": ExceptionType(
        "Outbound shipment departed late",
        "SOP-OUT-002",
        (),
        (
            "Carrier trailer arrived after the scheduled appointment.",
            "Driver hours-of-service limit reached; relief driver dispatched.",
            "Load not staged on time due to replenishment backlog in fast-pick.",
            "Carrier tractor breakdown en route to the DC.",
        ),
        (
            "Customer notified of the revised ETA by the transportation planner.",
            "Carrier scorecard updated; repeated late arrival escalated to carrier account manager.",
            "Load moved to backup carrier from the routing guide.",
        ),
    ),
    "HAZMAT_SEGREGATION": ExceptionType(
        "Incompatible hazmat classes planned on one trailer",
        "SOP-HAZ-002",
        ("49 CFR 177.848", "49 CFR 177.834"),
        (
            "Load plan combined two professional orders without running the segregation check.",
            "Order was amended after the load plan was released; check not re-run.",
            "New planner unaware that limited-quantity exception does not apply to bulk pails/drums.",
        ),
        (
            "Load re-planned: incompatible pallets moved to a second trailer.",
            (
                "Pallets separated within the trailer so commingling could not occur in a leak, "
                "with corrosive liquids not loaded above or adjacent to oxidizers."
            ),
            "Hazmat shipping clerk refresher briefing on 177.848 segregation table.",
        ),
    ),
    "LEAK_SPILL": ExceptionType(
        "Leaking hazardous material container",
        "SOP-HAZ-004",
        ("29 CFR 1910.1200", "49 CFR 177.834"),
        (
            "Container punctured by forklift tine during putaway.",
            "Cap not torqued at the filling line; slow leak during storage.",
            "Case crushed under an overloaded pallet in the rack above.",
        ),
        (
            "Area isolated, spill contained with the zone spill kit and absorbent per SDS section 6.",
            "Leaking pallet moved to quarantine zone Q; waste disposed via licensed contractor.",
            "EHS coordinator reviewed SDS and confirmed no reportable release.",
        ),
    ),
    "FORKLIFT_NEAR_MISS": ExceptionType(
        "Powered industrial truck near miss",
        "SOP-MHE-001",
        ("29 CFR 1910.178(l)", "29 CFR 1910.178(m)", "29 CFR 1910.176(a)"),
        (
            "Operator reversed without looking in the direction of travel.",
            "Pedestrian walked through a forklift-only aisle.",
            "Load raised while traveling; partial obstruction of view.",
            "Pallet staged in the aisle reduced clearance at an intersection.",
        ),
        (
            "Operator received refresher training and re-evaluation per 1910.178(l)(4).",
            "Aisle floor markings repainted and pedestrian barrier added.",
            "Toolbox talk on travel direction and horn use delivered to all shifts.",
        ),
    ),
    "INVENTORY_MISMATCH": ExceptionType(
        "Cycle count variance",
        "SOP-INV-001",
        (),
        (
            "Pallet put away to the wrong location (adjacent bay).",
            "Pick confirmed against wrong SKU variant.",
            "Unrecorded damage write-off.",
        ),
        (
            "Recount by a second counter confirmed the variance; system adjusted.",
            "Misplaced pallet located and moved to its system location.",
        ),
    ),
    "QUALITY_HOLD": ExceptionType(
        "Lot placed on quality hold",
        "SOP-QA-001",
        (),
        (
            "Plant reported a fill-weight deviation on the lot.",
            "Customer complaint about leaking caps from this lot.",
            "Missing batch release certificate.",
        ),
        (
            "All pallets of the lot blocked in the WMS and moved to quarantine zone Q.",
            "Open orders reallocated to an unaffected lot.",
        ),
    ),
}


SEVERITY_WORDS = {"low": "Low", "medium": "Medium", "high": "High"}


def render_incident(exc: dict, rng: random.Random) -> str:
    """Markdown incident report for one exception row (dict from the exceptions table)."""
    t = TYPES[exc["type"]]
    regs = ", ".join(t.regulations) if t.regulations else "n/a"
    timeline = [
        (
            f"- **{exc['created_at']}** - Exception detected and logged "
            f"({exc['reference_type']} {exc['reference_id']})."
        ),
        f"- **{exc['created_at']}** - {exc['owner_name']} ({exc['owner_role']}) assigned as owner.",
    ]
    if exc["resolved_at"]:
        timeline.append(f"- **{exc['resolved_at']}** - Corrective action completed; exception closed.")
    else:
        timeline.append("- Exception still **open** at time of writing.")
    lessons = rng.choice(
        (
            "Check the governing SOP step before improvising a fix.",
            "Earlier escalation would have reduced the impact.",
            "The issue was caught by the control designed for it; no change to the control needed.",
            "Recurring pattern for this partner; tracked in the monthly partner review.",
        )
    )
    return f"""---
doc_id: {exc['incident_report_id']}
doc_type: incident_report
title: "{exc['incident_report_id']} - {t.title}"
exception_id: {exc['exception_id']}
exception_type: {exc['type']}
severity: {exc['severity']}
status: {exc['status']}
sku: {exc['sku'] or ''}
zone: {exc['zone'] or ''}
sop: {t.sop}
synthetic: true
---

# {exc['incident_report_id']} - {t.title}

**Site:** {DC['name']} ({DC['code']})
**Exception:** {exc['exception_id']} | **Severity:** {SEVERITY_WORDS[exc['severity']]} | **Status:** {exc['status']}
**Reference:** {exc['reference_type']} {exc['reference_id']}{f" | **SKU:** {exc['sku']}" if exc['sku'] else ''}{f" | **Zone:** {exc['zone']}" if exc['zone'] else ''}

## Summary
{exc['description']}

## Timeline
{chr(10).join(timeline)}

## Root cause
{exc['root_cause']}

## Corrective and preventive actions{' (planned - not yet completed)' if exc['status'] == 'open' else ''}
{exc['corrective_action']}

## References
- Governing procedure: {t.sop}
- Regulations / standards: {regs}

## Lessons learned
{lessons}

*Synthetic record generated for the DC Exception Copilot project. All names are fictional.*
"""
