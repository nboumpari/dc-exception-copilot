---
doc_id: SOP-HAZ-003
doc_type: sop
title: Limited Quantity Shipments and Markings
version: 1.9
owner: Hazmat Shipping Clerk
effective: 2026-02-15
references: [SOP-HAZ-002, SOP-REC-001, 49 CFR 172.315, 49 CFR 173.306, 49 CFR 173.150]
synthetic: true
---

# SOP-HAZ-003 Limited Quantity Shipments and Markings

## 1. Purpose
Most consumer-size hazmat products we ship (aerosols, hand sanitizer, nail polish remover,
drain opener, concentrated bleach, pool shock 454 g) travel as **limited quantities (LQ)**.
This SOP explains what that means and how to check LQ markings.

## 2. What limited quantity means
A limited quantity is a hazardous material packed in small inner packagings within the
limits set in 49 CFR Part 173 for that class, for example:
- aerosols and small compressed-gas receptacles: 49 CFR 173.306;
- Class 3 flammable liquids: 49 CFR 173.150.

LQ packages are relieved of several requirements (for example, they do not need hazard
labels), but **they are still hazardous materials** and must carry the limited quantity
marking. When unsure whether a relief applies, ask the hazmat shipping clerk - do not guess.

## 3. The limited quantity marking (49 CFR 172.315)
- A package prepared under the limited quantity requirements and offered by a mode other
  than air must display the **limited quantity marking**: a square-on-point with black top and
  bottom sections and a white center.
- The marking must be durable, legible and on a background of contrasting color.
- When LQ cases are stretch-wrapped on a pallet (an overpack), the marking must be visible
  from outside, or the overpack itself must be marked.

## 4. Receiving check
At receiving (SOP-REC-001), for every LQ SKU confirm the LQ mark is visible on the overpack.
If not: log `MISSING_HAZMAT_MARKING` (severity medium), apply an LQ mark to the overpack, and
inform the supplier.

## 5. Shipping check
Before an LQ pallet leaves:
1. LQ marking visible on at least two sides of the overpack.
2. Pallet weight on the shipment record.
3. Do not mix LQ and fully regulated packages of the same product on one pallet.

## 6. Important for load planning
LQ status affects the segregation check (SOP-HAZ-002 section 4 step 2): LQ packages are not
required to bear hazard labels, so the 177.848 segregation table does not apply to them.
Fully regulated drums and pails of the same chemistry (e.g. pool shock 25 kg pail) **are**
subject to the table.
