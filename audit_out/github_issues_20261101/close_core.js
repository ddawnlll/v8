// Close every v8-core-scoped open issue, with a rationale comment. Records exit codes.
const fs = require('fs');
const { execFileSync } = require('child_process');
const c = require('./classification.json');
const targets = c.rows.filter(r => r.verdict === 'v8-core').map(r => r.number);

const commentFor = r => [
  'Closing: this issue is **`v8-core` scope**.',
  '',
  '`v8-core/` is archived and read-only — it is no longer developed (root `AGENTS.md` §1: only `v8-next/` is active, and `v8-core/` must never be modified, built, or tested). The subject/acceptance of this issue targets that archived Rust codebase, so there is no path to working it.',
  '',
  '**Scope evidence:** ' + r.rationale,
  '',
  'If the underlying concern still applies to the active `v8-next/` tree, re-file it against `v8-next/` with a v8-next code surface as the acceptance object.',
].join('\n');

const log = [];
for (const r of c.rows.filter(r => r.verdict === 'v8-core')) {
  let code = 0, err = '';
  try {
    execFileSync('gh', ['issue', 'close', String(r.number), '--reason', 'not planned', '--comment', commentFor(r)], { encoding: 'utf8', stdio: 'pipe' });
  } catch (e) { code = e.status === undefined ? -1 : e.status; err = String((e.stderr || e.message || '')).slice(0, 500); }
  log.push({ number: r.number, verdict: r.verdict, exit_code: code, stderr: err });
  process.stdout.write(`${r.number}:${code} `);
}
fs.writeFileSync('close_log.json', JSON.stringify(log, null, 2));
const failed = log.filter(l => l.exit_code !== 0);
console.log('\nattempted=' + log.length + ' ok=' + (log.length - failed.length) + ' failed=' + failed.length);
if (failed.length) console.log(JSON.stringify(failed));
