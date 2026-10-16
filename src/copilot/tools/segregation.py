"""Deterministic hazmat load check: 49 CFR 177.848 segregation + DC policy.

The segregation table is parsed from the downloaded regulation XML (not typed in by
hand), so every verdict traces back to a cell of the official table.

Rules applied, in order:
1. 177.848(a): the table applies only to packages that must be labeled or placarded.
   Limited-quantity packages are excepted from hazard labels, so they are excluded.
2. 177.848(d): for each pair of classes among the remaining packages,
   "X" = may not be loaded together; "O" = only if separated so leaks cannot commingle.
   DC policy (SOP-HAZ-002 §3): any "O" pair goes on separate trailers.
3. DC chemical rule (SOP-HAZ-002 §3, SDS section 10): calcium hypochlorite and TCCA are
   both 5.1 - allowed together by the table - but must never be adjacent. Applies to all
   package sizes, including limited quantities.

Known simplifications (documented, not hidden): segregation uses the primary hazard class;
all class 8 products in the catalog are treated as liquids ("8 liquids only" column);
Class 1 compatibility groups (177.848(f)) and the ammonium nitrate note "A" are out of
scope because the DC stores no explosives.
"""

import re
from dataclasses import dataclass
from functools import lru_cache
from itertools import combinations
from pathlib import Path

from lxml import etree

from copilot.config import RAW_DIR

SOURCE_XML = RAW_DIR / "hmr_177_848" / "hmr_177_848.xml"
TABLE_CITATION = "49 CFR 177.848(d)"
SCOPE_CITATION = "49 CFR 177.848(a)"
POLICY_CITATION = "SOP-HAZ-002 §3"

# UN numbers for the calcium hypochlorite / chlorinated isocyanurate incompatibility
CALCIUM_HYPOCHLORITE = {"UN1748", "UN2208", "UN2880", "UN3485", "UN3486", "UN3487"}
CHLORINATED_ISOCYANURATES = {"UN2465", "UN2468"}


def _clean(el) -> str:
    return re.sub(r"\s+", " ", "".join(el.itertext())).strip()


def _classes(label: str, row_name: str = "") -> list[str]:
    """Normalize table labels: '1.1 and 1.2' -> ['1.1','1.2'], '2.3 gas zone A' -> ['2.3A']."""
    text = f"{label} {row_name}".lower()
    nums = re.findall(r"\d\.\d|\b\d\b", label)
    if nums and nums[0] in ("2.3", "6.1"):
        zone = re.search(r"zone ([ab])", text)
        return [nums[0] + (zone.group(1).upper() if zone else "")]
    return nums


@lru_cache(maxsize=1)
def segregation_table(path: Path = SOURCE_XML) -> dict[frozenset, str]:
    """{frozenset({class_a, class_b}): 'X' | 'O' | '*'}; absent pair = no restriction."""
    root = etree.parse(str(path)).getroot()
    table = next(root.iter("TABLE"))
    rows = [[_clean(c) for c in tr if c.tag in ("TH", "TD")] for tr in table.iter("TR")]
    header = rows[0]
    col_classes = [_classes(h) for h in header]
    out: dict[frozenset, str] = {}
    for row in rows[1:]:
        for rc in _classes(row[1], row[0]):
            for ci in range(3, len(row)):
                code = row[ci].strip()
                if not code:
                    continue
                for cc in col_classes[ci]:
                    key = frozenset({rc, cc})
                    if out.get(key, code) != code:  # the official table is symmetric
                        raise ValueError(f"asymmetric segregation table cell {rc}/{cc}")
                    out[key] = code
    return out


def pair_code(class_a: str, class_b: str) -> str:
    """'X', 'O', '*' or '' (no restriction) for two hazard classes."""
    return segregation_table().get(frozenset({class_a, class_b}), "")


@dataclass
class LoadItem:
    sku: str
    description: str
    hazard_class: str | None
    un_number: str | None
    limited_quantity: bool

    @property
    def regulated(self) -> bool:
        """Fully regulated hazmat: must be labeled, so subject to the segregation table."""
        return bool(self.hazard_class) and not self.limited_quantity


def check_load(items: list[LoadItem]) -> dict:
    """Return findings for items planned on ONE trailer. `compliant` is False if any
    finding has severity 'violation'."""
    findings = []
    lq = [i for i in items if i.hazard_class and i.limited_quantity]
    if lq:
        findings.append({
            "severity": "info",
            "rule": "Limited quantities excluded from segregation table",
            "citation": SCOPE_CITATION,
            "items": [i.sku for i in lq],
            "detail": "Limited-quantity packages are not required to bear hazard labels, so the "
                      "177.848 segregation table does not apply to them.",
        })

    regulated = [i for i in items if i.regulated]
    by_class: dict[str, list[LoadItem]] = {}
    for i in regulated:
        by_class.setdefault(i.hazard_class, []).append(i)
    for a, b in combinations(sorted(by_class), 2):
        code = pair_code(a, b)
        skus = [i.sku for i in by_class[a] + by_class[b]]
        if code == "X":
            findings.append({
                "severity": "violation", "rule": f"Class {a} and {b} may not be loaded together",
                "citation": TABLE_CITATION, "items": skus, "table_value": "X",
                "detail": "Table value X: may not be loaded, transported or stored together."})
        elif code == "O":
            findings.append({
                "severity": "violation",
                "rule": f"Class {a} and {b} require segregation (DC policy: separate trailers)",
                "citation": f"{TABLE_CITATION}; {POLICY_CITATION}", "items": skus, "table_value": "O",
                "detail": "Table value O: not allowed together unless separated so leaking packages "
                          "cannot commingle. DC-COL1 does not separate within a trailer, so the "
                          "class 5.1 pallets must move to a separate shipment."})

    cal = [i for i in items if i.un_number in CALCIUM_HYPOCHLORITE]
    tcca = [i for i in items if i.un_number in CHLORINATED_ISOCYANURATES]
    if cal and tcca:
        findings.append({
            "severity": "requirement",
            "rule": "Calcium hypochlorite and TCCA must never be adjacent",
            "citation": f"{POLICY_CITATION}; SDS section 10", "items": [i.sku for i in cal + tcca],
            "detail": "Both class 5.1, so the table allows them together, but mixing can cause fire "
                      "or explosion. Separate pallets, never adjacent, never in the same overpack, "
                      "with a non-hazmat pallet or empty space between them."})

    return {
        "compliant": not any(f["severity"] == "violation" for f in findings),
        "regulated_classes": sorted(by_class),
        "findings": findings,
    }
