export const meta = {
  name: 'v8-p4-novelty-gated-rounds',
  description: 'P4: novelty-gated mechanism extraction over 13 rounds. Frozen registry snapshot per round, T3 corroboration for matches, T4 (A/B/audit/adjudicate) for NEW, round-end merge barrier, saturation ledger.',
  phases: [
    { title: 'Gate', detail: 'novelty gate per book against frozen registry' },
    { title: 'T3', detail: 'corroboration for MATCH/VARIANT claims' },
    { title: 'T4', detail: 'A/B/audit/adjudicate for NEW + quantitative claims' },
    { title: 'Merge', detail: 'round-end canonical merge (barrier)' },
    { title: 'Saturate', detail: 'saturation ledger + downgrade decision' },
  ],
}

const ROLE = (name) => `Read your role prompt file exactly: research/pipeline_v2/prompts/${name}.v21.md. Follow it precisely.`

// ---------------------------------------------------------------- schemas

const GATE_SCHEMA = {
  type: 'object',
  properties: {
    book_id: { type: 'string' },
    decisions: { type: 'array', items: {
      type: 'object',
      properties: {
        claim_ref: { type: 'string' },
        decision: { enum: ['MATCH', 'VARIANT_OF', 'NEW'] },
        matched_behavior_id: { type: ['string', 'null'] },
        difference: { type: 'string' },
        mechanism_draft: { type: 'object' },
        carries_quantity: { type: 'boolean' },
      },
      required: ['claim_ref', 'decision'],
    } },
  },
  required: ['book_id', 'decisions'],
}

const CORROB_SCHEMA = {
  type: 'object',
  properties: {
    records: { type: 'array', items: {
      type: 'object',
      properties: {
        claim_ref: { type: 'string' },
        behavior_id: { type: 'string' },
        page: { type: ['integer', 'null'] },
        exact_text: { type: 'string' },
        added_conditions: { type: 'array', items: { type: 'string' } },
        added_parameters: { type: 'array', items: { type: 'object' } },
      },
      required: ['claim_ref', 'behavior_id'],
    } },
  },
  required: ['records'],
}

const CLAIMS_SCHEMA = {
  type: 'object',
  properties: { claims: { type: 'array', items: { type: 'object' } } },
  required: ['claims'],
}

const AUDITS_SCHEMA = { type: 'object', properties: { audits: { type: 'array', items: { type: 'object' } } }, required: ['audits'] }
const ADJ_SCHEMA = { type: 'object', properties: { adjudications: { type: 'array', items: { type: 'object' } } }, required: ['adjudications'] }

const MERGE_SCHEMA = {
  type: 'object',
  properties: {
    round: { type: 'integer' },
    new_behaviors: { type: 'array', items: {
      type: 'object',
      properties: {
        canonical_behavior_id: { type: 'string' },
        canonical_family_id: { type: 'string' },
        precondition_class: { type: 'string' },
        boundary_event: { type: 'string' },
        follow_through_state: { type: 'string' },
        resolution_event: { type: 'string' },
        direction_relation: { type: 'string' },
        source_claim_refs: { type: 'array', items: { type: 'string' } },
        variant_claim_refs: { type: 'array', items: { type: 'string' } },
      },
      required: ['canonical_behavior_id', 'canonical_family_id'],
    } },
    merged_variants: { type: 'array', items: { type: 'object' } },
    trial_events: { type: 'array', items: { type: 'object' } },
  },
  required: ['round', 'new_behaviors'],
}

// ---------------------------------------------------------------- seed registry (12 canonical behaviors from the 6 lineages)

const SEED_REGISTRY = [
  { canonical_behavior_id: 'trend_continuation_pullback', canonical_family_id: 'trend_following', precondition_class: 'established_trend', boundary_event: 'pullback_to_support', follow_through_state: 'trend_resumes', resolution_event: 'new_extreme', direction_relation: 'with_trend' },
  { canonical_behavior_id: 'breakout_retest', canonical_family_id: 'boundary_interaction', precondition_class: 'established_range', boundary_event: 'range_breach', follow_through_state: 'retest_holds', resolution_event: 'reversal_or_resume', direction_relation: 'against_breach' },
  { canonical_behavior_id: 'failed_breakout_reentry', canonical_family_id: 'boundary_interaction', precondition_class: 'established_range', boundary_event: 'false_breakout', follow_through_state: 'return_inside', resolution_event: 'reversal', direction_relation: 'against_breach' },
  { canonical_behavior_id: 'liquidity_sweep_reclaim', canonical_family_id: 'liquidity', precondition_class: 'prior_extreme', boundary_event: 'wick_through', follow_through_state: 'reclaim_close', resolution_event: 'reversal', direction_relation: 'with_reclaim' },
  { canonical_behavior_id: 'volatility_breakout', canonical_family_id: 'volatility_expansion', precondition_class: 'compression', boundary_event: 'range_expansion', follow_through_state: 'directional_move', resolution_event: 'trend_or_fade', direction_relation: 'with_break' },
  { canonical_behavior_id: 'mean_reversion_band', canonical_family_id: 'mean_reversion', precondition_class: 'overextension', boundary_event: 'band_touch', follow_through_state: 'reversion', resolution_event: 'return_to_mean', direction_relation: 'against_extension' },
  { canonical_behavior_id: 'support_resistance_bounce', canonical_family_id: 'boundary_interaction', precondition_class: 'established_level', boundary_event: 'level_test', follow_through_state: 'bounce', resolution_event: 'continuation_or_break', direction_relation: 'with_bounce' },
  { canonical_behavior_id: 'momentum_divergence_reversal', canonical_family_id: 'momentum', precondition_class: 'extended_move', boundary_event: 'price_divergence', follow_through_state: 'momentum_failure', resolution_event: 'reversal', direction_relation: 'against_trend' },
  { canonical_behavior_id: 'trend_following_channel', canonical_family_id: 'trend_following', precondition_class: 'established_channel', boundary_event: 'channel_test', follow_through_state: 'channel_holds', resolution_event: 'channel_break', direction_relation: 'with_trend' },
  { canonical_behavior_id: 'capitulation_exhaustion', canonical_family_id: 'capitulation_exhaustion', precondition_class: 'panic_selloff', boundary_event: 'volume_climax', follow_through_state: 'exhaustion', resolution_event: 'reversal', direction_relation: 'against_climax' },
  { canonical_behavior_id: 'volume_confirmed_breakout', canonical_family_id: 'volume', precondition_class: 'consolidation', boundary_event: 'breakout', follow_through_state: 'volume_confirm', resolution_event: 'continuation', direction_relation: 'with_break' },
  { canonical_behavior_id: 'gap_reversion', canonical_family_id: 'mean_reversion', precondition_class: 'price_gap', boundary_event: 'gap_open', follow_through_state: 'gap_fill', resolution_event: 'fill_or_continue', direction_relation: 'toward_fill' },
]

// ---------------------------------------------------------------- helpers

function chunk(arr, n) {
  const out = []
  for (let i = 0; i < arr.length; i += n) out.push(arr.slice(i, i + n))
  return out
}

// ---------------------------------------------------------------- phases

const rounds = args.rounds          // [{round, books: [book_id]}]
const gateChunks = args.gate_chunks // {book_id: [chunk paths]}
const START_REGISTRY = SEED_REGISTRY
const ROUNDS_TO_RUN = args.rounds_to_run || rounds.length

let registry = JSON.parse(JSON.stringify(START_REGISTRY))
const saturationLedger = []
const trialLedger = []
const allNew = []
const allCorroborations = []

for (let ri = 0; ri < ROUNDS_TO_RUN; ri++) {
  const rnd = rounds[ri]
  if (!rnd) break
  phase('Gate')
  const booksIn = rnd.books.filter(b => (gateChunks[b] || []).length)
  if (!booksIn.length) { saturationLedger.push({ round: rnd.round, books: [], note: 'no claims' }); continue }
  log(`round ${rnd.round}: ${booksIn.length} books gating`)

  // P4.a — novelty gate: 1 agent per gate chunk (40 M-claims), reads the chunk file, gates vs FROZEN registry
  const gateJobs = []
  for (const b of booksIn) {
    for (const cp of (gateChunks[b] || [])) gateJobs.push({ book_id: b, chunk_path: cp })
  }
  const gates = await parallel(gateJobs.map((j, i) => () =>
    agent(`${ROLE('novelty_gate')}\n\nBook ${j.book_id}. Read the claims chunk file: ${j.chunk_path}\n` +
      `(each line: claim_id + anchor passage; all are route == 'M'). Frozen registry snapshot (${registry.length} behaviors):\n` +
      JSON.stringify(registry) +
      `\n\nFor each claim decide MATCH | VARIANT_OF | NEW. Be CONSERVATIVE about NEW: if unsure between VARIANT_OF and NEW, choose VARIANT_OF. Every new behavior increases the program's trial count and weakens every later statistical claim.`,
      { label: `gate:r${rnd.round}:${i + 1}`, phase: 'Gate', schema: GATE_SCHEMA, effort: 'low', model: 'haiku' })))

  const decisions = gates.filter(Boolean).flatMap(g => g.decisions || [])
  const newClaims = decisions.filter(d => d.decision === 'NEW')
  const matchClaims = decisions.filter(d => d.decision !== 'NEW')
  const quantClaims = decisions.filter(d => d.carries_quantity)
  // quantitative claims go to T4 even if matched
  const t4Claims = [...newClaims, ...quantClaims.filter(d => !newClaims.includes(d))]
  log(`round ${rnd.round}: gated ${decisions.length} claims -> NEW=${newClaims.length}, MATCH/VARIANT=${matchClaims.length}, quant(T4) add=${quantClaims.length}`)

  phase('T3')
  const corrobChunks = chunk(matchClaims, 10)
  const corrob = await parallel(corrobChunks.map((c, i) => () =>
    agent(`${ROLE('corroborator')}\n\nCorroborate these ${c.length} claims against the registry (page-cited evidence, record author-added conditions/parameters).\n` +
      c.map(x => `CLAIM ${x.claim_ref} matched ${x.matched_behavior_id} diff=${x.difference || 'none'}\n`).join('\n') +
      `\nClaims detail is in the book files. Return a corroboration record per claim.`,
      { label: `t3:r${rnd.round}:${i + 1}`, phase: 'T3', schema: CORROB_SCHEMA, effort: 'medium' })))
  const corrobRecords = corrob.filter(Boolean).flatMap(x => x.records || [])
  allCorroborations.push(...corrobRecords.map(r => ({ ...r, round: rnd.round })))

  phase('T4')
  const t4Groups = chunk(t4Claims.slice(0, 60), 5)
  const t4A = await parallel(t4Groups.map((g, i) => () =>
    agent(`${ROLE('extractor_a')}\n\nExtract raw claims for these ${g.length} NEW/quantitative claims (book files hold the passages).\n` +
      g.map(x => `CLAIM ${x.claim_ref} (${x.decision}) draft=${JSON.stringify(x.mechanism_draft || {})}`).join('\n'),
      { label: `t4a:r${rnd.round}:${i + 1}`, phase: 'T4', schema: CLAIMS_SCHEMA, effort: 'high' })))
  const t4B = await parallel(t4Groups.map((g, i) => () =>
    agent(`${ROLE('extractor_b')}\n\nYou are the INDEPENDENT second extractor; you have NOT seen extractor A's output. Extract raw claims for these ${g.length} claims.\n` +
      g.map(x => `CLAIM ${x.claim_ref}\n`).join('\n'),
      { label: `t4b:r${rnd.round}:${i + 1}`, phase: 'T4', schema: CLAIMS_SCHEMA, effort: 'high' })))
  const t4Audit = await parallel(t4Groups.map((g, i) => () =>
    agent(`${ROLE('skeptic_auditor')}\n\nAudit these claims for counterevidence (read the book's counterevidence.jsonl if present).\n` +
      g.map(x => `CLAIM ${x.claim_ref}\n`).join('\n'),
      { label: `t4audit:r${rnd.round}:${i + 1}`, phase: 'T4', schema: AUDITS_SCHEMA, effort: 'low', model: 'haiku' })))
  const t4Adj = await parallel(t4Groups.map((g, i) => () =>
    agent(`${ROLE('adjudicator')}\n\nAdjudicate extractor A vs B for these ${g.length} claims (field by field; UNRESOLVED valid).\n` +
      g.map(x => `CLAIM ${x.claim_ref}\n`).join('\n'),
      { label: `t4adj:r${rnd.round}:${i + 1}`, phase: 'T4', schema: ADJ_SCHEMA, effort: 'high' })))

  const t4ClaimsOut = t4A.filter(Boolean).flatMap(x => x.claims || [])
  allNew.push(...t4ClaimsOut.map(c => ({ ...c, round: rnd.round })))

  phase('Merge')
  const merge = await agent(`${ROLE('canonical_merge')}\n\nRound ${rnd.round} merge. These NEW candidates were declared by the novelty gate this round:\n` +
    JSON.stringify(t4ClaimsOut.map(c => ({ claim_ref: c.claim_ref || c.lead_id, draft: c.mechanism_draft || c.source_rule }))) +
    `\nExisting registry (${registry.length}):\n` + JSON.stringify(registry.map(b => b.canonical_behavior_id)) +
    `\n\nMerge round-NEW candidates: identical mechanisms collapse into ONE canonical behavior (source variants preserved). Be CONSERVATIVE about is_new_behavior. Return new_behaviors (only genuinely new ones), merged_variants, and trial_events (FAMILY_PROPOSED/REJECTED/MERGED/VARIANT_ADDED).`,
    { label: `merge:r${rnd.round}`, phase: 'Merge', schema: MERGE_SCHEMA, effort: 'high' })

  if (merge && merge.new_behaviors) {
    registry = registry.concat(merge.new_behaviors)
  }
  if (merge && merge.trial_events) trialLedger.push(...merge.trial_events.map(e => ({ ...e, round: rnd.round })))

  phase('Saturate')
  const prev = saturationLedger[saturationLedger.length - 1]
  const dry = (merge && merge.new_behaviors && merge.new_behaviors.length === 0) ? (prev ? prev.consecutive_dry + 1 : 1) : 0
  const t4Mode = dry >= 3 ? 'DOWNGRADED' : 'ON'
  saturationLedger.push({
    round: rnd.round,
    books: booksIn,
    claims_gated: decisions.length,
    new_families: (merge && merge.new_behaviors || []).length,
    total_families: registry.length,
    consecutive_dry_rounds: dry,
    t4_mode: t4Mode,
  })
  log(`round ${rnd.round}: families=${registry.length}, new=${(merge && merge.new_behaviors || []).length}, t4_mode=${t4Mode}`)
}

return {
  pipeline_version: 'research_pipeline_v2.1',
  rounds_executed: Math.min(ROUNDS_TO_RUN, rounds.length),
  registry: registry,
  saturation_ledger: saturationLedger,
  trial_ledger: trialLedger,
  corroborations: allCorroborations,
  new_claims: allNew,
  counts: {
    registry_behaviors: registry.length,
    new_families_total: saturationLedger.reduce((a, s) => a + s.new_families, 0),
    corroborations: allCorroborations.length,
    new_claims_extracted: allNew.length,
  },
}
