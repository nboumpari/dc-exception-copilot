"""Parse eCFR section XML into citable chunks.

eCFR sections are a flat run of <P> paragraphs whose text starts with a label such as
"(a)", "(1)", "(i)". We group paragraphs by their top-level letter so each chunk cites
e.g. "29 CFR 1910.178(l)". Appendices (inside <EXTRACT>) are grouped by their HD1/HD2
headings instead. Tables become markdown so the LLM can read rows and columns.
"""

import json
import re
from collections.abc import Iterator
from pathlib import Path

from lxml import etree

from copilot.ingest.chunking import Chunk, make_chunks

_LABEL = re.compile(r"^\(([a-z0-9]{1,5})\)")
_RANGE = re.compile(r"^\(([a-z])\)\s*[-–]\s*\(([a-z])\)")
_WRAPPERS = {"EXTRACT", "DIV"}  # containers we read through
_SKIP = {"CITA", "EDNOTE", "PSPACE", "img", "SECAUTH", "AUTH", "SOURCE"}
_HEADINGS = {"HD1": 0, "HD2": 1, "HD3": 2}


def clean(el: etree._Element) -> str:
    return re.sub(r"\s+", " ", "".join(el.itertext())).strip()


def table_to_markdown(table: etree._Element) -> str:
    lines = []
    caption = table.find("CAPTION")
    if caption is not None and clean(caption):
        lines.append(f"Table: {clean(caption)}")
    rows = [
        [clean(cell).replace("|", "/") for cell in tr if cell.tag in ("TH", "TD")]
        for tr in table.iter("TR")
    ]
    rows = [r for r in rows if any(r)]
    if rows:
        width = max(len(r) for r in rows)
        rows = [r + [""] * (width - len(r)) for r in rows]
        lines.append("| " + " | ".join(rows[0]) + " |")
        lines.append("|" + "---|" * width)
        lines.extend("| " + " | ".join(r) + " |" for r in rows[1:])
    for foot in table.iter("TFOOT"):
        if clean(foot):
            lines.append(clean(foot))
    return "\n".join(lines)


def iter_blocks(parent: etree._Element) -> Iterator[tuple[str, str]]:
    """Yield (kind, text) in document order: kind is 'heading:<level>', 'p', 'p_deep', 'table'.

    'p_deep' marks paragraphs with an italic label like (<I>c</I>): these are level-5
    sub-paragraphs that reuse the letters a, b, c... and must never start a top-level unit.
    """
    for el in parent.iterchildren():
        tag = el.tag if isinstance(el.tag, str) else ""
        if not tag or tag in _SKIP or tag == "HEAD":
            continue
        if tag in _HEADINGS:
            yield f"heading:{_HEADINGS[tag]}", clean(el)
        elif tag == "TABLE":
            yield "table", table_to_markdown(el)
        elif tag == "DIV" and el.find(".//TABLE") is not None:
            # table wrappers: emit each table once (captions hold <P>, so don't recurse)
            for table in el.iter("TABLE"):
                yield "table", table_to_markdown(table)
        elif tag in _WRAPPERS:
            yield from iter_blocks(el)
        elif tag == "NOTE":
            yield "p", "Note: " + clean(el)
        else:  # P, FP, FP-2, ...
            text = clean(el)
            if text:
                italic_label = (el.text or "").strip() == "(" and len(el) and el[0].tag == "I"
                yield ("p_deep" if italic_label else "p"), text


def _is_next_top_label(label: str, current: str | None) -> bool:
    """True if label is the next top-level paragraph letter: (a), (b), (c)...

    Roman numerals like (i) only count as top-level when they directly follow (h).
    """
    if len(label) != 1 or not label.isalpha():
        return False
    return label == "a" if current is None else ord(label) == ord(current) + 1


def _paragraph_title(text: str) -> str:
    """'(l) Operator training. (1) ...' -> '(l) Operator training.'; else first ~9 words."""
    m = re.match(r"^(\([a-z]\)\s*.{1,80}?\.)(?=\s)", text)
    if m:
        return m.group(1)
    words = text.split()
    return " ".join(words[:9]) + (" ..." if len(words) > 9 else "")


def _appendix_citation(base: str, appendix: str | None, heading: str | None) -> str:
    """-> '29 CFR 1910.1200 App. A A.0.1' (heading number appended when present)."""
    if appendix is None:
        return base
    num = re.match(r"^([A-Z]+\.[\d.]*\d)\b", heading or "")
    return f"{base} App. {appendix}" + (f" {num.group(1)}" if num else "")


def parse_ecfr(path: Path, source_id: str, url: str) -> list[Chunk]:
    root = etree.parse(str(path)).getroot()
    meta = json.loads(root.get("hierarchy_metadata", "{}"))
    citation_base = meta.get("citation") or f"CFR {root.get('N')}"
    head = clean(root.find("HEAD"))  # "§ 1910.178 Powered industrial trucks."
    section_title = re.sub(r"^§\s*[\d.]+\s*", "", head).rstrip(".")
    source_title = f"{citation_base} {section_title}"

    # Group blocks into units: (citation, section_path, blocks)
    units: list[tuple[str, list[str], list[str]]] = []
    top: str | None = None
    headings: list[str] = []
    appendix: str | None = None  # sticky until the next "Appendix X" heading
    appendix_title = ""

    def new_unit(citation: str, path: list[str]) -> None:
        units.append((citation, path, []))

    new_unit(citation_base, [section_title])
    for kind, text in iter_blocks(root):
        if kind.startswith("heading:"):
            m = re.match(r"^Appendix ([A-Z]+)\b", text)
            if m:
                appendix, appendix_title, headings = m.group(1), text, []
            else:
                level = int(kind.split(":")[1])
                headings = headings[:level] + [text]
            top = None
            path = [section_title, *([appendix_title] if appendix else []), *headings]
            heading = headings[-1] if headings else None
            new_unit(_appendix_citation(citation_base, appendix, heading), path)
            continue
        if kind == "p" and appendix is None and not headings:
            m = _LABEL.match(text)
            if m and _is_next_top_label(m.group(1), top):
                top = m.group(1)
                new_unit(f"{citation_base}({top})", [section_title, _paragraph_title(text)])
                # "(c)-(d) [Reserved]" covers two letters: the next real paragraph is (e)
                rng = _RANGE.match(text)
                if rng:
                    top = rng.group(2)
        units[-1][2].append(text)

    chunks: list[Chunk] = []
    for citation, section_path, blocks in units:
        if not blocks:
            continue
        chunks += make_chunks(
            source_id=source_id,
            source_title=source_title,
            citation=citation,
            section_path=section_path,
            blocks=blocks,
            url=url,
            start_index=len(chunks),
        )
    return chunks
