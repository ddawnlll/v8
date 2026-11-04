# v8-next critical-bug hunt — 2026-11-03

**Scope:** `v8-next/` only. Audit mode (read-only for product code): no strategy,
engine, sizing, execution, or gate behaviour was modified. Everything here is an
additive probe plus its captured output.

**Method:** source inspection of the money/authority path, then controlled
reproduction. Findings are ranked by what they can corrupt: live/paper position
accounting first, gate verdicts second.

**Verdict: FAIL — 3 critical and 2 high-severity defects reproduce.**

| # | Severity | Area | One-line finding |
|---|---|---|---|
| 1 | CRITICAL | `adapters/swing_engine.py` | OCO/timeout cancel is a no-op: `cancel_order()` receives an `Order` instead of a `ClientOrderId`, raises inside the callback, and the error is swallowed by NautilusTrader. Sibling bracket legs stay live. |
| 2 | CRITICAL | `adapters/swing_engine.py` | Bracket legs carry `position_id=None` (submitted before `PositionOpened`) and are not `reduce_only`; a stale leg therefore opens an untracked opposite position. Reproduced on real tape. |
| 3 | HIGH | `evaluation/gate_resolution.py` G3 | Open-position MTM (dimensionless return) is added to realized PnL (USDT) in one equity/drawdown series. A 50% open loss PASSes G3; the same loss realized BLOCKs. |
| 4 | HIGH | `evaluation/gate_resolution.py` G7 | Pass band `0.01 <= e < 20` accepts zero-exposure and always-wrong candidates. Both were measured as PASS. |
| 5 | HIGH | `evaluation/gate_resolution.py` G8 | `PASS/LIVE_VENUE_SETTLED` is minted from a local JSONL file when the caller labels provenance `authenticated_venue_statement`; no signature or account reconciliation is required. |

---

## 1. CRITICAL — bracket OCO/timeout cancellation never happens

**Location:** `src/v8_next/adapters/swing_engine.py:402` (timeout close) and
`:463` (sibling cancel after a bracket-leg fill).

**Root cause.** `Strategy.cancel_order` takes a `ClientOrderId`, but both call
sites pass the cached `Order` object:

```python
for order in list(self.cache.orders_open(instrument_id=self.instrument_id)):
    self.cancel_order(order)          # line 402, 463
```

The pyo3 binding raises `TypeError: 'LimitOrder' object is not an instance of
'ClientOrderId'`. NautilusTrader catches exceptions raised inside strategy
callbacks and logs them, so the replay continues with the sibling order still
`ACCEPTED`. The source comment claims the sibling "is cancelled from
`on_order_filled`"; the probe shows the cancel call raises before any cancel
command is emitted.

**Evidence (mechanics probe, `results/swing_oco.json`).**

```
["filled", "O-...-2", "95.00"]
["cancel_order_raised", "TypeError", "'LimitOrder' object is not an instance of 'ClientOrderId'"]
["position_closed", "BTCUSDT-PERP.BINANCE-Probe-000"]
["filled", "O-...-3", "105.00"]            <-- sibling target fills afterwards
["position_opened", "BTCUSDT-PERP.BINANCE-Probe-000"]   <-- opposite SHORT
```

The run ends with an open `SHORT 1.000` that the probe never intended to hold.

**Real-tape evidence (`results/swing_real_tape.json`).** Unmodified
`run_swing_engine` on `plain_swing`, BTCUSDT, 2022-07-01..2025-12-31:

* the 2022-08-04 SHORT campaign's stop filled at `1659668400000000000`;
* its target `O-20220804-170000-001-000-7` filled **340 hours later** at
  `1660892400000000000`;
* the run's fills net to **+0.239 BTC**, while the adapter's event record reports
  4 opens / 3 closes and a tracked campaign that is closing at timeout.

The target fill is the stale leg from a campaign that had already closed, not a
new campaign.

**Impact.** Every engine-lane artifact that trusts the event record (orders,
positions, PnL, reconciliation) can be computed on a position the adapter does
not track. The same failure affects the timeout path, which is supposed to
retire both legs before the market close.

**Fix direction (not applied).** Pass `order.client_order_id`; assert after the
cancel that the sibling is not open; add a regression that the timeout/sibling
path leaves `orders_open_at_end == []` and that the sibling never fills.

---

## 2. CRITICAL — bracket legs are not reduce-only and are submitted before the position exists

**Location:** `src/v8_next/adapters/swing_engine.py:383-384`, submitted from
`on_order_filled` (`:426`) while `active_position_id` is assigned only in
`on_position_opened` (`:465`).

**Root cause, two independent mistakes.**

1. NautilusTrader calls `on_order_filled` **before** `on_position_opened`.
   Measured sequence: `filled` → `position_opened`. At bracket submission the
   cache has no open position, so `_position_id()` returns `None` and both legs
   are submitted with `position_id=None`.
2. Even when a `position_id` is supplied, it does not make an order reduce-only.
   `probe_reduce_only.py` submits a stop after `PositionOpened` with
   `position_id=pid`: the cached order still reads `position_id=null` and
   `is_reduce_only=false`. The control order built with `reduce_only=True`
   reads `is_reduce_only=true`. The adapter constructs both legs without that
   argument.

**Evidence.** `results/swing_oco.json` records
`["positions_open_at_entry_fill", "0"]`, then
`["bracket_submitted", "None", "None", "False", "False"]` (stop id, target id,
stop reduce-only, target reduce-only). On the real tape, the stale target from
finding 1 fills as a **BUY 0.239** while the adapter's tracked campaign is a
0.004 position — a position 60x larger than the campaign it is attributed to.

**Impact.** Any stale or double-triggered leg becomes an entry rather than a
reduction. On a bar whose range spans both stop and target, the second leg can
open the opposite position immediately; a partial entry fill makes the bracket
size exceed the position. The adapter never reconciles this against its `plan`.

**Fix direction (not applied).** Submit protection from `on_position_opened`
with `reduce_only=True` and the actual filled quantity, or use
`order_factory.bracket(...)`; enforce a guard that a protection order can only
subtract from the position it was created for.

**Relationship to the existing ledger.** This confirms
`AUDIT_FOLLOWUPS_2026-10-31.md` item 1 ("stop/target submitted before the
position id is known") and adds the missing half — `position_id` alone is not a
reduce-only instruction — plus a real-tape fill.

---

## 3. HIGH — G3 mixes USDT PnL with dimensionless MTM

**Location:** `src/v8_next/evaluation/gate_resolution.py:414-432`.

Realized campaigns append `float(realized_pnl)` in USDT (`:419`). Open campaigns
append `((last_close - entry) / entry) * direction`, a dimensionless return
(`:425-426`), to the same `pnls` list; the drawdown loop then starts at 10000
and does `cum_equity += pnl` (`:432`). One USDT of loss and one 100% open loss
are 1.0 and -1.0 respectively.

**Evidence (`results/gates.json`).** Holding the candidate fixed, a 50% loss on
an open position is scored as drawdown `0.00005` → **G3 PASS**. The identical
50% loss realized is `0.5` → **G3 BLOCKED**.

**Secondary defect in the same loop:** `next(c for c in closed if
c["position_id"] == pos["position_id"])` pairs by netting position id only. In
NETTING, several opens reuse one id, so a later open can consume the first
close again; the G3 PnL list can double-count a close.

**Impact.** G3 can pass a regime whose open exposure lost most of its capital,
and the published `max_observed_drawdown` / `return_variance` are not in the
declared units. It also breaks the "one accounting contract" rule the G5 code
explicitly enforces.

**Fix direction (not applied).** Convert open MTM to USDT via entry notional
(or quantity × price) before appending; pair by `opening_order_id` and event
order, not position id; assert one unit per series.

---

## 4. HIGH — G7 passes inert and always-wrong candidates

**Location:** `src/v8_next/evaluation/gate_resolution.py:1259`:
`passed = 0.01 <= e_process_raw < 20.0 and drift_val < 0.15`.

That band treats maximal evidence **against** the candidate (e near 0.01) as a
pass, and accepts e = 1.0 from a candidate that never took exposure. The
e-process starts at 1.0 and each update is bounded in `[0.9, 1.1]`, so a losing
run only crawls downward and can remain inside the band.

**Evidence (`results/gates.json`).**

| candidate | exposure bars | final e | drift | verdict |
|---|---|---|---|---|
| no decisions at all | 0 | 1.0 | 0.0 | **PASS** |
| LONG on a monotonically falling stream | 99 | 0.9517 | 0.0483 | **PASS** |

The always-wrong candidate is long on every one of 99 observed bars while price
falls 0.05% per bar; it still PASSes because the e-process only reaches 0.9517
and drift stays below 0.15.

**Reachability.** The current benchmark runner calls G7 without a declared
stream, so it publishes UNKNOWN; the defect is latent for that path but fully
reachable through `evaluate_g7_prospective_shadow` and any future wiring of a
prospective window.

**Fix direction (not applied).** Require `candidate_exposure_bars` above a
declared minimum and one-sided evidence (a high e-value, not a symmetric band);
separate the drift guard from the evidence decision; fail closed on zero
exposure.

---

## 5. HIGH — G8 trusts caller-declared provenance and can PASS unreconciled

**Location:** `src/v8_next/evaluation/gate_resolution.py:1358-1370`;
provenance handling in `src/v8_next/adapters/shadow_ingest.py:56-62,121-126`.

`provenance` and `account_id` are caller-supplied strings. If
`provenance == "authenticated_venue_statement"` and `account_id` is non-empty,
any well-formed local JSONL file reads `LIVE_VENUE_SETTLED`; with `account=None`
the function still returns `GateState.PASS` and only labels
`account_reconciled=False`.

**Evidence (`results/gates.json`).** A single local JSONL row, no account, no
signature:

```
state=PASS  mode=LIVE_VENUE_SETTLED  authority=VENUE_STATEMENT  account_reconciled=false
```

**Impact.** The live-realization authority boundary is enforced by a string the
same caller can set. Anything that consumes a G8 PASS (certificate/claim
elevation) can be reached without a venue statement or account reconciliation.

**Fix direction (not applied).** Accept only a verifiable artifact (signed
statement / API-sourced file with digest and venue metadata), independently
verify the signature, and refuse PASS unless reconciliation actually ran and
matched. Unverified declarations should stay NOT_APPLICABLE or BLOCKED.

---

## Already known, not counted as new

`AUDIT_FOLLOWUPS_2026-10-31.md` remains accurate for funding re-timing (#2),
the future-close funding mark on irregular bars (#3), the G5 Bonferroni family
(#4), `p=0.0` in the White reality check (#5), the partially-failed DuckDB
fallback (#6), and hardcoded tape paths (#7). They are lower reachability than
the five defects above and are not claimed as fixed here.

## Artifact manifest

| Artifact | SHA-256 |
|---|---|
| `probe_swing_oco.py` | `ceae3ce1e3989d917b4638370c5fcdfa2ad10e4cd28363f0f06b740e6f4ef6c4` |
| `probe_swing_real_tape.py` | `26c20c491a1c2a74b6550059c6cae1901028ebc410bb8ea15f59b869433be13a` |
| `probe_gates.py` | `2e93e52d8b5c2039ee6920ec79f92c9708db0006ab839981c697a1dc21fccb91` |
| `probe_reduce_only.py` | `40b2868ba7d6b527c34e07c4993ce660181fba5ddda8767c369763b6895b2751` |
| `results/swing_oco.json` | `93b1dbb2ec74fddb4be021b93bcf5c1172fce40871387820cbc1859d97514674` |
| `results/swing_real_tape.json` | `c3ca4e2f504b268d6df72e4f38f6486e72517de32bd32d6e85c97ab07ea203cc` |
| `results/gates.json` | `345d83ac96f147ec9ca60ad50dc6f26934a32078bd06babcb0b37ec561f787ab` |
| `results/reduce_only.json` | `edc126f21c91a299cffd74ea794b004081404f848b5ff8560f6bc45a59497aba` |

## Reproduction

```sh
cd v8-next
uv run --project v8-next python audit_out/bug_hunt_2026-11-03/probe_swing_oco.py
uv run --project v8-next python audit_out/bug_hunt_2026-11-03/probe_reduce_only.py
uv run --project v8-next python audit_out/bug_hunt_2026-11-03/probe_swing_real_tape.py \
    --tape /Users/hootie/src/v8/research/tape/multi-1h-4y/tape.jsonl
uv run --project v8-next python audit_out/bug_hunt_2026-11-03/probe_gates.py
```

The mechanics/gate probes need no tape. The real-tape probe exits 3 when the
stale leg reproduces and 2 when the tape is absent; the capture above used the
external four-year tape. No economic claim is made or implied by any artifact.
