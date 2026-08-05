export const meta = {
  name: 'v8-p2a2b-m-track-lead-triage',
  description: 'P2.A2b: regex-lead triage for all M-track books (10.7k leads). Agents read lead files, write triage to disk.',
  phases: [
    { title: 'TriageLeads', detail: 'claim_triage on M-track regex leads, 40/call' },
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

phase('TriageLeads')
const jobs = args.jobs
const results = await parallel(jobs.map((j, i) => () =>
  agent(`${ROLE('claim_triage')}\n\nTriage the leads of book ${j.book_id}. Read the lead file fully:\n  ${j.input_path}\n` +
    `Each line is one lead: {"id": ..., "a": <passage>}. For EVERY lead, decide route (M|X|G|F|DROP), claim_type, drop_reason, needs_wider_context, carries_quantity, confidence.\n` +
    `WRITE the decisions as JSONL to: ${j.output_path} (fields: lead_id, route, claim_type, drop_reason, needs_wider_context, carries_quantity, confidence). Every input lead must appear exactly once.\n` +
    `Then return the confirmation. Be terse.`,
    { label: `mtriage:${j.book_id}:${i % 25}`, phase: 'TriageLeads', schema: CONFIRM_SCHEMA, effort: 'low', model: 'haiku' })))

const ok = results.filter(Boolean)
log(`M lead triage done: ${ok.length}/${jobs.length} jobs, ${ok.reduce((a, r) => a + (r.n_records || 0), 0)} records`)

return {
  pipeline_version: 'research_pipeline_v2.1',
  jobs_total: jobs.length,
  jobs_done: ok.length,
  records: ok.reduce((a, r) => a + (r.n_records || 0), 0),
}
