"""The agent graph and a small runner around it.

    START -> agent --(tool calls?)--> tools -> agent -> ... -> END
                 \\--(no tool calls)--> END

`agent` is the LLM with the tools bound; `tools` executes the requested calls. When
`propose_action` runs, LangGraph `interrupt()` pauses the graph; the checkpointer keeps
the conversation so `Copilot.resume()` can continue after a human approves or rejects.
"""

import json
import re
import unicodedata
import uuid
from dataclasses import dataclass, field

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.types import Command

from copilot.agent.prompts import SYSTEM_PROMPT
from copilot.agent.tools import TOOLS
from copilot.config import settings
from copilot.observability import setup_tracing, traceable
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


@dataclass
class AgentResult:
    thread_id: str
    answer: str | None
    tool_calls: list[dict] = field(default_factory=list)
    citations: list[str] = field(default_factory=list)
    unverified_citations: list[str] = field(default_factory=list)
    pending_action: dict | None = None
    citation_retries: int = 0
    available_citations: list[str] = field(default_factory=list)
    foreign_words: list[str] = field(default_factory=list)


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
                "run_name": "copilot", "metadata": {"thread_id": thread_id}}

    @traceable(name="copilot.ask", run_type="chain")
    def ask(self, question: str, thread_id: str | None = None) -> AgentResult:
        thread_id = thread_id or uuid.uuid4().hex[:12]
        self.graph.invoke({"messages": [HumanMessage(question)]}, self._config(thread_id))
        return self._verified_result(thread_id)

    @traceable(name="copilot.resume", run_type="chain")
    def resume(self, thread_id: str, approved: bool, comment: str = "",
               edited_body: str | None = None, approver: str = "user") -> AgentResult:
        decision = {"approved": approved, "comment": comment, "edited_body": edited_body,
                    "approver": approver}
        self.graph.invoke(Command(resume=decision), self._config(thread_id))
        return self._verified_result(thread_id)

    def _verified_result(self, thread_id: str) -> AgentResult:
        """Answer guardrail: if the answer cites sources no tool returned, or contains stray
        words in another script, ask the model ONCE to rewrite it. Remaining problems are
        reported on the result (and shown to the user) rather than hidden."""
        result = self._result(thread_id)
        if not result.answer:
            return result
        problems = []
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
        tool_texts = [m.content if isinstance(m.content, str) else json.dumps(m.content)
                      for m in turn if isinstance(m, ToolMessage)]
        pending = None
        if state.interrupts:
            pending = state.interrupts[0].value.get("proposal")
            answer = None
        else:
            answer = _text(messages[-1])
        cited, unverified = check_citations(answer or "", tool_texts)
        question = str(messages[last_human].content)
        return AgentResult(thread_id, answer, calls, cited, unverified, pending,
                           available_citations=available_citations(tool_texts),
                           foreign_words=foreign_words(answer or "", question))
