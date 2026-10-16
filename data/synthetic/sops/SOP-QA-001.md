---
doc_id: SOP-QA-001
doc_type: sop
title: Quality Hold and Quarantine
version: 1.8
owner: Quality Assurance Specialist
effective: 2025-11-01
references: [SOP-REC-002, SOP-HAZ-004, SOP-INV-001]
synthetic: true
---

# SOP-QA-001 Quality Hold and Quarantine

## 1. Purpose
Make sure product that may be unsafe or out of specification cannot be shipped.

## 2. Triggers for a quality hold (`QUALITY_HOLD`)
- The plant or QA reports a deviation on a lot (fill weight, seal, contamination).
- Customer complaint pointing at a specific lot.
- Missing batch release certificate.
- Damaged or leaking product (after spill response, SOP-HAZ-004).

## 3. Placing a hold
1. QA blocks **all pallets of the lot** in the WMS (status `hold`). Blocked stock cannot be
   allocated.
2. Pallets already allocated to a shipment are de-allocated; the transportation planner is
   told which shipments are affected.
3. Physically move held pallets to zone Q within 4 hours when space allows. Pallets in zone Q
   have status `quarantine`.
4. Hazmat in zone Q stays segregated by class inside the quarantine area (oxidizers apart from
   flammables and corrosives).

## 4. Releasing or disposing
- **Release:** QA signs off; status back to `available`; pallets return to the home zone.
- **Rework:** relabel/repack under QA supervision, then release.
- **Destroy:** hazardous waste goes via the licensed contractor only. Never pour hazmat
  product into drains.

## 5. Timing
A hold must be dispositioned within 10 working days. Open holds older than 10 days are listed
in the weekly operations review.
