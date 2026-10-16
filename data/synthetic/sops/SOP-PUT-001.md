---
doc_id: SOP-PUT-001
doc_type: sop
title: Putaway and Storage Zone Assignment
version: 4.0
owner: Inventory Control Lead
effective: 2026-01-15
references: [SOP-HAZ-001, 29 CFR 1910.176, 29 CFR 1910.106]
synthetic: true
---

# SOP-PUT-001 Putaway and Storage Zone Assignment

## 1. Purpose
Put every received pallet into the correct storage zone, safely and so the WMS location is
always accurate.

## 2. Storage zones at DC-COL1
| Zone | Name | What goes there |
|---|---|---|
| A | Ambient racking | General merchandise, selective racking, 5 levels |
| B | Fast-pick | High-velocity SKUs, ground-level pick faces |
| H1 | Aerosol cage | Class 2.1 / 2.2 aerosols, mesh-enclosed, sprinklered |
| H2 | Flammable liquids room | Class 3 liquids, fire-rated room |
| H3 | Oxidizer bay | Class 5.1 oxidizers |
| H4 | Corrosives bay | Class 8 corrosives, bunded floor, eyewash station |
| Q | Quarantine | Quality hold, damaged and leaking goods |
| D | Dock staging | Inbound and outbound staging lanes |

The SKU master (`skus.storage_zone`) defines the home zone. Hazmat SKUs may **never** be put
away outside their H-zone, even temporarily, except into zone Q after a leak.

## 3. Putaway steps
1. Scan the pallet SSCC, then scan the location barcode. The WMS rejects a location in the
   wrong zone.
2. Check the pallet is stable and wrapped. Unstable loads must be restacked before lifting
   (29 CFR 1910.176(b)).
3. Keep aisles and passageways clear; never leave a pallet in a marked aisle
   (29 CFR 1910.176(a)).
4. Heavy pallets (>900 kg) go on levels 1-2 only.

## 4. Flammable liquids (zone H2)
Class 3 liquids are stored only in the H2 flammable liquids room, built and operated to
29 CFR 1910.106 (container and portable tank storage). Ignition sources are prohibited in H2.
Only electric forklifts approved for the area may enter.

## 5. If the target location is full
Choose another location **in the same zone**. If the zone is full, call the inventory control
lead. Do not overflow hazmat into zone A.
