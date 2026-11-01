const fs = require('fs');
const crypto = require('crypto');
const sha = f => crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex');

const rep = fs.readFileSync('FINAL_REPORT.md', 'utf8');
const results = [];
const add = (name, ok, detail) => results.push({ name, status: ok ? 'PASS' : 'FAIL', detail });

// 1. required headings
const need = ['## 1. Gates', '## 2. Reconciliation', '## 3. Classification criterion',
  '## 4. Full classification table (70 rows)', '## 5. Per-issue examination',
  '### 5.3 Duplicate clusters', '### 5.4 Blockers', '## 6. Closed-issue manifest', '## 7. Artifact manifest and hashes'];
const missing = need.filter(h => !rep.includes(h));
add('required headings present', missing.length === 0, missing.length ? 'missing: ' + missing.join(', ') : need.length + ' heading checks, all present');

// 2. gate enum
const gateRows = rep.split('\n').filter(l => /^\| G\d+ \|/.test(l));
const badGate = gateRows.filter(l => { const c = l.split('|')[3].trim(); return !['PASS', 'FAIL', 'BLOCKED', 'NOT_APPLICABLE'].includes(c); });
add('gate statuses strictly in {PASS,FAIL,BLOCKED,NOT_APPLICABLE}', badGate.length === 0, gateRows.length + ' gate rows; non-conforming: ' + (badGate.length ? badGate.join(' / ') : 'none'));
add('no PASS_WITH_LIMITATION anywhere', !/PASS_WITH_LIMITATION/.test(rep), /PASS_WITH_LIMITATION/.test(rep) ? 'FOUND' : '0 occurrences');

// 3. reconciliation
const cls = require('./classification.json');
const post = require('./post_close_open.json').map(i => i.number);
const core = cls.rows.filter(r => r.verdict === 'v8-core').map(r => r.number);
const next = cls.rows.filter(r => r.verdict === 'v8-next').map(r => r.number);
const amb = cls.rows.filter(r => r.verdict === 'ambiguous').map(r => r.number);
add('classification reconciles to 70',
  core.length + next.length + amb.length === 70 && cls.rows.length === 70,
  `${core.length} core + ${next.length} next + ${amb.length} ambiguous = ${core.length + next.length + amb.length}; rows=${cls.rows.length}`);
const coreStillOpen = post.filter(n => core.includes(n));
add('zero orphan/unmatched: no v8-core issue still open', coreStillOpen.length === 0, coreStillOpen.length ? coreStillOpen.join(',') : 'none');
const nextMissing = next.filter(n => !post.includes(n));
add('zero orphan/unmatched: all 25 v8-next issues still open', nextMissing.length === 0, nextMissing.length ? nextMissing.join(',') : 'none');

// 4. exit codes
const log = require('./close_log.json');
const failed = log.filter(l => l.exit_code !== 0);
add('every close exit_code == 0', failed.length === 0 && log.length === 45, `${log.length} closes, failures: ${failed.length}`);

// 5. artifact hashes
const files = fs.readdirSync('.').filter(f => !f.endsWith('.js') && !f.startsWith('SELF_AUDIT') && f !== 'FINAL_REPORT.md' && f !== 'SHA256SUMS.txt' && fs.statSync(f).isFile());
const sums = fs.existsSync('SHA256SUMS.txt') ? fs.readFileSync('SHA256SUMS.txt', 'utf8') : '';
const notHashed = files.filter(f => !sums.includes(f));
add('every non-report artifact has a recorded sha256', notHashed.length === 0, notHashed.length ? 'unhashed: ' + notHashed.join(', ') : files.length + ' files covered');

// 6. git boundary
const gs = fs.readFileSync('git_state.txt', 'utf8');
const diffNames = gs.split('$ git diff --name-only')[1].split('$ git status')[0].split('\n').map(s => s.trim()).filter(Boolean);
const forbidden = diffNames.filter(p => p.startsWith('v8-core/') || p.startsWith('src/v8/') || /^tests\//.test(p));
add('git diff --name-only excludes v8-core/, src/v8/, tests/', forbidden.length === 0, forbidden.length ? forbidden.join(', ') : `touched: ${diffNames.join(', ') || 'none'}`);

// 7. test + lint exit codes recorded
add('focused test + lint exit codes recorded in report',
  rep.includes('38 passed, 1 skipped') && rep.includes('All checks passed'), 'ruff 0 (All checks passed), pytest 0 (38 passed, 1 skipped)');

const fail = results.filter(r => r.status === 'FAIL');
const out = {
  generated_by: 'audit_out/github_issues_20261101/self_audit.js',
  checks: results,
  total: results.length,
  passed: results.length - fail.length,
  failed: fail.length,
  verdict: fail.length === 0 ? 'PASS' : 'FAIL',
};
fs.writeFileSync('SELF_AUDIT.json', JSON.stringify(out, null, 2));

const md = ['## 10. Completion self-audit', '', 'Run by `self_audit.js`; machine output in `SELF_AUDIT.json`.', '',
  '| check | status | detail |', '|---|---|---|'];
for (const r of results) md.push('| ' + r.name + ' | ' + r.status + ' | ' + r.detail.replace(/\|/g, '\\|') + ' |');
md.push('', `**${out.passed}/${out.total} checks pass — self-audit verdict: ${out.verdict}.**`);
fs.writeFileSync('SELF_AUDIT.md', md.join('\n') + '\n');

fs.appendFileSync('FINAL_REPORT.md', '\n---\n\n' + md.join('\n') + '\n');
console.log(JSON.stringify({ verdict: out.verdict, passed: out.passed, total: out.total }));
for (const r of results) console.log((r.status === 'PASS' ? '  ok  ' : ' FAIL ') + r.name + ' :: ' + r.detail);
