# Post-Entry Predicate IR Specification

**Status:** PROVISIONAL_DECISION (D-082). This contract defines how an Expert's
post-entry thesis check (`still_valid`) is compiled into data that the replay
kernel evaluates natively, so that the compute plane never re-enters Python
(`COMPUTE_CORE_SPEC` §3). The surface measurement in §2 is
PROJECT_EVIDENCE_SUPPORTED; the IR design is DESIGN_INFERENCE until its
equivalence gate passes. No economic claim (rule 12).

## 1. Why an IR rather than a callback

The canonical simulator consults the owning Expert's thesis on every stepped
bar: a thesis that dies before price does closes the position at that bar's
close (`THESIS_INVALIDATED`) instead of being held to STOP/TARGET/EXPIRY. In
V8.0 this is a Python closure passed into `sim.run(..., thesis_valid=...)`.

Inside a native kernel that closure is not merely slow — it is structurally
inadmissible (`COMPUTE_CORE_SPEC` §3). The thesis must therefore be available
to the kernel as **data compiled ahead of time**, and it must mean exactly what
the Python method means, or the counterfactual and executed populations are
evaluated under different exit policies — the precise failure the
`thesis_valid` hook exists to prevent.

## 2. The measured surface

Extracted by AST from `src/v8/experts/*.py` (28 modules; the registry's 28th,
`fib_rsi_bb_confluence`, is D-076):

| Expert | Lines | Live features read |
|---|---|---|
| `bollinger_breakout` | 24 | `close` |
| `bollinger_reversion` | 25 | `close`, `ema_fast`, `ema_slow` |
| `breakout_retest` | 15 | `close` |
| `candlestick_reversal` | 16 | `close` |
| `divergence_12_setups` | 28 | `close` |
| `donchian_breakout` | 35 | `close`, `history`, `window_high_`, `window_low_` |
| `failed_breakout` | 22 | `close`, `prior_high` |
| `failed_breakout_2b` | 15 | `close` |
| `fib_projection_reversal` | 19 | `close` |
| `fib_retracement_continuation` | 21 | `close` |
| `fib_rsi_bb_confluence` | 31 | `close`, `rsi14` |
| `floor_trader_pivot` | 15 | `close` |
| `funding_crowding_reversal` | 20 | `close` |
| `gap_exhaustion` | 17 | `close` |
| `ichimoku_cloud` | 22 | `close`, `history` |
| `liquidity_sweep_reclaim` | 20 | `close` |
| `macd_stoch_trend` | 14 | `macd` |
| `market_profile_value_area` | 21 | `close` |
| `obv_adl_regime` | 18 | `close` |
| `open_interest_divergence` | 20 | `close` |
| `pandf_breakout` | 21 | `close` |
| `pattern_measuring_objective` | 15 | `close` |
| `range_breakout_1to1` | 16 | `close` |
| `rsi_stoch_reversion` | 32 | `cci20`, `rsi14`, `stoch_k` |
| `trend_pullback` | 9 | `ema_fast`, `ema_slow` |
| `trend_pullback_depth` | 18 | `close`, `ema_fast`, `ema_slow` |
| `volume_climax_reversal` | 19 | `close` |
| `volume_confirmed_breakout` | 19 | `close` |

**567 lines across 28 predicates, mean 20.** The complete live-feature
vocabulary is eleven names:

```text
cci20  close  ema_fast  ema_slow  history  macd
prior_high  rsi14  stoch_k  window_high_  window_low_
```

Nineteen of the 28 read only `close`; 26 of 28 read only scalar features. Two
(`donchian_breakout`, `ichimoku_cloud`) read `history` and need the windowed
form in §4.

The canonical shape is a direction-sensitive comparison of one live feature
against a **frozen** reference captured in `risk_geometry` at birth:

```python
ref = geom.get('upper_2sd_ref' if long else 'lower_2sd_ref')
if ref is None:
    return True                       # unobservable input fails OPEN
return c > float(ref) if long else c < float(ref)
```

## 3. Core IR

```text
Predicate  := Dispatch(cases: [ (GeomKeyPresent, Rule) ], default: Rule)
Rule       := FailOpen
            | Compare { lhs: Operand, op: Op, rhs: Operand, orient: Orient }
            | AllOf([Rule]) | AnyOf([Rule])
Operand    := LiveFeature(name)        # from the eleven-name vocabulary
            | FrozenRef(geom_key)      # captured at birth, immutable
            | Const(f64)
            | WindowAgg { feature, n, agg }        # §4
Op         := GT | LT | GTE | LTE
Orient     := AS_WRITTEN | FLIP_ON_SHORT
Agg        := MAX | MIN
```

Semantics, which are normative because they reproduce V8.0 behaviour exactly:

1. **Fail-open on absence.** If any operand resolves to absent — a missing
   geometry key, a feature not present in the projection, or a `None` value —
   the rule yields `true` (thesis still valid). Price, not the thesis, governs
   the exit. Fail-*closed* here would silently convert data absence into a
   forced exit and change the outcome population.
2. **`FLIP_ON_SHORT`** applies the comparison as written for `LONG` and with
   the operator reversed for `SHORT`. The direction is frozen on the Candidate
   and never re-read from state.
3. **Dispatch is ordered.** Cases are evaluated in declaration order and the
   first whose geometry key is present wins; this mirrors the `if 'x' in geom
   … elif 'y' in geom … else` chains in the sources.
4. **Frozen references are values, not lookups.** A `FrozenRef` is materialized
   into the compiled Candidate at birth. The kernel never reads a MarketState
   for it, which is what keeps the cell's read set bounded
   (`OUTCOME_CUBE_SPEC` §5).
5. **Live features are read at the stepped bar** from the dataset's feature
   columns at that bar index — never from a later bar, and never from a
   feature whose availability clock exceeds the bar's decision clock.

## 4. The windowed form

`donchian_breakout` and `ichimoku_cloud` consult a window rather than a scalar.
`WindowAgg { feature, n, agg }` covers both: a max/min over the last `n` values
of a feature column ending at the stepped bar, inclusive. `n` is a declared
constant taken from the Expert's frozen declaration, never data-dependent.

If a future Expert needs a thesis that this form cannot express, the correct
response is **not** to add a callback. Either the form is extended by a
registered decision, or the Expert declares no post-entry thesis and its
positions are governed by price alone. The IR's expressiveness is a contract
surface, not an implementation convenience.

## 5. Compilation and identity

Compilation happens in the control plane, once per Candidate batch:

```text
Expert declaration  ──►  Predicate IR  ──►  compiled bytes in CompiledCandidate
```

- The compiled predicate carries a `predicate_version` derived from the IR
  bytes. It participates in the Candidate's identity, so a thesis change
  re-versions every cell that consulted it
  (`PARITY_AND_IDENTITY_SPEC` §6).
- The IR is emitted in the canonical byte encoding
  (`PARITY_AND_IDENTITY_SPEC` §4), so its hash is runtime-independent.
- An Expert whose `still_valid` cannot be compiled fails **closed at
  compilation time**, loudly, listing the construct that defeated the compiler.
  It is never silently treated as fail-open, and it is never quietly replaced
  by a Python callback.

## 6. Equivalence gate

A compiled predicate is accepted only when it is shown equivalent to the Python
method it replaces:

| # | Condition |
|---|---|
| E1 | **Differential test:** over a generated grid of (direction, geometry, feature-value) tuples covering present/absent for every operand, the compiled predicate and `still_valid` agree on every input |
| E2 | Absence handling is exercised explicitly: each operand is tested missing, `None`, and present |
| E3 | Both directions are tested for every predicate, including the degenerate case where the frozen ref equals the live value (boundary, not just strict inequality) |
| E4 | **Replay parity:** on the V8.0 candidate population, the outcome produced with the compiled predicate is bit-identical to the outcome produced with the Python closure — same endpoint, same `net_r`, same horizon, same `label_status` |
| E5 | The eleven-name vocabulary is closed: a predicate referencing any other feature fails compilation |

E4 is the load-bearing gate. E1-E3 test the predicate in isolation; only E4
proves that the exit policy the counterfactual population is evaluated under is
the same one the executed population saw.

## 7. Cheap executable tests

1. Every registered Expert's `still_valid` compiles, or is explicitly declared
   thesis-free; there is no third state.
2. The extracted live-feature vocabulary equals the eleven declared names; a
   new Expert widening it fails the registry test until the vocabulary is
   extended by decision.
3. A predicate whose frozen ref is absent returns `true` for every live value
   (fail-open), in both directions.
4. Removing one case from a `Dispatch` changes at least one E1 grid outcome —
   i.e. the grid actually discriminates the cases.
5. A mutated compiled predicate (one operator flipped) fails E4 on the real
   candidate population.

## 8. Evidence and citations

- **PROJECT_EVIDENCE_SUPPORTED:** the table in §2 — 28 implementations, 567
  lines, the eleven-name vocabulary, and the 19/28 `close`-only share —
  extracted by AST from the sources in this repository.
- **PROJECT_EVIDENCE_SUPPORTED:** the fail-open convention and the frozen-ref
  pattern are quoted from `src/v8/experts/bollinger_breakout.py`, whose
  docstring states the rule ("Unobservable inputs fail open (price still
  governs)").
- **DESIGN_INFERENCE:** the IR grammar, the windowed form, the compilation and
  identity rules, and the equivalence gate.
- **Not claimed:** that the IR is sufficient for Experts not yet written. §4
  states the response when it is not — extend by decision, or declare no
  thesis. Adding a callback is excluded by `COMPUTE_CORE_SPEC` §3.
