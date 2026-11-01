## Status

PARTIAL on PR #502 (open, unmerged, base `a921da2`). R1 (the swing-capacity contract is imported by the
canonical path at `app/portfolio.py:209`, so an extrapolated bound can no longer publish `MEASURED_*`),
R2 (maxima bit-identical), R3, R5 and gate 2 for **every** published entry are delivered and verified
end-to-end on a real producer run: 6 of 6 `capacity_scenarios` entries carry a contract status
(`PROJECTED_LINEAR_BOUND`/`UNRESOLVED` x3, `HYPOTHETICAL_SCENARIO`/`NO_ECONOMIC_CLAIM` x3), where the
committed receipt had `MEASURED_LINEAR_BOUND` with no `status` at all. R4 is not fully satisfied: the
canonical 12-month `quad-1h-12m` tape is absent, so the receipt was re-taken from a real 4-leg rebuild
of the same window, not from the committed canonical artifact. Evidence: `477_evidence.md`,
`E2E_EVIDENCE.md`, `e2e/477_post/`. The PR says `Refs #477 — do not close on merge`.

---

Objective: The canonical economic path must not publish a capacity bound as *measured* at a participation scale the run never observed, while the contract landed in the immediately preceding commit defines exactly that case as `UNRESOLVED`. Today the only capacity producer wired into the canonical portfolio run is never routed through the swing-capacity contract that same commit built, so the published block carries an unqualified `MEASURED_LINEAR_BOUND` for thresholds 10^3-10^5x beyond the observed participation.

Authority:
- `docs/evidence/archive/l2/README.md` (landed by `e971daf8`, "Archived L2 evidence", 2026-09-12) — the active capacity contract: "observed participation and implementation shortfall only; `DATA_BLOCKED` when real fills or the ADV basis are absent; **`UNRESOLVED` for participation scales outside observed fills**".
- `docs/contracts/V87_READINESS_BENCHMARK_SPEC.md` §§4/10 (same commit) — "The primary swing contract does not require L2/depth or queue data"; §10 forbids "L2/depth data as an implicit requirement of the primary hourly swing benchmark" and "Filling a missing pillar, gate or measurement with zero to make the score move".
- `v8-next/src/v8_next/evaluation/capacity.py` (same commit) — `SwingCapacityObservation` / `measure_swing_capacity`, whose published `status` vocabulary is exactly `DATA_BLOCKED | UNRESOLVED | NO_ECONOMIC_CLAIM` (`:110`, `:155`, `:179`, `:193`, `:223`).
- `NO_ECONOMIC_CLAIM` / honest-reporting rule: a number may be published only as what its own evidence supports.

Change class: DEFECT_FIX (producer state/claim only; no return column moves, no bound is loosened).

Current (read-only this tick; HEAD `72469acca1cbd28d4caf455fe4d66e73610748eb`; no engine run, no artifact written, no repo file modified):

1. The canonical portfolio path builds its capacity block in `v8-next/src/v8_next/app/portfolio.py:187-227` `capacity_from_participation`: for `threshold in (0.01, 0.05, 0.10)` it publishes `max_cap = capital * threshold / peak` under `"kind": "MEASURED_LINEAR_BOUND"` (`:211`) with `"basis": "LINEAR_EXTRAPOLATION_OF_MEASURED_PARTICIPATION"` (`:215`). There is no `status` field and no `UNRESOLVED`/`DATA_BLOCKED` branch anywhere in the function.
2. The bound receipt the canonical ledger currently holds, `artifacts/benchmarks/economic_receipt_9dcc92b9.json` (bound by ledger seq 21, `entry_hash 210f7a0b4bd2dc83…`, case `BC-QUAD-PORTFOLIO-01`, policy `pol_portfolio_quad`, 336 bars, `capital: 10000.0`), publishes:
   `observed_peak_participation = 9.99224484403338e-07` with `max_capital_linear = 100077611.74878787` (1 %), `500388058.74393934` (5 %), `1000776117.4878787` (10 %) — i.e. a "measured" linear bound 10^3-10^5x outside the participation the run actually observed (the worst leg participates at ~1e-6 of ADV), and with no state naming it unresolved.
3. The commit that defined the contract left the producer untouched: `git show e971daf8 --stat` lists `docs/contracts/V87_READINESS_BENCHMARK_SPEC.md`, `docs/evidence/archive/l2/README.md`, `v8-next/src/v8_next/evaluation/capacity.py`, `v8-next/src/v8_next/evaluation/economic_benchmark.py`, `v8-next/tests/test_capacity.py`, `v8-next/tests/test_economic_benchmark.py` — and *not* `v8-next/src/v8_next/app/portfolio.py`.
4. The new estimator has no consumer in `src`: `grep -rn "measure_swing_capacity" v8-next` matches only `evaluation/capacity.py:65,149` and `tests/test_capacity.py:10,48,57`. So the contract's own vocabulary exists but never reaches the surface the canonical run publishes.
5. Nothing downstream can flag the block either: `grep -n "capacity" v8-next/src/v8_next/evaluation/report.py v8-next/src/v8_next/app/readiness.py` returns 0 hits, so the capacity block is published in the receipt and consumed by no final surface (the missing consumer edge is a separate, already-owned gap — see Non-goals; this card is only about the claim the producer mints).

Impact / which decision this unblocks: capacity is the number a reader uses to decide how much capital the policy can carry before its own fills move the market, and today the only producer on the canonical path answers that question with a linear multiple of a 1e-6 participation reading while the contract written one commit earlier says that scale is `UNRESOLVED`. Either the number is a modelled projection (and must say so, with the observed scale beside it) or it is unmeasured (and must be `UNRESOLVED`) — as published, a consumer cannot tell, and the same block already stores the caveat (`impact_beyond: UNVERIFIED_NO_IMPACT_MODEL`) in a field no rule binds.

Target (measurable acceptance):
- R1 — Every entry `capacity_from_participation` publishes carries a `status` from the committed contract vocabulary (`DATA_BLOCKED | UNRESOLVED | NO_ECONOMIC_CLAIM`); an entry whose `participation_threshold` lies outside the observed fill/participation scale is `UNRESOLVED` and is not published under a `MEASURED_*` kind. The observed scale stays published in the same entry (no number is hidden).
- R2 — The threshold entries keep their numbers and their extrapolation identity (they are not deleted, zeroed or re-pinned); a `MEASURED_*` kind may survive only for a threshold the run actually observed, otherwise the kind names the projection it is.
- R3 — `v8-next/tests/test_portfolio_benchmark.py:128-135` (which currently asserts `max_capital_linear == pytest.approx(10000.0 * 0.01 / 2e-6)` with no state) is extended, not weakened, to assert the state beside the preserved number.
- R4 — The canonical bound receipt is re-taken through its own producer (`uv run --project v8-next python -m v8_next.app.portfolio …`, never by hand-editing `artifacts/benchmarks/*`), so the ledger entry that `tools/generate_status.py` reads publishes the new state.
- R5 — No gate, tolerance or bound is loosened and no economic claim is minted; NO_ECONOMIC_CLAIM is unchanged.

Files (scope: **v8-next** tree only):
- `v8-next/src/v8_next/app/portfolio.py` (`capacity_from_participation` `:187-227`, call site `:924`)
- `v8-next/src/v8_next/evaluation/capacity.py` (reuse `measure_swing_capacity` / its status vocabulary; do not create a second ontology)
- `v8-next/tests/test_portfolio_benchmark.py` (extend), `v8-next/tests/test_capacity.py` (extend)
- Artifact `artifacts/benchmarks/economic_receipt_9dcc92b9.json` + `artifacts/benchmarks/benchmark_ledger.jsonl` seq 21 are evidence to regenerate, never hand-edited.
- No `v8-core/`, no `src/v8/`, no `tests/` (frozen oracle) change.

Verification gates (minimal discriminating):
1. Mechanics: for the receipt's own reading (`peak = 9.99224484403338e-07`, `capital = 10000.0`), the published threshold entries are `UNRESOLVED` (or `DATA_BLOCKED` where the contract's fill basis is absent) — this fails on today's producer, which returns `MEASURED_LINEAR_BOUND` at 1.0e8.
2. Bound-artifact decision assertion: from `artifacts/benchmarks/economic_receipt_9dcc92b9.json` alone, every `capacity_scenarios[*]` entry's `status` is a member of the contract vocabulary, and no entry whose `participation_threshold / observed_peak_participation > 1e3` is `MEASURED_*`.
3. E2E (W6): producer → consumer → final surface — regenerate the canonical receipt with `uv run --project v8-next python -m v8_next.app.portfolio --tape-path research/tape/quad-1h-12m --bars 336 --output-dir <tmp>` and report the observed `capacity_scenarios[*].status` field in the emitted receipt (state the observed value; do not claim TRUE/FALSE without it).
4. `uv run --project v8-next --extra dev pytest -q v8-next/tests/test_portfolio_benchmark.py v8-next/tests/test_capacity.py`, `ruff check`, `mypy` on the touched files.

Non-goals / forbidden scope: no L2/depth or queue data may be re-introduced as the primary capacity basis (e971daf8 retired it); no market-impact model, no calibration, no capital authorization, no capital/`capital_linear` limit may be raised or "fixed" toward a nicer number; no change to any return, cost, or verdict column; no new module or parallel state vocabulary; the missing *consumer* edge from the receipt's capacity block to the final report/readiness surface is already owned by the open card #476 and must not be duplicated here.

Evidence: this tick's authoring probes were reads only — `git show e971daf8 --stat`, `sed -n` on `portfolio.py`, `grep` for `measure_swing_capacity` / `capacity` across `v8-next/src`, `json.load` of `artifacts/benchmarks/economic_receipt_9dcc92b9.json`, and the ledger receipt of seq 21 read back from `artifacts/benchmarks/benchmark_ledger.jsonl`. No engine run, no backtest, no full-tape scan, no artifact written.

<!-- agent: scout (job e0a9e2697d65) -->


