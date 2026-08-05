# ## V.12 — `canonical_merge` (P4.c ve P6.b — BARİYER, tek çağrı)

> research_pipeline_v2.1 worker prompt. Extract from the devir belgesi (AGENT_HANDOFF_PROMPT.md Bölüm V). No-leak, provenance and quota rules apply verbatim. Edit only with a research_pipeline_v2.2 version bump.
```
Several source strategies from different books have been proposed. Establish
their relationships and their canonical identity. You never delete a source
variant.

INPUT
- the proposed source strategies (or, in round merge, the NEW behaviour
  declarations made during this round)
- the existing canonical registry

TASK
1. For each pair that plausibly relates, assign a relationship:
     EXACT_DUPLICATE | CORROBORATES | REFINES | SPECIALIZES | GENERALIZES
     | CONTRADICTS | SIMILAR_MECHANISM | DIFFERENT_BEHAVIOR
2. Assign canonical identity: canonical_family_id + canonical_behavior_id.
3. Where two round-declarations describe the same behaviour, collapse them to
   ONE canonical behaviour while keeping BOTH source variants intact.

OUTPUT (JSON)
{ "relationships": [
    { "a": "source_strategy_id", "b": "source_strategy_id",
      "type": "REFINES",
      "shared_behavior": [...], "differences": [...] } ],
  "canonical_assignments": [
    { "source_strategy_id": "...", "canonical_family_id": "...",
      "canonical_behavior_id": "...", "is_new_behavior": true } ],
  "merged_declarations": [
    { "collapsed": ["decl_id","decl_id"], "into": "canonical_behavior_id",
      "why": "one sentence" } ] }

RULES
- Source variants are NEVER deleted or rewritten. One canonical behaviour may
  carry many source variants, and each keeps its own rules and its own gaps.
  Elder's version and Connors' version of the same behaviour stay separate
  records under one canonical identity.
- CONTRADICTS is a valid and valuable relationship. Record it; do not resolve
  it by preferring one author.
- Be conservative about is_new_behavior. Every new behaviour increases the
  program's trial count and weakens every later statistical claim.
```

---
