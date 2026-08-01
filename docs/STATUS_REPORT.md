# V8 Autonomous Build — Status Report

**Session:** runbook steps 0-7, Phase 0-3 scope only
**Date (UTC):** 2026-08-01
**Prepared by:** V8-build-agent (autonomous session)
**Read this first** (runbook step 7): this report is the operator's only
required reading. RUNLOG.md holds the full per-step evidence.

---

## Summary

All 7 steps are **DONE**. The Phase 0-3 build is complete on the frozen
contract: no contract under `docs/` was modified (monograph probe rebuild is
byte-identical to the baseline hash at every step), the vertical-slice suite
grew monotonically 15 -> 42 tests, and one commit per step exists with the
`v8-step-N` message protocol.

**Gates held at every step:** pytest green with non-decreasing count;
monograph probe byte-identical (`65eef39ff65595be4c50676a41618e56a167d081c2d28f8129f6be93b52cce2a`);
no forbidden component names (`router|scorer|ranker|RL`) in new code; no wall
clock in `src/v8/`; one explicit-file-list commit per step.

**Forbidden scope respected:** no router, learned scorer, ranker, learned/RL
execution, online learning, or event-driven clock mode was created (rules
6/14). No frozen OOS was opened, `v8_slice_001` was not run, and no
profitability claim appears anywhere (rule 12; `NO_ECONOMIC_CLAIM` verdict
blocked by absent authority receipt).

## Steps

### Step 0 — Baseline — DONE
- Evidence: `.venv/bin/python -m pytest tests -q` -> `15 passed`; probe
  rebuild byte-identical; baseline commit `5962982` (operator-taken);
  clean tree.
- Commit: `5962982` `v8-step-0: initial commit` (operator-taken).

### Step 1 — D-026 episode_key anchored to setup_anchor_event_id — DONE
- Evidence: pytest `18 passed`; probe byte-identical; +3 key-stability/dedup
  tests.
- Fixes: lab.py suppressed-duplicate append missing `source`/`event_id`
  (store inbox crash) — code fix, not a test change; `_geometry_version`
  excludes data-dependent `atr_ref`.
- Commit: `4f34abe` `v8-step-1: ...`.

### Step 2 — Funding settlement in canonical simulator — DONE
- Evidence: pytest `22 passed`; probe byte-identical; +4 funding goldens
  (`SETTLEMENT_BEFORE_ORDERS`, boundary edges, window-vs-full replay,
  zero-rate byte-identity).
- Fixes: a bogus `startswith(v4 tag)` hash assertion replaced with the exact
  expected v4 hash; open-interval start / closed end boundary semantics
  pinned in code.
- Commit: `760e6cc` `v8-step-2: ...`.

### Step 3 — D-024 mechanical tradability mask — DONE
- Evidence: pytest `26 passed` (22 -> 26, +4); probe byte-identical.
- Interpretation pinned: (a) funding-window veto fires for entry bars with
  `0 < B - close <= funding_window_bars*interval`; the bar ending exactly ON
  a boundary enters after that settlement (Step-2 open-interval golden) and
  is NOT vetoed; (b) "defaults do not veto the synthetic baseline" is tested
  as no SPREAD/DEGRADED vetoes on the seed-7 run — with 1h bars some bar of
  any hourly tape is always within 1h of an 8h boundary, so funding-window
  vetoes on that tape are a deterministic epoch-alignment artifact, not a
  threshold overreach.
- Commit: `778ceb1` `v8-step-3: ...`.

### Step 4 — Phase 1 data plane: vision_backfill.py + tape audit — DONE
- Evidence: pytest `33 passed` (26 -> 33, +7 offline audit tests); CLI smoke
  offline: build `6 rows`, re-run `0 rows (skipped 6)` idempotent, `--audit`
  clean; lab replay of the produced tape verified.
- OPEN_PIN + DEVIATION: runbook pins "reuse tools/data.py's row-building
  logic (import it; do not fork it)", but `tools/data.py` raises SystemExit
  at import without polars/pandera/pyarrow/duckdb (none installed), and
  O-009 / runbook step 5 forbid adding those deps this session.
  `tools/vision_backfill.py` therefore mirrors data.py's *documented*
  contracts as stdlib code (kline column order + ms->ns conversion from
  `_normalize_kline_archive`; checksum-file contract from
  `_parse_checksum_file`/`_sha256_file`), cited inline. Real download is
  operator-only (`--download`); tests never touch the network.
- Commit: `b1e3c83` `v8-step-4: ...`.

### Step 5 — Phase 2 state engine: feature groups + lineage — DONE
- Evidence: pytest `37 passed` (33 -> 37, +4); probe byte-identical.
- Design notes: `FEATURE_GROUPS` declares the five pinned ontology groups
  plus a `raw` base layer (close) and the `history` group (D-026);
  `requires:` is a frozen declaration, not a per-state guarantee (short tapes
  can emit history before the 20-bar EMA warmup). Lineage hash extended to
  (value, max_input_available_time, group, feature_version) so a re-tag or
  re-version changes every dependent hash. Parquet materializations deferred
  (O-009). PIT tests run on synthetic tape (no Phase-1 tape in session).
- Commit: `64582ce` `v8-step-5: ...`.

### Step 6 — Phase 3 expert metadata + registry — DONE
- Evidence: pytest `42 passed` (37 -> 42, +5); probe byte-identical even with
  `docs/EXPERTS_REGISTRY.yaml` present (it is not in the monograph NAMES
  list). Registry YAML parses (pyyaml installed into the venv via uv —
  documented environment addition, `pyyaml>=6` added to the dev extra).
- Design notes: mechanism/behavior/variant ids per the pinned interpretation
  (`trend_continuation`/`pullback_in_trend`/`a`,
  `liquidity_vacuum_reentry`/`failed_breakout_reentry`/`a`); YAML-vs-code
  consistency test prevents ontology drift; `requires` audited against actual
  feature consumption. No registry experiment registered; nothing promoted.
- Commit: `00295a8` `v8-step-6: ...`.

### Step 7 — Status report — DONE
- This file; summary appended to RUNLOG.md; commit `v8-step-7: status report`.

## Deviations and fixes (complete list)

| Step | What | Resolution |
|---|---|---|
| 1 | `suppressed_duplicate` append crashed the store inbox (`KeyError: 'source'`) | Added `source`/`event_id` keys, event_id unique per clock — code fix, test unchanged |
| 1 | episode key varied with `atr_ref` (data-dependent) | `_geometry_version` hashes structural geometry only |
| 2 | `startswith(v4 tag)` hash assertion was bogus | Replaced with exact expected v4 hash + `!= v3` |
| 3 | Funding-window semantics vs Step-2 open-interval golden | Pinned: only `0 < B - close <= window` vetoes; exactly-on-boundary entries are clean |
| 3 | Pinned test (d) "defaults don't veto baseline" impossible literally (1h bars, 8h period) | Tested as no SPREAD/DEGRADED vetoes on seed-7; artifact documented |
| 4 | `tools/data.py` unimportable without forbidden deps (O-009) | OPEN_PIN + stdlib mirror of its documented contracts, cited inline |
| 4 | JSONL rows must round-trip `TapeRow(**r)` | `payload_hash`/`schema_version` nested inside `payload`, not top-level |
| 5 | Pinned group set lacks a home for `close` | Added `raw` base layer to the ontology table |
| 6 | Registry gate needs a YAML parser | `uv pip install pyyaml`; dev extra updated (environment, not contract) |
| 6 | Creating a file under `docs/` | Authorized by the runbook's own owns-list (`docs/EXPERTS_REGISTRY.yaml (new)`); probe byte-identity confirms no monograph section changed |

## Open pins (unresolved, operator decision)

1. **OPEN_PIN — data.py reuse (Step 4).** Literal `import tools.data` reuse is
   impossible in the slice venv (SystemExit on missing polars/pandera/
   pyarrow/duckdb) and O-009 forbids adding those deps this session. The
   stdlib mirror in `tools/vision_backfill.py` implements the same documented
   contracts. Resolve later via register decision: either accept the mirror,
   or install the heavy deps when Phase-1 parquet materialization lands
   (DATASET_SPEC section 5).
2. **Tracked corpus note (not a build defect):** IMPLEMENTATION_LAYOUT
   section 4 divergence rows 1-2 (episode_key anchor form; funding
   settlement) are closed in code by steps 1-2 but the frozen table still
   shows OPEN — updating the table is a docs/ change outside this session's
   writable set; operator should close those rows via a CHANGELOG entry.
3. **Interpretation record (Step 3):** the funding-window mask fires on the
   schedule regardless of `funding_rate_r` (pinned text is unconditional),
   and the seed-7 synthetic epoch produces funding-window vetoes on bars
   `i % 8 == 0` — a synthetic-tape artifact, not a threshold overreach.

## Unfinished steps

**None.** All runbook steps 0-7 are DONE within the 2-hour wall clock.

## Session artifact

- `RUNLOG.md` (repo root): full per-step entries with commands, output tails,
  fixes, commits, gates. Steps 0-2 rows were written by the prior session
  after the step-2 commit and rode in the step-3 commit (content unchanged).
- Commits (oldest -> newest): `5962982`, `4f34abe`, `760e6cc`, `778ceb1`,
  `b1e3c83`, `64582ce`, `00295a8`, and the `v8-step-7: status report` commit.
