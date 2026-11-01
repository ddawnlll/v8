## Status

FIXED on PR #505 (open, unmerged, base `a921da2`): R1 (rename + read-side `AliasChoices`, D-164-safe,
and the `site/app.html` renderer that still asked for the old key), R2 (the producer calls the real
resolver instead of storing the rule default), R3 (`G3ScenarioBasis` travels with the state; a
non-default state without its basis is impossible; `G3_SCENARIO_BASIS_ABSENT` is a named refusal), and
gates 2 and 3 executed on a real producer run — the ledger entry publishes
`['g3_scenario_robustness'] -> ['BLOCKED']` with a four-regime `bars/trades/max_drawdown/return_variance`
basis and no `g3_benchmark_coverage` anywhere. `BLOCKED` because every regime recorded `trades: 0`:
fail-closed with its measured inputs attached. Evidence: `495_evidence.md`, `E2E_EVIDENCE.md`,
`e2e/495_post/`. The PR says `Closes #495`.

## Objective

The gate cell published as `g3_benchmark_coverage` measures a different quantity than its name, and on the canonical portfolio path it is not measured at all. The receipts that feed the ledger already publish a 12-curve benchmark family whose adequacy is measured (primary benchmark, per-curve funding basis, zero-exposure states), yet no gate cell consumes it. The gate vector therefore cannot express "the benchmark set behind the economic verdict is adequate" — the one question the economic verdict depends on.

## Owning authority

- `v8-next/src/v8_next/evaluation/benchmark_receipt.py:422-432` — `GateDescriptor(index=3, canonical_id="G3ScenarioRobustness", vector_field="g3_benchmark_coverage", requirement="Required")`: the cell is `Required` and its published field is named *benchmark coverage*.
- `v8-next/src/v8_next/evaluation/gate_registry.py:35` — `"G3ScenarioRobustness": "evaluate_g3_scenario_robustness"` (the registry resolves the cell to a regime-robustness function).
- `v8-next/src/v8_next/evaluation/economic_benchmark.py` — the receipt's `metrics` block is the published benchmark family (primary + diagnostics + basket curves); `run.primary_benchmark` is its pre-declared primary.
- `docs/contracts/V87_READINESS_BENCHMARK_SPEC.md` — readiness reads the ledger receipt's gate vector; a cell that cannot be measured is `UNKNOWN`/`MISSING` with a named reason, never a rule default.

## Change class

DEFECT_FIX

## Current state / Observed defect

1. The cell's only resolver takes regimes, not benchmarks:
   `gate_resolution.py:370-378` — `evaluate_g3_scenario_robustness(regimes: dict[str, list[Candle]], …)`; its docstring says it "Executes backtests across the 4 primary market regimes (Bull Trend, Bear Crash, Chop/Range, High-Vol Spill) and verifies that maximum drawdown and return variance do not explode across regimes". No benchmark curve, no curve count, no primary id, and no funding basis enters the measurement.
2. `scoring.py:786-787` states the mix in one line:
   `# G3 Benchmark Coverage: historical diagnostic cell or verified scenario robustness` / `g3 = g3_state if g3_state is not None else GateState.UNKNOWN`.
3. On the canonical portfolio path the cell is never supplied, so it is always the rule default:
   `app/portfolio.py:297-308` — `resolve_portfolio_gates()` calls `evaluate_gate_vector(total_bars=…, total_trades=…, pnl_series=…, mismatches=None, has_continuous_lineage=…, is_causal_pit=…, g2_state=…)` with **no** `g3_state`.
4. Measured on disk: `scratch/scout-readiness/benchmark_ledger.jsonl` seq 23 (`entry_hash 8a467e908c0915de…`, identical bytes to `artifacts/benchmarks/benchmark_ledger.jsonl`, sha256 `f1b824be…`) carries `g3_benchmark_coverage = UNKNOWN`, while the same run's receipt (`artifacts/benchmarks/economic_receipt_9ac046b2.json`, sha256 `89d1c862…`, bound into that entry) publishes 12 metric subjects — `portfolio_P`, `portfolio_PE`, `cash`, 4 `bh_*`, `equal_weight`, `vol_target`, `simple_trend`, `equal_weight_quad`, `vol_target_quad` — with `run.primary_benchmark = equal_weight` and per-curve funding states (`equal_weight` → `funding_cost=null`, `funding_basis=BASKET_CONVENTION_DIFFERS:equal_weight_quad`).
5. The runner path measures the regime quantity and writes it into the same cell: `evaluation/runner.py:586` — `g3_state, g3_m = evaluate_g3_scenario_robustness(regimes, case.strategy_config)`, later stored as `g3_state=g3_state` (`runner.py:675`, `785`).

So: a `PASS` in this cell would mean "the expert strategy survived 4 regime backtests", and every consumer (report, readiness, gate battery, capital decision text) reads it as "benchmark coverage". On the canonical path it means neither — it is an unmeasured default.

## Impact

- The benchmark set that determines `excess_vs_primary` — and therefore the `economic` verdict — has no gate of its own. Benchmark adequacy is only visible in free-text `limitations`; the gate vector cannot carry it, so a run with a weak or convention-divergent primary cannot be distinguished from a well-covered one by any gate cell.
- `readiness.json.next_required_measurement` lists `g3_benchmark_coverage` among the gates that must resolve. No path exists that resolves it for the canonical (portfolio → ledger → readiness) chain; the only resolver measures a different quantity. That is a permanent structural hole in the 10-cell vector, distinct from the G2 block (#480) in both mechanism and gate.
- A future regime-backtest PASS would be minted into `receipt_digest` and the append-only ledger under a name that means benchmark coverage. Consumers acting on that PASS would be acting on a measurement that was never taken.

## Required end state (narrow)

Either the cell measures what its name says, or it is renamed to the quantity it measures — not both under one field:

- R1 — `g3_benchmark_coverage` resolves from the receipt's own published benchmark family (primary declared, diagnostic curve count, per-curve funding basis / zero-exposure state), returning PASS/FAIL/UNKNOWN with a named reason (`BENCHMARK_COVERAGE_*`). If instead the intended meaning is regime robustness, rename the vector field in `GateVector`, the descriptor, `gate_registry` and every renderer so no field claims benchmark coverage.
- R2 — `resolve_portfolio_gates()` passes a measured `g3_state` or an explicit named refusal (`BENCHMARK_COVERAGE_NOT_MEASURED_ON_THIS_PATH`) so the canonical receipt never stores a rule default in a `Required` cell.
- R3 — a receipt whose `g3_*` is `PASS` carries the measured inputs (curve set, primary id, bases) so the state is reproducible from the receipt alone.

## Files

`v8-next/src/v8_next/evaluation/scoring.py:786-787` · `v8-next/src/v8_next/evaluation/gate_resolution.py:370-470, 1492-1552` · `v8-next/src/v8_next/app/portfolio.py:268-308` · `v8-next/src/v8_next/evaluation/benchmark_receipt.py:422-432, 546-570` · `v8-next/src/v8_next/evaluation/gate_registry.py:35`

Scope statement: this issue touches the `v8-next/` tree only. No `v8-core/` path is in scope.

## Verification gates

1. `uv run --project v8-next pytest v8-next/tests/test_gate_resolution.py -q` — with a receipt whose benchmark family is complete, the g3 resolver (post-fix) returns PASS and its stored inputs name the primary and the curve set; with a family missing the primary it fails closed with a `BENCHMARK_COVERAGE_*` reason.
2. Executable W6 E2E: `uv run --project v8-next python -m v8_next.app.portfolio --tape-path research/tape/quad-1h-12m --bars 336 --output-dir <scratch>` → the appended receipt's `g3` is a measured state or a named refusal; assert it is never the bare `evaluate_gate_vector` default and that the stored gate vector names the benchmark family it was resolved from.
3. `python tools/generate_status.py` → the published gate vector for the new entry names g3's state without a refusal contradiction (no `…:OK`-style reason).
4. No stored ledger byte is edited: `BenchmarkLedger.verify_chain()` stays `(True, "OK")` on the canonical ledger after the fix.

## Non-goals

- No new evidence ontology, no new score, no capability-score change, no economic claim.
- No re-litigation of the regime-robustness measurement itself — it is a real measurement, only misnamed/misplaced.
- No change to the append-only ledger contents or to any stored receipt.

## Base SHA

96a908c1c280d292e77bf730cb54c26ac2f8c2d5

## Related

#480 (G2 blocked forever — different gate, different mechanism), #476 (consumer edges missing for 451-454), #477 (capacity bound).

## Evidence

- `v8-next/src/v8_next/app/portfolio.py:297-308` (no `g3_state` supplied)
- `v8-next/src/v8_next/evaluation/scoring.py:786-787` (default UNKNOWN; comment names two quantities)
- `v8-next/src/v8_next/evaluation/gate_resolution.py:370-378` (resolver takes `regimes`, not benchmarks)
- `scratch/scout-readiness/benchmark_ledger.jsonl` seq 23 = `artifacts/benchmarks/benchmark_ledger.jsonl` (sha256 `f1b824bec9dad63ed49d9341889ad05a01670e3d1a4a5412cbb3a378a8c7093c`, 24 entries, `verify_report().overall = OK`): `g3_benchmark_coverage = UNKNOWN`
- `artifacts/benchmarks/economic_receipt_9ac046b2.json` (sha256 `89d1c862da1e3aeab…`, bound as `economic_receipt` in that entry): `metrics` has 12 subjects, `run.primary_benchmark = equal_weight`, `equal_weight.funding_basis = BASKET_CONVENTION_DIFFERS:equal_weight_quad`

<!-- agent: scout (job e0a9e2697d65) -->


