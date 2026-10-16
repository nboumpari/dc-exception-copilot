"""Retrieval tests - fully offline (HashEmbedder instead of OpenAI)."""

import numpy as np
import pytest

from copilot.config import PROCESSED_DIR
from copilot.eval.retrieval_eval import is_relevant, load_golden, normalize, validate_golden
from copilot.retrieval.embeddings import CachedEmbedder, EmbeddingCache, HashEmbedder
from copilot.retrieval.retriever import Retriever, _rrf, load_chunks, tokenize


def chunk(cid: str, text: str, **extra) -> dict:
    return {"chunk_id": cid, "source_id": cid.split(":")[0], "citation": cid, "text": text,
            "body": text, "extra": extra}


CHUNKS = [
    chunk("reg:1", "Forklift operators must be evaluated at least once every three years."),
    chunk("reg:2", "Class 8 corrosive liquids may not be loaded adjacent to oxidizers. See 177.848."),
    chunk("sop:1", "Move the pallet without SSCC to the exception lane in zone D.", collection="dc_sops"),
    chunk("sds:1", "UN1950 aerosols flammable, store in the aerosol cage.", collection="dc_sds"),
]


@pytest.fixture
def retriever(tmp_path):
    return Retriever(CHUNKS, HashEmbedder(), name="test", chroma_dir=tmp_path / "chroma")


def test_tokenize_keeps_codes_whole_and_split():
    toks = tokenize("Check 177.848 for SHP-01209 and UN1950")
    assert {"177.848", "177", "848", "shp-01209", "01209", "un1950"} <= set(toks)
    assert "for" not in toks and "and" not in toks


def test_rrf_rewards_agreement():
    scores = _rrf([[1, 2, 3], [2, 1, 4]])
    assert scores[1] == scores[2] > scores[3] > 0
    assert scores[4] < scores[1]


def test_bm25_finds_exact_code(retriever):
    hits = retriever.search("UN1950", k=1, mode="bm25")
    assert hits[0].chunk["chunk_id"] == "sds:1"


def test_hybrid_and_filters(retriever):
    hits = retriever.search("pallet SSCC exception lane", k=2, mode="hybrid")
    assert hits[0].chunk["chunk_id"] == "sop:1"
    assert hits[0].bm25_rank is not None and hits[0].vector_rank is not None
    only_sds = retriever.search("pallet", k=4, mode="hybrid", where={"collection": "dc_sds"})
    assert {h.chunk["chunk_id"] for h in only_sds} <= {"sds:1"}


def test_vector_index_is_reused_when_corpus_unchanged(tmp_path):
    Retriever(CHUNKS, HashEmbedder(), name="reuse", chroma_dir=tmp_path)
    counting = CachedEmbedder("count", lambda batch: HashEmbedder().embed(batch),
                              EmbeddingCache(tmp_path / "cache.sqlite"))
    Retriever(CHUNKS, counting, name="reuse2", chroma_dir=tmp_path)
    assert counting.api_calls == 1  # first build embeds once
    Retriever(CHUNKS, counting, name="reuse2", chroma_dir=tmp_path)
    assert counting.api_calls == 1  # second build: index reused, no new calls


def test_embedding_cache_only_calls_api_for_new_texts(tmp_path):
    calls = []

    def raw(batch):
        calls.append(list(batch))
        return np.ones((len(batch), 4))

    emb = CachedEmbedder("t", raw, EmbeddingCache(tmp_path / "c.sqlite"))
    emb.embed(["a", "b"])
    emb.embed(["a", "b", "c"])
    assert calls == [["a", "b"], ["c"]]


def test_embedding_cache_is_safe_across_threads(tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    emb = CachedEmbedder("t", lambda batch: np.ones((len(batch), 4)),
                         EmbeddingCache(tmp_path / "c.sqlite"))
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda i: emb.embed([f"text {i}", "shared"]), range(20)))
    assert all(r.shape == (2, 4) for r in results)


def test_relevance_matching_is_robust_to_formatting():
    c = {"text": "the unique identi-\nfication  Number"}
    assert normalize("identification number") in normalize(c["text"])
    assert is_relevant(c, ["IDENTIFICATION number"])


@pytest.mark.skipif(not (PROCESSED_DIR / "chunks_naive.jsonl").exists(), reason="chunks not built")
def test_golden_set_evidence_exists_in_both_chunk_sets():
    sets = {"structured": load_chunks(PROCESSED_DIR / "chunks.jsonl"),
            "naive": load_chunks(PROCESSED_DIR / "chunks_naive.jsonl")}
    assert validate_golden(load_golden(), sets) == []
