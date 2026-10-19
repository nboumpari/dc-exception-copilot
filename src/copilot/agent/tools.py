"""LangChain tool wrappers around copilot.tools, as the agent sees them.

The wrappers expose only what the LLM should control (no file paths), describe each tool
for the model, and cap the size of what comes back so one tool call cannot flood the
context window.
"""

import json
from datetime import datetime
from typing import Annotated, Literal

from langchain_core.tools import tool
from langgraph.types import interrupt

from copilot.agent.guardrails import blocked_recipient
from copilot.config import DATA_DIR
from copilot.logs import log_event
from copilot.tools.hazmat import lookup_hazmat as _lookup_hazmat
from copilot.tools.receipts import assess_inbound_receipt as _assess_inbound_receipt
from copilot.tools.search import read_source as _read_source
from copilot.tools.search import search_documents as _search_documents
from copilot.tools.shipments import assess_departure_risk as _assess_departure_risk
from copilot.tools.shipments import carrier_performance as _carrier_performance
from copilot.tools.shipments import check_shipment_compliance as _check_shipment_compliance
from copilot.tools.sql import sql_query as _sql_query

MAX_TOOL_CHARS = 12_000
OUTBOX_PATH = DATA_DIR / "outbox" / "actions.jsonl"


def _json(result) -> str:
    text = json.dumps(result, ensure_ascii=False, default=str)
    if len(text) > MAX_TOOL_CHARS:
        text = text[:MAX_TOOL_CHARS] + ' ... [truncated: narrow the query]'
    return text


@tool
def sql_query(query: Annotated[str, "One SQLite SELECT statement"]) -> str:
    """Query the warehouse database (shipments, receipts, inventory, SKUs, carriers,
    exceptions). Read-only: one SELECT per call, max 100 rows. Use it for any question about
    specific shipments, products, stock or past exceptions - never guess IDs or numbers."""
    return _json(_sql_query(query))


@tool
def check_shipment_compliance(shipment_id: Annotated[str, "e.g. SHP-01209"]) -> str:
    """Hazmat compliance check of one shipment: 49 CFR 177.848 segregation (limited
    quantities excluded), the calcium hypochlorite/TCCA rule and carrier hazmat endorsement.
    ALWAYS use this for hazmat questions about a shipment - do not judge it yourself."""
    return _json(_check_shipment_compliance(shipment_id))


@tool
def assess_departure_risk(shipment_id: Annotated[str, "e.g. SHP-01212"]) -> str:
    """Whether a planned shipment is at risk of departing late, per SOP-OUT-002 §3
    (trailer assignment, carrier 30-day on-time rate, hazmat endorsement)."""
    return _json(_assess_departure_risk(shipment_id))


@tool
def lookup_hazmat(
    un_number: Annotated[str | None, "UN/NA number, e.g. UN1950"] = None,
    name: Annotated[str | None, "part of a proper shipping name, e.g. 'hypochlorite'"] = None,
) -> str:
    """Look up the official 49 CFR 172.101 Hazardous Materials Table: hazard class, packing
    group, label codes, special provisions and quantity limits."""
    return _json(_lookup_hazmat(un_number=un_number, name=name))


@tool
def search_documents(
    query: Annotated[str, "what to look for, in plain words"],
    collection: Annotated[
        Literal["regulations", "dc_sops", "dc_sds", "dc_incidents"] | None,
        "regulations = OSHA/DOT/GS1 law and standards; dc_sops = OUR procedures; "
        "dc_sds = safety data sheets; dc_incidents = past incident reports; omit = all",
    ] = None,
) -> str:
    """Search the document corpus. Returns passages with exact citations to quote.
    For 'what do we do / what is our procedure' questions use collection='dc_sops'."""
    return _json(_search_documents(query, collection=collection))


@tool
def read_source(reference: Annotated[str, "a citation or document id from a search result, "
                                          "e.g. '29 CFR 1910.178(l)', 'SDS-NPRM', 'SOP-ESC-001'"]) -> str:
    """Read the FULL text of a source found by search_documents. Search returns short
    snippets; when the right source appears but the snippet lacks the exact detail, read it
    here before concluding the information is missing."""
    return _json(_read_source(reference))


@tool
def assess_inbound_receipt(receipt_id: Annotated[str, "e.g. RCV-00408 (find it with sql_query)"]) -> str:
    """Briefing for an inbound receipt: lines and hazmat, the supplier's label/exception
    history over 30 days, enhanced-inspection status and a receiving checklist with SOP
    citations. Use it for any 'what should receiving watch out for' question."""
    return _json(_assess_inbound_receipt(receipt_id))


@tool
def carrier_performance(days: Annotated[int, "look-back window in days"] = 30) -> str:
    """On-time departure rate of every carrier, using the official definition in
    SOP-OUT-002 (on time = departed <= 60 min after plan). Use this for any carrier
    reliability question instead of computing it with SQL."""
    return _json(_carrier_performance(days))


@tool
def propose_action(
    action_type: Annotated[Literal["email", "ticket"], "email to a partner, or an internal ticket"],
    recipient: Annotated[str, "who receives it, e.g. 'Cardinal Carriers dispatch'"],
    subject: Annotated[str, "short subject line"],
    body: Annotated[str, "full text to send"],
    reason: Annotated[str, "why this action is needed, with citations"],
) -> str:
    """Propose an outward action (email to a carrier/customer/supplier, or a ticket). A human
    must approve it before anything is sent. Never claim an action was sent unless this
    tool returns status 'sent'."""
    if personal := blocked_recipient(recipient):
        log_event("guardrail.recipient_blocked", 30, action_type=action_type)
        return _json({"status": "blocked", "error": (
            f"{personal} is a personal email address. Company data may only be sent to "
            "business partners' official addresses or internal teams. Do not retry; tell the "
            "user the request needs approval from the data owner.")})
    proposal = {"action_type": action_type, "recipient": recipient, "subject": subject,
                "body": body, "reason": reason}
    decision = interrupt({"type": "approval_request", "proposal": proposal})
    if not isinstance(decision, dict) or not decision.get("approved"):
        comment = decision.get("comment", "") if isinstance(decision, dict) else ""
        return _json({"status": "rejected", "comment": comment})
    record = {**proposal, "body": decision.get("edited_body") or body,
              "approved_by": decision.get("approver", "user"),
              "sent_at": datetime.now().isoformat(timespec="seconds"), "simulated": True}
    OUTBOX_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTBOX_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return _json({"status": "sent", "simulated": True, "outbox": str(OUTBOX_PATH.name)})


TOOLS = [sql_query, check_shipment_compliance, assess_departure_risk, assess_inbound_receipt,
         carrier_performance, lookup_hazmat, search_documents, read_source, propose_action]
