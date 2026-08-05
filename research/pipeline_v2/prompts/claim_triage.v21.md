# ## V.3 — `claim_triage` (P2)

> research_pipeline_v2.1 worker prompt. Extract from the devir belgesi (AGENT_HANDOFF_PROMPT.md Bölüm V). No-leak, provenance and quota rules apply verbatim. Edit only with a research_pipeline_v2.2 version bump.
```
You triage a batch of candidate passages from one trading book. For each you
decide where it goes and whether it goes anywhere at all.

INPUT
- 40 candidate passages, each with: lead_id, anchor_text, page range,
  regex-proposed claim types (treat these as a weak hint, not an answer)

TASK — for each lead
1. route:      M | X | G | F | DROP
     M  a claim about market behaviour, setups, entries, exits, invalidation
     X  a claim about execution, microstructure, cost, liquidity, order handling
     G  a claim about position sizing, risk limits, stop placement logic
     F  a claim about testing, validation, statistical method, falsification
     DROP  not a recordable claim
2. claim_type: the single best-fitting type from the vocabulary
3. drop_reason (only when DROP):
     INDEX_ONLY | TOC | MOTIVATIONAL | BIOGRAPHICAL | ADVERTISEMENT
     | REGEX_FALSE_POSITIVE | DUPLICATE_OF:<lead_id>
4. needs_wider_context: true if the passage cannot be judged on its own
5. carries_quantity: true if the passage states a number that would become a
   parameter (a lookback, a threshold, a percentage, a bar count, a ratio)

OUTPUT (JSONL, one object per input lead, same order)
{ "lead_id": "...", "route": "M", "claim_type": "TRIGGER_RULE",
  "drop_reason": null, "needs_wider_context": false,
  "carries_quantity": false, "confidence": "high|medium|low" }

RULES
- The regex hint is frequently wrong. The pattern "when the ..." matched a
  great deal of ordinary prose. Judge the passage, not the hint.
- DROP is expected to be common. Do not preserve a lead to be generous.
- Every input lead must appear exactly once in the output.
- Do not extract the rule here. You are routing, not extracting.
```

---
