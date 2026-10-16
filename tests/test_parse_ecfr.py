from copilot.ingest.parse_ecfr import _is_next_top_label, parse_ecfr

SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<DIV8 N="9.1" TYPE="SECTION" hierarchy_metadata="{&quot;citation&quot;:&quot;99 CFR 9.1&quot;}">
<HEAD>§ 9.1 Demo storage rules.</HEAD>
<P>(a) <I>Scope.</I> This section applies to warehouses.</P>
<P>(1) First sub-paragraph.</P>
<P>(b) Pallets must be stacked safely.</P>
<P>(i) Roman numeral under (b), not a new top-level paragraph.</P>
<DIV><TABLE><CAPTION><P>Max stack height</P></CAPTION>
<THEAD><TR><TH>Class</TH><TH>Height</TH></TR></THEAD>
<TBODY><TR><TD>3</TD><TD>2 m</TD></TR></TBODY></TABLE></DIV>
<EXTRACT>
<HD1>Appendix A to § 9.1—Examples (Non-mandatory)</HD1>
<HD1>A.1 Example one</HD1>
<P>Example text.</P>
</EXTRACT>
<CITA>[source note that should be skipped]</CITA>
</DIV8>
"""


def test_top_label_sequence():
    assert _is_next_top_label("a", None)
    assert _is_next_top_label("c", "b")
    assert not _is_next_top_label("i", "b")  # roman numeral, not (c)
    assert _is_next_top_label("i", "h")
    assert not _is_next_top_label("1", "a")


def test_parse_ecfr_citations_tables_and_appendix(tmp_path):
    path = tmp_path / "demo.xml"
    path.write_text(SAMPLE, encoding="utf-8")
    chunks = parse_ecfr(path, "demo", "https://example.org")

    by_cite = {c.citation: c for c in chunks}
    assert set(by_cite) == {"99 CFR 9.1(a)", "99 CFR 9.1(b)", "99 CFR 9.1 App. A A.1"}

    assert by_cite["99 CFR 9.1(a)"].section_path == ["Demo storage rules", "(a) Scope."]
    b = by_cite["99 CFR 9.1(b)"].body
    assert "(i) Roman numeral" in b
    assert "Table: Max stack height" in b and "| 3 | 2 m |" in b
    assert all("source note" not in c.body for c in chunks)

    app = by_cite["99 CFR 9.1 App. A A.1"]
    assert app.section_path[1].startswith("Appendix A")
    assert app.source_title == "99 CFR 9.1 Demo storage rules"
