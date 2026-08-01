# V8 Persistence and Replay Specification

**Status:** PROVISIONAL_DECISION. This spec gives the five `DATASET_SPEC`
storage layers a physical engine and defines the replay/crash-recovery
discipline that makes every research result reproducible.

## 1. Physical mapping of the storage layers

| `DATASET_SPEC` layer | Physical engine | Write pattern |
|---|---|---|
| Raw evidence | Partitioned **Parquet** (`dt=YYYY-MM-DD`), checksummed, immutable | Write once from the ingest pipeline; never modified |
| Decision ledger | **Append-only log** (JSONL) + **DuckDB** derived tables | Append-only; no `UPDATE`/`DELETE` |
| Execution ledger | Append-only log (same store, separate table) | Append-only |
| Outcome ledger | DuckDB tables, access-separated | Append-only |
| Research materializations | DuckDB tables generated from a pinned `ExperimentManifest` | Rebuilt, never edited |

Rationale: Parquet is the immutable columnar archive and interchange format;
DuckDB scans it directly with predicate pushdown, and provides ACID
transactions, MVCC snapshot isolation, and WAL plus checkpointing. DuckDB is
**single-writer** — the ingest pipeline is the only writer; replay and research
readers are read-only. The small append-only transition log may live in
SQLite (WAL mode) or plain JSONL at research scale; it is not the bar store.

## 2. Bitemporal and append-only modeling

Two orthogonal axes:

- **Valid time** — when the fact is true in the world (`event_time` on a tape
  row, bar open time on a bar).
- **Transaction time** — when the row was recorded (monotonic `ingested_seq`
  per source).

Rules:

- **Never `UPDATE`/`DELETE`.** A correction is a new row with the same valid
  time and a later transaction time; it supersedes the prior via an effective
  interval. This is how "what actually happened" and "what we believed at
  decision time D" coexist without backfill.
- Every table keyed with a source must carry `(source, valid_time,
  ingested_seq)` and a strictly monotonic `ingested_seq` per source — this is
  also the dedup key for idempotent ingestion.
- As-of queries filter `transaction_time <= query_time`. A decision at `D`
  can never observe a row ingested after `D` (`MARKET_STATE_CONTRACT` §1).

## 3. Event sourcing and crash recovery

- The **append-only event log is the source of truth.** Current state
  (candidate projections, MarketState caches) is a derived projection; replay
  of the log must reproduce it byte-identically (`CANDIDATE_LIFECYCLE_SPEC`
  §3).
- **Snapshots are derived caches:** version them, and invalidate them whenever
  fold logic changes. A snapshot that current code could never produce is the
  classic corruption bug.
- **WAL discipline:** log first, apply second. On restart, replay from the
  last durable checkpoint; both DuckDB and SQLite rely on this.
- **Idempotent ingestion:** at-least-once delivery with a unique constraint or
  inbox on `(source, event_id)`; an out-of-order or duplicated event is
  dropped against the inbox, never applied twice.

## 4. Determinism rules

- Use integer nanosecond timestamps and explicit tie-breaking on simultaneous
  events: `(venue, channel, sequence, received_sequence)`. Never call
  `time.time()` (or `NOW()`) inside replay; wall clock breaks replay
  idempotency.
- Replay must be stable across process restarts and library versions; a code
  change that alters the event stream requires a manifest/version bump, not
  silent recomputation.
- Hash-bound artifacts: raw manifests, feature graphs, code versions, and
  seeds are pinned in `ExperimentManifest`; a missing authority receipt blocks
  an economic verdict (`V8_CONSTITUTION` rules 8–9).

## 5. Cheap executable tests

1. Replay the full log twice; assert byte-identical state and hashes.
2. Inject a duplicate event (same `(source, event_id)`); the inbox must reject
   it and the log must remain unchanged.
3. Kill the process mid-write (simulated), restart, replay from the last
   checkpoint; assert the store is consistent and no partial event exists.
4. Revise a fact after `D`; an as-of rebuild at `D` must produce the prior
   hash, while a later rebuild may differ.
5. Insert a delisted instrument into the historical universe; it must appear
   before its end time and not after.
6. Refactor a fold and rerun a pinned manifest; the snapshot invalidation
   must trigger and the new snapshot must match the new fold.

## 6. Evidence and citations

- **LITERATURE_SUPPORTED:** DuckDB ACID transactions, WAL, and single-writer
  concurrency: [DuckDB transactions](https://duckdb.org/docs/lts/sql/statements/transactions),
  [analytics-optimized concurrent transactions](https://duckdb.org/2024/10/30/analytics-optimized-concurrent-transactions).
- **LITERATURE_SUPPORTED:** SQLite WAL mode for small single-writer logs:
  [SQLite WAL](https://www.sqlite.org/wal.html).
- **LITERATURE_SUPPORTED:** event sourcing and reconstruction of state from an
  append-only log: [Fowler, Event Sourcing](https://martinfowler.com/eaaDev/EventSourcing.html).
- **LITERATURE_SUPPORTED:** bitemporal modeling and correction-without-backfill:
  [Bitemporal modeling](https://en.wikipedia.org/wiki/Bitemporal_modeling).
- **DESIGN_INFERENCE:** the engine mapping in §1, the inbox dedup key, and the
  snapshot-invalidation rule are V8 choices; they are not claims about alpha.
