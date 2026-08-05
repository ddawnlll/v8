export const meta = {
  name: 'v8-corpus-v21',
  description: 'research_pipeline_v2.0 corpus-wide run: deterministic-scout leads -> extractA/B -> audit -> adjudicate -> synthesize -> canonical -> translate -> spec -> validate + recall audit',
  phases: [
    { title: 'Extract', detail: 'faithful extractors A (all leads) and B (high-priority only)' },
    { title: 'Audit', detail: 'skeptic counterevidence per book' },
    { title: 'Adjudicate', detail: 'A/B field resolution' },
    { title: 'Synthesize', detail: 'book-level source strategies' },
    { title: 'Recall', detail: 'sample-based missed-claim audit' },
    { title: 'Canonical', detail: 'cross-book relationships' },
    { title: 'Translate', detail: 'crypto/V8 translation' },
    { title: 'Spec', detail: 'typed ExpertSpecs' },
    { title: 'Validate', detail: 'expert validation gates' },
  ],
}

// ---------------------------------------------------------------- pipeline context

const PIPELINE = `RESEARCH PIPELINE v2.0 (research_pipeline_v2.0) — corpus-wide run.

INVARIANTS (never violated):
- Raw source layer contains ONLY what the source states. NO crypto/V8 additions: no BTC, bitcoin, perp, USDM, 1h, ATR stop, NEXT_BAR_CLOSE, frozen reference, 1R target, funding, binance, 24/7 unless the source itself says so.
- Every field a source does not specify is NOT_SPECIFIED / UNKNOWN and repeated in the unknowns list. NEVER complete a rule with "reasonable" defaults.
- No extraction quota per lead set. A pack may legitimately yield 0 claims.
- Index/TOC-derived leads are LEAD_ONLY hints, never executable rules.
- Field-level provenance labels: SOURCE_EXPLICIT | SOURCE_DERIVED | MARKET_TRANSLATION | V8_OPERATIONALIZATION | EXPERIMENTAL_ASSUMPTION | V8_DEFAULT | UNRESOLVED. Silent inference forbidden.
- Counterevidence is collected, never skipped.
- Extractor B works completely independently of Extractor A (different run, no shared context).
- Your role is one stage. Do not perform later stages or edit earlier stages.

V8 TARGET CONTEXT (translator/spec/validate stages only):
V8 is a falsification research program for crypto perpetual futures (multi-timeframe: 1h / 4h / 1d). MarketState feature groups: trend, volatility, location, participation, response, liquidity, flow, time, cross_market, history. An Expert is a pure function MarketState -> SignalCandidate | None; never decides size/leverage/portfolio admission. Complexity budget: max 3 active experts + at most one learned component. Gated components (router/scorer/ranker/learned execution) are absent by default.`

// ---------------------------------------------------------------- schemas (shared with calibration_v2)

const RAW_CLAIMS_SCHEMA = {
  type: 'object',
  properties: {
    book_id: { type: 'string' },
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
    author_caveats: { type: 'array', items: { type: 'object' } },
    failure_examples: { type: 'array', items: { type: 'object' } },
    contradictions: { type: 'array', items: { type: 'object' } },
    invented_fields_detected: { type: 'array', items: { type: 'string' } },
    counterevidence_status: { type: 'string' },
    executable_assessment: { type: 'string', enum: ['EXECUTABLE','SPEC_INCOMPLETE','NOT_EXECUTABLE','LEAD_ONLY'] },
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
    results: { type: 'array', items: { type: 'object', properties: { expert_id: { type: 'string' }, status: { type: 'string' }, reasons: { type: 'array', items: { type: 'string' } }, gates: { type: 'object' } }, required: ['expert_id', 'status', 'reasons'] } },
  },
  required: ['results'],
}

const RECALL_SCHEMA = {
  type: 'object',
  properties: {
    results: { type: 'array', items: { type: 'object', properties: { book_id: { type: 'string' }, sampled_passages: { type: 'integer' }, missed_claim_passages: { type: 'integer' }, missed_summaries: { type: 'array', items: { type: 'object', properties: { passage: { type: 'string' }, claim_type: { type: 'string' } } } }, recall_flag: { enum: ['OK','LOW'] } }, required: ['book_id', 'sampled_passages', 'missed_claim_passages', 'recall_flag'] } },
  },
  required: ['results'],
}

// ---------------------------------------------------------------- prompt builders

function extractorPrompt(pack, run) {
  const priorityNote = run === 'B'
    ? 'This pack may contain medium/low-priority leads too; extract ONLY from leads with priority == "high".'
    : 'Extract from every genuine lead in the pack.'
  return `${PIPELINE}

ROLE: faithful_extractor_${run}. Convert scout leads into RAW SOURCE CLAIMS.
Pack file to read (Read it fully — it is a JSONL array of leads, each with anchor_text from the source): ${pack.path}
Book: ${pack.book_id}

${priorityNote}

TASK — extract ONLY what the source states:
- For each lead that is a genuine claim, produce a raw_claim. Index-only leads (index_only=true) become claim_type=LEAD_ONLY at most.
- source_rule: fill prerequisites/setup/trigger/direction/invalidation/entry/stop/target/exit/holding_period ONLY from the source text. Anything unspecified: enum = NOT_SPECIFIED + add to unknowns. NEVER invent stop/target/timeframe/N-bar windows/"NEXT_BAR_CLOSE".
- original_context: asset_class/instrument/timeframe/session_model as the source implies; timeframe = the author's stated one or NOT_SPECIFIED.
- supporting_passages: 1-2 short verbatim quotes (<=250 chars) with best-effort page (null if unknown; is_ocr=true when from OCR).
- claim_type: closest type. Quantitative figures go to quantitative_claim with evidence_grade (E0-E7) and claim_status (SUBSTANTIATED/UNSUBSTANTIATED); no data reported -> E0 + UNSUBSTANTIATED.
- author_parameters: only source-explicit, provenance SOURCE_EXPLICIT.
- NO crypto/V8 vocabulary in any non-quote field.
- Do not beautify the author's reasoning. Merge leads describing the same strategy into ONE claim (no near-duplicates within the pack).
- A pack may yield 0 claims — that is a valid result.`
}

function auditorPrompt(booksChunk) {
  const desc = booksChunk.map(b => `Book ${b.book_id} (${b.title}) — claims: ${JSON.stringify((b.claimsA || []).map(c => c.raw_claim_id))}; parts: ${b.parts.map(p => p.path).join('; ')}`).join('\n')
  return `${PIPELINE}

ROLE: skeptic_auditor (cheap pass). Search each book's parts for counterevidence against its extracted claims. Try to kill the strategies.
${desc}

TASK (per book, produce one AUDIT record with book_id):
- Search the whole book for: author caveats ("avoid", "do not use", "requires confirmation", "unreliable when"), failure examples, whipsaw/parameter-instability/regime-dependency notes, contradictory passages.
- invented_fields_detected: any field in the claims NOT supported by any source passage (invented stop/target/window). Most important check.
- executable_assessment: EXECUTABLE / SPEC_INCOMPLETE / NOT_EXECUTABLE / LEAD_ONLY.
- If no counterevidence exists, counterevidence_status = NOT_FOUND_IN_SOURCE.
Use Read + Grep over the part files.`
}

function adjudicatorPrompt(book) {
  return `${PIPELINE}

ROLE: adjudicator. Resolve extractor A/B differences against the exact source for ONE book.
Book: ${book.book_id} (${book.title})
Extractor A claims: ${JSON.stringify(book.claimsA || [])}
Extractor B claims: ${JSON.stringify(book.claimsB || [])}
Skeptic audit: ${JSON.stringify(book.audit || {})}

TASK:
- Pair A/B claims by lead_id. Compare field by field (setup, trigger, direction, timeframe, invalidation, stop, target, entry, unknowns).
- For disagreeing fields return to the source; decision_type = SOURCE_EXPLICIT / SOURCE_DERIVED / UNRESOLVED (UNRESOLVED is valid — never guess).
- Carry forward the audit's invented_fields_detected into the relevant claim.
Return one adjudication per raw_claim_id.`
}

function synthesizerPrompt(book) {
  return `${PIPELINE}

ROLE: book_synthesizer. Combine the adjudicated claims of ONE book into source-native strategy variants. Do NOT adapt to crypto. Do NOT merge with other books.
Book: ${book.book_id} (${book.title})
Adjudicated claims: ${JSON.stringify(book.adjudications || [])}

TASK:
- Group claims describing the same strategy (setup+trigger+invalidation+exit pieces) into ONE source strategy.
- source_status: EXECUTABLE_COMPLETE / EXECUTABLE_BUT_INCOMPLETE / SPEC_INCOMPLETE / CONCEPTUAL_ONLY / LEAD_ONLY.
- source_native_spec: merged source-backed values only; unknowns into source_unknowns.
- supporting_claim_ids: every contributing claim.
- counterevidence_status from the audit.
- A book may yield 0 strategies — a valid result.`
}

function recallPrompt(booksChunk) {
  const desc = booksChunk.map(b => `Book ${b.book_id} (${b.title}) — parts: ${b.parts.map(p => p.path).join('; ')}; extracted claim count: ${(b.claimsA || []).length}`).join('\n')
  return `${PIPELINE}

ROLE: recall auditor (cheap pass). For each book, sample ~6 passages the deterministic scout did NOT flag (read a few lines from scattered line offsets in each part), and judge whether the scout/extractors MISSED a genuine claim there.
${desc}

TASK (per book, one result with book_id):
- For ~6 sampled passages per book, mark missed_claim_passages count and a short missed_summary per miss (passage + claim_type).
- recall_flag: OK if 0-1 misses out of 6 samples; LOW if 2+ misses.
- This measures the false-negative rate of the deterministic scouting. Be conservative: a miss is a genuine market claim (setup/trigger/rule/risk/empirical) not covered by any extracted claim.`
}

function canonicalPrompt(allStrategies) {
  return `${PIPELINE}

ROLE: canonical_registry. Relate source strategies ACROSS all corpus books. Do not merge source variants — preserve them.
Source strategies (JSON): ${JSON.stringify(allStrategies)}

TASK:
- relationships for meaningful pairs: EXACT_DUPLICATE / CORROBORATES / REFINES / SPECIALIZES / GENERALIZES / CONTRADICTS / SIMILAR_MECHANISM / DIFFERENT_BEHAVIOR, with shared_behavior + differences.
- canonical_families: group by shared mechanism into canonical_family_id + canonical_behavior_id; members keep their ids.
- Books repeating the same rule are NOT independent evidence — note origin_type when detectable (ORIGINAL_AUTHOR_RULE / DERIVED_FROM_NAMED_SOURCE / UNSOURCED_RESTATEMENT / UNKNOWN_ORIGIN).
- Cap: emit the strongest ~150 relationships and ~80 canonical families; do not fabricate.`
}

function translatorPrompt(chunk) {
  return `${PIPELINE}

ROLE: crypto_translator. Translate source strategies to V8's target market (USDM perpetual, 1h, 24/7). Only here does crypto adaptation happen; every change provenance-tagged.
${JSON.stringify(chunk)}

TASK (per strategy): target_market; field_mappings with provenance (SOURCE_EXPLICIT/SOURCE_DERIVED/MARKET_TRANSLATION/V8_OPERATIONALIZATION/EXPERIMENTAL_ASSUMPTION/V8_DEFAULT); preserved_source_logic; unsupported_elements; transfer_risks (liquidation wicks, funding, 24/7, altcoin beta, taker-fee drag); required_data + data_status (AVAILABLE/PARTIAL/DATA_BLOCKED); translation_confidence.`
}

function specPrompt(chunk) {
  return `${PIPELINE}

ROLE: expert_spec_builder. Produce typed ExpertSpecs from translations. An expert is a PURE SIGNAL function; it does NOT decide size/leverage/portfolio admission or invent geometry.
${JSON.stringify(chunk)}

TASK (per translation with an executable core): expert_id, translation_id, source_claim_ids, expert_type (SIGNAL_EXPERT for strategies; regime/risk/lifecycle/methodology rules get their correct type), required_inputs (V8 feature keys), preconditions, emit_candidate_when, natural_invalidation, parameters (source_status/parameter_status/default/range), output SignalCandidate, missing_geometry {stop,target,position_size} booleans (true when undefined — central RiskGeometryResolver fills later), pit_safe/deterministic.`
}

function validatorPrompt(specs) {
  return `${PIPELINE}

ROLE: expert_validator. Apply hard gates to every expert spec:
- QA_PASSED / SPEC_INCOMPLETE / DATA_BLOCKED / REJECTED / DEFER (gated component or below priority).
Gates: source_fidelity, executability, falsifiability, pit, determinism, data_availability — pass/fail with reason.
${JSON.stringify(specs)}`
}

// ---------------------------------------------------------------- helpers

function chunk(arr, n) {
  const out = []
  for (let i = 0; i < arr.length; i += n) out.push(arr.slice(i, i + n))
  return out
}

// ---------------------------------------------------------------- phases

const books = args.books        // [{book_id, title, parts, packs:[paths], packs_b:[paths]}]

phase('Extract')
const jobs = []
for (const b of books) {
  for (const p of b.packs) jobs.push({ b, path: p, run: 'A' })
  for (const p of (b.packs_b || [])) jobs.push({ b, path: p, run: 'B' })
}
const extracts = await parallel(jobs.map(j => () =>
  agent(extractorPrompt(j, j.run), { label: `extract${j.run}:${j.b.book_id}`, phase: 'Extract', schema: RAW_CLAIMS_SCHEMA, effort: 'high' })))

const claimsAByBook = {}, claimsBByBook = {}
extracts.forEach((r, i) => {
  if (!r || !r.book_id) return
  const run = jobs[i].run
  const dest = run === 'B' ? claimsBByBook : claimsAByBook
  ;(dest[r.book_id] = dest[r.book_id] || []).push(...(r.claims || []))
})
log(`extract done: ${extracts.filter(Boolean).length} packs -> A ${Object.values(claimsAByBook).reduce((a, x) => a + x.length, 0)} claims, B ${Object.values(claimsBByBook).reduce((a, x) => a + x.length, 0)} claims`)

phase('Audit')
const auditBatches = chunk(books.map(b => ({ ...b, claimsA: claimsAByBook[b.book_id] || [] })), 2)
const audits = await parallel(auditBatches.map((cb, i) => () =>
  agent(auditorPrompt(cb), { label: `audit:${i + 1}`, phase: 'Audit', schema: AUDIT_SCHEMA, effort: 'low', model: 'haiku' })))
const auditByBook = {}
for (const a of audits.filter(Boolean)) if (a.book_id) auditByBook[a.book_id] = a
log(`audit done: ${Object.keys(auditByBook).length} books`)

phase('Adjudicate')
const adjBooks = books.map(b => ({ ...b, claimsA: claimsAByBook[b.book_id] || [], claimsB: claimsBByBook[b.book_id] || [], audit: auditByBook[b.book_id] }))
const adjudicated = await parallel(adjBooks.map(b => () =>
  agent(adjudicatorPrompt(b), { label: `adj:${b.book_id}`, phase: 'Adjudicate', schema: ADJUDICATED_SCHEMA, effort: 'high' })))
const adjByBook = {}
for (const a of adjudicated.filter(Boolean)) if (a.book_id) adjByBook[a.book_id] = a
log(`adjudicated: ${Object.keys(adjByBook).length} books`)

phase('Synthesize')
const synthBooks = books.map(b => ({ ...b, adjudications: adjByBook[b.book_id] || {}, claimsA: claimsAByBook[b.book_id] || [] }))
const synths = await parallel(synthBooks.map(b => () =>
  agent(synthesizerPrompt(b), { label: `synth:${b.book_id}`, phase: 'Synthesize', schema: SOURCE_STRATEGIES_SCHEMA, effort: 'high' })))
const strategiesByBook = {}
for (const s of synths.filter(Boolean)) if (s.book_id) strategiesByBook[s.book_id] = s.strategies || []
const allStrategies = Object.values(strategiesByBook).flat()
log(`synthesized ${allStrategies.length} strategies across ${Object.keys(strategiesByBook).length} books`)

phase('Recall')
const recallBatches = chunk(books.map(b => ({ ...b, claimsA: claimsAByBook[b.book_id] || [] })), 5)
const recalls = await parallel(recallBatches.map((cb, i) => () =>
  agent(recallPrompt(cb), { label: `recall:${i + 1}`, phase: 'Recall', schema: RECALL_SCHEMA, effort: 'low', model: 'haiku' })))
const recallResults = recalls.filter(Boolean).flatMap(r => r.results || [])
log(`recall audit: ${recallResults.length} books sampled`)

phase('Canonical')
const canonical = await agent(canonicalPrompt(allStrategies), { label: 'canonical', phase: 'Canonical', schema: CANONICAL_SCHEMA, effort: 'high' })

phase('Translate')
const stratChunks = chunk(allStrategies, 40)
const transRes = await parallel(stratChunks.map((c, i) => () =>
  agent(translatorPrompt(c), { label: `translate:${i + 1}`, phase: 'Translate', schema: TRANSLATIONS_SCHEMA, effort: 'high' })))
const translations = transRes.filter(Boolean).flatMap(t => t.translations || [])
log(`translated ${translations.length} strategies`)

phase('Spec')
const specChunks = chunk(translations, 40)
const specRes = await parallel(specChunks.map((c, i) => () =>
  agent(specPrompt(c), { label: `spec:${i + 1}`, phase: 'Spec', schema: EXPERT_SPECS_SCHEMA, effort: 'high' })))
const specs = specRes.filter(Boolean).flatMap(s => s.specs || [])
log(`built ${specs.length} expert specs`)

phase('Validate')
const validated = await agent(validatorPrompt(specs), { label: 'validate', phase: 'Validate', schema: VALIDATION_SCHEMA, effort: 'high' })

// metrics
const metrics = {
  pipeline_version: 'research_pipeline_v2.0',
  books: books.length,
  leads_total: books.reduce((a, b) => a + b.packs.reduce((x, p) => x + p.n_leads, 0), 0),
  packs_a: books.reduce((a, b) => a + b.packs.length, 0),
  packs_b: books.reduce((a, b) => a + (b.packs_b || []).length, 0),
  claims_a: Object.values(claimsAByBook).reduce((a, x) => a + x.length, 0),
  claims_b: Object.values(claimsBByBook).reduce((a, x) => a + x.length, 0),
  strategies: allStrategies.length,
  translations: translations.length,
  specs: specs.length,
  recall: recallResults,
  validation: validated ? validated.results : [],
}

return {
  metrics,
  books: books.map(b => ({ book_id: b.book_id, title: b.title })),
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
