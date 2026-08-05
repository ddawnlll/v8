export const meta = {
  name: 'v8-books-calibration-v2',
  description: 'research_pipeline_v2.0 calibration: 5 books through map->scout->extractA/B->audit->adjudicate->synthesize->canonical->translate->spec->validate',
  phases: [
    { title: 'Map', detail: 'book structure maps' },
    { title: 'Scout', detail: 'claim leads per part (prev/next context)' },
    { title: 'Extract', detail: 'independent faithful extractors A and B' },
    { title: 'Audit', detail: 'skeptic counterevidence per book' },
    { title: 'Adjudicate', detail: 'A/B resolution per field' },
    { title: 'Synthesize', detail: 'book-level source strategies' },
    { title: 'Canonical', detail: 'cross-book relationships' },
    { title: 'Translate', detail: 'crypto/V8 translation' },
    { title: 'Spec', detail: 'typed ExpertSpecs' },
    { title: 'Validate', detail: 'expert validation gates' },
  ],
}

// ---------------------------------------------------------------- pipeline context

const PIPELINE = `RESEARCH PIPELINE v2.0 (research_pipeline_v2.0) — calibration run on 5 books.

INVARIANTS (never violated):
- Raw source layer contains ONLY what the source states. NO crypto/V8 additions: no BTC, bitcoin, perp, USDM, 1h, ATR stop, NEXT_BAR_CLOSE, frozen reference, 1R target, funding, binance, 24/7 unless the source itself says so.
- Every field a source does not specify is recorded as NOT_SPECIFIED / UNKNOWN and repeated in the unknowns list. NEVER complete a rule with "reasonable" defaults.
- No extraction quota. A book/part may legitimately yield 0 leads/claims. Index/TOC entries produce LEAD_ONLY hints only — never executable rules.
- Field-level provenance labels: SOURCE_EXPLICIT | SOURCE_DERIVED | MARKET_TRANSLATION | V8_OPERATIONALIZATION | EXPERIMENTAL_ASSUMPTION | V8_DEFAULT | UNRESOLVED. Silent inference is forbidden.
- Counterevidence is collected, never skipped. If none exists in the source, record counterevidence_status = NOT_FOUND_IN_SOURCE.
- Extractor B works completely independently of Extractor A (different run, no shared context).
- Your role is one stage of the pipeline. Do not perform later stages, do not edit earlier stages.

V8 TARGET CONTEXT (only the translator/spec stages use this):
V8 is a falsification research program for crypto perpetual futures (multi-timeframe: 1h / 4h / 1d). MarketState feature groups: trend, volatility, location, participation, response, liquidity, flow, time, cross_market, history. An Expert is a pure function MarketState -> SignalCandidate | None; it never decides size, leverage, or portfolio admission. Complexity budget: max 3 active experts + at most one learned component (V8_CONSTITUTION rule 14). Gated components (router, scorer, ranker, learned execution) are absent by default.`

const PROVENANCE = ['SOURCE_EXPLICIT','SOURCE_DERIVED','MARKET_TRANSLATION','V8_OPERATIONALIZATION','EXPERIMENTAL_ASSUMPTION','V8_DEFAULT','UNRESOLVED']

// ---------------------------------------------------------------- schemas

const BOOK_MAP_SCHEMA = {
  type: 'object',
  properties: {
    book_id: { type: 'string' },
    chapters: { type: 'array', items: { type: 'object', properties: { chapter_id: { type: 'string' }, title: { type: 'string' }, part_range: { type: 'array', items: { type: 'integer' } }, page_range: { type: ['array', 'null'], items: { type: 'integer' } }, relevance: { type: 'object' } }, required: ['chapter_id', 'title', 'part_range'] } },
    total_parts: { type: 'integer' },
    mapped_parts: { type: 'integer' },
    coverage: { type: 'number' },
    missing_parts: { type: 'array', items: { type: 'integer' } },
    front_matter_parts: { type: 'array', items: { type: 'integer' } },
    back_matter_parts: { type: 'array', items: { type: 'integer' } },
    glossary_parts: { type: 'array', items: { type: 'integer' } },
    index_parts: { type: 'array', items: { type: 'integer' } },
    chart_heavy_parts: { type: 'array', items: { type: 'integer' } },
    empirical_result_parts: { type: 'array', items: { type: 'integer' } },
    part_content_types: { type: 'object', additionalProperties: { type: 'array', items: { type: 'string' } } },
  },
  required: ['book_id', 'chapters', 'total_parts', 'mapped_parts', 'coverage'],
}

const LEADS_SCHEMA = {
  type: 'object',
  properties: {
    book_id: { type: 'string' },
    part_id: { type: 'string' },
    leads: { type: 'array', items: {
      type: 'object',
      properties: {
        lead_id: { type: 'string' },
        claim_type_candidates: { type: 'array', items: { type: 'string' } },
        anchor_text: { type: 'string', description: 'verbatim passage, >= 25 chars' },
        local_start_line: { type: 'integer' },
        local_end_line: { type: 'integer' },
        context_before: { type: 'string' },
        context_after: { type: 'string' },
        reason: { type: 'string' },
        priority: { enum: ['high', 'medium', 'low'] },
        index_only: { type: 'boolean' },
      },
      required: ['lead_id', 'claim_type_candidates', 'anchor_text', 'local_start_line', 'local_end_line', 'reason'],
    } },
  },
  required: ['part_id', 'leads'],
}

const RAW_CLAIMS_SCHEMA = {
  type: 'object',
  properties: {
    book_id: { type: 'string' },
    extractor: { type: 'string' },
    claims: { type: 'array', items: {
      type: 'object',
      properties: {
        raw_claim_id: { type: 'string' },
        lead_id: { type: 'string' },
        source: { type: 'object', properties: { page_start: { type: ['integer', 'null'] }, page_end: { type: ['integer', 'null'] }, chapter: { type: 'string' }, part_id: { type: 'string' } } },
        supporting_passages: { type: 'array', items: { type: 'object', properties: { page: { type: ['integer', 'null'] }, exact_text: { type: 'string' }, is_ocr: { type: 'boolean' } }, required: ['exact_text'] } },
        claim_type: { type: 'string', enum: ['EXECUTABLE_STRATEGY_RULE','SETUP_DEFINITION','TRIGGER_RULE','INVALIDATION_RULE','EXIT_RULE','RISK_RULE','POSITION_SIZING','REGIME_RULE','FEATURE_CLAIM','EMPIRICAL_CLAIM','FAILURE_CLAIM','METHODOLOGY_CLAIM','PSYCHOLOGY_CLAIM','AUTHOR_CAVEAT','CONCEPT_DEFINITION','LEAD_ONLY'] },
        original_context: { type: 'object', properties: { asset_class: { type: 'string' }, instrument: { type: 'string' }, timeframe: { type: ['string', 'null'] }, session_model: { type: 'string' } } },
        source_rule: { type: 'object', properties: {
          prerequisites: { type: 'array', items: { type: 'string' } },
          setup: { type: 'array', items: { type: 'string' } },
          trigger: { type: 'array', items: { type: 'string' } },
          direction: { type: 'string' },
          entry: { type: 'string' }, entry_detail: { type: 'string' },
          invalidation: { type: 'array', items: { type: 'string' } },
          exit: { type: 'string' }, exit_detail: { type: 'string' },
          stop: { type: 'string' }, stop_detail: { type: 'string' },
          target: { type: 'string' }, target_detail: { type: 'string' },
          holding_period: { type: 'string' }, holding_period_detail: { type: 'string' },
        } },
        author_parameters: { type: 'array', items: { type: 'object', properties: { name: { type: 'string' }, value: { type: ['string', 'number', 'null'] }, unit: { type: 'string' }, provenance: { type: 'string' } }, required: ['name', 'provenance'] } },
        author_caveats: { type: 'array', items: { type: 'object' } },
        failure_examples: { type: 'array', items: { type: 'object' } },
        quantitative_claim: { type: ['object', 'null'], properties: { metric: { type: 'string' }, value: { type: ['number', 'string', 'null'] }, sample_size: { type: 'string' }, period: { type: ['string', 'null'] }, costs_included: { type: 'string' }, evidence_grade: { type: 'string' }, claim_status: { type: 'string' } } },
        unknowns: { type: 'array', items: { type: 'string' } },
      },
      required: ['raw_claim_id', 'lead_id', 'source', 'supporting_passages', 'claim_type', 'source_rule', 'unknowns'],
    } },
  },
  required: ['book_id', 'claims'],
}

const AUDIT_SCHEMA = {
  type: 'object',
  properties: {
    book_id: { type: 'string' },
    raw_claim_ids: { type: 'array', items: { type: 'string' } },
    author_caveats: { type: 'array', items: { type: 'object', properties: { page: { type: ['integer', 'null'] }, exact_text: { type: 'string' }, meaning: { type: 'string' } } } },
    failure_examples: { type: 'array', items: { type: 'object', properties: { page: { type: ['integer', 'null'] }, summary: { type: 'string' } } } },
    contradictions: { type: 'array', items: { type: 'object' } },
    invented_fields_detected: { type: 'array', items: { type: 'string' } },
    counterevidence_status: { type: 'string' },
    executable_assessment: { type: 'string', enum: ['EXECUTABLE','SPEC_INCOMPLETE','NOT_EXECUTABLE','LEAD_ONLY'] },
    missing_source_support: { type: 'array', items: { type: 'string' } },
  },
  required: ['book_id', 'raw_claim_ids', 'author_caveats', 'failure_examples', 'contradictions', 'invented_fields_detected', 'executable_assessment'],
}

const ADJUDICATED_SCHEMA = {
  type: 'object',
  properties: {
    book_id: { type: 'string' },
    adjudications: { type: 'array', items: {
      type: 'object',
      properties: {
        raw_claim_id: { type: 'string' },
        field_decisions: { type: 'array', items: { type: 'object', properties: { field: { type: 'string' }, extractor_a: { type: ['string', 'null'] }, extractor_b: { type: ['string', 'null'] }, decision: { type: ['string', 'null'] }, decision_type: { type: 'string' }, support: { type: 'object' }, confidence: { type: 'string' } }, required: ['field', 'extractor_a', 'extractor_b', 'decision'] } },
        disagreement_count: { type: 'integer' },
        resolved_count: { type: 'integer' },
        unresolved_count: { type: 'integer' },
      },
      required: ['raw_claim_id', 'field_decisions'],
    } },
  },
  required: ['book_id', 'adjudications'],
}

const SOURCE_STRATEGIES_SCHEMA = {
  type: 'object',
  properties: {
    book_id: { type: 'string' },
    strategies: { type: 'array', items: {
      type: 'object',
      properties: {
        source_strategy_id: { type: 'string' },
        source_name: { type: 'string' },
        supporting_claim_ids: { type: 'array', items: { type: 'string' } },
        source_status: { type: 'string', enum: ['EXECUTABLE_COMPLETE','EXECUTABLE_BUT_INCOMPLETE','SPEC_INCOMPLETE','CONCEPTUAL_ONLY','LEAD_ONLY'] },
        source_native_spec: { type: 'object' },
        source_unknowns: { type: 'array', items: { type: 'string' } },
        original_context: { type: 'object' },
        counterevidence_status: { type: 'string' },
      },
      required: ['source_strategy_id', 'source_name', 'supporting_claim_ids', 'source_status', 'source_native_spec', 'source_unknowns'],
    } },
  },
  required: ['book_id', 'strategies'],
}

const CANONICAL_SCHEMA = {
  type: 'object',
  properties: {
    relationships: { type: 'array', items: { type: 'object', properties: { source_strategy_a: { type: 'string' }, source_strategy_b: { type: 'string' }, relationship: { type: 'string' }, shared_behavior: { type: 'array', items: { type: 'string' } }, differences: { type: 'array', items: { type: 'string' } } }, required: ['source_strategy_a', 'source_strategy_b', 'relationship'] } },
    canonical_families: { type: 'array', items: { type: 'object', properties: { canonical_family_id: { type: 'string' }, canonical_behavior_id: { type: 'string' }, member_strategy_ids: { type: 'array', items: { type: 'string' } } }, required: ['canonical_family_id', 'member_strategy_ids'] } },
  },
  required: ['relationships', 'canonical_families'],
}

const TRANSLATIONS_SCHEMA = {
  type: 'object',
  properties: {
    translations: { type: 'array', items: {
      type: 'object',
      properties: {
        translation_id: { type: 'string' },
        source_strategy_id: { type: 'string' },
        target_market: { type: 'object' },
        field_mappings: { type: 'array', items: { type: 'object', properties: { field: { type: 'string' }, source_value: { type: ['string', 'null'] }, target_value: { type: ['string', 'null'] }, parameter_range: { type: 'array', items: { type: 'number' } }, reason: { type: 'string' }, provenance: { type: 'string' } }, required: ['field', 'source_value', 'target_value', 'provenance'] } },
        preserved_source_logic: { type: 'array', items: { type: 'string' } },
        unsupported_elements: { type: 'array', items: { type: 'string' } },
        transfer_risks: { type: 'array', items: { type: 'string' } },
        required_data: { type: 'array', items: { type: 'string' } },
        data_status: { type: 'string', enum: ['AVAILABLE','PARTIAL','DATA_BLOCKED'] },
        translation_confidence: { type: 'string' },
      },
      required: ['translation_id', 'source_strategy_id', 'target_market', 'field_mappings', 'preserved_source_logic', 'transfer_risks', 'required_data', 'translation_confidence'],
    } },
  },
  required: ['translations'],
}

const EXPERT_SPECS_SCHEMA = {
  type: 'object',
  properties: {
    specs: { type: 'array', items: {
      type: 'object',
      properties: {
        expert_id: { type: 'string' },
        translation_id: { type: 'string' },
        source_claim_ids: { type: 'array', items: { type: 'string' } },
        expert_type: { type: 'string' },
        direction_support: { type: 'array', items: { type: 'string' } },
        required_inputs: { type: 'array', items: { type: 'string' } },
        preconditions: { type: 'array', items: { type: 'string' } },
        emit_candidate_when: { type: 'object' },
        natural_invalidation: { type: 'array', items: { type: 'string' } },
        parameters: { type: 'array', items: { type: 'object' } },
        output: { type: 'object' },
        missing_geometry: { type: 'object' },
        pit_safe: { type: 'boolean' },
        deterministic: { type: 'boolean' },
      },
      required: ['expert_id', 'translation_id', 'expert_type', 'required_inputs', 'emit_candidate_when', 'natural_invalidation', 'output', 'missing_geometry'],
    } },
  },
  required: ['specs'],
}

const VALIDATION_SCHEMA = {
  type: 'object',
  properties: {
    results: { type: 'array', items: { type: 'object', properties: { expert_id: { type: 'string' }, status: { type: 'string', enum: ['QA_PASSED','SPEC_INCOMPLETE','DATA_BLOCKED','REJECTED','DEFER'] }, reasons: { type: 'array', items: { type: 'string' } }, gates: { type: 'object' } }, required: ['expert_id', 'status', 'reasons'] } },
  },
  required: ['results'],
}

// ---------------------------------------------------------------- prompt builders

function bookPartsDesc(book) {
  return book.parts.map(p => `  part ${p.order} (${p.part_id}): ${p.path} (${p.chars} chars)`).join('\n')
}

function mapperPrompt(book) {
  return `${PIPELINE}

ROLE: book_mapper. Map the structure of book "${book.title}" (${book.book_id}).
Input parts (read the front matter / TOC via Read; locate chapter headings via Grep for "chapter", "part", "section", or table-of-contents patterns):
${bookPartsDesc(book)}

TASK: Produce the book structure map ONLY. NO strategy extraction, NO claims.
- chapters: chapter_id, title, part_range (which parts contain it), page_range (best-effort; leave null if pages are not recoverable), relevance (strategy_rules/methodology/risk_rules).
- front_matter_parts, back_matter_parts, glossary_parts, index_parts, bibliography_parts, chart_heavy_parts, empirical_result_parts (part order numbers).
- part_content_types: part order -> content type tags (strategy_rules, risk_management, methodology, empirical_results, examples, narrative, front_matter, index, glossary, bibliography).
- total_parts, mapped_parts, coverage = mapped/total, missing_parts.
If a part is unreadable/garbled (OCR noise), still map it and note it in part_content_types as narrative/unreadable.`
}

function scoutPrompt(book, part, prevPath, nextPath) {
  return `${PIPELINE}

ROLE: claim_scout. Scan ONE part for candidate claim passages. You do NOT extract claims — you mark leads.
Book: "${book.title}" (${book.book_id}). Part ${part.order} of ${part.n_parts}: ${part.path}
Context available (Read for verification only):
  previous part tail: ${prevPath || '(none — first part)'}
  next part head: ${nextPath || '(none — last part)'}

TASK:
- Read the current part FULLY (it is up to ~320K chars; read every line in slices).
- Identify every passage that plausibly states a market claim, from these types: STRATEGY_SETUP, TRIGGER_RULE, ENTRY_RULE, INVALIDATION_RULE, EXIT_RULE, POSITION_SIZING, REGIME_FILTER, LIFECYCLE_RULE, PORTFOLIO_RISK_RULE, FEATURE_CLAIM, EMPIRICAL_CLAIM, FAILURE_EXAMPLE, AUTHOR_CAVEAT, METHODOLOGY_RULE.
- NO QUOTA: list every distinct candidate passage; a part may yield 0 or many. Do not invent passages. Do not complete or interpret rules — just mark the passage.
- For each lead: anchor_text (verbatim, >=25 chars), local_start_line/local_end_line (line numbers within the part file as you read it), claim_type_candidates, reason (what market claim it plausibly states), priority, index_only=true if it came from a TOC/index/glossary entry (such leads may only point to a page — never become executable claims).
- Keep anchor_text and context short but verbatim. If the passage spans a part boundary, still capture it (context_before/after from the neighbor parts).
Return leads for part ${part.part_id}.`
}

function extractorPrompt(book, leads, run) {
  const leadJson = JSON.stringify(leads)
  return `${PIPELINE}

ROLE: faithful_extractor_${run}. Convert the scout leads of one book into RAW SOURCE CLAIMS.
Book: "${book.title}" (${book.book_id}).
${run === 'B' ? 'You are the INDEPENDENT second extractor: you have NOT seen extractor A\'s output. Extract fresh from the source.' : ''}

Source parts for verification (Read the referenced region if you need more context than the lead provides):
${bookPartsDesc(book)}

LEADS (JSON): ${leadJson}

TASK — extract ONLY what the source states:
- For each lead that is a genuine claim, produce a raw_claim. Skip leads that are index-only (index_only=true) unless the actual passage is found elsewhere — those become claim_type=LEAD_ONLY at most.
- source_rule: fill prerequisites/setup/trigger/direction/invalidation/entry/stop/target/exit/holding_period ONLY from the source text. Anything the source does not specify: set the enum to NOT_SPECIFIED and add the field name to unknowns. NEVER invent stop/target/timeframe/N-bar windows/"NEXT_BAR_CLOSE" etc.
- original_context: asset_class / instrument / timeframe / session_model exactly as the source implies (equities/futures/forex...). timeframe: the author's stated timeframe or NOT_SPECIFIED.
- supporting_passages: 1-2 short verbatim quotes (<=250 chars each) with best-effort page (null if page mapping is unavailable — note is_ocr=true when the text came from OCR).
- claim_type: pick the closest type; quantitative figures (win rate, sample, period) go to quantitative_claim with evidence_grade (E0-E7) and claim_status SUBSTANTIATED/UNSUBSTANTIATED; if the author reports no data, E0 + UNSUBSTANTIATED.
- author_parameters: only source-explicit parameters with provenance SOURCE_EXPLICIT.
- NO crypto/V8 vocabulary in any non-quote field. Do not mention BTC, perp, funding, ATR stop, NEXT_BAR_CLOSE, 1R, binance, 24/7, frozen references.
- Do not beautify or "fix" the author's reasoning. Record caveats/failure examples the passage itself carries.
You may produce 0 claims if the leads carry no genuine claims.`
}

function skepticPrompt(book, claimsA) {
  const claimIds = (claimsA || []).map(c => c.raw_claim_id)
  return `${PIPELINE}

ROLE: skeptic_auditor. Search the ENTIRE book for counterevidence against the extracted claims. Your job is to try to kill the strategy, not defend it.
Book: "${book.title}" (${book.book_id}). Claims to audit: ${JSON.stringify(claimIds)}

Source parts (search all of them):
${bookPartsDesc(book)}

TASK:
- For each claim, search the whole book for: author caveats ("avoid", "do not use", "requires confirmation", "unreliable when", "fails when"), failure examples, whipsaw/parameter-instability/regime-dependency notes, contradictory passages, and cases where the author says the method did NOT work or was not used by them.
- invented_fields_detected: any field in extractor A's claims that is NOT supported by any source passage (e.g., a specific stop/target/window the source never gives). This is the most important check — list them explicitly.
- contradictions: passages that contradict each other on the same field.
- executable_assessment: EXECUTABLE (setup+trigger+direction+invalidation all source-backed), SPEC_INCOMPLETE (missing a required element), NOT_EXECUTABLE (no real rule), LEAD_ONLY.
- If no counterevidence exists in the source, set counterevidence_status = NOT_FOUND_IN_SOURCE. Finding none is a legitimate result.`
}

function adjudicatorPrompt(book, claimsA, claimsB, audit) {
  const a = JSON.stringify(claimsA || [])
  const b = JSON.stringify(claimsB || [])
  return `${PIPELINE}

ROLE: adjudicator. Resolve extractor A/B differences against the exact source.
Book: "${book.title}" (${book.book_id}).

Extractor A claims: ${a}
Extractor B claims: ${b}
Skeptic audit: ${JSON.stringify(audit)}

TASK:
- Pair A and B claims by lead_id. For each pair, compare field by field (setup, trigger, direction, timeframe, invalidation, stop, target, entry, unknowns).
- For every disagreeing field, return to the source passage and decide. decision_type = SOURCE_EXPLICIT (source states it) / SOURCE_DERIVED (logically implied) / UNRESOLVED (cannot resolve). Support with the exact text when possible.
- UNRESOLVED is a VALID terminal state — never paper over ambiguity with a guess.
- Also carry forward the skeptic audit's invented_fields_detected into the relevant claim.
Return one adjudication per raw_claim_id.`
}

function synthesizerPrompt(book, adjudications, claimsA) {
  return `${PIPELINE}

ROLE: book_synthesizer. Combine the adjudicated claims of ONE book into source-native strategy variants. Do NOT adapt to crypto. Do NOT merge with other books.
Book: "${book.title}" (${book.book_id}).

Adjudicated claims: ${JSON.stringify(adjudications)}
Extractor A claims (reference): ${JSON.stringify(claimsA || [])}

TASK:
- Group claims that describe the same strategy (setup+trigger+invalidation+exit pieces from multiple claims belong to one strategy).
- Produce ONE source_strategy per distinct native strategy. source_status: EXECUTABLE_COMPLETE (setup+trigger+direction+invalidation+stop+target all source-backed), EXECUTABLE_BUT_INCOMPLETE (executable core but geometry/other missing), SPEC_INCOMPLETE (missing a core element), CONCEPTUAL_ONLY, LEAD_ONLY.
- source_native_spec: merged prerequisites/setup/trigger/direction/entry/invalidation/exit/stop/target — only source-backed values; unknowns into source_unknowns.
- supporting_claim_ids: every claim that contributed.
- counterevidence_status: from the audit.
- A book may yield 0 strategies — that is a valid research result.`
}

function canonicalPrompt(allStrategies) {
  return `${PIPELINE}

ROLE: canonical_registry. Relate the source strategies ACROSS the 5 calibration books. Do not merge source variants — preserve them.
All source strategies: ${JSON.stringify(allStrategies)}

TASK:
- relationships: for meaningful pairs, relationship type: EXACT_DUPLICATE / CORROBORATES / REFINES / SPECIALIZES / GENERALIZES / CONTRADICTS / SIMILAR_MECHANISM / DIFFERENT_BEHAVIOR, with shared_behavior and differences.
- canonical_families: group strategies by shared mechanism into canonical_family_id + canonical_behavior_id (e.g. boundary_interaction / failed_breakout_delayed_reentry). Members keep their own ids.
- Books repeating the same rule are NOT independent evidence (SourceClaim != IndependentEvidence) — note origin_type when detectable (ORIGINAL_AUTHOR_RULE / DERIVED_FROM_NAMED_SOURCE / UNSOURCED_RESTATEMENT / UNKNOWN_ORIGIN).`
}

function translatorPrompt(strategiesChunk) {
  return `${PIPELINE}

ROLE: crypto_translator. Translate source strategies to V8's target market (USDM perpetual, 1h bars, 24/7). This is the ONLY stage where crypto adaptation happens, and every change must be provenance-tagged.
Source strategies to translate: ${JSON.stringify(strategiesChunk)}

TASK — for each source strategy:
- target_market: { instrument_type: USDM_PERPETUAL, timeframe: '1h', session_model: '24_7' }.
- field_mappings: for every source field that changes or needs definition, map { field, source_value, target_value, reason, provenance }. Provenance rules:
  * SOURCE_EXPLICIT / SOURCE_DERIVED: unchanged from source.
  * MARKET_TRANSLATION: session 24/7 -> fixed UTC bars, etc.
  * V8_OPERATIONALIZATION: "visually identified support" -> frozen windowed extreme; "two days" -> N-bar window, etc.
  * EXPERIMENTAL_ASSUMPTION: source-unspecified parameters given an allowed_range (mark clearly).
  * V8_DEFAULT: values V8 supplies (e.g. default horizon).
- preserved_source_logic: the mechanism elements that survive unchanged (direction, event sequence, invalidation logic).
- unsupported_elements: source elements with no crypto analogue (e.g. overnight gap).
- transfer_risks: liquidation wicks, funding, 24/7 structure, altcoin beta, taker-fee drag, venue data limits.
- required_data + data_status (AVAILABLE / PARTIAL / DATA_BLOCKED).
- translation_confidence: HIGH/MEDIUM/LOW.`
}

function specPrompt(translationsChunk) {
  return `${PIPELINE}

ROLE: expert_spec_builder. Produce typed ExpertSpecs from translations. An expert is a PURE SIGNAL function (MarketState -> SignalCandidate | None). It does NOT decide size, leverage, portfolio admission, or invent geometry.
Translations to spec: ${JSON.stringify(translationsChunk)}

TASK — for each translation with an executable core:
- expert_id (e.g. expert_failed_breakout_elder_v1), translation_id, source_claim_ids.
- expert_type SIGNAL_EXPERT (regime/risk/lifecycle/methodology rules are NOT signal experts — tag them with the correct expert_type instead).
- required_inputs: V8 feature keys (close, high, low, frozen window extremes, bars_since_*, volume, atr, etc. — only what the spec needs).
- preconditions, emit_candidate_when (state + conditions + direction), natural_invalidation.
- parameters: name, source_status (SOURCE_SPECIFIED/NOT_SPECIFIED), parameter_status (SOURCE_EXPLICIT/SOURCE_DERIVED/EXPERIMENTAL/V8_DEFAULT), default (null if EXPERIMENTAL), range.
- output: type SignalCandidate.
- missing_geometry: { stop, target, position_size } booleans — TRUE when neither source nor translation defined them. The central RiskGeometryResolver fills these later; the expert NEVER does.
- pit_safe / deterministic: leave true unless you identify a violation (future data, wall clock, repainting label).`
}

function validatorPrompt(specs) {
  return `${PIPELINE}

ROLE: expert_validator. Apply the hard gates to every expert spec and classify:
- QA_PASSED: source provenance present, setup+trigger+direction+invalidation present, PIT-safe, deterministic, data available.
- SPEC_INCOMPLETE: missing a core executable element (the expert must NOT emit candidates while incomplete).
- DATA_BLOCKED: required data not available.
- REJECTED: invented fields, source-faithfulness violation, not falsifiable.
- DEFER: gated component (router/scorer/ranker/learned execution) or below priority.
Specs to validate: ${JSON.stringify(specs)}

For each: gates {source_fidelity, executability, falsifiability, pit, determinism, data_availability} as pass/fail with reason.`
}

// ---------------------------------------------------------------- helpers

function chunk(arr, n) {
  const out = []
  for (let i = 0; i < arr.length; i += n) out.push(arr.slice(i, i + n))
  return out
}

// ---------------------------------------------------------------- phases

const books = args.books
const allParts = []
for (const b of books) {
  b.parts.forEach((p, i) => {
    allParts.push({
      ...p,
      book_id: b.book_id,
      book_title: b.title,
      n_parts: b.parts.length,
      prev: i > 0 ? b.parts[i - 1].path : null,
      next: i < b.parts.length - 1 ? b.parts[i + 1].path : null,
    })
  })
}

phase('Map')
const maps = await parallel(books.map(b => () =>
  agent(mapperPrompt(b), { label: `map:${b.book_id}`, phase: 'Map', schema: BOOK_MAP_SCHEMA, effort: 'high' })))
const mapById = {}
maps.filter(Boolean).forEach(m => { if (m.book_id) mapById[m.book_id] = m })
log(`mapped ${maps.filter(Boolean).length}/${books.length} books`)

phase('Scout')
const scouts = await parallel(allParts.map(p => () =>
  agent(scoutPrompt({ book_id: p.book_id, title: p.book_title, parts: books.find(b => b.book_id === p.book_id).parts }, p, p.prev, p.next),
    { label: `scout:${p.book_id}:p${p.order}`, phase: 'Scout', schema: LEADS_SCHEMA, effort: 'high' })))
const leadsByBook = {}
scouts.filter(Boolean).forEach(s => {
  const book = books.find(b => b.parts.some(pp => pp.part_id === s.part_id))
  const bid = s.book_id || (book && book.book_id)
  if (bid) (leadsByBook[bid] = leadsByBook[bid] || []).push(...(s.leads || []))
})
const totalLeads = Object.values(leadsByBook).reduce((a, x) => a + x.length, 0)
log(`scouted ${scouts.filter(Boolean).length} parts, ${totalLeads} leads`)

phase('Extract')
const claimJobs = []
for (const b of books) {
  claimJobs.push({ b, leads: leadsByBook[b.book_id] || [], run: 'A' })
  claimJobs.push({ b, leads: leadsByBook[b.book_id] || [], run: 'B' })
}
const extracts = await parallel(claimJobs.map(j => () =>
  agent(extractorPrompt(j.b, j.leads, j.run), { label: `extract${j.run}:${j.b.book_id}`, phase: 'Extract', schema: RAW_CLAIMS_SCHEMA, effort: 'high' })))
const claimsAByBook = {}, claimsBByBook = {}
extracts.filter(Boolean).forEach(e => {
  if (!e.book_id) return
  if (e.extractor === 'B') (claimsBByBook[e.book_id] = e.claims || [])
  else (claimsAByBook[e.book_id] = e.claims || [])
})
log(`extracted A: ${Object.values(claimsAByBook).reduce((a, x) => a + x.length, 0)} claims, B: ${Object.values(claimsBByBook).reduce((a, x) => a + x.length, 0)} claims`)

phase('Audit')
const audits = await parallel(books.map(b => () =>
  agent(skepticPrompt(b, claimsAByBook[b.book_id] || []), { label: `audit:${b.book_id}`, phase: 'Audit', schema: AUDIT_SCHEMA, effort: 'high' })))
const auditByBook = {}
audits.filter(Boolean).forEach(a => { if (a.book_id) auditByBook[a.book_id] = a })
log(`audited ${audits.filter(Boolean).length} books`)

phase('Adjudicate')
const adjudicated = await parallel(books.map(b => () =>
  agent(adjudicatorPrompt(b, claimsAByBook[b.book_id] || [], claimsBByBook[b.book_id] || [], auditByBook[b.book_id] || {}),
    { label: `adj:${b.book_id}`, phase: 'Adjudicate', schema: ADJUDICATED_SCHEMA, effort: 'high' })))
const adjByBook = {}
adjudicated.filter(Boolean).forEach(a => { if (a.book_id) adjByBook[a.book_id] = a })
log(`adjudicated ${adjudicated.filter(Boolean).length} books`)

phase('Synthesize')
const synths = await parallel(books.map(b => () =>
  agent(synthesizerPrompt(b, adjByBook[b.book_id] || {}, claimsAByBook[b.book_id] || []),
    { label: `synth:${b.book_id}`, phase: 'Synthesize', schema: SOURCE_STRATEGIES_SCHEMA, effort: 'high' })))
const strategiesByBook = {}
synths.filter(Boolean).forEach(s => { if (s.book_id) strategiesByBook[s.book_id] = s.strategies || [] })
const allStrategies = Object.values(strategiesByBook).flat()
log(`synthesized ${allStrategies.length} source strategies across ${synths.filter(Boolean).length} books`)

phase('Canonical')
const canonical = await agent(canonicalPrompt(allStrategies), { label: 'canonical', phase: 'Canonical', schema: CANONICAL_SCHEMA, effort: 'high' })
log(`canonical: ${(canonical && canonical.relationships || []).length} relationships, ${(canonical && canonical.canonical_families || []).length} families`)

phase('Translate')
const stratChunks = chunk(allStrategies, 6)
const transResults = await parallel(stratChunks.map((c, i) => () =>
  agent(translatorPrompt(c), { label: `translate:${i + 1}`, phase: 'Translate', schema: TRANSLATIONS_SCHEMA, effort: 'high' })))
const translations = transResults.filter(Boolean).flatMap(t => t.translations || [])
log(`translated ${translations.length} strategies`)

phase('Spec')
const transChunks = chunk(translations, 6)
const specResults = await parallel(transChunks.map((c, i) => () =>
  agent(specPrompt(c), { label: `spec:${i + 1}`, phase: 'Spec', schema: EXPERT_SPECS_SCHEMA, effort: 'high' })))
const specs = specResults.filter(Boolean).flatMap(s => s.specs || [])
log(`built ${specs.length} expert specs`)

phase('Validate')
const validated = await agent(validatorPrompt(specs), { label: 'validate', phase: 'Validate', schema: VALIDATION_SCHEMA, effort: 'high' })

// metrics
const metrics = {
  pipeline_version: 'research_pipeline_v2.0',
  books: books.map(b => {
    const a = claimsAByBook[b.book_id] || []
    const bb = claimsBByBook[b.book_id] || []
    const aIds = new Set(a.map(c => c.lead_id))
    const bIds = new Set(bb.map(c => c.lead_id))
    const both = [...aIds].filter(x => bIds.has(x)).length
    return {
      book_id: b.book_id,
      parts: b.parts.length,
      leads: (leadsByBook[b.book_id] || []).length,
      index_only_leads: (leadsByBook[b.book_id] || []).filter(l => l.index_only).length,
      claims_a: a.length,
      claims_b: bb.length,
      leads_both_extracted: both,
      strategies: (strategiesByBook[b.book_id] || []).length,
      audit: auditByBook[b.book_id] ? { counterevidence_status: auditByBook[b.book_id].counterevidence_status, invented_fields: (auditByBook[b.book_id].invented_fields_detected || []).length, caveats: (auditByBook[b.book_id].author_caveats || []).length, failures: (auditByBook[b.book_id].failure_examples || []).length } : null,
    }
  }),
  totals: {
    leads: totalLeads,
    claims_a: Object.values(claimsAByBook).reduce((a, x) => a + x.length, 0),
    claims_b: Object.values(claimsBByBook).reduce((a, x) => a + x.length, 0),
    strategies: allStrategies.length,
    translations: translations.length,
    specs: specs.length,
    validated: (validated && validated.results || []).length,
  },
  validation: validated ? validated.results : [],
}

return {
  metrics,
  books: books.map(b => ({ book_id: b.book_id, title: b.title })),
  maps: maps.filter(Boolean),
  leads_by_book: leadsByBook,
  claims_a: claimsAByBook,
  claims_b: claimsBByBook,
  audits: auditByBook,
  adjudicated: adjByBook,
  strategies: strategiesByBook,
  canonical,
  translations,
  specs,
  validation: validated ? validated.results : [],
}
