"""Step 4 - measure retrieval quality on the golden question set.

Usage:
    uv run python -m copilot.eval.retrieval_eval                 # all modes (needs API key)
    uv run python -m copilot.eval.retrieval_eval --modes bm25    # offline, keyword only

Compares chunking strategies (structured vs naive LangChain baseline) x search modes
(bm25, vector, hybrid). Writes data/eval/results/retrieval.md and .json.
"""

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from copilot.config import DATA_DIR, PROCESSED_DIR, settings
from copilot.retrieval.retriever import Retriever, load_chunks

GOLDEN_PATH = DATA_DIR / "eval" / "retrieval_golden.yaml"
RESULTS_DIR = DATA_DIR / "eval" / "results"
STRATEGIES = {
    "structured": PROCESSED_DIR / "chunks.jsonl",
    "naive": PROCESSED_DIR / "chunks_naive.jsonl",
}
DEPTH = 10  # ranks considered for MRR


def normalize(text: str) -> str:
    text = text.lower().replace("–", "-").replace("—", "-")
    text = text.replace("“", '"').replace("”", '"').replace("’", "'")
    text = re.sub(r"(\w)-\s+(\w)", r"\1\2", text)  # undo PDF line-break hyphenation
    return re.sub(r"\s+", " ", text)


def is_relevant(chunk: dict, evidence: list[str]) -> bool:
    body = normalize(chunk["text"])
    return any(normalize(e) in body for e in evidence)


def load_golden(path: Path = GOLDEN_PATH) -> list[dict]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def validate_golden(golden: list[dict], chunk_sets: dict[str, list[dict]]) -> list[str]:
    """Every question's evidence must exist in every chunk set, or the test is broken."""
    problems = []
    for q in golden:
        for name, chunks in chunk_sets.items():
            if not any(is_relevant(c, q["evidence"]) for c in chunks):
                problems.append(f"{q['id']}: evidence not found in '{name}' chunks")
    return problems


@dataclass
class Result:
    strategy: str
    mode: str
    ranks: dict[str, int | None]  # question id -> rank of first relevant hit (1-based)

    def metric(self, ids: list[str] | None = None) -> dict[str, float]:
        rs = [self.ranks[i] for i in (ids or self.ranks)]
        n = len(rs)
        return {
            "hit@1": sum(r == 1 for r in rs if r) / n,
            "hit@5": sum(r <= 5 for r in rs if r) / n,
            "mrr@10": sum(1 / r for r in rs if r) / n,
        }


def evaluate(retriever: Retriever, golden: list[dict], strategy: str, mode: str) -> Result:
    ranks = {}
    for q in golden:
        hits = retriever.search(q["question"], k=DEPTH, mode=mode)
        ranks[q["id"]] = next((r for r, h in enumerate(hits, 1) if is_relevant(h.chunk, q["evidence"])), None)
    return Result(strategy, mode, ranks)


def report(results: list[Result], golden: list[dict]) -> str:
    cats = sorted({q["category"] for q in golden})
    by_cat = {c: [q["id"] for q in golden if q["category"] == c] for c in cats}
    lines = [
        "# Retrieval evaluation",
        "",
        f"{len(golden)} questions ({', '.join(f'{c}: {len(i)}' for c, i in by_cat.items())}).",
        "",
        "| Chunking | Search | Hit@1 | Hit@5 | MRR@10 |",
        "|---|---|---|---|---|",
    ]
    for r in results:
        m = r.metric()
        lines.append(f"| {r.strategy} | {r.mode} | {m['hit@1']:.0%} | {m['hit@5']:.0%} | {m['mrr@10']:.3f} |")
    lines += ["", "## Hit@5 by category", "",
              "| Chunking | Search | " + " | ".join(cats) + " |",
              "|---|---|" + "---|" * len(cats)]
    for r in results:
        lines.append(f"| {r.strategy} | {r.mode} | "
                     + " | ".join(f"{r.metric(by_cat[c])['hit@5']:.0%}" for c in cats) + " |")
    lines += ["", "## Misses (no relevant chunk in top 5)", ""]
    for r in results:
        missed = [q for q in golden if not r.ranks[q["id"]] or r.ranks[q["id"]] > 5]
        lines.append(f"- **{r.strategy} / {r.mode}:** "
                     + (", ".join(f"{q['id']}" for q in missed) or "none"))
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--modes", default="bm25,vector,hybrid")
    parser.add_argument("--strategies", default="structured,naive")
    args = parser.parse_args()
    modes = args.modes.split(",")
    needs_vectors = any(m != "bm25" for m in modes)

    golden = load_golden()
    chunk_sets = {s: load_chunks(STRATEGIES[s]) for s in args.strategies.split(",")}
    problems = validate_golden(golden, chunk_sets)
    if problems:
        raise SystemExit("Golden set problems:\n  " + "\n  ".join(problems))

    embedder = None
    if needs_vectors:
        if settings.llm_provider != "azure" and not settings.openai_api_key:
            raise SystemExit("Vector modes need OPENAI_API_KEY in .env (or run with --modes bm25).")
        from copilot.retrieval.embeddings import openai_embedder

        embedder = openai_embedder()

    results = []
    for strategy, chunks in chunk_sets.items():
        print(f"Indexing '{strategy}' ({len(chunks)} chunks)...")
        retriever = Retriever(chunks, embedder, name=strategy)
        for mode in modes:
            results.append(evaluate(retriever, golden, strategy, mode))
            m = results[-1].metric()
            print(f"  {mode:7} hit@1={m['hit@1']:.0%}  hit@5={m['hit@5']:.0%}  mrr={m['mrr@10']:.3f}")
    if embedder is not None:
        print(f"Embedding API calls this run: {embedder.api_calls} (rest served from cache)")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    md = report(results, golden)
    (RESULTS_DIR / "retrieval.md").write_text(md, encoding="utf-8")
    (RESULTS_DIR / "retrieval.json").write_text(
        json.dumps([{"strategy": r.strategy, "mode": r.mode, **r.metric(), "ranks": r.ranks}
                    for r in results], indent=2), encoding="utf-8")
    print(f"\nReport -> {RESULTS_DIR / 'retrieval.md'}")


if __name__ == "__main__":
    main()
