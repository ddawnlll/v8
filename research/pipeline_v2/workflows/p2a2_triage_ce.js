export const meta = {
  name: 'v8-p2a2-lead-triage-counterevidence',
  description: 'P2.A2: regex-lead triage (X/G/F + narrative books) and P3 counterevidence sweep. Agents write to disk.',
  phases: [
    { title: 'TriageLeads', detail: 'claim_triage on regex leads, 40/call' },
    { title: 'Counterevidence', detail: 'P3 corpus sweep, 1 call/book' },
  ],
}

const ROLE = (name) => `Read your role prompt file exactly: research/pipeline_v2/prompts/${name}.v21.md. Follow it precisely.`

const CONFIRM_SCHEMA = {
  type: 'object',
  properties: {
    book_id: { type: 'string' },
    output_path: { type: 'string' },
    n_records: { type: 'integer' },
    note: { type: 'string' },
  },
  required: ['book_id', 'output_path', 'n_records'],
}

phase('TriageLeads')
const triageJobs = args.triage_jobs
const triages = await parallel(triageJobs.map((j, i) => () =>
  agent(`${ROLE('claim_triage')}\n\nTriage these ${j.leads.length} leads of book ${j.book_id} (regex hints are weak):\n` +
    j.leads.map(l => `  ${l.id}\n${l.a}`).join('\n\n---\n\n') +
    `\n\nAfter deciding, WRITE the triage decisions as JSONL to: ${j.output_path} (fields: lead_id, route, claim_type, drop_reason, needs_wider_context, carries_quantity, confidence).\nThen return the confirmation. Be terse.`,
    { label: `ltriage:${j.book_id}:${i % 20}`, phase: 'TriageLeads', schema: CONFIRM_SCHEMA, effort: 'low', model: 'haiku' })))
const tOk = triages.filter(Boolean)
log(`lead triage done: ${tOk.length}/${triageJobs.length} jobs`)

phase('Counterevidence')
const ceJobs = args.ce_jobs
const ces = await parallel(ceJobs.map((j, i) => () =>
  agent(`${ROLE('counterevidence_sweeper')}\n\nSweep book ${j.book_id} for counterevidence (caveats, failures, contradictions, scope limits).\n` +
    (j.leads && j.leads.length ? `Candidate leads (${j.leads.length}): ${j.leads.slice(0, 20).map(l => l.lead_id).join(', ')}` : 'No regex leads; scan the book sections directly.') +
    `\n\nWrite the counterevidence records as JSONL to: ${j.output_path} (fields: book_id, page, exact_text, kind [CAVEAT|FAILURE_EXAMPLE|CONTRADICTION|SCOPE_LIMIT|REFUTATION], normalized_meaning, topic_terms, applies_to_hint).\nIf nothing found, write one record: {"book_id":"${j.book_id}","counterevidence_status":"NOT_FOUND_IN_SOURCE"}.\nThen return the confirmation.`,
    { label: `ce:${j.book_id}`, phase: 'Counterevidence', schema: CONFIRM_SCHEMA, effort: 'low', model: 'haiku' })))
const ceOk = ces.filter(Boolean)
log(`counterevidence done: ${ceOk.length}/${ceJobs.length} books`)

return {
  pipeline_version: 'research_pipeline_v2.1',
  triage_jobs_total: triageJobs.length,
  triage_jobs_done: tOk.length,
  triage_records: tOk.reduce((a, r) => a + (r.n_records || 0), 0),
  ce_books_done: ceOk.length,
  ce_records: ceOk.reduce((a, r) => a + (r.n_records || 0), 0),
}
