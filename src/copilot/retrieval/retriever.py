"""Hybrid retriever: BM25 keyword search + vector search (ChromaDB), fused with RRF.

Why hybrid? Keyword search nails exact identifiers ("UN1950", "177.848", "SHP-01209")
but misses paraphrases; vector search finds paraphrases ("forklift driver training" ->
"powered industrial truck operator") but can blur exact codes. Reciprocal Rank Fusion
combines the two rankings without having to calibrate their very different scores.
"""

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

import bm25s
import chromadb
import numpy as np

from copilot.config import DATA_DIR, PROCESSED_DIR
from copilot.retrieval.embeddings import Embedder

CHROMA_DIR = DATA_DIR / "index" / "chroma"
RRF_K = 60  # standard constant from Cormack et al. (2009)
CANDIDATES = 50  # how many results each retriever contributes to the fusion

_TOKEN = re.compile(r"[a-z0-9]+(?:[.\-][a-z0-9]+)*")
_STOPWORDS = frozenset(
    ["a", "an", "and", "are", "as", "at", "be", "by", "can", "do", "does", "for", "from", "has", "have", "how", "i", "if", "in", "is", "it", "its", "may", "must", "not", "of", "on", "or", "our", "shall", "should", "so", "that", "the", "their", "them", "there", "these", "this", "to", "was", "we", "what", "when", "where", "which", "who", "will", "with", "you"]
)
# chunk metadata copied into Chroma for filtering (values must be str/int/float/bool)
_FILTER_FIELDS = ("source_id", "collection", "doc_type", "sku", "severity", "exception_type", "sop")


def tokenize(text: str) -> list[str]:
    """Lowercase word tokens; compound codes are kept whole AND split ('177.848' -> 3 tokens)."""
    out = []
    for tok in _TOKEN.findall(text.lower()):
        if tok in _STOPWORDS:
            continue
        out.append(tok)
        parts = re.split(r"[.\-]", tok)
        if len(parts) > 1:
            out.extend(p for p in parts if p and p not in _STOPWORDS)
    return out


def load_chunks(path: Path = PROCESSED_DIR / "chunks.jsonl") -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def corpus_hash(chunks: list[dict]) -> str:
    h = hashlib.sha256()
    for c in chunks:
        h.update(c["chunk_id"].encode())
        h.update(c["text"].encode())
    return h.hexdigest()[:16]


@dataclass
class Hit:
    chunk: dict
    score: float
    bm25_rank: int | None = None
    vector_rank: int | None = None


def _rrf(rankings: list[list[int]]) -> dict[int, float]:
    scores: dict[int, float] = {}
    for ranking in rankings:
        for rank, idx in enumerate(ranking):
            scores[idx] = scores.get(idx, 0.0) + 1.0 / (RRF_K + rank + 1)
    return scores


class Retriever:
    def __init__(self, chunks: list[dict], embedder: Embedder | None, name: str = "structured",
                 chroma_dir: Path = CHROMA_DIR):
        self.chunks = chunks
        self.index_of = {c["chunk_id"]: i for i, c in enumerate(chunks)}
        self.embedder = embedder

        self.bm25 = bm25s.BM25()
        self.bm25.index([tokenize(c["text"]) for c in chunks], show_progress=False)

        self.collection = None
        if embedder is not None:
            self.collection = self._vector_collection(name, chroma_dir)

    # ---------- vector index ----------
    def _vector_collection(self, name: str, chroma_dir: Path):
        client = chromadb.PersistentClient(
            path=str(chroma_dir), settings=chromadb.Settings(anonymized_telemetry=False)
        )
        slug = re.sub(r"[^a-zA-Z0-9._-]", "-", f"{name}-{self.embedder.name}")
        digest = corpus_hash(self.chunks)
        if slug in {c.name for c in client.list_collections()}:
            col = client.get_collection(slug)
            if (col.metadata or {}).get("corpus_hash") == digest and col.count() == len(self.chunks):
                return col  # index is up to date
            client.delete_collection(slug)  # corpus changed: rebuild
        col = client.create_collection(
            slug, embedding_function=None, metadata={"hnsw:space": "cosine", "corpus_hash": digest}
        )
        vecs = self.embedder.embed([c["text"] for c in self.chunks])
        for i in range(0, len(self.chunks), 1000):
            part = self.chunks[i : i + 1000]
            col.add(
                ids=[c["chunk_id"] for c in part],
                embeddings=vecs[i : i + 1000].tolist(),
                metadatas=[self._metadata(c) for c in part],
            )
        return col

    @staticmethod
    def _metadata(chunk: dict) -> dict:
        meta = {"source_id": chunk["source_id"], "citation": chunk["citation"]}
        for k in _FILTER_FIELDS:
            v = chunk.get("extra", {}).get(k)
            if isinstance(v, (str, int, float, bool)) and v != "":
                meta[k] = v
        meta.setdefault("collection", "regulation_or_standard")
        return meta

    # ---------- search ----------
    def _matches(self, chunk: dict, where: dict | None) -> bool:
        if not where:
            return True
        meta = self._metadata(chunk)
        return all(meta.get(k) == v for k, v in where.items())

    def bm25_ranking(self, query: str, n: int, where: dict | None = None) -> list[int]:
        scores = self.bm25.get_scores(tokenize(query))
        if where:
            mask = np.array([self._matches(c, where) for c in self.chunks])
            scores = np.where(mask, scores, -1.0)
        order = np.argsort(-scores)[:n]
        return [int(i) for i in order if scores[i] > 0]

    def vector_ranking(self, query: str, n: int, where: dict | None = None) -> list[int]:
        if self.collection is None:
            raise RuntimeError("Vector search needs an embedder (OPENAI_API_KEY in .env).")
        qvec = self.embedder.embed([query])[0].tolist()
        chroma_where = where if not where or len(where) == 1 else {"$and": [{k: v} for k, v in where.items()]}
        res = self.collection.query(query_embeddings=[qvec], n_results=n, where=chroma_where)
        return [self.index_of[i] for i in res["ids"][0]]

    def search(self, query: str, k: int = 5, mode: str = "hybrid", where: dict | None = None) -> list[Hit]:
        """mode: 'bm25' | 'vector' | 'hybrid'. `where` filters on metadata, e.g.
        {"collection": "dc_sops"} or {"doc_type": "sds"}."""
        if mode == "bm25":
            ranking = self.bm25_ranking(query, k, where)
            return [Hit(self.chunks[i], 1.0 / (r + 1), bm25_rank=r) for r, i in enumerate(ranking)]
        if mode == "vector":
            ranking = self.vector_ranking(query, k, where)
            return [Hit(self.chunks[i], 1.0 / (r + 1), vector_rank=r) for r, i in enumerate(ranking)]

        bm = self.bm25_ranking(query, CANDIDATES, where)
        vec = self.vector_ranking(query, CANDIDATES, where)
        fused = _rrf([bm, vec])
        bm_rank = {i: r for r, i in enumerate(bm)}
        vec_rank = {i: r for r, i in enumerate(vec)}
        top = sorted(fused, key=lambda i: -fused[i])[:k]
        return [Hit(self.chunks[i], fused[i], bm_rank.get(i), vec_rank.get(i)) for i in top]
