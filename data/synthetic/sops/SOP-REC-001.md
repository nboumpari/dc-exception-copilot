---
doc_id: SOP-REC-001
doc_type: sop
title: Inbound Receiving and ASN Reconciliation
version: 3.2
owner: Receiving Lead
effective: 2026-03-01
references: [SOP-REC-002, SOP-PUT-001, SOP-HAZ-003, GS1 Logistic Label Guideline]
synthetic: true
---

# SOP-REC-001 Inbound Receiving and ASN Reconciliation

## 1. Purpose
Receive inbound trailers safely, verify that what arrived matches the Advance Shipping
Notice (ASN), and release pallets for putaway with a scannable GS1 SSCC on every pallet.

## 2. Scope
All inbound receipts at DC-COL1 doors 1-8, from internal plants, contract manufacturers
and co-packers. Returns are covered by a separate procedure.

## 3. Before the trailer arrives
1. The receiving lead reviews tomorrow's expected receipts in the WMS by 16:00 the day before.
2. Receipts from suppliers on the **enhanced inspection list** are flagged. A supplier is put
   on the list for 30 days after two or more label exceptions in a rolling 30-day window
   (see SOP-REC-002 section 6).
3. Receipts that contain hazardous materials are assigned to a hazmat-trained receiver.

## 4. Unloading and checks
1. Chock the trailer wheels and verify the dock lock is engaged before any forklift enters
   the trailer.
2. Inspect the trailer for visible leaks, odor or damage **before** unloading. If a leak of a
   hazardous material is suspected, stop and follow SOP-HAZ-004.
3. For each pallet:
   - Scan the SSCC on the GS1 logistic label (AI (00)).
   - If the label is missing or the barcode does not scan, do not key a number from memory.
     Move the pallet to the exception lane and follow SOP-REC-002.
   - For hazmat SKUs, confirm hazard markings are visible (limited-quantity mark or hazard
     labels). Missing markings: follow SOP-HAZ-003.
4. Count cases on any mixed pallet and on 1 in 10 single-SKU pallets.

## 5. ASN reconciliation
| Variance | Action |
|---|---|
| Cases short or over by <= 2% of line | Receive physical count, log `QTY_DISCREPANCY` (low) |
| Cases short or over by > 2% of line | Receive physical count, log `QTY_DISCREPANCY`, notify supplier same day |
| Unexpected SKU on trailer | Hold in dock staging (zone D), contact purchasing before receiving |
| Pallets damaged | Follow SOP-REC-002 section 5 |

Always receive the **physical** quantity. Never force the receipt to match the ASN.

## 6. Release for putaway
A pallet is released to putaway (SOP-PUT-001) only when it has a scanned SSCC, the quantity
is confirmed and no exception is open against it.

## 7. Records
Receipt status in the WMS: `received` or `received_with_exceptions`. Exceptions are logged
in the exception log with the receipt ID as reference.
