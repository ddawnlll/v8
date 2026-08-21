# Issue #221 (KZ-014 / PORT-001): Cross-Asset Crypto-Beta Clustering & Portfolio Heat Allocation

**Status:** RESOLVED & RATIFIED (D-123)

## 1. Context & Normative Traceability
- **R1:** Implement cross-asset correlation clustering (BTC + ETH + SOL) in `v8-core/src/allocator.rs` to eliminate beta double-counting.
- **R2:** Replace independent symbol slot limits with cluster-level risk ceilings: $\sum_{s \in Cluster} Heat(s) \le MaxClusterHeat$.
- **R3:** Test hierarchical asset priority hypothesis (BTC Anchor vs Relative Strength leaders) as an empirical allocation challenger.
- **Traceability:** D-023, D-110, D-123, `docs/contracts/VENUE_AND_CAPITAL_SIMULATION_SPEC.md` §2.

## 2. Reused Types & Existing Contracts
- `v8_core::portfolio::PortfolioState`, `v8_core::allocator::RiskBudget`, `v8_core::types::ClusterRisk`.

## 3. Mathematical & Semantic Invariants
- **I1:** Cross-symbol rolling covariance matrix $\Sigma_t$ computed on closed bars (zero lookahead).
- **I2:** Total portfolio heat strictly capped at D-023 limit ($MaxHeat \le 3.0R$).
- **I3:** Outputs must emit `cross_asset_correlation_cube.parquet` and `cluster_heat_ledger.jsonl`.

## 4. Canonical Failure Semantics
- If covariance matrix is singular, non-positive-definite, or data is missing, assume worst-case correlation $\rho = 1.0$, group all crypto-beta into a single conservative cluster, and disallow new correlated exposure (fail safe).

## 5. Dependency & Composition Topology
- Predecessors: #217 (ALLOC-001).
- Successors: #218 (VERIFY-001).
