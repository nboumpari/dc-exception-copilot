import os

from copilot.config import settings
from copilot.eval.langsmith_eval import dataset_name, hit_at_1, hit_at_5, reciprocal_rank
from copilot.observability import setup_tracing
from copilot.retrieval.retriever import Hit, _as_document


def test_tracing_stays_off_without_a_key(monkeypatch):
    monkeypatch.setattr(settings, "langsmith_tracing", True)
    monkeypatch.setattr(settings, "langsmith_api_key", "")
    assert setup_tracing() is False
    assert os.environ["LANGSMITH_TRACING"] == "false"


def test_tracing_turns_on_with_flag_and_key(monkeypatch):
    monkeypatch.setattr(settings, "langsmith_tracing", True)
    monkeypatch.setattr(settings, "langsmith_api_key", "test-key")
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    assert setup_tracing(project="unit-test") is True
    assert os.environ["LANGSMITH_TRACING"] == "true"
    assert os.environ["LANGSMITH_PROJECT"] == "unit-test"


def test_hits_are_logged_as_langsmith_documents():
    chunk = {"chunk_id": "x:1", "citation": "29 CFR 1910.178(l)", "body": "Operator training.",
             "url": "https://example.org"}
    doc = _as_document(Hit(chunk, 0.0321, bm25_rank=None, vector_rank=0))
    assert doc["type"] == "Document"
    assert doc["page_content"] == "Operator training."
    assert doc["metadata"]["citation"] == "29 CFR 1910.178(l)"
    assert doc["metadata"]["vector_rank"] == 0 and doc["metadata"]["bm25_rank"] is None


def test_evaluators_score_rank_of_first_relevant_document():
    ref = {"evidence": ["once every three years"]}
    out = {"documents": [{"text": "unrelated"}, {"text": "Evaluated at least once every three years."}]}
    assert hit_at_1(out, ref)["score"] == 0
    assert hit_at_5(out, ref)["score"] == 1
    assert reciprocal_rank(out, ref)["score"] == 0.5
    assert reciprocal_rank({"documents": []}, ref)["score"] == 0.0
    assert hit_at_5({}, ref)["score"] == 0  # a failed run counts as a miss, not a crash


def test_dataset_name_is_versioned_by_golden_file_content():
    name = dataset_name()
    assert name.startswith("dc-retrieval-golden-") and len(name) == len("dc-retrieval-golden-") + 8
