# v8-next critical execution & gate-integrity remediation — 2026-11-03

**Scope:** fixes for the five defects recorded in
`audit_out/bug_hunt_2026-11-03/REPORT.md`. No live orders, no credentials, no
production account, no entry-signal or take-profit changes.

## Environment and baseline

| Item | Value |
|---|---|
| Branch / baseline HEAD | `main` / `f07d9e21d48dc61a6eb79e0dde98b61b02058eef` |
| Python | 3.12.12 |
| NautilusTrader | 2.0.0rc4 (pinned) |
| Baseline fast suite | 1043 passed, 41 skipped, 506 deselected (4.6 s) |
| Real tape | `/Users/hootie/src/v8/research/tape/multi-1h-4y/tape.jsonl` |
| Tape SHA-256 | `b27891e917c38b59aaede1c07fe8316cd0600332389bbefcb667253448a18fa0` |
| Tape size | 216 MiB, 30,696 BTCUSDT hourly candles in the audit window |

Baseline `mypy v8-next/src` already reported errors in unrelated files
(`certification.py`, `expert_strategy.py`, `audit/pipeline.py`, `app/paper.py`,
`app/portfolio.py`). The files changed by this remediation add no mypy errors.

## What changed

### 1. OCO / timeout cancellation (P0)
`adapters/swing_engine.py`
- Every cancellation now passes `order.client_order_id` (the pinned API type),
  not the `Order` object.
- Cancel requests, acknowledgements and rejections are separate, queryable
  events (`cancel_requests`, `cancel_acks`, `cancel_rejections`).
- A rejection keeps the order visible as a safety violation and is retried on
  the next bar, bounded to three attempts; exhausted retries publish
  `ORPHAN_EXIT_ORDER`.
- Timeout close retires both legs before submitting the reduce-only close.

### 2. Position identity, reduce-only protection (P0)
`adapters/swing_engine.py`
- Protection is submitted only after **both** the entry order is terminal and
  the native position id/quantity exist. The submission point is whichever of
  `on_order_filled` / `on_position_opened` happens second, plus a per-bar
  maintenance tick.
- Legs are sized from the engine's actual filled/reducible quantity, floored to
  the size increment. Requested quantity is never assumed.
- Both legs and the market close are built with `reduce_only=True` and the
  native `position_id`.
- Duplicate fill callbacks are deduplicated by event identity; a repeated
  callback cannot submit a second protection set.
- Protection rejection on the stop leg triggers a reduce-only emergency
  flatten; a target rejection is recorded and leaves the stop protection live.
- Late/unmatched fills are named, never absorbed into an unrelated campaign.

### 3. G3 dimensional accounting (P1)
`evaluation/gate_resolution.py`
- Every observation is monetary **USDT**: realized `realized_pnl` for closed
  campaigns, and `(mark - entry) * quantity * direction - entry taker fee` for
  open campaigns.
- Observations are sorted by their own event time (close event or scenario
  cutoff) before the equity path and drawdown.
- Variance is computed on dimensionless campaign returns
  (`PnL / initial_equity`), never on a mixed series.
- Closes are consumed once per open slot; orphan closes, unparseable PnL, and
  missing open quantity/mark block the regime with a named
  `ACCOUNTING_EVIDENCE_MISSING` reason.
- Published units and basis: `pnl_unit=USDT`,
  `return_unit=fraction_of_initial_equity`,
  `observation_basis=chronological_campaign_close_or_cutoff_mark`,
  `funding_included=false` (G3 has no funding input; this is disclosed, not
  zero-filled).

### 4. G7 evidence rule (P1)
`evaluation/gate_resolution.py`
- Removed the symmetric pass band `0.01 <= e < 20`.
- The gate now separates: `NO_DECISIONS`, `ZERO_EXPOSURE`,
  `INSUFFICIENT_OBSERVATIONS`, `INSUFFICIENT_EXPOSURE`,
  `INSUFFICIENT_DECISIONS`, `UNVERIFIED_PROVENANCE`,
  `EVIDENCE_AGAINST_CANDIDATE`,
  `STATISTICAL_EVIDENCE_RULE_NOT_PREREGISTERED`,
  `STATISTICAL_EVIDENCE_INSUFFICIENT`, `DRIFT_EXCEEDED`.
- Net-of-cost return is computed with a declared taker fee on exposure changes.
- A positive PASS now requires *all* of: declared forward window, verified
  provenance (`provenance_verified=True`, caller/trusted boundary), enough
  decisions and exposure, positive net return, a **pre-registered**
  `evidence_threshold` (no default), e-process at/above it, and drift inside
  the guard.
- Because the repository contains no pre-registered threshold, the default
  path fails closed with `STATISTICAL_EVIDENCE_RULE_NOT_PREREGISTERED`. This is
  a deliberate BLOCKED-by-spec outcome, not a fabricated pass rule.

### 5. G8 trust boundary (P1)
`adapters/shadow_ingest.py`, `evaluation/gate_resolution.py`
- A caller string (`provenance="authenticated_venue_statement"`), account id,
  filename or checksum no longer authenticates a file.
- Settlement additionally requires a trusted-ingestion receipt bound to the
  fill file SHA-256, venue, account id and issue time, and HMAC-signed with an
  out-of-band key (`V8_VENUE_ATTESTATION_KEY`). The key is a local trust
  anchor; the code does **not** claim the venue signs statements.
- Authenticated records must carry the full settlement schema (`side`,
  `venue_time_ns`, `order_id`); duplicate fill ids are rejected.
- G8 `PASS` now requires both the verified attestation and a successful
  account reconciliation. Missing or failed reconciliation publishes
  `RECONCILIATION_MISSING` / `RECONCILIATION_FAILED` and never `PASS`.
- Reconciliation now also compares signed fill quantity against native
  position quantity when both are available, in addition to fill/order counts.
- `account_reconciled=True` is set only when the reconciliation result actually
  reports `reconciled=True`.

## Regression tests added

- `tests/test_execution_safety_20261103.py` (10 tests): stop-first, target-first,
  timeout, long-tail stale revisit, same-bar stop/target eligibility, partial
  entry, cancel API type, cancel rejection visibility, stop rejection fail-safe,
  duplicate fill callback, unmatched late fill.
- `tests/test_gate_integrity_20261103.py` (15 tests): equal open/closed loss
  drawdown, long/short MTM signs, quantity scaling, fee effect, chronological
  drawdown, missing-evidence block, orphan close, G7 zero/wrong/unverified
  candidates, G8 unverified label, missing/failed/passing reconciliation,
  tampered attestation, duplicate fill ids, public-paper diagnostic.
- Updated the two tests that encoded the old unsafe G8 contract
  (`tests/test_gate_resolution.py`, `tests/test_public_shadow_nx10.py`).

## Verification

| Command | Result |
|---|---|
| `pytest -q v8-next/tests` | **1068 passed, 41 skipped, 506 deselected** (4.0 s) |
| `ruff check v8-next/src v8-next/tests` | **All checks passed** |
| `mypy v8-next/src` | 17 pre-existing errors in 5 untouched files; 0 in changed files |
| Real-tape probe (after fix) | `status=PASS`, `both_legs_filled=[]`, `stale_leg_fills=[]`, fill-derived net `0.001`, `orders_open_at_end=[]` |
| Real-tape probe (before fix) | `status=FAIL`, target filled 340 h after stop, fill-derived net `0.239` |
| G3 real-tape slice | BLOCKED with `INSUFFICIENT_REGIME_TRADES` on the 120-bar slice (honest fail-closed); no unit mix in the measured path |
| Probe `probe_gates.py` after fix | G3 equal-loss: open/closed both BLOCKED; G7 zero/wrong BLOCKED; G8 unverified BLOCKED |

## Acceptance matrix

| ID | Status | Evidence |
|---|---|---|
| EXEC-01 | PASS | `test_cancel_uses_client_order_id_never_order_object`; native run: 24 cancel acknowledgements, 0 rejections, no open orders at end |
| EXEC-02 | PASS | `test_stop_fill_retires_target...` (target CANCELED, no ghost after 300 bars) |
| EXEC-03 | PASS | `test_target_fill_retires_stop...` |
| EXEC-04 | PASS | `test_timeout_retires_exits...` |
| EXEC-05 | PASS | `test_cancel_rejection_is_visible_and_queryable` (fault-injected event; backtest cannot reject a cancel) |
| EXEC-06 | PASS | Long-tail revisit tests: no fill after campaign closure |
| EXEC-07 | PASS | `bracket_submitted.position_id` populated; `probe_reduce_only` shows `reduce_only` is the effective guard |
| EXEC-08 | PASS | Native order snapshots assert `is_reduce_only=True` on both legs and the close |
| EXEC-09 | PASS | `test_partial_entry_protects_actual_filled_quantity` |
| EXEC-10 | PASS | `test_duplicate_fill_callback_cannot_duplicate_protection`; `DuplicateFillIgnored` event |
| EXEC-11 | PASS | Fill-derived net, native open positions and adapter events all flat in every closure test; real tape consistent |
| EXEC-12 | PASS | `test_stop_rejection_triggers_reduce_only_fail_safe` (fault-injected rejection; emergency flatten path) |
| G3-01 | PASS | USDT observations, dimensionless returns (`pnl_unit` / `return_unit`) |
| G3-02 | PASS | 50% open loss drawdown `0.5005` vs realized `0.5`, both BLOCKED |
| G3-03 | PASS | `test_g3_missing_open_quantity_blocks` (`ACCOUNTING_EVIDENCE_MISSING`) |
| G3-04 | PASS | `test_g3_observations_are_chronological` |
| G7-01 | PASS | `NO_DECISIONS` / `ZERO_EXPOSURE`, BLOCKED |
| G7-02 | PASS | Always-long in a falling stream: `EVIDENCE_AGAINST_CANDIDATE`, BLOCKED |
| G7-03 | PASS | Provenance, exposure, observations and evidence are separate fields/states |
| G7-04 | **BLOCKED** | No pre-registered evidence threshold exists in the repository; the gate fails closed with `STATISTICAL_EVIDENCE_RULE_NOT_PREREGISTERED` |
| G8-01 | PASS | Caller label + account id + checksum yields `UNVERIFIED_PROVENANCE` |
| G8-02 | PASS | Attested file with no account -> `RECONCILIATION_MISSING` |
| G8-03 | PASS | Attested file with quantity mismatch -> `RECONCILIATION_FAILED` |
| G8-04 | PASS | `live_realization_verified` is derived from G8 PASS in the runner; only an attested + reconciled G8 can set it. Existing G9 tests still pass. |
| INT-01 | PASS | Full suite; G8 BLOCKED propagates as BLOCKED, never coerced to PASS |
| INT-02 | PASS | Public-paper and diagnostic-fold tests unchanged and passing |
| INT-03 | PASS | Diff touches execution lifecycle only; no entry/exit signal thresholds changed |
| INT-04 | PASS | No OOS protected-window code or data changed |
| INT-05 | PASS | Baseline and new regressions recorded above |

## Limitations and disclosures

1. **G7 positive PASS is intentionally unavailable by default.** The e-process
   under the existing bounded betting rule cannot reach a 20:1 threshold inside
   the 15% drift guard on realistic streams. Rather than tune a threshold
   against the evaluation window, the gate fails closed and names
   `STATISTICAL_EVIDENCE_RULE_NOT_PREREGISTERED`. This row is BLOCKED, not PASS.
2. **Cancel rejection is fault-injected.** NautilusTrader's backtest engine does
   not produce cancel rejections for a normal resting order; the visibility,
   retry bound and safety-violation path are unit-tested, not venue-simulated.
3. **Venue authenticity is a local trust anchor.** The HMAC receipt is produced
   by a trusted ingestion process, not by Binance. The spec limitation is
   documented in the code and this report; no venue-signed statement is claimed.
4. **Restart/reconstruction is not supported by this adapter** (in-memory
   state); no restart test is claimed.
5. **Real-tape probe relies on an external dataset** at the path above. The
   dataset hash is recorded; the PR tests do not require it.

No economic claim, live-order authority, or protected-OOS access is introduced.
