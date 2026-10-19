"""Application log, audit trail and search fallback - offline, with a fake LLM."""

import json

import httpx
import openai
import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from langchain_core.tools import tool

from copilot.agent import tools as agent_tools
from copilot.agent.graph import Copilot
from copilot.api.app import create_app
from copilot.logs import setup_logging
from copilot.tools import search
from fakes import ScriptedModel, call

QUESTION = "Is SHP-1 ok for the Lyon customer?"


@tool
def check_shipment_compliance(shipment_id: str) -> str:
    """Fake compliance tool."""
    return json.dumps({"compliant": True, "findings": []})


def read(path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_answer_and_tool_calls_are_logged_without_question_text(log_dir):
    setup_logging(console=False)
    cp = Copilot(model=ScriptedModel(script=[
        call("check_shipment_compliance", {"shipment_id": "SHP-1"}),
        AIMessage(content="Compliant.")]), tools=[check_shipment_compliance], schema="test")
    r = cp.ask(QUESTION)
    lines = read(log_dir / "app.jsonl")
    tool_line = next(x for x in lines if x["event"] == "tool.call")
    assert tool_line["tool"] == "check_shipment_compliance" and tool_line["status"] == "ok"
    assert tool_line["args"] == {"shipment_id": "SHP-1"} and tool_line["thread_id"] == r.thread_id
    answer = next(x for x in lines if x["event"] == "agent.answer")
    assert answer["tools"] == ["check_shipment_compliance"] and answer["status"] == "answered"
    assert answer["question_chars"] == len(QUESTION) and len(answer["question_sha"]) == 12
    assert "Lyon" not in (log_dir / "app.jsonl").read_text(encoding="utf-8")  # privacy


EMAIL = {"action_type": "email", "recipient": "Carrier", "subject": "Trailer?",
         "body": "Please confirm.", "reason": "No trailer"}


@pytest.fixture
def outbox(tmp_path, monkeypatch):
    monkeypatch.setattr(agent_tools, "OUTBOX_PATH", tmp_path / "outbox.jsonl")


def email_agent(final: str) -> Copilot:
    return Copilot(model=ScriptedModel(script=[call("propose_action", EMAIL), AIMessage(content=final)]),
                   tools=[agent_tools.propose_action], schema="test")


def test_approval_is_audited_and_long_args_are_shortened(log_dir, outbox):
    setup_logging(console=False)
    cp = email_agent("Sent.")
    r = cp.resume(cp.ask("Email the carrier").thread_id, approved=True,
                  edited_body="Please confirm today.", approver="supervisor")
    [entry] = read(log_dir / "audit.jsonl")
    assert entry["event"] == "action.approved" and entry["approver"] == "supervisor"
    assert entry["recipient"] == "Carrier" and entry["body_edited"] is True and entry["sent"] is True
    assert entry["thread_id"] == r.thread_id
    statuses = [x["status"] for x in read(log_dir / "app.jsonl") if x["event"] == "tool.call"]
    assert statuses == ["awaiting_approval", "ok"]  # paused, then completed after approval


def test_rejection_is_audited_even_without_setup_logging(log_dir, outbox):
    cp = email_agent("Not sent.")
    cp.resume(cp.ask("Email the carrier").thread_id, approved=False, comment="wrong carrier")
    [entry] = read(log_dir / "audit.jsonl")
    assert entry["event"] == "action.rejected" and entry["comment"] == "wrong carrier"
    assert entry["sent"] is False and not (log_dir / "app.jsonl").exists()


def test_api_requests_are_logged_with_a_request_id(log_dir):
    cp = Copilot(model=ScriptedModel(script=[AIMessage(content="Hello.")]),
                 tools=[check_shipment_compliance], schema="test")
    with TestClient(create_app(cp)) as c:
        res = c.post("/ask", json={"question": "hi"})
        assert c.post("/ask", json={"question": ""}).status_code == 422
    body = res.json()
    assert body["guardrail_flags"] == [] and body["run_id"] is None  # tracing is off in tests
    requests = [x for x in read(log_dir / "app.jsonl") if x["event"] == "api.request"]
    assert [(x["path"], x["status"]) for x in requests] == [("/ask", 200), ("/ask", 422)]
    assert requests[0]["request_id"] == res.headers["X-Request-ID"]
    assert requests[1]["level"] == "WARNING"


class FlakyRetriever:
    """Vector search fails like an exhausted OpenAI account; keyword search works."""

    def search(self, query, k, mode, where):
        if mode != "bm25":
            raise openai.RateLimitError(
                "no credits", body=None,
                response=httpx.Response(429, request=httpx.Request("POST", "https://x")))
        return []


def test_search_falls_back_to_keywords_when_embeddings_fail(log_dir, monkeypatch):
    setup_logging(console=False)
    monkeypatch.setattr(search, "_instance", FlakyRetriever())
    result = search.search_documents("forklift operator training")
    assert result["mode"].startswith("bm25 (fallback")
    assert any(x["event"] == "search.fallback" for x in read(log_dir / "app.jsonl"))
