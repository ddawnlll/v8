# Preregistration — Experiment `v8_slice_001`

**Status:** RATIFIED — operator-approved 2026-08-01; frozen until the
holdout is opened.
**Written:** 2026-08-01 (session 2 of the autonomous build), before the frozen
holdout exists.
**Rule of this document:** it specifies a test that will or will not be run;
nothing in it claims, implies, or estimates profitability
(`V8_CONSTITUTION` rule 12). The experiment has **not been run** and the
frozen holdout has **not been opened or downloaded** as of this writing.

This record follows the hypothesis-record field list of
`HYPOTHESIS_LAB_PROTOCOL` (H1–H8 records) and the attribution-validity gate
D-027. Thresholds in section 15 were proposed from the session-2 development
baseline (O-017) and **ratified by the operator on 2026-08-01**; they are
fixed here, before the holdout — they are never re-set after seeing a
verdict.

---

## 1. Experiment identity

- `experiment_id`: `v8_slice_001`
- System version: v0.1 (Phase 0-3 foundation + Phase-1 data plane).
- Families under test: the two registered pilot families
  (`docs/EXPERTS_REGISTRY.yaml`, both `FORMALIZED`, variant `a`):
  - `trend_continuation` / `pullback_in_trend` → expert `trend_pullback` v1
  - `liquidity_vacuum_reentry` / `failed_breakout_reentry` → expert
    `failed_breakout` v1
- A family is the multiplicity unit (rule 13): both pilots are their family's
  first variant; any threshold/geometry change during the experiment would be
  a **new variant of the same family** and would count against the same
  family-level correction — none is admitted by this record.

## 2. Formal null and alternative (per family)

For each family `f` on the frozen out-of-sample window, with
`μ_f = E[net_R | executed episode, family f]` computed under the canonical
simulator:

- **H0 (null):** `μ_f ≤ 0` — after cost and funding, the family's executed
  episodes do no better than the no-trade baseline (0 net_R).
- **H1 (alternative):** `μ_f > 0` — the family's executed episodes clear cost
  after the canonical execution policy.
- The **no-trade baseline** is fixed at 0 net_R (R-multiples, never percent
  returns). No direction-scrambled or shuffled control is a substitute for the
  frozen holdout; the directional control is reported as a secondary diagnostic
  only (below).
- The oracle statistic `E[max(U_long, U_short, 0)]` is **forbidden** as
  evidence (HYPOTHESIS_LAB_PROTOCOL): direction is fixed by the frozen expert
  definitions, never chosen after the outcome.

## 3. Economic mechanism

- `trend_continuation` (pullback-in-trend): after an established uptrend
  (`ema_fast > ema_slow`), a pullback that takes the close below `ema_slow` is
  hypothesized to be a continuation entry — a mean-reversion-within-trend
  claim. **Mechanism claimed; no evidence asserted.**
- `liquidity_vacuum_reentry` (failed breakout): a close back below the prior
  high after an excursion above it is hypothesized to be a liquidity-vacuum
  reentry short — an order-flow/mechanical claim. **Mechanism claimed; no
  evidence asserted.**
- Both are deterministic, falsifiable, and add no learned component (rule 14).

## 4. Behavior and deterministic detection rule

Fixed, frozen definitions (they already exist in code; they are the
`setup_anchor_event_id`-anchored detectors of D-026):

- `trend_pullback`: on closed 1h bars, setup predicate
  `ema_fast > ema_slow AND close < ema_slow`, with numeric parameters
  `ema_fast = EMA(5)`, `ema_slow = EMA(20)`; LONG entry at next-bar close;
  anchor = first bar of the current consecutive run of the predicate
  (episode identity, never the decision clock).
- `failed_breakout`: setup predicate `close < prior_high` (per-bar prior high
  within the 32-bar window); SHORT entry at next-bar close.
- **Parameter provenance:** all detector parameters (EMA 5/20, prior-high
  window 32, ATR 14) and the geometry were fixed in frozen code
  (`src/v8/`, session-1 steps 1-2, built against synthetic tapes) **before the
  real-data development window existed**. The dev window was used only for
  pipeline correctness and O-017 threshold calibration — never for parameter
  selection. No development search log exists because no development search
  was performed; there are no undisclosed variants.
- Post-entry thesis (`still_valid`): trend-pullback stays valid while
  `ema_fast > ema_slow`; failed-breakout stays valid while
  `close < prior_high`. A dead thesis closes at bar close
  (`THESIS_INVALIDATED`), a distinct exit from STOP.
- Deduplication: `episode_key` anchored to `setup_anchor_event_id`
  (D-026); repeats log `SUPPRESSED_DUPLICATE` and are never a second episode.

## 5. Universe as-of membership

- **Single instrument:** BTCUSDT USDT-M perpetual (O-011: the locked
  universe is not extended; venue extension happens only on a binding
  coverage failure of this tape).
- As-of membership: BTCUSDT is listed continuously across the whole window;
  no delisting/survivorship adjustment is required for a single live
  instrument. If the instrument is delisted before the experiment runs, the
  experiment is **cancelled** (a universe change is a new preregistration).
- Interval: 1h bars, UTC.

## 6. Data and source manifest

- Source: Binance Vision monthly klines archive
  (`data.binance.vision/data/futures/um/monthly/klines/BTCUSDT/1h/`),
  downloaded and SHA-256-verified by `tools/data.py`; converted to the JSONL
  PIT tape by `tools/vision_backfill.py` (three clocks, `schema_version`
  `binance-um-v1-ms`, `event_id` = kline open time).
- Development tape hash: the session-2 3-month tape was
  `8b12707e0d89f2a955d2badccf9f278267c0e086` (2,184 rows, 2026-04-01..
  2026-07-01); the D-041 12-month dev tape is `4c8e58885b88b903b54bcdffa093af336cef8d1c`
  (8,760 klines + 1,188 funding rows = 9,948 rows, 2025-07-01..2026-07-01,
  incl. the `2026-07` funding coverage horizon). The frozen-holdout tape hash
  is recorded **at download time, before any evaluation**, and appended to
  this record's operator approval (never silently).
- Development manifest (pinned input, D-041): `experiment_id
  v8-dev-12m-btcusdt`, `code_hash ea8db9e2a7d3204f215bab48893fba0556e427ca`,
  `data_hash 4c8e58885b88b903b54bcdffa093af336cef8d1c`. Derived run outputs
  (not input fields) are recorded in
  `research/tape/btcusdt-1h-12m/views/views_manifest.json`: ledger_hash
  `c78bf43a8c600520808690309f9385f5a290f4f3`, verdict `NO_ECONOMIC_CLAIM`,
  and materialized view row counts: market_states 8760, candidate_birth 2786,
  candidate_trigger 2779, candidate_outcomes 2786, execution_trajectories
  11684.
- `tools/data.py` / `tools/vision_backfill.py` / `tools/materialize_views.py`
  versions are bound by the recursive `src/v8/` code hash at run time;
  materializations fail closed on any pinned-hash mismatch (compile-once).

## 7. Decision / knowledge / availability clocks

- `event_time` = kline close time (integer ns; source ms normalized).
- `available_time` = `event_time + 1s` configured feed latency
  (FEED_INGESTION_SPEC §3).
- `ingested_time` = `available_time` (offline backfill; never a proxy for
  availability).
- `knowledge_time` = the decision clock `D` = `available_time` of the bar
  being decided. Every ExpertEvaluation/CandidateTransition records it.
- No wall clock anywhere in the decision path; `sha1_hex` for every hash
  (PERSISTENCE_REPLAY_SPEC §4).

## 8. Canonical geometry and costs (frozen)

- Execution: canonical simulator v4 (`canonical-sim-v4`), fill policy
  `FILL_AT_BAR_CLOSE`, entry at next-bar close, entry bar never inspected for
  exits, STOP_FIRST on same-bar ambiguity, gap semantics on stops (worse of
  barrier and bar open).
- Geometry (both pilots): `target_r = 1.0`, `stop_r = 1.0`,
  `expiry_bars = 8`; one R = the expert's declared `atr_ref` (14-bar ATR).
- Costs: `round_trip_cost_r = 0.07`, **locked for this experiment** (the
  provisional `binance_usdm_costs_v1` figure is frozen here; it is not
  revisable after a verdict — any revision is a new preregistration).
- Funding: **tape-driven settlement (D-041)** — the schedule is read from the
  tape's `funding` channel (Vision monthly fundingRate archives, SHA-256
  verified); every crossed boundary settles
  `funding_settled_r = entry_price × rate / risk_unit` (DATASET_SPEC §6.4).
  `funding_hours = 8` retained as the schedule grid; the `funding_rate_r`
  scalar remains only as a no-funding-tape fallback. The D-024 mask vetoes
  entries within 1 bar of a funding boundary regardless of rate, per the
  locked baseline.
- D-024 mechanical tradability mask (data-plane, frozen): `max_spread_frac =
  0.05`, `funding_window_bars = 1`; vetoed candidates are kept
  counterfactual (`NOT_EXECUTED`) with reason `TRADABILITY_MASK_VETO`.

## 9. Dependence unit

- The **episode** (`episode_key`, setup-anchored) is the unit, not the trade
  and not the bar.
- Uncertainty is estimated with a **block bootstrap** on episodes
  (HYPOTHESIS_LAB_PROTOCOL). The block size is a fixed mechanical rule: 24
  episode-blocks (one day) by default; if the estimated lag-1 autocorrelation
  of episode `net_R` in the frozen OOS sample exceeds 0.10 in magnitude, the
  block size is 168 (one week). The rule is fixed here and applied
  mechanically — it is not a free parameter. Naive trade-level t statistics
  are not reported as the headline interval.
- Single instrument: no cross-asset clustering is required; episode overlap
  within the instrument is handled by the block resampling.

## 10. Primary metric

Per family `f`, on the frozen OOS window:

- **Primary:** mean after-cost `net_R` per executed episode,
  `μ̂_f = (1/n_f) Σ net_R`. `net_R` is the R-multiple from the canonical
  simulator (never a fractional price return).
- **Secondary (diagnostics, not gates):** executed-episode count `n_f`;
  endpoint distribution (TARGET/STOP/EXPIRY/THESIS_INVALIDATED); mean
  `MAE_R`/`MFE_R`; direction-scrambled control mean; and the
  `execution_share` + divergence statistics of section 15.

## 11. Test

- Per family: one-sided test `H1: μ_f > 0` at the **family-corrected** level
  `α_f = 0.025` (Bonferroni 0.05/2 across the two families on the primary
  metric — the only error-rate procedure; no alternative is left open).
  Bootstrap CI is the **percentile method, one-sided**: the lower bound is
  the 2.5th percentile of the block-bootstrap distribution of `μ̂_f` under
  the section-9 rule; the family passes if that lower bound exceeds 0
  **and** `n_f ≥` the minimum coverage of section 12.
- **Family-level control:** all variants explored inside a family (none so
  far beyond `variant a`) count as one multiplicity unit (rule 13).
- Attribution gate (D-027) is evaluated first: if
  `ATTRIBUTION_UNSAFE_LOW_COVERAGE` or
  `ATTRIBUTION_UNSAFE_POPULATION_DIVERGENCE` fires (section 15), the run is
  **not** scored for the primary metric — it is reported as attribution-unsafe
  and the correct responses are to widen capacity / narrow the universe /
  reduce expert overlap, never to reinterpret the counterfactual population
  as a traded one.

## 12. Minimum event / asset coverage

- **Minimum executed episodes per family:** `n_f ≥ 30`. Below that the family
  is `insufficient-event` (blocks the family-level conclusion; it is not a
  failure of the hypothesis — HYPOTHESIS_LAB_PROTOCOL).
- **Minimum window coverage:** the frozen OOS window spans at least 2
  calendar months (≥ 1,400 1h bars) so that episode counts and the block
  bootstrap have material support.
- **Minimum asset coverage:** 1 instrument (BTCUSDT) per the locked universe;
  a single-instrument result is a statement about that instrument's window,
  never a market-wide claim.

## 13. Development / frozen partitions (chronological)

- **Development window (D-041):** `2025-07-01 00:00 UTC` .. `2026-07-01 00:00
  UTC` — 12 months (BTCUSDT 1h; tape hash `4c8e5888…`).
  Used only for pipeline correctness and for the section-15 diagnostics (the
  O-017 thresholds were ratified pre-holdout and are **fixed forever** — an
  updated dev baseline never re-sets them). It is **not** the test window and
  contributes nothing to the primary metric. The dev tape also carries a
  declared **funding coverage horizon**: funding rows for `2026-07` so
  positions entered in the final dev bars settle across the 2026-07-01
  boundary (mirrors the 9-bar label extension; funding rows never enter
  features or the decision loop).
- **Frozen out-of-sample window (declared, never touched):** the **first two
  published months strictly after** `2026-07-01 00:00 UTC` (≥ 1,400 1h bars,
  satisfying section 12; `2026-07` was not yet published on 2026-08-01, so at
  experiment time the holdout is the earliest two consecutive monthly Vision
  archives available). Its tape is downloaded **only at experiment time**, by
  the frozen manifest, checksum-verified, and hashed **before any
  evaluation**. Until the operator approves this record, the holdout does not
  exist.
- **Label-horizon at the holdout end:** episodes anchored in the final bars of
  the window realize their outcome up to `expiry_bars = 8` bars later. The
  holdout tape is therefore extended by the **9 bars** needed to complete
  every window-anchored episode (8-bar expiry + 1 entry bar); the extension is
  fetched with the holdout, is part of the frozen holdout, and is hashed
  before any evaluation. Any episode whose outcome still cannot be observed
  because the extension is unavailable is `RIGHT_CENSORED` — never excluded
  silently and never given a fabricated outcome.
- No development observation may be purged/embargoed into the holdout; splits
  are chronological with no overlap and no label-horizon bleeding between
  development and holdout.

## 14. Rejection consequence

- If **neither** family passes its preregistered test on the frozen OOS, the
  falsification program stops here: gated components (scorer, ranker, router,
  learned execution) are **never built** without a surviving family (rule 12),
  and the status of both families is recorded as failed/rejected for this
  window (not a universal statement).
- If a family passes, the next step is **replication** on additional
  chronological slices (untouched) before any promotion; `PROMOTED` requires
  replication (EXPERT_PROTOCOL §4). A `PASS` is a statement about the
  preregistered gate, never universal validity.
- Any `ATTRIBUTION_UNSAFE_*` verdict is **not** a failed hypothesis and is
  never reported as one.

## 15. Attribution-validity thresholds (O-017, operator-ratified 2026-08-01, set pre-holdout)

Derived from the session-2 development baseline (never from a holdout
verdict), per D-027 and O-017. On the dev window (2026-04..06, BTCUSDT 1h,
both pilots, locked baseline): `n_executed = 256`,
`n_portfolio_rejected = 360` (all `EXISTING_EXPOSURE_CONFLICT`;
`PORTFOLIO_HEAT_EXCEEDED = 0`), so
`execution_share = 256/(256+360) = 0.4156`. The executed vs
portfolio-rejected `net_R` samples (n=256/360) had means `+0.0519/+0.0184`,
std `0.8906/0.9415`, and a **two-sample Kolmogorov-Smirnov statistic of
0.073**.

The session-2 stats above are the O-017 calibration record (how the ratified
thresholds were derived). After the D-041 12-month rebuild, the updated
dev-window diagnostics are recorded in this section **as diagnostics only** —
they never re-set the ratified thresholds, which are fixed pre-holdout
(O-017).

On the D-041 12-month dev window (2025-07-01..2026-07-01, BTCUSDT 1h, both
pilots, locked baseline): `n_executed = 1,111` (outcome `label_status` !=
`NOT_EXECUTED`), `n_portfolio_rejected = 1,317` (all
`EXISTING_EXPOSURE_CONFLICT`; `PORTFOLIO_HEAT_EXCEEDED = 0`), so
`execution_share = 1111/(1111+1317) = 0.4576`. The executed vs
portfolio-rejected `net_R` samples (n=1111/1317) had means `−0.0514/+0.0477`,
std `0.8834/0.9135`, and a **two-sample KS statistic of 0.1044**. Both sit
inside the ratified bounds (share 0.4576 ≥ 0.25; KS 0.1044 ≤ 0.20) —
informational only; never a verdict and never a threshold re-set. These
numbers are produced by the lab's own D-027 computation
(`LabReport.execution_share` / `divergence_ks`, `src/v8/lab.py`).

- **`execution_share` floor:** **0.25** — 60% of the observed dev-window
  share. A frozen-OOS run with `execution_share < 0.25` returns
  `ATTRIBUTION_UNSAFE_LOW_COVERAGE`. The floor is low enough not to trip a
  healthy single-instrument run yet high enough that a run whose population is
  overwhelmingly counterfactual cannot produce an economic verdict.
- **Population-divergence threshold:** **two-sample KS on `net_R`
  (executed vs portfolio-rejected) ≤ 0.20**. A frozen-OOS run with
  `KS > 0.20` returns `ATTRIBUTION_UNSAFE_POPULATION_DIVERGENCE`. The
  threshold sits ~2.7× the observed dev-window divergence (0.073), catching
  material population drift while tolerating the small baseline gap.
- Both statistics are computed **only on portfolio-state rejections**
  (`EXISTING_EXPOSURE_CONFLICT`, `PORTFOLIO_HEAT_EXCEEDED`); cost gates,
  invalidation, expiry, and the data-plane mask veto (D-024) are rejections
  that express the strategy itself — D-027's principle — not selection bias,
  and are excluded from the denominator.
- Verdict rules (D-027): low coverage → `ATTRIBUTION_UNSAFE_LOW_COVERAGE`;
  divergence → `ATTRIBUTION_UNSAFE_POPULATION_DIVERGENCE`; both within bounds
  AND the authority receipt present → an economic verdict is permitted. No
  authority receipt exists; the economic verdict of any run stays
  `NO_ECONOMIC_CLAIM` (rules 8–9).

## 16. Governance

- This record is **operator-approved** (ratified 2026-08-01). No field may be
  changed after the frozen holdout is opened. Any material change requires a
  new preregistration and a fresh untouched holdout.
- Operator actions at experiment time: (a) ~~ratify the O-017 thresholds of
  section 15~~ **DONE 2026-08-01** — `execution_share` floor 0.25, KS
  threshold 0.20 approved; (b) record the frozen-holdout tape hash before any
  evaluation; (c) provide an authority receipt before any economic verdict.
- The experiment itself (`tools/`-driven run of `v8_slice_001`) is **not**
  executed by this session and the frozen holdout is not opened.
