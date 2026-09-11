# Perf pass: the per-bar decision record (2026-09-11)

Owner directive: solve the backtest/benchmark performance problem, and agents may
not self-impose sleeps longer than 10 seconds. These are the measured numbers, not
estimates — every figure below came from a command in this document.

## What was slow (measured, not guessed)

`cProfile` over `python -m v8_next.app.portfolio --output-dir artifacts/perf/pf`
(385 real quad bars, P vs P+E), 10.79s profiled, ordered by internal time:

| # | hot spot | calls | tottime | cumtime |
|---|---|---|---|---|
| 1 | `dataclasses._asdict_inner` | 3,322,545 | 1.17s | 2.42s |
| 2 | `dataclasses.replace` | 499,051 | 0.99s | 1.88s |
| 3 | `PyLazyFrame.collect` | 43,679 | 0.75s | 0.75s |
| 4 | `builtins.getattr` | 7,197,580 | 0.45s | 0.45s |
| 5 | `registry.observe_expert` | 301,840 | 0.29s | 5.68s |
| 6 | `dataclasses.fields` | 302,131 | 0.28s | 0.50s |
| 7 | `copy.deepcopy` | 325,313 | 0.26s | 0.40s |

Root cause: the innermost loop (`bars x curves x legs x 28 experts`) converted
every `Stance` to a dict with `dataclasses.asdict()` — which recurses, re-derives
the field list per call and `deepcopy`s every non-container value (including the
`StanceKind` enum) — and then rebuilt every stance with `dataclasses.replace()`
just to stamp the witness metadata (same field re-derivation + deepcopy).

`Stance` (10 fields) and `Opportunity` (8 fields) are flat frozen dataclasses with
scalar fields only, so none of that machinery was buying anything.

## What changed

1. `economics/decisions.py`: `STANCE_FIELDS` / `OPPORTUNITY_FIELDS` resolved once at
   import, plus `stance_record()` / `opportunity_record()` — flat attribute copies.
2. `adapters/expert_strategy.py`: the per-bar decision record uses those instead of
   `asdict` (the call site that produced 302k asdict calls per run).
3. `experts/registry.py`: witness metadata is stamped by building the stance from
   its own instance dict merged with the metadata — no `replace`, no deepcopy, and
   a field added later still flows through.
4. `evaluation/gate_resolution.py`: `DEFAULT_TAPE_PATH` is now anchored to the
   repository root (with a `V8_TAPE_PATH` override) instead of the bare relative
   path `research/tape/...`. A cwd-relative default is a correctness defect that
   looks like speed: `if DEFAULT_TAPE_PATH.exists()` (G5 regime fallback) silently
   did not run when a process started outside the repo root, so the same nominal
   run graded G5 differently depending on where it was launched — and every
   real-tape test guarding on the same constant skipped instead of running.

Equivalence is pinned, not asserted in prose: `tests/test_perf_hot_paths.py`
compares the new records to `asdict` field-by-field for all 28 canonical experts on
the real BTC tape, and compares the registry's witness-stamped stance to the old
`dataclasses.replace` path for all 28.

## Measured after — corrected, with the counting method stated

Two rounds of the same fix (cProfile over `python -m v8_next.app.portfolio`, same
command, same machine). Call counts come from the profiler's own statistics, so
they do not depend on system load:

| profile | profiled CPU total | `_asdict_inner` calls | `deepcopy` calls |
|---|---|---|---|
| BEFORE | **10.79 s** | 302,090 top-level (3.32 M recursive) | 627,147 |
| AFTER-1 (flat records replacing `asdict`) | **8.33 s** | **5** | 23,467 |
| AFTER-2 (experts stamp variant/version without `replace`) | **7.07 s** | 5 | 23,467 |

Net on the profiled CPU work: **10.79 s → 7.07 s (-34.5%)**, with the recursive
`asdict` plumbing effectively eliminated (302,090 → 5).

Wall clock is **load-sensitive on this machine** and must be quoted with its load
average, which is why an earlier interim number was wrong:

| when | load avg | wall clock |
|---|---|---|
| baseline, start of the pass | ~4 | 6.10 s / 6.01 s |
| interim re-check (before the expert-side fix) | 5.87 | 6.17 / 5.97 / 6.14 s |
| after the expert-side fix | 3.44 | **4.92 / 4.61 / 4.65 s** |

The interim re-check is why this section was rewritten: the earlier "6.10 → 4.81"
claim could not be reproduced under load 5.87, and a wall-clock figure that only
holds when the machine is idle is not a measurement worth publishing. The
load-independent numbers above are the ones to trust; the wall clock is reported
with the condition it was taken under.

Verification: `tests/test_perf_hot_paths.py` (7 tests: record equality against
`asdict` for all 28 experts, `stance_with` equality against `replace` in every
kwarg shape, the registry witness-stamping equivalence, a speed guard, and a guard
that the experts still stamp their variants) plus the full suite: **849 passed**.

## Remaining measured cost (next targets, in profile order)

* `PyLazyFrame.collect` — 43,679 polars collects over a run; the per-bar frame
  build collects a lazy frame instead of materialising once.
* `observe_expert` — after this pass the remaining cost is the observers' own
  computation, not dataclass plumbing (`replace` is now confined to the 10,780
  per-bar `Candle` copies in `domain/market.py:from_ordered_prefix`).
* Import time (`_imp.create_dynamic` 0.40 s) — module-level imports, not a hot path.
* `block_bootstrap_ci` (0.36s / 40 calls) — statistical battery, kept as is:
  it is the evidence, not overhead.

## Operating rule (owner directive)

Agents must not block on a sleep longer than 10 seconds; run slow work with
`terminal(background=true, notify=true)`, poll a bounded interval, or wait on the
real artifact/process handle. Framing: waiting is not work, and a blind multi-minute
sleep makes a stalled step indistinguishable from a slow one.

Note: the write of this rule into the root `AGENTS.md` was blocked by the
protected-file approval prompt (it timed out with no answer), so the rule lives
here until the owner approves that edit.
