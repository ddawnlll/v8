# #495 evidence — G3 cell named for what it measures, with its basis attached

PR [#505](https://github.com/ddawnlll/v8/pull/505) · branch `codex/issue-495-g3-cell-honesty`
Two commits: `34f00b7` (rename + producer wiring) and `afe664c` (R3 basis).

## R1 (rename branch) — delivered by `34f00b7`

`g3_benchmark_coverage` → `g3_scenario_robustness` on every surface: `GateVector` field,
`vector_field` descriptor in `benchmark_receipt.py`, `scoring.py`'s `evaluate_gate_vector` keyword,
the `gate_resolution.py` docstring, `app/portfolio.py`, and the five test files that assert on the name.

Stored ledgers stay readable, unchanged on disk:

```python
g3_scenario_robustness: GateState = Field(
    default=GateState.MISSING,
    validation_alias=AliasChoices("g3_scenario_robustness", "g3_benchmark_coverage"),
)
```

`tests/fixtures/ledger_canon/*.json` still contain the old key and were **not** edited (D-164 forbids
editing stored ledger bytes). G3's `DIAGNOSTIC` registry role is unchanged, so a PASS still mints no
authority.

## R2 — delivered by `34f00b7`

`resolve_portfolio_gates` now calls the only resolver that exists for G3
(`app/portfolio.py:311` → `evaluate_g3_scenario_robustness(regimes)`), so the canonical receipt no
longer stores the rule default in a `Required` cell, and an unmeasurable partition fails closed with a
named reason.

## R3 — delivered by `afe664c`

The auditor's objection was exact: `app/portfolio.py:311` discarded the resolver's metrics
(`g3_state, _g3_metrics = ...`), so a PASS receipt carried no regime basis.

Now the state and its basis travel together:

- `G3ScenarioBasis` (in `benchmark_receipt.py`) carries `state`, the `regimes` mapping of
  `G3RegimeMeasurement(bars, trades, max_drawdown, return_variance)`, `evaluated_regimes`, the named
  `reason`, and the thresholds that decided it. Its validator `_state_and_basis_travel_together`
  refuses a non-default state with no basis.
- Named absence instead of an empty mapping: `G3_SCENARIO_BASIS_ABSENT`. An empty dict would read as
  "measured nothing"; the named absence reads as "not measured".
- Published as `BenchmarkReceipt.g3_scenario_robustness_basis`, **beside** the digest canons rather
  than inside them, so no stored digest changes.
- `resolve_portfolio_gates(..., include_g3_basis=True)` returns `(vector, basis)`; the default call
  still returns the vector alone, so the existing producer contract is not broken.

## Verification, both directions

| check | result |
|---|---|
| R1's new test on clean `main@a921da2` | 2 failed — `AttributeError: 'GateVector' object has no attribute 'g3_scenario_robustness'` |
| R1's new tests on branch | 2 passed |
| R3's new test on the **previous tip** `34f00b7` (detached checkout, test copied in) | **1 failed** — `ImportError: cannot import name 'G3_SCENARIO_BASIS_ABSENT'` |
| R3's new test on branch tip `afe664c` | passes |
| full suite on `afe664c` | **1009 passed, 9 skipped, 497 deselected** (baseline 1007/9) |
| `ruff check src tests` | All checks passed! |

Test name: `tests/test_portfolio_gate_vector_471.py::test_portfolio_receipt_carries_the_g3_basis_that_reproduces_its_state`

## Note on the G5 false alarm

An earlier orchestrator run reported `test_g5_selection_control_dsr_and_wrc` failing on this branch
(`BLOCKED` where `PASS` expected). **Not reproducible** — the test passes alone, in its file, and in
the exact two-file pairing that "failed", twice in a row. Cause: I ran pytest inside the agent's live
worktree while it was running `uv sync` there. Retracted to the agent and recorded here so the false
alarm is not mistaken for a fixed bug.

## Gates 2 and 3 — DELIVERED on a real producer run

A real 4-leg tape was built with the shipped tool from sha256-verified Binance Vision archives
(BTC/ETH/SOL/AVAX 1h, 2025-07) and the canonical producer was run on it. The emitted ledger entry
(`e2e/495_post/benchmark_ledger.jsonl`, sha256 `797b3202…`):

- gate keys: `['g3_scenario_robustness']` → `['BLOCKED']`
- `g3_benchmark_coverage` anywhere in the entry: **False**
- `g3_scenario_robustness_basis` present: **True** — state `BLOCKED`, regimes
  `['Bear Crash', 'Bull Trend', 'Chop/Range', 'High-Vol Spill']`, each carrying
  `bars / trades / max_drawdown / return_variance`

`BLOCKED` rather than `PASS` because every regime recorded `trades: 0` — the resolver fails closed.
That is exactly what R3 asks for: the measured inputs travel with the published state, so the verdict
is reproducible from the receipt alone.

## Dashboard renderer (the rename's last surface)

`494fcbc`: `site/app.html` still asked for `g3_benchmark_coverage`, so after the rename the cell would
have rendered `UNKNOWN` on a receipt that measured it — the same silent-default failure the issue
exists to remove, moved into a renderer. It now reads `g3_scenario_robustness` and keeps the old key
only as a fallback for immutable stored ledgers (D-164).
`tests/test_dashboard_gate_keys_495.py` fails on both counts against the previous commit and passes now.
