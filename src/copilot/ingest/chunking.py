"""Shared chunk model and size-aware packing used by every parser."""

import re
from dataclasses import dataclass, field

import tiktoken

MAX_TOKENS = 500  # upper bound per chunk body; tables may be split by rows to fit

_ENC = tiktoken.get_encoding("o200k_base")
_SENTENCE_END = re.compile(r"(?<=[.;:])\s+(?=[A-Z(\[])")


@dataclass
class Chunk:
    chunk_id: str
    source_id: str
    source_title: str
    citation: str  # human-readable pointer, e.g. "29 CFR 1910.178(l)" or "GS1 Logistic Label §5.2"
    section_path: list[str]  # headings from the document root down to this chunk
    body: str  # the chunk content, shown to users as the quoted source
    text: str  # breadcrumb header + body; this is what gets embedded
    tokens: int
    url: str
    page_start: int | None = None
    page_end: int | None = None
    extra: dict = field(default_factory=dict)


def count_tokens(text: str) -> int:
    return len(_ENC.encode(text))


def make_chunks(
    *,
    source_id: str,
    source_title: str,
    citation: str,
    section_path: list[str],
    blocks: list[str],
    url: str,
    start_index: int,
    page_start: int | None = None,
    page_end: int | None = None,
) -> list[Chunk]:
    """Pack the blocks of one logical unit (a paragraph, a PDF section) into Chunks."""
    header = f"{source_title}\n{citation} - {' > '.join(section_path)}"
    chunks = []
    for i, body in enumerate(pack(blocks, MAX_TOKENS)):
        text = f"{header}\n\n{body}"
        chunks.append(
            Chunk(
                chunk_id=f"{source_id}:{start_index + i:04d}",
                source_id=source_id,
                source_title=source_title,
                citation=citation,
                section_path=section_path,
                body=body,
                text=text,
                tokens=count_tokens(text),
                url=url,
                page_start=page_start,
                page_end=page_end,
            )
        )
    return chunks


def pack(blocks: list[str], max_tokens: int) -> list[str]:
    """Greedily join blocks into groups of at most max_tokens, never splitting a block
    unless it is oversized on its own."""
    groups: list[str] = []
    cur: list[str] = []
    cur_tokens = 0
    for block in blocks:
        for piece in split_oversized(block, max_tokens):
            n = count_tokens(piece)
            if cur and cur_tokens + n > max_tokens:
                groups.append("\n\n".join(cur))
                cur, cur_tokens = [], 0
            cur.append(piece)
            cur_tokens += n
    if cur:
        groups.append("\n\n".join(cur))
    return groups


def split_oversized(text: str, max_tokens: int) -> list[str]:
    if count_tokens(text) <= max_tokens:
        return [text]
    lines = text.split("\n")
    table_start = next((i for i, ln in enumerate(lines) if ln.startswith("|")), None)
    if table_start is not None and len(lines) - table_start > 3:
        return _split_table(lines, table_start, max_tokens)
    return _split_prose(text, max_tokens)


def _split_table(lines: list[str], start: int, max_tokens: int) -> list[str]:
    """Split a markdown table by rows, repeating caption + header row in every piece."""
    head = lines[: start + 2]  # caption lines, header row, separator row
    rows = lines[start + 2 :]
    head_tokens = count_tokens("\n".join(head))
    pieces, cur, cur_tokens = [], [], head_tokens
    for row in rows:
        n = count_tokens(row) + 1
        if cur and cur_tokens + n > max_tokens:
            pieces.append("\n".join(head + cur))
            cur, cur_tokens = [], head_tokens
        cur.append(row)
        cur_tokens += n
    if cur:
        pieces.append("\n".join(head + cur))
    return pieces


def _split_prose(text: str, max_tokens: int) -> list[str]:
    sentences = _SENTENCE_END.split(text)
    out: list[str] = []
    for s in sentences:
        if count_tokens(s) <= max_tokens:
            out.append(s)
        else:  # a single monster sentence: hard token windows
            ids = _ENC.encode(s)
            out.extend(_ENC.decode(ids[i : i + max_tokens]) for i in range(0, len(ids), max_tokens))
    # re-join sentences into pieces near max_tokens
    pieces, cur = [], ""
    for s in out:
        candidate = f"{cur} {s}".strip()
        if cur and count_tokens(candidate) > max_tokens:
            pieces.append(cur)
            cur = s
        else:
            cur = candidate
    if cur:
        pieces.append(cur)
    return pieces
