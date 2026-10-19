"""Document search tool for the agent, on top of the step-4 retriever.

Mode choice follows the retrieval evaluation: vector search scored best on natural-
language questions (hit@5 88% vs 81% hybrid), so it is the default. Queries containing
an exact identifier (UN number, CFR section, SKU/shipment/incident id) use hybrid search,
because keyword matching is what finds exact codes.

Graceful degradation: vector search needs the embedding API for every new question. If
that call fails (no credits, outage, no network), search falls back to keyword search
(BM25, fully local) and says so in the result, instead of failing the whole answer.
"""

import logging
import re
import threading
from typing import Literal

import openai

from copilot.logs import log_event
from copilot.observability import traceable
from copilot.retrieval.retriever import Retriever, load_chunks

Collection = Literal["regulations", "dc_sops", "dc_sds", "dc_incidents"]
_IDENTIFIER = re.compile(
    r"\b(UN\d{4}|NA\d{4}|\d{3,4}\.\d{1,4}|[A-Z]{2,4}-\d{3,5}|SOP-[A-Z]{3}-\d{3})\b", re.IGNORECASE)
SNIPPET_CHARS = 1500


_lock = threading.Lock()
_instance: Retriever | None = None


def _retriever() -> Retriever:
    """Shared retriever, built once. The agent runs parallel tool calls in threads, so
    construction is locked (two threads opening ChromaDB at once crashed its client)."""
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                from copilot.retrieval.embeddings import openai_embedder

                _instance = Retriever(load_chunks(), openai_embedder())
    return _instance


def choose_mode(query: str) -> str:
    return "hybrid" if _IDENTIFIER.search(query) else "vector"


@traceable(run_type="tool", name="search_documents")
def search_documents(query: str, collection: Collection | None = None, k: int = 5) -> dict:
    """Search regulations, GS1 standards, DC SOPs, safety data sheets and incident reports.

    collection narrows the search: 'regulations' (OSHA, DOT, GS1), 'dc_sops',
    'dc_sds' or 'dc_incidents'. Leave empty to search everything.
    """
    where = None
    if collection == "regulations":
        where = {"collection": "regulation_or_standard"}
    elif collection:
        where = {"collection": collection}
    mode = choose_mode(query)
    try:
        hits = _retriever().search(query, k=k, mode=mode, where=where)
    except openai.OpenAIError as exc:  # embedding API unavailable: keyword search still works
        log_event("search.fallback", logging.WARNING, error=type(exc).__name__, mode=mode)
        hits = _retriever().search(query, k=k, mode="bm25", where=where)
        mode = "bm25 (fallback: embedding service unavailable)"
    return {
        "mode": mode,
        "results": [
            {
                "citation": h.chunk["citation"],
                "source": h.chunk["source_title"],
                "url": h.chunk.get("url", ""),
                "text": h.chunk["body"][:SNIPPET_CHARS],
            }
            for h in hits
        ],
    }


READ_CHARS = 12_000


@traceable(run_type="tool", name="read_source")
def read_source(reference: str) -> dict:
    """Full text of a source found by search: a citation ('29 CFR 1910.178(l)',
    'SOP-REC-002 §1-3') returns every passage with that citation; a document id
    ('SDS-NPRM', 'SOP-ESC-001', 'INC-0205') returns the whole document."""
    ref = reference.strip().strip("[]")
    chunks = _retriever().chunks
    hits = [c for c in chunks if c["citation"] == ref]
    if not hits:
        hits = [c for c in chunks if c["source_id"].lower() == ref.lower()]
    if not hits:  # a document id inside a longer citation, e.g. 'SDS-NPRM §9'
        doc = ref.split(" §")[0].split(" -")[0]
        hits = [c for c in chunks if c["source_id"].lower() == doc.lower()]
    if not hits:
        return {"error": f"no source matches {ref!r}; use a citation or document id from search"}
    passages, used, truncated = [], 0, False
    for c in hits:
        if used + len(c["body"]) > READ_CHARS:
            truncated = True
            break
        passages.append({"citation": c["citation"], "text": c["body"]})
        used += len(c["body"])
    return {"reference": ref, "source": hits[0]["source_title"], "url": hits[0].get("url", ""),
            "passages": passages, "truncated": truncated}
