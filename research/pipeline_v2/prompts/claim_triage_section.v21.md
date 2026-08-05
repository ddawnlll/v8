# claim_triage_section — P2 section-level triage (recall fix)

> research_pipeline_v2.1 worker prompt. Section-level variant of claim_triage
> chosen at HITL-1 because deterministic-scout recall was ~0.09 (lexicon too
> narrow). The worker reads a FULL section (not regex leads) and marks every
> claim, so claims the regex vocabulary would miss are still captured.
> No-leak, provenance and quota rules apply verbatim.

```
You triage one or more full SECTIONS of a trading book. You read every line
and mark every passage that is a recordable claim. The regex did NOT see these
sections first — you are the primary scanner, not a verifier.

INPUT
- section files (each 4-8k tokens), with section_id and book_id

TASK — for each section, for EVERY distinct claim passage in it:
1. route:      M | X | G | F | DROP
     M  a claim about market behaviour, setups, entries, exits, invalidation
     X  a claim about execution, microstructure, cost, liquidity, order handling
     G  a claim about position sizing, risk limits, stop placement logic
     F  a claim about testing, validation, statistical method, falsification
     DROP  not a recordable claim
2. claim_type: the single best-fitting type from the vocabulary:
     STRATEGY_SETUP | TRIGGER_RULE | ENTRY_RULE | INVALIDATION_RULE | EXIT_RULE
     | POSITION_SIZING | REGIME_FILTER | LIFECYCLE_RULE | PORTFOLIO_RISK_RULE
     | FEATURE_CLAIM | EMPIRICAL_CLAIM | FAILURE_EXAMPLE | AUTHOR_CAVEAT
     | METHODOLOGY_RULE
3. anchor_text: the verbatim passage (10-250 chars)
4. local_start_line / local_end_line: line numbers within the section file
5. drop_reason (only when DROP):
     MOTIVATIONAL | BIOGRAPHICAL | ADVERTISEMENT | DEFINITION_ONLY | TOC_INDEX
6. carries_quantity: true if the passage states a number that would become a
   parameter (lookback, threshold, percentage, bar count, ratio)
7. needs_wider_context: true if the claim cannot be judged without the next
   section

OUTPUT (JSONL, one object per claim)
{ "section_id": "...", "book_id": "...",
  "route": "M", "claim_type": "TRIGGER_RULE",
  "anchor_text": "...", "local_start_line": 0, "local_end_line": 0,
  "drop_reason": null, "carries_quantity": false,
  "needs_wider_context": false, "confidence": "high|medium|low" }

RULES
- NO QUOTA. A section may yield 0 claims. Zero is a correct answer.
- Do not merge two distinct claims; do not split one paragraph into many
  near-identical claims.
- DROP motivational, biographical, promotional and definition-only prose.
- An index/TOC/glossary entry is never a rule.
- Do NOT extract or complete the rule here. You route and mark.
- If a rule clearly continues past the section end, set needs_wider_context.
```
