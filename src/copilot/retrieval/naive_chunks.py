"""Baseline for comparison: the 'tutorial' approach to chunking.

Extract plain text from every source and cut it with LangChain's
RecursiveCharacterTextSplitter (2,000 characters ~ 500 tokens, 200 overlap). No
awareness of paragraphs, sections or tables, and no precise citations. Evaluating
retrieval on both chunk sets shows whether structure-aware chunking pays off.

Usage:
    uv run python -m copilot.retrieval.naive_chunks
"""

import json
import re

import pymupdf
import yaml
from langchain_text_splitters import RecursiveCharacterTextSplitter
from lxml import etree

from copilot.config import CONFIG_DIR, PROCESSED_DIR, PROJECT_ROOT, RAW_DIR
from copilot.ingest.chunking import count_tokens
from copilot.ingest.parse_markdown import split_front_matter

NAIVE_PATH = PROCESSED_DIR / "chunks_naive.jsonl"
SPLITTER = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=200)


def raw_documents() -> list[tuple[str, str, dict]]:
    """(source_id, plain text, extra metadata) for every RAG source."""
    manifest = json.loads((RAW_DIR / "manifest.json").read_text(encoding="utf-8"))
    cfg = yaml.safe_load((CONFIG_DIR / "corpus_sources.yaml").read_text(encoding="utf-8"))
    docs = []
    for entry in manifest:
        if entry["use"] != "rag":
            continue
        path = RAW_DIR / entry["path"]
        if entry["kind"] == "ecfr":
            root = etree.parse(str(path)).getroot()
            text = "\n".join(re.sub(r"\s+", " ", "".join(el.itertext())).strip()
                             for el in root.iter("P", "HEAD", "HD1", "HD2", "TD"))
        else:
            with pymupdf.open(path) as doc:
                text = "\n".join(page.get_text() for page in doc)
        docs.append((entry["id"], text, {}))
    for src in cfg.get("local", []):
        for f in sorted(PROJECT_ROOT.glob(src["glob"])):
            meta, body = split_front_matter(f.read_text(encoding="utf-8"))
            docs.append((meta.get("doc_id", f.stem), body,
                         {"collection": src["id"], "doc_type": meta.get("doc_type")}))
    return docs


def build_naive_chunks() -> list[dict]:
    chunks = []
    for source_id, text, extra in raw_documents():
        for n, piece in enumerate(SPLITTER.split_text(text)):
            chunks.append({
                "chunk_id": f"naive:{source_id}:{n:04d}",
                "source_id": source_id,
                "source_title": source_id,
                "citation": f"{source_id} (chunk {n})",
                "section_path": [],
                "body": piece,
                "text": piece,
                "tokens": count_tokens(piece),
                "url": "",
                "extra": {k: v for k, v in extra.items() if v},
            })
    return chunks


def main() -> None:
    chunks = build_naive_chunks()
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    with NAIVE_PATH.open("w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    print(f"{len(chunks)} naive chunks, {sum(c['tokens'] for c in chunks):,} tokens -> {NAIVE_PATH}")


if __name__ == "__main__":
    main()
