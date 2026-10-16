# DC Exception Copilot

An agentic RAG assistant that helps distribution-center (DC) staff resolve warehouse
exceptions: hazmat loading questions, pallet-label problems, shipments at risk, and
safety/handling questions — grounded in real regulations and the DC's own data.

> Runs entirely on a laptop: SQLite + a local vector store + an LLM API.
> All documents are free and public; downloaded by script, never committed.

## Example questions

- *"Can 6 pallets of aerosol air freshener ship on the same trailer as 2 pallets of bleach?"*
- *"Inbound pallet from supplier S-014 has no SSCC barcode. What do we do?"*
- *"Which outbound shipments for tomorrow contain hazmat, and are they marked correctly?"*
- *"What training does a forklift operator need before driving in the hazmat zone?"*

## Architecture (target)

```
User (Streamlit UI / FastAPI)
        │
   Supervisor agent (LangGraph) ── plans, routes, writes final cited answer
        ├── Knowledge agent  → hybrid RAG over regulations, GS1 standards, SOPs
        ├── Ops data agent   → read-only SQL over the DC database (SQLite)
        ├── Hazmat tool      → deterministic 49 CFR 177.848 segregation check
        └── Action step      → drafts incident report / email, human approves
```

## Corpus

| Source | What | Use |
|---|---|---|
| 29 CFR 1910 (OSHA) via eCFR | Warehouse safety, forklifts, flammables, HazCom/SDS | RAG |
| 49 CFR 172–177 (HMR) via eCFR | Limited quantities, aerosols, loading, segregation | RAG |
| 49 CFR 172.101 | Hazardous Materials Table | Structured lookup |
| GS1 Logistic Label Guideline, General Specs | Pallet labels, SSCC, barcodes | RAG |
| Synthetic SOPs + incident reports | The fictional DC's own procedures & history | RAG |
| Synthetic WMS data | SKUs, inventory, shipments, exceptions | SQL |

Sources are listed in [`config/corpus_sources.yaml`](config/corpus_sources.yaml).

## Quickstart

```bash
uv sync                                   # install
cp .env.example .env                      # add your API key
uv run python -m copilot.ingest.download  # fetch corpus (~18 MB) into data/raw/
uv run pytest                             # run tests
```

## Project layout

```
config/            corpus sources and settings
data/raw/          downloaded corpus (git-ignored)
data/synthetic/    generated SOPs, incidents, WMS data
src/copilot/       package: ingest/, retrieval/, agents/, tools/, api/
tests/             unit tests + eval suite
```

See [ROADMAP.md](ROADMAP.md) for build steps.
