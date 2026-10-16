---
doc_id: SOP-HAZ-004
doc_type: sop
title: Spill and Leak Response
version: 4.1
owner: EHS Coordinator
effective: 2026-01-15
references: [SOP-HAZ-001, SOP-QA-001, SOP-ESC-001, 29 CFR 1910.1200, 49 CFR 177.834]
synthetic: true
---

# SOP-HAZ-004 Spill and Leak Response

## 1. Purpose
Respond to leaking containers of hazardous materials safely and consistently.

## 2. Immediate actions (anyone who finds a leak)
1. **Stop** - stop work in the area and warn others.
2. **Isolate** - keep people at least 10 m away; block the aisle with cones.
3. **Identify** - read the product name / SKU from the case label. Do not touch the liquid.
4. **Call** - radio the shift supervisor and the EHS coordinator.

## 3. Assess (shift supervisor + EHS coordinator)
1. Open the Safety Data Sheet for the product. Use:
   - Section 2 - hazards;
   - Section 6 - accidental release measures;
   - Section 8 - personal protective equipment;
   - Section 10 - incompatible materials.
2. Check what is nearby. A leak of a corrosive (class 8) or flammable (class 3) near the
   oxidizer bay H3 is treated as **high severity** because mixing can cause fire or toxic gas.
3. Chlorine-releasing products (bleach, calcium hypochlorite, TCCA) must not contact acids or
   ammonia-based products.

## 4. Contain and clean up
| Spill size | Who | How |
|---|---|---|
| Small (< 4 L or a few cases), no reaction | Trained DC staff with PPE from SDS section 8 | Zone spill kit, compatible absorbent |
| Large, reacting, fumes, or near H3 | Evacuate zone; EHS calls emergency services | Do not attempt clean-up |

Use the absorbent specified in the SDS. Never use sawdust or other combustible absorbents on
oxidizers.

## 5. After clean-up
1. Move damaged and leaking product to zone Q (status `quarantine`) and place a quality hold
   (SOP-QA-001).
2. Collect waste in labeled containers for the licensed waste contractor.
3. Log a `LEAK_SPILL` exception with the zone, SKU, estimated quantity and root cause.
4. If a leak was found inside an inbound trailer, record it on the bill of lading and inform
   the carrier: hazmat packages must be secured against shifting in transport
   (49 CFR 177.834(a)), and a shifted load is a common root cause.

## 6. Reporting
The EHS coordinator decides within 2 hours whether the release is externally reportable and
records the decision in the incident report.
