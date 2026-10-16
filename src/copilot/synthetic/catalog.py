"""The fictional DC, its products, partners and storage zones.

Everything here is invented EXCEPT the hazmat classification fields (UN number, proper
shipping name, class, packing group), which were taken from the 49 CFR 172.101
Hazardous Materials Table in data/raw/ so the data is consistent with the regulations
the copilot retrieves from.
"""

from dataclasses import dataclass

DC = {
    "code": "DC-COL1",
    "name": "Meridian Consumer Goods - Columbus Distribution Center",
    "company": "Meridian Consumer Goods (fictional)",
    "address": "4100 Logistics Pkwy, Columbus, OH 43217, USA",
    "jurisdiction": "US (OSHA 29 CFR 1910, DOT 49 CFR)",
}

# Simulation clock: history runs up to SIM_TODAY, planned work runs a few days past it.
SIM_TODAY = "2026-10-16"
SIM_NOW = f"{SIM_TODAY} 18:00"  # the moment the copilot is "used" in demos and evaluation
HISTORY_DAYS = 90
FUTURE_DAYS = 3

ZONES = {
    "A": ("Ambient racking", "General merchandise, selective pallet racking"),
    "B": ("Fast-pick", "High-velocity SKUs, ground-level pick faces"),
    "H1": ("Aerosol cage", "Class 2.1/2.2 aerosols, mesh-enclosed, sprinklered"),
    "H2": ("Flammable liquids room", "Class 3 liquids, fire-rated room per 29 CFR 1910.106"),
    "H3": ("Oxidizer bay", "Class 5.1 oxidizers, separated from H2 and H4 by 6 m and curb"),
    "H4": ("Corrosives bay", "Class 8 corrosives, bunded floor, eyewash station"),
    "Q": ("Quarantine", "Quality hold, damaged and leaking goods"),
    "D": ("Dock staging", "Inbound/outbound staging lanes in front of doors 1-24"),
}


@dataclass(frozen=True)
class Hazmat:
    un_number: str
    proper_shipping_name: str
    hazard_class: str
    subsidiary: str  # "" if none
    packing_group: str  # "" for classes without PG (e.g. aerosols, batteries)
    limited_quantity: bool  # shipped under LQ provisions (consumer sizes)


@dataclass(frozen=True)
class Family:
    code: str
    name: str
    brand: str
    category: str
    zone: str
    sizes: tuple[tuple[str, int, float], ...]  # (pack size, units per case, case kg)
    variants: tuple[str, ...]
    cases_per_pallet: int
    hazmat: Hazmat | None = None
    sds: bool = False  # generate a Safety Data Sheet for this family
    channel: str = "retail"  # "retail" | "professional"


FAMILIES: tuple[Family, ...] = (
    # --- non-hazardous consumer goods ---
    Family("LQD", "Liquid Laundry Detergent", "Brightwash", "Fabric care", "A",
           (("1.47 L", 6, 9.8), ("2.95 L", 4, 12.9)), ("Original", "Free & Clear", "Spring Rain"),
           48, sds=True),
    Family("PODS", "Laundry Detergent Pods", "Brightwash", "Fabric care", "B",
           (("42 ct", 4, 6.1), ("81 ct", 4, 11.3)), ("Original", "Oxi"), 60, sds=True),
    Family("DISH", "Dishwashing Liquid", "Puro", "Home care", "B",
           (("650 mL", 12, 8.9),), ("Lemon", "Original", "Sensitive"), 70),
    Family("SHMP", "Shampoo", "Silkara", "Hair care", "A",
           (("400 mL", 12, 5.6),), ("Repair", "Volume", "Anti-dandruff"), 90),
    Family("DIAP", "Baby Diapers", "Softy", "Baby care", "A",
           (("Size 3 x 84", 2, 4.4), ("Size 5 x 64", 2, 4.9)), ("Standard",), 36),
    Family("PTWL", "Paper Towels", "Fluffa", "Family care", "A",
           (("6 rolls", 4, 3.9),), ("Standard",), 30),
    Family("RAZR", "Razor Cartridges", "Edgeline", "Grooming", "B",
           (("8 ct", 24, 2.1),), ("3-blade", "5-blade"), 120),
    Family("HBLC", "Household Bleach 6%", "Puro", "Home care", "A",
           (("3.78 L", 3, 12.2),), ("Regular", "Splashless"), 54, sds=True),
    # --- limited-quantity hazmat (consumer sizes) ---
    Family("AFRS", "Air Freshener Aerosol", "Fresha", "Air care", "H1",
           (("250 mL", 12, 3.9),), ("Linen", "Citrus", "Lavender", "Unscented"), 100,
           Hazmat("UN1950", "Aerosols, flammable", "2.1", "", "", True), sds=True),
    Family("DEOD", "Antiperspirant Spray", "Silkara", "Personal care", "H1",
           (("150 mL", 12, 2.4),), ("Men Sport", "Women Fresh"), 120,
           Hazmat("UN1950", "Aerosols, flammable", "2.1", "", "", True), sds=True),
    Family("FPOL", "Furniture Polish Aerosol (non-flammable)", "Puro", "Home care", "H1",
           (("300 mL", 12, 4.6),), ("Lemon",), 90,
           Hazmat("UN1950", "Aerosols, non-flammable", "2.2", "", "", True), sds=True),
    Family("HSAN", "Hand Sanitizer Gel 70% Ethanol", "Puro", "Health care", "H2",
           (("500 mL", 12, 6.8),), ("Original", "Aloe"), 80,
           Hazmat("UN1170", "Ethanol solution", "3", "", "II", True), sds=True),
    Family("NPRM", "Nail Polish Remover (Acetone)", "Silkara", "Beauty", "H2",
           (("200 mL", 24, 5.3),), ("Original",), 100,
           Hazmat("UN1090", "Acetone", "3", "", "II", True), sds=True),
    Family("DRNO", "Drain Opener Gel", "CleanPro", "Home care", "H4",
           (("1 L", 6, 7.4),), ("Max Gel",), 70,
           Hazmat("UN1824", "Sodium hydroxide solution", "8", "", "II", True), sds=True),
    Family("BLCC", "Concentrated Bleach 12.5%", "CleanPro", "Home care", "H4",
           (("3.78 L", 4, 17.1),), ("Regular",), 40,
           Hazmat("UN1791", "Hypochlorite solution", "8", "", "III", True), sds=True),
    Family("PSHK", "Pool Shock (Calcium Hypochlorite)", "AquaShock", "Pool care", "H3",
           (("454 g", 24, 11.6),), ("Standard",), 48,
           Hazmat("UN2880", "Calcium hypochlorite, hydrated mixture", "5.1", "", "II", True),
           sds=True),
    Family("ETBR", "Electric Toothbrush (Li-ion)", "Edgeline", "Oral care", "B",
           (("1 unit", 6, 2.2),), ("Pro 3000", "Kids"), 140,
           Hazmat("UN3481", "Lithium ion batteries contained in equipment", "9", "", "", True)),
    # --- fully regulated hazmat (professional / bulk channel) ---
    Family("PSHB", "Pool Shock Bulk Pail", "AquaShock", "Pool care (professional)", "H3",
           (("25 kg pail", 1, 26.4),), ("Standard",), 36,
           Hazmat("UN2880", "Calcium hypochlorite, hydrated mixture", "5.1", "", "II", False),
           sds=True, channel="professional"),
    Family("TCCA", "Chlorine Tablets (TCCA)", "AquaShock", "Pool care (professional)", "H3",
           (("20 kg pail", 1, 21.0),), ("3-inch",), 36,
           Hazmat("UN2468", "Trichloroisocyanuric acid, dry", "5.1", "", "II", False),
           sds=True, channel="professional"),
    Family("HPOX", "Hydrogen Peroxide 35%", "CleanPro", "Janitorial (professional)", "H3",
           (("20 L drum", 1, 23.5),), ("Stabilized",), 24,
           Hazmat("UN2014", "Hydrogen peroxide, aqueous solution", "5.1", "8", "II", False),
           sds=True, channel="professional"),
    Family("CAUS", "Caustic Floor Stripper", "CleanPro", "Janitorial (professional)", "H4",
           (("20 L drum", 1, 25.8),), ("Heavy Duty",), 24,
           Hazmat("UN1824", "Sodium hydroxide solution", "8", "", "II", False),
           sds=True, channel="professional"),
    Family("ETHB", "Ethanol 96% Sanitizer Base", "Puro", "Janitorial (professional)", "H2",
           (("20 L drum", 1, 17.9),), ("Denatured",), 24,
           Hazmat("UN1170", "Ethanol", "3", "", "II", False),
           sds=True, channel="professional"),
)

SUPPLIERS = (
    ("S-001", "Meridian Plant Lima (OH)", "internal plant", 0.01),
    ("S-002", "Meridian Plant Cape Girardeau (MO)", "internal plant", 0.02),
    ("S-007", "Northgate Aerosol Fillers", "contract manufacturer", 0.03),
    ("S-009", "Lakeshore Chemicals", "contract manufacturer", 0.04),
    ("S-011", "Pinecrest Paper Co.", "contract manufacturer", 0.02),
    ("S-014", "Delta Copack Services", "co-packer", 0.12),  # chronic label problems
    ("S-016", "AquaChem Industries", "contract manufacturer", 0.05),
)  # (id, name, type, base probability of a label/SSCC defect per pallet)

CARRIERS = (
    ("C-RDG", "Ridgeline Freight", True, 0.94),
    ("C-BLU", "BlueLine Logistics", True, 0.89),
    ("C-SUM", "Summit Express", False, 0.96),
    ("C-CRD", "Cardinal Carriers", True, 0.78),  # unreliable, used for the at-risk demo
    ("C-HWY", "Highway 70 Transport", False, 0.91),
)  # (id, name, hazmat_endorsed, on-time rate)

CUSTOMERS = (
    ("K-VAL", "ValueMart Regional DC", "Indianapolis, IN", "retail"),
    ("K-FRC", "FreshCo Grocery", "Cincinnati, OH", "retail"),
    ("K-CTP", "CityPharm Drugstores", "Pittsburgh, PA", "retail"),
    ("K-HOM", "HomeBase Stores", "Louisville, KY", "retail"),
    ("K-GLM", "Great Lakes Market", "Cleveland, OH", "retail"),
    ("K-PRO", "ProClean Janitorial Supply", "Detroit, MI", "professional"),
    ("K-AQP", "AquaPool Supply", "Lexington, KY", "professional"),
)

EMPLOYEES = (  # invented names; roles drive who appears in incident reports
    ("E-101", "Dana Whitfield", "Shift Supervisor"),
    ("E-102", "Marco Ruiz", "Shift Supervisor"),
    ("E-103", "Priya Natarajan", "EHS Coordinator"),
    ("E-104", "Tom Becker", "Inventory Control Lead"),
    ("E-105", "Aisha Coleman", "Transportation Planner"),
    ("E-106", "Kevin O'Brien", "Receiving Lead"),
    ("E-107", "Lena Hoffmann", "Quality Assurance Specialist"),
    ("E-108", "Sam Okafor", "Forklift Operator"),
    ("E-109", "Jess Morales", "Forklift Operator"),
    ("E-110", "Ravi Shah", "Hazmat Shipping Clerk"),
)
