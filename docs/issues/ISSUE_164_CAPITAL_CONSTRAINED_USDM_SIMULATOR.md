# [IMPL] Issue #164: Implement Capital-Constrained Binance USDⓈ-M Portfolio Simulator & 4-Part State Machine in v8-core

**Status:** RESOLVED / VERIFIED  
**Issue Type:** `IMPLEMENTATION`  
**Change Class:** `NEW_FILE_FAMILY_OR_MODULE` / `CONTRACT_IMPLEMENTATION`  
**Labels:** `type:implementation`, `triage`, `risk:economic-authority`  
**Owning Authority:** `VENUE_AND_CAPITAL_SIMULATION_SPEC.md` §§1–11, Decisions `D-028A`, `D-028B`, `D-109`, `D-110`, `D-111`, `D-112`, `D-113`, `D-114`, `D-115`, `D-116`.

---

## 1. Objective
Implement the authoritative finite-capital exchange simulation engine and 4-part state machine in pure Rust (`v8-core`), transitioning V8 from dimensionless, unconstrained $R$-space replay to physical, venue-realizable monetary performance ($\text{USDT}$-space) under Binance USDⓈ-M exchange rules.

---

## 2. Owning Authority
- **Primary Specification:** [`docs/contracts/VENUE_AND_CAPITAL_SIMULATION_SPEC.md`](file:///c:/Users/dresden/Documents/v8/docs/contracts/VENUE_AND_CAPITAL_SIMULATION_SPEC.md) §§1–11
- **Oracle Specification:** [`docs/contracts/TARGET_ORACLE_SPEC.md`](file:///c:/Users/dresden/Documents/v8/docs/contracts/TARGET_ORACLE_SPEC.md) §§1–8, §16, §19
- **Truth Specification:** [`docs/contracts/SIMULATION_TRUTH_SPEC.md`](file:///c:/Users/dresden/Documents/v8/docs/contracts/SIMULATION_TRUTH_SPEC.md) §§1–5
- **Formal Decisions:**
  - `D-028A`: Declared price-distance risk unit ($R_{\text{price}}$).
  - `D-028B`: Capital-risk normalized multiple ($R_{\text{norm}} = \text{PnL}_{\text{USDT}} / R_{\text{effective}}$).
  - `D-109`: Formal decoupling of $R$-space diagnostics from $\text{USDT}$-space economics.
  - `D-110`: 4-part state ontology (`MarketState`, `VenueState`, `AccountState`, `PortfolioState`).
  - `D-111`: Binance USDⓈ-M as a versioned `VenueContract`.
  - `D-112`: Dual Hindsight Oracle architecture (Local Candidate Ceiling vs Capital-Constrained Portfolio Ceiling $V^*(S_t)$).
  - `D-113`: Identifiability preconditions for `EconomicCaptureRatio`.
  - `D-114`: Multidimensional `ExecutionAuthorityProfile`.
  - `D-115`: Partial identification bounds (`OutcomeBound`) for intrabar order ambiguity.
  - `D-116`: Independent reference simulator cashflow verification.

---

## 3. Current State
- `v8-core` currently executes candidate episodes via `v8-core/src/runloop.rs` and `v8-core/src/exit_ablation.rs` using a scalar dimensionless $R$ metric under an implicit infinite-capital and single-trade independence assumption.
- `v8-core/src/quant.rs` has implemented 4D PIT regime classification, Brownian bridge ambiguity probabilities, TCA gross/net decomposition, and Sharpe/Kelly metrics, but the runtime lacks:
  1. Stateful account balances (`wallet_balance_usdt`, `available_balance_usdt`, `initial_margin_usdt`).
  2. Concrete `VenueContract<BinanceUsdM>` filter enforcement (`LOT_SIZE`, `PRICE_FILTER`, `MIN_NOTIONAL`, tiered leverage brackets).
  3. Physical `RiskBudgetAllocator` generating discretized order requests from equity fractions.
  4. 5-component `EconomicCashflow` event-driven transaction ledger.
  5. The path-dependent Capital-Constrained Portfolio Hindsight Oracle solver $V^*(S_t)$.

---

## 4. Required End State
1. **4-Part State Machine:**
   `DecisionState` struct in `v8-core` composed of `MarketState`, `VenueState`, `AccountState`, and `PortfolioState`.
2. **Binance USDⓈ-M Venue Contract:**
   `VenueContract` struct modeling exact Binance BTCUSDT perpetual rules (tickSize: 0.1, stepSize: 0.001, minNotional: 5.0 USDT, 125x leverage brackets, $MMR_k$ maintenance margin schedule, VIP0 maker 0.02% / taker 0.05% fee tiers).
3. **Risk Budget Allocator:**
   `RiskBudgetAllocator` computing nominal risk budget $B_{\text{USDT}} = E_t \times f_{\text{risk}}$, raw quantity $Q_{\text{raw}} = B_{\text{USDT}} / \Delta P_{\text{stop}}$, applying lot step rounding $\lfloor Q \rfloor_{\text{step}}$, and enforcing min notional, available margin, and concurrency slot legality.
4. **Typed Allocation Rejections:**
   Emits canonical failure codes (`INSUFFICIENT_AVAILABLE_BALANCE`, `MIN_NOTIONAL_REJECTED`, `QUANTITY_ROUNDS_TO_ZERO`, `MARGIN_LIMIT_EXCEEDED`, `LEVERAGE_CONSTRAINT`, `CAPITAL_CONSTRAINT_REJECTION`) instead of silent drops.
5. **5-Component Cashflow Ledger:**
   Emits `economic-cashflow.jsonl` recording `realized_market_pnl_usdt`, `commission_usdt`, `funding_cashflow_usdt`, `slippage_usdt`, `gap_through_stop_usdt`, and wallet transitions.
6. **Execution CLI Subcommand:**
   `v8-core usdm-sim --initial-balance 1000.0 --risk-fraction 0.005 --leverage 5` outputting `.audit/rust_audit_current/portfolio_receipt.json` with terminal equity, CAGR, Max Drawdown in %, margin utilization peak, total fee drag in USDT, and capital rejection counts.

---

## 5. Expected File / Module Surface
- `v8-core/src/venue.rs` [NEW]: `VenueContract`, `PriceFilter`, `LotSizeFilter`, `LeverageBracket`, `LiquidationModel`.
- `v8-core/src/account.rs` [NEW]: `AccountState`, `MarginMode`, `FeeTier`, wallet balance update math.
- `v8-core/src/portfolio.rs` [NEW]: `PortfolioState`, `OpenPosition`, `OpenOrder`, margin tracking, portfolio heat.
- `v8-core/src/allocator.rs` [NEW]: `RiskBudgetAllocator`, quantity discretization, slot contention gating, typed rejection emission.
- `v8-core/src/cashflow.rs` [NEW]: `EconomicCashflow`, ledger serialization, accounting conservation assertions.
- `v8-core/src/simulator.rs` [MODIFY]: Wire 4-part state discrete-event runner.
- `v8-core/src/main.rs` [MODIFY]: Expose `usdm-sim` subcommand.

---

## 6. Verification Gates
1. **Automated Unit Test Battery:**
   - `cargo test --manifest-path v8-core/Cargo.toml` (All tests pass, zero regressions).
   - `test_lot_size_discretization`: Verifies stepSize truncation and zero-rounding rejection.
   - `test_min_notional_filter`: Verifies orders $< 5.0\text{ USDT}$ fail closed with `MIN_NOTIONAL_REJECTED`.
   - `test_margin_exhaustion_rejection`: Verifies orders exceeding available balance fail with `INSUFFICIENT_AVAILABLE_BALANCE`.
   - `test_liquidation_price_isolated`: Verifies byte-exact match with Binance official liquidation formulas.
   - `test_cashflow_accounting_conservation`: Verifies $\Delta \text{Wallet} == \text{Gross} - \text{Fee} \pm \text{Funding} - \text{Slip}$ for every trade.
2. **Clippy Linter Gate:**
   - `cargo clippy --manifest-path v8-core/Cargo.toml --all-targets -- -D warnings` (0 errors, 0 warnings).
3. **Boundary Audits:**
   - `python tools/audit_python_boundary.py` (PASS).
   - `python tools/forbidden_names.py` (PASS).

---

## 7. Required Evidence Artifacts
- `.audit/rust_audit_current/economic-cashflow.jsonl` (Immutable append-only cashflows).
- `.audit/rust_audit_current/portfolio_receipt.json` (Structured execution summary).
- `walkthrough.md` updated with realized monetary equity curve and capacity sensitivity grid.

---

## 8. Non-Goals / Forbidden Scope
- **NO Online Trading / API Key Signing:** This is a deterministic research simulation engine; no live network calls or private key handlers.
- **NO In-Place Mutation of Frozen Python Oracle (`src/v8/`):** Pure Rust implementation in `v8-core/` only.
- **NO Learned RL / Black-Box Allocators:** Baseline allocation is deterministic fixed-fractional Kelly with mechanical risk caps.
- **NO Synthetic Price Excursions:** All execution paths derived strictly from historical closed bars and Point-in-Time tape features.

---

## 9. Normative Traceability

| Req ID | Requirement Description | Owning Authority | Reuse Surface |
| :---: | :--- | :--- | :--- |
| **R1** | Decouple $R$-space diagnostics from $\text{USDT}$-space monetary economics | `VENUE_AND_CAPITAL_SIMULATION_SPEC.md` §2, `D-109` | `quant.rs:TcaAttribution` |
| **R2** | Implement 4-part state ontology (`MarketState`, `VenueState`, `AccountState`, `PortfolioState`) | `VENUE_AND_CAPITAL_SIMULATION_SPEC.md` §3, `D-110` | `state.rs:MarketState` |
| **R3** | Implement versioned Binance USDⓈ-M `VenueContract` with lot/tick/notional/bracket rules | `VENUE_AND_CAPITAL_SIMULATION_SPEC.md` §4, `D-111` | `simulator.rs` |
| **R4** | Implement `RiskBudgetAllocator` with lot-step discretization and typed rejection codes | `VENUE_AND_CAPITAL_SIMULATION_SPEC.md` §6, `D-108` | `runloop.rs:dispatch_order` |
| **R5** | Implement 5-component `EconomicCashflow` ledger with conservation invariants | `VENUE_AND_CAPITAL_SIMULATION_SPEC.md` §7, `D-116` | `quant.rs:TcaAttribution` |
| **R6** | Implement Capital-Constrained Portfolio Hindsight Oracle ($V^*(S_t)$) | `VENUE_AND_CAPITAL_SIMULATION_SPEC.md` §8, `D-112` | `quant.rs:partition_by_regime` |
| **R7** | Implement multidimensional `ExecutionAuthorityProfile` | `VENUE_AND_CAPITAL_SIMULATION_SPEC.md` §5.1, `D-114` | `oracle/authority.rs` | <!-- AUDIT-DOC-PATHS: PLANNED_MODULE `oracle/authority.rs` is the target location for R7 work, not an implemented path; `v8-core/src/oracle/authority.rs` is the unrelated existing module. -->
| **R8** | Implement bounded partial identification (`OutcomeBound`) for intrabar ambiguity | `VENUE_AND_CAPITAL_SIMULATION_SPEC.md` §5.2, `D-115` | `quant.rs:BrownianBridge` |

---

## 10. Existing Types / Interfaces to Reuse
- `MarketState` (`v8-core/src/state.rs`): Exogenous price and technical feature provider.
- `MarketRegimeTag`, `BrownianBridge`, `TcaAttribution`, `PortfolioMetrics` (`v8-core/src/quant.rs`): Quantitative formulas.
- `CandidateDraft`, `EpisodeKey`, `SetupAnchor` (`v8-core/src/runloop.rs`): Signal definitions.
- `InterventionManifest` (`v8-core/src/regret.rs`): Causal intervention tags.

---

## 11. Mathematical & Semantic Invariants

```text
I1 (Price Discretization):  P_eff = ⌊P / tickSize⌋ × tickSize
I2 (Lot Discretization):    Q_eff = ⌊Q / stepSize⌋ × stepSize
I3 (Margin Legality):       InitialMargin(Q_eff, P_eff, Leverage) <= AvailableBalance
I4 (Liquidation Formula):   P_liq = (P_entry × Q - Margin + cum_k) / (Q × (1 ± MMR_k))
I5 (Cashflow Conservation): ΔWallet = GrossMarketPnL - Commission ± Funding - Slippage
I6 (Single-Writer Ledger):  Ledger records are strictly append-only and hash-bound.
```

---

## 12. Canonical Failure Semantics
- `InitialMargin > AvailableBalance` $\implies$ `INSUFFICIENT_AVAILABLE_BALANCE`
- `Q_eff × P_entry < 5.0 USDT` $\implies$ `MIN_NOTIONAL_REJECTED`
- `Q_raw < stepSize / 2` $\implies$ `QUANTITY_ROUNDS_TO_ZERO`
- `GrossNotional > TierMaxNotional` $\implies$ `MARGIN_LIMIT_EXCEEDED`
- `RequiredLeverage > PolicyMaxLeverage` $\implies$ `LEVERAGE_CONSTRAINT`
- `PortfolioHeat > MaxHeatLimit` $\implies$ `PORTFOLIO_HEAT_EXCEEDED`
- `ActivePositions >= MaxSlots` $\implies$ `CAPITAL_CONSTRAINT_REJECTION`
- `ContractHashes Diverge` $\implies$ `CAPTURE_RATIO_NOT_IDENTIFIABLE`

---

## 13. Dependency Map
```text
Market Tape Data
      │
      ▼
MarketState(t) ──> Deterministic 28 Experts ──> CandidateDraft
                                                       │
AccountState(t) ───────────────────────────────────────┤
VenueState(t)   ───────────────────────────────────────┤
PortfolioState(t) ─────────────────────────────────────┤
                                                       ▼
                                             RiskBudgetAllocator
                                                       │
                                      ┌────────────────┴────────────────┐
                                      ▼                                 ▼
                              [Legal Order]                    [Typed Rejection]
                                      │                                 │
                                      ▼                                 ▼
                            ExchangeSimulator                  AllocationLedger
                                      │
                                      ▼
                           EconomicCashflow Ledger
                                      │
                                      ▼
                           Next Account/PortfolioState
```

---

## 14. Ambiguity / OPEN_PIN Triggers
- If Binance historical funding timestamps diverge from integer 8-hour intervals, STOP and escalate to GOVERNANCE (`OPEN_PIN`).
- If an order type is encountered that cannot be mapped to Market, Limit, Stop-Market, or Trailing-Stop, STOP rather than inventing execution semantics.
- If margin mode (Cross vs Isolated) rules conflict across active positions, fail closed with `ISOLATED_MARGIN_ONLY`.

---

## 15. Reading List & References
1. **Boyd, S., Busseti, E., et al. (2017)**. *Multi-period trading via convex optimization*. [arXiv:2003.01809](https://arxiv.org/abs/2003.01809).
2. **Almgren, R., & Chriss, N. (2000); Kyle, A. S., & Obizhaeva, A. A. (2016)**. *Market microstructure invariance and optimal execution*.
3. **Alexander, C., et al. (2020); He, S., et al. (2022)**. *Microstructure of cryptocurrency perpetual futures*. [arXiv:2102.04591](https://arxiv.org/abs/2102.04591).
4. **Manski, C. F. (2003)**. *Partial Identification of Probability Distributions*. Springer.
5. **Bailey, D. H., & López de Prado, M. (2014)**. *The Deflated Sharpe Ratio*.
6. **Binance Developer Center**: [Binance USDⓈ-M Futures API & Margin Rules Documentation](https://developers.binance.com/).
7. **V8 Monograph**: [`docs/contracts/VENUE_AND_CAPITAL_SIMULATION_SPEC.md`](file:///c:/Users/dresden/Documents/v8/docs/contracts/VENUE_AND_CAPITAL_SIMULATION_SPEC.md).

---

## 16. V8 Guards
- [x] I will not invent a new canonical error code, ontology, or parallel interface unless an R# requirement explicitly authorizes it.
- [x] No unrelated semantic strategy change is bundled into this implementation issue.
- [x] No frozen OOS is opened unless this issue explicitly carries that authority.
- [x] If the owning contract is ambiguous, I will open/escalate an OPEN_PIN rather than invent an interpretation.
