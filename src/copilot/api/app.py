"""FastAPI service around the copilot agent.

Run:
    uv run uvicorn copilot.api.app:app --port 8000
Then open http://localhost:8000 (chat page) or http://localhost:8000/docs (API docs).

Endpoints:
    GET  /health                       liveness + configuration (no secrets)
    POST /ask                          ask a question (optionally continue a thread)
    GET  /threads/{thread_id}          is the conversation waiting for an approval?
    POST /threads/{thread_id}/approve  approve, edit or reject a proposed action

If API_KEY is set in .env, /ask and the thread endpoints require the X-API-Key header.
Conversations live in memory: they are lost when the server restarts.
"""

import logging
import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

import openai
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from copilot.agent.graph import AgentResult, Copilot
from copilot.config import settings
from copilot.synthetic.catalog import SIM_NOW

STATIC_DIR = Path(__file__).parent / "static"
log = logging.getLogger("copilot.api")


# ---------- request / response models (these also generate the /docs page) ----------
class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000,
                          examples=["Is SHP-01209 OK to load tomorrow?"])
    thread_id: str | None = Field(None, description="continue an earlier conversation")


class ToolCall(BaseModel):
    name: str
    args: dict


class ProposedAction(BaseModel):
    action_type: str
    recipient: str
    subject: str
    body: str
    reason: str


class AgentResponse(BaseModel):
    thread_id: str
    status: str = Field(description="'answered' or 'awaiting_approval'")
    answer: str | None
    citations: list[str]
    unverified_citations: list[str]
    tool_calls: list[ToolCall]
    pending_action: ProposedAction | None
    usage: dict


class ApprovalRequest(BaseModel):
    approved: bool
    comment: str = ""
    edited_body: str | None = Field(None, description="replace the email/ticket body before sending")
    approver: str = Field("api user", max_length=100)


class ThreadStatus(BaseModel):
    thread_id: str
    status: str


def to_response(r: AgentResult) -> AgentResponse:
    return AgentResponse(
        thread_id=r.thread_id,
        status="awaiting_approval" if r.pending_action else "answered",
        answer=r.answer,
        citations=r.citations,
        unverified_citations=r.unverified_citations,
        tool_calls=[ToolCall(**c) for c in r.tool_calls],
        pending_action=ProposedAction(**r.pending_action) if r.pending_action else None,
        usage=r.usage,
    )


# ---------- dependencies ----------
def get_copilot(request: Request) -> Copilot:
    return request.app.state.copilot


def require_api_key(x_api_key: Annotated[str | None, Header()] = None) -> None:
    if settings.api_key and not secrets.compare_digest(x_api_key or "", settings.api_key):
        raise HTTPException(status_code=401, detail="missing or invalid X-API-Key header")


CopilotDep = Annotated[Copilot, Depends(get_copilot)]


def create_app(copilot: Copilot | None = None) -> FastAPI:
    """App factory; tests pass a Copilot built on a scripted fake model."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.copilot = copilot or Copilot()  # build the agent once, at startup
        yield

    app = FastAPI(title="DC Exception Copilot", version="0.1.0", lifespan=lifespan,
                  description="Agentic RAG assistant for distribution-center exceptions.")
    protected = [Depends(require_api_key)]

    @app.exception_handler(openai.APIError)
    async def llm_unavailable(request: Request, exc: openai.APIError) -> JSONResponse:
        """The LLM provider failed (no credits, rate limit, outage): say so clearly with 503
        instead of a 500 stack trace."""
        log.warning("LLM provider error: %s", exc)
        if getattr(exc, "status_code", None) == 429:
            detail = ("The language model provider refused the request: rate limit reached "
                      "or no API credits left.")
        else:
            detail = "The language model provider is unavailable. Try again later."
        return JSONResponse(status_code=503, content={"detail": detail})

    @app.exception_handler(Exception)
    async def unexpected(request: Request, exc: Exception) -> JSONResponse:
        """Anything else: log the details, return a JSON error without internals."""
        log.exception("unhandled error on %s", request.url.path)
        return JSONResponse(status_code=500, content={"detail": "Internal error - see server logs."})

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "chat_model": settings.chat_model,
                "reasoning_effort": settings.reasoning_effort, "simulation_time": SIM_NOW,
                "auth_required": bool(settings.api_key)}

    @app.post("/ask", response_model=AgentResponse, dependencies=protected)
    def ask(req: AskRequest, cp: CopilotDep) -> AgentResponse:
        # a plain `def` endpoint: FastAPI runs it in a worker thread, so a slow agent
        # call does not block other requests
        if req.thread_id and cp.thread_status(req.thread_id) == "awaiting_approval":
            raise HTTPException(409, "this conversation is waiting for an approval decision")
        return to_response(cp.ask(req.question, thread_id=req.thread_id))

    @app.get("/threads/{thread_id}", response_model=ThreadStatus, dependencies=protected)
    def thread(thread_id: str, cp: CopilotDep) -> ThreadStatus:
        status = cp.thread_status(thread_id)
        if status == "unknown":
            raise HTTPException(404, "unknown thread")
        return ThreadStatus(thread_id=thread_id, status=status)

    @app.post("/threads/{thread_id}/approve", response_model=AgentResponse,
              dependencies=protected)
    def approve(thread_id: str, req: ApprovalRequest, cp: CopilotDep) -> AgentResponse:
        status = cp.thread_status(thread_id)
        if status == "unknown":
            raise HTTPException(404, "unknown thread")
        if status != "awaiting_approval":
            raise HTTPException(409, "nothing is waiting for approval in this thread")
        return to_response(cp.resume(thread_id, approved=req.approved, comment=req.comment,
                                     edited_body=req.edited_body, approver=req.approver))

    @app.get("/", include_in_schema=False)
    def chat_page() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    return app


app = create_app()
