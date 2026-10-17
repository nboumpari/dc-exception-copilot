# Agent evaluation

Model `gpt-5.4-mini` (reasoning: low), judge `gpt-5.4`. 36 cases x 3 run(s).

**Pass rate: 87%** (runs: 86%, 86%, 89%) - a case passes when every check scores 1.

| Metric | Score | Answers |
|---|---|---|
| action | 100% | 108 |
| citations_valid | 99% | 108 |
| judge_complete | 92% | 108 |
| judge_correct | 99% | 108 |
| key_facts | 97% | 99 |
| no_forbidden | 100% | 18 |
| required_citation | 100% | 24 |
| tool_selection | 100% | 33 |

| Category | Pass rate | Cases |
|---|---|---|
| action | 100% | 2 |
| data | 83% | 4 |
| procedure | 63% | 9 |
| refusal | 89% | 3 |
| regulation | 94% | 6 |
| safety | 100% | 3 |
| sds | 100% | 3 |
| shipment | 100% | 6 |

Median tokens per answer: 8,365; median latency: 4.1 s; answers rewritten by the citation check: 11.

## Cases that did not always pass

Pass fraction across runs; the checks and judge note are from a failing run.

- **B04** 1/3 passed (data) What should receiving watch out for with tomorrow's inbound from Delta Copack?  
  key_facts=0.50, judge_complete=0.00  
  judge: The answer includes some correct core facts from the reference, such as RCV-00408, 09:00, and 11 pallets, and it does not directly contradict the reference. However, it misses the main required watchout: Delta Copack’s repeated missing/unreadable SSCC labels, the enhanced inspection status, and the instruction to check every pallet’s SSCC and handle exceptions per SOP-REC-002.
- **P02** 2/3 passed (procedure) A pallet just arrived without an SSCC label. What do I do?  
  citations_valid=0.00  
  judge: The answer matches the reference: do not put it away, move it to zone D exception lane, match to the ASN, relabel with a DC SSCC, log a MISSING_SSCC exception, and escalate ambiguous matches to the receiving lead. It adds extra procedural detail, but nothing contradicts the ground truth.
- **P03** 0/3 passed (procedure) The pallet barcode won't scan. Can I just type the number in by hand?  
  judge_complete=0.00  
  judge: The answer matches the reference on the decision and key conditions: manual entry is allowed only with receiver + lead verification, only if the check digit validates, and the pallet must be relabeled with a DC-printed label. However, it omits the required step to log UNREADABLE_LABEL.
- **P04** 2/3 passed (procedure) What happens to a forklift driver after a near miss?  
  judge_complete=0.00  
  judge: The answer matches the key outcome that a FORKLIFT_NEAR_MISS triggers refresher training and an auto-created task due within 7 days. However, it omits the reference’s main compliance detail that OSHA 1910.178(l)(4)(ii) requires refresher training with evaluation after a near miss.
- **P05** 1/3 passed (procedure) Can we store pool shock and chlorine tablets in the same bay?  
  key_facts=0.50  
  judge: The answer matches the reference decision: they must not be stored in the same bay, and it correctly states they are kept in separate H3 bays. It omits the fire/explosion rationale and the aisle/spill-container specifics, but those are not necessary to fully answer the question asked.
- **P07** 2/3 passed (procedure) What should we never use to soak up a spilled oxidizer?  
  judge_complete=0.00  
  judge: The answer correctly says not to use combustible materials such as sawdust on an oxidizer spill. However, it misses the other main point from the reference: to use the absorbent specified in the SDS.
- **P09** 1/3 passed (procedure) When does a supplier get put on the enhanced inspection list?  
  judge_complete=0.00  
  judge: The answer correctly states the trigger: two or more label exceptions from the same supplier within a 30-day window, and it correctly notes the Delta Copack exception. However, it misses a main point from the reference: suppliers normally remain on the enhanced inspection list for 30 days.
- **R05** 2/3 passed (regulation) What hazard class and packing group is 35% hydrogen peroxide for transport?  
  key_facts=0.50  
  judge: The answer matches the reference: 35% hydrogen peroxide is UN2014, hazard class 5.1 with subsidiary class 8, packing group II. It includes all main points relevant to the question.
- **U03** 2/3 passed (refusal) What will the weather be in Columbus tomorrow?  
  judge_correct=0.00  
  judge: The answer correctly says it cannot provide weather data and directs the user to an external source, which matches the reference. However, it includes an incorrect specific date for “tomorrow” (2026-10-17), so it contains a substantive error.
