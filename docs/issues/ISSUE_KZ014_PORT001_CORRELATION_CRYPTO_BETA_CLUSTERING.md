# Issue (KZ-014 / PORT-001): Cross-Asset Crypto-Beta Clustering & Portfolio Heat Allocation

## 1. Context & Normative Traceability
- **R1:** Implement cross-asset correlation clustering (BTC + ETH + SOL) in `v8-core/src/allocator.rs` to eliminate beta double-counting.
- **R2:** Replace independent symbol slot limits with cluster-level risk ceilings: $\sum_{s \in Cluster} Heat(s) \le MaxClusterHeat$.
- **R3:** Enforce priority routing: allocate capital to Tier-1 Sovereign Anchor (BTC) first before granting margin to high-beta satellite altcoins.
- **Traceability:** D-023, D-110, D-123, `docs/contracts/VENUE_AND_CAPITAL_SIMULATION_SPEC.md` §2.

## 2. Reused Types & Existing Contracts
- `v8_core::portfolio::PortfolioState`, `v8_core::allocator::RiskBudget`, `v8_core::types::ClusterRisk`.

## 3. Mathematical & Semantic Invariants
- **I1:** Cross-symbol rolling covariance matrix $\Sigma_t$ computed on closed bars (zero lookahead).
- **I2:** Total portfolio heat strictly capped at D-023 limit ($MaxHeat \le 3.0R$).
- **I3:** Outputs must emit `cross_asset_correlation_cube.parquet` and `cluster_heat_ledger.jsonl`.

## 4. Canonical Failure Semantics
- If correlation matrix is singular or non-positive-definite, fallback to 100% BTC-isolated exposure (fail safe).

## 5. Dependency & Composition Topology
- Predecessors: Issue #209 (ALLOC-001).
- Successors: Issue #210 (VERIFY-001).
