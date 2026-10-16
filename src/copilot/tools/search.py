"""Document search tool for the agent, on top of the step-4 retriever.

Mode choice follows the retrieval evaluation: vector search scored best on natural-
language questions (hit@5 88% vs 81% hybrid), so it is the default. Queries containing
an exact identifier (UN number, CFR section, SKU/shipment/incident id) use hybrid search,
because keyword matching is what finds exact codes.
"""

import re
from functools import lru_cache
from typing import Literal

from copilot.observability import traceable
from copilot.retrieval.retriever import Retriever, load_chunks

Collection = Literal["regulations", "dc_sops", "dc_sds", "dc_incidents"]
_IDENTIFIER = re.compile(
    r"\b(UN\d{4}|NA\d{4}|\d{3,4}\.\d{1,4}|[A-Z]{2,4}-\d{3,5}|SOP-[A-Z]{3}-\d{3})\b", re.IGNORECASE)
SNIPPET_CHARS = 1500


@lru_cache(maxsize=1)
def _retriever() -> Retriever:
    from copilot.retrieval.embeddings import openai_embedder

    return Retriever(load_chunks(), openai_embedder())


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
    hits = _retriever().search(query, k=k, mode=mode, where=where)
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
