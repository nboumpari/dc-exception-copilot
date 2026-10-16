import pymupdf

from copilot.ingest.parse_pdf import find_heading, parse_pdf, to_paragraphs


def test_find_heading_handles_number_and_title_on_separate_lines():
    lines = [(1, "Contents"), (2, "5.2 "), (2, "Customer name and address"), (2, "Body")]
    assert find_heading(lines, 0, "5.2 Customer name and address", page=2) == 1


def test_find_heading_respects_page_window():
    lines = [(1, "Intro"), (9, "Intro")]
    assert find_heading(lines, 0, "Intro", page=5) is None


def test_to_paragraphs_joins_wrapped_lines_and_splits_rules():
    lines = ["The SSCC is a", "unique identi-", "fication number.", "", "[5-1] Rule one.", "[5-2] Rule two."]
    assert to_paragraphs(lines) == [
        "The SSCC is a unique identification number.",
        "[5-1] Rule one.",
        "[5-2] Rule two.",
    ]


def test_parse_pdf_end_to_end(tmp_path):
    doc = pymupdf.open()
    body = "Every logistic unit must carry an SSCC. " * 6
    for n, (num, title) in enumerate([("1", "Introduction"), ("2", "Pallet labels")]):
        page = doc.new_page()
        page.insert_text((50, 40), "Demo Guideline Release 1.0")  # running header
        page.insert_text((50, 80), num)
        page.insert_text((50, 100), title)
        page.insert_textbox(pymupdf.Rect(50, 120, 550, 400), f"Section {n + 1}. {body}")
    page = doc.new_page()
    page.insert_text((50, 40), "Demo Guideline Release 1.0")
    doc.set_toc([[1, "1 Introduction", 1], [1, "2 Pallet labels", 2]])
    path = tmp_path / "demo.pdf"
    doc.save(path)

    chunks = parse_pdf(path, "demo", "Demo Guideline", "https://example.org")
    assert [c.citation for c in chunks] == ["Demo Guideline §1", "Demo Guideline §2"]
    assert chunks[1].page_start == 2
    assert "Section 2." in chunks[1].body
    assert all("Release 1.0" not in c.body for c in chunks)
