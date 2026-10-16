"""Sanity checks on config/corpus_sources.yaml (no network)."""

import yaml

from copilot.config import CONFIG_DIR

CFG = yaml.safe_load((CONFIG_DIR / "corpus_sources.yaml").read_text(encoding="utf-8"))
ALL = CFG["ecfr"] + CFG["pdf"]


def test_ids_are_unique():
    ids = [s["id"] for s in ALL]
    assert len(ids) == len(set(ids))


def test_every_source_has_a_valid_use():
    assert all(s["use"] in {"rag", "structured"} for s in ALL)


def test_ecfr_sections_match_their_title():
    for s in CFG["ecfr"]:
        assert s["title"] in (29, 49)
        assert "." in s["section"]
