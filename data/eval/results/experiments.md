# Evaluation experiment log

Decisions about the agent are made on measurements, not impressions. Each entry: what was
tried, how it was measured, the numbers, the decision. Judge for all entries:
`google:gemini-3.8-flash`; agent: `gpt-5.4-mini`.

## 1. Data questions (text-to-SQL)

The original set had 4 data questions; 8 were added (name matching, date windows,
rankings, a "nothing arriving" question). Answers were computed with SQL first, and
checked under alternative interpretations (e.g. "last 30 days" from midnight vs 18:00).

| Change | Measured on | Before | After |
|---|---|---|---|
| `assess_inbound_receipt` tool: supplier label history and enhanced-inspection rule decided in code (the agent forgot the supplier history in 7 of 10 runs) | B04 x 10 runs | 3/10 | 9/10 |
| Schema lists the exact values of categorical columns (the agent invented `UNREADABLE_SSCC` for `UNREADABLE_LABEL` and silently counted nothing) | queries using the invented value, 12 cases x 3 | 1 | 0 |
| SQL tool hint on empty results after an exact name match (`name = 'ValueMart'` returned 0 although the customer is "ValueMart Regional DC"; prompt rules alone were followed 35/36 times) | unit tests | - | hint returned; no hint for genuinely empty results |
| Today/tomorrow dates stated in the prompt (agent picked a delivery two days out) | B04 failure analysis | 1 wrong-date run | - |

Lesson: prompt rules lower error rates; checks inside tools make specific errors impossible.

## 2. Reasoning effort

| `REASONING_EFFORT` | Data (12 x 3) | Full suite (44 x 3) | Median tokens | Median latency |
|---|---|---|---|---|
| low | 97% | 92% (runs 93 / 91 / 91) | 8,905 | 3.4 s |
| **medium** | **100%** | **97%** (runs 95 / 95 / 100) | 9,932 (+12%) | 5.0 s |

Decision: `medium` is the default - about a third fewer failures overall for 12% more
tokens and 1.6 s per answer.

## 3. Judge provider

Same 108 answers graded by `openai:gpt-5.4` and `google:gemini-3.8-flash`: agreement 99%
(correct) and 95% (complete). On the 6 disagreements, a manual check of the sources sided
with Gemini 5 times (1 tie). Decision: Gemini is the judge (different provider from the
agent). Details: [judge_comparison.md](judge_comparison.md).

## Remaining known weaknesses (medium, full suite)

- B05 (2/3): the agent once added an unrelated brand to a product filter.
- P05 (1/3): omits the fire/explosion reason when saying the chemicals must be stored apart.
- R05 (2/3): omits the subsidiary hazard class 8 despite the prompt rule.
