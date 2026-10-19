# Agent evaluation

Model `gpt-5.4-mini` (reasoning: medium), judge `google:gemini-3.8-flash`. 44 cases x 3 run(s).

**Pass rate: 95%** (runs: 98%, 95%, 93%) - a case passes when every check scores 1.

| Metric | Score | Answers |
|---|---|---|
| action | 100% | 132 |
| citations_valid | 99% | 132 |
| judge_complete | 98% | 132 |
| judge_correct | 100% | 132 |
| key_facts | 98% | 123 |
| no_forbidden | 100% | 18 |
| required_citation | 100% | 24 |
| tool_selection | 100% | 57 |

| Category | Pass rate | Cases |
|---|---|---|
| action | 100% | 2 |
| data | 100% | 12 |
| procedure | 85% | 9 |
| refusal | 100% | 3 |
| regulation | 89% | 6 |
| safety | 100% | 3 |
| sds | 100% | 3 |
| shipment | 100% | 6 |

Median tokens per answer: 9,418; median latency: 4.9 s; answers rewritten by the citation check: 14.

## Cases that did not always pass

Pass fraction across runs; the checks and judge note are from a failing run.

- **P04** 2/3 passed (procedure) What happens to a forklift driver after a near miss?  
  key_facts=0.50, judge_complete=0.00  
  judge: The assistant correctly states that a near miss triggers refresher training and evaluation, but it fails to mention the key timeline requirement that the training must be completed within 7 days.
- **P05** 0/3 passed (procedure) Can we store pool shock and chlorine tablets in the same bay?  
  key_facts=0.50  
  judge: The assistant correctly states that the items cannot be stored in the same bay, identifies both substances and their hazard class, notes that they must be stored in separate H3 bays (aisles 01 and 02), and mentions separate spill containers.
- **R05** 2/3 passed (regulation) What hazard class and packing group is 35% hydrogen peroxide for transport?  
  judge_complete=0.00  
  judge: The assistant correctly identified primary Hazard Class 5.1 and Packing Group II, but failed to include the subsidiary hazard Class 8 (corrosive).
- **R06** 2/3 passed (regulation) What does the limited quantity mark look like?  
  citations_valid=0.00  
  judge: The assistant accurately and completely describes the limited quantity mark according to 49 CFR 172.315, including the square-on-point shape, black top and bottom portions, black border, and contrasting center.
