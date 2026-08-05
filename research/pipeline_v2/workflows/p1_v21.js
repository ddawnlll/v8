export const meta = {
  name: 'v8-p1-calibration',
  description: 'P1: book_router (125) + scout recall audit + 5-book calibration chain -> HITL-1 package',
  phases: [
    { title: 'Router', detail: 'route 125 books to M/X/G/F tracks' },
    { title: 'Recall', detail: 'llm_scout on sampled sections vs regex leads' },
    { title: 'Triage', detail: 'calibration lead triage (50 leads)' },
    { title: 'Novelty', detail: 'novelty gate vs empty registry' },
    { title: 'Extract', detail: 'T4 extractor A/B independent' },
    { title: 'AuditAdjudicate', detail: 'skeptic audit + adjudication' },
    { title: 'Synthesize', detail: 'book-level strategies' },
    { title: 'Translate', detail: 'crypto translation' },
    { title: 'Spec', detail: 'expert specs' },
    { title: 'Validate', detail: 'expert validation gates' },
  ],
}

const PROMPTS_DIR = 'research/pipeline_v2/prompts'
const ROLE = (name) => `Read your role prompt file exactly: ${PROMPTS_DIR}/${name}.v21.md. Follow it precisely; it overrides generic instructions.`

// ---------------------------------------------------------------- schemas

const ROUTER_SCHEMA = {
  type: 'object',
  properties: {
    routes: { type: 'array', items: {
      type: 'object',
      properties: {
        book_id: { type: 'string' },
        tracks: { type: 'array', items: { type: 'string' } },
        lineage: { type: 'string' },
        confidence: { enum: ['high', 'medium', 'low'] },
        evidence: { type: 'object' },
        notes: { type: 'string' },
      },
      required: ['book_id', 'tracks', 'lineage', 'confidence'],
    } },
  },
  required: ['routes'],
}

const SCOUT_SCHEMA = {
  type: 'object',
  properties: {
    section_id: { type: 'string' },
    candidates: { type: 'array', items: {
      type: 'object',
      properties: {
        anchor_text: { type: 'string' },
        local_start_line: { type: 'integer' },
        local_end_line: { type: 'integer' },
        claim_type_candidates: { type: 'array', items: { type: 'string' } },
        reason: { type: 'string' },
        priority: { type: 'string' },
        index_only: { type: 'boolean' },
      },
      required: ['anchor_text', 'claim_type_candidates', 'reason'],
    } },
  },
  required: ['section_id', 'candidates'],
}

const TRIAGE_SCHEMA = {
  type: 'object',
  properties: {
    decisions: { type: 'array', items: {
      type: 'object',
      properties: {
        lead_id: { type: 'string' },
        route: { enum: ['M', 'X', 'G', 'F', 'DROP'] },
        claim_type: { type: 'string' },
        drop_reason: { type: ['string', 'null'] },
        needs_wider_context: { type: 'boolean' },
      },
      required: ['lead_id', 'route', 'claim_type'],
    } },
  },
  required: ['decisions'],
}

const NOVELTY_SCHEMA = {
  type: 'object',
  properties: {
    decisions: { type: 'array', items: {
      type: 'object',
      properties: {
        lead_id: { type: 'string' },
        decision: { enum: ['MATCH', 'VARIANT_OF', 'NEW'] },
        matched_behavior_id: { type: ['string', 'null'] },
        difference: { type: 'string' },
        mechanism_draft: { type: 'object' },
      },
      required: ['lead_id', 'decision'],
    } },
  },
  required: ['decisions'],
}

const CLAIMS_SCHEMA = {
  type: 'object',
  properties: {
    claims: { type: 'array', items: { type: 'object' } },
  },
  required: ['claims'],
}

const AUDITS_SCHEMA = {
  type: 'object',
  properties: {
    audits: { type: 'array', items: { type: 'object' } },
  },
  required: ['audits'],
}

const ADJUDICATED_SCHEMA = {
  type: 'object',
  properties: {
    adjudications: { type: 'array', items: {
      type: 'object',
      properties: {
        lead_id: { type: 'string' },
        field_decisions: { type: 'array', items: { type: 'object' } },
        disagreement_count: { type: 'integer' },
        resolved_count: { type: 'integer' },
        unresolved_count: { type: 'integer' },
      },
      required: ['lead_id', 'field_decisions'],
    } },
  },
  required: ['adjudications'],
}

const STRATEGIES_SCHEMA = {
  type: 'object',
  properties: {
    strategies: { type: 'array', items: { type: 'object' } },
  },
  required: ['strategies'],
}

const TRANSLATIONS_SCHEMA = { type: 'object', properties: { translations: { type: 'array', items: { type: 'object' } } }, required: ['translations'] }
const SPECS_SCHEMA = { type: 'object', properties: { specs: { type: 'array', items: { type: 'object' } } }, required: ['specs'] }
const VALIDATION_SCHEMA = { type: 'object', properties: { results: { type: 'array', items: { type: 'object' } } }, required: ['results'] }

// ---------------------------------------------------------------- helpers

function chunk(arr, n) {
  const out = []
  for (let i = 0; i < arr.length; i += n) out.push(arr.slice(i, i + n))
  return out
}

function sectionPath(sid) {
  return `research/pipeline_v2/corpus/sections_text/${sid}.txt`
}

// ---------------------------------------------------------------- phases

const books = args.books           // [{book_id, title, year, first_section_id, sample_sections:[ids]}]
const recallSections = args.recall // [{label, section_id, book_id, text_path, is_leadless}]
const calibLeads = args.calib      // [{lead_id, book_id, section_id, priority, claim_type_candidates, anchor_text}]
const leadById = {}
for (const l of calibLeads) leadById[l.lead_id] = l

phase('Router')
const routerBatches = chunk(books, 5)
const routed = await parallel(routerBatches.map((cb, i) => () =>
  agent(`${ROLE('book_router')}\n\nRoute these ${cb.length} books. For each: read the front-matter/TOC section and 2 body sections listed.\n` +
    cb.map(b => `BOOK ${b.book_id} "${b.title}" (${b.year})\n  TOC: ${sectionPath(b.first_section_id)}\n  body: ${b.sample_sections.map(sectionPath).join(', ')}`).join('\n\n'),
    { label: `router:${i + 1}`, phase: 'Router', schema: ROUTER_SCHEMA, effort: 'medium' })))
const routeByBook = {}
for (const r of routed.filter(Boolean)) for (const x of (r.routes || [])) if (x.book_id) routeByBook[x.book_id] = x
log(`router: ${Object.keys(routeByBook).length}/${books.length} books routed`)

phase('Recall')
const recalls = await parallel(recallSections.map((s) => () =>
  agent(`${ROLE('llm_scout')}\n\nScout this section FULLY (read the whole file, no prior regex output): ${s.text_path}\nBook ${s.book_id}, label ${s.label}, section ${s.section_id}.`,
    { label: `recall:${s.section_id.slice(0, 28)}`, phase: 'Recall', schema: SCOUT_SCHEMA, effort: 'medium' })))

function dice(a, b) {
  const ta = new Set(a.split(/\s+/).filter(w => w.length > 3))
  const tb = new Set(b.split(/\s+/).filter(w => w.length > 3))
  if (!ta.size || !tb.size) return 0
  let inter = 0
  for (const w of ta) if (tb.has(w)) inter++
  return 2 * inter / (ta.size + tb.size)
}

// recall: does the deterministic regex scout find the same claim passages as the LLM scout?
const REGEX_LEADS = args.regex_leads || {}
const recallResults = recalls.filter(Boolean).map((r, i) => {
  const sec = recallSections[i]
  const regexLeads = REGEX_LEADS[sec.section_id] || []
  const cands = (r.candidates || [])
  let matched = 0
  const missed = []
  for (const c of cands) {
    const ct = (c.anchor_text || '').toLowerCase().replace(/\s+/g, ' ').slice(0, 160)
    const hit = regexLeads.some(rl => {
      const rt = (rl.anchor_text || '').toLowerCase().replace(/\s+/g, ' ').slice(0, 160)
      return (rt && (ct.includes(rt) || rt.includes(ct))) || dice(ct, rt) > 0.6
    })
    if (hit) matched++
    else missed.push({ text: (c.anchor_text || '').slice(0, 220), reason: c.reason, claim_types: (c.claim_type_candidates || []) })
  }
  return { section: { section_id: sec.section_id, book_id: sec.book_id, label: sec.label, is_leadless: sec.is_leadless },
           llm_leads: cands.length, regex_leads: regexLeads.length, matched,
           recall: cands.length ? matched / cands.length : 1,
           missed: missed.slice(0, 3) }
})
const recallSectionsDone = recallResults.filter(x => x.llm_leads > 0)
const recallOverall = recallSectionsDone.length
  ? recallSectionsDone.reduce((a, x) => a + x.recall, 0) / recallSectionsDone.length : 0
log(`recall: ${recallResults.length} sections, overall=${recallOverall.toFixed(3)} (${recallSectionsDone.length} sections with LLM leads)`)

phase('Triage')
const triageBatches = chunk(calibLeads, 25)
const triaged = await parallel(triageBatches.map((cb, i) => () =>
  agent(`${ROLE('claim_triage')}\n\nTriage these ${cb.length} leads (anchor_text + section context).\n` +
    cb.map(l => `LEAD ${l.lead_id} (${l.book_id}) route-priority ${l.priority}\n${l.anchor_text.slice(0, 800)}\nsection: ${sectionPath(l.section_id)}`).join('\n\n---\n\n'),
    { label: `triage:${i + 1}`, phase: 'Triage', schema: TRIAGE_SCHEMA, effort: 'medium' })))
const triageByLead = {}
for (const t of triaged.filter(Boolean)) for (const d of (t.decisions || [])) if (d.lead_id) triageByLead[d.lead_id] = d
const mLeads = calibLeads.filter(l => triageByLead[l.lead_id] && triageByLead[l.lead_id].route === 'M' && !triageByLead[l.lead_id].drop_reason)
const dropped = calibLeads.filter(l => triageByLead[l.lead_id] && triageByLead[l.lead_id].route === 'DROP')
log(`triage: ${calibLeads.length} leads -> M=${mLeads.length}, dropped=${dropped.length}`)

phase('Novelty')
const noveltyBatches = chunk(mLeads, 12)
const novelties = await parallel(noveltyBatches.map((cb, i) => () =>
  agent(`${ROLE('novelty_gate')}\n\nRegistry snapshot: EMPTY (calibration). Gate these ${cb.length} M-track leads.\n` +
    cb.map(l => `LEAD ${l.lead_id}\n${l.anchor_text.slice(0, 900)}\nsection: ${sectionPath(l.section_id)}`).join('\n\n---\n\n'),
    { label: `novelty:${i + 1}`, phase: 'Novelty', schema: NOVELTY_SCHEMA, effort: 'medium' })))
const noveltyByLead = {}
for (const n of novelties.filter(Boolean)) for (const d of (n.decisions || [])) if (d.lead_id) noveltyByLead[d.lead_id] = d
const newLeads = mLeads.filter(l => noveltyByLead[l.lead_id] && noveltyByLead[l.lead_id].decision === 'NEW')
const variantLeads = mLeads.filter(l => noveltyByLead[l.lead_id] && noveltyByLead[l.lead_id].decision !== 'NEW')
log(`novelty: M leads ${mLeads.length} -> NEW=${newLeads.length}, MATCH/VARIANT=${variantLeads.length}`)

phase('Extract')
// T4 only for NEW leads (bounded): A and B independent
const t4Batches = chunk(newLeads.slice(0, 30), 10)
const extractA = await parallel(t4Batches.map((cb, i) => () =>
  agent(`${ROLE('extractor_a')}\n\nExtract raw claims for these leads (source-faithful; do NOT add stop/target/timeframe).\n` +
    cb.map(l => `LEAD ${l.lead_id}\n${l.anchor_text}\nsection: ${sectionPath(l.section_id)}`).join('\n\n---\n\n'),
    { label: `extractA:${i + 1}`, phase: 'Extract', schema: CLAIMS_SCHEMA, effort: 'high' })))
const extractB = await parallel(t4Batches.map((cb, i) => () =>
  agent(`${ROLE('extractor_b')}\n\nYou are the INDEPENDENT second extractor; you have NOT seen extractor A's output. Extract raw claims for these leads.\n` +
    cb.map(l => `LEAD ${l.lead_id}\n${l.anchor_text}\nsection: ${sectionPath(l.section_id)}`).join('\n\n---\n\n'),
    { label: `extractB:${i + 1}`, phase: 'Extract', schema: CLAIMS_SCHEMA, effort: 'high' })))

const claimsA = extractA.filter(Boolean).flatMap(r => r.claims || [])
const claimsB = extractB.filter(Boolean).flatMap(r => r.claims || [])
log(`extract T4: A=${claimsA.length} claims, B=${claimsB.length} claims`)

phase('AuditAdjudicate')
const audits = await parallel(t4Batches.map((cb, i) => () =>
  agent(`${ROLE('skeptic_auditor')}\n\nAudit the extracted claims for these leads against the source sections.\n` +
    cb.map(l => `LEAD ${l.lead_id}\n${l.anchor_text}\nsection: ${sectionPath(l.section_id)}`).join('\n\n---\n\n'),
    { label: `audit:${i + 1}`, phase: 'AuditAdjudicate', schema: AUDITS_SCHEMA, effort: 'medium' })))
const auditByLead = {}
for (const a of audits.filter(Boolean)) for (const x of (a.audits || [])) if (x.lead_id) auditByLead[x.lead_id] = x

const adjBatches = chunk(newLeads.slice(0, 30), 10)
const adjudicated = await parallel(adjBatches.map((cb, i) => () =>
  agent(`${ROLE('adjudicator')}\n\nAdjudicate extractor A vs B for these leads (field by field; UNRESOLVED is valid).\n` +
    cb.map(l => `LEAD ${l.lead_id}\nA: ${JSON.stringify((claimsA.filter(c => c.lead_id === l.lead_id))[0] || {})}\nB: ${JSON.stringify((claimsB.filter(c => c.lead_id === l.lead_id))[0] || {})}`).join('\n\n---\n\n'),
    { label: `adj:${i + 1}`, phase: 'AuditAdjudicate', schema: ADJUDICATED_SCHEMA, effort: 'high' })))
const adjByLead = {}
for (const a of adjudicated.filter(Boolean)) for (const x of (a.adjudications || [])) if (x.lead_id) adjByLead[x.lead_id] = x

// A/B agreement
let agree = 0, disagree = 0, unresolved = 0
for (const x of Object.values(adjByLead)) {
  agree += (x.resolved_count || 0)
  unresolved += (x.unresolved_count || 0)
  for (const fd of (x.field_decisions || [])) {
    if (fd.extractor_a != null && fd.extractor_b != null && String(fd.extractor_a) === String(fd.extractor_b)) agree++
    else if (fd.decision !== 'UNRESOLVED') disagree++
    else unresolved++
  }
}
log(`adjudication: ${Object.keys(adjByLead).length} claims; agree=${agree} disagree=${disagree} unresolved=${unresolved}`)

phase('Synthesize')
const synthBooks = [...new Set(calibLeads.map(l => l.book_id))]
const synths = await parallel(synthBooks.map(bid => () =>
  agent(`${ROLE('book_synthesizer')}\n\nSynthesize source strategies for book ${bid} from its adjudicated claims.\nClaims: ${JSON.stringify(claimsA.filter(c => leadById[c.lead_id]?.book_id === bid))}`,
    { label: `synth:${bid}`, phase: 'Synthesize', schema: STRATEGIES_SCHEMA, effort: 'high' })))
const strategies = synths.filter(Boolean).flatMap(s => s.strategies || [])
log(`synthesize: ${strategies.length} strategies`)

phase('Translate')
const transRes = await parallel(chunk(strategies, 10).map((c, i) => () =>
  agent(`${ROLE('crypto_translator')}\n\nTranslate these source strategies to USDM perpetual 1h (provenance per field).\n${JSON.stringify(c)}`,
    { label: `translate:${i + 1}`, phase: 'Translate', schema: TRANSLATIONS_SCHEMA, effort: 'high' })))
const translations = transRes.filter(Boolean).flatMap(t => t.translations || [])

phase('Spec')
const specRes = await parallel(chunk(translations, 10).map((c, i) => () =>
  agent(`${ROLE('expert_spec_builder')}\n\nBuild ExpertSpecs from these translations (pure signal; missing_geometry flags).\n${JSON.stringify(c)}`,
    { label: `spec:${i + 1}`, phase: 'Spec', schema: SPECS_SCHEMA, effort: 'high' })))
const specs = specRes.filter(Boolean).flatMap(s => s.specs || [])

phase('Validate')
const validated = await agent(`${ROLE('expert_validator')}\n\nValidate these expert specs (QA_PASSED/SPEC_INCOMPLETE/DATA_BLOCKED/REJECTED/DEFER).\n${JSON.stringify(specs)}`,
  { label: 'validate', phase: 'Validate', schema: VALIDATION_SCHEMA, effort: 'high' })

// ---- HITL-1 package ----
const validationResults = (validated && validated.results) || []
const gatePass = validationResults.filter(r => r.status === 'QA_PASSED').length

return {
  pipeline_version: 'research_pipeline_v2.1',
  metrics: {
    books_routed: Object.keys(routeByBook).length,
    routes: routeByBook,
    recall_overall: recallOverall,
    recall_sections: recallResults,
    triage: { total: calibLeads.length, m: mLeads.length, dropped: dropped.length },
    novelty: { m: mLeads.length, new: newLeads.length, variant_match: variantLeads.length },
    t4: { leads_processed: newLeads.slice(0, 30).length, claims_a: claimsA.length, claims_b: claimsB.length },
    agreement: { fields_agree: agree, fields_disagree: disagree, unresolved },
    strategies: strategies.length,
    translations: translations.length,
    specs: specs.length,
    validation: { total: validationResults.length, qa_passed: gatePass, statuses: validationResults.map(r => r.status) },
  },
  claims_a: claimsA,
  claims_b: claimsB,
  audits: Object.values(auditByLead),
  adjudications: Object.values(adjByLead),
  strategies,
  translations,
  specs,
  validation: validationResults,
}
