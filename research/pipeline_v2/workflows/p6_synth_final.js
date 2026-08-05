export const meta = {
  name: 'v8-p6-synthesis-final',
  description: 'P6: per-book synthesis -> canonical registry -> multi-timeframe translation -> ExpertSpec -> validation. Final LLM stage before the HTML report.',
  phases: [
    { title: 'Synthesize', detail: 'book-level source strategies from triaged claims + P4 outputs' },
    { title: 'Canonical', detail: 'cross-book canonical merge (barrier)' },
    { title: 'Translate', detail: 'crypto/V8 multi-timeframe translation' },
    { title: 'Spec', detail: 'typed ExpertSpecs' },
    { title: 'Validate', detail: 'expert validation gates' },
  ],
}

const ROLE = (name) => `Read your role prompt file exactly: research/pipeline_v2/prompts/${name}.v21.md. Follow it precisely.`

const STRATS_SCHEMA = { type: 'object', properties: { strategies: { type: 'array', items: { type: 'object' } } }, required: ['strategies'] }
const CANON_SCHEMA = { type: 'object', properties: { relationships: { type: 'array', items: { type: 'object' } }, canonical_families: { type: 'array', items: { type: 'object' } } }, required: ['relationships', 'canonical_families'] }
const TRANS_SCHEMA = { type: 'object', properties: { translations: { type: 'array', items: { type: 'object' } } }, required: ['translations'] }
const SPECS_SCHEMA = { type: 'object', properties: { specs: { type: 'array', items: { type: 'object' } } }, required: ['specs'] }
const VAL_SCHEMA = { type: 'object', properties: { results: { type: 'array', items: { type: 'object' } } }, required: ['results'] }

function chunk(arr, n) {
  const out = []
  for (let i = 0; i < arr.length; i += n) out.push(arr.slice(i, i + n))
  return out
}

const claimPaths = args.claim_paths
const p4Outputs = args.p4_outputs || { registry: [], new_claims: [], corroborations: [] }

phase('Synthesize')
const books = Object.keys(claimPaths)
const synths = await parallel(books.map(b => () =>
  agent(`${ROLE('book_synthesizer')}\n\nSynthesize source strategies for book ${b}. Read its claims: ${claimPaths[b]}\n` +
    `P4 outputs for this book (NEW claims + corroborations, if any):\n` +
    JSON.stringify({
      new_claims: (p4Outputs.new_claims || []).filter(c => c.round || true).slice(0, 200).map(c => ({ claim_ref: c.claim_ref || c.lead_id, source_rule: c.source_rule })),
      corroborations: (p4Outputs.corroborations || []).filter(r => !r || true).length,
    }).slice(0, 4000) +
    `\n\nMerge the book's claims into source-native strategy variants (no crypto adaptation). A book may yield 0 strategies.`,
    { label: `synth:${b}`, phase: 'Synthesize', schema: STRATS_SCHEMA, effort: 'medium' })))
const strategiesByBook = {}
for (const s of synths.filter(Boolean)) if (s.book_id) strategiesByBook[s.book_id] = s.strategies || []
const allStrategies = Object.values(strategiesByBook).flat()
log(`synthesized ${allStrategies.length} source strategies across ${Object.keys(strategiesByBook).length} books`)

phase('Canonical')
const canonical = await agent(`${ROLE('canonical_merge')}\n\nCross-book canonical registry. Registry so far (${(p4Outputs.registry || []).length} behaviors):\n` +
  JSON.stringify((p4Outputs.registry || []).map(b => b.canonical_behavior_id)) +
  `\nSource strategies: ${JSON.stringify(allStrategies.map(s => ({ id: s.source_strategy_id || s.source_name, spec: s.source_native_spec }))).slice(0, 6000)}\n` +
  `\nRelate strategies across books (EXACT_DUPLICATE/CORROBORATES/REFINES/...), add new canonical families, keep source variants.`,
  { label: 'canonical', phase: 'Canonical', schema: CANON_SCHEMA, effort: 'high' })
log(`canonical: ${(canonical && canonical.relationships || []).length} relationships, ${(canonical && canonical.canonical_families || []).length} families`)

phase('Translate')
const stratChunks = chunk(allStrategies, 30)
const trans = await parallel(stratChunks.map((c, i) => () =>
  agent(`${ROLE('crypto_translator')}\n\nTranslate these source strategies to USDM perpetual, MULTI-TIMEFRAME (1h/4h/1d — choose per strategy, never force 1h).\n${JSON.stringify(c)}`,
    { label: `translate:${i + 1}`, phase: 'Translate', schema: TRANS_SCHEMA, effort: 'high' })))
const translations = trans.filter(Boolean).flatMap(t => t.translations || [])
log(`translated ${translations.length} strategies`)

phase('Spec')
const trChunks = chunk(translations, 30)
const specs = await parallel(trChunks.map((c, i) => () =>
  agent(`${ROLE('expert_spec_builder')}\n\nBuild typed ExpertSpecs from these translations (timeframe: 1h/4h/1d/MULTI; missing_geometry flags).\n${JSON.stringify(c)}`,
    { label: `spec:${i + 1}`, phase: 'Spec', schema: SPECS_SCHEMA, effort: 'high' })))
const allSpecs = specs.filter(Boolean).flatMap(s => s.specs || [])
log(`built ${allSpecs.length} expert specs`)

phase('Validate')
const validated = await agent(`${ROLE('expert_validator')}\n\nValidate these expert specs.\n${JSON.stringify(allSpecs)}`,
  { label: 'validate', phase: 'Validate', schema: VAL_SCHEMA, effort: 'high' })

return {
  pipeline_version: 'research_pipeline_v2.1',
  strategies_by_book: strategiesByBook,
  all_strategies: allStrategies,
  canonical,
  translations,
  specs: allSpecs,
  validation: (validated && validated.results) || [],
  counts: {
    strategies: allStrategies.length,
    translations: translations.length,
    specs: allSpecs.length,
    validation_total: ((validated && validated.results) || []).length,
  },
}
