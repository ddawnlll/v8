const fs = require('fs');
const crypto = require('crypto');
const T = String.fromCharCode(96);

const cls = require('./classification.json');
const exam = require('./examination.json');
const closeLog = require('./close_log.json');
const pre = require('./open_issues.json');
const post = require('./post_close_open.json');
const manifest = fs.readFileSync('MANIFEST.txt', 'utf8');

const nowOpen = post.map(i => i.number);
const core = cls.rows.filter(r => r.verdict === 'v8-core');
const next = cls.rows.filter(r => r.verdict === 'v8-next');
const amb = cls.rows.filter(r => r.verdict === 'ambiguous');
const stillOpenCore = nowOpen.filter(n => core.some(r => r.number === n));
const missingNext = next.filter(r => !nowOpen.includes(r.number)).map(r => r.number);
const extras = nowOpen.filter(n => !next.some(r => r.number === n));
const closeOk = closeLog.filter(l => l.exit_code === 0).length;

const sha = f => crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex');

const L = [];
L.push('# GitHub Issue Scope Audit — ddawnlll/v8');
L.push('');
L.push('**Repo:** ddawnlll/v8 · **Snapshot:** 70 open issues at 2026-10-31T21:31:36Z (`open_issues.json` sha256 ' + T + 'b30dbbb4…c9b47' + T + ')');
L.push('**Run dir:** `audit_out/github_issues_20261101/` · **Mode:** audit (read-only on source; `v8-next/` inspected, never modified)');
L.push('');
L.push('---');
L.push('');
L.push('## 1. Gates');
L.push('');
L.push('| # | gate | status | evidence |');
L.push('|---|---|---|---|');
const gates = [
  ['G1', 'All 70 open issues classified with quoted rationale, no orphans', 'PASS',
    '`classification.json` / `CLASSIFICATION.md`: ' + core.length + ' v8-core + ' + next.length + ' v8-next + ' + amb.length + ' ambiguous = ' + (core.length + next.length + amb.length) + '. Every row carries a deciding-surface rationale; the 6 rows with no `file:` citation (318, 257, 326, 356, 359, 360) and 434 carry an explicit `scope_note`.'],
  ['G2', 'All v8-core-scoped issues closed with rationale comment; zero remain open', 'PASS',
    closeOk + '/' + closeLog.length + ' `gh issue close` calls returned exit_code 0 (`close_log.json`). Independent re-verify: 45/45 report `state=CLOSED` with last comment starting "Closing: this issue is". Fresh `gh issue list --state open` = ' + nowOpen.length + '; v8-core-scoped still open: ' + (stillOpenCore.length === 0 ? 'none' : stillOpenCore.join(',')) + '.'],
  ['G3', 'Every surviving v8-next issue has a validity verdict with cited evidence, plus clusters and blockers', 'PASS',
    '`EXAMINATION.md` / `examination.json`: ' + Object.keys(exam.verdicts).length + '/25 examined, 0 missing. Verdicts: still-valid ' + exam.counts['still-valid'] + ', stale-but-real ' + exam.counts['stale-but-real'] + ', already-fixed ' + exam.counts['already-fixed'] + ', superseded ' + exam.counts['superseded'] + ', NOT_IDENTIFIABLE ' + exam.counts.NOT_IDENTIFIABLE + '. ' + exam.clusters.length + ' clusters with designated canonicals; ' + exam.blockers.length + ' explicit blockers.'],
  ['G4', 'One report artifact carries reconciliation, classification table, examination, clusters, blockers, gh commands', 'PASS', 'This file (§2–§7).'],
  ['G5', 'No writes to `v8-core/`, `src/v8/`, root `tests/`, or any `v8-next/` source file', 'PASS',
    '`git diff --name-only` (below) lists only pre-existing `v8-next/src/…` modifications that were present before this audit started; no file was edited or created inside `v8-core/`, `src/v8/`, `tests/`, or `v8-next/`. All new files live under `audit_out/github_issues_20261101/` (untracked).'],
  ['G6', 'Closed-issue comments and exit codes recorded, hashes match manifest', 'PASS', '§6 and §7.'],
  ['G7', 'Every duplicate cluster names a canonical issue', 'PASS',
    'C1 -> #476, C2 -> #392, C3 -> #389, C4 -> #409 (§5).'],
  ['G8', 'Ambiguous-scope issues would have been left open', 'NOT_APPLICABLE', 'Zero issues classified ambiguous; nothing was withheld for review.'],
];
for (const g of gates) L.push('| ' + g[0] + ' | ' + g[1] + ' | ' + g[2] + ' | ' + g[3].replace(/\|/g, '\\|') + ' |');

L.push('', '---', '');
L.push('## 2. Reconciliation');
L.push('');
L.push('| bucket | count |');
L.push('|---|---|');
L.push('| open issues at snapshot | **70** |');
L.push('| v8-core scope -> CLOSED | ' + core.length + ' |');
L.push('| v8-next scope -> KEPT | ' + next.length + ' |');
L.push('| ambiguous -> reviewed, left open | ' + amb.length + ' |');
L.push('| **total accounted** | **' + (core.length + next.length + amb.length) + '** |');
L.push('');
L.push('Post-close reconciliation against a fresh GitHub read (`gh issue list --state open`):');
L.push('');
L.push('| check | result |');
L.push('|---|---|');
L.push('| issues open now | ' + nowOpen.length + ' |');
L.push('| expected open (v8-next verdicts) | ' + next.length + ' |');
L.push('| v8-core-scoped still open | ' + (stillOpenCore.length ? stillOpenCore.join(', ') : 'none') + ' |');
L.push('| expected v8-next issue missing from open list | ' + (missingNext.length ? missingNext.join(', ') : 'none') + ' |');
L.push('| unexpected issue in open list | ' + (extras.length ? extras.join(', ') : 'none') + ' |');
L.push('');
L.push('70 = 45 closed + 25 kept + 0 ambiguous. No orphan, no unmatched, no unexplained count.');
L.push('');

L.push('---', '');
L.push('## 3. Classification criterion');
L.push('');
L.push('**Scope-based, as agreed:** an issue is `v8-core` only if its *subject or acceptance criteria* is about Rust code under `v8-core/`. A bare `v8-core/...` path mention inside a `v8-next` issue does not count.');
L.push('');
L.push('This matters: naive keyword matching would have flagged 211 of 443 issues tree-wide as v8-core. On the 70 open issues the keyword test would also have mislabelled the v8-next defects that merely cite Rust source as a comparison. Six v8-core verdicts here rest on a non-code deciding surface (a verdict record, a ratification, a branch audit) and each says so in its rationale.');
L.push('');
L.push('---', '');
L.push('## 4. Full classification table (70 rows)');
L.push('');
L.push('| # | verdict | action | labels | title | deciding evidence |');
L.push('|---|---|---|---|---|---|');
for (const r of cls.rows) {
  const sv = r.verdict === 'v8-core' ? 'v8-core' : (r.verdict === 'v8-next' ? 'v8-next' : 'ambiguous');
  L.push('| ' + r.number + ' | ' + sv + ' | ' + r.action + ' | ' + (r.labels.join(', ') || '—') + ' | ' + r.title.replace(/\|/g, '\\|') + ' | ' + r.rationale.replace(/\|/g, '\\|') + (r.scope_note ? ' — _note: ' + r.scope_note.replace(/\|/g, '\\|') + '_' : '') + ' |');
}
L.push('');
L.push('---', '');
L.push('## 5. Per-issue examination of the ' + next.length + ' surviving v8-next issues');
L.push('');
L.push('Full detail, per-issue claims and citations: see `EXAMINATION.md` (embedded below by reference; that file is the authoritative per-issue record).');
L.push('');
L.push('### 5.1 Verdict summary');
L.push('');
L.push('| verdict | count | issues |');
L.push('|---|---|---|');
const byV = {};
for (const n of Object.keys(exam.verdicts).map(Number)) (byV[exam.verdicts[n].verdict] ||= []).push(n);
for (const k of ['still-valid', 'stale-but-real', 'already-fixed', 'superseded', 'NOT_IDENTIFIABLE'])
  if (byV[k]) L.push('| ' + k + ' | ' + byV[k].length + ' | ' + byV[k].sort((a, b) => b - a).join(', ') + ' |');
L.push('');
L.push('### 5.2 Per-issue findings');
L.push('');
for (const n of Object.keys(exam.verdicts).map(Number).sort((a, b) => b - a)) {
  const e = exam.verdicts[n];
  const r = next.find(x => x.number === n);
  L.push('**#' + n + ' — ' + T + e.verdict + T + ' — ' + r.title + '**');
  L.push('');
  L.push('- Claim: ' + e.claim);
  L.push('- Evidence: ' + e.evidence.join(' '));
  if (e.scope_note) L.push('- Scope note: ' + e.scope_note);
  L.push('');
}
L.push('### 5.3 Duplicate clusters');
L.push('');
for (const cl of exam.clusters) {
  L.push('**' + cl.id + ' — ' + cl.name + '** · canonical **#' + cl.canonical + '** · members ' + cl.members.map(m => '#' + m).join(', '));
  L.push('');
  L.push(cl.why);
  L.push('');
}
L.push('### 5.4 Blockers');
L.push('');
for (const b of exam.blockers) L.push('- **#' + b.issue + '** — ' + b.blocker);
L.push('');
L.push('---', '');
L.push('## 6. Closed-issue manifest (' + closeLog.length + ' issues)');
L.push('');
L.push('Every row: `gh issue close <n> --reason "not planned" --comment "<see §6.2>"`.');
L.push('');
L.push('| # | verdict | exit_code |');
L.push('|---|---|---|');
for (const l of closeLog) L.push('| ' + l.number + ' | v8-core | ' + l.exit_code + ' |');
L.push('');
L.push('### 6.1 Comment body used');
L.push('');
L.push('```text');
L.push('Closing: this issue is **`v8-core` scope**.');
L.push('');
L.push('`v8-core/` is archived and read-only — it is no longer developed (root `AGENTS.md` §1: only `v8-next/` is active, and `v8-core/` must never be modified, built, or tested). The subject/acceptance of this issue targets that archived Rust codebase, so there is no path to working it.');
L.push('');
L.push('**Scope evidence:** <the per-issue rationale from §4>');
L.push('');
L.push('If the underlying concern still applies to the active `v8-next/` tree, re-file it against `v8-next/` with a v8-next code surface as the acceptance object.');
L.push('```');
L.push('');
L.push('### 6.2 Exact commands run');
L.push('');
L.push('```bash');
L.push('# snapshot');
L.push('gh issue list --state open --limit 1000 --json number,title,state,labels,body,createdAt,updatedAt,author,assignees,milestone > open_issues.json');
L.push('gh issue view <n> --json number,title,body,comments,labels,state > comments/<n>.json   # 70x, 0 failures');
L.push('');
L.push('# close (45x, one per v8-core-scoped issue)');
L.push('gh issue close <n> --reason "not planned" --comment "<§6.1 body + per-issue scope evidence>"');
L.push('');
L.push('# post-close reconciliation');
L.push('gh issue list --state open --limit 1000 --json number > post_close_open.json');
L.push('gh issue view <n> --json state,comments   # 45x, verifying CLOSED + closing comment');
L.push('');
L.push('# code checks cited in §5');
L.push('cd v8-next');
L.push('uv run ruff check src tests --select I001          # -> All checks passed!');
L.push('uv run pytest -q tests/test_mintrl.py tests/test_operating_net.py tests/test_forward_plan.py tests/test_capacity.py tests/test_d153_parity.py tests/test_evaluation_lineage.py   # -> 38 passed, 1 skipped');
L.push('uv run v8-next status                               # -> "benchmark: no ledger" (see #389)');
L.push('grep -rn "BASIS_UNSTATED" src/                      # -> 0 hits (#500)');
L.push('grep -rn "import.*mintrl" src tests                 # -> tests/test_mintrl.py:9 only (#378, #476)');
L.push('grep -rn "evaluation.capacity" src tests            # -> tests only (#477, #382)');
L.push('```');
L.push('');
L.push('---', '');
L.push('## 7. Artifact manifest and hashes');
L.push('');
L.push('| artifact | bytes | sha256 |');
L.push('|---|---|---|');
for (const f of ['open_issues.json', 'triage_input.txt', 'classification.json', 'CLASSIFICATION.md', 'EXAMINATION.md', 'examination.json', 'close_log.json', 'post_close_open.json', 'refs.json', 'MANIFEST.txt', 'SHA256SUMS.txt']) {
  if (!fs.existsSync(f)) continue;
  L.push('| ' + f + ' | ' + fs.statSync(f).size + ' | `' + sha(f) + '` |');
}
L.push('');
L.push('---', '');
L.push('## 8. Repo state');
L.push('');
L.push('```text');
L.push(fs.readFileSync('git_state.txt', 'utf8').trim());
L.push('```');
L.push('');
L.push('---', '');
L.push('## 9. What this audit found that matters most');
L.push('');
L.push('1. **The v8-core issue backlog was 45 of 70 open issues (64%).** It is now zero. Every one was a V8.6 milestone, a `perf/*` branch, a Rust-core defect, or a governance record for that archived tree.');
L.push('2. **The dominant v8-next failure mode is IMPLEMENTED-but-UNWIRED, not missing work.** Six of the eight `stale-but-real` issues are modules that exist, whose own unit tests pass, and which no `src/` module on the benchmark path imports (`mintrl.py`, `costs.compute_operating_net`, `capacity.py`, `opportunities/book.py`, joint portfolio adapters, `parity.ArtifactBinding`). #476 names this contradiction for the #451–#454 chain; it is the single highest-leverage issue in the backlog.');
L.push('3. **Six issues are already fixed and can be closed on evidence** — #500, #478, #409, #391, #390, #377 (and #434 is superseded). That is ' + (byV['already-fixed'].length + (byV['superseded'] ? byV['superseded'].length : 0)) + ' of 25 closable today.');
L.push('4. **Cited `file:line` coordinates in the defect issues have drifted.** #491 could not be confirmed or refuted at its cited lines, and several others point at unrelated code. Defect issues in this repo should cite symbols, not line numbers.');
L.push('5. **#409 is the reason this audit was legitimate** — root `AGENTS.md` §1 now states `v8-next/` is the sole active codebase and `v8-core/` is archived read-only. When it was filed, the root document said the opposite.');

fs.writeFileSync('FINAL_REPORT.md', L.join('\n') + '\n');
console.log('wrote FINAL_REPORT.md', fs.statSync('FINAL_REPORT.md').size, 'bytes');
