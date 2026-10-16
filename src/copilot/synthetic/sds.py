"""Synthetic Safety Data Sheets in the 16-section GHS / OSHA HazCom format.

Chemistry (CAS numbers, typical hazards, incompatibilities) reflects real substances;
Section 14 comes from catalog.Hazmat (taken from 49 CFR 172.101). Product names,
formulations and companies are invented. Each SDS states that it is synthetic.
"""

from copilot.config import SYNTHETIC_DIR
from copilot.synthetic.catalog import DC, FAMILIES, SIM_TODAY, ZONES, Family

SDS_DIR = SYNTHETIC_DIR / "sds"

_FIRST_AID_CORROSIVE = {
    "Inhalation": "Move to fresh air. Get medical attention if irritation or breathing difficulty occurs.",
    "Skin": "Immediately remove contaminated clothing. Rinse skin with plenty of water for at least 15 minutes. Get medical attention.",
    "Eyes": "Immediately rinse with water for at least 15 minutes, holding eyelids open. Remove contact lenses if easy. Get immediate medical attention.",
    "Ingestion": "Rinse mouth. Do NOT induce vomiting. Get immediate medical attention.",
}
_FIRST_AID_IRRITANT = {
    "Inhalation": "Move to fresh air if symptoms occur.",
    "Skin": "Rinse with water. Get medical advice if irritation persists.",
    "Eyes": "Rinse cautiously with water for several minutes. Remove contact lenses if easy. If irritation persists, get medical advice.",
    "Ingestion": "Rinse mouth and drink a glass of water. Do not induce vomiting. Call a poison center if unwell.",
}
_FIRST_AID_FLAMMABLE = {
    "Inhalation": "Move to fresh air. If drowsiness or dizziness occurs, get medical advice.",
    "Skin": "Rinse with water. Remove contaminated clothing away from ignition sources.",
    "Eyes": "Rinse cautiously with water for several minutes. If irritation persists, get medical advice.",
    "Ingestion": "Rinse mouth. Do not induce vomiting. Call a poison center.",
}

PROFILES: dict[str, dict] = {
    "LQD": dict(
        use="Household laundry detergent", signal="Warning",
        ghs=["Skin irritation, Category 2 (H315)", "Eye irritation, Category 2A (H319)"],
        comp=[("Sodium dodecylbenzenesulfonate", "25155-30-0", "10-20"),
              ("Alcohols, C9-11, ethoxylated", "68439-46-3", "5-10"),
              ("Propylene glycol", "57-55-6", "1-5"), ("Water", "7732-18-5", "60-80")],
        aid=_FIRST_AID_IRRITANT, phys="Blue viscous liquid, mild fragrance; pH 8-9; not flammable.",
        incompat="Strong oxidizers (e.g. concentrated bleach, pool chemicals).",
        fire="Product does not burn readily. Use media suitable for surrounding fire.",
        spill="Absorb with inert material; floor will be slippery. Rinse residue to sanitary drain only if permitted locally.",
        ppe="None needed for intact packages. Gloves and goggles for spill clean-up.",
        tox="Mild skin and eye irritant.", eco="Surfactants are readily biodegradable.",
    ),
    "PODS": dict(
        use="Household unit-dose laundry detergent", signal="Warning",
        ghs=["Skin irritation, Category 2 (H315)", "Eye irritation, Category 2A (H319)"],
        comp=[("Alcohols, C9-11, ethoxylated", "68439-46-3", "20-30"),
              ("Sodium dodecylbenzenesulfonate", "25155-30-0", "15-25"),
              ("Propylene glycol", "57-55-6", "5-10"), ("Glycerol", "56-81-5", "5-10"),
              ("Polyvinyl alcohol (film)", "9002-89-5", "1-5")],
        aid=_FIRST_AID_IRRITANT, phys="Liquid-filled water-soluble pouches; pH 7-8; not flammable.",
        incompat="Water/moisture (film dissolves); strong oxidizers.",
        fire="Not flammable. Use media suitable for surrounding fire.",
        spill="Collect crushed pouches in a dry container. Keep away from water to avoid foaming.",
        ppe="Gloves and goggles when handling crushed product.",
        tox="Concentrated detergent; eye irritant. Keep out of reach of children.",
        eco="Surfactants are readily biodegradable.",
    ),
    "HBLC": dict(
        use="Household bleach (6% sodium hypochlorite)", signal="Danger",
        ghs=["Skin irritation, Category 2 (H315)", "Serious eye damage, Category 1 (H318)",
             "Supplemental: contact with acids liberates toxic gas"],
        comp=[("Sodium hypochlorite", "7681-52-9", "5-7"), ("Sodium hydroxide", "1310-73-2", "<1"),
              ("Sodium chloride", "7647-14-5", "1-5"), ("Water", "7732-18-5", "85-95")],
        aid=_FIRST_AID_CORROSIVE, phys="Clear pale yellow liquid, chlorine odor; pH 11-12.",
        incompat="Acids (releases chlorine gas), ammonia and ammonia-containing cleaners (releases chloramines), oxidizable organics, metals.",
        fire="Not flammable, but decomposes when heated releasing chlorine. Cool containers with water.",
        spill="Dilute small spills with water and absorb with inert absorbent. Never mix with acid or ammonia cleaners.",
        ppe="Chemical goggles and nitrile gloves for spills.",
        tox="Eye damage on direct contact. Inhalation of mists irritates airways.",
        eco="Toxic to aquatic life before dilution and neutralization.",
    ),
    "AFRS": dict(
        use="Aerosol air freshener", signal="Danger",
        ghs=["Aerosol, Category 1 (H222: Extremely flammable aerosol)",
             "H229: Pressurized container - may burst if heated"],
        comp=[("Butane", "106-97-8", "20-30"), ("Propane", "74-98-6", "5-15"),
              ("Ethanol", "64-17-5", "5-10"), ("Water", "7732-18-5", "40-60")],
        aid=_FIRST_AID_FLAMMABLE, phys="Pressurized aerosol; liquid propellant; flammable.",
        incompat="Heat, sparks, open flames; strong oxidizers.",
        fire="Extremely flammable. Containers may rupture violently (projectile hazard) when heated. Use water spray, foam, dry chemical or CO2; cool containers from a distance.",
        spill="Remove ignition sources. Ventilate. Collect leaking cans into a closed metal drum.",
        ppe="None for intact cans. Gloves when handling damaged cans.",
        tox="Inhalation of high concentrations may cause dizziness.", eco="Not expected to be harmful at use concentrations.",
    ),
    "DEOD": dict(
        use="Aerosol antiperspirant", signal="Danger",
        ghs=["Aerosol, Category 1 (H222: Extremely flammable aerosol)",
             "H229: Pressurized container - may burst if heated"],
        comp=[("Isobutane", "75-28-5", "40-60"), ("Butane", "106-97-8", "10-20"),
              ("Aluminum chlorohydrate", "12042-91-0", "5-10")],
        aid=_FIRST_AID_FLAMMABLE, phys="Pressurized aerosol; white powder spray; flammable.",
        incompat="Heat, sparks, open flames; strong oxidizers.",
        fire="Extremely flammable. Containers may burst when heated. Use water spray, foam, dry chemical or CO2.",
        spill="Remove ignition sources. Collect leaking cans into a closed metal drum.",
        ppe="None for intact cans.", tox="Do not inhale deliberately.", eco="No significant effects expected.",
    ),
    "FPOL": dict(
        use="Aerosol furniture polish (non-flammable propellant)", signal="Warning",
        ghs=["Aerosol, Category 3 (H229: Pressurized container - may burst if heated)"],
        comp=[("Water", "7732-18-5", "60-80"), ("Carbon dioxide (propellant)", "124-38-9", "1-5"),
              ("Paraffin oil", "8012-95-1", "5-10")],
        aid=_FIRST_AID_IRRITANT, phys="Pressurized aerosol; white emulsion; not flammable.",
        incompat="Heat above 50 C.", fire="Not flammable, but containers may burst when heated.",
        spill="Collect damaged cans; wipe residue (slippery).", ppe="None required.",
        tox="Low toxicity.", eco="No significant effects expected.",
    ),
    "HSAN": dict(
        use="Hand sanitizer gel (70% ethanol)", signal="Danger",
        ghs=["Flammable liquid, Category 2 (H225: Highly flammable liquid and vapor)",
             "Eye irritation, Category 2A (H319)"],
        comp=[("Ethanol", "64-17-5", "65-75"), ("Water", "7732-18-5", "20-30"),
              ("Glycerol", "56-81-5", "1-3"), ("Carbomer", "9007-20-9", "<1")],
        aid=_FIRST_AID_FLAMMABLE, phys="Clear gel, alcohol odor; flash point approx. 21 C (closed cup).",
        incompat="Strong oxidizers (pool shock, chlorine tablets, hydrogen peroxide), strong acids.",
        fire="Highly flammable; vapors may travel to ignition source. Use alcohol-resistant foam, dry chemical or CO2.",
        spill="Remove ignition sources. Absorb with non-combustible absorbent; use non-sparking tools.",
        ppe="Goggles; nitrile gloves for spills.", tox="Eye irritant. Ingestion of large amounts causes intoxication.",
        eco="Ethanol is readily biodegradable.",
    ),
    "NPRM": dict(
        use="Nail polish remover", signal="Danger",
        ghs=["Flammable liquid, Category 2 (H225)", "Eye irritation, Category 2A (H319)",
             "Specific target organ toxicity - single exposure, Category 3 (H336: may cause drowsiness or dizziness)"],
        comp=[("Acetone", "67-64-1", "80-95"), ("Water", "7732-18-5", "5-15"), ("Glycerol", "56-81-5", "1-3")],
        aid=_FIRST_AID_FLAMMABLE, phys="Clear volatile liquid; flash point approx. -20 C (closed cup).",
        incompat="Strong oxidizers (hydrogen peroxide, hypochlorites), strong acids, strong bases.",
        fire="Highly flammable; vapors heavier than air. Use alcohol-resistant foam, dry chemical or CO2.",
        spill="Remove ignition sources; ventilate; absorb with non-combustible absorbent.",
        ppe="Goggles; butyl gloves for prolonged contact.", tox="Vapors cause drowsiness at high concentration.",
        eco="Readily biodegradable.",
    ),
    "ETHB": dict(
        use="Ethanol 96% sanitizer base (professional)", signal="Danger",
        ghs=["Flammable liquid, Category 2 (H225)", "Eye irritation, Category 2A (H319)"],
        comp=[("Ethanol", "64-17-5", "94-96"), ("Denaturant", "Proprietary", "1-2"), ("Water", "7732-18-5", "2-5")],
        aid=_FIRST_AID_FLAMMABLE, phys="Clear liquid; flash point approx. 14 C (closed cup).",
        incompat="Strong oxidizers (calcium hypochlorite, TCCA, hydrogen peroxide), strong acids, alkali metals.",
        fire="Highly flammable. Use alcohol-resistant foam, dry chemical or CO2. Cool drums with water spray.",
        spill="Remove ignition sources. Dike and absorb with non-combustible absorbent. Prevent entry to drains.",
        ppe="Goggles, nitrile gloves; respirator in confined spaces.", tox="Eye irritant; CNS depression at high vapor concentration.",
        eco="Readily biodegradable.",
    ),
    "DRNO": dict(
        use="Drain opener gel (sodium hydroxide)", signal="Danger",
        ghs=["Skin corrosion, Category 1A (H314: causes severe skin burns and eye damage)",
             "Corrosive to metals, Category 1 (H290)"],
        comp=[("Sodium hydroxide", "1310-73-2", "10-20"), ("Sodium silicate", "1344-09-8", "1-5"),
              ("Water", "7732-18-5", "70-85")],
        aid=_FIRST_AID_CORROSIVE, phys="Viscous colorless gel; pH > 13.",
        incompat="Acids (violent reaction, heat), aluminum and zinc (hydrogen gas), ammonium salts, oxidizers.",
        fire="Not flammable. Contact with some metals releases flammable hydrogen.",
        spill="Contain with inert absorbent; neutralize carefully with dilute weak acid only under EHS supervision.",
        ppe="Face shield, chemical goggles, alkali-resistant gloves and apron.",
        tox="Corrosive: severe burns to skin, eyes and digestive tract.", eco="Harmful to aquatic life due to pH shift.",
    ),
    "CAUS": dict(
        use="Caustic floor stripper (professional)", signal="Danger",
        ghs=["Skin corrosion, Category 1A (H314)", "Corrosive to metals, Category 1 (H290)"],
        comp=[("Sodium hydroxide", "1310-73-2", "20-30"), ("Water", "7732-18-5", "65-80"),
              ("Alcohols, C9-11, ethoxylated", "68439-46-3", "1-5")],
        aid=_FIRST_AID_CORROSIVE, phys="Clear to amber liquid; pH 14.",
        incompat="Acids, oxidizers (hydrogen peroxide, hypochlorites), aluminum, zinc, tin.",
        fire="Not flammable. Reaction with metals may produce hydrogen.",
        spill="Dike, absorb with inert absorbent. Keep away from oxidizer bay H3.",
        ppe="Face shield, goggles, alkali-resistant gloves, apron and boots.",
        tox="Corrosive.", eco="Harmful to aquatic life due to pH shift.",
    ),
    "BLCC": dict(
        use="Concentrated bleach (12.5% sodium hypochlorite)", signal="Danger",
        ghs=["Skin corrosion, Category 1B (H314)", "Corrosive to metals, Category 1 (H290)",
             "Hazardous to the aquatic environment, acute, Category 1 (H400)",
             "Supplemental: contact with acids liberates toxic gas"],
        comp=[("Sodium hypochlorite", "7681-52-9", "12-13"), ("Sodium hydroxide", "1310-73-2", "<1"),
              ("Sodium chloride", "7647-14-5", "5-10"), ("Water", "7732-18-5", "75-85")],
        aid=_FIRST_AID_CORROSIVE, phys="Clear yellow-green liquid, strong chlorine odor; pH 12-13.",
        incompat="Acids (chlorine gas), ammonia and amines (chloramines), oxidizable organics, metals, hydrogen peroxide (vigorous oxygen release).",
        fire="Not flammable, but an oxidizing solution. Decomposes on heating releasing chlorine and oxygen.",
        spill="Isolate area. Absorb with inert, non-combustible absorbent (no sawdust). Prevent entry to drains.",
        ppe="Chemical goggles and face shield, PVC/neoprene gloves, apron.",
        tox="Corrosive to eyes and skin; mists irritate the respiratory tract.", eco="Very toxic to aquatic life.",
    ),
    "PSHK": dict(
        use="Pool shock (calcium hypochlorite), consumer pack", signal="Danger",
        ghs=["Oxidizing solid, Category 2 (H272: may intensify fire; oxidizer)",
             "Acute toxicity oral, Category 4 (H302)", "Skin corrosion, Category 1B (H314)",
             "Hazardous to the aquatic environment, acute, Category 1 (H400)",
             "Supplemental: contact with acids liberates toxic gas"],
        comp=[("Calcium hypochlorite", "7778-54-3", "65-75"), ("Sodium chloride", "7647-14-5", "10-20"),
              ("Water of hydration", "7732-18-5", "5.5-16")],
        aid=_FIRST_AID_CORROSIVE, phys="White granules, chlorine odor; solution pH 10-11.",
        incompat="**Trichloroisocyanuric acid (TCCA) and other chlorinated isocyanurates - mixing can cause fire or explosion.** Acids, ammonia, organic materials, flammable liquids (ethanol, acetone), reducing agents, small amounts of water.",
        fire="Oxidizer: intensifies fire and can ignite combustibles. Use large amounts of water only. Do not use dry chemical or foam.",
        spill="Sweep up into a clean, dry, dedicated container. Do not use combustible absorbents. Do not return spilled material to the original container.",
        ppe="Goggles, face shield, rubber gloves; dust respirator for spills.",
        tox="Corrosive; harmful if swallowed; dust irritates airways.", eco="Very toxic to aquatic life.",
    ),
    "TCCA": dict(
        use="Chlorine tablets (trichloroisocyanuric acid), professional", signal="Danger",
        ghs=["Oxidizing solid, Category 2 (H272)", "Acute toxicity oral, Category 4 (H302)",
             "Eye irritation, Category 2A (H319)", "STOT single exposure, Category 3 (H335: respiratory irritation)",
             "Hazardous to the aquatic environment, acute 1 / chronic 1 (H400, H410)",
             "Supplemental: contact with acids liberates toxic gas"],
        comp=[("Trichloroisocyanuric acid", "87-90-1", ">95")],
        aid=_FIRST_AID_CORROSIVE, phys="White 3-inch tablets, chlorine odor; solution pH 2.7-3.3.",
        incompat="**Calcium hypochlorite and other hypochlorites - mixing can cause fire or explosion.** Ammonia and ammonium salts, nitrogen-containing compounds, small amounts of water, reducing agents, organics, flammable liquids.",
        fire="Oxidizer. When wetted with small amounts of water may produce nitrogen trichloride (explosive). Use large amounts of water.",
        spill="Collect into a clean, dry, dedicated container. Keep separate from calcium hypochlorite waste.",
        ppe="Goggles, rubber gloves, dust respirator.", tox="Harmful if swallowed; respiratory irritant.",
        eco="Very toxic to aquatic life with long lasting effects.",
    ),
    "HPOX": dict(
        use="Hydrogen peroxide 35% (professional)", signal="Danger",
        ghs=["Oxidizing liquid (H272: may intensify fire; oxidizer)", "Acute toxicity oral, Category 4 (H302)",
             "Serious eye damage, Category 1 (H318)", "STOT single exposure, Category 3 (H335)"],
        comp=[("Hydrogen peroxide", "7722-84-1", "35"), ("Water", "7732-18-5", "65"),
              ("Stabilizers", "Proprietary", "<0.1")],
        aid=_FIRST_AID_CORROSIVE, phys="Clear colorless liquid; pH 2-3; vented drum closures.",
        incompat="Combustible and organic materials, flammable liquids, reducing agents, bases (caustic stripper), metals and metal salts (catalytic decomposition), hypochlorites.",
        fire="Oxidizer; decomposes releasing oxygen, which intensifies fire. Flood with water. Containers may rupture from oxygen pressure.",
        spill="Dilute with large amounts of water. Do not absorb with combustible materials. Keep away from corrosives bay H4 and flammables H2.",
        ppe="Face shield, goggles, PVC or neoprene gloves, apron.",
        tox="Causes serious eye damage; irritates skin and airways.", eco="Decomposes to water and oxygen; harmful at high concentration.",
    ),
}
PROFILES["PSHB"] = {**PROFILES["PSHK"], "use": "Pool shock (calcium hypochlorite), 25 kg professional pail"}


def _section14(fam: Family) -> str:
    hz = fam.hazmat
    if hz is None:
        return "Not regulated as a hazardous material for transport (US DOT)."
    pg = hz.packing_group or "n/a"
    sub = f" ({hz.subsidiary})" if hz.subsidiary else ""
    lq = ("Shipped as **limited quantity** in this package size (see 49 CFR Part 173; "
          "mark per 49 CFR 172.315)." if hz.limited_quantity else
          "Shipped **fully regulated** in this package size: hazard labels, placards and shipping "
          "papers required; subject to the 49 CFR 177.848 segregation table.")
    return (f"| Item | Value |\n|---|---|\n| UN number | {hz.un_number} |\n"
            f"| Proper shipping name | {hz.proper_shipping_name} |\n"
            f"| Hazard class | {hz.hazard_class}{sub} |\n| Packing group | {pg} |\n\n{lq}")


def render_sds(fam: Family) -> str:
    p = PROFILES[fam.code]
    sizes = ", ".join(s[0] for s in fam.sizes)
    comp = "\n".join(f"| {n} | {cas} | {pct} |" for n, cas, pct in p["comp"])
    aid = "\n".join(f"- **{k}:** {v}" for k, v in p["aid"].items())
    ghs = "\n".join(f"- {g}" for g in p["ghs"])
    zone_name = ZONES[fam.zone][0]
    return f"""---
doc_id: SDS-{fam.code}
doc_type: sds
title: "Safety Data Sheet - {fam.brand} {fam.name}"
family_code: {fam.code}
un_number: {fam.hazmat.un_number if fam.hazmat else ''}
hazard_class: {fam.hazmat.hazard_class if fam.hazmat else ''}
revision: {SIM_TODAY}
synthetic: true
---

# Safety Data Sheet - {fam.brand} {fam.name}

## 1. Identification
- **Product:** {fam.brand} {fam.name} ({sizes})
- **Product family code:** {fam.code}
- **Recommended use:** {p['use']}
- **Supplier:** {DC['company']}

## 2. Hazard identification
**Signal word:** {p['signal']}

{ghs}

## 3. Composition / information on ingredients
| Component | CAS number | % (w/w) |
|---|---|---|
{comp}

## 4. First-aid measures
{aid}

## 5. Fire-fighting measures
{p['fire']}

## 6. Accidental release measures
{p['spill']}

## 7. Handling and storage
Handle in accordance with good industrial hygiene. At {DC['code']} store only in zone {fam.zone}
({zone_name}). Keep containers closed. Keep away from: {p['incompat']}

## 8. Exposure controls / personal protection
{p['ppe']}

## 9. Physical and chemical properties
{p['phys']}

## 10. Stability and reactivity
Stable under recommended storage conditions. **Incompatible materials:** {p['incompat']}

## 11. Toxicological information
{p['tox']}

## 12. Ecological information
{p['eco']}

## 13. Disposal considerations
Dispose of via a licensed waste contractor in accordance with local, state and federal
regulations. Do not pour into drains.

## 14. Transport information
{_section14(fam)}

## 15. Regulatory information
Classified according to OSHA Hazard Communication Standard, 29 CFR 1910.1200.

## 16. Other information
Revision date: {SIM_TODAY}. **Synthetic SDS** created for the DC Exception Copilot project:
the product and supplier are fictional and the classification is simplified. Do not use for
real products.
"""


def write_sds() -> int:
    SDS_DIR.mkdir(parents=True, exist_ok=True)
    n = 0
    for fam in FAMILIES:
        if fam.sds:
            (SDS_DIR / f"SDS-{fam.code}.md").write_text(render_sds(fam), encoding="utf-8")
            n += 1
    return n
