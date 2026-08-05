export const meta = {
  name: 'v8-p2a1-section-triage',
  description: 'P2.A1: section-level LLM triage for all M-track books (recall fix). Agents write triage JSONL to disk.',
  phases: [
    { title: 'Triage', detail: 'section-level triage, 3 sections per call' },
  ],
}

const ROLE = (name) => `Read your role prompt file exactly: research/pipeline_v2/prompts/${name}.v21.md. Follow it precisely.`

const CONFIRM_SCHEMA = {
  type: 'object',
  properties: {
    book_id: { type: 'string' },
    output_path: { type: 'string' },
    n_claims: { type: 'integer' },
    sections: { type: 'array', items: { type: 'object', properties: { section_id: { type: 'string' }, n_claims: { type: 'integer' }, routes: { type: 'array', items: { type: 'string' } } } } },
  },
  required: ['book_id', 'output_path', 'n_claims'],
}

phase('Triage')
const jobs = args.jobs
const results = await parallel(jobs.map((j, i) => () =>
  agent(`${ROLE('claim_triage_section')}\n\nTriage these sections of book ${j.book_id} (read each file fully):\n` +
    j.section_ids.map(sid => `  ${sid}: research/pipeline_v2/corpus/sections_text/${sid}.txt`).join('\n') +
    `\n\nAfter marking all claims, WRITE the claims as JSONL to this exact path using the Write tool: ${j.output_path}\n` +
    `Then return the confirmation (do not paste the claims into the return). Be terse; do not over-explain.`,
    { label: `triage:${j.book_id}:${i % 20}`, phase: 'Triage', schema: CONFIRM_SCHEMA, effort: 'low', model: 'haiku' })))

const ok = results.filter(Boolean)
const totalClaims = ok.reduce((a, r) => a + (r.n_claims || 0), 0)
log(`section triage done: ${ok.length}/${jobs.length} jobs, ${totalClaims} claims written`)

const byBook = {}
for (const r of ok) {
  byBook[r.book_id] = byBook[r.book_id] || { jobs: 0, claims: 0, paths: [] }
  byBook[r.book_id].jobs++
  byBook[r.book_id].claims += r.n_claims || 0
  byBook[r.book_id].paths.push(r.output_path)
}

return {
  pipeline_version: 'research_pipeline_v2.1',
  jobs_total: jobs.length,
  jobs_done: ok.length,
  jobs_failed: jobs.length - ok.length,
  claims_total: totalClaims,
  by_book: byBook,
}
