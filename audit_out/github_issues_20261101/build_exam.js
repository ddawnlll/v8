const fs = require('fs');
const { E, CLUSTERS, BLOCKERS } = require('./examination.js');
const c = require('./classification.json');
const iss = new Map(require('./open_issues.json').map(i => [i.number, i]));
const next = c.rows.filter(r => r.verdict === 'v8-next').map(r => r.number).sort((a, b) => b - a);
const TICK = String.fromCharCode(96);

const vc = {};
for (const n of next) vc[E[n].verdict] = (vc[E[n].verdict] || 0) + 1;

const md = ['# Per-issue examination — 25 surviving v8-next issues', '',
  'Verdict vocabulary: ' + ['still-valid', 'already-fixed', 'stale-but-real', 'superseded', 'NOT_IDENTIFIABLE'].map(v => TICK + v + TICK).join(' | ') + '.',
  'Every verdict cites at least one real v8-next path or an executed command result. Cited `file:line` coordinates were treated as claims, not facts — several had drifted.', '',
  '## Verdict summary', '',
  '| verdict | count | issues |', '|---|---|---|'];
const byV = {};
for (const n of next) (byV[E[n].verdict] ||= []).push(n);
for (const k of ['still-valid', 'already-fixed', 'stale-but-real', 'superseded', 'NOT_IDENTIFIABLE'])
  if (byV[k]) md.push('| ' + k + ' | ' + byV[k].length + ' | ' + byV[k].join(', ') + ' |');

md.push('', '## Per-issue', '');
for (const n of next) {
  const e = E[n], i = iss.get(n);
  md.push('### #' + n + ' — ' + TICK + e.verdict + TICK + ' — ' + i.title, '');
  md.push('**Claim as filed:** ' + e.claim, '');
  md.push('**Check performed:** ' + e.check, '');
  md.push('**Evidence:**', '');
  for (const x of e.evidence) md.push('- ' + x);
  if (e.scope_note) md.push('', '**Scope note:** ' + e.scope_note);
  md.push('');
}

md.push('## Duplicate clusters', '');
for (const cl of CLUSTERS) {
  md.push('### ' + cl.id + ' — ' + cl.name, '');
  md.push('**Canonical issue:** #' + cl.canonical, '');
  md.push('**Members:** ' + cl.members.map(m => '#' + m).join(', '), '');
  md.push('**Why one cluster:** ' + cl.why, '');
}

md.push('## Blockers', '');
for (const b of BLOCKERS) md.push('- **#' + b.issue + '** — ' + b.blocker);

fs.writeFileSync('EXAMINATION.md', md.join('\n') + '\n');
fs.writeFileSync('examination.json', JSON.stringify({ verdicts: Object.fromEntries(next.map(n => [n, E[n]])), clusters: CLUSTERS, blockers: BLOCKERS, counts: vc }, null, 2));
console.log('counts', JSON.stringify(vc), 'bytes', fs.statSync('EXAMINATION.md').size);
