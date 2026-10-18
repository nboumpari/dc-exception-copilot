"""Agent graph tests with a scripted fake LLM - no API calls, deterministic."""

import json

import pytest
from langchain_core.messages import AIMessage
from langchain_core.tools import tool

from copilot.agent import tools as agent_tools
from copilot.agent.graph import (
    CITATION_CHECK,
    Copilot,
    available_citations,
    check_citations,
    foreign_words,
)
from fakes import ScriptedModel, call


@tool
def check_shipment_compliance(shipment_id: str) -> str:
    """Fake compliance tool."""
    return json.dumps({"compliant": False, "findings": [
        {"severity": "violation", "citation": "49 CFR 177.848(d)", "rule": "5.1 + 8"}]})


def copilot(script: list, tools=None) -> tuple[Copilot, ScriptedModel]:
    model = ScriptedModel(script=script, seen=[])
    return Copilot(model=model, tools=tools or [check_shipment_compliance],
                   schema="test schema"), model


def test_agent_calls_tool_then_answers_with_verified_citation():
    cp, _ = copilot([
        call("check_shipment_compliance", {"shipment_id": "SHP-1"}),
        AIMessage(content="Not compliant [49 CFR 177.848(d)]."),
    ])
    r = cp.ask("Is SHP-1 ok?")
    assert r.tool_calls == [{"name": "check_shipment_compliance", "args": {"shipment_id": "SHP-1"}}]
    assert r.citations == ["49 CFR 177.848(d)"] and r.unverified_citations == []
    assert r.citation_retries == 0


def test_invented_citation_triggers_one_rewrite_with_valid_options():
    cp, model = copilot([
        call("check_shipment_compliance", {"shipment_id": "SHP-1"}),
        AIMessage(content="Not compliant [SOP-XYZ-999 §1]."),       # invented
        AIMessage(content="Not compliant [49 CFR 177.848(d)]."),    # after the check note
    ])
    r = cp.ask("Is SHP-1 ok?")
    assert r.citation_retries == 1 and r.unverified_citations == []
    note = model.seen[-1][-1]
    assert note.name == CITATION_CHECK and "49 CFR 177.848(d)" in note.content
    assert r.tool_calls  # the turn still includes the original tool call


@pytest.fixture
def outbox(tmp_path, monkeypatch):
    path = tmp_path / "outbox.jsonl"
    monkeypatch.setattr(agent_tools, "OUTBOX_PATH", path)
    return path


EMAIL = {"action_type": "email", "recipient": "Carrier", "subject": "Trailer?",
         "body": "Please confirm the trailer.", "reason": "No trailer [SOP-OUT-002 §3.1]"}


def test_action_pauses_for_approval_and_sends_only_after_yes(outbox):
    cp, _ = copilot([call("propose_action", EMAIL), AIMessage(content="Email sent.")],
                    tools=[agent_tools.propose_action])
    r = cp.ask("Email the carrier")
    assert r.answer is None and r.pending_action["recipient"] == "Carrier"
    assert not outbox.exists()  # nothing sent while waiting
    r = cp.resume(r.thread_id, approved=True, approver="tester")
    assert r.answer == "Email sent."
    record = json.loads(outbox.read_text(encoding="utf-8"))
    assert record["approved_by"] == "tester" and record["simulated"] is True


def test_rejected_action_is_never_sent(outbox):
    cp, model = copilot([call("propose_action", EMAIL), AIMessage(content="Okay, not sent.")],
                        tools=[agent_tools.propose_action])
    r = cp.resume(cp.ask("Email the carrier").thread_id, approved=False, comment="no")
    assert r.answer == "Okay, not sent." and not outbox.exists()
    tool_reply = model.seen[-1][-1]
    assert '"status": "rejected"' in tool_reply.content


def test_edited_body_is_what_gets_sent(outbox):
    cp, _ = copilot([call("propose_action", EMAIL), AIMessage(content="Sent.")],
                    tools=[agent_tools.propose_action])
    r = cp.ask("Email the carrier")
    cp.resume(r.thread_id, approved=True, edited_body="Edited text.")
    assert json.loads(outbox.read_text(encoding="utf-8"))["body"] == "Edited text."


# ---------- guardrail helpers ----------
def test_citation_parsing_splits_and_ignores_non_citations():
    answer = "A [49 CFR 177.848(d); SOP-HAZ-002 §3] B [Your Name] C [DB: shipments] D [SDS-X §9]"
    cited, unverified = check_citations(answer, ['"citation": "49 CFR 177.848(d); SOP-HAZ-002 §3"'])
    assert cited == ["49 CFR 177.848(d)", "SOP-HAZ-002 §3", "DB: shipments", "SDS-X §9"]
    assert unverified == ["SDS-X §9"]


def test_available_citations_reads_tool_json():
    texts = ['{"citation": "SOP-OUT-002 §3.1"}', '{"results": [{"citation": "SDS-BLCC §1-8"}]}']
    assert available_citations(texts) == ["SOP-OUT-002 §3.1", "SDS-BLCC §1-8"]


def test_foreign_words_flagged_only_for_latin_questions():
    assert foreign_words("Do this հիմա, now.", "What now?") == ["հիմա"]
    assert foreign_words("Café naïve résumé.", "What now?") == []          # accented Latin is fine
    assert foreign_words("Καλημέρα", "Τι κάνω τώρα;") == []                 # user wrote Greek
