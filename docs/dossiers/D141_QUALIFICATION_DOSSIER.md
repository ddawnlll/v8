# D-141 Qualification Dossier

**Decision:** D-141 Expert Proving Ground & Alpha Refinery
**Scope:** deterministic semantic qualification only
**Economic authority:** `NO_ECONOMIC_CLAIM`

## Test-only evidence boundary

D-141 semantic scenarios are Rust `#[cfg(test)]` fixtures. The production CLI has no `qualify-experts` command and no D-141 synthetic receipt writer: this prevents generated worlds from entering runtime evaluation or report artifacts. The authoritative verification is the scoped Rust test output bound to the reviewed code revision; it contains no profit, return, or promotion assertion.

## Pilot result contract

| Expert | Formal manifest | Semantic verdict | Economic verdict |
|---|---|---|---|
| `failed_breakout:v1` | D-141 manifest hash in test evidence | `SEMANTICALLY_QUALIFIED` only if EWQ-01…06 pass | `NO_ECONOMIC_CLAIM` |
| `fib_projection_reversal:v1` | D-141 manifest hash in test evidence | `SEMANTICALLY_QUALIFIED` only if EWQ-01…06 pass | `NO_ECONOMIC_CLAIM` |
| `liquidity_sweep_reclaim:v1` | D-141 manifest hash in test evidence | `SEMANTICALLY_QUALIFIED` only if EWQ-01…06 pass | `NO_ECONOMIC_CLAIM` |
| `trend_pullback:v1` | D-141 manifest hash in test evidence | `SEMANTICALLY_QUALIFIED` only if EWQ-01…06 pass | `NO_ECONOMIC_CLAIM` |
| `trend_pullback_depth:v1` | D-141 manifest hash in test evidence | `SEMANTICALLY_QUALIFIED` only if EWQ-01…06 pass | `NO_ECONOMIC_CLAIM` |
| `donchian_breakout:v1` | D-141 manifest hash in test evidence | `SEMANTICALLY_QUALIFIED` only if EWQ-01…06 pass | `NO_ECONOMIC_CLAIM` |
| `volume_confirmed_breakout:v1` | D-141 manifest hash in test evidence | `SEMANTICALLY_QUALIFIED` only if EWQ-01…06 pass | `NO_ECONOMIC_CLAIM` |
| `range_breakout_1to1:v1` | D-141 manifest hash in test evidence | `SEMANTICALLY_QUALIFIED` only if EWQ-01…06 pass | `NO_ECONOMIC_CLAIM` |
| `floor_trader_pivot:v1` | D-141 manifest hash in test evidence | `SEMANTICALLY_QUALIFIED` only if EWQ-01…06 pass | `NO_ECONOMIC_CLAIM` |
| `fib_retracement_continuation:v1` | D-141 manifest hash in test evidence | `SEMANTICALLY_QUALIFIED` only if EWQ-01…06 pass | `NO_ECONOMIC_CLAIM` |
| `obv_adl_regime:v1` | D-141 manifest hash in test evidence | `SEMANTICALLY_QUALIFIED` only if EWQ-01…06 pass | `NO_ECONOMIC_CLAIM` |
| `funding_crowding_reversal:v1` | D-141 manifest hash in test evidence | `SEMANTICALLY_QUALIFIED` only if EWQ-01…06 pass | `NO_ECONOMIC_CLAIM` |
| `open_interest_divergence:v1` | D-141 manifest hash in test evidence | `SEMANTICALLY_QUALIFIED` only if EWQ-01…06 pass | `NO_ECONOMIC_CLAIM` |
| `candlestick_reversal:v1` | D-141 manifest hash in test evidence | `SEMANTICALLY_QUALIFIED` only if EWQ-01…06 pass | `NO_ECONOMIC_CLAIM` |
| `volume_climax_reversal:v2` | D-141 manifest hash in test evidence | `SEMANTICALLY_QUALIFIED` only if EWQ-01…06 pass | `NO_ECONOMIC_CLAIM` |
| `gap_exhaustion:v1` | D-141 manifest hash in test evidence | `SEMANTICALLY_QUALIFIED` only if EWQ-01…06 pass | `NO_ECONOMIC_CLAIM` |
| `bollinger_reversion:v1` | D-141 manifest hash in test evidence | `SEMANTICALLY_QUALIFIED` only if EWQ-01…06 pass | `NO_ECONOMIC_CLAIM` |
| `bollinger_breakout:v1` | D-141 manifest hash in test evidence | `SEMANTICALLY_QUALIFIED` only if EWQ-01…06 pass | `NO_ECONOMIC_CLAIM` |
| `failed_breakout_2b:v1` | D-141 manifest hash in test evidence | `SEMANTICALLY_QUALIFIED` only if EWQ-01…06 pass | `NO_ECONOMIC_CLAIM` |
| `breakout_retest:v1` | D-141 manifest hash in test evidence | `SEMANTICALLY_QUALIFIED` only if EWQ-01…06 pass | `NO_ECONOMIC_CLAIM` |
| `macd_stoch_trend:v1` | D-141 manifest hash in test evidence | `SEMANTICALLY_QUALIFIED` only if EWQ-01…06 pass | `NO_ECONOMIC_CLAIM` |

The other registered generator-experts are intentionally not counted as passed or failed until they receive their own Behavior Card and manifest. The denominator is 28, not 29: `predicate` is a post-entry thesis evaluator rather than an Expert witness. Registry manifest coverage is reported separately from the executed-test pass rate.

## Gate interpretation

- EWQ-01…06 are semantic qualification gates. A failed canonical, metamorphic, or critical mutation control falsifies qualification.
- EWQ-07 (sealed challenge) and EWQ-08 (statistical no-regression) remain `UNRESOLVED` in the pilot receipt.
- EWQ-09 (real-tape attribution) is `NOT_APPLICABLE` in this synthetic semantic run.
- EWQ-10 (frozen economic OOS) is `BLOCKED`; D-141 rejects absent authority rather than opening substitute data.

## Issue-to-receipt traceability

| Issue | Implementation surface | Verification / receipt |
|---|---|---|
| #285–#287 | manifests, scenarios, runner | manifest/run/scenario hashes |
| #288–#291 | metamorphic, mutation, generator, EAST | relation, kill, coverage, counterexample receipts |
| #292–#294 | statistics, risk, passport | typed non-economic evidence and gate map |
| #295–#297 | attribution, interaction, migration | optional diagnostic fields and unscored legacy strength |
| #298–#300 | EWQ gates, self-qualification, frozen guard | explicit pass/fail/unresolved/blocked state |
| #301 | monographs and this dossier | regenerated EN/TR monographs |

No D-141 receipt is evidence of live profitability, realized cashflow, or promotion eligibility.
