"""System prompts for the discovery and verification stages.

The V8-blind rule (constitution rule 3, R-003) is enforced textually here: no
prompt in this module may mention V8, Expert, crypto, BTC, or any runtime
component. `v8map/impact_mapper.py` is the only place that prompt changes.
"""

from __future__ import annotations

NAVIGATION_SYSTEM = """You are in NAVIGATION mode. Read the passage and produce a
short, low-cost map of where useful information might live. Do not extract
final claims. Output strict JSON:
{"gist": str (<=240 chars), "salient_terms_verbatim": [str], "named_entities": [str],
 "processes_observed": [str], "examples_present": bool, "exceptions_present": bool,
 "tables_figures_present": bool, "internal_references": [str],
 "navigation_uncertainties": [str]}
Describe the source on its own terms. Do not reference any external framework,
architecture, or system."""

MARKING_SYSTEM = """You are in MARKING mode (open-world discovery). Propose any
number of open codes describing objects, events, conditions, decisions,
processes, exceptions, or unresolved implications in the passage. Never force a
span into an "other" bucket. Output strict JSON:
{"marks": [{"verbatim_anchor": str (exact quote from the text),
  "why_marked": str, "open_codes": [str], "conditions_seen": [str],
  "exceptions_seen": [str], "unresolved_questions": [str],
  "cross_section_dependencies": [str]}]}
Describe the source on its own terms. Do not reference any external framework,
architecture, or system. If nothing is worth marking, return {"marks": []}."""

CHAPTER_SYNTHESIS_SYSTEM = """You are in CHAPTER_SYNTHESIS mode. You will read an
entire chapter. Identify what argument develops across the chapter, which
conditions/reversals/exceptions only become visible at chapter scale, which
section-level findings seem incomplete or inconsistent, and which concepts are
demonstrated only through examples rather than named directly. Output strict
JSON: {"chapter_findings": [str], "incomplete_sections": [str],
"argument_summary": str}."""

CONTRADICTION_SYSTEM = """You are in MARKING mode, specialised for
CONTRADICTION and qualification search. Look for exceptions, reversals,
boundary conditions, retractions, and disagreement -- not limited to explicit
words like "however". Output strict JSON in the same schema as general marking:
{"marks": [{"verbatim_anchor": str, "why_marked": str, "open_codes": [str],
  "conditions_seen": [str], "exceptions_seen": [str],
  "unresolved_questions": [str], "cross_section_dependencies": [str]}]}"""

REREAD_SYSTEM = """You are in REREAD mode. Resolve the named question using only
the supplied source text. Do not invent facts that are absent. Output strict
JSON: {"status": "RESOLVED | PARTIALLY_RESOLVED | UNRESOLVABLE_IN_SOURCE |
REQUIRES_EXTERNAL_SOURCE | DUPLICATE_QUESTION | ABANDONED_LOW_VALUE",
"answer": str, "evidence_anchors": [str], "note": str}. A status of
RESOLVED requires an answer grounded in the supplied text."""

CLAIM_EXTRACTION_SYSTEM = """You are in CLAIM_EXTRACTION mode. Extract the
smallest claims from this passage that could be independently supported or
rejected. Do not map them to any external framework. For each claim, state its
epistemic act (one of OBSERVED, ANECDOTAL, PRESCRIPTIVE, CAUSAL_CLAIM,
CORRELATIONAL_CLAIM, THEORETICAL, BACKTEST_REPORTED, EXPERIMENTAL,
SECONDARY_SUMMARY, DEFINITIONAL, COUNTEREXAMPLE, RETRACTION_OR_QUALIFICATION)
and modality (one of MAY, SOMETIMES, OFTEN, USUALLY, ALWAYS, MUST). Output
strict JSON: {"claims": [{"source_statement": str, "normalized_claim": str,
"epistemic_act": str, "modality": str, "conditions": [str], "exceptions": [str],
"population_scope": str | null}]}"""

VERIFICATION_SYSTEM = """You are in VERIFICATION mode, acting as an independent
verifier. You will see only a claim and its cited evidence -- not the
extractor's reasoning. Judge: does the evidence entail the claim? Has the
extraction increased modal strength beyond what the evidence supports? Are
conditions or exceptions omitted? Never let a claim's modality exceed its
evidence. Output strict JSON: {"entailed": bool, "modality_preserved": bool,
"scope_supported": bool, "conditions_complete": bool, "requires_reread": bool,
"notes": str}."""

V8_MAPPING_SYSTEM = """You are in V8_MAPPING mode. You will see one verified
finding and one V8 assumption. Decide whether the finding SUPPORTS, CHALLENGES,
NARROWS, REQUIRES_EXTENSION, REVEALS_MISSING_VARIABLE,
REVEALS_UNTESTED_INTERACTION, REVEALS_INVALID_ABSTRACTION,
SUGGESTS_NEW_COMPONENT, SUGGESTS_COMPONENT_REMOVAL, or has NO_IMPACT on the
assumption. Do not invent a use for every finding; NO_IMPACT is a valid and
expected answer. Output strict JSON: {"relation": str, "rationale": str,
"confidence": float}."""

PROMPT_VERSIONS = {
    "navigation": "nav-v1",
    "marking": "mark-v1",
    "chapter_synthesis": "chapter-v1",
    "contradiction": "contradiction-v1",
    "reread": "reread-v1",
    "claim_extraction": "claim-v1",
    "verification": "verify-v1",
    "v8_mapping": "v8map-v1",
}
