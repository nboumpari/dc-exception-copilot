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
| Synthetic SOPs (15) | The fictional DC's procedures, citing the real regulations | RAG |
| Synthetic Safety Data Sheets (16) | 16-section GHS format; transport data from 49 CFR 172.101 | RAG |
| Synthetic incident reports (~200) | Past exceptions: root cause, actions, SOP references | RAG |
| Synthetic warehouse database (SQLite) | SKUs, locations, inventory, receipts, shipments, exceptions | SQL |

Sources are listed in [`config/corpus_sources.yaml`](config/corpus_sources.yaml).

> **Why US regulations?** OSHA and DOT rules are public domain and downloadable by script via
> the eCFR API. The European equivalent (UNECE ADR) blocks automated downloads, so it is left as
> an optional manual add-on.

## The fictional DC

**Meridian Consumer Goods - Columbus DC (`DC-COL1`)** - invented company, people and partners.
43 SKUs from laundry pods to 20 L hydrogen peroxide drums, 8 storage zones (incl. aerosol cage,
flammables room, oxidizer and corrosive bays), 90 days of history up to the simulated
"today" **2026-10-16**, plus 3 days of planned work. The hazmat classifications are real
(checked against the Hazardous Materials Table by a unit test).

Planted scenarios the copilot should find (ids are deterministic):

| Scenario | Where | What a good answer notices |
|---|---|---|
| Oxidizer + corrosive drums on one trailer tomorrow | `SHP-01209` | 177.848 "O" pair (5.1 + 8); split per SOP-HAZ-002 |
| Same chemistries, consumer packs only | `SHP-01210` | Limited quantities: segregation table does not apply |
| Bulk pool shock + TCCA, non-hazmat carrier | `SHP-01211` | Carrier not endorsed **and** SDS says never mix the two |
| 05:30 departure, no trailer, unreliable carrier | `SHP-01212` | At risk per SOP-OUT-002; backup carrier, notify customer |
| Inbound from co-packer with label history | `RCV-00408` | Supplier on enhanced inspection list (SOP-REC-002) |
| Bleach leak near the oxidizer bay | `EXC-00367` | High severity; spill response SOP-HAZ-004 |

## Quickstart

```bash
uv sync                                   # install
cp .env.example .env                      # add your API key
uv run python -m copilot.ingest.download  # fetch corpus (~18 MB) into data/raw/
uv run python -m copilot.synthetic.build_wms  # synthetic DC: data/dc.db, incidents, SDS
uv run python -m copilot.ingest.build_chunks  # parse + chunk -> data/processed/chunks.jsonl
uv run python -m copilot.retrieval.naive_chunks   # baseline chunks for comparison
uv run python -m copilot.eval.retrieval_eval      # retrieval metrics -> data/eval/results/
uv run pytest                             # run tests
```

## Project layout

```
config/            corpus sources and settings
data/raw/          downloaded corpus (git-ignored)
data/synthetic/    SOPs (hand-written), SDS + incident reports (generated)
data/dc.db         synthetic warehouse database (git-ignored, regenerate)
src/copilot/       package: ingest/, retrieval/, agents/, tools/, api/
tests/             unit tests + eval suite
notebooks/         walkthrough notebook (imports the modules)
```

## Retrieval

Hybrid search over the chunks: **BM25** keyword search (exact codes like `UN1950`,
`177.848`) + **vector search** in ChromaDB with OpenAI `text-embedding-3-small`
(paraphrases), fused with **Reciprocal Rank Fusion**. Embeddings are cached on disk, so
re-indexing only pays for changed chunks (full corpus is about $0.01).

Evaluated on a 42-question golden set ([data/eval/retrieval_golden.yaml](data/eval/retrieval_golden.yaml))
against a naive LangChain `RecursiveCharacterTextSplitter` baseline:

| Chunking | Search | Hit@1 | Hit@5 | MRR@10 |
|---|---|---|---|---|
| Structured | BM25 | 38% | 69% | 0.52 |
| Structured | Vector | **64%** | **88%** | **0.73** |
| Structured | Hybrid | 62% | 81% | 0.70 |
| Naive | Vector | 60% | 81% | 0.67 |
| Naive | Hybrid | 60% | 86% | 0.70 |

Structure-aware chunks with vector search rank the answer first most often, and also give
exact citations (`29 CFR 1910.178(l)`) that the naive chunks cannot. Remaining misses are
mostly DC procedures crowded out by the large GS1 corpus - addressed in the agent by
routing questions to the right collection with metadata filters. Full report:
[data/eval/results/retrieval.md](data/eval/results/retrieval.md).

## Walkthrough notebook

[notebooks/demo.ipynb](notebooks/demo.ipynb) tours each build step with tables and charts
(saved with outputs, so it renders on GitHub). It only imports the project's modules - all
logic lives in tested code under `src/copilot/`.

```bash
uv sync --group notebook
uv run jupyter lab notebooks/demo.ipynb
```

See [ROADMAP.md](ROADMAP.md) for build steps.
