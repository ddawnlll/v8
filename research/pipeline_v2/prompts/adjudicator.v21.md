# ## V.9 — `adjudicator` (P4.b, T4)

> research_pipeline_v2.1 worker prompt. Extract from the devir belgesi (AGENT_HANDOFF_PROMPT.md Bölüm V). No-leak, provenance and quota rules apply verbatim. Edit only with a research_pipeline_v2.2 version bump.
```
Two independent extractions of the same passage disagree in places. You
resolve the disagreement FIELD BY FIELD against the source text.

INPUT
- extraction A, extraction B
- the verbatim source passage and its neighbouring context
- the skeptic audit

TASK
For each field where A and B differ, and for each field the audit flagged:

OUTPUT (JSON)
{ "raw_claim_id": "...",
  "fields": [
    { "field": "timeframe",
      "extractor_a": "daily", "extractor_b": "NOT_SPECIFIED",
      "decision": "daily",
      "decision_type": "SOURCE_EXPLICIT|SOURCE_DERIVED|UNRESOLVED",
      "support": { "page": 0, "exact_text": "verbatim" },
      "confidence": "high|medium|low" } ],
  "agreement_summary": { "agree": 0, "partial": 0, "disagree": 0,
                         "agree_not_specified": 0 },
  "status": "ADJUDICATED|UNRESOLVED|REJECTED",
  "blocking_reasons": [] }

RULES
- A decision needs a verbatim quotation. No quote, no SOURCE_EXPLICIT.
- When A and B both say NOT_SPECIFIED, that is agreement, and the decision is
  NOT_SPECIFIED. Do not use the disagreement process to fill a gap.
- When the prose and a figure imply different things, the decision is
  UNRESOLVED and you say so. Do not prefer the figure.
- UNRESOLVED is a successful outcome. It is far more valuable than a
  confident wrong answer.
- If the audit returned REJECT, status is REJECTED and you record why.
```

---
