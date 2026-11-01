# Per-issue examination — 25 surviving v8-next issues

Verdict vocabulary: `still-valid` | `already-fixed` | `stale-but-real` | `superseded` | `NOT_IDENTIFIABLE`.
Every verdict cites at least one real v8-next path or an executed command result. Cited `file:line` coordinates were treated as claims, not facts — several had drifted.

## Verdict summary

| verdict | count | issues |
|---|---|---|
| still-valid | 9 | 495, 477, 476, 456, 455, 389, 384, 382, 381 |
| already-fixed | 6 | 500, 478, 409, 391, 390, 377 |
| stale-but-real | 8 | 494, 393, 392, 385, 383, 380, 379, 378 |
| superseded | 1 | 434 |
| NOT_IDENTIFIABLE | 1 | 491 |

## Per-issue

### #500 — `already-fixed` — [DEFECT] Canonical P+E verdict ignores its own mix

**Claim as filed:** Canonical receipt publishes the full engine-level mixer but hands the verdict builder a stripped copy, so one artifact carries `scope: ENGINE_LEVEL_SAME_BUDGET` and, three keys away, `BASIS_UNSTATED`.

**Check performed:** Grepped the whole service for the described symptom constant and for the mixer hand-off.

**Evidence:**

- `grep -rn "BASIS_UNSTATED" src/` -> 0 hits tree-wide (symptom constant no longer exists).
- `v8-next/src/v8_next/app/portfolio.py:734` still publishes `"scope": "ENGINE_LEVEL_SAME_BUDGET"`.
- `v8-next/src/v8_next/evaluation/economic_benchmark.py:4285-4298` now branches on `mix.get("scope") == "ENGINE_LEVEL_SAME_BUDGET"` read from the *same* published `r.portfolio_mix` to emit the budget note — one object, one basis statement.

### #495 — `still-valid` — [DEFECT] G3 benchmark coverage cell measures regime robustness

**Claim as filed:** The gate cell published as `g3_benchmark_coverage` measures regime robustness, not benchmark coverage, and on the canonical portfolio path it is not measured at all.

**Check performed:** Checked the G3 cell identity, its resolver, and its readiness role.

**Evidence:**

- `v8-next/src/v8_next/evaluation/benchmark_receipt.py:429-430` — `canonical_id="G3ScenarioRobustness"`, `vector_field="g3_benchmark_coverage"` (name/value mismatch unchanged).
- `benchmark_receipt.py:552` — `g3_benchmark_coverage: GateState = GateState.MISSING` (default state, consistent with "not measured").
- `v8-next/src/v8_next/evaluation/gate_registry.py:35` — `"G3ScenarioRobustness": "evaluate_g3_scenario_robustness"` (the resolver measures robustness).
- `gate_registry.py:51` — G3 is registered `DIAGNOSTIC`, so it grants no authority over coverage.

### #494 — `stale-but-real` — [DEFECT] DSR subject chosen by alphabetical sort

**Claim as filed:** The receipt's DSR describes a curve picked by `sorted(...)[0]`, and the pinned `StatisticsPlan` carries no field naming which variant the number is about.

**Check performed:** Searched for the alphabetical selector and inspected the `StatisticsPlan` field set.

**Evidence:**

- The `sorted(...)[0]` selector is gone from `v8-next/src/v8_next/evaluation/gate_resolution.py` (`grep "sorted(.*)\[0\]"` now hits only `economic_benchmark.py:1470`, which picks a *series length*, not a DSR subject).
- `v8-next/src/v8_next/evaluation/statistics_plan.py:53-77` — `StatisticsPlan` fields are family/block_size/reps/seed/multiplicity_trials/effective_independent_trials/independence_basis/pbo_*/wrc_*/authority_conditions/diagnostics/pinned_ns/interval_bars. No subject field: a receipt still cannot name the variant its DSR is about.
- Conclusion: the selection half was refactored away; the declaration half (the issue's actual requirement — "make the receipt's DSR name a **declared** subject") is not implemented.

### #491 — `NOT_IDENTIFIABLE` — [DEFECT] Equity path drops closed campaign exit P&L

**Claim as filed:** Both engine->series builders delete a position from the mark book before its exit price is marked, so the exit leg never enters `equity_mtm`; the gap is then smeared by the #436 graft.

**Check performed:** Tried to confirm at the cited lines.

**Evidence:**

- Cited lines have drifted: `v8-next/src/v8_next/evaluation/economic_benchmark.py:3149-3155` now contains open-position MTM/entry-commission accounting, not the equity-path builder the issue describes.
- The described builder is not locatable from the issue text alone at the cited coordinates; confirming whether the exit leg is booked needs re-derivation of the current builder, which is outside this audit's read-only remit.
- Verdict is fail-closed: not claimed fixed, not claimed still-valid.

### #478 — `already-fixed` — [DEFECT] Ledger keeps a superseded cost verdict

**Claim as filed:** Ledger `seq 21` publishes `cost_basis = MISMATCH` / `EXECUTION_UNPROVEN` for the same window and fills that `seq 23` publishes as `VERIFIED_ENGINE_FUNDED`, so a consumer cannot tell which cost verdict governs.

**Check performed:** Looked for the declared superseded->corrected mechanism the issue asked for.

**Evidence:**

- `v8-next/src/v8_next/app/readiness.py:786` — `DECLARED_CORRECTIONS` with a `superseded -> corrected` pair plus "the authority that decided it".
- `readiness.py:812` — the superseded value is asserted against the declaration (`float(before) == float(declared["superseded"])`).
- `readiness.py:893-896` — "and never a verdict — the value it supersedes stays a property of this record".
- `readiness.py:919` — the corrected value is scored against its declared pair instead of the superseded value.

### #477 — `still-valid` — [DEFECT] Canonical capacity bound bypasses swing contract

**Claim as filed:** The only capacity producer wired into the canonical portfolio run is never routed through the swing-capacity contract, so a bound is published as *measured* at a participation scale the run never observed.

**Check performed:** Checked whether the swing contract landed, and whether the canonical path consumes it.

**Evidence:**

- The contract landed inside the module: `v8-next/src/v8_next/evaluation/capacity.py:179` and `:223` return `status="UNRESOLVED" if scaled else "NO_ECONOMIC_CLAIM"`; `:11` documents that resolution.
- But the module is consumed by nothing: `grep -rn "evaluation.capacity" src/ tests/` -> only `tests/test_capacity.py` imports it. No `src/v8_next/**` module imports `v8_next.evaluation.capacity`.
- So the canonical portfolio run still cannot route through the contract — the issue's actual complaint (unwired) holds, even though the contract code exists.

### #476 — `still-valid` — [DEFECT] 451-454 outputs are IMPLEMENTED but unwired to the benchmark path (MISSING on the final surface)

**Claim as filed:** Chain issues #451-#454 are closed as "all R IDs complete" but their outputs are consumed by no executable path ending at `v8-next benchmark` -> BenchmarkRunner -> BenchmarkReceipt -> PolicyCertificate -> readiness/regression.

**Check performed:** Tested the claim directly by asking whether the chain-family modules are imported anywhere outside their own tests.

**Evidence:**

- `v8-next/src/v8_next/evaluation/mintrl.py` — `grep -rn "import.*mintrl" src tests` -> only `tests/test_mintrl.py:9`.
- `v8-next/src/v8_next/evaluation/costs.py` `compute_operating_net` — only `tests/test_operating_net.py:11` imports it.
- `v8-next/src/v8_next/evaluation/capacity.py` — no `src/` importer at all.
- `v8-next/src/v8_next/opportunities/book.py` — imported only by `adapters/expert_strategy.py` and `opportunities/__init__.py`; no `evaluation/` or `app/` economic path consumes it.
- This is the same IMPLEMENTED-but-UNWIRED pattern the issue names, reproduced on 2026-10-30 code.

### #456 — `still-valid` — [IMPL] v8-next port chain 7/7: expert lifecycle (delta + D-141 qualification + kaizen/assurance/governance remainder)

**Claim as filed:** Chain 7/7: close the expert lifecycle — expert-delta mapping, D-141 qualification, kaizen/assurance/governance remainder — measured against the closed scoring of the earlier chain issues.

**Check performed:** Checked the delta test the issue names and the expert module set.

**Evidence:**

- `v8-next/tests/test_expert_delta.py` — does not exist (`ls` -> No such file or directory); the issue names it as required surface.
- `v8-next/src/v8_next/experts/` exists with the ported experts (bollinger, breakouts, candlestick, ...), so the module side is present while the delta/qualification evidence is not.
- Chain predecessor #455 is still `state:blocked`, so 456 cannot be measured against "the closed scoring of the earlier chain issues".

**Scope note:** Port-parity program presumes v8-core as the reference implementation. If v8-core is no longer a reference, this becomes NOT_APPLICABLE rather than closable-as-done.

### #455 — `still-valid` — [IMPL] v8-next port chain 6/7: scoring closure (bench-eval delta + synthetic discipline + temporal)

**Claim as filed:** Chain 6/7: close scoring — bench-eval delta, synthetic discipline, temporal — so every published score is a function of bound evidence.

**Check performed:** Read the issue's own lifecycle declaration and checked the named evidence test.

**Evidence:**

- Body: "Lifecycle state:blocked — chain step 6/7 implemented; R1-R4 evidenced at `b78a86e3aea3aa1150e083ed01cdf3cea2056c9f`; R5 BLOCKED on two named foreign reds (below); 2026-09-12." Self-declared blocked, not done.
- `v8-next/tests/test_d153_parity.py` and `test_gate_window_binding_406_421.py` exist and pass (38 passed, 1 skipped across the focused set), so R1-R4 evidence is reproducible.
- Label `state:blocked` on the live issue matches the body.

**Scope note:** Port-parity program presumes v8-core as reference; see 456.

### #434 — `superseded` — [GOV] Otonom merge yetkisi verildi — merge yasagi kaldirildi (D-163)

**Claim as filed:** Owner directive 2026-09-11 (D-163): the autonomous-merge ban is lifted; agents/workers may merge verified work to main without human approval.

**Check performed:** Checked whether the directive is recorded and whether the tree now encodes it.

**Evidence:**

- `docs/GOVERNANCE_MERGE_AUTHORITY_2026-09-11.md` exists — the directive's full text is recorded in the repo.
- Root `AGENTS.md` §4 now encodes the resulting loop: "`edit in v8-next/ -> run focused tests/lint -> commit to main -> continue`. No PR ceremony".
- The issue is an announcement with no work item attached; its content is fully represented in tracked documents.

### #409 — `already-fixed` — [DEFECT] Active product boundary rewritten without authority record

**Claim as filed:** Two mutually exclusive product-boundary declarations coexist: root `AGENTS.md` says "`v8-core/` is the ONLY active, authoritative codebase" while `v8-next/AGENTS.md` says the opposite.

**Check performed:** Read both declarations at HEAD.

**Evidence:**

- Root `AGENTS.md` §1 now reads: "**`v8-next/` (PRIMARY & ACTIVE):** The sole active codebase." and "**`v8-core/` (ARCHIVED RUST — READ-ONLY):** Never modify, create files, or run `cargo` builds/tests here."
- `v8-next/AGENTS.md` header: "On 2026-09-11 the owner explicitly confirmed that v8-next is the intended codebase ... This supersedes the historical freeze and Rust-only wording below for this scope".
- The two declarations no longer conflict; the "v8-core is the ONLY active codebase" text the issue quotes is gone.
- This audit independently relied on that resolution: the 45 v8-core-scoped closures are premised on root `AGENTS.md` §1.

### #393 — `stale-but-real` — [RESEARCH] V8-next: close the economic evidence gate without weakening NO_ECONOMIC_CLAIM

**Claim as filed:** Umbrella: define and execute the remaining evidence program to resolve the V8-next economic gate while preserving NO_ECONOMIC_CLAIM until all receipts are independently verified.

**Check performed:** Checked whether the umbrella's child surfaces exist and are wired.

**Evidence:**

- All named surfaces exist: `evaluation/runner.py`, `gate_resolution.py`, `economic_benchmark.py`, `parity.py`, `overfitting.py`, `store.py`.
- But the program cannot close: children 378/381/382/383/385 are implemented-yet-unwired (see 476) and 392's UNKNOWN states remain.
- As a container issue it stays real, but it will not converge until the wiring work in 476 is done.

### #392 — `stale-but-real` — [IMPL] V8-next: resolve UNKNOWN and MISSING gate states with explicit evidence

**Claim as filed:** Turn the gate vector's UNKNOWN/MISSING states into explicit, evidence-backed outcomes without forcing or fabricating passes.

**Check performed:** Counted the UNKNOWN returns still present in the resolver.

**Evidence:**

- `v8-next/src/v8_next/evaluation/gate_resolution.py:675` returns `GateState.UNKNOWN` for an unauthorized underpowered track.
- `gate_resolution.py:1099-1103` returns `UNKNOWN` for G7 with a named reason ("prospective evidence, so G7 stays UNKNOWN instead of passing").
- Both are correct fail-closed outcomes, so the remaining work is narrower than the issue text: the states are now named rather than silent, but MISSING defaults still exist (`benchmark_receipt.py:552`).

### #391 — `already-fixed` — [DEFECT] V8-next Ruff import ordering failure blocks clean quality gate

**Claim as filed:** The v8-next quality gate fails with one Ruff I001 import-ordering error.

**Check performed:** Ran the gate.

**Evidence:**

- `uv run ruff check src tests --select I001` -> "All checks passed!".

### #390 — `already-fixed` — [DEFECT] V8-next test environment lacks locked DuckDB dependency

**Claim as filed:** The full test command fails with `ModuleNotFoundError: No module named 'duckdb'` because the dependency is not locked.

**Check performed:** Checked the declaration and the lock.

**Evidence:**

- `v8-next/pyproject.toml:35` — `"duckdb>=1.0",` is a declared dependency.
- `v8-next/uv.lock:94-105` — `name = "duckdb"` version 1.5.5 with per-platform wheels pinned.
- `v8-next/tests/test_store_models_and_duckdb.py` exists (14035 bytes).

### #389 — `still-valid` — [DEFECT] V8-next status ledger fails self-verification at entry 0

**Claim as filed:** The status ledger fails self-verification at entry 0 (ENTRY_RECEIPT_INVALID / DIGEST_TAMPERED), yet the dashboard still renders a latest benchmark certificate.

**Check performed:** Read the `status` command and tried to reproduce.

**Evidence:**

- `v8-next/src/v8_next/app/cli.py:110-133` — `chain_ok, chain_msg = ledger.verify_chain()` is used *only* inside the print f-string; `chain_ok` never gates the subsequent `ledger.publication()`, `PolicyCertificate.generate(...).render_ascii()` or the `return 0`.
- So a BROKEN chain still renders a certificate and exits 0 — the issue's third required end state ("the dashboard clearly separates latest report metadata from a valid evidence-chain status") is not implemented.
- Reproduction of the entry-0 digest mismatch is NOT_IDENTIFIABLE now: `v8-next/artifacts/benchmarks/` does not exist and no `benchmark_ledger*.jsonl` is on disk; `v8-next status` reports "benchmark: no ledger".
- The defect is therefore confirmed structurally, not by replaying the original corrupted ledger.

### #385 — `stale-but-real` — [IMPL] V8-next: real operating net and venue-cost calibration

**Claim as filed:** Add an evidence-backed operating-net layer separating strategy net, venue friction, funding and fixed operating costs, using real venue observations.

**Check performed:** Checked whether the layer made it onto the economic path.

**Evidence:**

- The layer exists: `v8-next/src/v8_next/evaluation/costs.py:93-220` (`OperatingNetResult`, `compute_operating_net`, `operating_net=strategy_net - operating_costs`).
- `v8-next/tests/test_operating_net.py` exists and passes.
- But `grep -rn "compute_operating_net" src tests` -> only its own test. `economic_benchmark.py` contains 0 references to `operating_net`/`OperatingNet`. The issue names `economic_benchmark.py` and `report.py` as expected surface — neither consumes it.

### #384 — `still-valid` — [IMPL] V8-next: bind complete candidate lifecycle to economic evaluation

**Claim as filed:** Make economic evaluation consume the complete candidate/opportunity/campaign lifecycle (triggered, rejected, invalidated, expired, unfilled, filled) with reasons.

**Check performed:** Checked whether the economic evaluator imports the opportunity book.

**Evidence:**

- `v8-next/src/v8_next/opportunities/book.py` exists, but `grep -rn "from v8_next.opportunities\|import opportunities" src/v8_next/evaluation src/v8_next/app` -> no hits. Only `adapters/expert_strategy.py`, `opportunities/__init__.py` reference it.
- `v8-next/tests/test_candidate_lifecycle_evaluator.py` — does not exist (named as expected surface).
- Verdict: the lifecycle is not consumed by economic evaluation.

### #383 — `stale-but-real` — [IMPL] V8-next: wire two-ledger external parity into the economic evaluator

**Claim as filed:** Connect economic evaluation to two physically produced native/reference ledgers with explicit semantic mapping and fail-closed parity receipts.

**Check performed:** Checked what `parity` actually binds on the economic path.

**Evidence:**

- Some parity is wired: `v8-next/src/v8_next/app/economic.py:28` imports `ArtifactBinding` from `v8_next.evaluation.parity`; `:595` publishes `parity={"engine_rerun_parity": "EXACT_MATCH" if parity_ok else "DIVERGED", ...}`; `:652` attaches `artifact_bindings`.
- But that is same-engine rerun parity plus artifact binding — not two *physically produced* native/reference ledgers with semantic mapping.
- `v8-next/tests/test_economic_parity_wiring.py` — does not exist (named as expected surface). `tests/test_d153_parity.py` exists and passes, covering the module in isolation.

### #382 — `still-valid` — [RESEARCH] V8-next: validate capacity and market impact from L2 data

**Claim as filed:** Measure executable capacity across capital scales using real tick/L2/ADV and venue fill data instead of linear OHLCV extrapolation.

**Check performed:** Read the capacity module's own declared contract and checked its consumers.

**Evidence:**

- `v8-next/src/v8_next/evaluation/capacity.py:4-5` — "hourly OHLCV/ADV observations plus fills produced by the declared execution model; **order-book/L2 data is not part of this contract**." The module explicitly declines the issue's core requirement.
- `capacity.py:13` — "no linear notional extrapolation read as a measurement" (one half of the issue is addressed).
- `capacity.py` has no `src/` importer, so the measurement is not on the canonical path either.

### #381 — `still-valid` — [IMPL] V8-next: joint P+E portfolio execution and shared capital

**Claim as filed:** Replace allocator-only P vs P+E sleeve arithmetic with a single joint portfolio execution and accounting path under one capital and risk budget.

**Check performed:** Checked whether the economic benchmark imports the joint portfolio adapters.

**Evidence:**

- `grep -n "portfolio_backtest\|portfolio_equity" v8-next/src/v8_next/evaluation/economic_benchmark.py` -> no hits.
- Those adapters are consumed elsewhere (`adapters/basket_backtest.py`, `funding_history.py`, `node_backtest.py`; `adapters/economic_paper.py`, `historical_trial.py`, `portfolio_risk.py`), not by the canonical economic comparison.
- `v8-next/tests/test_joint_portfolio_execution.py` — does not exist (named as expected surface).

### #380 — `stale-but-real` — [IMPL] V8-next: complete funding finality and coverage

**Claim as filed:** Make funding cost an evidence-backed, position-aware, final accounting component for the benchmark and paper paths.

**Check performed:** Checked how deep funding reaches into the economic benchmark, and whether the finality test exists.

**Evidence:**

- Funding is broadly wired: `grep -c "funding" v8-next/src/v8_next/evaluation/economic_benchmark.py` -> 193; `adapters/funding_history.py` and `adapters/settlements.py` exist; `tests/test_online_funding.py` and `tests/test_bounded_funding_capture.py` exist.
- `v8-next/tests/test_funding_finality.py` — does not exist (named as expected surface), so the "final/finality" half has no acceptance test.
- Verdict: the accounting component is present and partly tested; the finality claim the issue asks for is unproven.

### #379 — `stale-but-real` — [IMPL] V8-next: venue fills, latency, shortfall, and account reconciliation

**Claim as filed:** Add a real venue-evidence path separating decision/submission/acceptance/fill/rejection/account clocks and reconciling model execution against venue-settled outcomes.

**Check performed:** Checked shortfall/clock reconciliation reach and the acceptance test.

**Evidence:**

- Shortfall reconciliation is wired: `shortfall` appears in `adapters/execution_telemetry.py`, `adapters/shadow_ingest.py`, `evaluation/economic_benchmark.py`, `evaluation/capacity.py`, `evaluation/scoring.py` (11 modules).
- `v8-next/tests/test_shortfall_reconciliation.py` — does not exist (named as expected surface). `tests/test_capture_integrity.py` and `tests/test_d153_parity.py` exist and pass.
- Verdict: implementation largely present; the named reconciliation acceptance test and the clock-separation claim are unproven.

### #378 — `stale-but-real` — [RESEARCH] V8-next: implement and validate MinTRL estimator

**Claim as filed:** Implement a declared-assumption MinTRL estimator reporting the minimum observation horizon needed to distinguish a target Sharpe at a stated confidence and power.

**Check performed:** Checked the estimator and whether the economic path consumes it.

**Evidence:**

- Implemented: `v8-next/src/v8_next/evaluation/mintrl.py` (`MinTRLPlan`, `estimate_min_trl`), `v8-next/tests/test_mintrl.py` exists and passes.
- `grep -rn "import.*mintrl" src tests` -> only `tests/test_mintrl.py:9`. No `src/` module imports it, and `economic_benchmark.py` has 0 `mintrl`/`min_trl` references — the issue names `economic_benchmark.py` as expected surface.

### #377 — `already-fixed` — [IMPL] V8-next: protected OOS and complete search-family evidence

**Claim as filed:** Implement a protected, one-shot chronological OOS workflow and complete local search-family accounting.

**Check performed:** Checked the workflow module, its CLI exposure, and its tests.

**Evidence:**

- `v8-next/src/v8_next/evaluation/forward_plan.py` plus `v8_next/app/forward.py` and `v8_next/app/plan.py` exist; `evaluation/historical_plan.py` extends the family.
- Exposed on the CLI: `v8-next/src/v8_next/app/cli.py:494` — `"forward": "v8_next.app.forward"` passthrough.
- `tests/test_forward_plan.py` and `tests/test_family.py` exist and pass (part of 38 passed / 1 skipped).

## Duplicate clusters

### C1 — IMPLEMENTED-but-UNWIRED (root cause of the chain family)

**Canonical issue:** #476

**Members:** #476, #455, #456, #378, #381, #382, #383, #385, #384, #393

**Why one cluster:** Each member asks for a capability that exists as a standalone module with a green unit test, but which no `src/` module on the benchmark/economic path imports. #476 is the only issue that states the general contradiction and the governing contract (`docs/contracts/WIRING_COMPLETION_CONTRACT.md` §4); the others are instances. Fixing the wiring closes most of them at once.

### C2 — Gate-vector naming / evidence expression

**Canonical issue:** #392

**Members:** #392, #494, #495

**Why one cluster:** All three are about the gate vector failing to say what it measured: 495 (G3 cell named coverage but measuring robustness), 494 (DSR name not a declared subject), 392 (UNKNOWN/MISSING states needing explicit evidence). 392 is the umbrella that defines how a cell must express its basis; resolving it settles the vocabulary for 494 and 495.

### C3 — Clean-quality-gate defects (all three reproducible by one command each)

**Canonical issue:** #389

**Members:** #389, #390, #391

**Why one cluster:** Not duplicates — distinct defects — but a single cluster because 390 and 391 are already fixed and verifiably closed, leaving 389 as the only live gate blocker. Closing 390/391 first makes 389 the sole red.

### C4 — Archived-boundary governance

**Canonical issue:** #409

**Members:** #409, #434

**Why one cluster:** Both are repo-wide governance records, not code. 409 (boundary conflict) is resolved at HEAD; 434 (merge authority) is recorded in docs. Neither has a v8-next code surface.

## Blockers

- **#455** — R5 blocked on "two named foreign reds" — the issue body declares `state:blocked` at `b78a86e3` with R1-R4 evidenced and R5 open. Cannot close until those foreign reds are named-and-cleared in a fresh run.
- **#456** — Depends on #455 (chain 6/7). #455 is blocked, so 7/7 cannot be measured "against the closed scoring of the earlier chain issues". Also `tests/test_expert_delta.py` is absent.
- **#476** — Gated on `docs/contracts/WIRING_COMPLETION_CONTRACT.md` §4 being applied to the #451-#454 outputs. No `src/` consumer exists for mintrl / operating-net / capacity / opportunity-book, so the work is a wiring program, not a defect patch.
- **#393** — Child-dependent: 377-385 must reach a terminal state. Today 378/381/382/383/385 are unwired and 392 is open, so the umbrella cannot converge.
- **#389** — The reproducing ledger no longer exists on disk (`v8-next/artifacts/benchmarks/` absent; `v8-next status` -> "no ledger"). The structural defect is confirmed by code read, but a regression test needs a synthetically corrupted ledger fixture, which the issue already asks for and which is absent.
- **#491** — Cited `file:line` coordinates have drifted since filing, so the claim cannot be confirmed or refuted at the given location. Needs re-derivation against the current equity-path builder before either closing or scheduling.
