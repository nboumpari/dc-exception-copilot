---
doc_id: SOP-OUT-001
doc_type: sop
title: Outbound Loading and Trailer Inspection
version: 3.3
owner: Shift Supervisor
effective: 2026-02-01
references: [SOP-HAZ-002, SOP-OUT-002, 49 CFR 177.834]
synthetic: true
---

# SOP-OUT-001 Outbound Loading and Trailer Inspection

## 1. Purpose
Load outbound trailers safely, completely and on time.

## 2. Before loading
1. Trailer must be assigned in the WMS (`shipments.trailer_id`) and checked in at the gate.
2. Inspect the trailer: floor intact, no holes in walls or roof, clean, dry, no odor. A trailer
   that fails inspection is rejected and the carrier asked for a replacement (SOP-OUT-002).
3. Chock wheels and engage the dock lock.
4. For hazmat shipments the hazmat shipping clerk must complete SOP-HAZ-002 checks first.

## 3. Loading
1. Scan every pallet SSCC as it is loaded; the WMS blocks pallets that are not allocated to the
   shipment or are on hold.
2. Load heavy pallets first and on the floor; do not double-stack hazmat drums.
3. Secure the load with load bars or straps. Hazmat packages must be secured against shifting
   (49 CFR 177.834(a)).
4. Photograph the load before closing doors.

## 4. Departure
1. Seal the trailer and record the seal number.
2. Hand over shipping papers (hazmat) and the bill of lading.
3. Confirm departure in the WMS - this records `actual_departure`.

## 5. Staging deadlines
Pallets must be staged in zone D at least 2 hours before planned departure. Loads not staged
in time are escalated to the shift supervisor.
