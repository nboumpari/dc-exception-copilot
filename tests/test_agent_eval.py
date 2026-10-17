"""The evaluator must be trustworthy: scoring logic and golden-set validity, offline."""

import json

import pytest

from copilot.agent.tools import TOOLS
from copilot.config import PROCESSED_DIR
from copilot.eval.agent_eval import code_scores, judged_text, load_cases, passed, report

CASE = {
    "id": "T1", "category": "shipment", "question": "Is SHP-1 ok?",
    "required_tools": ["check_shipment_compliance"],
    "required_citations": ["49 CFR 177.848(d)"],
    "must_mention": [["5.1"], ["separate", "split"]],
    "must_not_mention": ["was sent"],
    "reference": "No.",
}


def outcome(answer="", tools=(), citations=(), unverified=(), proposal=None) -> dict:
    return {"answer": answer, "tool_calls": [{"name": t, "args": {}} for t in tools],
            "citations": list(citations), "unverified_citations": list(unverified),
            "proposal": proposal}


def test_perfect_answer_passes_every_check():
    out = outcome("Not ok: **class 5.1** must be split [49 CFR 177.848(d)].",
                  tools=["check_shipment_compliance"], citations=["49 CFR 177.848(d)"])
    scores = code_scores(CASE, out)
    assert scores == {"tool_selection": 1.0, "required_citation": 1.0, "key_facts": 1.0,
                      "no_forbidden": 1.0, "citations_valid": 1.0, "action": 1.0}
    assert passed(scores)


def test_each_check_fails_independently():
    out = outcome("Class 5.1. The email was sent.", tools=["sql_query"],
                  citations=["SOP-X"], unverified=["SOP-X"],
                  proposal={"action_type": "email"})
    s = code_scores(CASE, out)
    assert s["tool_selection"] == 0 and s["required_citation"] == 0
    assert s["key_facts"] == 0.5  # mentions 5.1 but not separate/split
    assert s["no_forbidden"] == 0 and s["citations_valid"] == 0
    assert s["action"] == 0  # proposed an action that was not expected
    assert not passed(s)


def test_judge_sees_the_rejected_proposal():
    text = judged_text(outcome("Not sent.", proposal={
        "action_type": "email", "recipient": "Carrier", "subject": "S", "body": "Body text"}))
    assert "Not sent." in text and "rejected by the user in this test" in text
    assert "Body text" in text


def test_report_shows_pass_fraction_across_repeats():
    rows = [{"id": "A", "category": "c", "question": "q", "repeat": i, "passed": i != 1,
             "scores": {"k": float(i != 1)}, "judge_note": "", "usage": {}, "latency_s": 1,
             "citation_retries": 0} for i in range(3)]
    md = report(rows)
    assert "**Pass rate: 67%** (runs: 100%, 0%, 100%)" in md
    assert "**A** 2/3 passed" in md


# ---------- golden set validity ----------
def test_case_ids_are_unique():
    ids = [c["id"] for c in load_cases()]
    assert len(ids) == len(set(ids))


def test_required_tools_exist():
    names = {t.name for t in TOOLS}
    for c in load_cases():
        assert set(c.get("required_tools", [])) <= names, c["id"]


@pytest.mark.skipif(not (PROCESSED_DIR / "chunks.jsonl").exists(), reason="chunks not built")
def test_required_citations_exist_in_corpus_or_tools():
    corpus = {json.loads(line)["citation"]
              for line in (PROCESSED_DIR / "chunks.jsonl").open(encoding="utf-8")}
    from_tools = {"49 CFR 177.848(a)", "49 CFR 177.848(d)", "49 CFR 172.101",
                  "SOP-OUT-002 §3.1", "SOP-OUT-002 §3.2", "SOP-OUT-002 §3-4"}
    for c in load_cases():
        for cit in c.get("required_citations", []):
            assert cit in corpus | from_tools, f"{c['id']}: {cit}"


def test_every_case_has_a_reference_for_the_judge():
    assert all(c.get("reference") for c in load_cases())
