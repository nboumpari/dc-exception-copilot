"""HTTP API tests: the real FastAPI app around an agent driven by a scripted fake model."""

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
from copilot.config import settings
from fakes import ScriptedModel, call


@tool
def check_shipment_compliance(shipment_id: str) -> str:
    """Fake compliance tool."""
    return json.dumps({"compliant": False, "findings": [{"citation": "49 CFR 177.848(d)"}]})


EMAIL = {"action_type": "email", "recipient": "Cardinal Carriers", "subject": "Trailer?",
         "body": "Please confirm the trailer.", "reason": "No trailer [SOP-OUT-002 §3.1]"}


def client_for(script: list, raise_errors: bool = True) -> TestClient:
    copilot = Copilot(model=ScriptedModel(script=script),
                      tools=[check_shipment_compliance, agent_tools.propose_action],
                      schema="test schema")
    return TestClient(create_app(copilot), raise_server_exceptions=raise_errors)


@pytest.fixture(autouse=True)
def outbox(tmp_path, monkeypatch):
    path = tmp_path / "outbox.jsonl"
    monkeypatch.setattr(agent_tools, "OUTBOX_PATH", path)
    return path


def test_health_reports_config_without_secrets():
    with client_for([]) as c:
        body = c.get("/health").json()
    assert body["status"] == "ok" and "chat_model" in body
    assert not any("key" in k and k != "auth_required" for k in body)


def test_ask_returns_answer_with_citations_and_tools():
    with client_for([call("check_shipment_compliance", {"shipment_id": "SHP-1"}),
                     AIMessage(content="Not compliant [49 CFR 177.848(d)].")]) as c:
        r = c.post("/ask", json={"question": "Is SHP-1 ok?"})
    body = r.json()
    assert r.status_code == 200 and body["status"] == "answered"
    assert body["citations"] == ["49 CFR 177.848(d)"]
    assert body["tool_calls"][0]["name"] == "check_shipment_compliance"


def test_ask_validates_input():
    with client_for([]) as c:
        assert c.post("/ask", json={"question": ""}).status_code == 422
        assert c.post("/ask", json={}).status_code == 422


def test_approval_flow_over_http(outbox):
    with client_for([call("propose_action", EMAIL), AIMessage(content="Email sent.")]) as c:
        r = c.post("/ask", json={"question": "Email the carrier"}).json()
        tid = r["thread_id"]
        assert r["status"] == "awaiting_approval" and r["pending_action"]["recipient"] == "Cardinal Carriers"
        assert c.get(f"/threads/{tid}").json()["status"] == "awaiting_approval"
        assert not outbox.exists()
        # cannot ask something new while a decision is pending
        assert c.post("/ask", json={"question": "hi", "thread_id": tid}).status_code == 409
        done = c.post(f"/threads/{tid}/approve",
                      json={"approved": True, "edited_body": "Edited.", "approver": "tester"}).json()
        assert done["status"] == "answered" and done["answer"] == "Email sent."
        # approving twice is refused
        assert c.post(f"/threads/{tid}/approve", json={"approved": True}).status_code == 409
    record = json.loads(outbox.read_text(encoding="utf-8"))
    assert record["body"] == "Edited." and record["approved_by"] == "tester"


def test_rejection_sends_nothing(outbox):
    with client_for([call("propose_action", EMAIL), AIMessage(content="Not sent.")]) as c:
        tid = c.post("/ask", json={"question": "Email the carrier"}).json()["thread_id"]
        r = c.post(f"/threads/{tid}/approve", json={"approved": False, "comment": "no"})
    assert r.json()["answer"] == "Not sent." and not outbox.exists()


def test_unknown_thread_is_404():
    with client_for([]) as c:
        assert c.get("/threads/nope").status_code == 404
        assert c.post("/threads/nope/approve", json={"approved": True}).status_code == 404


def test_api_key_is_enforced_when_configured(monkeypatch):
    monkeypatch.setattr(settings, "api_key", "secret-123")
    with client_for([AIMessage(content="ok")]) as c:
        assert c.post("/ask", json={"question": "hi"}).status_code == 401
        assert c.post("/ask", json={"question": "hi"},
                      headers={"X-API-Key": "wrong"}).status_code == 401
        assert c.get("/health").status_code == 200  # monitoring stays open
        r = c.post("/ask", json={"question": "hi"}, headers={"X-API-Key": "secret-123"})
    assert r.status_code == 200


def test_root_redirects_to_api_docs():
    with client_for([]) as c:
        r = c.get("/", follow_redirects=False)
    assert r.status_code in (302, 307) and r.headers["location"] == "/docs"


def test_llm_out_of_credits_returns_clear_503():
    no_credits = openai.RateLimitError(
        "You have no credits remaining.",
        response=httpx.Response(429, request=httpx.Request("POST", "https://api.openai.com")),
        body={"error": {"code": "credit_balance_exhausted"}})
    with client_for([no_credits]) as c:
        r = c.post("/ask", json={"question": "Is SHP-1 ok?"})
    assert r.status_code == 503 and "credits" in r.json()["detail"]


def test_unexpected_errors_return_json_without_internals():
    with client_for([RuntimeError("secret internal detail")], raise_errors=False) as c:
        r = c.post("/ask", json={"question": "Is SHP-1 ok?"})
    assert r.status_code == 500 and r.json() == {"detail": "Internal error - see server logs."}
