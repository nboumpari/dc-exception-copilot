"""Streamlit UI for the DC Exception Copilot.

Run (two terminals):
    uv run uvicorn copilot.api.app:app --port 8000
    uv run --group ui streamlit run src/copilot/ui/streamlit_app.py

The Chat tab talks to the agent only through the HTTP API (copilot.ui.client), like any
other client. The Evaluation tab reads the saved evaluation results.
"""

import json
import statistics

import altair as alt
import pandas as pd
import streamlit as st

from copilot.config import DATA_DIR
from copilot.ui.client import DEFAULT_URL, ApiError, CopilotClient

RESULTS_DIR = DATA_DIR / "eval" / "results"
BLUE, ORANGE, INK_2 = "#2a78d6", "#eb6834", "#52514e"
EXAMPLES = [
    "Is SHP-01209 OK to load tomorrow?",
    "Can SHP-01210 go out tomorrow?",
    "Check SHP-01211 before it leaves.",
    "Is SHP-01212 at risk of leaving late?",
    "What should receiving watch out for with tomorrow's inbound from Delta Copack?",
    "Email Cardinal Carriers to confirm the trailer for SHP-01212.",
]

st.set_page_config(page_title="DC Exception Copilot", page_icon=":package:", layout="wide")


# ---------- state ----------
def init_state() -> None:
    st.session_state.setdefault("messages", [])  # {"role", "content"} or {"role", "response"}
    st.session_state.setdefault("thread_id", None)
    st.session_state.setdefault("api_url", DEFAULT_URL)
    st.session_state.setdefault("api_key", "")


def client() -> CopilotClient:
    """One client per browser session (tests put a fake client here before running)."""
    if "client" not in st.session_state:
        st.session_state.client = CopilotClient(st.session_state.api_url,
                                                st.session_state.api_key or None)
    return st.session_state.client


def reset_client() -> None:
    st.session_state.pop("client", None)


def pending_message() -> dict | None:
    for m in st.session_state.messages:
        r = m.get("response") or {}
        if r.get("pending_action") and not m.get("decision"):
            return m
    return None


# ---------- sidebar ----------
def sidebar() -> None:
    with st.sidebar:
        st.header("DC Exception Copilot")
        st.caption("Agentic RAG for a fictional distribution center (DC-COL1).")
        try:
            h = client().health()
            st.success("API connected")
            st.caption(f"Model `{h['chat_model']}` · reasoning {h['reasoning_effort']}  \n"
                       f"Simulation time: {h['simulation_time']}")
        except ApiError as exc:
            st.error(str(exc))
        with st.expander("Connection"):
            st.text_input("API URL", key="api_url", on_change=reset_client)
            st.text_input("API key (if the server requires one)", key="api_key",
                          type="password", on_change=reset_client)
        if st.button("New conversation", width="stretch"):
            st.session_state.messages = []
            st.session_state.thread_id = None
            st.rerun()


# ---------- chat ----------
# what each guardrail flag from the API means for the person reading the answer
GUARDRAIL_NOTES = {
    "injection_suspected": "The question looked like an attempt to override the copilot's rules; "
                           "they still applied.",
    "injection_in_tool_output": "A record or document contained instructions aimed at the "
                                "assistant; they were treated as data and not followed.",
    "claimed_sent_after_rewrite": "The answer may claim a message was sent - nothing is sent "
                                  "without your approval.",
    "granted_exception_after_rewrite": "Only the EHS coordinator can approve exceptions, in "
                                       "writing.",
    "redacted_secret": "Something that looked like a secret key was removed from the answer.",
}


def render_response(r: dict) -> None:
    if r.get("answer"):
        st.markdown(r["answer"])  # Streamlit escapes HTML by default: quoted text stays inert
    if r.get("citations"):
        st.caption("Sources: " + " · ".join(r["citations"]))
    if r.get("unverified_citations"):
        st.warning("Could not verify: " + ", ".join(r["unverified_citations"]))
    notes = [GUARDRAIL_NOTES[f] for f in r.get("guardrail_flags", []) if f in GUARDRAIL_NOTES]
    if notes:
        st.info("Guardrail: " + " ".join(notes), icon="🛡️")
    if r.get("tool_calls"):
        with st.expander(f"Tools used ({len(r['tool_calls'])})"):
            for t in r["tool_calls"]:
                st.code(f"{t['name']}({json.dumps(t['args'], ensure_ascii=False)})", language=None)


def approval_form(message: dict, index: int) -> None:
    r = message["response"]
    p = r["pending_action"]
    with st.container(border=True):
        st.markdown(f"**Approval needed:** {p['action_type']} to **{p['recipient']}**")
        st.caption(f"Subject: {p['subject']}  \nReason: {p['reason']}")
        body = st.text_area("Message body (you can edit it before approving)", p["body"],
                            height=180, key=f"body-{index}")
        approve, reject = st.columns(2)
        decision = None
        if approve.button("Approve & send", type="primary", key=f"approve-{index}",
                          width="stretch"):
            decision = True
        if reject.button("Reject", key=f"reject-{index}", width="stretch"):
            decision = False
        if decision is None:
            return
        with st.spinner("Sending decision…"):
            try:
                follow = client().approve(r["thread_id"], decision,
                                          comment="" if decision else "Rejected in the UI",
                                          edited_body=body if decision and body != p["body"] else None)
            except ApiError as exc:
                st.error(str(exc))
                return
        message["decision"] = "approved" if decision else "rejected"
        st.session_state.messages.append({"role": "assistant", "response": follow})
        st.rerun()


def render_history() -> None:
    for i, m in enumerate(st.session_state.messages):
        with st.chat_message(m["role"]):
            if m["role"] == "user":
                st.markdown(m["content"])
            elif "error" in m:
                st.error(m["error"])
            else:
                render_response(m["response"])
                if m["response"].get("pending_action"):
                    if m.get("decision") == "approved":
                        st.success("Approved - sent (simulated).")
                    elif m.get("decision") == "rejected":
                        st.info("Rejected - nothing was sent.")
                    else:
                        approval_form(m, i)


def ask(question: str) -> None:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"), st.spinner("Checking data, rules and procedures…"):
        try:
            r = client().ask(question, st.session_state.thread_id)
            st.session_state.thread_id = r["thread_id"]
            st.session_state.messages.append({"role": "assistant", "response": r})
        except ApiError as exc:
            st.session_state.messages.append({"role": "assistant", "error": str(exc)})
    st.rerun()


def chat_tab() -> None:
    if not st.session_state.messages:
        st.markdown("Ask about shipments, hazmat compatibility, inbound receipts or procedures. "
                    "Try one of these:")
        cols = st.columns(2)
        for i, q in enumerate(EXAMPLES):
            if cols[i % 2].button(q, key=f"example-{i}", width="stretch"):
                st.session_state.queued = q
    render_history()
    waiting = pending_message() is not None
    question = st.chat_input("Approve or reject the proposed action first" if waiting
                             else "Ask about shipments, hazmat, procedures…", disabled=waiting)
    question = question or st.session_state.pop("queued", None)
    if question and not waiting:
        ask(question)


# ---------- evaluation ----------
def load(name: str) -> list | None:
    path = RESULTS_DIR / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def bar_chart(df: pd.DataFrame, x: str, y: str, color: str | None = None, sort=None,
              color_order: list[str] | None = None) -> alt.Chart:
    base = alt.Chart(df).encode(
        x=alt.X(f"{x}:Q", axis=alt.Axis(format="%", grid=True, title=None), scale=alt.Scale(domain=[0, 1])),
        y=alt.Y(f"{y}:N", sort=sort or "-x", title=None),
        tooltip=[y, alt.Tooltip(f"{x}:Q", format=".0%")] + ([color] if color else []),
    )
    if color:
        bars = base.mark_bar(cornerRadiusEnd=4, height=12).encode(
            color=alt.Color(f"{color}:N", sort=color_order,
                            scale=alt.Scale(domain=color_order, range=[BLUE, ORANGE]),
                            legend=alt.Legend(orient="top", title=None)),
            yOffset=alt.YOffset(f"{color}:N", sort=color_order))
    else:
        bars = base.mark_bar(cornerRadiusEnd=4, height=16, color=BLUE)
    labels = base.mark_text(align="left", dx=4, color=INK_2).encode(
        text=alt.Text(f"{x}:Q", format=".0%"),
        **({"yOffset": alt.YOffset(f"{color}:N", sort=color_order)} if color else {}))
    return (bars + labels).properties(height=alt.Step(30 if color else 26))


def evaluation_tab() -> None:
    agent = load("agent")
    retrieval = load("retrieval")
    if not agent and not retrieval:
        st.info("No evaluation results yet - run `python -m copilot.eval.agent_eval --repeats 3`.")
        return
    if agent:
        rows = pd.DataFrame(agent)
        tokens = [u.get("input_tokens", 0) + u.get("output_tokens", 0) for u in rows["usage"]]
        st.subheader("Agent: end-to-end answers")
        st.caption(f"{rows['id'].nunique()} test cases × {rows['repeat'].nunique()} runs, "
                   f"graded by code checks and an LLM judge (`{rows['judge'].dropna().iloc[0]}`).")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Pass rate", f"{rows['passed'].mean():.0%}")
        m2.metric("Judged correct",
                  f"{pd.DataFrame(rows['scores'].tolist())['judge_correct'].mean():.0%}")
        m3.metric("Valid citations",
                  f"{pd.DataFrame(rows['scores'].tolist())['citations_valid'].mean():.0%}")
        m4.metric("Median tokens / answer", f"{statistics.median(tokens):,.0f}")
        by_cat = rows.groupby("category")["passed"].mean().reset_index(name="pass_rate")
        st.markdown("**Pass rate by question category**")
        st.altair_chart(bar_chart(by_cat, "pass_rate", "category"), width="stretch")
        per_case = rows.groupby(["id", "question"])["passed"].agg(["sum", "count"]).reset_index()
        flaky = per_case[per_case["sum"] < per_case["count"]]
        if len(flaky):
            st.markdown("**Cases that did not pass every run**")
            st.dataframe(flaky.assign(passed=flaky["sum"].astype(str) + "/" + flaky["count"].astype(str))
                         [["id", "passed", "question"]], hide_index=True, width="stretch")
    if retrieval:
        st.subheader("Retrieval: does search find the right passage?")
        df = pd.DataFrame(retrieval)[["strategy", "mode", "hit@5"]]
        df["strategy"] = df["strategy"].map({"structured": "Structured chunks",
                                             "naive": "Naive chunks (LangChain)"})
        st.altair_chart(bar_chart(df, "hit@5", "mode", color="strategy",
                                  sort=["bm25", "vector", "hybrid"],
                                  color_order=["Structured chunks", "Naive chunks (LangChain)"]),
                        width="stretch")
        st.caption("Hit@5 = share of 42 test questions whose answer is in the top 5 results.")
    log = RESULTS_DIR / "experiments.md"
    if log.exists():
        with st.expander("Experiment log - how each improvement was measured"):
            st.markdown(log.read_text(encoding="utf-8"))


def main() -> None:
    init_state()
    sidebar()
    chat, evaluation = st.tabs(["Chat", "Evaluation"])
    with chat:
        chat_tab()
    with evaluation:
        evaluation_tab()


main()
