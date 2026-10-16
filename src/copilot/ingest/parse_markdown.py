"""Parse the DC's own markdown documents (SOPs, SDS, incident reports) into chunks.

Each file has YAML front matter (doc_id, doc_type, title, ...). Short documents become a
single chunk; longer ones are split on '## ' sections, with consecutive small sections
packed together, citing e.g. "SOP-HAZ-002 §3" or "SDS-PSHB §10-13".
"""

import re
from datetime import date
from pathlib import Path

import yaml

from copilot.ingest.chunking import MAX_TOKENS, Chunk, count_tokens, make_chunks

_FRONT_MATTER = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
_SECTION_NUM = re.compile(r"^(\d+)[.)]?\s")


def split_front_matter(text: str) -> tuple[dict, str]:
    m = _FRONT_MATTER.match(text)
    if not m:
        return {}, text
    meta = yaml.safe_load(m.group(1)) or {}
    # YAML parses 2026-03-01 as a date; keep metadata JSON-serializable
    meta = {k: v.isoformat() if isinstance(v, date) else v for k, v in meta.items()}
    return meta, text[m.end():]


def parse_markdown(path: Path, url: str) -> list[Chunk]:
    meta, body = split_front_matter(path.read_text(encoding="utf-8"))
    doc_id = meta.get("doc_id", path.stem)
    title = meta.get("title", doc_id)
    # drop the H1 line (title is already in the breadcrumb header)
    body = re.sub(r"^# .*\n", "", body.lstrip(), count=1)
    extra = {k: v for k, v in meta.items() if k not in ("doc_id", "title")}

    if count_tokens(body) <= MAX_TOKENS:
        chunks = make_chunks(source_id=doc_id, source_title=title, citation=doc_id,
                             section_path=[title], blocks=[body.strip()], url=url, start_index=0)
    else:
        chunks = []
        for group in _group_sections(_sections(body)):
            nums = [n for n, _, _ in group if n]
            if nums:
                cite = f"{doc_id} §{nums[0]}" + (f"-{nums[-1]}" if len(nums) > 1 else "")
            else:
                cite = f"{doc_id} - {group[0][1]}"
            chunks += make_chunks(
                source_id=doc_id, source_title=title, citation=cite,
                section_path=[title, " / ".join(h for _, h, _ in group)],
                blocks=[f"## {h}\n{t}".strip() for _, h, t in group],
                url=url, start_index=len(chunks))
    for c in chunks:
        c.extra = dict(extra)
    return chunks


def _sections(body: str) -> list[tuple[str | None, str, str]]:
    """[(section number or None, heading, text)] split on '## ' headings."""
    parts = re.split(r"^## (.+)$", body, flags=re.MULTILINE)
    out = []
    if parts[0].strip():
        out.append((None, "Overview", parts[0].strip()))
    for heading, text in zip(parts[1::2], parts[2::2]):
        m = _SECTION_NUM.match(heading)
        out.append((m.group(1) if m else None, heading.strip(), text.strip()))
    return out


def _group_sections(sections: list) -> list[list]:
    """Pack consecutive sections into groups that fit MAX_TOKENS (oversized ones alone)."""
    groups, cur, cur_tokens = [], [], 0
    for sec in sections:
        n = count_tokens(f"## {sec[1]}\n{sec[2]}")
        if cur and cur_tokens + n > MAX_TOKENS:
            groups.append(cur)
            cur, cur_tokens = [], 0
        cur.append(sec)
        cur_tokens += n
    if cur:
        groups.append(cur)
    return groups
