"""Run the retrieval evaluation as LangSmith experiments.

Usage:
    uv run python -m copilot.eval.langsmith_eval                          # all configs
    uv run python -m copilot.eval.langsmith_eval --strategies structured --modes vector

1. Uploads the golden set as a LangSmith dataset. The dataset name carries a hash of the
   YAML file, so editing the questions creates a new dataset version instead of silently
   changing what old experiments were measured against.
2. Runs one experiment per (chunking strategy, search mode); each example is traced with
   its retrieved documents, and scored by hit@1, hit@5 and reciprocal rank.
3. Compare experiments side by side in the LangSmith UI (Datasets -> Experiments).

The local `retrieval_eval` module computes the same metrics offline; this one adds the
dashboard, per-question traces and experiment history.
"""

import argparse
import hashlib

from langsmith import Client, evaluate

from copilot.config import settings
from copilot.eval.retrieval_eval import GOLDEN_PATH, STRATEGIES, is_relevant, load_golden
from copilot.observability import setup_tracing
from copilot.retrieval.embeddings import OPENAI_MODEL
from copilot.retrieval.retriever import Retriever, load_chunks

DEPTH = 10


def dataset_name() -> str:
    digest = hashlib.sha256(GOLDEN_PATH.read_bytes()).hexdigest()[:8]
    return f"dc-retrieval-golden-{digest}"


def sync_dataset(client: Client) -> str:
    """Create the dataset for the current golden file if it does not exist yet."""
    name = dataset_name()
    if client.has_dataset(dataset_name=name):
        return name
    golden = load_golden()
    ds = client.create_dataset(
        name, description="Retrieval golden set: DC staff questions with evidence phrases."
    )
    client.create_examples(
        dataset_id=ds.id,
        examples=[
            {
                "inputs": {"question": q["question"]},
                "outputs": {"evidence": q["evidence"]},
                "metadata": {"qid": q["id"], "category": q["category"]},
            }
            for q in golden
        ],
    )
    return name


# ---------- evaluators: (outputs, reference_outputs) -> score ----------
def _first_relevant_rank(outputs: dict, reference_outputs: dict) -> int | None:
    for rank, doc in enumerate(outputs["documents"], 1):
        if is_relevant({"text": doc["text"]}, reference_outputs["evidence"]):
            return rank
    return None


def hit_at_1(outputs: dict, reference_outputs: dict) -> dict:
    return {"key": "hit@1", "score": int(_first_relevant_rank(outputs, reference_outputs) == 1)}


def hit_at_5(outputs: dict, reference_outputs: dict) -> dict:
    rank = _first_relevant_rank(outputs, reference_outputs)
    return {"key": "hit@5", "score": int(rank is not None and rank <= 5)}


def reciprocal_rank(outputs: dict, reference_outputs: dict) -> dict:
    rank = _first_relevant_rank(outputs, reference_outputs)
    return {"key": "reciprocal_rank", "score": 1 / rank if rank else 0.0}


EVALUATORS = [hit_at_1, hit_at_5, reciprocal_rank]


def make_target(retriever: Retriever, mode: str):
    def target(inputs: dict) -> dict:
        hits = retriever.search(inputs["question"], k=DEPTH, mode=mode)
        return {"documents": [{"citation": h.chunk["citation"], "text": h.chunk["text"]} for h in hits]}

    return target


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--modes", default="bm25,vector,hybrid")
    parser.add_argument("--strategies", default="structured,naive")
    args = parser.parse_args()

    if not settings.langsmith_api_key:
        raise SystemExit("LANGSMITH_API_KEY is not set in .env.")
    setup_tracing()  # experiments are logged either way; this also enables live tracing if on
    from copilot.retrieval.embeddings import openai_embedder

    client = Client(api_key=settings.langsmith_api_key, api_url=settings.langsmith_endpoint)
    data = sync_dataset(client)
    embedder = openai_embedder()
    print(f"Dataset: {data}")
    for strategy in args.strategies.split(","):
        retriever = Retriever(load_chunks(STRATEGIES[strategy]), embedder, name=strategy)
        for mode in args.modes.split(","):
            results = evaluate(
                make_target(retriever, mode),
                data=data,
                evaluators=EVALUATORS,
                experiment_prefix=f"{strategy}-{mode}",
                metadata={"strategy": strategy, "mode": mode, "embedding_model": OPENAI_MODEL,
                          "k": DEPTH},
                max_concurrency=4,
                client=client,
            )
            print(f"  {strategy}/{mode}: {results.experiment_name}")
    print("Open LangSmith -> Datasets & Experiments to compare.")


if __name__ == "__main__":
    main()
