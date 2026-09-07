# D-160: V8.6 Phase-1 Execution-Lane Charter — Attic Disposition, Verdicts, and Migration Authority

**Status:** `PROVISIONAL_DECISION` (reversible; grants no economic authority).
**Date:** 2026-09-07. **Branch:** `exec/v86-autonomous` (PR #361).
**Authority:** V8.6 Production Recalibration Research Monograph §18 (Stage B
archiving mandate), §11 (evaluation authority), Appendix A (migration
disposition); issues #344 (W1), #345 (W2), #346 (W3), #347 (W4).
**Predecessors:** D-149 (Rule 44 full-text anchoring), D-153 (Benchmark
Fabric), D-156 (evidence hardening), D-159 (research-validity audit).

## 1. What this decision covers

Phase 1 of the V8.6 migration program puts the repository into an
implementation-ready state WITHOUT changing runtime behavior:

1. Archive provably dead code to `v8-core/attic/` (W1/W2/W3).
2. Close UNKNOWN verdict rows with evidence (W4).
3. Dispose of the stale dirty-911 work without smuggling behavior changes.
4. Pin the D-153 verification table as an immutable constraint.
5. Charter the V8.6 implementation work items (§6/§14/§15/§18) with
   requirement traceability.

Every verdict in scope remains `NO_ECONOMIC_CLAIM`. No p-value, effect size,
tolerance, expected improvement, or confidence value is introduced.

## 2. Attic dispositions (behavior-preserving moves)

| Lane | Moved to | Content | Receipt |
|---|---|---|---|
| W1 (#344) | `v8-core/attic/kaizen-governance/` (9 files net) | `correlation`, `derivatives`, `governance`, `mega`, `provenance`, `pyramiding`, `cost_surface`, `liquidity_floor`, `verification` | Zero-caller scan; `cargo check` green |
| W1 amendment | reverted to live | `kaizen/{controller,verdict}.rs` | §3 (constitutional gate outranks zero-caller heuristic) |
| W1 KEEP | live, OPEN_PIN closed | `campaign`, `chop_suppression`, `exit_trailing`, `quantization`, `research_debt` + closure (`challenger`, `diagnosis`, `hypothesis`, `adaptive`, `robustness`, `validation`, `iteration`) | Live consumers: `usdm_sim.rs`, `main.rs`, `benchmark/kaizen_feed.rs`, `d153_benchmark_fabric_sabotage` |
| W2 (#345) | `v8-core/attic/evaluation/` (7 files) | `manifest`, `statistics`, `surfaces`, `paths`, `regression`, `html_report`, `deployment_case` + `EvaluationEngine` gut | §4 bundle gate |
| W2 quarantine | live, tagged | `friction`, `production_growth`, `scope` (`needs:authority` to grow; sole consumer `tests/production_growth_contract.rs`) | 5/5 tests green |
| W3 (#346) | `v8-core/attic/w3-dead-quartet/` (4 files) | `checkpoint`, `world/learned`, `analysis/scorecard`, `opportunity/harness_t1_t12` | Per-file consumer scans; `cargo check` green |
| W4 (#347) | no moves | `differential.rs` KEEP (dormant); `system_proving/*` KEEP + quarantine-tag | `.audit/w4/VERDICT.md` receipts R2(a–c) |

Attic directories are NOT compiled (no `mod` declaration references them);
`tools/audit_doc_path_refs.py` classifies relocated citations as `RETIRED`
(real predecessor in git history) and passes.

## 3. W1 amendment: constitutional gate outranks heuristics

After W1, `tools/audit_reachability.py` (D-132/Rule 35 enforcement) FAILED:
it requires `v8-core/src/kaizen/{controller,verdict}.rs` as sovereign
components ("all economic claims must pass through ClaimValue/ClaimRegistry/
Kaizen"). W1's own gate included reachability. The pair is self-contained
(deps only on live `claims`/`authority`/`hash`/`research_debt`) and was
reverted; reachability is back to `PASS (100%)`. Rule: no future attic move
may remove a file named by a constitutional enforcement tool without first
amending the tool's authority — weakening the gate to fit the move is
forbidden.

## 4. Verification gates (all green on the lane)

- `cargo check`: rc=0, zero warnings after every move.
- Oracle-coverage receipt: stdout byte-identical before/after W2.
- Full-audit certificate: byte-identical before/after W2 modulo 10 named
  wall-clock fields (`*_duration_sec`, `total_wall_time_sec`, S6 timers);
  every artifact hash identical (normalizer: `.audit/w2/norm_cert.py`).
- **D-153 pin** (`.audit/d153_pin/baseline.json`): 132/132 unchanged across
  W1/W2/W3 — BFS sabotage 24, minerva/dashboard 3, parity adapters 50,
  receipt/ledger self-verify 40, d152 firewall 15.
- Expected test-count delta: atticed internal tests leave the build
  (`harness_t1_t12` 13, `checkpoint`/`scorecard`/`evaluation` unit tests).
  This is disposition, not regression; the D-153 pin is the immutable table.

## 5. D-153 immutability constraint (registered user directive)

The D-153 verification table (D-153 register row: BFS-001..024 24/24, #327
15 tests, #328 40 tests, #329 50 tests) MUST NOT change as a result of
Phase-1 or Phase-2 work. Any future run reporting different counts is a
STOP condition, not a re-baseline, until adjudicated by a new decision.
The D-153 row itself is untouched by this decision.

## 6. Dirty-911 disposition: drop the port, preserve the ideas

The uncommitted 911-line work on the stale `main@c2539cd8` fork (funding
settlement rework, liquidation `cum`-sign flip, trailing-stop rework,
validity witnesses against the pre-split single-file `usdm_sim` layout) is
NOT ported: the base predates the `usdm_sim/` split and D-152/D-156/D-159,
and porting would smuggle unregistered behavior changes into a
behavior-preserving lane while voiding the §4 bundle seal. The local `main`
tree is left untouched. Each novel claim is preserved as a V8.6 work item
(§7), where the liquidation formula question must be settled against a named
venue spec BEFORE any code change.

## 7. Migration program authority (Phase 2 work items)

This decision charters R#-traced implementation issues for: V8.6 §6
(NautilusTrader execution substrate), §14 (venue conformance layer, incl.
funding-ledger ownership and the liquidation parity question), §15
(portfolio/risk authority, incl. the carried trailing-stop rework claim),
§18 (migration program). W14 (differential successor question) is the open
thread that may revisit the W4 `differential.rs` KEEP verdict once a named
successor exists.

## 8. Failure semantics

- Bundle drift vs the W2 seal → FAIL, revert the move (per-issue semantics stand).
- D-153 pin drift → STOP, no re-baseline without a new decision (§5).
- Verdict without receipts → BLOCKED (W4 rule stands).
- Unregistered architectural code → shadow, blocks merge (§9 of AGENTS.md).

## 9. Carried OPEN_PINs

`OPEN_PIN_GATE_NAMING` (D-152 §5 vs D-153 §2, from D-159); D-156 registered
benchmark evaluator; pre-v2 ledger rows unbound; D-116
commission/funding/terminal-balance parity unmapped (now joined by the
liquidation `cum`-sign question, §6). None is adjudicated here.

Modified artifacts: this spec + `docs/tr/D160_V86_PHASE1_EXECUTION_LANE_SPEC.md`,
`docs/decisions/DECISION_REGISTER.md`, `docs/tr/DECISION_REGISTER.md`,
`docs/contracts/IMPLEMENTATION_LAYOUT.md`, `docs/CHANGELOG.md`,
`site/index.html`, `site/tr.html`, `v8-core/attic/*`, lane receipts under
`.audit/{d153_pin,w2,w3,w4,dirty911}/`.
