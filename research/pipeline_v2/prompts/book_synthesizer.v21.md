# ## V.11 — `book_synthesizer` (P6.a)

> research_pipeline_v2.1 worker prompt. Extract from the devir belgesi (AGENT_HANDOFF_PROMPT.md Bölüm V). No-leak, provenance and quota rules apply verbatim. Edit only with a research_pipeline_v2.2 version bump.
```
All claims from ONE book have been extracted and adjudicated. Assemble them
into the strategy variants that this book itself defines. You work within one
book only.

INPUT
- every adjudicated claim from this book
- this book's counterevidence records

TASK
Group claims that together describe one procedure (a setup claim + its trigger
claim + its exit claim + its caveats + its empirical claims).

OUTPUT (JSONL, one per source strategy)
{ "source_strategy_id": "...", "book_id": "...",
  "supporting_claims": ["claim_id", ...],
  "source_name": "the author's own name for it, or null",
  "source_status": "EXECUTABLE | EXECUTABLE_BUT_INCOMPLETE | NOT_EXECUTABLE",
  "source_native_spec": {
      "prerequisites": [...], "setup": [...], "trigger": [...],
      "direction": [...], "invalidation": [...],
      "entry": "... or NOT_SPECIFIED", "stop": "... or NOT_SPECIFIED",
      "target": "... or NOT_SPECIFIED" },
  "source_caveats": [ {"page","exact_text"} ],
  "source_unknowns": [ "what this book never resolves" ],
  "blocking_reasons": [] }

FORBIDDEN
- Translating to any target market.
- Determining any downstream system action.
- Producing a parameter the book did not state.
- Merging with strategies from other books. That happens later, elsewhere.
- Resolving an unknown by borrowing from another chapter unless the author
  explicitly cross-references it.
```

---
