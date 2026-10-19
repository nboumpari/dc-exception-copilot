# Roadmap

Each step ends with something that runs and is tested, and is one git commit (or a few).
Each step also adds a section to [notebooks/demo.ipynb](notebooks/demo.ipynb).

| # | Step | Output | Status |
|---|------|--------|--------|
| 1 | **Setup + corpus download** | Project skeleton, `download.py`, manifest of 15 sources | done |
| 2 | **Parse + chunk** | eCFR XML → section/paragraph chunks with citations; GS1 PDFs → heading chunks; all to `chunks.jsonl` (1,636 chunks, 539k tokens) | done |
| 3 | **Synthetic DC data** | 15 SOPs, 16 SDS, 205 incident reports; SQLite WMS (1.2k shipments, 367 exceptions, 6 planted scenarios); corpus now 1,896 chunks | done |
| 4 | **Retrieval baseline** | BM25 + ChromaDB vectors + RRF hybrid; 42-question golden set; structured vs naive chunking compared | done |
| 4b | **Observability** | LangSmith tracing of retrieval and embeddings; golden set as LangSmith dataset + experiments | done |
| 5 | **Tools** | Read-only SQL, Hazardous Materials Table lookup, 177.848 segregation + shipment compliance, departure risk, document search; tested on the planted scenarios | done |
| 6 | **Agent (LangGraph)** | Single tool-calling agent (simpler and easier to evaluate than several sub-agents); cited answers with citation verification; human approval for actions; CLI | done |
| 7 | **Agent evaluation** (moved before the API) | 44-case golden set, code checks + cross-provider LLM judge (Gemini grading an OpenAI agent, validated against a second judge), 3 runs per case, LangSmith experiments; 64% -> 97% with documented experiments | done |
| 8 | **API + UI** | FastAPI service (ask, approvals, health, typed docs), explicit 503/409/401 errors, Streamlit UI (chat with approvals + evaluation dashboard) as an API client; API and UI tests with a fake model | done |
| 9 | **Guardrails + logging** | Code guardrails (blocked secret/prompt requests, injection flags incl. in data, personal-email block, output rewrite checks, key redaction, keyword-search fallback); 12-case red-team set 64% -> 92%; JSON app log (requests, answers, tool calls, linked to LangSmith run ids) + approval audit log | done |
| 10 | **CI + polish** | GitHub Actions: lint, data rebuilt from scratch with a reproducibility check, 150 tests on every push; manual evaluation gate (16 real-agent cases, fails below 90%); README architecture diagram and results summary | done |

Optional stretch: add UNECE ADR 2025 (manual download) for a European variant; swap to Azure OpenAI + Azure AI Search (config switch), Dockerfile.
