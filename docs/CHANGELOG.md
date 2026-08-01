# V8 Changelog

Format: dated, brief, reversible. This log records document and architecture
decisions — never economics. Each entry names the artifacts it changed.

## 2026-08-01 — Session-2 closure: Phase 1 real data + preregistration (operator pass)

Session 2 (commits `3436248`..`91396fe`) executed Phase 1 on real data and
wrote the `v8_slice_001` preregistration; all 5 steps DONE, suite 42 -> 50
tests, monograph probe byte-identical to the session-2 baseline
(`ea5b7705…`) at every step, corpus untouched (verified independently on
re-review). This operator pass closes the pins the agent left.

- **D-038 registered** — Phase-1 tooling deps (polars/pyarrow/
  pandera[polars]/duckdb) admitted as the `tooling` extra for `tools/data.py`
  + `tools/materialize_views.py`; decision path stays stdlib-only. Resolves
  the session-2 open pin 1.
- **IMPLEMENTATION_LAYOUT updated** — `tools/vision_backfill.py` and
  `tools/materialize_views.py` moved from "planned" into the file family
  (tree + file table); five test files listed.
- **Real tape pinned** — BTCUSDT 1h 2026-04..06 (2184 rows, tape hash
  `8b12707e…`), verified via `data.py`; JSONL PIT tape audit clean;
  materializations + lab run deterministic (ledger `2c1e0fd8…`,
  `NO_ECONOMIC_CLAIM`). Derived artifacts live under `research/tape/`
  (gitignored, reproducible — never committed).
- **`v8_slice_001` preregistration** (`docs/PREREGISTRATION_V8_SLICE_001.md`)
  written with all HYPOTHESIS_LAB_PROTOCOL fields; O-017 proposal (share
  floor 0.25, KS threshold 0.20) derived pre-holdout from the dev baseline
  (execution_share 0.4156, KS 0.073); adversarial review (1 blocker + 7
  warnings) incorporated. **Not yet in the monograph** — it is frozen content
  awaiting operator ratification (§16); holdout not downloaded, experiment
  not run.
- **Carry-forwards (operator + Phase 4):** D-027 verdict gating
  (`execution_share`/divergence/`ATTRIBUTION_UNSAFE_*` in `LabReport`)
  remains code-pending; it lands with the Phase-4 experiment runner. The
  preregistration's §16 operator actions (ratify thresholds; record holdout
  tape hash at download time; authority receipt before any verdict) are
  unperformed by design.
- Rebuilt `site/index.html` (31 sections — the three edited corpus files are
  all monograph sections; the probe baseline for the next session changes).

## 2026-08-01 — Autonomous build session closure (operator pass)

The Phase 0-3 autonomous build (commits `4f34abe`..`f2f8bf2`) completed all
7 runbook steps: the vertical-slice suite grew 15 -> 42 tests, the monograph
probe rebuild was byte-identical to the baseline hash at every step, and the
`docs/` corpus was untouched by the agent (verified independently on
re-review). This operator pass closes the artifacts the agent was not
authorized to write.

- **IMPLEMENTATION_LAYOUT §4 divergence rows closed** with their commits:
  episode_key anchor (D-026, `4f34abe`), funding settlement
  (SIMULATION_TRUTH_SPEC §5/§7, `760e6cc`), D-024 mask (`778ceb1`). The D-026
  key-stability cheap test is now part of the suite (§5 item 4 updated).
- **D-037 registered** — resolves the Step-4 OPEN_PIN: the stdlib mirror of
  `tools/data.py` contracts in `tools/vision_backfill.py` is accepted;
  literal reuse deferred until Phase-1 parquet materialization admits the
  heavy deps. `pyyaml>=6` dev-extra noted (environment, not decision path).
- **`docs/EXPERTS_REGISTRY.yaml` registered in the monograph build** (section
  count 30 -> 31): the Phase-3 expert registry now has a visible home next to
  CLAIMS/EXPERIMENT registries; the agent could not add it to NAMES (docs
  freeze).
- Rebuilt `site/index.html`; runbook Step 3's funding-window interpretation
  and the seed-7 epoch artifact remain recorded in `RUNLOG.md` and
  `docs/STATUS_REPORT.md` (session artifacts, not corpus).

## 2026-08-01 — Autonomous build handoff (design + tooling line)

Design line only; no runtime code changed in this pass.

- **`docs/AGENT_RUNBOOK.md` added** — execution contract for a ~2h
  autonomous build (Phase 0-3). Seven timeboxed steps (D-026 anchor, funding
  settlement, D-024 mask, `vision_backfill.py` + tape audit, feature
  groups/lineage, expert metadata + registry, status report) each with
  owning files, DoD commands, gates, and commit messages. Hard rules: spec
  freeze (agent never edits `docs/` except RUNLOG/STATUS_REPORT), forbidden
  components (rules 6/14), no experiment runs, no frozen-OOS opening,
  tests-as-contract-probes, no `--amend`, no `git add -A`.
- **Anti-drift gate:** every step re-probes the monograph build and requires
  byte-identity with the pre-flight hash — a contract edit would change the
  hash and fail the gate.
- **D-034/035/036 registered** — implementation pins for D-026 (anchor =
  first bar of the setup run via a new 32-bar `history` feature group; key
  drops birth timestamp; `is_duplicate` becomes anchor-key equality),
  funding (`funding_rate_r`/`funding_hours` manifest fields,
  `SETTLEMENT_BEFORE_ORDERS`, `canonical-sim-v4`), and D-024 mask
  (declared constants, `TRADABILITY_MASK_VETO`). The agent implements the
  pins; it does not revisit them.
- `tools/build_monograph.py` NAMES extended (29 -> 30 sections);
  `site/index.html` rebuilt. `RUNLOG.md` template at repo root (session
  artifact, not corpus).

## 2026-08-01 — File-family restructure (code + layout)

- **D-033 — `src/v8/experts/` subpackage.** `experts.py` split into one file
  per behavior family: `experts/base.py` (Expert base + `_need` +
  `still_valid` contract), `experts/trend_pullback.py`,
  `experts/failed_breakout.py`; `experts/__init__.py` re-exports the pilot set
  so `from v8.experts import ...` is unchanged for consumers.
- **`marketstate.py` retained.** The proposed `state.py` rename was rejected
  by the owner — the file mirrors the `MarketState` record name.
- **`lab._code_hash` now recursive (`rglob('*.py')`).** The flat glob missed
  `experts/*.py`, so an Expert change would not have bound the report (D-010).
  Relative path keys keep the hash stable across checkouts.
- `IMPLEMENTATION_LAYOUT.md` §1/§2/§3 updated to the new tree; file-family
  table now covers `experts/` per file. Tests: 15/15 green after the move.

## 2026-08-01 — Architecture + implementation-layout contracts (design line)

Design-line only; no runtime code changed in this pass.

- **`docs/contracts/ARCHITECTURE_SPEC.md` added.** The monograph claimed to be
  an architecture specification but carried only the 5-line minimum-coherent
  diagram. The new contract names the full component map (tape -> MarketState
  -> Experts -> candidate log -> acceptance/RiskGate -> canonical simulator ->
  lab runner -> hash-bound report), the owning contract and gate of every
  stage, the stepped vs counterfactual execution split (D-009/D-027), and the
  absent-by-default list. Registered as **D-031** (technology baseline).
- **`docs/contracts/IMPLEMENTATION_LAYOUT.md` added.** The file family was
  never designed: `src/v8/` files emerged from the vertical slice, and three
  code/spec divergences followed (episode_key, funding, D-024). The contract
  predetermines every file's responsibility, public interface, and owning
  contract; layering rules (acyclic one-way imports, composition root =
  `lab.py`, no wall clock, stdlib-only decision path); a tracked-divergence
  table; and cheap tests including a kept-red D-026 key-stability gate.
  Registered as **D-032**.
- **O-009 scoped:** the storage-engine *design* is resolved by D-031 (Parquet
  archive + JSONL ledgers + DuckDB derived tables per PERSISTENCE_REPLAY_SPEC
  §1); only the scale-validation experiment remains open.
- `tools/build_monograph.py` NAMES extended (27 -> 29 sections);
  `site/index.html` rebuilt. `docs/tr/` remains a partial mirror and skips the
  new sections, consistent with the existing TR lag.

## 2026-08-01 — R-unit correction, excursions, thesis exit (code + design)

- **D-028 — the simulator was not producing R.** `stop_r`/`target_r` were
  applied as fractional price moves (`entry * (1 + target_r)`, so the shipped
  `target_r = 1.0` meant a +100% price target) and `net_r` was a fractional
  return with an R-calibrated cost constant subtracted from it. Measured before
  the fix: a target hit returned −0.0500 and a stop-out −0.0800 — a winning
  trade booked a loss, and every trade was negative regardless of outcome, so
  no Expert could ever have passed. Risk was also invisible: two positions with
  10× different stop width returned identical numbers. R is now an explicit
  declared price distance (`simulator.risk_unit`, from `atr_ref` or a declared
  `risk_frac`), non-positive units fail closed, and the same measurements now
  return +1.9300 / −1.0700 / identical-across-widths. This defect sat under
  D-023: heat summed a quantity that was not risk.
- **D-030 — excursions and ambiguity restored.** `OpenPosition` and
  `CounterfactualOutcome` carry `mae_r`, `mfe_r` and `ambiguous_bars`. The
  vendored V7 simulator (`simtruth/sim.py`) already had `mae_r`/`mfe_r`; the
  V8 canonical simulator had dropped them — a regression on precisely the
  quantity V7 measured as most predictable (ICs +0.124/+0.152 vs +0.015). Same-
  bar stop+target ambiguity was being resolved by `STOP_FIRST` but never
  recorded, contrary to `SIMULATION_TRUTH_SPEC`. O-013 is now answerable and
  the ambiguity bracket measurable.
- **D-029 — post-entry thesis invalidation.** `Expert.still_valid(state, draft)`
  is evaluated on closed bars while a position is `EXECUTED`; a dead thesis
  closes at that bar's close with `THESIS_INVALIDATED`, distinct from `STOP`.
  Implemented for both shipped Experts (trend gone / breakout succeeded after
  all). Deterministic, inside the frozen spec, no new lifecycle state, no
  learned component; fails open when inputs are unobservable.
- Simulator hash bumped to `canonical-sim-v3`; pre-fix ledgers can no longer
  compare equal to post-fix ones.
- Tests: 7 → 15. New golden tests pin stop-out to exactly −1R − cost, target to
  +target_r − cost, R-invariance across 10× risk width, excursion values,
  ambiguity counting with STOP_FIRST, fail-closed risk unit, and the thesis
  exit. Full suite green.
- Not done: funding is still absent from the simulator while
  `SIMULATION_TRUTH_SPEC` §5/§7 mandate `SETTLEMENT_BEFORE_ORDERS` and
  boundary golden tests — material for perps (~3 settlements per 24×1h hold)
  and the V7 audit's one caught defect. `episode_key` still implements the
  D-026 defective form. D-024 tradability mask remains spec-only.

## 2026-08-01 — Attribution validity gate + episode identity (design line)

Design-line only; no code changed in this pass.

- **D-026 — episode identity contradiction resolved.** `episode_key` was
  defined three ways at once: `CANDIDATE_LIFECYCLE_SPEC` §1 (birth timestamp),
  `EXPERT_PROTOCOL` §2 (`setup_anchor_event_id`), and `src/v8/lifecycle.py`
  (birth timestamp). The clock-anchored form is a defect, not a variant: the
  same setup on consecutive bars hashes differently, so the suppression window
  can never match and deduplication silently never fires — confirmed by direct
  execution against `CandidateRegistry.is_duplicate`. §1 is now the single
  normative definition, anchored to `setup_anchor_event_id`; `EXPERT_PROTOCOL`
  references it instead of restating it, and a key-stability cheap test was
  added. **Follow-up: `src/v8/lifecycle.py:36` still implements the defective
  form; spec and code are knowingly divergent until that lands.**
- **D-027 — attribution validity gate (new).** V8 failed closed on data and on
  authority but not on whether the measured population was the traded one. With
  the exposure rule and heat cap enforced against a stepped ledger, rejection is
  the designed outcome for most simultaneous Candidates, so counterfactual
  domination is structural rather than accidental. `LabReport` now carries
  `execution_share` (portfolio-state rejections only in the denominator — cost
  and invalidation rejections are the hypothesis, not bias) plus an
  executed-vs-rejected divergence statistic; breaching either declared bound
  yields `ATTRIBUTION_UNSAFE_LOW_COVERAGE` / `ATTRIBUTION_UNSAFE_POPULATION_DIVERGENCE`
  rather than a net-utility figure. Refusal, not correction: OPE needs
  propensities a deterministic admission rule cannot produce (rejected
  Candidates have probability 0, the deficient-support case), and two
  independent literature searches returned no admissible finance application.
  Adds no decision-path component; complexity budget (rule 14) untouched.
- **O-014 rewritten, O-017 opened.** O-014's admission condition previously
  called for an OPE correction layer that the evidence does not support; it now
  routes divergence to D-027 instead. O-017 carries the two gate thresholds,
  which must be set from the observed rejection rate before the frozen slice is
  opened.
- Rebuilt `site/index.html` from the corpus. `docs/tr/` remains a partial
  mirror (11 of 27 sections) and does not yet carry D-026/D-027.

## 2026-08-01 — Production-readiness pass

- Repo restructured: `docs/` (corpus, single source of truth), `site/`
  (generated EN/TR monographs), `research/` (papers, text, manifest), `tools/`,
  `src/` (Phase-2 vertical slice). Git initialized.
- Corpus restored from `/tmp` backup (EN + TR); build made reproducible
  (`tools/build_monograph.py`, `site/index.html` and
  `site/tr.html`).
- 42 duplicate PDFs removed (md5-verified), ~88 MB freed.
- New plane specs: `FEED_INGESTION_SPEC`, `PERSISTENCE_REPLAY_SPEC`,
  `RUNTIME_SCHEDULER_SPEC`, `OPERATIONS_SPEC`; decision register extended
  (D-011..D-016).
- Phase-2 vertical slice (`src/v8/`): tape -> MarketState -> experts ->
  candidate lifecycle -> canonical simulator -> hash-bound lab report;
  synthetic-data tests passing.
- Ontology levels + identity metadata adopted (`V8_CONSTITUTION` rule 13;
  `EXPERT_PROTOCOL` section 1); feature-group `requires:` declarations added.
- Exposure-aware acceptance adopted (rule 16; `CANDIDATE_LIFECYCLE_SPEC`
  section 6); `ExposureBook` guard in the vertical slice.
- `LEARNING_PROTOCOL.md` added; online mutation forbidden (rule 15).
- Complexity budget adopted (rule 14).
- Tape compilation discipline adopted (`DATASET_SPEC` section 5; rule 17).
- V7 `lab/` vendored into `src/v8/simtruth/` (canonical reference simulation
  truth; only import paths rewritten) and V7 `tools/data.py` copied to
  `tools/` (canonical Binance archive -> verified tape builder).
  ENGINEERING-ONLY: V8's simulation authority is not renewed by the copy
  (D-022; OPERATIONS_SPEC section 1).
- Project venv via uv (`.venv`, numpy + pytest); 7/7 tests green.
- Roadmap added (`docs/ROADMAP.md`, Phases 0-7 with evidence gates).
- Agentic-coding pass: `CLAUDE.md` at repo root (read order, commands,
  non-negotiable rules); monograph build now emits a table of contents
  (`<nav id="toc">`) with per-section anchors; `site/archive/` removed
  (backed up); `tools/` reorganized (`build_monograph.py`, `heads/`).
- Stepped runtime (CANDIDATE_LIFECYCLE_SPEC section 6 conformance):
  `CanonicalSimulator` split into `step()` (execution ledger — positions live
  across decision clocks) and `run()` (batch counterfactual); `lab.run()`
  drives a 3-phase loop (enter -> step -> trigger -> evaluate); exposure
  conflicts now fire naturally; rejected candidates keep `NOT_EXECUTED`
  counterfactual outcomes — the executed-vs-rejected selection-bias dataset
  is now measurable; `RiskGate` skeleton added (`src/v8/risk.py`), heat
  policy is an open decision.
- Design-phase encoding (index.html only; code paused at user request):
  `CANDIDATE_LIFECYCLE_SPEC` section 6 extended — two-path execution (batch
  counterfactual attribution vs stepped execution ledger, positions live
  across decision clocks), portfolio heat cap (stop-risk R, fixed clusters,
  reject-not-downsize, D-023), mechanical tradability mask (D-024),
  fractional Kelly cap (D-025); open decisions O-013..O-016 (position
  management, selection bias, learned regime veto, drawdown sizing); evidence
  matrix citation verification (two arXiv ID corrections against the reading
  list; four converging literature gaps).
