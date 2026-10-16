# Retrieval evaluation

42 questions (incident: 3, regulation: 16, sds: 6, sop: 12, standard: 5).

| Chunking | Search | Hit@1 | Hit@5 | MRR@10 |
|---|---|---|---|---|
| structured | bm25 | 38% | 69% | 0.520 |
| structured | vector | 64% | 88% | 0.731 |
| structured | hybrid | 62% | 81% | 0.697 |
| naive | bm25 | 43% | 69% | 0.562 |
| naive | vector | 60% | 81% | 0.671 |
| naive | hybrid | 60% | 86% | 0.700 |

## Hit@5 by category

| Chunking | Search | incident | regulation | sds | sop | standard |
|---|---|---|---|---|---|---|
| structured | bm25 | 100% | 69% | 100% | 50% | 60% |
| structured | vector | 100% | 100% | 100% | 67% | 80% |
| structured | hybrid | 100% | 88% | 100% | 58% | 80% |
| naive | bm25 | 100% | 62% | 83% | 67% | 60% |
| naive | vector | 100% | 88% | 100% | 58% | 80% |
| naive | hybrid | 100% | 81% | 100% | 75% | 100% |

## Misses (no relevant chunk in top 5)

- **structured / bm25:** R02, R06, R09, R11, R13, S01, S02, P02, P06, P07, P08, P09, P12
- **structured / vector:** S05, P02, P08, P09, P12
- **structured / hybrid:** R02, R06, S05, P02, P06, P08, P09, P12
- **naive / bm25:** R02, R06, R09, R11, R14, R16, S01, S02, P02, P07, P08, P12, D05
- **naive / vector:** R02, R06, S05, P02, P06, P08, P09, P12
- **naive / hybrid:** R02, R06, R09, P02, P08, P09
