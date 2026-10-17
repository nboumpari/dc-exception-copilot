# Agent evaluation

Model `gpt-5.4-mini` (reasoning: medium), judge `google:gemini-3.8-flash`. 44 cases x 3 run(s).

**Pass rate: 97%** (runs: 95%, 95%, 100%) - a case passes when every check scores 1.

| Metric | Score | Answers |
|---|---|---|
| action | 100% | 132 |
| citations_valid | 100% | 132 |
| judge_complete | 98% | 132 |
| judge_correct | 99% | 132 |
| key_facts | 98% | 123 |
| no_forbidden | 100% | 18 |
| required_citation | 100% | 24 |
| tool_selection | 100% | 57 |

| Category | Pass rate | Cases |
|---|---|---|
| action | 100% | 2 |
| data | 97% | 12 |
| procedure | 93% | 9 |
| refusal | 100% | 3 |
| regulation | 94% | 6 |
| safety | 100% | 3 |
| sds | 100% | 3 |
| shipment | 100% | 6 |

Median tokens per answer: 9,932; median latency: 5.0 s; answers rewritten by the citation check: 11.

## Cases that did not always pass

Pass fraction across runs; the checks and judge note are from a failing run.

- **B05** 2/3 passed (data) How many pallets of air freshener do we have available right now?  
  key_facts=0.00, judge_correct=0.00, judge_complete=0.00  
  judge: The assistant reports 88 available pallets instead of the correct number of 63 pallets specified in the reference answer.
- **P05** 1/3 passed (procedure) Can we store pool shock and chlorine tablets in the same bay?  
  key_facts=0.50  
  judge: The assistant correctly states that pool shock and chlorine tablets cannot be stored in the same bay because they must never touch, noting that they are class 5.1 oxidizers stored in separate H3 bays.
- **R05** 2/3 passed (regulation) What hazard class and packing group is 35% hydrogen peroxide for transport?  
  judge_complete=0.00  
  judge: The assistant correctly identified the primary hazard class (5.1) and packing group (PG II), but failed to include the subsidiary hazard class 8 (corrosive), which is a key part of the required transport classification for UN2014.
