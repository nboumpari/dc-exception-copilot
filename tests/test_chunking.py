from copilot.ingest.chunking import count_tokens, make_chunks, pack, split_oversized


def test_pack_respects_token_budget():
    blocks = [f"Paragraph {i}. " + "word " * 60 for i in range(20)]
    groups = pack(blocks, max_tokens=200)
    assert len(groups) > 1
    assert all(count_tokens(g) <= 200 for g in groups)
    # nothing lost
    assert sum(g.count("Paragraph") for g in groups) == 20


def test_oversized_table_is_split_by_rows_with_header_repeated():
    rows = [f"| row{i} | " + "x " * 20 + "|" for i in range(60)]
    table = "\n".join(["Table: Demo", "| a | b |", "|---|---|", *rows])
    pieces = split_oversized(table, max_tokens=150)
    assert len(pieces) > 1
    assert all(p.startswith("Table: Demo\n| a | b |\n|---|---|") for p in pieces)
    assert sum(p.count("| row") for p in pieces) == 60


def test_oversized_prose_is_split_on_sentences():
    text = " ".join(f"Sentence number {i} is here." for i in range(200))
    pieces = split_oversized(text, max_tokens=100)
    assert all(count_tokens(p) <= 100 for p in pieces)
    assert pieces[0].startswith("Sentence number 0")


def test_make_chunks_adds_breadcrumb_and_stable_ids():
    chunks = make_chunks(
        source_id="src",
        source_title="Doc",
        citation="Doc §1",
        section_path=["1 Intro"],
        blocks=["Hello world."],
        url="u",
        start_index=7,
    )
    assert chunks[0].chunk_id == "src:0007"
    assert chunks[0].text.startswith("Doc\nDoc §1 - 1 Intro\n\nHello world.")
