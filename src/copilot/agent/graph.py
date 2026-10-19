"""The agent graph and a small runner around it.

    START -> agent --(tool calls?)--> tools -> agent -> ... -> END
                 \\--(no tool calls)--> END

`agent` is the LLM with the tools bound; `tools` executes the requested calls. When
`propose_action` runs, LangGraph `interrupt()` pauses the graph; the checkpointer keeps
the conversation so `Copilot.resume()` can continue after a human approves or rejects.
"""

import hashlib
import json
import logging
import re
import threading
import time
import unicodedata
import uuid
from dataclasses import dataclass, field

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.errors import GraphBubbleUp
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.types import Command
from langsmith.run_helpers import get_current_run_tree

from copilot import __version__
from copilot.agent import guardrails
from copilot.agent.prompts import SYSTEM_PROMPT
from copilot.agent.tools import TOOLS
from copilot.config import settings
from copilot.logs import audit, log_event
from copilot.observability import setup_tracing, traceable, tracing_enabled
from copilot.tools.sql import describe_schema

RECURSION_LIMIT = 25  # max graph steps per question (each tool round trip = 2 steps)
CITATION_CHECK = "citation_check"  # name marking automatic citation-correction messages
_CITATION = re.compile(r"\[([^\[\]]{3,80})\]")
# only bracketed text that looks like a source reference counts as a citation
_LOOKS_LIKE_CITATION = re.compile(r"CFR|SOP-|SDS-|INC-|GS1|DB:|§")


def make_chat_model() -> BaseChatModel:
    if settings.llm_provider == "azure":
        from langchain_openai import AzureChatOpenAI

        return AzureChatOpenAI(
            azure_deployment=settings.azure_openai_chat_deployment,
            api_key=settings.azure_openai_api_key,
            azure_endpoint=settings.azure_openai_endpoint,
            api_version=settings.azure_openai_api_version,
        )
    from langchain_openai import ChatOpenAI

    if not settings.openai_api_key:
        raise SystemExit("OPENAI_API_KEY is not set in .env")
    return ChatOpenAI(
        model=settings.chat_model,
        api_key=settings.openai_api_key,
        use_responses_api=True,  # required for tools + reasoning on GPT-5.x models
        reasoning={"effort": settings.reasoning_effort},
    )


def build_graph(model: BaseChatModel, tools=TOOLS, checkpointer=None, schema: str | None = None):
    system = SystemMessage(SYSTEM_PROMPT.replace("{schema}", schema or describe_schema()))
    llm = model.bind_tools(tools)

    def agent(state: MessagesState) -> dict:
        return {"messages": [llm.invoke([system, *state["messages"]])]}

    g = StateGraph(MessagesState)
    g.add_node("agent", agent)
    g.add_node("tools", ToolNode(tools))
    g.add_edge(START, "agent")
    g.add_conditional_edges("agent", tools_condition)  # -> "tools" or END
    g.add_edge("tools", "agent")
    return g.compile(checkpointer=checkpointer or InMemorySaver())


def _loggable(args: dict) -> dict:
    """Tool arguments for the app log: identifiers as they are, free text (search queries,
    SQL, email bodies) only as its length - the full text is in the LangSmith trace."""
    return {k: v if not isinstance(v, str) or len(v) <= 40 else f"<{len(v)} chars>"
            for k, v in args.items()}


class ToolCallLogger(BaseCallbackHandler):
    """Logs every tool call (name, arguments, duration, outcome) to the app log.
    Tools run in parallel threads, so start times are kept per run id under a lock."""

    def __init__(self, thread_id: str):
        self.thread_id = thread_id
        self._started: dict = {}
        self._lock = threading.Lock()

    def on_tool_start(self, serialized, input_str, *, run_id, inputs=None, **kwargs):
        with self._lock:
            self._started[run_id] = (serialized.get("name", "?"), inputs or {}, time.perf_counter())

    def _done(self, run_id, status: str, level: int = logging.INFO) -> None:
        with self._lock:
            name, args, start = self._started.pop(run_id, ("?", {}, time.perf_counter()))
        log_event("tool.call", level, thread_id=self.thread_id, tool=name, args=_loggable(args),
                  status=status, duration_ms=round((time.perf_counter() - start) * 1000))

    def on_tool_end(self, output, *, run_id, **kwargs):
        text = str(getattr(output, "content", output))
        self._done(run_id, "error" if text.startswith('{"error"') else "ok")

    def on_tool_error(self, error, *, run_id, **kwargs):
        if isinstance(error, GraphBubbleUp):  # propose_action pausing for human approval
            self._done(run_id, "awaiting_approval")
        else:
            self._done(run_id, f"exception:{type(error).__name__}", logging.WARNING)


@dataclass
class AgentResult:
    thread_id: str
    answer: str | None
    tool_calls: list[dict] = field(default_factory=list)
    citations: list[str] = field(default_factory=list)
    unverified_citations: list[str] = field(default_factory=list)
    pending_action: dict | None = None
    citation_retries: int = 0  # answers rewritten by the answer check (citations, guardrails)
    available_citations: list[str] = field(default_factory=list)
    foreign_words: list[str] = field(default_factory=list)
    usage: dict = field(default_factory=dict)  # LLM tokens used in this turn
    guardrail_flags: list[str] = field(default_factory=list)  # see copilot.agent.guardrails
    action_sent: bool = False  # a proposed action was approved and sent in this turn
    run_id: str | None = None  # LangSmith trace id (None when tracing is off)


def _text(msg: AIMessage) -> str:
    return str(msg.text)  # .text is a str property in langchain-core 1.x


def check_citations(answer: str, tool_texts: list[str]) -> tuple[list[str], list[str]]:
    """Citations in the answer, and those that never appeared in any tool result."""
    parts = (p.strip() for c in _CITATION.findall(answer) for p in c.split(";"))
    cited = list(dict.fromkeys(p for p in parts if p and _LOOKS_LIKE_CITATION.search(p)))
    haystack = "\n".join(tool_texts)
    unverified = [c for c in cited if not c.startswith("DB:") and c not in haystack]
    return cited, unverified


def available_citations(tool_texts: list[str]) -> list[str]:
    """Every citation string the tools actually returned in this turn."""
    found = []
    for t in tool_texts:
        found += re.findall(r'"citation": "([^"]+)"', t)
    return list(dict.fromkeys(found))


def foreign_words(answer: str, question: str) -> list[str]:
    """Words in a non-Latin script when the question was written in Latin script
    (catches the occasional stray token from another language)."""
    def non_latin(word: str) -> bool:
        return any(ch.isalpha() and "LATIN" not in unicodedata.name(ch, "") for ch in word)

    if any(non_latin(w) for w in question.split()):
        return []  # user wrote in another script: answering in it is fine
    return list(dict.fromkeys(w.strip(".,;:!?*()") for w in answer.split() if non_latin(w)))


class Copilot:
    """Ask questions, and resume after an approval request."""

    def __init__(self, model: BaseChatModel | None = None, **graph_kwargs):
        setup_tracing()
        self.graph = build_graph(model or make_chat_model(), **graph_kwargs)

    def _config(self, thread_id: str) -> dict:
        return {"configurable": {"thread_id": thread_id}, "recursion_limit": RECURSION_LIMIT,
                "run_name": "copilot", "callbacks": [ToolCallLogger(thread_id)],
                "tags": [settings.chat_model, f"reasoning-{settings.reasoning_effort}"],
                "metadata": {"thread_id": thread_id, "app_version": __version__,
                             "chat_model": settings.chat_model,
                             "reasoning_effort": settings.reasoning_effort}}

    @staticmethod
    def _run_id() -> str | None:
        run = get_current_run_tree() if tracing_enabled() else None
        return str(run.id) if run else None

    @traceable(name="copilot.ask", run_type="chain")
    def ask(self, question: str, thread_id: str | None = None) -> AgentResult:
        thread_id = thread_id or uuid.uuid4().hex[:12]
        start = time.perf_counter()
        check = guardrails.check_input(question)
        if check.blocked:  # answered by code; the LLM never sees the request
            result = AgentResult(thread_id, check.reply, guardrail_flags=check.flags)
        else:
            self.graph.invoke({"messages": [HumanMessage(question)]}, self._config(thread_id))
            result = self._verified_result(thread_id)
            result.guardrail_flags = check.flags + result.guardrail_flags
        result.run_id = self._run_id()
        self._log_turn("agent.answer", result, start,
                       question_chars=len(question),
                       question_sha=hashlib.sha256(question.encode()).hexdigest()[:12])
        return result

    def thread_status(self, thread_id: str) -> str:
        """'unknown' (no such conversation), 'awaiting_approval' or 'idle'."""
        state = self.graph.get_state(self._config(thread_id))
        if not state.values.get("messages"):
            return "unknown"
        return "awaiting_approval" if state.interrupts else "idle"

    @traceable(name="copilot.resume", run_type="chain")
    def resume(self, thread_id: str, approved: bool, comment: str = "",
               edited_body: str | None = None, approver: str = "user") -> AgentResult:
        start = time.perf_counter()
        state = self.graph.get_state(self._config(thread_id))
        proposal = state.interrupts[0].value.get("proposal", {}) if state.interrupts else {}
        decision = {"approved": approved, "comment": comment, "edited_body": edited_body,
                    "approver": approver}
        self.graph.invoke(Command(resume=decision), self._config(thread_id))
        result = self._verified_result(thread_id)
        result.run_id = self._run_id()
        body = edited_body or proposal.get("body", "")
        audit(event="action.approved" if approved else "action.rejected", thread_id=thread_id,
              run_id=result.run_id, approver=approver, action_type=proposal.get("action_type"),
              recipient=proposal.get("recipient"), subject=proposal.get("subject"),
              body_edited=edited_body is not None and edited_body != proposal.get("body"),
              body_sha=hashlib.sha256(body.encode()).hexdigest()[:12], comment=comment,
              sent=result.action_sent)
        self._log_turn("agent.resume", result, start, approved=approved)
        return result

    @staticmethod
    def _log_turn(event: str, r: AgentResult, start: float, **extra) -> None:
        flags = r.guardrail_flags
        log_event(event, logging.WARNING if flags or r.unverified_citations else logging.INFO,
                  thread_id=r.thread_id, run_id=r.run_id,
                  status="awaiting_approval" if r.pending_action else "answered",
                  tools=[c["name"] for c in r.tool_calls], llm_calls=r.usage.get("llm_calls", 0),
                  tokens=r.usage.get("input_tokens", 0) + r.usage.get("output_tokens", 0),
                  latency_ms=round((time.perf_counter() - start) * 1000),
                  citations=len(r.citations), unverified_citations=len(r.unverified_citations),
                  rewritten=r.citation_retries, guardrail_flags=flags, **extra)

    def _verified_result(self, thread_id: str) -> AgentResult:
        """Answer check: if the answer cites sources no tool returned, contains stray words
        in another script, claims an unapproved message was sent or grants an exception,
        ask the model ONCE to rewrite it. Remaining problems are reported on the result
        (and shown to the user) rather than hidden; key-like strings are always redacted."""
        result = self._result(thread_id)
        if not result.answer:
            return result
        flags, problems = guardrails.output_problems(result.answer, result.action_sent)
        if result.unverified_citations:
            problems.append(
                f"These citations do not appear in any tool result: {result.unverified_citations}. "
                f"Valid citations from this turn's tools: {result.available_citations}. Use only "
                "those, copied exactly, or remove the claim.")
        if result.foreign_words:
            problems.append(f"Your answer contains non-English words {result.foreign_words}; "
                            "write it entirely in English.")
        if problems:
            note = "Answer check failed. " + " ".join(problems) + " Rewrite your previous answer."
            self.graph.invoke({"messages": [HumanMessage(note, name=CITATION_CHECK)]},
                              self._config(thread_id))
            result = self._result(thread_id)
            result.citation_retries = 1
            if result.answer:  # still wrong after the one rewrite: flag it, do not loop
                still, _ = guardrails.output_problems(result.answer, result.action_sent)
                flags += [f"{f}_after_rewrite" for f in still]
        result.guardrail_flags += flags
        if result.answer:
            result.answer, redacted = guardrails.redact_secrets(result.answer)
            if redacted:
                result.guardrail_flags.append("redacted_secret")
        return result

    def _result(self, thread_id: str) -> AgentResult:
        state = self.graph.get_state(self._config(thread_id))
        messages = state.values["messages"]
        # the turn starts at the user's question (citation-check notes are not new questions)
        last_human = max(i for i, m in enumerate(messages)
                         if isinstance(m, HumanMessage) and m.name != CITATION_CHECK)
        turn = messages[last_human:]
        calls = [{"name": c["name"], "args": c["args"]}
                 for m in turn if isinstance(m, AIMessage) for c in m.tool_calls]
        tool_msgs = [m for m in turn if isinstance(m, ToolMessage)]
        tool_texts = [m.content if isinstance(m.content, str) else json.dumps(m.content)
                      for m in tool_msgs]
        pending = None
        if state.interrupts:
            pending = state.interrupts[0].value.get("proposal")
            answer = None
        else:
            answer = _text(messages[-1])
        cited, unverified = check_citations(answer or "", tool_texts)
        question = str(messages[last_human].content)
        usage = {"input_tokens": 0, "output_tokens": 0, "llm_calls": 0}
        for m in turn:
            if isinstance(m, AIMessage) and m.usage_metadata:
                usage["input_tokens"] += m.usage_metadata.get("input_tokens", 0)
                usage["output_tokens"] += m.usage_metadata.get("output_tokens", 0)
                usage["llm_calls"] += 1
        sent = any('"status": "sent"' in t for t, m in zip(tool_texts, tool_msgs)
                   if m.name == "propose_action")
        flags = ["injection_in_tool_output"] if guardrails.injection_in_tool_output(tool_texts) else []
        return AgentResult(thread_id, answer, calls, cited, unverified, pending,
                           available_citations=available_citations(tool_texts),
                           foreign_words=foreign_words(answer or "", question), usage=usage,
                           guardrail_flags=flags, action_sent=sent)
