---
doc_id: SOP-INV-001
doc_type: sop
title: Cycle Counting and Inventory Variances
version: 2.1
owner: Inventory Control Lead
effective: 2026-02-01
references: [SOP-PUT-001, SOP-QA-001]
synthetic: true
---

# SOP-INV-001 Cycle Counting and Inventory Variances

## 1. Purpose
Keep system inventory accurate so orders are allocated against stock that really exists.

## 2. Count frequency
| Class | Which SKUs | Frequency |
|---|---|---|
| A | Top 20% by outbound volume, and all hazmat SKUs | Every 2 weeks |
| B | Next 30% | Monthly |
| C | Remaining SKUs | Quarterly |

Hazmat SKUs are always class A because a lost hazmat pallet is a safety issue, not only a
financial one.

## 3. Counting
1. Counts are blind: the counter does not see the system quantity.
2. Count full cases; partial cases are counted as units and converted.
3. Scan the pallet SSCC and the location.

## 4. Variances (`INVENTORY_MISMATCH`)
1. Any variance triggers a recount by a **second** counter.
2. If the recount confirms the variance, search adjacent bays and levels before adjusting.
3. Adjust the system only after the search. Variances above 10 cases or any hazmat variance
   require approval of the inventory control lead.
4. A missing hazmat pallet that cannot be found within one shift is escalated to the EHS
   coordinator (SOP-ESC-001).

## 5. Root causes to record
Wrong-location putaway, wrong-variant pick, unrecorded damage write-off, receiving miscount.
