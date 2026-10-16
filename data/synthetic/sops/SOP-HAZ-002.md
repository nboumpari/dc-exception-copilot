---
doc_id: SOP-HAZ-002
doc_type: sop
title: Hazmat Outbound Load Planning and Segregation Check
version: 2.6
owner: Hazmat Shipping Clerk
effective: 2026-04-01
references: [SOP-HAZ-001, SOP-HAZ-003, SOP-OUT-001, 49 CFR 177.848, 49 CFR 177.834]
synthetic: true
---

# SOP-HAZ-002 Hazmat Outbound Load Planning and Segregation Check

## 1. Purpose
Prevent incompatible hazardous materials from being loaded on the same trailer, and make
sure hazmat loads go only with carriers authorized to haul them.

## 2. When this SOP applies
Any outbound shipment where `hazmat_on_board = 1`. The checks in section 4 are mandatory for
shipments that contain **fully regulated** hazmat (packages that must be labeled or placarded),
which at DC-COL1 means the professional-channel drums and pails.

## 3. Key rule: 49 CFR 177.848 segregation table
The segregation table in 49 CFR 177.848(d) shows, for each pair of hazard classes, whether
they may be loaded together:
- **X** - may not be loaded, transported or stored together in the same vehicle.
- **O** - may not be loaded together **unless separated** so that, if packages leak, the
  materials cannot commingle. In addition, Class 8 corrosive liquids may not be loaded above
  or adjacent to Class 4 or Class 5 materials.
- blank - no restriction.

Pairs that matter in our catalog:
| Pair | Table value | What it means for us |
|---|---|---|
| 3 + 5.1 | O | Ethanol base + pool shock / TCCA / peroxide: separate trailers (DC policy) |
| 5.1 + 8 (liquids) | O | Peroxide / pool shock + caustic stripper / bleach: separate trailers (DC policy) |
| 2.1 + 3 | blank | Aerosols + flammable liquids may ride together |
| 5.1 + 5.1 | blank | Allowed by the table - **but see the chemical rule below** |

**Chemical incompatibility the table does not show:** calcium hypochlorite (pool shock) and
TCCA (chlorine tablets) are both class 5.1, so the table allows them together, yet their SDS
(section 10) warns that mixing can cause fire or explosion. DC policy: they may share a trailer
only on separate pallets, never adjacent, never in the same overpack, with a non-hazmat pallet
or an empty pallet space between them. Always check SDS section 10 in addition to the table.

**DC policy:** although "O" allows loading with adequate separation, DC-COL1 does not attempt
in-trailer separation. Any "O" pair is split onto separate trailers. Exceptions require
written approval from the EHS coordinator.

## 4. Load planning steps
1. The transportation planner runs the segregation check in the WMS when the load is built
   **and again if any order line changes**.
2. Ignore limited-quantity lines for the table check: per 177.848(a) the section applies to
   packages that must be labeled or placarded, and limited-quantity packages are excepted
   from hazard labels (see SOP-HAZ-003).
3. If a conflict is found, move all class 5.1 pallets to a separate shipment.
4. Confirm the carrier is **hazmat-endorsed** in the carrier master. Non-endorsed carriers
   (e.g. Summit Express, Highway 70 Transport) may only take shipments with no fully regulated
   hazmat. Reassign the load if needed.
5. The hazmat shipping clerk prints shipping papers and checks placards with the driver.

## 5. At the dock (final check)
1. The hazmat shipping clerk re-checks the actual pallets on the trailer against the shipping
   papers.
2. All hazmat packages must be secured against shifting, including movement between packages
   (49 CFR 177.834(a)). Use load bars or straps.
3. If an incompatible pair is found on the trailer: stop loading, log a `HAZMAT_SEGREGATION`
   exception (severity high), unload the 5.1 pallets and re-plan.

## 6. Escalation
A segregation conflict found after the trailer has departed is a reportable internal event:
call the EHS coordinator immediately and contact the carrier (SOP-ESC-001).
