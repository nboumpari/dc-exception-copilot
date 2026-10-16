---
doc_id: SOP-ESC-001
doc_type: sop
title: Exception Escalation Matrix
version: 1.5
owner: Site Operations Manager
effective: 2026-04-01
references: [SOP-REC-002, SOP-HAZ-002, SOP-HAZ-004, SOP-MHE-001, SOP-OUT-002, SOP-QA-001]
synthetic: true
---

# SOP-ESC-001 Exception Escalation Matrix

## 1. Purpose
Define who must be told about which exception, and how fast.

## 2. Severity levels
| Severity | Meaning |
|---|---|
| Low | Operational issue, no safety or compliance impact, fixable within the shift |
| Medium | Customer or supplier impact, or a compliance gap caught before harm |
| High | Safety risk, regulatory non-compliance, or significant customer impact |

## 3. Escalation matrix
| Exception type | Owner | Escalate to | Within |
|---|---|---|---|
| MISSING_SSCC, UNREADABLE_LABEL | Receiving Lead | Supplier quality (medium) | 1 working day |
| DAMAGED_INBOUND, QTY_DISCREPANCY | Receiving Lead | Purchasing | 1 working day |
| MISSING_HAZMAT_MARKING | Hazmat Shipping Clerk | EHS Coordinator | Same shift |
| HAZMAT_SEGREGATION | Hazmat Shipping Clerk | EHS Coordinator + Site Ops Manager | Immediately |
| LEAK_SPILL | EHS Coordinator | Site Ops Manager (high: emergency services) | Immediately |
| FORKLIFT_NEAR_MISS | EHS Coordinator | Site Ops Manager | Same shift |
| LATE_CARRIER | Transportation Planner | Customer service (if ETA +2 h) | 1 hour |
| INVENTORY_MISMATCH | Inventory Control Lead | EHS if hazmat pallet missing | 1 shift |
| QUALITY_HOLD | QA Specialist | Customer service if orders affected | 4 hours |

## 4. Incident reports
Every medium or high exception gets an incident report (INC-xxxx) with summary, timeline, root
cause, corrective actions and references. Reports are reviewed weekly; recurring root causes
are raised at the monthly partner review.

## 5. Decisions the copilot may not take
The DC Exception Copilot may **suggest** actions and **draft** messages, but a person must
approve before anything is sent to a carrier, supplier or customer, and only the EHS
coordinator may approve exceptions to hazmat segregation policy.
