from copilot.ingest.parse_markdown import parse_markdown

SHORT = """---
doc_id: INC-9999
doc_type: incident_report
title: "INC-9999 - Test"
effective: 2026-01-01
---

# INC-9999 - Test

## Summary
Short report.
"""


def test_short_doc_is_one_chunk_with_metadata(tmp_path):
    p = tmp_path / "INC-9999.md"
    p.write_text(SHORT, encoding="utf-8")
    [chunk] = parse_markdown(p, "data/synthetic/incidents/INC-9999.md")
    assert chunk.citation == "INC-9999"
    assert chunk.extra["doc_type"] == "incident_report"
    assert chunk.extra["effective"] == "2026-01-01"  # date made JSON-safe
    assert "# INC-9999" not in chunk.body  # H1 dropped, title lives in the header


def test_long_doc_is_split_by_numbered_sections(tmp_path):
    sections = "\n\n".join(f"## {i}. Section {i}\n" + "Rule text. " * 120 for i in range(1, 5))
    p = tmp_path / "SOP-TST-001.md"
    p.write_text(f"---\ndoc_id: SOP-TST-001\ntitle: Test SOP\n---\n\n# Test SOP\n\n{sections}",
                 encoding="utf-8")
    chunks = parse_markdown(p, "x")
    assert len(chunks) > 1
    assert chunks[0].citation.startswith("SOP-TST-001 §1")
    assert all(c.source_id == "SOP-TST-001" for c in chunks)
