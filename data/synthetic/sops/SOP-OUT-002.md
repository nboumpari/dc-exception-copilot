---
doc_id: SOP-OUT-002
doc_type: sop
title: Carrier Delays, Cut-offs and Customer Notification
version: 2.2
owner: Transportation Planner
effective: 2026-03-15
references: [SOP-OUT-001, SOP-HAZ-002, SOP-ESC-001]
synthetic: true
---

# SOP-OUT-002 Carrier Delays, Cut-offs and Customer Notification

## 1. Purpose
Handle shipments at risk of departing late and keep customers informed.

## 2. Definitions
- **On time:** departs no more than 60 minutes after planned departure.
- **Late:** departs more than 60 minutes after planned departure.
- **Exception threshold:** a `LATE_CARRIER` exception is logged when departure is more than
  2 hours late (severity medium) or more than 5 hours late (severity high).

## 3. At-risk checks (transportation planner, every day at 15:00 for next day)
A shipment is **at risk** when any of these is true:
1. No trailer assigned the afternoon before an early departure (before 08:00).
2. Carrier on-time rate over the last 30 days is below 85%.
3. The carrier is not hazmat-endorsed but the load has fully regulated hazmat (this is a
   compliance problem, not only a delay risk - reassign immediately, SOP-HAZ-002 step 4).
4. Pallets not yet picked 4 hours before departure.

## 4. Actions for at-risk shipments
1. Call the carrier and confirm the trailer and driver ETA.
2. If the carrier cannot confirm within 1 hour, book a backup carrier from the routing guide.
   For hazmat loads only hazmat-endorsed carriers may be used.
3. Notify the customer if the revised ETA is more than 2 hours later than promised. Use the
   template: shipment ID, original ETA, new ETA, reason, contact person.
4. Log the outcome on the shipment record.

## 5. Carrier performance
Carrier on-time performance is reviewed monthly. A carrier below 85% on-time for two
consecutive months is escalated to the carrier account manager. Cardinal Carriers is currently
under performance review.
