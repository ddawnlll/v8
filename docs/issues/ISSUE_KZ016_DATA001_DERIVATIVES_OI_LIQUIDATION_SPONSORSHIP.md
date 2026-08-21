# Issue (KZ-016 / DATA-001): Derivatives Tape Ingestion — Open Interest, Liquidation Clusters & Sponsorship

## 1. Context & Normative Traceability
- **R1:** Ingest Open Interest (`open_interest`), Liquidation Volume (`liquidations`), and Spot/Perp CVD channels into the PIT market tape.
- **R2:** Unblock the `open_interest_divergence` expert family from `DATA_BLOCKED` status to `FORMALIZED`.
- **R3:** Provide structural institutional sponsorship signals (OI accumulation, short squeeze exhaustion) to the Campaign Aggregator.
- **Traceability:** D-041, D-050, D-054, D-123, `FEED_INGESTION_SPEC` §1–4, `DATASET_SPEC` §6.

## 2. Reused Types & Existing Contracts
- `v8_core::data::TapeRow`, `v8_core::state::MarketState`, `v8_core::experts::open_interest_divergence`.

## 3. Mathematical & Semantic Invariants
- **I1:** Derivatives tape timestamps must strictly align with closed 1h klines without future lookahead.
- **I2:** Missing OI bars fail closed to `StateQuality::DEGRADED` rather than interpolating synthetic data.
- **I3:** Outputs must emit `derivatives_channel_manifest.json` and `oi_sponsorship_surface.parquet`.

## 4. Canonical Failure Semantics
- If derivatives data is corrupted or hash diverges, mark channel `DATA_BLOCKED` (fail safe).

## 5. Dependency & Composition Topology
- Predecessors: None (Data-plane foundation).
- Successors: Issue #205 (MEGA-001), Issue #207 (CAMP-001).
