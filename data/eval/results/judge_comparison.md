# Judge comparison

Same 108 answers graded by two judges: `openai:gpt-5.4` (previous) vs `google:gemini-3.8-flash` (current).

| Check | Agreement | Previous judge passes | Current judge passes |
|---|---|---|---|
| judge_correct | 99% | 99% | 100% |
| judge_complete | 95% | 92% | 96% |

## Disagreements

- **P03** run 1 `judge_complete`: previous=0, current=1  
  previous: The answer matches the reference on the key decision: manual entry is allowed only with two-person verification and a valid check digit, followed by relabeling with a DC-printed label. However, it omits the required step to log UNREADABLE_LABEL.  
  current: The assistant correctly details that manual entry requires two-person verification (receiver + lead), check digit validation, relabeling with a DC-printed label, and following the unreadable label procedure.
- **P04** run 0 `judge_complete`: previous=0, current=1  
  previous: The answer matches the key outcome that a FORKLIFT_NEAR_MISS triggers refresher training and an auto-created task due within 7 days. However, it omits the reference’s main compliance detail that OSHA 1910.178(l)(4)(ii) requires refresher training with evaluation after a near miss.  
  current: The assistant accurately explains that a FORKLIFT_NEAR_MISS triggers a refresher training task for the operator due within 7 days, aligning with the reference answer.
- **P07** run 2 `judge_complete`: previous=0, current=1  
  previous: The answer correctly says not to use combustible materials such as sawdust on an oxidizer spill. However, it misses the other main point from the reference: to use the absorbent specified in the SDS.  
  current: The assistant correctly and completely answers what should never be used to soak up a spilled oxidizer (combustible materials like sawdust).
- **P09** run 0 `judge_complete`: previous=0, current=1  
  previous: The answer correctly states the trigger: two or more label exceptions from the same supplier within a 30-day window, and it correctly notes the Delta Copack exception. However, it misses a main point from the reference: suppliers normally remain on the enhanced inspection list for 30 days.  
  current: The assistant accurately answers when a supplier is added to the list (two or more label exceptions within 30 days) and mentions Delta Copack's special status.
- **P09** run 2 `judge_complete`: previous=0, current=1  
  previous: The answer correctly states the trigger: two or more label exceptions from the same supplier within a 30-day window, and it correctly notes the Delta Copack exception. However, it misses a main point from the reference: suppliers normally remain on the enhanced inspection list for 30 days.  
  current: The assistant accurately identifies the threshold for being placed on the enhanced inspection list (two or more label exceptions within 30 days) and correctly notes Delta Copack's special status.
- **U03** run 0 `judge_correct`: previous=0, current=1  
  previous: The answer correctly says it cannot provide weather data and directs the user to an external source, which matches the reference. However, it includes an incorrect specific date for “tomorrow” (2026-10-17), so it contains a substantive error.  
  current: The assistant correctly states that it cannot check live weather forecasts and does not attempt to fabricate weather data.
