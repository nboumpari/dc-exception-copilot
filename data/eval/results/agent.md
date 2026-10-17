# Agent evaluation

Model `gpt-5.4-mini` (reasoning: low), judge `google:gemini-3.8-flash`. 36 cases x 3 run(s).

**Pass rate: 93%** (runs: 94%, 89%, 94%) - a case passes when every check scores 1.

| Metric | Score | Answers |
|---|---|---|
| action | 100% | 108 |
| citations_valid | 99% | 108 |
| judge_complete | 96% | 108 |
| judge_correct | 100% | 108 |
| key_facts | 97% | 99 |
| no_forbidden | 100% | 18 |
| required_citation | 100% | 24 |
| tool_selection | 100% | 33 |

| Category | Pass rate | Cases |
|---|---|---|
| action | 100% | 2 |
| data | 83% | 4 |
| procedure | 81% | 9 |
| refusal | 100% | 3 |
| regulation | 94% | 6 |
| safety | 100% | 3 |
| sds | 100% | 3 |
| shipment | 100% | 6 |

Median tokens per answer: 8,365; median latency: 4.1 s; answers rewritten by the citation check: 11.

## Cases that did not always pass

Pass fraction across runs; the checks and judge note are from a failing run.

- **B04** 1/3 passed (data) What should receiving watch out for with tomorrow's inbound from Delta Copack?  
  key_facts=0.50, judge_complete=0.00  
  judge: The assistant identified the correct receipt and pallet count, but completely missed the primary watchout from the reference: Delta Copack's history of missing or unreadable SSCC labels, its presence on the enhanced inspection list, and the need to verify every pallet's SSCC per SOP-REC-002.
- **P02** 2/3 passed (procedure) A pallet just arrived without an SSCC label. What do I do?  
  citations_valid=0.00  
  judge: The assistant's answer correctly covers all required steps from the reference, including not putting the pallet away, moving it to zone D, matching to the ASN, relabeling with a DC SSCC, escalating ambiguous matches to the receiving lead, and logging a MISSING_SSCC exception.
- **P03** 1/3 passed (procedure) The pallet barcode won't scan. Can I just type the number in by hand?  
  judge_complete=0.00  
  judge: The assistant correctly states the conditions for manual entry (two-person verification and check digit validation) and mentions relabeling the pallet, but it fails to mention logging the UNREADABLE_LABEL exception.
- **P05** 1/3 passed (procedure) Can we store pool shock and chlorine tablets in the same bay?  
  key_facts=0.50  
  judge: The assistant correctly states that pool shock and chlorine tablets cannot be stored in the same bay and must be kept in separate H3 bays, fully aligning with the reference.
- **R05** 2/3 passed (regulation) What hazard class and packing group is 35% hydrogen peroxide for transport?  
  key_facts=0.50  
  judge: The assistant accurately provides the primary hazard class (5.1), subsidiary risk (8), packing group (II), and UN number (UN2014) in accordance with 49 CFR 172.101.
