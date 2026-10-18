"""Streamlit UI tests: the API client against the real app, and the Streamlit script via
AppTest (runs the app headless, clicks buttons in code) with a stub client."""

import json

import httpx
import openai
import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from copilot.agent import tools as agent_tools
from copilot.agent.graph import Copilot
from copilot.api.app import create_app
from copilot.config import PROJECT_ROOT
from copilot.ui.client import ApiError, CopilotClient
from fakes import ScriptedModel, call

APP = str(PROJECT_ROOT / "src" / "copilot" / "ui" / "streamlit_app.py")
EMAIL = {"action_type": "email", "recipient": "Cardinal Carriers", "subject": "Trailer?",
         "body": "Please confirm the trailer.", "reason": "No trailer [SOP-OUT-002 §3.1]"}


# ---------- API client against the real FastAPI app ----------
def api_client(script: list, tmp_path, monkeypatch) -> CopilotClient:
    monkeypatch.setattr(agent_tools, "OUTBOX_PATH", tmp_path / "outbox.jsonl")
    cp = Copilot(model=ScriptedModel(script=script), tools=[agent_tools.propose_action],
                 schema="test schema")
    test_client = TestClient(create_app(cp))
    test_client.__enter__()  # run the app's startup
    return CopilotClient(http=test_client)


def test_client_ask_and_approve_round_trip(tmp_path, monkeypatch):
    c = api_client([call("propose_action", EMAIL), AIMessage(content="Sent.")], tmp_path, monkeypatch)
    r = c.ask("Email the carrier")
    assert r["status"] == "awaiting_approval"
    done = c.approve(r["thread_id"], True, edited_body="Edited.")
    assert done["answer"] == "Sent."
    sent = json.loads((tmp_path / "outbox.jsonl").read_text(encoding="utf-8"))
    assert sent["body"] == "Edited." and sent["approved_by"] == "streamlit user"


def test_client_turns_api_errors_into_readable_messages(tmp_path, monkeypatch):
    no_credits = openai.RateLimitError(
        "no credits", response=httpx.Response(429, request=httpx.Request("POST", "https://x")),
        body=None)
    c = api_client([no_credits], tmp_path, monkeypatch)
    with pytest.raises(ApiError) as err:
        c.ask("hi")
    assert err.value.status == 503 and "credits" in str(err.value)


def test_client_reports_unreachable_server():
    c = CopilotClient("http://127.0.0.1:9")  # nothing listens on port 9
    with pytest.raises(ApiError, match="Cannot reach the API"):
        c.health()


# ---------- Streamlit app with a stub client ----------
class StubClient:
    def __init__(self, ask_response: dict, approve_response: dict | None = None):
        self.ask_response, self.approve_response = ask_response, approve_response
        self.approved = None

    def health(self):
        return {"chat_model": "stub", "reasoning_effort": "medium",
                "simulation_time": "2026-10-16 18:00"}

    def ask(self, question, thread_id=None):
        return self.ask_response

    def approve(self, thread_id, approved, comment="", edited_body=None, approver=""):
        self.approved = approved
        return self.approve_response


def response(answer=None, pending=None) -> dict:
    return {"thread_id": "t1", "status": "awaiting_approval" if pending else "answered",
            "answer": answer, "citations": ["49 CFR 177.848(d)"] if answer else [],
            "unverified_citations": [], "tool_calls": [{"name": "check_shipment_compliance",
                                                        "args": {"shipment_id": "SHP-01209"}}],
            "pending_action": pending, "usage": {}}


@pytest.fixture
def app_test():
    at_module = pytest.importorskip("streamlit.testing.v1")
    return lambda stub: _run(at_module.AppTest.from_file(APP, default_timeout=30), stub)


def _run(at, stub):
    at.session_state["client"] = stub
    return at.run()


def test_app_renders_without_errors(app_test):
    at = app_test(StubClient(response("ok")))
    assert not at.exception
    assert any("API connected" in s.value for s in at.success)


def test_example_question_shows_cited_answer(app_test):
    at = app_test(StubClient(response("**Not compliant** [49 CFR 177.848(d)]")))
    at.button(key="example-0").click().run()
    assert not at.exception
    assert any("Not compliant" in m.value for m in at.markdown)
    assert any("49 CFR 177.848(d)" in c.value for c in at.caption)


def test_proposed_email_needs_approval_and_blocks_new_questions(app_test):
    stub = StubClient(response(pending=EMAIL), response("Email sent (simulated)."))
    at = app_test(stub)
    at.button(key="example-5").click().run()
    assert at.chat_input[0].disabled  # no new questions while a decision is pending
    assert at.text_area[0].value == "Please confirm the trailer."
    at.button(key="approve-1").click().run()
    assert not at.exception and stub.approved is True
    assert any("Approved" in s.value for s in at.success)
    assert any("Email sent" in m.value for m in at.markdown)
    assert not at.chat_input[0].disabled


def test_evaluation_tab_renders(app_test):
    at = app_test(StubClient(response("ok")))
    assert not at.exception
    assert any(m.label == "Pass rate" for m in at.metric) or any(
        "No evaluation results" in i.value for i in at.info)
