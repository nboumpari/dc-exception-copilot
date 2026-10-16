# Retrieval evaluation

42 questions (incident: 3, regulation: 16, sds: 6, sop: 12, standard: 5).

| Chunking | Search | Hit@1 | Hit@5 | MRR@10 |
|---|---|---|---|---|
| structured | bm25 | 38% | 67% | 0.510 |
| naive | bm25 | 43% | 67% | 0.550 |

## Hit@5 by category

| Chunking | Search | incident | regulation | sds | sop | standard |
|---|---|---|---|---|---|---|
| structured | bm25 | 100% | 62% | 100% | 50% | 60% |
| naive | bm25 | 100% | 56% | 83% | 67% | 60% |

## Misses (no relevant chunk in top 5)

- **structured / bm25:** R02, R06, R09, R10, R11, R13, S01, S02, P02, P06, P07, P08, P09, P12
- **naive / bm25:** R02, R06, R09, R10, R11, R14, R16, S01, S02, P02, P07, P08, P12, D05
