export const meta = {
  name: 'v8-recovery-missing-triage',
  description: 'Recovery: re-run triage jobs + counterevidence books whose outputs were lost in the RAM/reboot. Agents write to disk.',
  phases: [
    { title: 'TriageRecover', detail: 'missing lead-triage jobs' },
    { title: 'CERecover', detail: 'missing counterevidence books' },
  ],
}

const ROLE = (name) => `Read your role prompt file exactly: research/pipeline_v2/prompts/${name}.v21.md. Follow it precisely.`

const CONFIRM_SCHEMA = {
  type: 'object',
  properties: {
    book_id: { type: 'string' },
    output_path: { type: 'string' },
    n_records: { type: 'integer' },
  },
  required: ['book_id', 'output_path', 'n_records'],
}

phase('TriageRecover')
const jobs = args.jobs
const results = await parallel(jobs.map((j, i) => () =>
  agent(`${ROLE('claim_triage')}\n\nTriage the leads of book ${j.book_id}. Read the lead file fully:\n  ${j.input_path}\n` +
    `Each line is one lead: {"id": ..., "a": <passage>}. For EVERY lead, decide route (M|X|G|F|DROP), claim_type, drop_reason, needs_wider_context, carries_quantity, confidence.\n` +
    `WRITE the decisions as JSONL to: ${j.output_path} (fields: lead_id, route, claim_type, drop_reason, needs_wider_context, carries_quantity, confidence). Every input lead must appear exactly once.\n` +
    `Then return the confirmation. Be terse.`,
    { label: `rtriage:${j.book_id}:${i % 25}`, phase: 'TriageRecover', schema: CONFIRM_SCHEMA, effort: 'low', model: 'haiku' })))
const tOk = results.filter(Boolean)
log(`recovery triage done: ${tOk.length}/${jobs.length} jobs`)

phase('CERecover')
const ceJobs = args.ce_jobs
const ces = await parallel(ceJobs.map((j, i) => () =>
  agent(`${ROLE('counterevidence_sweeper')}\n\nSweep book ${j.book_id} for counterevidence (caveats, failures, contradictions, scope limits).\n` +
    (j.leads_path ? `Candidate leads file (Read it): ${j.leads_path}` : 'No regex leads; scan the book sections directly.') +
    `\n\nWrite the counterevidence records as JSONL to: ${j.output_path} (fields: book_id, page, exact_text, kind [CAVEAT|FAILURE_EXAMPLE|CONTRADICTION|SCOPE_LIMIT|REFUTATION], normalized_meaning, topic_terms, applies_to_hint).\nIf nothing found, write one record: {"book_id":"${j.book_id}","counterevidence_status":"NOT_FOUND_IN_SOURCE"}.\nThen return the confirmation.`,
    { label: `rce:${j.book_id}`, phase: 'CERecover', schema: CONFIRM_SCHEMA, effort: 'low', model: 'haiku' })))
const ceOk = ces.filter(Boolean)
log(`recovery CE done: ${ceOk.length}/${ceJobs.length} books`)

return {
  pipeline_version: 'research_pipeline_v2.1',
  recovery_triage_jobs: jobs.length,
  recovery_triage_done: tOk.length,
  recovery_ce_books: ceJobs.length,
  recovery_ce_done: ceOk.length,
  triage_records: tOk.reduce((a, r) => a + (r.n_records || 0), 0),
}
