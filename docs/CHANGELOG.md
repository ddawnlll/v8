# V8 Changelog

Format: dated, brief, reversible. This log records document and architecture
decisions — never economics. Each entry names the artifacts it changed.

## 2026-08-10 — V8 x Recoverable Regret v0.2, Phase-0 build step 1: golden repair + two portability bugs + multi-symbol dev tape

Three local repairs and one data-plane addition, all prerequisites for the
Phase-0 measurement instrument frozen in `FCR-V8RR-004` (read-only ACCP
evidence chain `RIR-V8RR-001` .. `FCR-V8RR-004`, not committed to `docs/` —
research-session artifacts under `reports/accp/v8-rr-v02-phase0/`).

**1. Golden regression re-pin (`tests/test_golden_backtest.py`).** The golden
was RED at HEAD: `states_hash`/`ledger_hash` had drifted since the last pin
because `marketstate.py` (D-054) and `lab.py` moved, and `_BUILDER_SRC_HASH`
is a whole-file hash bound into every state's `provenance.code_version` by
design. Measured before re-pinning: `data_hash`, `candidate_count` (15) and
`terminal_distribution` (`{CLOSED:12, INVALIDATED:1, REJECTED:2}`) were
UNCHANGED — no Expert, setup, trigger, price or economics decision moved.
Re-pinned `GOLDEN_LEDGER_HASH`/`GOLDEN_STATES_HASH` with a dated comment
recording the invariance proof, per the file's own "do not update silently"
convention.

**2. `AppendOnlyLog` gained a `close()` method (`src/v8/store.py`).**
`tools/vision_backfill.sort_tape` opens a log, reads it, then calls
`os.replace` on the exact path the log's still-open append handle points to.
POSIX permits a rename over an open handle; Windows does not (`WinError 5`),
which was the root cause of the pre-existing `tests/test_funding_wiring.py`
failure (previously misdiagnosed as an environment artifact) and blocked
`--sort` on a freshly downloaded tape outright. `sort_tape` now calls
`log.close()` before `os.replace`. `close()` is idempotent and is the only
new public surface on `AppendOnlyLog`.

**3. `_code_hash()`/`_tooling_hash()` made platform-independent
(`src/v8/lab.py`).** Both keyed their per-file dict on `str(p.relative_to(base))`,
which embeds the OS path separator — the identical source tree hashed
differently on Windows (`experts\base.py`) vs POSIX (`experts/base.py`),
silently breaking rule 9's "outputs bind ... code ... hashes" invariant
across machines. Switched to `.relative_to(base).as_posix()` (same files,
same bytes, a canonical separator in the hash key only).
`tests/test_bugfix_pass.py::test_code_hash_excludes_vendored_simtruth`'s
independent mirror updated to match — it previously split path keys on `'/'`
while `str(Path)` produced `'\\'`-joined keys on Windows, so the mirror's own
`simtruth` exclusion silently no-opped on this platform. No golden hash
depends on `_code_hash()`'s value (`ExperimentManifest.code_hash` is `''` in
every pinned fixture and is not itself asserted), so no other pin moved.
Full suite after all three repairs: 733 passed, 1 skipped (up from 730
passed / 3 failed at HEAD).

**4. Multi-symbol dev tape built (`research/tape/multi-1h-dev/`, gitignored
— reproducible from public archives).** `tools/build_multi_tape.py --symbols
BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,XRPUSDT,DOGEUSDT --start 2025-07 --end
2026-07 --interval 1h --channels kline,funding --download`: 144 Binance
Vision monthly archives (0.03 GB), 0 misses. Symbol set = `risk.py`'s
`DEFAULT_CLUSTERS` (the "btc"/"major" cluster grouping already wired into
`RiskGate`'s heat caps); date range = the existing D-041 dev window,
strictly inside the frozen 2026-07-01 holdout boundary that the builder
itself refuses to cross. Sorted and audited clean: 59,130 rows,
`tape_hash=b9079440e2cc7a03300eb6fc3366baf25d1fc7e3`, 0 duplicate rows,
monotonic, all payload hashes verified, 0 venue-sequence gaps. This is
research/diagnostic data (rule 11, "explore broadly in development") — it
does not amend `DATASET_SPEC` section 6's declared single-symbol
`v8_slice_001` universe, which stays the only canonical dataset for an
economic claim; extending that declaration remains an O-011 registry
decision.
## 2026-08-10 — V8 x Recoverable Regret v0.2, Phase-0 CERTIFIED (D-071)

Continuation of the build-step-1 entry above (golden repair, `AppendOnlyLog.close()`,
`_code_hash` portability, multi-symbol dev tape). This entry closes Phase 0:
`tools/regret.py` (+ `tools/regret_reference.py`) implements the ten frozen
contracts (`FCR-V8RR-004`) and is certified against real command evidence in
`TVR-V8RR-005` / promoted in `PRR-V8RR-006` (both under
`reports/accp/v8-rr-v02-phase0/source/`). Full decision text: `D-071`.

**Instrument.** A READ-ONLY evaluator over a completed `Lab` store: joins
`CandidateSnapshot`s (re-derives `episode_key`, never a stored edge), asserts
PIT lineage, reconciles `Replay(C, a_actual, M)` against the observed ledger,
generates a per-Candidate `LegalActionManifest` (`NO_TRADE` + the actual
action seeded first + a small declared `target_r` x `expiry_bars` grid;
`pyramid_add_rules` and `direction` structurally excluded), replays every
legal action through the SAME `CanonicalSimulator` the run used (refusing —
`UNDEFINED_FUTURE` / `CENSORED` / `NOT_EVALUABLE_ACTION` / `NO_ENTRY` — rather
than accepting a degenerate-future or censored cell as a number), writes the
cube (`cube.jsonl`) and the gap (`regret.jsonl`, ties reported never broken,
abstains whenever any potentially-maximizing cell is not fully observed).
Phase 0 computes NO statistics; every number is `MODEL_DERIVED` and carries
no economic authority.

**Certification evidence, all real command output.** Golden synthetic
fixture (15 candidates): reconciles 12/12 exact at 1e-12, 0 PIT violations.
Real 12-month single-symbol BTCUSDT 1h store (1,532 candidates, built from
the freshly downloaded 6-symbol tape, trimmed 3 days before its true end to
stay inside the tape's own funding-coverage boundary): reconciles 754/754
exact at 1e-12, 0 deviation on every field, 0 PIT violations — closing the
FCR's own flagged "measured only on synthetic data" gap. The v0.2 invariant
`hindsight >= actual` holds with zero negative gaps across 543 COMPUTED
candidates combined. An independently-derived reference walk (written from
`SIMULATION_TRUTH_SPEC` text, imports nothing from `v8.simulator`) agrees
with the canonical simulator on 150 Hypothesis-generated randomized paths.
Five fault-injection cases (TP-shortened axis attribution, cost-doubling
isolation, direction-flip structural illegality, habitat-randomization
structural non-claim, missing-evidence explicit refusal) behave as
specified — the last two by correctly REFUSING to claim something Phase 0
has no evidence for, not by localizing them.

**One more additive `src/v8/` change.** `Lab.run()` now also persists
`report.json` alongside `manifest.json` (not part of `ledger_hash`): a
completed store previously could not recover its own `risk_gate_hash`
without re-running the lab, which a read-only evaluator must never do.

**Suite:** 751 passed, 1 skipped (18 new tests: `test_regret_phase0.py`,
`test_regret_faults.py`, `test_regret_reference.py`), up from 730 passed / 3
failed at HEAD before this session.

**Two honest limitations carried into Phase 1, not silently resolved.**
`funding_r`/`gross_utility` are `None` (never fabricated as `0.0`) on any
store whose manifest declares nonzero funding or whose tape carries a
funding channel, because `CounterfactualOutcome` does not persist
`funding_paid_r` and extending it would move `sim.hash()` and re-pin every
golden for no semantic gain — Phase 1 must read `net_utility` as
authoritative and not attempt a funding breakdown from the cube. Only
BTCUSDT was reconciled on real data this session; the other five downloaded
symbols are validated identically (not differently) during Phase 1's
per-symbol runs (`v8.lab.Lab`'s bar-driven loop is single-instrument by
design, `src/v8/lab.py:369-374`).
## 2026-08-10 — V8 x Recoverable Regret v0.2, Phase 1+2: a replicated (not yet recoverable) `mean_legal_hindsight_gap` finding (D-072)

`tools/regret_phase1.py` (descriptive join, label `MODEL_DERIVED_DESCRIPTIVE_NOT_YET_GATED`,
zero statistics) and `tools/regret_phase2.py` (systematicity discovery per
`FCR-V8RR-007`, reusing `src/v8/statistics.py` in full — zero new estimator
code) ran over the certified Phase-0 output for all 6 downloaded symbols
(9,218 Candidates). 12 of the 72 declared discovery slices reached
`CANDIDATE_SYSTEMATIC` on `mean_legal_hindsight_gap` (vs 3.6 expected under
the null at family alpha 0.05) — `trend_pullback` LONG and `failed_breakout`
SHORT, each on all 6 symbols, never the mirror direction, never on
`mean_actual_vs_no_trade`. All 12 confirmed as `SYSTEMATIC_FINDING` on the
untouched second half of the dev window, queried exactly once, with stable
point estimates both halves (`trend_pullback` ~0.5-0.7R, `failed_breakout`
~1.0-1.2R). **Epistemic status, stated explicitly because it is easy to
overclaim here:** this is evidence that value is being left on the table
inside the represented Candidate/action universe, under a costed, versioned,
reconciled Replay Model, and that the pattern replicates chronologically. It
is NOT evidence that the gap is recoverable — v0.2 section 5.3's
`HindsightOpportunity != RecoverableOpportunity` applies without exception,
and V8_CONSTITUTION rule 12 still blocks any profitability or validated-
execution claim. Full decision text and numbers: `D-072`. Evidence:
`reports/accp/v8-rr-v02-phase0/source/ECR-V8RR-008.accp.yaml`,
`tmp/phase2/*.json(l)` (real command output, this session).
## 2026-08-10 — Confluence experiment: Fib + RSI + Bollinger (D-076)

- **D-076 — `fib_rsi_bb_confluence` admitted as an exploratory dev-window
  family** (mechanism `confluence_reversion_continuation`). One new
  `src/v8/experts/` module; two variants evaluated in one run — `a` STRICT
  (all three legs point the same way), `b` MAJORITY (at least two of three).
  Each leg is a registered family's idiom verbatim: the Bollinger 2-SD fade
  zone (`bollinger_reversion`), the Wilder-RSI dip-and-recover
  (`rsi_stoch_reversion` variant a), and the fib retracement reclaim at
  **0.786** (`fib_retracement_continuation`). The deep ratio is a structural
  choice, not a fit: a fade-zone close (below the 20-SMA's lower band) can
  only co-occur with a retracement level that sits BELOW that band; of the
  standard ratios only 0.786 does so (the co-occurrence was computed before
  the experiment ran). Geometry is the family default 1R:1R:8bar with
  `atr_ref`; the frozen 78.6% level and the frozen 3-SD band are the
  post-entry invalidation refs (`prior_*_ref` + `lower/upper_3sd_ref`, the
  D-042 pattern). Registry FORMALIZED; `variants_evaluated` [a, b];
  `search_universe_size` 2.
- Runner `tools/run_fib_rsi_bb_confluence.py`: builds a single-symbol SOLUSDT
  tape inside the dev window (`build_multi_tape` REFUSES >= 2026-07),
  runs both variants with tape-driven funding and a 10-bps round-trip taker
  cost, and reports per-variant + pooled after-cost stats beside a zero-cost
  reference row joined by candidate_id.
- **Result (dev-window, SOLUSDT 1h, 2025-07..2026-06, 8760 bars, exploratory —
  not a registered test):** variant `a` fired **once** (0.011% of bars,
  invalidated before entry, 0 executed) — the strict triple confluence
  essentially never co-occurs on this tape. Variant `b` fired 159 times, 33
  executed: win rate 39.4%, mean net_R **-0.253** after 10 bps (detrended
  -0.254; 90% CI [-0.471, -0.062], entirely negative), profit factor 0.59,
  equity -8.3%, max drawdown -9.8%. At **zero cost** the mean is still
  **-0.158 R/trade**: the signal itself has negative expectancy; cost adds
  ~-0.095 R. The lab's feasibility note records breakeven win rate 0.547 >
  realized 0.394. Verdict stays NO_ECONOMIC_CLAIM (no authority receipt,
  rule 12). The confluence does not beat its own relaxation here, and neither
  clears cost.
- **D-026 hardening (correctness):** `lab._geometry_version` now also
  excludes the frozen band refs `lower_3sd_ref`/`upper_3sd_ref` from episode
  identity — they are data-dependent (a stable setup must not change key
  across decision clocks). Without it the confluence's 179 candidates carried
  179 distinct geometry hashes and dedup could not fire; after the fix the
  run dedups to 160 candidates. Backward-compatible: no other family uses the
  band-ref keys.
- Tests: `tests/test_expert_fib_rsi_bb_confluence.py` (16 tests: crafted
  STRICT LONG/SHORT tapes, MAJORITY firing/abstain, vote-rule unit tests,
  episode-key separation, still_valid composition, registry/lab smoke);
  registry gate green (28 -> 29 entries).
## 2026-08-09 — Hot-path pass: 3.4x less CPU for byte-identical output (D-075)

The diagnostic was saturating every core for minutes per run. Profiled rather
than guessed (cProfile, one 540-bar BTCUSDT cell):

| | before | after |
|---|---|---|
| single cell (in-process) | 72.6s | **17.4s** (4.2x) |
| 2 symbols x 2 timeframes, 60d, `--processes 4` | 102.5s wall / 245.4s CPU | **29.2s wall / 71.2s CPU** (3.4x) |

Four wastes and one latent bug:

1. **`_median_atr` recomputed 202,000 times** — 54.3s of 72.6s (75%), and the
   source of 287M dict lookups. It is a pure function of the frozen draft set
   and was being rescanned and re-SORTED once per null draft. Memoised.
2. **`dataclasses.replace` on the `OpenPosition` hot path** — 3.9M calls,
   20.4s of the remaining 28.0s (73%), under 57M `getattr`s. `step()` chains
   up to three per bar. Replaced by `simulator._evolve`, which populates a
   fresh frozen instance directly; `OpenPosition` has no `__post_init__`, no
   validation and no `__slots__`, and the equivalence is pinned field-by-field
   against `dataclasses.replace` in `tests/test_perf_hotpaths.py`.
3. **`_post_exit_max` computed for null walks** that never read it — 24 bar
   reads x ~200k walks per cell.
4. **The tape was re-parsed per cell** — ~395k JSON lines, once per
   (symbol, timeframe). Now parsed once per process.

5. **A latent correctness bug, found while profiling.** The walk cache was
   keyed on `id(draft)`. `id()` is unique only among LIVE objects, and a null
   draft is freed immediately after its walk, so CPython hands the same
   address to the next one — a (recycled id, same `entry_idx`, same geometry)
   key could return a walk taken in the OPPOSITE DIRECTION, quietly
   contaminating `always_long` / `always_short` / `random_entry`. The cache
   also grew unbounded (97,263 entries against 1,387 real drafts). Entries now
   store `(draft, result)` and verify identity on hit; null drafts bypass the
   cache entirely. This is a correctness fix, not a speed trade.

**Output identity is the gate, and it holds twice.** The lab economics dump
(every outcome's `net_r`/`endpoint`/`entry_price`/`risk_unit_price` plus the
whole `LabReport` minus hashes) is byte-identical to the pre-change baseline;
and the diagnostic's own aggregate `net_R_mean` and all 22 decision-table rows
are identical before vs after on `BTCUSDT-1h`. Only `ledger_hash` moved,
because `_SIMULATOR_SRC_HASH` binds the module source — re-pinned with the
evidence recorded in the golden test.

No numpy, no new dependency, no change to the concurrency model — those stay
unregistered under the D-031 baseline. 749/749 tests pass.
## 2026-08-09 — Per-Expert scenario correctness audit (rule 10 contract tests)

`tests/test_expert_scenarios.py` (new, 18 tests): hand-crafted bar sequences
with a known correct fire/no-fire/geometry outcome for the three original
pilot Experts (`trend_pullback`, `failed_breakout`, `liquidity_sweep_reclaim`)
— positive setups, negative/no-setup mirrors, strict-inequality boundary
cases (hand-built `MarketState`, bypassing `build_state`), the shared
<20-bar habitat gate, `still_valid` invalidation, and a cross-Expert
metamorphic invariant (every `CANDIDATE` an Expert emits over synthetic
noise must independently re-derive from its own documented setup predicate
against the raw `history` tuple). Contract-only per rule 10: no `Lab`, no
economic claim, no `src/v8/` change. Superseded as the primary diagnostic
instrument by the already-existing `tools/diagnostics.py` report center
(9-section per-Expert forensics across all 27 registered Experts, run
2026-08-07/08 — see `.audit/RESULTS.md`); this file remains a narrower,
faster-running correctness check on the three original pilots specifically,
independent of that instrument.


## 2026-08-09 — Diagnostic integrity pass: the report could not falsify its own exit diagnosis

Four defects, found by auditing the 2026-08-08 multi-cell report against its
own numbers. None of them changes an Expert, a geometry or a verdict's
authority (still `NONE`); they change what the instrument is capable of
measuring. Decisions D-067..D-070.

**1. The exit grid was one-dimensional (D-068).** `EXIT_VARIANTS` moved the
take-profit while pinning the shipped 8-bar expiry: `tp_4r` = `{'tp': 4.0}`.
The report's own horizon section says mean favorable excursion reaches ~4R
near 48 bars, so that cell converted targets into expiries and its loss
carried no information about a 1:4 geometry. "Exit is not the problem" was
therefore unfalsifiable. The grid is now a cross of `EXIT_TP_GRID` (1/2/3/4R,
no-TP) x `EXIT_EXPIRY_GRID` (8/24/48/96) = 20 cells, with `no_sl` and
`trail_1atr` kept OUTSIDE the cross as structural probes. Shape taken from
Katz & McCormick's Standard Exit Strategy (Encyclopedia of Trading Strategies,
2000, ch. 13), which moves target and horizon together — the shape only; no
geometry is adopted.

**2. Selection was reported as if it were a result (D-068/D-069).** The max of
the grid was printed as `best_exit` with no search size and no correction. It
now travels as `exit_cross` with `n_cells_searched`, a naive p and a
Bonferroni-corrected p, and the portfolio section reports both the per-expert
max (labelled a selection-inflated upper bound) and a single fixed cell chosen
once for every expert — the difference between the two is the selection.

**3. The decision table contradicted section 8 (D-069).** Section 8 refuses to
score a segment cell below its 95%-CI sample floor; the decision table
simultaneously emitted "Add regime filter" from an n=19 cell. `_main_problem`
had no sample gate at all. Replaced by `_observations`, where every entry
carries `supported: bool` from the same floor (`_min_n_for`), and an
unsupported observation is printed but can never label a row or move a
verdict. The prescriptive action column is gone: naming the best corner of a
44-cell search IS the selection (Aronson, *Evidence-Based Technical Analysis*
2007, ch. 6), so the column now states the measured quantity and its support.
A regression test asserts the old strings never come back.

The first run under the new table exposed a fifth defect the first four did
not close: on `BTCUSDT-4h`, `candlestick_reversal` reached **KEEP on n=10**
(a 100th-percentile random-null result) while its own observation column read
"sign-permutation p=0.070 — not distinguishable from sign noise". The verdict
gate had only `n >= 10`. `KEEP` now also requires `n >= _min_n_for(nets,
zero_cost_edge)` — enough sample to resolve the edge it claims — and
under-powered candidates are held at `INVESTIGATE` ("not enough yet"), never
demoted to a failure.

**4. Coverage was invisible (D-069).** 48 `Expert` subclasses are defined,
27 are registered, and 5 registered experts produced zero setups on the
window. Neither gap appeared anywhere, so a row labelled `donchian_breakout`
read as a statement about the family while measuring variant `a` — which is
long-only by definition, making its SHORT n=0 look like a broken direction.
New section C reports zero-setup experts and unregistered variant classes.

**Cost form (D-067).** `round_trip_cost_r` is denominated in R and is
therefore invariant to the R unit: widening the risk unit rescales stop and
target but leaves the charge untouched, so "widen R to dilute the cost" is a
no-op in the model and an R-widening experiment could not be measured.
`CanonicalSimulator` gains an optional `round_trip_cost_bps`, resolved at one
point (`cost_r(entry_price, unit)`) that every `net_r` site now calls.
Flat-R remains the default and is byte-identical — verified by diffing every
outcome's `net_r`/`endpoint`/`entry_price`/`risk_unit_price` and the whole
`LabReport` minus hashes, before vs after: identical. Only `ledger_hash`
moved, because `sim.hash()` now binds the cost form.

**Determinism (D-070).** Found while wiring the above: `run_multi`'s parallel
branch seeded `seed + i` while the sequential branch used a bare `seed`, so
`--processes 1` and `--processes 4` disagreed on every cell but the first.
The job list is now built once by a pure `plan_cells` and seeded by position.

- `src/v8/simulator.py` — `cost_r()`, `round_trip_cost_bps`, hash binds form
- `src/v8/schema.py` — `RunManifest.round_trip_cost_bps`
- `src/v8/lab.py` — per-episode realized cost feeds RM-11's `w_min`
- `tools/diagnostics.py` — exit cross, `_observations`/`_min_n_for`,
  `_coverage`, `plan_cells`, `--cost-bps`
- `tests/test_cost_form_and_exit_grid.py` — 23 new contract tests
- goldens re-pinned with the byte-identity evidence recorded in-file

733/733 tests pass.

## 2026-08-08 — Dev multi report: 100% of the info in ONE HTML

`tools/diagnostics.py` matrix report (`--symbols`) now embeds EVERY cell's
COMPLETE report — 9 sections + per-expert forensics + MarketState audit +
charts — in a single `report.html`, not just the cross-symbol verdict matrix
(which was a summary of badges, with the full per-cell reports stranded in
separate `out/{symbol}-{tf}/report.html` files). A nav menu anchors to each
cell's embedded report.

- `render_html` gained `fragment: bool = False` — `fragment=True` returns the
  body WITHOUT the `<html>/<head>/<style>` wrapper, so a parent document that
  already carries `_CSS` can embed a cell report (nested HTML was invalid).
  Default is byte-identical to the legacy self-contained report.
- `_run_cell` returns the full cell `report` + `trades` (they were already
  computed, previously discarded); `run_multi` keeps them for the renderer.
- `--allow-surface` now flows `run_multi -> _run_cell -> DiagnosticEngine`
  (it was accepted but never forwarded, so §6 exit surface never ran per cell).
- `report.json` (multi) stays an aggregate-only view via
  `_jsonable_multi_report` — the bulky per-cell reports/trades are already on
  disk under `out/{symbol}-{tf}/`, so the JSON is not bloated.
- Dead-code cleanup: two shadowed `main()` definitions (legacy single, legacy
  matrix) removed; the unified CLI is the one entry point.
- Determinism: cell order is the fixed (symbol, timeframe) enumeration; the
  only wall-clock bytes in the HTML are the `generated_at_utc` provenance
  stamp (report metadata, outside the decision path) — pinned in the test.

Tests: `test_multi_dev_html_embeds_every_cell_full_report`,
`test_multi_dev_html_is_deterministic`, `test_multi_allow_surface_reaches_cells`,
`test_render_html_fragment_backward_compat`. **710/710 tests pass.** Verified on
`research/tape/multi-1h-4y` (2 symbols × 1h, 60-day span): `report.html`
272K carries both cells' full reports; single mode still writes its 5-file set.

Artifacts: `tools/diagnostics.py`, `tests/test_diagnostic.py`,
`.audit/diagnostic/dev-html/`.

## 2026-08-08 — Total-pipeline perf pass + single-file report center

Perf pass across the decision path and the report tooling. Every
decision-path change is VALUE-EQUIVALENT (tests/test_state_cache_identity.py
pins cached == uncached on every bar; tests/test_perf_fastpaths.py pins the
fast hashing/serialization against the reference semantics); the golden
backtest re-pinned ledger/states hashes because `code_version` and `code_hash`
moved, with candidate_count/terminal_distribution/data_hash unchanged
(tests/test_golden_backtest.py comment documents the re-pin).

Decision path (src/v8/):
- marketstate.py: per-feature input-lineage digests built from precomputed
  row bytes (`_slice_digest`) instead of re-json-dumping payload dicts per
  feature per bar; `closed_digests`/`manifest_digest` are now incremental
  hashers (O(N²) full-prefix re-hash -> O(1) amortized per bar, byte-identical);
  `project_state` gained a static `projection_allowed_keys` superset so a
  projection is one frozenset membership per key instead of a per-key
  `feature_interval` call.
- lab.py: projection specs (allowed keys/depths/intervals) hoisted once per
  Expert per run; `record_dict(..., event_id=state.state_id)` skips the
  auto `sha1_hex` of the full state record that the caller overwrote anyway.
- schema.py: `record_dict` uses `_asdict_fast`, a dataclasses.asdict
  equivalent without per-call `fields()`/deepcopy (tuple-preserving, so
  `== asdict` holds on CPython 3.14).
- equity.py: `risk_of_ruin` draws each simulated life with one
  `random.choices(k=n)` call instead of n `choice` calls (~10k x n draws in C).
- store.py: unchanged semantics; the rejected incremental-hash design is
  pinned as a regression test (comma-before-first bug) in
  tests/test_perf_fastpaths.py.

Measured: 8760-bar x 3-pilot lab run 46.9s -> 16.6s (~2.8x); 1500-bar x
27-expert 16.4s -> 8.0s. Full suite 706 passed.

Report tooling (tools/, consolidated 2026-08-08):
- NEW `tools/diagnostics.py` is the single report center: the diagnostic
  engine (9 sections) + per-expert forensics + the multi-symbol matrix runner
  + the self-contained HTML renderer now live in ONE file, per the report-
  center directive ("everything in one file, no multi"). `tools/diagnostic.py`,
  `diagnostic_report.py`, `forensics.py`, `multi_diagnostic.py` are thin
  re-export shims for backward compatibility; the CLI takes `--symbols` to
  opt into the matrix report (formerly multi_diagnostic).
- diagnostic.py engine: `_simulate` walk memoization — one bar walk per
  (draft, entry, geometry) serves every cost/funding variant (Section 2
  ablations, forensics cost sweep, the repeated full-set sims). 306,809
  `_simulate` calls collapse to 91,853 distinct walks (~3.3x) on an 8760-bar
  run; net_r derivation is bit-exact for the scalar funding path
  (`_simulate` == `_simulate_full` pinned in tests/test_diagnostic.py).
  `_detect` hoists the per-expert projection spec (sort/closure/declaration
  computed once, not per bar).
- vision_backfill.audit_tape gained an optional `rows=` param; monitor_tape
  passes its already-parsed rows so a --schema cycle parses the tape once,
  not twice.

## 2026-08-07 — Equities data-authority survey (O-026 refinement)

The deferred-equities open decision (O-026) gained an empirical source survey
instead of an assumption. Method: live endpoint tests (İş Yatırım API returned
THYAO daily OHLCV back to 1997), Wayback snapshots (stooq bulk archives),
official docs (Massive/Polygon flat files, BIST DataStore), GitHub API;
WebSearch returned nothing in this environment, so DuckDuckGo HTML, direct URL
fetches and Wayback were used as fallbacks. **Finding: no source — free OR paid
— offers rule 9's checksum-verifiable immutable archive.** NASDAQ's closest
candidate is Massive (ex-Polygon) Flat Files (official SIP daily files since
2003, bulk + immutable, but paid ≥ $29/mo, no published checksums — only S3
ETags) or stooq bulk ZIPs (checksumless); BIST's only official channel is
DataStore (paid, contractually "Confidential", no checksum, no accuracy
guarantee) and the free İş Yatırım API violates every rule-9 axis (unofficial,
mutable). So the O-026 admission condition (source authority binding) is
currently unmet for both venues — equities stay a documented research
direction (D-065), never a canonical dataset.

Artifacts: `docs/decisions/OPEN_DECISIONS.md` (O-026),
`docs/tr/OPEN_DECISIONS.md` (O-026), `docs/CHANGELOG.md`.

## 2026-08-07 — WHY-IS-IT-NEGATIVE diagnostic engine (tools/diagnostic.py)

A read-only diagnostic engine that EXPLAINS the lab's negative economics
without fixing them. It produces diagnostics, never decisions:
`AUTHORITY: NONE — DIAGNOSTIC ONLY` on every report. Spec: 9 sections
(identity + R-denominator census, cost census, zero-cost ablation, null
baselines, path statistics, horizon sweep, exit-parameter surface, entry
timing, simulator invariants) + a verdict enum
(`MECHANICAL_FLOOR | COST_DOMINATED | NO_EDGE | EXIT_MISSPECIFIED |
SIMULATOR_INVALID | INDETERMINATE`), each cited to its evidence.

V8 adaptations recorded in the manifest: lives in `tools/` (a `src/v8/` module
would move the decision-path code hash, D-032); the entry set is re-detected
from the tape (drafts are not persisted) at birth+lag with one fixed
convention, and every counterfactual reuses it; ALL simulation goes through
`CanonicalSimulator.step()` geometry overrides (no re-derived barrier/gap/cost
formulas); V8 models fee+slippage as ONE flat `round_trip_cost_r`; 1h-bar
horizons (15m unrepresentable); no liquidation model (stopped-before-h =
shipped-SL stop); `trades.jsonl` not parquet (D-031). The engine never writes
to a store/registry/authority path — a foreign write raises
`DiagnosticWriteError`.

**First run on the real dev tape** (btcusdt-1h-12m, 2500 bars, all 27 experts,
cost 0.07): verdict **MECHANICAL_FLOOR** — the shipped signal is
indistinguishable from random entries (actual −0.0618R inside the random-entry
null [−0.136, −0.030], percentile 78.5%). Supporting numbers: gross edge
+0.0082R vs flat cost 0.07R (**cost is 8.5× the raw edge**); frictionless
+0.0082R (break-even); mean trade duration **3.7 bars** (median 3, p90 8);
holding to 4-5 days would have been WORSE (−0.19 to −0.25R); **early-TP: 79% of
target-exits continued >2R after exit (mean +4.5R)** — the 1R target clips a
real favorable tail; early-SL: 33.5% of stops saw >0.5R favorable first;
intrabar ambiguity 144 trades with a 1.79R optimistic/pessimistic spread;
no entry-timing problem (mark-out ≈ 0 bps). The verdict is a diagnostic
finding, not an economic claim (authority still NONE).

**Automatic HTML report + charts.** Every run also writes a self-contained
`report.html` with inline-SVG charts (stdlib-only — no matplotlib/JS/CDN):
verdict banner + KPI cards, a horizon-sweep line chart with the actual mean
duration marked, a cost-census bar chart, an ablation bar chart, a
"actual vs random-null band" chart, an exit-reason bar chart, net_R/MAE/MFE/
duration histograms from the per-trade ledger, an entry-timing mark-out line
chart, segment tables and the invariants block. Deterministic — a given run
always produces byte-identical HTML. Renderer: `tools/diagnostic_report.py`.

**Expert forensics layer** (`tools/forensics.py`): the actionable answer to
"which strategy is salvageable, which is trash?". Every expert gets a
leaderboard row (n, gross/net/zero-cost edge, PF, winrate, max drawdown,
LONG/SHORT split), a cost sweep with its **breakeven cost**, an exit-variant
sweep (no-TP / no-SL / 2R·3R·4R-TP / time-24 / trailing), a sign-permutation
p-value, a per-expert random-entry null, a bootstrap 95% CI, regime
(vol/trend), time-of-day and window-split breakdowns, a TP-robustness metric,
and an automated **KEEP / REPAIR / HARD_REPAIR / INVESTIGATE** verdict with a
cited main problem and an action. The vocabulary has no "kill": an expert is
never deleted by a diagnostic — `HARD_REPAIR` means it is broken (no edge even
frictionless) and needs a fundamental rebuild. The verdict is anchored on the
ZERO-COST edge (an expert with a real frictionless edge killed by cost is
REPAIR, not HARD_REPAIR) and a KEEP needs n + positive frictionless edge +
distinguishable-from-random-null (the spec's "most critical filter"). The
report's top carries the strategy decision table; each expert has a
collapsible `<details>` drill-down; the report closes with a portfolio
conclusion (verdict counts, strongest/weakest, dominant failure, long-vs-short,
exit-vs-entry, recommended next experiment).

**Per-expert MarketState (D-054) verification.** The report now states and
verifies that every expert evaluates its OWN projected MarketState view: the
canonical state filtered to the expert's declared intervals + `requires`
feature groups (an expert never sees another expert's undeclared features).
The engine records a per-expert state audit (intervals, groups, depth, view-vs-
canonical feature count) and verifies the projection withheld every undeclared
group (`view_groups_verified`). On the dev tape all experts declare the base
interval (1h) only, so the diagnostic data is 1h-barred and the per-expert
"custom MarketState" is the group projection on that 1h state — stated in the
manifest (`base_interval`, `multi_interval_experts`,
`per_expert_state_projection`).

**Multi-symbol × multi-timeframe** (`tools/multi_diagnostic.py`): the
single-symbol report answers "why is this strategy negative on BTC 1h?"; this
layer answers "does any edge survive OTHER symbols and OTHER timeframes?". Each
(symbol, timeframe) cell — e.g. 4 symbols × {1h, 4h} over one shared calendar
span — runs the full engine (aggregate + per-expert forensics) in parallel and
writes its own report dir; the aggregate report carries a cross-symbol verdict
matrix (experts × cells), a consistency analysis (robustly salvageable experts
vs experts that FLIP across symbols — the anti-overfit filter), and an
aggregate portfolio conclusion. The 4h/1d cells aggregate the same calendar
bars via `v8.interval.aggregate` (incomplete buckets dropped; no funding
channel on the aggregated cells, stated in every manifest).

Tests: `tests/test_diagnostic.py` — the spec's 6 synthetic fixtures each
produce its known verdict (not-NO_EDGE / COST_DOMINATED / MECHANICAL_FLOOR /
EXIT_MISSPECIFIED / SIMULATOR_INVALID / identity-stops-the-engine) + a
write-guard test + a report.html render test. **693/693 tests pass.**

Artifacts: `tools/diagnostic.py`, `tools/diagnostic_report.py`,
`tests/test_diagnostic.py`, `.audit/diagnostic/real/` (first real-tape
report, incl. `report.html`).

## 2026-08-07 — Universe scope: equities (NASDAQ/BIST) deferred as a research axis (O-026, D-065)

Scope proposal to add stock equities as dataset sources was evaluated against
the constitution and recorded, not implemented. Equities are structurally
different from the locked Binance USD-M universe — no funding/mark/index/premium
tapes, a session calendar with gaps and corporate actions, a different
cost/authority model — so the proposal is a NEW research axis (O-026), not an
O-011 venue extension. Decision (D-065): the universe stays locked until the
Phase-4 base-case gate is measured; data-plane exploration may proceed in
parallel as research-only, but no equities tape may become canonical and no
preregistration may name it until a surviving family replicates cross-asset
under its own multiplicity controls and rule 9 source authority is met (a hard
constraint today — NASDAQ free archives lack checksum-verified immutability;
BIST requires a commercial provider or an authority-inadmissible scraper).

Artifacts: `docs/decisions/OPEN_DECISIONS.md` (O-026),
`docs/decisions/DECISION_REGISTER.md` (D-065), `docs/CHANGELOG.md`.

## 2026-08-07 — Audit-fix pass: 12 reproduced defects (issues #61-#72)

The adversarial audit of 2026-08-06 filed 12 issues. Each was reproduced on
the working tree with a deterministic probe (`.audit/repro/`; 12/12 confirmed)
and fixed. The fixes are behavioral (ledger-changing), so the golden hashes
re-pinned (data_hash, candidate_count and terminal_distribution UNCHANGED; see
`tests/test_golden_backtest.py` re-pin note).

**Entry is not entry: `PENDING -> TRIGGERED` is gated on a frozen trigger**
(#62/#67). `risk_geometry` gains a normative trigger contract
(`trigger_ref` absolute price + `trigger_side` CLOSE_ABOVE/CLOSE_BELOW;
`schema.py`). `lab.py` PHASE 2 evaluates the book's close-confirmation
predicate before triggering; an unconfirmed candidate stays PENDING and is
re-checked each bar until it fires, invalidates, or the epilogue expires it.
`candlestick_reversal` (Ch14.2 p556) is the pilot and now declares
`trigger_side`; the pre-fix unconditional path entered 16/27 candlestick
candidates whose close had NOT confirmed beyond the trigger. Unconditional
experts keep `entry: NEXT_BAR_CLOSE` (no `trigger_ref` -> no predicate).
Artifacts: `src/v8/lab.py`, `src/v8/schema.py`,
`src/v8/experts/candlestick_reversal.py`.

**Structural stop: `stop_ref` is the static stop when declared** (#63). The
simulator placed the stop at `entry ± stop_r × ATR` even when the expert froze
the structural level (swept extreme / pattern level). `step()` now uses
`risk_geometry['stop_ref']` as the static stop when present; `stop_r × unit`
is the fallback. Measured pre-fix: 33/33 candlestick drafts had the ATR stop
0.44R (mean) from the structural level; 37.3% of executions were stopped by
adverse excursion alone. Artifacts: `src/v8/simulator.py`.

**Geometry invariants fail closed** (#70). `simulator.validate_geometry()`
rejects non-positive `target_r`/`stop_r` and `expiry_bars < 1` at `step()` and
`run()` entry — a `target_r=-1` previously booked a −1.07R loss as a TARGET
win. Defense-in-depth on top of the experts' own guards.
Artifacts: `src/v8/simulator.py`, `tests/test_audit_fixes.py`.

**Windowed pre-entry invalidation fallback** (#66). The all-bars
`prior_high`/`prior_low` are UNBOUNDED prefix extremes (marketstate), so an
invalidation tested against them was dead code for the 6 experts that freeze
no ref (measured: 7 fires across 2,067 drafts). The lab's fallback now uses a
32-bar windowed extreme (the frozen-ref convention) so the gate is meaningful
for every expert. Artifacts: `src/v8/lab.py`.

**Contention tie-break is the candidate's episode_key hash** (#68). Same-bar
same-direction slot races used to be decided by alphabetical `expert_id`
order — measured 295/303 (97.4%) contended slots won by the alphabetically
first expert, and the executed subset was 1.83× worse than the average setup.
PHASE 1a now iterates in candidate-hash order: deterministic, economically
neutral, and NOT a ranker (rule 6/14 — the implicit ranker is removed, not
formalized). Artifacts: `src/v8/lab.py`,
`tests/test_admission_contention.py`.

**Feasibility notes surface in the report** (#64, #69). The report now carries
an RM-11 note when the cost-degraded breakeven win rate exceeds the realized
win rate, and an excess_cost feasibility note when the cost gate fires
(previously the excess-cost rejection was silent beyond
`rejection_distribution`). Artifacts: `src/v8/lab.py`.

**Synthetic tape continuity variant** (#72). `make_synthetic_tape` gains
`continuous=True` (open = prior close ± small move) — the legacy default
fabricated TR > (H−L) gaps on ~73% of bars vs ~0.6% on the real tape. The
legacy default stays byte-identical (pinned golden/contract tests); flipping
it is D-064. The golden-hash mismatch the audit filed was already resolved on
the working tree (re-pinned, `1 passed`). Artifacts: `src/v8/synth.py`,
`tests/test_audit_fixes.py`.

**Recorded, not behavior-changed** — #61 (cost 10.9× the raw edge; the
cost/edge feasibility ratio), #71 (gap asymmetry, a 3.30R conservative budget,
now documented in the SIMULATION_TRUTH_SPEC area of the changelog), #65
(literature-condition table for `failed_breakout`: 2/10 implemented; the rest
are OPEN_QUESTION/REJECTED_OPTION). See DECISION_REGISTER D-057..D-064 and
OPEN_DECISIONS O-024.

Artifacts: `docs/CHANGELOG.md`, `docs/decisions/DECISION_REGISTER.md`,
`docs/decisions/OPEN_DECISIONS.md`, `.audit/BASELINE.md`,
`.audit/repro/*` (repro scripts + evidence), `tests/test_audit_fixes.py`.

## 2026-08-07 — Single-process multi-tape driver + funding-interval audit fix

`tools/build_multi_tape.py` spawned one subprocess per archive, and every
per-archive provenance write re-read and re-hashed the whole growing tape —
O(N²) in rows, ~80 min of CPU for a 960-archive grid. The driver now imports
vision_backfill's functions directly, opens ONE append-only log (the dedup
inbox is built once), skips archives already recorded with the same zip
sha256, and writes provenance once at the end (atomic temp + os.replace). A
corrupt source.json is rebuilt from the on-disk zips + their `.CHECKSUM` files
— the revision guard is re-armed from the authoritative checksums, not
silently disarmed. Measured: the full 960-archive grid (10 symbols x 48 months
x 2 channels) rebuild finished in ~7 s (was 1 h+).

`audit_tape` false-flagged funding settlements that straddle a venue schedule
change: the gap from the previous settlement is governed by the PREVIOUS row's
declared `funding_interval_hours`, not the current row's. The real SOLUSDT
2022-11 archive hit exactly this (a 4h transition gap flagged against the new
2h schedule). The tolerance now uses the previous row's interval; a genuinely
missing settlement under a steady schedule still flags (regression-tested).

The `research/tape/multi-1h-4y` dataset is now complete: 960/960 archives,
394,545 rows, 10 symbols x 48 months x (kline + funding), provenance rebuilt
atomically, sorted to replay order, and audit-clean (monotonic, venue_gaps 0,
duplicate_rows 0, payload hashes verified).

Artifacts: `tools/build_multi_tape.py`, `tools/vision_backfill.py`,
`tests/test_build_multi_tape.py`, `tests/test_tape_audit.py`,
`research/tape/multi-1h-4y/`.

## 2026-08-07 — AppendOnlyLog parsed-log cache (no contract change)

`AppendOnlyLog.read()` re-read and re-parsed the entire JSONL on every call,
and `hash` was `sha1_hex(self.read())` — a full re-parse followed by a full
re-serialization of the whole record list. One lab run touches the logs 17
times (4 emptiness probes, the post-loop report scans, and five `hash`
properties bound into `ledger_hash`), which measured 5.87 s of a 39.2 s run on
the 8,760-bar dev tape (14% of wall).

`read()` now caches the parsed list and `hash` memoizes its digest; `append()`
invalidates both. The log is append-only and the instance owns the sole write
handle, so the file cannot change behind the cache. `append()` invalidates
rather than splicing the record in, because the stored form is the record's
JSON round-trip (tuples become lists) and splicing would let `read()` disagree
with the file. `read()` returns a shallow copy so callers keep the previous
"fresh outer list" semantics; the record dicts are shared and documented
read-only (every current caller iterates, filters or `sorted()`s).

PERFORMANCE ONLY — no contract, schema or decision changed. Measured on the
8,760-bar dev tape with 27 Experts, 3 runs each: 39.2 s → 36.7 s (1.07x);
the log-read component itself 5.87 s → 3.44 s (1.7x). `candidate_count`
(28,088) is unchanged, and the full suite including the golden backtest stays
green (668 passed) — an invariance the D-056 fast path could not claim,
because `marketstate` binds its own source bytes into every state's
`code_version`. Roughly half the reads are still cold (each log's first
post-append read); eliminating them needs a rolling digest so `hash` never
re-reads, which is not done here.

Artifacts: `src/v8/store.py`.

## 2026-08-07 — D-056: state-builder fast path (O(N²) → O(N × window))

The bar-driven state pre-build recomputed every series (EMA/ATR/RSI/ADX/CCI/
MACD/pivots/prefix extremes/OBV/ADL) from scratch per decision clock, making a
backtest O(N²) in bars: ~280 s for 8,760 bars and an estimated 1-2 h for one
4-year symbol. `build_state` now takes an optional per-symbol `BarSeries`
(precomputed once over the full tape) and reads it by index per clock; the lab
builds it once per run. Unbounded features (`prior_high`/`prior_low`) keep the
exact running prefix max/min — never a fixed window, which silently diverges
(measured 83.5% of bars at a 520-bar window) and 21/27 Experts read them.
The growing-list lineage hashes keep exact `sha1_hex(list)` semantics via
precomputed per-row canonical bytes (O(N) per state with a small constant —
exact values, no chained-hash substitution). Every emitted value, per-feature
lineage, `lineage_hash` and `state_id` is byte-identical:
`tests/test_state_cache_identity.py` proves cached == uncached on every bar;
diffing the golden fixture against the pre-change code shows candidates,
evaluations and outcomes with 0 differing fields and states differing only in
the provenance `code_version` (whole-file source hash — its designed behavior,
re-pinned in `test_golden_backtest.py`). Measured on this machine: 8,760-bar
backtest 280 s → 12 s; BTCUSDT 4-year (35,064 bars, exact lab shape incl.
funding) 67 s; 8-symbol × 4-year serial-store projection ≈ 9 min (was an
estimated 11-12 h).

- **`src/v8/marketstate.py`** — `Prefix` view, `BarSeries` + `build_bar_series`,
  `_adx_series`, `_last_significant_pivot`/`_last_confirmed_swing`, cached
  branch in `build_state`/`build_multi_state` (`series=` param).
- **`src/v8/lab.py`** — builds the series once per run, passes them in.
- **`tests/test_state_cache_identity.py`** — cached == uncached on every bar
  (synthetic every bar, real tape sampled, multi-state).
- **`tests/test_golden_backtest.py`** — states/ledger hashes re-pinned; the
  move is provenance `code_version` only (diffed and documented).
- **`docs/decisions/DECISION_REGISTER.md`** — D-056.

## 2026-08-07 — D-055: strict-climax challenger for volume_climax_reversal

The O-022 measurement showed the 2-sigma climax gate fires on nearly every bar
(8,272 distinct candidates on 8,760 bars -> a 4.6% D-027 execution_share; the
family floods the rule-16 exposure pool and blocks its own re-entries). A
strict-climax challenger variant `e` (vol_zscore >= 3.0) joins the family,
owning every 3-sigma bar. Declared and frozen pre-holdout; the frozen-OOS
within-family Reality-Check (D-044) decides whether `e` survives, never the
dev window.

- **`src/v8/experts/volume_climax_reversal.py`** — variant `e` (3-sigma fade in
  the trend direction), `variants_evaluated` (a,b,c,d,e), `search_universe_size`
  5, priority e > d > c > b > a.
- **`docs/EXPERTS_REGISTRY.yaml`** — volume_climax variants/search updated.
- **`docs/decisions/DECISION_REGISTER.md`** — D-055.
- **`tests/test_expert_volume_climax_reversal.py`** — a/b/d tapes re-based on an
  alternating volume series so their vol_zscore sits in [2,3) (the near-constant
  base made ANY spike a ~10-sigma event and routed every test to the new strict
  variant); new variant-e test (8.0 spike -> z~10 -> e/LONG and e/SHORT).

## 2026-08-07 — Declared per-Expert MarketState (D-054) + block-bootstrap defect (D-052)

Two changes to the evidence machinery, both frozen pre-holdout.

**D-052 — the block bootstrap manufactured one false positive per run.**
Preregistration section 9's block-size constants (24 / 168) are bar-counts
("one day" / "one week" of 1h bars) applied to an episode-indexed `net_R`
series. When `block_size >= n` the circular sampler draws a cyclic rotation
holding every index exactly once, so all 2000 resample means equal the sample
mean: the interval collapses to zero width and any family with a positive mean
and `n >= 30` rejects H0 by construction. On the pinned dev baseline 8 of 21
families with episodes had `block >= n`, and exactly one spurious rejection
resulted. Degeneracy is the endpoint of a bias, not an isolated case — at
`block/n ~ 0.3-0.5` (every family with n=45..100) the resample variance is
already understated.

- **`src/v8/statistics.py`** — `select_block_size` becomes an n-adaptive
  episode-unit rate (`round(n**(1/3))`, doubled above the 0.10 lag-1 gate,
  capped at `n // 2`); `_block_bootstrap_indices` raises on `block >= n`.
- **`tools/run_experiment.py`** — `_block_size` delegates to the module (the
  rule existed in two copies); `resamples_for_alpha` ties the resample count to
  alpha so the bound stays a stable order statistic (at 0.05/28 the old 2000
  put it at index 3); the `2.5th-percentile` misnomer is corrected.
- Verified on an unchanged ledger (`452d91bcf890` before and after): degenerate
  families 8 -> 1 (the survivor is n=1, where a bootstrap has no variance by
  construction), H0 rejections 1 -> 0, every former zero-width row gained a real
  interval, and intervals widened slate-wide.

**D-054 — Experts declare the MarketState they need.** The 27-family inventory
found the binding constraint was not the 1h tape but the global 32-bar
`history` pin: `ichimoku_cloud` needs 78 bars and declares 3 of 4 variants
unevaluated, `breakout_retest` drops variant d, `donchian_breakout` falls back
to a 50-bar anchor scan, `pattern_measuring_objective` cannot express its
patterns. Only `market_profile_value_area` demonstrably needs higher-interval
bar structure.

- **`src/v8/interval.py`** (new) — exact up-only aggregation of the base tape
  into declared intervals; buckets anchored to a fixed UTC epoch (never tape
  start), aggregate `available_time` = its last constituent's, partial trailing
  buckets never emitted as closed.
- **`src/v8/experts/base.py`** — `intervals` + `depth` join `requires` as
  frozen specification; both default to pre-D-054 behavior.
- **`src/v8/marketstate.py`** — `build_multi_state` namespaces higher intervals
  `{sym}.{tf}.{feature}` (base stays unprefixed); `project_state` serves each
  Expert exactly its declared groups x intervals x depth; the 32-bar pin becomes
  `HISTORY_DEPTH_DEFAULT`, a default rather than a ceiling.
- **`src/v8/lab.py`** — the canonical state carries the union of declarations
  and ONE state per clock is still what the ledger records; `Lab.feasibility`
  refuses a declaration the tape cannot serve in words, so an unservable Expert
  is never indistinguishable from a signal-less one.
- **`tools/vision_backfill.py`** — archive provenance is keyed by
  (symbol, channel, month). Keying on (channel, month) was correct only while a
  tape dir held one instrument: a second symbol's 2025-01 archive was misread as
  a revision of the first's, so a multi-instrument tape could not be built.
- **`tools/build_multi_tape.py`** (new) — drives the backfill over a
  symbol x month grid into one tape, refusing any month at or past the frozen
  holdout anchor.

Golden backtest re-pinned twice, both times provenance-only: `_BUILDER_SRC_HASH`
is a whole-file hash, so adding functions re-versions every state's
`code_version` even when no formula moves. `data_hash`, `candidate_count` (15)
and `terminal_distribution` unchanged both times, and a run with the projection
disabled reproduces the enabled run's four ledger hashes byte-for-byte.

## 2026-08-06 — Expert bug-fix pass: two-step failed_breakout gate, origin-based fib extensions, climax-bar anchor, fib swing-guard removal

Adversarial audit of the 27 expert families against their hypotheses and the
Handbook of Technical Analysis (Lim 2016) found and fixed three implementation
bugs plus four audit/doc drift items. All are code-correctness fixes — the
code now matches its own documented hypothesis and the cited book; no
threshold, registry multiplicity, or hypothesis was tuned.

- **`src/v8/experts/failed_breakout.py`** — the detection gate fired a SHORT on
  ANY close below the windowed prior high, never verifying the breakout leg
  ("a close above the prior high that fails back below it", Ch7.3 p228). A
  plain downtrend with no close-breakout produced candidates. Gate and anchor
  predicate now require a prior bar that CLOSED above its own prior high; the
  frozen level is the breakout level; the anchor is the first failure bar
  after the breakout (dedup stable, no window-edge anchor slide).
- **`src/v8/marketstate.py`** — `_fib_levels` projected extensions from the
  impulse END extreme; the book's formula is origin-based ("Upside extension =
  Trough + (Range x Ratio)", Ch10.5.1 p404 / "Downside = Peak - ...", 10.5.2
  p405). Every extension level moved one full impulse-range. Retracements
  unchanged. Consumers: `fib_projection_reversal`.
- **`src/v8/experts/volume_climax_reversal.py`** — the D-026 anchor resolved to
  the trend-run start (the trend predicate is near-always-true), collapsing
  every distinct climax inside one trend into a single episode. The anchor is
  now the detection (climax) bar; the per-bar trend predicates became dead code
  and were removed.
- **`src/v8/experts/fib_projection_reversal.py`** — removed the swing-lattice
  consistency guard that gated on the significance-FILTERED swing_high_10 /
  swing_low_10 pair (a different pair than the unfiltered confirmed-swings
  anchor `_fib_levels` uses) — it vetoed states with a valid anchor and
  NO_HABITAT'd states where the filtered pair was absent. `fib_levels` is the
  habitat gate and its own consistency guard. Same fix in
  `fib_retracement_continuation.py`. Docstring corrected: Fig10.51 is a LONG
  reversal at a DOWNWARD 161.8% projection, not a short at an up-projection.
- **`tests/`** — new `test_expert_failed_breakout.py` (two-step gate,
  no-breakout regression, fresh-high rejection, anchor, still_valid,
  warmup); updated fib projection levels to origin-based values in
  `test_expert_fib_projection_reversal.py` and `test_feature_groups.py`;
  registry CONSUMPTION manifest corrected (`failed_breakout` no longer reads
  `prior_high`); golden backtest re-pinned (candidate_count 21 -> 15 after the
  two-step gate, then states/ledger only after the fib fix); vertical-slice
  exposure-conflict assertion relaxed (the gate fix removed the overlap on the
  synthetic fixture; the guard is pinned end-to-end in
  `test_admission_contention.py`).
- **`docs/EXPERTS_REGISTRY.yaml`** — unchanged (the removed swing features
  were never part of `requires`; `fib_levels` is a location-group feature the
  fib experts still declare via 'location').

## 2026-08-06 — O-022 measured: rule-16 exposure blocking matrix + D-027 execution_share distribution

Quantified the cross-family coupling on the corrected dev diagnostic: of
11,673 `EXISTING_EXPOSURE_CONFLICT` rejections, all had a same-direction open
slot at the block time; bollinger_breakout blocked 4,115 (incl. 1,226 of its
own — self-blocking). Per-family D-027 `execution_share` clears the 0.25 floor
for only 6 of 21 families; 15 sit below (5 under 0.10). Recorded in O-022 as
measured evidence: on the current slate the D-027 attribution gate would score
~6 families on the OOS and mark the rest `ATTRIBUTION_UNSAFE_*`.

## 2026-08-06 — v2 challenger registration for the bug-fixed families (O-023, D-053)

Operator chose O-023's admission condition: `failed_breakout` stays v1
(bug-completion — fixed series is a strict subset, 369 -> 76); the two families
whose fixes ADD behavior become v2 challengers.

- **`src/v8/experts/volume_climax_reversal.py`**, **`fib_projection_reversal.py`** — `expert_version` bumped v1 -> v2 (enters the episode_key, so v1 and v2 episodes never collide).
- **`docs/EXPERTS_REGISTRY.yaml`** — the two families' `expert_version` v2.
- **`docs/decisions/DECISION_REGISTER.md`** — D-053 decision; **`docs/decisions/OPEN_DECISIONS.md`** — O-022/O-023 (exposure coupling across families, version discipline).
- **`tests/test_expert_volume_climax_reversal.py`** — version assertion v2.

## 2026-08-06 — D-052: block-bootstrap block-size rule corrected from bar-units to n-adaptive episode units

The prereg §9 block-size rule applied bar-counts (24 / 168 — "one day" /
"one week" of 1h bars) to an episode-indexed `net_R` series: a unit error,
visible in §9's own prose ("24 episode-blocks (one day)"). The fix makes the
tier values n-adaptive episode-unit rates — `round(n**(1/3))`, doubled when
the lag-1 autocorrelation gate fires, hard-capped at `n // 2` — and the tool
now delegates to the module's `select_block_size` (one rule of record).

- **`src/v8/statistics.py`** — `select_block_size` re-expressed in episode
  units; `_block_bootstrap_indices` gains a fail-closed `block_size < n`
  invariant (at `block_size >= n` every resample is a rotation of the whole
  series and the bootstrap collapses to a point mass at the sample mean —
  a zero-width `ci_lower == mu_hat` that rejected H0 by construction).
- **`tools/run_experiment.py`** — `_block_size` delegates to
  `select_block_size`; new `resamples_for_alpha` keeps the tail index a
  stable order statistic (`int(N * alpha) >= 100`); `N_RESAMPLES` 2000 ->
  60000 (the bound was `int(2000 * 0.05/28) = 3` — the 4th-smallest draw
  standing in for a 0.18th percentile).
- **`docs/decisions/DECISION_REGISTER.md`** — D-052 decision with the
  mechanical reproduction, outcome-neutrality of the rule choice across the
  three candidate rules, and the measured cost.
- **`tests/`** — invariant tests for the non-degeneracy (point-mass rejection,
  width under the rule), the episode-unit tier values, and the stable tail
  index in `test_statistics_ext.py` / `test_reality_check.py` /
  `test_run_experiment.py`.

## 2026-08-06 — Handbook+Evidence extraction lands: feature graph, 24 expert families, risk & execution management (D-048/49/50)

The two-book extraction round (D-042) reaches code: the feature-group ontology
widens to 11 groups / 73 new features (FG-1..FG-7, G-01..G-43), 24 expert
families are implemented and registered (EXP-01..24, E-05/E-06 survivors +
E-01..E-24), and risk/execution management lands (RISK-1..6, EXEC-1..6).

- **`docs/decisions/DECISION_REGISTER.md`** — D-048 (risk additions), D-049 (feature graph), D-050 (expert admission).
- **`src/v8/schema.py`** — FEATURE_GROUPS +7 groups (candle_shape/oscillator/session/positioning, participation activated, volatility/location extended); CandidateDraft.size; ExperimentManifest.risk_per_trade/min_trades; CounterfactualOutcome endpoint vocabulary extended (TIME_EXIT).
- **`src/v8/marketstate.py`** — 73 new feature computations (Wilder RSI/MACD/ADX, Bollinger, swing lattice with Ch27.2 ATR range filter, fib levels, pivot, consolidation, gap, OBV/ADL/CMF, session, funding/OI); add() value widened to tuple/list; no-signal -> numeric sentinel (never None, D-024 veto preserved).
- **`src/v8/experts/*`** — 24 new expert files (one per behavior family, D-033), each with variants_evaluated (D-044) + search_universe_size (D-046). CRIT fixes applied: E-01 variants b..g (CRIT-4), E-07 declared subset (CRIT-6), E-17 self-gating regime (CRIT-7).
- **`src/v8/equity.py`** (new) — RiskState drawdown ladder (RM-06, O-016 challenger) + trade_units_for (RM-07).
- **`src/v8/risk.py`** — size-aware heat (size*stop_r, byte-identical at 1.0), equity wiring, min-trades/PF gates.
- **`src/v8/simulator.py`** — breakeven roll + chandelier trail, scale-out (closed_fraction + PARTIAL_EXIT), pyramid plumbing, FILL_AT_LIMIT, TIME_EXIT; sim.hash() -> canonical-sim-v7.
- **`src/v8/statistics.py`** — D-045 detrending (passive_benchmark_r/detrend_net_r) retained; METH-1..6 extensions follow in the next entry.
- **`docs/EXPERTS_REGISTRY.yaml`** — 28 entries (24 new FORMALIZED, open_interest DATA_BLOCKED, breakout_retest FORMALIZED); registry test derives expected set from code.
- **`tests/`** — test_feature_groups.py, 24 test_expert_*.py, test_risk.py, test_execution.py; golden re-pinned (hashes moved by construction, candidate_count 21 + terminal_distribution unchanged throughout).

## 2026-08-06 — Retire v2 research subsystems from version control (D-051)

The v2.3 research-corpus pipeline (`research/pipeline_v2/`) and the standalone
`research_base/` package were superseded by the `src/v8/` runtime and are
removed from the tree, along with `research/revision/` visual-preview artifacts,
`research/text/` corpus copies, and the three revision-monograph builders whose
data sources they were (`tools/build_v8_revision.py`,
`tools/generate_gemini_master_html.py`, `tools/generate_10k_gemini_master_html.py`).

- **`docs/decisions/DECISION_REGISTER.md`** — D-051 (PROVISIONAL_DECISION).
- No prereg, contract, or test references the retired paths (verified); the 615-test suite and monograph build are unchanged.
- Recoverable from git history (introduced in `a051a20`) should the v2.3 ledger be needed again.

## 2026-08-06 — Position management and fill policies land as declared, optional mechanics (EXEC-1..6, D-047)

The handbook's execution additions (EX-01..EX-12 in `books/reports/HAND_RISK_EXEC.md`,
gated by OPEN_DECISIONS O-013 — admission still requires replicated OOS gain vs
static geometry) become first-class, DECLARED risk_geometry keys and one new
fill policy. Every key is optional; the pilots' frozen geometry declares none,
so step()/run() output on default geometry is byte-identical to pre-change code
(verified by diffing the executed outcomes of both code versions on the golden
fixture). This is the O-013 mechanics layer: the question "does active position
management beat static geometry" can now be asked.

- **`src/v8/simulator.py`** — EXEC-1 breakeven roll + chandelier trail
  (`breakeven_roll_at_mfe_r` / `breakeven_margin_r` = `round_trip_cost_r` /
  `trail_stop_atr`; `OpenPosition.stop_level` + `stop_rolled`; endpoint stays
  STOP); EXEC-2 scale-out partial exit (`scale_out_ratio` > 0 enables +
  `scale_out_at_mfe_r`; `StepResult.closed_fraction` < 1.0 is a NON-TERMINAL
  event; `OpenPosition.remaining`/`realized_r` fraction-weighted R accounting);
  EXEC-5 TIME_EXIT endpoint (`time_exit_bars`, distinct from EXPIRY); EXEC-4
  `FILL_AT_LIMIT` fill policy (barrier entry at `risk_geometry['limit_price']`,
  fill-only entry-bar inspection, never-filling orders never enter); EXEC-3
  `pyramid_add_rules` declared but P2/off (fail closed on request;
  `midpoint_stop` primitive implemented + tested). `hash()` →
  `canonical-sim-v8`. Funding path untouched (the funding goldens are
  byte-identical). Management updates apply from the bar AFTER the bar that
  triggered them (bar-atomic OHLC cannot order intrabar events).
- **`src/v8/lifecycle.py`** — `CandidateRegistry.position_action`: the
  append-only `PositionAction` event (`kind: position_action`), EXEC-2's
  PARTIAL_EXIT. Non-terminal: no transition, `current()` unchanged, joins the
  candidates ledger and therefore `ledger_hash`.
- **`src/v8/lab.py`** — executed path records PARTIAL_EXIT PositionActions and
  continues the position; FILL_AT_LIMIT executed entry (resting order, never
  entered → the epilogue's never-entered convention); TIME_EXIT closes the
  position (`expiry_reached`); equity feed books fraction-weighted net_r
  against the admission size.
- **`src/v8/schema.py`** — endpoint vocabulary documented with TIME_EXIT;
  PARTIAL_EXIT documented as a non-terminal PositionAction, never an endpoint;
  `risk_geometry` management keys and `limit_price` documented on
  `CandidateDraft`; `ExperimentManifest.fill_policy` documents FILL_AT_LIMIT.
- **`tests/`** — `test_execution.py` (new: EXEC-1..6 unit + lab end-to-end,
  including the fill-only entry-bar invariant and a managed-geometry lab run),
  `test_lifecycle.py` (new: PositionAction append-only/non-transition/replay),
  hash-canary goldens re-pinned to `canonical-sim-v8`,
  `SUPPORTED_FILL_POLICIES == ('FILL_AT_BAR_CLOSE', 'FILL_AT_LIMIT')`,
  golden-backtest ledger re-pinned (outcome records carry the re-versioned
  `simulator_hash`; data/states/candidate/terminal unchanged).
- **Not done here:** O-013's admission gate (replicated OOS gain vs static
  geometry) is a preregistration/experiment act, not code; RM-04 two-tier heat
  consumption of `stop_rolled` is dormant in `risk.py` until a register
  decision revises D-023's domain (CRIT-2.6); pyramiding (EXEC-3) and the full
  EX-13 action lattice (ADD/REENTER/HEDGE) are P2.

## 2026-08-06 — The net-R null is detrended, and the search universe is declared (D-045, D-046)

Two multiplicity/centering defects from the handbook evidence extraction
(`books/reports/EV_METHODS.md` G-01/G-02, issues METH-1 and METH-2), both
landed pre-holdout while prereg §16 still permits it — no manifest, store or
outcome ledger exists yet.

**D-045 — the null was mis-centered.** `μ_f ≤ 0` on raw episode net_R is
mean-zero only for a no-skill rule on *detrended* data (Aronson Ch1 p23-27,
Appendix A). On a trending tape a long-biased family earns positive expected
net_R with zero predictive power, and every pilot carries long-direction
setups — so the single-config lower-bound gate and the Reality Check were
both testing against a null the tape had already moved. Episode net_R is now
centered on a same-exposure passive benchmark before any gate; the raw mean
survives beside it as a diagnostic and the difference is published as
`position_bias_component`. Signal generation never sees a detrended value.

**D-046 — the search universe was undeclared.** `variants_evaluated` (D-044)
counts only the configurations whose episode series were retained; parameter
grids, discarded indicator variants and the direction-sign choice are search
the family also consumed. The registry now declares the total, the runner
publishes it with every family statistic, and an undercount is flagged rather
than silently inflating significance.

- **`src/v8/schema.py`** — `CounterfactualOutcome` gains `entry_price`,
  `risk_unit_price`, `market_move_r`. Recorded, never re-derived: `risk_unit`
  depends on the fill whenever a draft declares `risk_frac` instead of
  `atr_ref`, so the R denominator is not recoverable downstream.
- **`src/v8/simulator.py`** — populates them; `hash()` → `canonical-sim-v6`.
- **`src/v8/lab.py`** — the executed path does not go through `simulator.run`
  (it steps positions and closes them in `_record_outcome`), so the fields are
  supplied at each entered call site too; they stay 0.0 for never-entered
  candidates.
- **`src/v8/statistics.py`** — `EpisodeExposure`, `mean_log_drift_per_bar`,
  `passive_benchmark_r`, `detrend_net_r`, `placebo_exposures`,
  `appendix_a_invariant`. `invariant_holds` is deliberately unimplemented and
  raises: the "≈ 0" tolerance is itself a preregistered constant and is left
  to an explicit operator choice rather than a silent default.
- **`docs/EXPERTS_REGISTRY.yaml`** — required `search_universe_size`; all five
  pilots declare 1, consistent with prereg §4 (parameters frozen in code
  against synthetic tapes before the dev window existed).
- **`tools/run_experiment.py`** — scores the detrended series, reports the
  drift estimate, the raw/detrended pair and the search accounting; fails
  closed on a pre-D-045 ledger that carries no `risk_unit_price`.
- **`tests/`** — `test_detrended_null.py` (new: reproduces the position bias,
  then asserts it is removed), plus runner and registry gates. Goldens
  re-pinned: `net_r`, endpoints, labels, `data_hash`, `states_hash`,
  `candidate_count` and `terminal_distribution` are all UNCHANGED and only
  `ledger_hash` moved — the evidence this changed the record, not a decision.
- **Not done here:** prereg §2/§10/§11 still describe the uncentered null in
  prose; the `invariant_holds` threshold is unchosen. Both are operator acts.

## 2026-08-06 — Within-family variant multiplicity fixed: Reality-Check replaces "variants count as one unit" (D-044)

Preregistration §11 said "all variants explored inside a family count as one
multiplicity unit (rule 13)." That over-read rule 13's ontology (a variant is
not a new Expert) into a statistical claim (variant search is
multiplicity-free), which is false: best-of-N variant search inside one
family reintroduces exactly the selection bias rule 11 exists to control
(the canonical case is Aronson's 6,402-rule study, which understates its own
search by an order of magnitude under a themes-only counting rule). The bug
was harmless while every pilot sat at `variant_id: 'a'`; it stops being
harmless the moment variant search starts, which literature extraction is
about to do. Cross-family Bonferroni (`α_f = 0.05/F`) is unchanged — still
valid, only conservative under correlation, and not the urgent half of this.

- **`docs/decisions/DECISION_REGISTER.md`** — D-044 added.
- **`docs/PREREGISTRATION_V8_SLICE_001.md`** — §1 and §11 revised: within a
  family, `len(variants_evaluated) == 1` keeps the original single-config
  percentile-bootstrap test; `> 1` spends the family's `α_f` via
  `src/v8/statistics.reality_check_p_value` (White 2000 Procedure RC,
  already `LITERATURE_SUPPORTED` in `HYPOTHESIS_LAB_PROTOCOL.md`'s Sources
  section) over all evaluated variants' episode series, using the same
  section-9 block-size rule. Cross-family pooling into one N-configuration
  statistic is explicitly **not** implemented — families fire on disjoint
  episode grids and a correct pooled test needs a bar-level panel, not an
  episode-level one (O-021).
- **`docs/EXPERTS_REGISTRY.yaml`** — new required field `variants_evaluated`
  per entry (losers included, not just the reported `variant_id`); all five
  current entries carry `['a']` since no variant search has happened yet.
- **`src/v8/statistics.py`** (new) — `reality_check_p_value`,
  `select_block_size`, stdlib-only, explicit seed, aligned-episode-grid
  inputs only. Not yet wired into a runner: `tools/run_experiment.py` (the
  `v8_slice_001` Phase-4 runner) does not exist yet, so this is unit-tested
  on synthetic data only.
- **`tests/test_reality_check.py`** (new) — determinism, p-value bounds,
  block-contiguity, `select_block_size` against known-autocorrelation
  synthetic series, mismatched-length and empty-input rejection.
- **`tests/test_expert_registry.py`** — gates `variants_evaluated` presence
  and that the reported `variant_id` is a member of it.
- **`docs/contracts/IMPLEMENTATION_LAYOUT.md`** — `statistics.py` and
  `tests/test_reality_check.py` rows added (D-032: new files are registry
  decisions).
- **`docs/decisions/OPEN_DECISIONS.md`** — O-021 opened: whether and how to
  pool the Reality-Check test across families (bar-level panel), deferred
  rather than built ad hoc.
- Legal pre-holdout per prereg §16, same basis as D-041: the frozen holdout
  has not been opened or downloaded.

## 2026-08-04 — Rule 14 rewritten: complexity budget splits runtime from evidence (D-043)

The constitution capped "at most 3 active Experts". That single number
conflated an engineering question (how many modules evaluate per bar — zero
validity content) with a statistical one (how many independent hypotheses are
simultaneously under test on one frozen OOS). The cap was already breached:
`EXPERTS_REGISTRY.yaml` carries 5 Experts after D-042. No code enforced it, so
this is a documentary correction.

- **`docs/charter/V8_CONSTITUTION.md` — rule 14 rewritten** on two axes:
  (a) runtime Expert count unbounded, limited only by determinism and compute,
  explicitly *not* a validity constraint; (b) the preregistered cap applies to
  the `behavior_family` count simultaneously carrying a claim on one frozen-OOS
  evaluation, entering rule 11's family-level multiplicity correction. The
  minimum-architecture diagram's `(2–3)` becomes `(N, unbounded)`.
- **"At most one learned component" rescoped to per pipeline position.** A
  Candidate Scorer (ladder step B) and an ML Expert challenger sit at different
  positions and are each already gated by rule 5's preregistered frozen-OOS
  comparison; the global "never both at once" added no statistical control, only
  a sequencing preference. `LEARNING_PROTOCOL` §3 and its cheap test 5 updated.
- **`docs/contracts/ARCHITECTURE_SPEC.md` §4, `ROADMAP.md`, `PLAN_V8_FULL.md`** —
  the copied "hard cap" wording replaced; router/scorer/ranker/RL absence
  unchanged.
- **`docs/decisions/DECISION_REGISTER.md`** — D-043 added; D-003 and D-020
  annotated as revised. Both keep `PROVISIONAL_DECISION`: rule 2's label
  vocabulary is closed, and the register's own note makes that status the
  sanctioned reversible one — inventing a `SUPERSEDED` label would breach rule 2
  while fixing rule 14.

- **`tests/test_admission_contention.py` (new) — contention is now tested.**
  `RUNTIME_SCHEDULER_SPEC` §5 test 3 (Expert-order shuffle) was only exercised
  by the two pilots, which almost never emit on the same bar — so the claim was
  verified with **no contention at all**. The new tests use unconditional
  contenders that collide on one exposure slot every bar, and pin two separate
  properties: (1) the ledger stays order-independent under full contention,
  because `lab.run` sorts Experts by `expert_id` before evaluating; (2) the
  surviving tie-break is therefore that lexicographic name — measured, the
  first-sorting of two behaviorally identical Experts wins contested slots
  roughly 2:1, and the advantage follows the name when the names are swapped.

- **`max_spread_frac` renamed to `max_bar_range_frac`; veto detail `SPREAD` to
  `BAR_RANGE`.** The D-024 predicate is `(high-low)/close` — the entry bar's
  intrabar range. It is not a bid-ask spread and cannot be: the tape carries no
  depth. The old name propagated the misnomer into `PREREGISTRATION` §8 and the
  runbook, where it read as an execution-cost control. Pure rename across
  `schema.py` / `risk.py` / `lab.py` / `tools/materialize_views.py` and the
  tests; **`GOLDEN_LEDGER_HASH` re-pinned** because `config_hash =
  sha1(asdict(manifest))` keys on field names, while `data_hash`,
  `states_hash`, `candidate_count` (21) and `terminal_distribution` are
  unchanged — that invariance is the evidence no decision moved.
- **`docs/tr/V8_CONSTITUTION.md` — rules 13–17 added.** The Turkish mirror
  stopped at rule 12 and had never carried the ontology, complexity-budget,
  learning, risk-admission, or materialization rules. Rule 2's label discipline
  cannot hold in a corpus that omits the rules; the TR diagram's `(2–3)` is
  corrected with the EN one.
- **Three open questions registered rather than guessed.** O-018 (should the
  heat cap scale with the Expert population — caps stay at 3.0 / 2.0 until a
  preregistered comparison moves them), O-019 (does the 0.05 intrabar-range
  veto fire at all on the declared dev window; "declared, never fitted" answers
  leakage but not inertness, and the firing rate has never been measured),
  O-020 (per-Expert `history` lookback instead of the global 32 bars —
  deliberately not implemented here: it adds a public field to the Expert
  contract, a D-032 change needing its own decision, and it moves the state
  hash).

Two couplings are recorded as follow-ups, not resolved here. The binding
constraints on portfolio scale are rule 16 (one exposure per instrument +
direction) and D-023 (`max_heat = 3.0`), not the Expert count — with those in
place a 400-Expert portfolio holds the same positions as a 3-Expert one. Rule 16
and `CANDIDATE_LIFECYCLE_SPEC` §6 now say so explicitly and restate the
single-exposure rule as the attribution default it is; whether the heat cap
should scale with the Expert population is opened as **O-018** rather than
guessed at, and the caps stay at 3.0 / 2.0 until a preregistered comparison
moves them. And
contested-slot priority is decided by Expert *name*, which is deterministic and
harmless at three Experts but is a silent allocation policy at the count rule 14
now permits. A principled tie-break is a ranker, gated by rule 6 / D-008
(O-006 / O-012); the new test fails if one is added, forcing that decision to be
registered rather than landing silently. No economic claim is made or implied;
the verdict stays `NO_ECONOMIC_CLAIM` (rule 12).

## 2026-08-02 — Second-level provenance + PIT bugfix pass (7 fixed)

An adversarial re-audit against the `V8_CONSTITUTION` bug-class catalogue
(implementation substitution / parallel economic truth / temporal leakage /
silent data corruption / boundary bugs / provenance scope) confirmed several
second-level defects; all were fixed with regression tests and a deliberate
golden re-pin (candidate_count 21 and terminal_distribution UNCHANGED).

- **`src/v8/lab.py` (medium) — PIT consumption order.** The state accumulator
  consumed the tape in canonical replay order `(event_time, available_time,
  venue_sequence)`, which is NOT guaranteed available-monotonic when latencies
  are heterogeneous — a row with a later event can become available earlier,
  and the moving pointer silently SKIPPED it (a state built without a bar that
  WAS admissible at the decision clock). The lab now consumes a stable
  available_time-sorted copy (`pit`) for the bar loop AND the accumulator;
  byte-identical for co-monotonic tapes (golden unchanged).
- **`src/v8/lab.py` (medium) — parallel economic truth.** The tape-end close
  of an open position re-derived the net formula `sign*(close-entry)/unit -
  cost - funding_paid` in the epilogue instead of delegating to the simulator.
  Added `CanonicalSimulator.close_out(pos, final_close)` as the single
  authority; the epilogue calls it (a second copy would silently diverge the
  moment cost/funding policy changes).
- **`src/v8/lab.py` + `src/v8/schema.py` (medium) — unpinned risk gate.** The
  effective `RiskGate` (max_heat / max_cluster_heat / clusters) is a
  run-configuration input, but was invisible in every hash when no cap was
  breached. The ledger hash now binds `risk_config_hash` and the `LabReport`
  surfaces `risk_gate_hash` (report-only). Golden ledger hash re-pinned.
- **`src/v8/lab.py` (low) — `_code_hash` over-binds vendored `simtruth/`.**
  The decision-path code hash covered `src/v8/simtruth/**` (vendored V7,
  engineering only, nothing imports it), so a vendored edit invalidated every
  pinned manifest for a byte-identical decision path. `simtruth/` is now
  excluded from `_code_hash`.
- **`src/v8/lab.py` (low) — fabricated empty-tail counterfactual.** A
  TRIGGERED candidate rejected for excess cost on the FINAL tape bar (no entry
  bar) got a fabricated `EXPIRY/0.0/NOT_EXECUTED` outcome from `sim.run([])`,
  while the identical never-entered candidate below the cost gate is recorded
  `INVALIDATED_BEFORE_TRIGGER`. Same fact, two endpoints. The never-entered
  convention now applies in both branches.
- **`src/v8/marketstate.py` (low) — null is not zero.** An absent feature
  (`prior_high`/`prior_low` on the first bar) was labelled `COMPLETE` with
  `null_reason=None` and its `max_input_available_time` borrowed the newest
  bar it never consumed — both contradict the `MARKET_STATE_CONTRACT`
  (§2 consumed-derived clock; §4 "null is not zero"). None-valued features are
  now auto-`DEGRADED` with `null_reason=NOT_YET_AVAILABLE` and a consumed-only
  calculation clock (0 when nothing was consumed). Golden state/ledger hashes
  re-pinned; candidate decisions unchanged.
- **`tools/run_experiment.py` (medium) — holdout window never reconciled.**
  `data_hash` binds the tape bytes, not the window: a dev-period tape (or a
  dev+OOS merge) authored with `start_ns >= anchor` was evaluated as the
  frozen OOS. The runner now fails closed when the tape's kline event range
  falls outside `[start_ns, end_ns]` (prereg §13).

Artifacts: `src/v8/lab.py`, `src/v8/simulator.py`, `src/v8/marketstate.py`,
`src/v8/schema.py`, `tools/run_experiment.py`, `tests/test_golden_backtest.py`
(deliberate golden re-pin), `tests/test_bugfix_pass.py`,
`tests/test_run_experiment.py`.

## 2026-08-01 — Adversarial-audit fixes on Phase 2-4 code (14 findings, 6 fixed)

A four-dimension adversarial review (correctness / contract / determinism /
runner) confirmed 14 findings; the real ones are fixed here.

- **`src/v8/lab.py` (medium)** — the pre-entry invalidation now uses the
  expert's FROZEN windowed prior ref (`prior_low_ref` / `prior_high_ref` in
  the draft geometry) instead of the all-bars state feature, which diverges
  from the thesis ref (an old spike outside the 32-bar window pins it). A
  dead-thesis candidate no longer triggers and enters, polluting the executed
  population. Dev trigger count 3,295 -> 2,939; golden terminal distribution
  changes (deliberate re-pin).
- **`src/v8/marketstate.py` (low ×2)** — `max_input_available_time` is now
  the consumed-derived clock (prior_high/prior_low never claim the newest bar,
  which is not their input); the history feature's `input_lineage_hash` now
  covers the full close series (its EMA columns depend on it).
- **`tools/run_experiment.py` (medium ×2, low)** — prereg §9 mechanical
  block-size rule implemented (24 by default; 168 when the lag-1
  autocorrelation of episode net_R exceeds 0.10); family scores are NOT
  reported when the D-027 gate fires ATTRIBUTION_UNSAFE_* (§11 "not scored");
  the holdout hash is REQUIRED (fail closed on an un-pinned holdout, §16);
  the frozen OOS window must start strictly after the 2026-07-01 anchor (§13);
  `h0_rejected` is now the composite §11/§12 test (lower bound > 0 AND
  n_f >= 30).
- **Runner bootstrap percentile fix** (caught by the dev-tape smoke run) — the
  2.5th-percentile LOWER bound was indexed at the 97.5th percentile; a
  negative-mean family could falsely report h0_rejected.
- 5 new regression tests; suite 148 -> 152. Dev materialization re-pinned
  (`adad594a…`, views4); prereg §6/§15 updated (execution_share 0.4662,
  KS 0.1028 — diagnostics only; thresholds unchanged).

## 2026-08-01 — Dev materialization re-pin (three pilots, D-042)

- Dev tape re-materialized with the third pilot (`liquidity_sweep_reclaim`)
  and the Phase-2/Phase-4a code: candidate_count 2,786 -> 3,323, ledger_hash
  `40d4f23a…` (fresh `views3` dir, compile-once; code_hash `fec878c5…`).
- Prereg §6 derived outputs and §15 12-month diagnostics updated: with three
  pilots the D-027 populations are `n_executed` 1,415 / `n_portfolio_rejected`
  1,476, execution_share 0.4895, KS 0.0932 — **diagnostics only**, the
  ratified thresholds 0.25/0.20 are unchanged (O-017).
- Monograph rebuilt; suite 147 tests green.

## 2026-08-01 — Phase 4b: v8_slice_001 experiment runner

- **`tools/run_experiment.py`** — the preregistered `v8_slice_001` runner:
  validates the frozen manifest (experiment_id, universe BTCUSDT, interval
  1h), verifies the pre-recorded holdout tape hash before any evaluation
  (fail closed on mismatch or absent holdout — never fabricates a verdict),
  runs the two pilot families on the frozen OOS, computes family-level
  one-sided tests with a deterministic block bootstrap (block 24, fixed seed)
  and Bonferroni multiplicity control (alpha_f = 0.025), and surfaces the
  D-027 attribution statistics. Authority blocks first (no receipt ->
  NO_ECONOMIC_CLAIM). The RUN is gated on the frozen holdout existing (first
  two published months after 2026-07-01 + 9-bar extension, prereg §13).
- 5 tests (fail-closed absent holdout, frozen-constant validation, holdout
  hash recorded-before-evaluation, hash mismatch fail-closed, bootstrap
  determinism/one-sidedness). Suite 142 -> 147.

## 2026-08-01 — Phase 3: third pilot + DATA_BLOCKED backlog (D-042)

- **`src/v8/experts/liquidity_sweep_reclaim.py`** — `LiquiditySweepReclaimExpert`
  (`liquidity_sweep_reclaim` / `sweep_reclaim`, variant `a`): LONG after a
  sweep of the windowed prior low that closes back above it, SHORT after a
  prior-high sweep reclaimed by the close; `prior_low_ref`/`prior_high_ref`
  frozen at detection (failed_breakout pattern) and excluded from
  `geometry_version` (`src/v8/lab.py`). Re-exported; added to
  `tools/materialize_views.py` PILOTS.
- **`docs/EXPERTS_REGISTRY.yaml`** — third pilot at FORMALIZED; `breakout_retest`
  and `capitulation` backlog families registered DATA_BLOCKED until
  derivatives tape (no code module — ROADMAP Phase 3 backlog).
- **`docs/contracts/IMPLEMENTATION_LAYOUT.md`** — tree + file table + planned
  note updated; **`D-042`** registered (D-032 file-family rule).
- Registry/artifact tests amended for the third pilot + DATA_BLOCKED entries.
  4 new expert tests; suite 139 -> 142. The dev materialization is re-pinned
  (see the materialization entry below).

## 2026-08-01 — D-027 attribution-validity gating in LabReport (Phase 4a)

- **`src/v8/schema.py`** — LabReport gains `n_executed` / `n_portfolio_rejected`
  / `execution_share` / `divergence_ks` (two-sample KS on executed vs
  portfolio-state-rejected net_R) and the verdict vocabulary
  NO_ECONOMIC_CLAIM | CERTIFIED_AVAILABLE | ATTRIBUTION_UNSAFE_LOW_COVERAGE |
  ATTRIBUTION_UNSAFE_POPULATION_DIVERGENCE. Authority blocks first (receipt
  None -> NO_ECONOMIC_CLAIM regardless); thresholds are the ratified O-017
  numbers (0.25 / 0.20), fixed forever.
- **`src/v8/lab.py`** — stdlib-pure `_two_sample_ks` (scipy/numpy banned in the
  decision path, D-031), `_d027_verdict`, and the epilogue computation of both
  populations. Verified to reproduce the prereg §15 12-month diagnostics
  exactly (execution_share 0.4576, KS 0.1044, n=1111/1317) on the dev tape.
  Hash-neutral (statistics derive from ledgers already inside ledger_hash) —
  no golden re-pin.
- **Prereg §15** — the 12-month diagnostics corrected to the
  label_status-based population definition (n_executed 1,111 — the earlier
  draft counted INVALIDATED_BEFORE_TRIGGER as executed); the lab's own
  D-027 computation is now the source of these numbers.
- 9 new tests; suite 127 -> 136.

## 2026-08-01 — Phase 2 completion: per-feature input lineage + state provenance

- **`src/v8/schema.py`** — `FeatureValue` gains `input_lineage_hash` (identity
  of the raw rows that produced the feature) and `calculation_time`;
  `FEATURE_GRAPH_VERSION` (hash of the FEATURE_GROUPS declaration);
  `MarketState` gains a `provenance` block
  {raw_manifest_hash, feature_graph_version, code_version}.
- **`src/v8/marketstate.py`** — build_state binds each feature's input lineage
  (payload_hash when the tape computes it, else the payload — synthetic tapes
  carry no payload_hash) and fills the provenance block. These are audit
  metadata: they do NOT join the identity hashes (a raw revision that does not
  change a value must not fabricate a new state identity).
- **Golden re-pin (deliberate, PERSISTENCE_REPLAY_SPEC 4):** the persisted
  state records gain the new fields, so `GOLDEN_STATES_HASH` and
  `GOLDEN_LEDGER_HASH` move; `GOLDEN_DATA_HASH`, candidate count 21 and the
  terminal distribution are unchanged (feature values are identical — expert
  behavior is byte-identical).
- 3 new tests (per-feature lineage + calculation clock, revision-without-
  value-change lineage, provenance determinism). Suite 136 -> 139.

## 2026-08-01 — 12-month dev materialization + pinned rebuild (D-041)

- **12-month dev tape built and audited clean** — BTCUSDT 1h 2025-07-01..
  2026-07-01: 8,760 klines + 1,188 funding rows (incl. the `2026-07` coverage
  horizon) = 9,948 rows, tape hash `4c8e5888…`, 25 SHA-256-verified Vision
  archives. Audit: 0 gaps, 0 duplicates, payload hashes OK; the old 3-month
  tape still audits clean.
- **`research/tape/btcusdt-1h-12m/manifest_dev.json`** — `experiment_id
  v8-dev-12m-btcusdt`, code_hash `ea8db9e2…`, data_hash `4c8e5888…`.
  Materialized in a fresh store/views dir (compile-once): market_states 8760,
  candidate_birth/outcomes 2786, candidate_trigger 2779,
  execution_trajectories 11684; ledger `c78bf43a…`, verdict
  `NO_ECONOMIC_CLAIM` (no authority receipt).
- **Prereg pins updated** — §6 manifest + derived outputs, §13 dev hash, §15
  12-month diagnostics appended (execution_share 0.4596, KS 0.1067) **as
  diagnostics only**; O-017 thresholds 0.25/0.20 unchanged. DATASET_SPEC
  §6.1/§6.2/§6.4 measured rows updated.
- Monograph rebuilt; suite untouched (127 tests).

## 2026-08-01 — Tape-driven funding wiring (D-041) + golden re-pin (sim v5)

- **`src/v8/simulator.py`** — `CanonicalSimulator` gains `funding_schedule`
  ((boundary_time_ns, rate) pairs); a non-empty schedule settles each crossed
  boundary at `entry_price × rate / risk_unit` (DATASET_SPEC 6.4) and fails
  closed on a missing boundary; the empty schedule keeps the legacy scalar
  path byte-identical. Sim hash bumps to `canonical-sim-v5`; schedule values
  are tape data bound by `data_hash`, never by `sim.hash()`.
- **`src/v8/lab.py`** — `Lab.run` builds the schedule from the tape's
  `funding` rows and passes it to the simulator; `_validate_tape_rows` gains
  the funding branch (non-finite / |rate| > 0.10 fail closed).
- **Golden re-pin (PERSISTENCE_REPLAY_SPEC 4, deliberate):** the only moved
  pin is `GOLDEN_LEDGER_HASH` (outcomes' `simulator_hash` changed via the sim
  source hash + v5); `GOLDEN_DATA_HASH`, `GOLDEN_STATES_HASH`, candidate
  count 21 and the terminal distribution are unchanged — the synthetic tape
  carries no funding rows, so the event stream is byte-identical.
- Tests: 4 schedule-driven funding tests + 1 lab-level schedule wiring test;
  sim-hash canaries re-pinned to v5. Full suite 122 -> 127.

## 2026-08-01 — D-041: 12-month dev window + tape-driven funding (owner)

- **D-041 registered** — the declared dev dataset expands from 3 to 12 months
  (BTCUSDT 1h, `2025-07-01`..`2026-07-01`, ~8,760 bars) and the `funding`
  channel is ingested into the PIT tape with tape-driven settlement
  (`funding_settled_r = entry_price × rate / risk_unit`), per DATASET_SPEC
  §6.4. O-017 thresholds 0.25/0.20 are **not** touched; the 12-month baseline
  updates prereg §15 diagnostics only. Funding coverage horizon `2026-07`
  declared so end-of-dev positions settle across the 2026-07-01 boundary.
  Dev end stays strictly before the holdout anchor.
- **`docs/PREREGISTRATION_V8_SLICE_001.md`** — §8 funding baseline becomes
  tape-schedule-driven (scalar retained as no-funding-tape fallback); §13 dev
  window 12 months + coverage horizon; §15 diagnostics note (thresholds
  fixed); §6 dev-tape hash marked pending the rebuild.
- **`docs/contracts/DATASET_SPEC.md`** — §6.1 channels/dev-window rows, §6.2
  scale expectations, §6.4 funding status, §6.5 declared list updated.
- **`docs/decisions/DECISION_REGISTER.md`** — D-041 row.
- No code or test changed in this pass. Monograph rebuilt; suite untouched
  (112 tests).

## 2026-08-01 — Full-program target (D-040, owner)

- **D-040 registered** — the v0.1-only framing is retired; the program target
  is the full 8-phase roadmap with the evidence gates unchanged (rules 5-6,
  12, 14). Build priority completes Phases 0-4 first; the critical path is the
  Phase-4 `v8_slice_001` experiment runner + D-027 verdict gating. Phases 5/7
  are built only when their gate passes — never on a calendar date.
- **`docs/PLAN_V8_FULL.md` added** — sprint breakdown (Sprint A: Phase-4
  runner; Sprint B: Phase 2/3 completion; Sprint C: Phase 6 ops;
  data-blocked: derivatives tape, holdout window). Planning artifact, not
  registered in the monograph NAMES list (no TR mirror).
- **`docs/ROADMAP.md` updated** — the versioning line no longer frames the
  program as "v0.1 = Phase 0-4 foundation"; the full roadmap is the target.
- No code, contract, or test changed in this pass. Monograph rebuilt; suite
  untouched (112 tests).

## 2026-08-01 — Session-6 bugfix pass (adversarial audit fixes)

Adversarial bug hunt (11 class-scoped finders + per-finding verification) on
`src/v8/` + `tools/` confirmed 26 findings; this pass fixes them. Decision-path
changes move the golden ledger hash (outcome-label change) and are re-pinned in
`tests/test_golden_backtest.py`; candidate counts and terminal distribution are
unchanged. New regression tests: `tests/test_bugfix_pass.py` (11 tests). Full
suite 86 → 97.

- **`src/v8/lab.py`** — closed-only bars in the decision loop (open klines no
  longer drive entries/stops); multi-instrument tapes fail closed (H1/M5);
  duplicate decision clocks fail closed (M6); pre-entry invalidation re-checked
  on the entry bar (H3); `INVALIDATED_BEFORE_TRIGGER` relabelled `NOT_EXECUTED`
  (H5); counterfactual now applies the owning Expert's `still_valid` via a
  per-clock state map (H2); `prior_low/prior_high` fail closed instead of
  defaulting to 0/inf (M10); `_INTERVAL_NS` fails closed on unknown intervals
  (M12); `excess_cost` threshold promoted to named `EXCESS_COST_THRESHOLD_R`.
- **`src/v8/simulator.py`** — `run()` gains `thesis_valid(bar_time, payload)`
  so the batch counterfactual exits `THESIS_INVALIDATED` like the executed path;
  every returned outcome carries `label_available_time` (exit clock), the
  DATASET_SPEC section 4.5 embargo primitive.
- **`src/v8/schema.py` / `tools/materialize_views.py`** — `CounterfactualOutcome`
  and the `candidate_outcomes` view now expose `label_available_time`, so a
  training consumer can refuse labels whose availability overlaps its
  validation window (M4).
- **`src/v8/risk.py`** — D-024 funding-window veto measures boundaries on
  absolute wall-clock hours (`funding_hours * HOUR_NS`), matching
  `simulator._boundaries_crossed`; on non-1h tapes the old period missed
  imminent-boundary entries (H4).
- **`src/v8/marketstate.py`** — a universe symbol with zero emitted features
  degrades the state (DEGRADED), closing the missing-symbol quality gap (M2).
- **`src/v8/lifecycle.py`** — `any terminal -> ARCHIVED` added to `LEGAL`
  (CANDIDATE_LIFECYCLE_SPEC), making ARCHIVED reachable (M9).
- **`tools/monitor_tape.py`** — OHLC type/finiteness/invariant + volume checks
  (booleans, NaN/±inf, high<low, negative volume all fail); staleness measures
  kline rows only (M1/M7/L3).
- **`tools/vision_backfill.py`** — `audit_tape` gains OHLC/volume/finiteness
  invariants; `check_archive_revision` also guards legacy single-month
  `source.json` (M1/M8).
- **`tools/data.py`** — `_validate_price_rows` fails closed on NaN/±inf prices
  (M1).
- **`tools/materialize_views.py`** — `views_manifest.json` now carries a
  `views_pin` binding view SQL + manifest economics + code hash + views_dir;
  a recompile with a changed pin fails closed instead of silently replacing
  the "pinned" views (M11).

## 2026-08-01 — Session-6 second-level audit fixes (post-fix classes)

Second adversarial pass on the POST-FIX codebase (8 class-scoped finders:
alternative paths, boundary matrix, fail-open, hash canary, state coverage,
feature contamination, zero-trade provenance, reconciliation; 29 agents).
Confirmed 13 findings; this entry fixes them. Suite 104 → 108 (new regression
tests in `tests/test_bugfix_pass.py`); golden re-pinned (candidate_count
24 → 21: failed_breakout now gates on a windowed prior-high reference).

- **`src/v8/experts/failed_breakout.py`** — gate and anchor now share ONE
  prior-high reference (the history-window max excluding the newest bar). The
  old gate used the state's ALL-BARS prior_high, which an old spike outside the
  window pinned forever: the draft fired every bar, the anchor slid, and
  episode-key dedup silently produced a new DETECTED episode per bar. The
  post-entry thesis (`still_valid`) now uses a FROZEN `prior_high_ref`
  (excluded from episode identity like `atr_ref`), so a reversal that re-crosses
  the entry-time breakout level invalidates instead of drifting with the
  adverse move.
- **`src/v8/lab.py`** — `Lab.run` fails closed on a non-empty manifest
  `code_hash`/`data_hash` that does not match the live code/tape (the
  composition root no longer reports a stale or forged pin; materialize_views
  already checked, Lab.run is the authority). `terminal_distribution` is now
  candidate-counted (a `CLOSED -> ARCHIVED` candidate appears once) and the
  report adds `rejection_distribution` (D-024 vs risk vs excess-cost), `tooling_hash`
  (tools/*.py, outside the decision-path hash), and the excess-cost/tape-end
  `label_available_time` fallback to `last_as_of` (the 0-sentinel leak).
- **`src/v8/risk.py`** — the D-024 FUNDING_WINDOW veto fires whenever
  `window >= period` (a boundary always books funding on the first post-entry
  step; the old `window < period` guard silently disabled the check, so e.g.
  1d bars with funding_hours=8 admitted entries that settled 3x). The veto
  clock basis is the entry FILL time (available), matching simulator settlement.
- **`src/v8/schema.py`** — `LabReport.rejection_distribution`, `tooling_hash`.
- **`src/v8/experts/`** — no other changes; the trend_pullback thesis remains
  a live trend reference (correct by design).

## 2026-08-01 — Session-6 provenance + performance fixes (B1-B4, P1-P3)

Follow-up audit (parallel session) confirmed 4 ledger/provenance bugs + 3
structural performance items; this entry fixes them. The ledger hash now binds
the run configuration, so the golden re-pins. Suite 108 → 112.

- **`src/v8/lab.py`** — B1: a TRIGGERED candidate with no entry bar before tape
  end records `INVALIDATED_BEFORE_TRIGGER`/`NOT_EXECUTED`/0.0 (label knowable at
  tape end) instead of the fabricated empty-tail counterfactual
  (`EXPIRY`/`RIGHT_CENSORED`/0.0 with a fake simulator hash) — a non-trade no
  longer merges into the censored population (B5 naming aligned with the
  INVALIDATED terminal). B2/B3: the manifest is persisted to
  `<store>/manifest.json` and the ledger hash binds `config_hash =
  sha1_hex(asdict(manifest))` — different economics AND an authority receipt
  added later both move the ledger hash (no silent re-labelling). P1: the
  per-bar state build is O(N) incremental (moving pointer over the replay-sorted
  tape) instead of the O(N²) rescan that dominated run time.
- **`src/v8/lifecycle.py`** — B4: `CandidateRegistry` replay validates every
  `(from_state, to_state)` against LEGAL and raises on an illegal transition in
  a corrupt log (mutation-campaign fail-closed).
- **`src/v8/store.py`** — P2: `AppendOnlyLog` opens the append handle once and
  flushes per record (per-record open/close was ~half the profiled append cost);
  crash-loss policy stays bounded to the current record.
- **`src/v8/simulator.py`** — P3: `_boundaries_crossed` is O(1)
  (`floor(t/P) - floor(entry/P)`), byte-identical over the 144-case boundary
  matrix vs the per-hour loop.
- **`src/v8/marketstate.py`** — P1: the 5/20 EMA series are computed once and
  shared by the trend features and the history tuples (was computed twice per
  state).

## 2026-08-01 — Declared dataset v0.1 (operator)

- **D-039 — `DATASET_SPEC` §6 "Declared dataset v0.1" added.** The corpus had
  no declaration of what the dataset is or at what scale; this closes it.
  Declares: universe BTCUSDT (O-011 lock), 1h interval, channels `kline`
  (ingested) + `funding` (**declared, ingestion pending**), dev window
  2026-04..06 (hash `8b12707e…`), frozen OOS = first two published months
  after 2026-07-01 + 9-bar label extension (downloaded only at experiment
  time). Scale expectations table is measured (1h tape is small by
  construction: ~640 B/row; full history ~33 MB; 30 symbols ~1 GB; Tier-A/S
  gated by O-010). "More data" is now a register decision, never a silent
  download.
- **Funding gap made explicit and actionable:** simulator funding plumbing
  exists but `funding_rate_r = 0.0` (dev manifest + preregistration §8) — the
  channel is now declared with ingestion pending; next step is
  `GET /fapi/v1/fundingRate` backfill -> `funding` tape rows ->
  `funding_settled_r = entry_price × rate / risk_unit` -> preregistration §8
  revision, all before the holdout is opened (§16).
- Rebuilt `site/index.html` (32 sections — new probe baseline for the next
  session).

## 2026-08-01 — O-017 ratification + preregistration promoted (operator)

- **O-017 resolved by operator ratification** (2026-08-01):
  `execution_share` floor = **0.25** (60% of the dev-window 0.4156) and
  population-divergence threshold = **two-sample KS on `net_R` ≤ 0.20**
  (~2.7× the dev-window 0.073). Both were derived pre-holdout from the
  session-2 baseline (`v8-dev-2026q2-btcusdt`) and are fixed forever — never
  revisable after a verdict. Moved from the open list to a Resolved section
  in `OPEN_DECISIONS.md`; D-027 register entry updated.
- **`PREREGISTRATION_V8_SLICE_001.md` status RATIFIED** (was "frozen content
  for operator approval"); §16(a) marked DONE. The document is now registered
  in `tools/build_monograph.py` NAMES and appears in the monograph (section
  count 31 -> 32).
- The experiment is still **not run**: the frozen holdout does not exist
  until experiment time, no authority receipt exists, and every run's verdict
  stays `NO_ECONOMIC_CLAIM` (rules 8-9, 12).
- Rebuilt `site/index.html` (new probe baseline for the next session).

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
