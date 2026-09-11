# V8.7 evidence revision 2 — warmup alignment

**Status:** diagnostic reproduction. `docs/evidence/v87/` (revision 1) is **unchanged and
stays the frozen technical acceptance of record** until the unified engine–replay
acceptance lands as revision 3. Nothing in revision 1 was rewritten, re-hashed or deleted.

## The defect this revision fixes

The swing harness replayed with a **hardcoded warmup of 62 bars** (`tools/nx06_swing_baseline.py`
and `tools/nx09_fold_research.py`), while the family's pre-registration declares its
requirement in `economics/grammar.py` (`POLICY_REQUIRED_BARS`): 25 bars for
`trend-continuation-v2`, 49 for `range-breakout-48-v1`. A harness replaying a different
warmup than the policy declares is measuring a different policy.

It was found by the readiness audit's cross-check, which refused to report until the
recomputed campaign sum matched the frozen NX06 receipt — the mismatch was `1.07e-06`.

The pre-registration itself was never wrong: `SwingPolicySpec.identity()` already covers
`required_bars`, so the registry hash does not move. The **recorder** was wrong, not the
registration. Both harnesses now read `POLICY_REQUIRED_BARS[grammar_policy]`, and each
per-policy result carries `warmup_bars` + `warmup_source`.

## Artifacts reproduced under this revision

| Artifact | Revision 1 (frozen) | Revision 2 | Note |
|---|---|---|---|
| NX06 family registry | `d8aaf1e8…` | `d8aaf1e8…` | identical: the registry is the declaration |
| NX06 comparative receipt | `b51e4e53…` | `8245419…` | measurements changed, declaration did not |
| NX09 fold freeze | (r1) | `e2a3115…` | same window/plan identity, warmup recorded |
| NX09 fold results | (r1) | `0c1bd7b…` | 20 of 40 cells moved |
| NX07 statistics plan | `bf0941c7…` | `bf0941c7…` | identical |
| NX07 statistics receipt | `79acbaa9…` | `79acbaa9…` | byte-identical: this path is warmup-insensitive |

## Measured effect (never estimated)

Four-fold net return totals over the same eight fold-symbol cells:

| Policy | Revision 1 | Revision 2 | Change |
|---|---:|---:|---:|
| `cash` | +0.00000000 | +0.00000000 | — |
| `causal_trend` | **−0.00409588** | **+0.00148415** | sign flips |
| `swing_squeeze_baseline` | −0.00908619 | −0.00913624 | −5.0e-05 |
| `swing_squeeze_m1` | −0.00959523 | −0.00964529 | −5.0e-05 |
| `swing_squeeze_m2` | −0.00904338 | −0.00909343 | −5.0e-05 |

Largest single-cell move: `+1.50e-03` (FOLD_1 BTCUSDT `causal_trend`). The two policies with
the longest declared warmups move the most, which is the expected signature of this defect.

## What this changes in the reading, and what it does not

* **Changes:** the trend baseline's four-fold total is **positive** under the declared warmup
  (`+0.00148415`), so "the baseline is negative over the folds" is no longer supportable.
* **Does not change:** the swing family still loses money in **7 of 8** cells and is still
  **worse than the trend baseline in 4 of 8** (better in the other 4) — the corrected
  statement in NX09/NX11/NX00 and D-164 holds under both revisions.
* The final window is still **not opened** (`final_eligible: false`, `NO_PROTECTED_FINAL`:
  the tail is `TAIL_BURNED`). No protected final exists in either revision.

## Still missing after this revision (not zero, not filled)

* Engine fill parity for the swing family — its outcomes are decision-plane replay
  (revision 3: the engine lane).
* Funding and slippage on the swing path. The data **exists**: the tape carries a `funding`
  channel (43,905 rows over four years, `binance-um-funding-v1-ms`, 8-hour settlements with
  `funding_rate`/`funding_time_ms`) — the label `MISSING_NOT_FED_TO_THIS_PATH` means exactly
  that. Mark price is **absent**, so any mark-based markout/shortfall measurement stays
  `MISSING` (revision 3: the cost lane).
* Prospective maturity: the frozen window has not been observed.
