"""Consistency checks for the synthetic DC: the data must agree with the real regulations
and with the DC's own SOPs, otherwise evaluation answers would be wrong."""

import re

import pytest
import yaml
from lxml import etree

from copilot.config import CONFIG_DIR, RAW_DIR, SYNTHETIC_DIR
from copilot.synthetic.build_wms import Generator, gs1_check_digit, make_sscc
from copilot.synthetic.catalog import CARRIERS, FAMILIES
from copilot.synthetic.incidents import TYPES


@pytest.fixture(scope="module")
def gen():
    g = Generator(seed=42)
    g.scenarios = g.run()
    return g


def test_gs1_check_digit_known_example():
    assert gs1_check_digit("400638133393") == "1"  # GTIN-13 4006381333931


def test_sscc_is_18_digits_and_valid():
    sscc = make_sscc(123)
    assert len(sscc) == 18 and sscc.isdigit()
    assert gs1_check_digit(sscc[:-1]) == sscc[-1]


def test_generation_is_deterministic(gen):
    other = Generator(seed=42)
    other.run()
    assert {t: len(r) for t, r in gen.rows.items()} == {t: len(r) for t, r in other.rows.items()}
    assert gen.rows["exceptions"][:20] == other.rows["exceptions"][:20]


def test_every_exception_type_points_to_an_existing_sop():
    sops = {p.stem for p in (SYNTHETIC_DIR / "sops").glob("*.md")}
    assert {t.sop for t in TYPES.values()} <= sops


def test_regulations_cited_by_playbook_are_in_the_corpus():
    cfg = yaml.safe_load((CONFIG_DIR / "corpus_sources.yaml").read_text(encoding="utf-8"))
    sections = {s["section"] for s in cfg["ecfr"]}
    for t in TYPES.values():
        for ref in t.regulations:
            m = re.match(r"(?:29|49) CFR ([\d.]+)", ref)
            if m:
                assert m.group(1) in sections, ref


def test_sop_cross_references_resolve():
    sops = {p.stem: p for p in (SYNTHETIC_DIR / "sops").glob("*.md")}
    for path in sops.values():
        for ref in re.findall(r"SOP-[A-Z]{3}-\d{3}", path.read_text(encoding="utf-8")):
            assert ref in sops, f"{path.name} references missing {ref}"


def test_fully_regulated_hazmat_only_on_endorsed_carriers_except_planted(gen):
    endorsed = {c[0] for c in CARRIERS if c[2]}
    regulated = {s["sku"] for s in gen.skus if gen.regulated_class(s)}
    hazmat_shipments = {r[0] for r in gen.rows["shipment_lines"] if r[1] in regulated}
    bad = {r[0] for r in gen.rows["shipments"] if r[0] in hazmat_shipments and r[2] not in endorsed}
    assert bad == {gen.scenarios["carrier_not_hazmat"]}


def test_planted_segregation_conflict(gen):
    shp = gen.scenarios["seg_conflict_tomorrow"]
    lines = [gen.sku_by_id[r[1]] for r in gen.rows["shipment_lines"] if r[0] == shp]
    assert frozenset({"5.1", "8"}) in gen.conflicts(lines)
    lq = gen.scenarios["lq_no_conflict"]
    lq_lines = [gen.sku_by_id[r[1]] for r in gen.rows["shipment_lines"] if r[0] == lq]
    assert gen.conflicts(lq_lines) == []  # same classes, but limited quantity


@pytest.mark.skipif(not (RAW_DIR / "hmr_172_101").exists(), reason="corpus not downloaded")
def test_catalog_hazmat_matches_the_hazardous_materials_table():
    root = etree.parse(str(RAW_DIR / "hmr_172_101" / "hmr_172_101.xml")).getroot()
    rows = set()
    for tr in root.iter("TR"):
        cells = [re.sub(r"\s+", " ", "".join(td.itertext())).strip() for td in tr if td.tag == "TD"]
        if len(cells) > 3 and cells[3].startswith("UN"):
            rows.add((cells[3], cells[2]))  # (UN number, hazard class)
    for fam in FAMILIES:
        if fam.hazmat:
            assert (fam.hazmat.un_number, fam.hazmat.hazard_class) in rows, fam.code
