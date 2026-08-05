# V8 Runtime and Scheduler Specification

**Status:** PROVISIONAL_DECISION. This spec defines what triggers an
evaluation, who owns state, and how replay stays deterministic. It is the
execution layer of the research runtime — the "runnable vertical-slice gates"
the project audit requires before any component is added.

## 1. Clock driver

The runtime advances a single **decision clock** `D`. The default driver is
**bar-driven**: a heartbeat loop advances `D` to the next bar boundary and
emits a `BarClosed(symbol, interval, bar)` event only when
`bar_available_time <= D` (`FEED_INGESTION_SPEC` §3). Events flow through a
FIFO queue; the inner loop dispatches them to experts, the lifecycle service,
acceptance, and the simulator in order. This is deterministic by construction
and fast enough for research.

Event-driven mode (discrete trade/depth events) is a later, explicitly gated
option: it raises fidelity but complicates total ordering, so it must clear a
preregistered incremental-value experiment before replacing the bar driver.

Rules:

- `D` is stored on every decision artifact as `knowledge_time`
  (`MARKET_STATE_CONTRACT` §1). Nothing in an evaluation may observe a fact
  with `available_time > D`.
- Never `time.time()` inside replay; the clock is driven by the tape.
- Integer nanosecond timestamps with explicit tie-breaks
  (`PERSISTENCE_REPLAY_SPEC` §4).

## 2. Evaluation triggers

| Trigger | Fires | Consumer |
|---|---|---|
| `BarClosed` | each closed bar, per symbol | all cheap self-gating experts; state builder |
| `TradeFlow` (optional) | aggTrade events when a declared feature needs them | state builder; experts that declare trade-level inputs |
| `FundingBoundary` | funding settlement times (venue schedule, versioned) | experts whose expiry/risk geometry depends on funding |
| `TimerTick` | declared cadence (e.g. hourly) | lifecycle service (expiry checks), lab runner |

The locked baseline is **full self-gating**: every inexpensive expert
evaluates every `BarClosed` event and returns `Candidate | None`
(`EXPERT_PROTOCOL` §3). A router is admitted only via its registry
experiment; it is absent by default (`V8_CONSTITUTION` rule 6).

## 3. Topology and state ownership

- The research runtime is currently a **single process**: components are
  modules with interface contracts (`Expert.evaluate`, `Lifecycle.apply`,
  `Simulator.step`, `Lab.run`), not services. There is no hidden shared
  mutable state; all cross-component information flows through `MarketState`
  values and append-only logs.
- Determinism rests on the **single writer plus a declared evaluation order**
  (Experts sorted by `expert_id`), not on the process count. This matters now
  that rule 14 leaves the Expert count unbounded: growing it is a throughput
  question, and a future multi-process or multi-threaded evaluation fan-out is
  an engineering change, not a validity change, as long as the single-writer
  discipline and the declared order are preserved.
- The **candidate lifecycle service owns transition legality**: only it may
  write `CandidateTransition` records, and only legal transitions pass
  (`CANDIDATE_LIFECYCLE_SPEC` §2).
- **Single writer, many readers:** the ingest pipeline is the only writer to
  the store; replay and research are read-only. Concurrency is restricted to
  the boundaries declared by `PERSISTENCE_REPLAY_SPEC` §3, and those
  boundaries are idempotent.
- Experts may be stateful only through append-only candidate history; hidden
  mutable state is forbidden (`EXPERT_PROTOCOL` §2).

## 4. Replay/live parity

The engine core is shared between replay and any future live mode; only the
data edge (tape file vs live adapter) and the execution edge (canonical
simulator vs a later shadow execution) swap. This is a design constraint now
so that a live mode, if ever admitted, cannot fork the research code path.

Per `V8_CONSTITUTION` rule 12 and the project evidence audit, **live execution
is not part of this runtime**: the current simulation authority is
uncertified, and no profitability, validated-execution, or promoted-system
claim is admissible until it is independently renewed.

## 5. Cheap executable tests

1. At `D < bar_available_time`, no `BarClosed` fires for that bar; requesting
   its OHLC returns `NOT_YET_AVAILABLE`.
2. Two events with identical timestamps are processed in the declared
   tie-break order, deterministically, across runs.
3. Shuffle the caller's Expert list; results and stored events are identical.
   The runtime sorts by `expert_id` before evaluating, so this holds under full
   exposure contention too, not only when Experts rarely coincide
   (`tests/test_admission_contention.py`). The surviving tie-break for a
   contested exposure slot is therefore that lexicographic order — deterministic
   but arbitrary; replacing it with a ranking is gated by rule 6 / D-008
   (O-006 / O-012).
4. A replay run and a live-adaptor contract test produce the same event
   stream for the same tape window.
5. An expert that reads a fact with `available_time > D` fails the state
   builder check before evaluation.

## 6. Evidence and citations

- **LITERATURE_SUPPORTED:** the bar-driven heartbeat + FIFO event queue
  pattern (event-driven backtesting loop): [QuantStart, Event-Driven Backtesting with Python](https://www.quantstart.com/articles/Event-Driven-Backtesting-with-Python-Part-I/).
- **LITERATURE_SUPPORTED:** one engine core with swappable data/execution
  edges so backtest and live share code is the NautilusTrader architectural
  pattern (event-driven engine design; not cited as evidence of edge).
- **DESIGN_INFERENCE:** the trigger table, single-process topology, and
  single-writer discipline are V8 choices that make determinism testable.
