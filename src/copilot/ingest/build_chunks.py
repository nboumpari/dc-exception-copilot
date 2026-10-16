"""Step 2 - turn the downloaded corpus into data/processed/chunks.jsonl.

Usage:
    uv run python -m copilot.ingest.build_chunks

Reads data/raw/manifest.json (written by download.py), parses every source marked
`use: rag`, and writes one JSON object per chunk plus a stats summary.
"""

import json
import re
from collections import Counter
from dataclasses import asdict

import yaml

from copilot.config import CONFIG_DIR, PROCESSED_DIR, RAW_DIR
from copilot.ingest.chunking import Chunk
from copilot.ingest.parse_ecfr import parse_ecfr
from copilot.ingest.parse_pdf import parse_pdf


def ecfr_public_url(api_url: str) -> str:
    """API url -> the human-readable eCFR page users can click from a citation."""
    title = re.search(r"title-(\d+)", api_url).group(1)
    section = re.search(r"section=([\d.]+)", api_url).group(1)
    return f"https://www.ecfr.gov/current/title-{title}/section-{section}"


def build() -> list[Chunk]:
    manifest = json.loads((RAW_DIR / "manifest.json").read_text(encoding="utf-8"))
    cfg = yaml.safe_load((CONFIG_DIR / "corpus_sources.yaml").read_text(encoding="utf-8"))
    pdf_titles = {s["id"]: s["title"] for s in cfg.get("pdf", [])}

    chunks: list[Chunk] = []
    for entry in manifest:
        if entry["use"] != "rag":
            continue
        path = RAW_DIR / entry["path"]
        if entry["kind"] == "ecfr":
            parsed = parse_ecfr(path, entry["id"], ecfr_public_url(entry["url"]))
        else:
            parsed = parse_pdf(path, entry["id"], pdf_titles[entry["id"]], entry["url"])
        for c in parsed:
            c.extra = {"topic": entry["topic"], "source_sha256": entry["sha256"]}
        print(f"  {entry['id']:20} {len(parsed):5} chunks")
        chunks += parsed
    return chunks


def main() -> None:
    chunks = build()
    ids = [c.chunk_id for c in chunks]
    dupes = [i for i, n in Counter(ids).items() if n > 1]
    if dupes:
        raise SystemExit(f"Duplicate chunk ids: {dupes[:5]}")

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out = PROCESSED_DIR / "chunks.jsonl"
    with out.open("w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(asdict(c), ensure_ascii=False) + "\n")

    tokens = sorted(c.tokens for c in chunks)
    stats = {
        "chunks": len(chunks),
        "total_tokens": sum(tokens),
        "tokens_min": tokens[0],
        "tokens_median": tokens[len(tokens) // 2],
        "tokens_max": tokens[-1],
        "per_source": dict(Counter(c.source_id for c in chunks)),
    }
    (PROCESSED_DIR / "chunk_stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    print(f"\n{stats['chunks']} chunks, {stats['total_tokens']:,} tokens "
          f"(median {stats['tokens_median']}, max {stats['tokens_max']}) -> {out}")


if __name__ == "__main__":
    main()
