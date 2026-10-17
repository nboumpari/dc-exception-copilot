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
| 8 | **API + UI** | FastAPI `/ask` endpoint; simple chat UI with sources and approvals | |
| 9 | **Guardrails + logging** | Prompt-injection tests, refusal when unsure, structured logs of every tool call | |
| 10 | **CI + polish** | GitHub Actions (lint, tests, eval on small set); README diagram; demo video | |

Optional stretch: add UNECE ADR 2025 (manual download) for a European variant; swap to Azure OpenAI + Azure AI Search (config switch), Dockerfile.
