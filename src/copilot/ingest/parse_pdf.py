"""Parse GS1 PDFs into section-level chunks using the PDF's bookmark tree (TOC).

1. Extract text lines per page and drop running headers/footers (lines that repeat on
   many pages, "Page N of M").
2. Locate every TOC heading in the line stream. Headings are often split over two lines
   ("5.2" then "SSCC"), so we match the number and title separately.
3. Each section = lines between its heading and the next one; lines are rejoined into
   paragraphs and packed into chunks citing e.g. "GS1 Logistic Label Guideline §5.2".
"""

import re
from collections import Counter
from pathlib import Path

import pymupdf

from copilot.ingest.chunking import Chunk, count_tokens, make_chunks

MIN_SECTION_TOKENS = 25  # sections that are only a heading (parents of subsections)
_PAGE_FOOTER = re.compile(r"^Page \d+ of \d+$")
_NUMBERED = re.compile(r"^((?:\d+|[A-Z])(?:\.\d+)*)\s+(.+)$")  # "5.2 SSCC", "A.1 Foo"
_NEW_PARA = re.compile(r"^(\[\d+-\d+\]|[•▪■●\-–]\s|\d+\.\s|[a-z]\)\s)")


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def extract_lines(doc: pymupdf.Document) -> list[tuple[int, str]]:
    """All text lines as (1-based page number, line), headers/footers removed."""
    pages = [page.get_text("text").split("\n") for page in doc]
    freq = Counter(_norm(ln) for lines in pages for ln in set(lines) if ln.strip())
    threshold = max(3, int(0.4 * len(pages)))
    noise = {ln for ln, n in freq.items() if n >= threshold}
    out = []
    for page_no, lines in enumerate(pages, start=1):
        for ln in lines:
            key = _norm(ln)
            if key in noise or _PAGE_FOOTER.match(ln.strip()):
                continue
            out.append((page_no, ln.rstrip()))
    return out


def find_heading(lines: list[tuple[int, str]], start: int, title: str, page: int) -> int | None:
    """Index of the line where TOC heading `title` starts, searching from `start`
    within its TOC page (or the next one, for headings at a page break)."""
    m = _NUMBERED.match(title)
    num, rest = (m.group(1), _norm(m.group(2))) if m else (None, _norm(title))
    full = _norm(title)
    for i in range(start, len(lines)):
        p, ln = lines[i]
        if p < page:
            continue
        if p > page + 1:
            return None
        cur = _norm(ln)
        if not cur:
            continue
        if cur.startswith(full[:40]):
            return i
        if num and cur == num.lower():
            nxt = next((_norm(t) for _, t in lines[i + 1 : i + 4] if t.strip()), "")
            if nxt and (nxt.startswith(rest[:25]) or rest.startswith(nxt[:25])):
                return i
    return None


def to_paragraphs(lines: list[str]) -> list[str]:
    paras, cur = [], []
    for ln in lines:
        s = ln.strip()
        if not s or _NEW_PARA.match(s):
            if cur:
                paras.append(" ".join(cur))
            cur = [s] if s else []
        else:
            cur.append(s)
    if cur:
        paras.append(" ".join(cur))
    # undo end-of-line hyphenation: "identi- fication" -> "identification"
    return [re.sub(r"(\w)- (\w)", r"\1\2", p) for p in paras if p]


def parse_pdf(path: Path, source_id: str, source_title: str, url: str) -> list[Chunk]:
    doc = pymupdf.open(path)
    toc = doc.get_toc()  # [[level, title, page], ...]
    lines = extract_lines(doc)

    # locate headings in order
    located: list[tuple[int, int, str]] = []  # (line index, level, title)
    cursor = 0
    for level, title, page in toc:
        idx = find_heading(lines, cursor, title.strip(), page)
        if idx is not None:
            located.append((idx, level, title.strip()))
            cursor = idx + 1

    chunks: list[Chunk] = []
    stack: list[str] = []
    for n, (idx, level, title) in enumerate(located):
        stack = stack[: level - 1] + [title]
        end = located[n + 1][0] if n + 1 < len(located) else len(lines)
        body_lines = [ln for _, ln in lines[idx:end]]
        # drop the heading line(s) themselves
        title_tokens = len(_norm(title).split())
        while body_lines and title_tokens > 0:
            title_tokens -= len(_norm(body_lines.pop(0)).split())
        paras = to_paragraphs(body_lines)
        if count_tokens(" ".join(paras)) < MIN_SECTION_TOKENS:
            continue
        m = _NUMBERED.match(title)
        citation = f"{source_title} §{m.group(1)}" if m else f"{source_title} - {title}"
        chunks += make_chunks(
            source_id=source_id,
            source_title=source_title,
            citation=citation,
            section_path=list(stack),
            blocks=paras,
            url=url,
            start_index=len(chunks),
            page_start=lines[idx][0],
            page_end=lines[end - 1][0],
        )
    doc.close()
    print(f"    {source_id}: matched {len(located)}/{len(toc)} TOC headings")
    return chunks
