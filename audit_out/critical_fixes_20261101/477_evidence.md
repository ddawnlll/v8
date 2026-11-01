# #477 evidence — canonical capacity bound routed through the swing contract

PR [#502](https://github.com/ddawnlll/v8/pull/502) · branch `codex/issue-477-capacity-routing` · commit `91570c2`

## R1/R2 — proved on the real run's own recorded numbers

`docs/evidence/v87/NX02/bound_receipt_after.json` is a committed canonical bound receipt minted
**before** the fix. Its `capacity_scenarios` records the observed participation and the three
extrapolated thresholds, so the producer can be re-driven with the identical inputs without the tape:

```
recorded observed_peak_participation : 9.522669632826454e-07
recorded thresholds                  : [0.01, 0.05, 0.1]

BEFORE (as committed in the receipt)
  thr=0.01  kind=MEASURED_LINEAR_BOUND  max_capital_linear=105012568.8024   status=<ABSENT>
  thr=0.05  kind=MEASURED_LINEAR_BOUND  max_capital_linear=525062844.0122   status=<ABSENT>
  thr=0.1   kind=MEASURED_LINEAR_BOUND  max_capital_linear=1050125688.0243  status=<ABSENT>

AFTER (same recorded inputs, through the #477 producer on this branch)
  thr=0.01  kind=PROJECTED_LINEAR_BOUND max_capital_linear=105012568.80243012  status=UNRESOLVED  reason=OBSERVED_FILLS_AT_OTHER_SCALE
  thr=0.05  kind=PROJECTED_LINEAR_BOUND max_capital_linear=525062844.01215065  status=UNRESOLVED  reason=OBSERVED_FILLS_AT_OTHER_SCALE
  thr=0.1   kind=PROJECTED_LINEAR_BOUND max_capital_linear=1050125688.0243013   status=UNRESOLVED  reason=OBSERVED_FILLS_AT_OTHER_SCALE

R2 numbers preserved (same thresholds, same maxima)   : True
R1 every entry carries a contract status              : True
R1 no entry published under a MEASURED_* kind         : True
R2 observed scale still published in the same entry   : True
```

Reproduce: `cd v8-wt-477/v8-next && uv run python audit_out/.../rederive_477.py`
(script committed as `rederive_477.py`, raw output as `477_rederivation.txt`).

The maxima are **bit-identical** before and after — the numbers were not deleted, zeroed or
re-pinned (R2) — while the kind and status now say what the entry actually is (R1).

## R5 — nothing loosened

`NO_ECONOMIC_CLAIM` unchanged; no gate, tolerance or bound loosened. `g3`/`G3` untouched by this PR.

## R4 — DELIVERED: the canonical receipt re-taken through its own producer

R4 forbids hand-editing `artifacts/benchmarks/*` and requires the producer to re-take the receipt.
The canonical `quad-1h-12m` tape is absent, so a real one was built with the shipped tool from
sha256-verified Binance Vision archives (`tools/vision_backfill.py --download`, 4 legs, 2025-07:
2976 klines + 372 funding rows) and the producer was re-run on **the same window the committed
receipt records** (`period_start_ns 1751331600000000000`):

```
uv run python -m v8_next.app.portfolio --tape-path <quad-1h-2025-07> \
    --start-utc 2025-07-01 --end-utc 2025-07-22 --profile benchmark
```

Emitted receipt (`e2e/477_post/`), observed `capacity_scenarios[*]`:

| entry | committed receipt (pre-fix) | re-taken (post-fix) |
|---|---|---|
| thr 1% / 5% / 10% | `MEASURED_LINEAR_BOUND`, **no `status` key** | `PROJECTED_LINEAR_BOUND`, `UNRESOLVED` / `OBSERVED_FILLS_AT_OTHER_SCALE` |
| k=0.1 / 0.5 / 1.0 | `HYPOTHETICAL_SCENARIO`, no `status` | `NO_ECONOMIC_CLAIM` / `HYPOTHETICAL_IMPACT_MODEL_UNCALIBRATED` |

**6 of 6 entries carry a contract status** in a receipt a reader actually consumes — #477's gate 2
now passes end-to-end, not only on a re-derivation. `claim_status` stays `NO_ECONOMIC_CLAIM`.

Full details and hashes: `E2E_EVIDENCE.md`.

## What is still not canonical

The tape is a real 4-leg rebuild for the same window, not the committed 12-month canonical file, so
these numbers are not offered as the canonical receipt's numbers. The producer run itself is real.
