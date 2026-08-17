# V8.2 Compute-Core Migration — Status Report

**Date:** 2026-08-16 · **Session:** autonomous build session 6
**Oracle tree hash (frozen):** `184fb934c8d6071d03db76ade1ea5d462f0e1f25`
(`git rev-parse HEAD:src/v8` — any change to `src/v8` invalidates every parity
result recorded below).

## Summary

The V8.2 Rust compute plane migration (`COMPUTE_CORE_SPEC` §8) now has the
S0–S7 surfaces implemented: ingest, state/features, predicate/replay,
cube/regret, candidate/evaluation loop, cache/evidence, analysis, verdict,
report/audit, and the backend boundary. All 28 registered Expert families are
present in the Rust registry. An optional Linux Vulkan f64 K4 backend is
implemented under D-098; CPU remains the reference and unsupported GPU cells
fail closed or route through CPU.

Local gates currently pass: 200 GPU-feature tests, 198 release tests, strict
Clippy, format check, Linux-target GPU check, and GPU-feature release build.
The only missing receipt is execution of `gpu-probe`/`gpu-parity` on a physical
Linux Vulkan adapter exposing `SHADER_F64`; the Apple development host reports
that capability unavailable by design. No speed or economic claim is made.

## Completed stages (evidence in `reports/parity/`)

| Stage | Commit | Gate evidence | Status |
|---|---|---|---|
| S0 — parity harness + Dataset ingest | `f6c1909` | `reports/parity/S0.md`: tape round-trips, three clocks preserved; G1-G6 on synthetic + real tapes | DONE |
| S1 — FeatureStore + StateView | `926965f` | `reports/parity/S1.md`: value parity on EVERY bar x EVERY feature (all 77); G1-G6; state_id mutation property | DONE |
| S2 — Predicate IR + ReplayKernel | `3a23ef8` | `reports/parity/S2.md`: E1-E5 (738-point predicate grid over all 28 experts), E4 replay parity on the V8.0 candidate population; G4-G6 | DONE |
| S3 — CubeReducer + streaming regret | `8851fad` | `reports/parity/S3.md`: reduced tables match `tools/regret.py` Phase-0 on every BOUND Candidate; gap>=0; G4-G6 | DONE |

Also recorded: the D-085 fast-cache module was committed as one unit
(`079394a`), and the migration plan + workspace decisions are registered
(D-087..D-090).

## Cross-stage determinism findings (LOCKED for the remaining stages)

1. **CPython `sum()` is compensated summation** (`_PyFloat_Fsum` =
   `math.fsum`), not a left fold — a fold drifts by ulps on ~20-element
   windows. `state::fsum` is a verbatim port incl. the special final fold and
   the half-even tie fix. (S1, pinned by a unit-test battery.)
2. **`x ** 2` and `x ** 0.5` are libm `pow`**, which differ from `x*x` /
   `sqrt(x)` by 1 ulp on some values; LLVM folds `pow(x, 2.0) -> x*x` in
   release, so the exponents are `black_box`'d to force the libm call. (S1.)
3. **serde_json's default float parser is not correctly rounded** (measured:
   `"0.9632136759338213"` parses 1 ulp low) — `float_roundtrip` is enabled;
   request-side floats must parse exactly. (S2.)
4. **Fail-open is not uniform** in `still_valid`: per-operand vs
   whole-condition — the IR's `guard` node captures the distinction; and
   `fib_rsi_bb_confluence`'s prior_low_ref valid-form is GTE (the equality
   boundary holds) while the 3sd rule is GT. (S2.)
5. The tape itself is parsed by `jsonx` (std's correctly-rounded parse), so
   tape values were never affected by finding 3.

## Historical next steps (session 5; closed by session 6)

### S4 — CandidateBuffer + ExpertPlane (the candidate population gate)

**Done this session:** `v8-core/src/candidate.rs` (episode_key anchored to
setup_anchor_event_id, CandidateRegistry/is_duplicate, the LEGAL/TERMINAL
transition map, ExposureBook, RiskGate with heat caps, the D-024 tradability
mask); `v8-core/src/experts/port.rs` (the evaluate-port framework with
`find_setup_anchor` + FeatMap) with the **three pilots ported and proven**:
`tests/parity/test_parity_s4.py` compares every bar's Rust draft against the
Python lab's evaluations — decision, direction, birth_time, risk_geometry and
setup anchor match bit-for-bit. `v8-core evaluate-check` (batch) subcommand.

**Historical remaining list:** the other 25 `evaluate()` ports (each needs its setup
predicate + geometry + anchor transcribed from the source; the anchor is NOT
uniform — `volume_climax_reversal` anchors at the detection bar, `pandf`
at the P&F column start, `rsi_stoch_reversion`/`macd_stoch_trend` replicate
run-start semantics with a local `_run_start`), and the full per-bar loop
(Phases 1a/1b/2/3: entry, step, trigger, evaluate) + the candidate-population
parity harness. The lifecycle/admission machinery in candidate.rs is built
and ready to wire. The `evaluate` subcommand that runs the loop is the
composition point.

**Closed in session 6:** all registered Expert ports and the full per-bar loop
are now wired in `v8-core`; the Python source remains a historical oracle.

**Historical pin (O-030):** S4 stayed last — porting the moving expert spec was deferred;
the plan is to port it after S3, which is now done.

### S5 — EvidenceStore + DAG cache

- `v8-core/src/evidence.rs` is already the columnar writer (S0). Extend it to
  the state/candidate/outcome/evaluation/cube artifacts with the
  `IDENTITY_ONLY`/`VALUES`/`FULL` tiers and the artifact-header run-constants
  (LEDGER_FORMAT_SPEC §3-4).
- `v8-core/src/cache.rs`: the content-addressed DAG cache whose missing node
  is cube level — `(candidate_id, action_id, simulator_hash, data_hash) ->
  outcome`; a hit must never change the ledger identity (the gate).
- The gate: cache hit/miss produce the same ledger identity; the
  LEDGER_FORMAT_SPEC §8 cheap tests (round-trip, header completeness,
  byte-stability, tier honesty, no-decimal-floats scan, retention).

## Open pins / known bounds

- The donchian `responsive`/`significant_extreme` exit kinds are compiled in
  the IR table but not exercised by the E1 grid (module-local subclasses,
  not exported by the registry); they are exercised only if a fixture
  produces such a candidate.
- `FILL_AT_LIMIT` is ported but unexercised (no registered Expert declares
  `limit_price`).
- Multi-interval `build_multi_state` aggregation is not yet in the S1 gate
  (deferred with the interval port).
- Real-tape parity (btcusdt-1h-12m, multi-1h-4y) is exercised at S0/S1;
  candidate/cube parity fixtures are single-symbol synthetic.

## What was NOT claimed

No speed claim anywhere. The parity gates are correctness; the
`PERFORMANCE_AUDIT_V82` figures remain the comparison baseline for any future
measurement. The economic verdict stays `NO_ECONOMIC_CLAIM`.

## Scope revision — D-091 (2026-08-12)

D-091 revises the V8.2 plane split: the analysis, verdict and audit planes
join the Rust plane. The runtime is one Rust binary end to end — compute,
regret analysis phases 1-3, verdict statistics and report/audit artifacts —
with **no Python in the request path** (D-078 extended). Python is reduced to
the frozen parity oracle (`src/v8/`), the vendored `simtruth/` lab (D-022) and
pre-V8.2 dev/research tooling retired as its Rust equivalent lands.

The migration order S0..S5 was extended with **S6** (Analysis: reconciliation
+ regret phases 1-3) and **S7** (Verdict: statistics + report/audit artifacts)
by D-091; all four later stages are now implemented and locally gated. The
session-5 findings above remain historical provenance, not open work.

The port is tracked issue-based on GitHub (`ddawnlll/v8`):
- S4/S5/infra: epics #74-#76, tasks #77-#112 (`stage-s4`/`stage-s5` labels)
- S6/S7: epics #113-#114, tasks #115-#130 (`stage-s6`/`stage-s7` labels)

The S6/S7 scan surfaced three parity prerequisites that the issue bodies
carry: (a) **MT19937 bit-exact RNG parity** — `statistics.py` consumes CPython
`random` (`random()` = `genrand_res53`, not `getrandbits(53)/2**53`) — issue
#127; (b) **banker's rounding** in `select_block_size` (Python `round()` is
half-even; Rust `f64::round()` is half-away) — issue #128; (c)
`appendix_a_invariant` returns `InvariantCheck`, it does not raise by itself —
issue #124.
