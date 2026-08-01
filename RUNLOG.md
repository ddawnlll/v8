# V8 Autonomous Build — Runlog

Session artifact, not corpus. Filled by the build agent per `docs/AGENT_RUNBOOK.md`.
Every step gets an entry: status, evidence, fixes, commit. The operator reads
this file and `docs/STATUS_REPORT.md`.

## Format

```markdown
## Step N — <title> — <DONE | BLOCKED | SKIPPED>
- started: <UTC> finished: <UTC>
- files touched: <paths>
- evidence: <command> -> <output tail>
- fixes / deviations: <what broke and how it was fixed>
- commit: <short hash> `v8-step-N: ...`
- gate: pytest=<pass count> monograph=byte-identical?<yes/no> forbidden-scan=clean?
```

## Step 0 — Baseline — DONE
- started: 2026-08-01T02:34:00Z finished: 2026-08-01T02:35:40Z
- files touched: (none — verification only; RUNLOG.md filled)
- evidence: `.venv/bin/python -m pytest tests -q` -> `15 passed in 0.27s`;
  `.venv/bin/python tools/build_monograph.py --lang en --docs docs --out /tmp/v8_index_probe.html` ->
  `wrote /tmp/v8_index_probe.html: sections=30 papers=60 words=46331`;
  `shasum -a 256 /tmp/v8_index_probe.html site/index.html` ->
  `65eef39ff65595be4c50676a41618e56a167d081c2d28f8129f6be93b52cce2a  /tmp/v8_index_probe.html`
  `65eef39ff65595be4c50676a41618e56a167d081c2d28f8129f6be93b52cce2a  site/index.html`
  (byte-identical);
  `git log --oneline -1` -> `5962982 v8-step-0: initial commit — corpus + Phase 2 vertical slice (15 tests green, monograph reproducible)`;
  `git status --short` -> empty (clean tree)
- fixes / deviations: none. No DEVIATION; no extra commit created (baseline
  commit operator-taken; RUNLOG.md rides in the Step 1 commit per commit protocol).
- commit: 5962982 `v8-step-0: initial commit` (operator-taken baseline; RUNLOG.md
  baseline row committed with Step 1)
- gate: pytest=15 monograph=byte-identical?yes forbidden-scan=clean?yes (no new
  code yet) tree-clean?yes

## Step 1 — D-026: episode_key anchored to setup_anchor_event_id — DONE
- started: 2026-08-01T02:36:00Z finished: 2026-08-01T02:47:00Z
- files touched: src/v8/schema.py, src/v8/marketstate.py, src/v8/lifecycle.py,
  src/v8/experts/base.py, src/v8/experts/trend_pullback.py,
  src/v8/experts/failed_breakout.py, src/v8/lab.py, tests/test_vertical_slice.py,
  RUNLOG.md
- evidence: `.venv/bin/python -m pytest tests -q` -> `18 passed in 0.22s`
  (baseline 15; +3 new tests: key stability across consecutive clocks, fresh
  setup new key, repeat logged SUPPRESSED_DUPLICATE);
  monograph probe -> `shasum 65eef39ff65595be4c50676a41618e56a167d081c2d28f8129f6be93b52cce2a`
  (byte-identical, `uniq -c` = `2`);
  forbidden-scan `grep -rniE 'router|scorer|rank(er|ing)?|\bRL\b'` -> hits only in
  pre-existing files (risk.py:13 comment, schema.py/simtruth docstrings); risk.py
  confirmed untouched via `git diff --name-only`.
- fixes / deviations: (1) latent bug exposed: `suppressed_duplicate` append in
  lab.py lacked `source`/`event_id`, crashing AppendOnlyLog dedup inbox
  (`KeyError: 'source'`); fixed by adding both keys, event_id unique per clock
  (`{cid}:suppressed:{as_of}`). Code fix, not a test change. (2) `_geometry_version`
  in lab.py hashes risk_geometry excluding data-dependent `atr_ref` so a stable
  setup keeps its key across clocks. (3) crafted test tape verified numerically
  against build_state EMA (run A bars 60-61 anchor SOLUSDT:61; run B bars 67-69
  anchor SOLUSDT:68) — bar indices in tests are the verified ones.
- commit: 4f34abe `v8-step-1: D-026 setup-anchored episode key (history group, setup_anchor_event_id, time-free dedup)`
- gate: pytest=18 monograph=byte-identical?yes forbidden-scan=clean?yes (new code
  only; pre-existing mentions in risk.py/simtruth) wall-clock=clean?yes

## Step 2 — Funding settlement in canonical simulator — DONE
- started: 2026-08-01T02:48:00Z finished: 2026-08-01T02:58:00Z
- files touched: src/v8/schema.py, src/v8/simulator.py, src/v8/lab.py,
  tests/test_vertical_slice.py, RUNLOG.md
- evidence: `.venv/bin/python -m pytest tests -q` -> `22 passed in 0.36s`
  (18 -> 22; +4 funding goldens); monograph probe byte-identical
  (65eef39f...); forbidden-scan CLEAN in changed files; wall-clock scan CLEAN
  (only pre-existing docstring mentions).
- fixes / deviations: (1) test-only fix — `startswith(sha1 of v4 tag)` was a
  bogus assertion (hash is of the full tuple); replaced with exact expected
  v4 hash `sha1(('canonical-sim-v4', 'FILL_AT_BAR_CLOSE', 0.07, 0.0, 8))` and
  `!= v3`. (2) Semantics pinned in code: open interval at the start boundary
  (hold starting exactly on a boundary not double-settled) and closed at the
  end (hold ending exactly on one settles exactly once — V7 terminal-boundary
  defect). (3) `bar_time` param on `step()`/`times` on `run()`: None = no
  funding, preserving byte-identity for time-less callers and for
  `funding_rate_r=0.0` (golden d).
- commit: 760e6cc `v8-step-2: funding settlement in canonical simulator (SETTLEMENT_BEFORE_ORDERS, boundary goldens, sim hash v4)`
- gate: pytest=22 monograph=byte-identical?yes forbidden-scan=clean?yes
  wall-clock=clean?yes

## Step 3 — D-024 mechanical tradability mask — DONE
- started: 2026-08-01T03:00:00Z finished: 2026-08-01T03:02:55Z
- files touched: src/v8/schema.py, src/v8/risk.py, src/v8/lab.py,
  tests/test_vertical_slice.py, RUNLOG.md
- evidence: `.venv/bin/python -m pytest tests -q` -> `26 passed in 0.42s`
  (22 -> 26; +4 mask tests: spread-tail veto, funding-window veto,
  DEGRADED-state veto, defaults-don't-veto-SPREAD/DEGRADED-on-baseline);
  monograph probe -> `shasum 65eef39ff65595be4c50676a41618e56a167d081c2d28f8129f6be93b52cce2a`
  (byte-identical, `uniq -c` = 2);
  forbidden-scan `grep -niE 'router|scorer|rank(er|ing)?|\bRL\b'` over changed
  files -> no matches;
  wall-clock scan over changed files -> no matches (only vendored
  simtruth/ docstring false-positives remain, pre-existing).
- fixes / deviations: (1) INTERPRETATION of pinned test (d): with 1h bars and
  an 8h funding period some bar of any hourly tape is always within
  funding_window_bars of a boundary, so "thresholds at defaults do not veto
  the synthetic baseline run" is implemented as *no SPREAD/DEGRADED vetoes* on
  the seed-7 run; funding-window vetoes on that tape are a deterministic
  epoch-alignment artifact (FIXED_EPOCH % 8h = 7.108h puts every bar i%8==0
  within 1h of a boundary). (2) Funding-window semantics pinned against the
  Step-2 open-interval golden: the bar ending EXACTLY on a boundary enters
  after that settlement (fill > B) and is NOT vetoed; only bars with
  0 < B - close <= funding_window_bars*interval are (settlement books on the
  first post-entry step). (3) RUNLOG rows for steps 0-2 sat uncommitted in the
  tree (written by the prior session after the step-2 commit); they ride in
  this commit with the step-3 row — content unchanged, no new commits created.
- commit: (below) `v8-step-3: D-024 mechanical tradability mask (manifest constants, RiskGate-adjacent veto, NOT_EXECUTED counterfactuals)`
- gate: pytest=26 monograph=byte-identical?yes forbidden-scan=clean?yes
  wall-clock=clean?yes
