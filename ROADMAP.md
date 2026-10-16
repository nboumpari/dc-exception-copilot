# Roadmap

Each step ends with something that runs and is tested, and is one git commit (or a few).

| # | Step | Output | Status |
|---|------|--------|--------|
| 1 | **Setup + corpus download** | Project skeleton, `download.py`, manifest of 15 sources | done |
| 2 | **Parse + chunk** | eCFR XML → section/paragraph chunks with citations; GS1 PDFs → heading chunks; all to `chunks.jsonl` (1,636 chunks, 539k tokens) | done |
| 3 | **Synthetic DC data** | ~15 SOPs + ~150 incident reports (markdown); SQLite WMS: SKUs, inventory, shipments, exceptions | |
| 4 | **Retrieval baseline** | Embeddings + ChromaDB + BM25 hybrid; small golden set; recall@5 measured | |
| 5 | **Tools** | Read-only SQL tool, Hazmat Table lookup, 177.848 segregation checker (unit-tested) | |
| 6 | **Agents (LangGraph)** | Supervisor + knowledge + ops agents; cited answers; human-approval step for actions | |
| 7 | **API + UI** | FastAPI `/ask` endpoint; Streamlit chat with sources panel and trace view | |
| 8 | **Evaluation** | ~60-question golden set; groundedness, citation accuracy, SQL accuracy, refusal tests | |
| 9 | **Guardrails + logging** | Prompt-injection tests, refusal when unsure, structured logs of every tool call | |
| 10 | **CI + polish** | GitHub Actions (lint, tests, eval on small set); README diagram; demo video | |

Optional stretch: swap to Azure OpenAI + Azure AI Search (config switch), Dockerfile.
