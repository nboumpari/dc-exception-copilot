---
doc_id: SOP-REC-002
doc_type: sop
title: Inbound Label and Damage Exceptions
version: 2.4
owner: Receiving Lead
effective: 2026-03-01
references: [SOP-REC-001, SOP-QA-001, SOP-HAZ-004, GS1 Logistic Label Guideline, GS1 General Specifications §2.2.1, 29 CFR 1910.176(b)]
synthetic: true
---

# SOP-REC-002 Inbound Label and Damage Exceptions

## 1. Purpose
Handle inbound pallets that cannot be received normally: missing or unreadable GS1 logistic
labels, and physically damaged pallets.

## 2. Background: why the SSCC matters
Every logistic unit must be identified with a unique Serial Shipping Container Code (SSCC),
encoded in a GS1-128 barcode with Application Identifier (00). The DC uses the SSCC to link the
physical pallet to the ASN, lot, and location. A pallet without a valid SSCC cannot be tracked
or recalled and must not enter storage.

GS1 guidance on label placement (GS1 Logistic Label Guideline §8.1): for all pallets the
barcodes SHALL be positioned between 400 mm and 800 mm from the base of the pallet (rule
[8-1]), and it is recommended that two sides of the pallet carry identical labels so one is
always visible. **DC policy makes the two-sided label mandatory** for pallets relabeled here.

## 3. Missing SSCC label (`MISSING_SSCC`)
1. Move the pallet to the exception lane in zone D. Do not put away.
2. Match the pallet to the ASN line using product, lot and case count.
3. If the match is unambiguous, print a DC SSCC label (company prefix 0614141) and apply it on
   two sides of the pallet. Record the supplier SSCC from the ASN as the "expected SSCC" in the
   exception note. Apply labels so the barcode is 400-800 mm from the pallet base.
4. If the match is ambiguous (two ASN lines with the same SKU), escalate to the receiving lead.
5. Log a `MISSING_SSCC` exception. Severity **medium** if 3 or more pallets on one receipt are
   affected or the supplier is on the enhanced inspection list; otherwise **low**.

## 4. Unreadable barcode (`UNREADABLE_LABEL`)
1. Try a second scanner. If it still fails, check the human-readable SSCC text under the barcode.
2. The SSCC may be keyed manually **only** with two-person verification (receiver + lead) and
   only if the check digit validates.
3. Relabel the pallet with a DC-printed label so it scans at every later step.
4. Log `UNREADABLE_LABEL` and note the probable cause (low contrast, wrinkled label, quiet zone
   violated, wet label).

## 5. Damaged pallet (`DAMAGED_INBOUND`)
1. Photograph the damage and note it on the bill of lading **before** the driver leaves.
2. Material must be stored so it is stable and secure against sliding or collapse
   (29 CFR 1910.176(b)). A leaning or broken pallet is restacked onto a new pallet before
   putaway.
3. Damaged cases are moved to zone Q and dispositioned per SOP-QA-001.
4. If the damaged product is a hazardous material and anything is leaking, stop and switch to
   SOP-HAZ-004.

## 6. Supplier follow-up
- Two or more label exceptions from the same supplier in 30 days: supplier is added to the
  enhanced inspection list and receives a supplier quality notice.
- Delta Copack Services (S-014) is on the enhanced inspection list until further notice.
- Monthly label performance by supplier is reviewed in the partner review meeting.
