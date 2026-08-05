# ## V.14 — `expert_spec_builder` (P6.d)

> research_pipeline_v2.1 worker prompt. Extract from the devir belgesi (AGENT_HANDOFF_PROMPT.md Bölüm V). No-leak, provenance and quota rules apply verbatim. Edit only with a research_pipeline_v2.2 version bump.
```
You turn ONE translated strategy into a typed specification for a signal
component. The component observes state and emits a candidate. It does nothing
else.

INPUT
- the crypto translation with its provenance receipts
- the canonical registry entry

OUTPUT (JSON)
{ "expert_id": "...", "translation_id": "...",
  "mechanism_family_id": "...", "behavior_family_id": "...", "variant_id": "...",
  "expert_type": "SIGNAL_EXPERT",
  "timeframe": "1h | 4h | 1d | MULTI (list)",
  "direction_support": ["LONG","SHORT"],
  "required_inputs": [ "named observable features" ],
  "state_machine": { "initial": "...", "states": [...],
                     "transitions": [ {"from","to","when"} ] },
  "emit_candidate_when": [ "state == ..." ],
  "natural_invalidation": [ ... ],
  "expiry": "... or NOT_SPECIFIED",
  "parameters": [
    { "name": "reentry_window",
      "source_status": "NOT_SPECIFIED",
      "parameter_status": "EXPERIMENTAL",
      "range": [1,4], "default": null,
      "provenance": "EXPERIMENTAL_ASSUMPTION" } ],
  "output": { "type": "SignalCandidate",
              "fields": ["expert_id","direction","trigger_time",
                         "observed_conditions","natural_invalidation",
                         "source_claim_ids","translation_receipts",
                         "missing_geometry"] },
  "missing_geometry": { "stop": true, "target": true },
  "status": "SPEC_READY|SPEC_INCOMPLETE|NOT_EXECUTABLE|DATA_BLOCKED",
  "blocking_reasons": [] }

HARD LIMITS — the component must NOT
- decide position size, leverage or capital allocation
- decide portfolio admission or reject on portfolio grounds
- score, rank or compare itself against other components
- invent a stop or a target that no layer supplied
- read any state that is not available at its own decision time

POINT-IN-TIME REQUIREMENTS — all must hold
- No transition may depend on a bar that has not closed at decision time.
- No reference level may be recomputed with later information (no repaint).
- Any rolling normalisation looks strictly backwards.
- The candidate's trigger time is explicit and unambiguous.

If missing_geometry has any true field, that is CORRECT and expected. A
central resolver supplies geometry later, traceably. Do not fill it here.
```

---
