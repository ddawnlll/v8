# Historical Market Archetype Registry & Multi-Episode Allegorical Audit Suite

**Status:** RATIFIED AUDIT (D-125, ALLEGORY-001)  
**Owning Authority:** `TARGET_ORACLE_SPEC.md` §9, `WORK_ITEM_POLICY.md` v1.2, `v8-core/src/evaluation/allegory.rs`  
**Academic References:** arXiv:2607.19497 (Trend-Following Skew & Multi-Horizon Persistence), arXiv:2106.08420 (Dynamic Momentum Turning Points), arXiv:2102.02865 (Crypto Bear/Bull Asymmetry), arXiv:2608.03616 (Liquidation Cascades & OI Clearing), arXiv:0902.4159 (Order-Book Liquidity & Impact), arXiv:2602.00776 (Flash Crash Microstructure), arXiv:2208.01445 (Cross-Asset Correlation Dynamics), arXiv:2506.08573 (Perpetual Funding Mechanics), arXiv:2504.15790 (Pump & Dump Accumulation Separation), arXiv:2308.07041 (Stablecoin Collateral Death Spirals).

---

## 1. Executive Summary & Epistemic Framework

Single-date retrospective benchmarking (e.g. "05 February 2026 BTC Breakout") is vulnerable to narrative cherry-picking and hindsight overfitting. **ALLEGORY-001** expands V8's evaluation engine into a systematic, multi-episode registry of **12 Canonical Market Archetypes (A01–A12)** across **4 Super-Classes**.

### Core Invariants
1. **Zero-Hindsight Leakage:** No archetype defines an "expected action" or hardcoded outcome. Each episode measures ex-ante candidate admissions against the ex-post unconstrained / capital-constrained opportunity frontier.
2. **Mandatory Anti-Allegory (Negative Control) Calibration:** Every directional or forced-flow archetype is paired with a strictly matched negative control to prevent asymmetric overfitting (e.g., *Compression $\to$ False Breakout*, *Capitulation $\to$ Cascade Continuation*).
3. **Constitution Rule 12 (`NO_ECONOMIC_CLAIM`):** All scorecards and evaluations are classified `MODEL_DERIVED_AUDIT` with `NO_ECONOMIC_CLAIM`.

---

## 2. The 12 Canonical Archetypes & Super-Classes

### I. Directional Opportunity
* **A01: Compression $\to$ Expansion (🚀):**
  * *Audit Question:* Did the engine detect pre-expansion volatility compression and participate with bounded slippage?
  * *Negative Control:* Compression $\to$ Dead Range / False Expansion.
* **A02: Slow Grind Trend (🐢):**
  * *Audit Question:* Did the engine maintain trend persistence without premature overbought exit?
  * *Key Metrics:* `trend_start`, `first_useful_signal`, `first_accepted_campaign`, `total_trend_mfe`, `realized_capture`, `premature_exits`, `re_entry_count`.
  * *Negative Control:* Slow Grind $\to$ Abrupt Mean Reversion Breakdown.
* **A03: Failed Breakout / Trap (🪤):**
  * *Audit Question:* Did the engine distinguish failed breakouts from structural acceptance?
  * *Key Metrics:* `close_acceptance`, `volume_participation`, `derivatives_confirmation`, `retest_survival`, `structural_invalidation`.
  * *Negative Control:* True Breakout $\to$ Structural Acceptance.
* **A04: Capitulation $\to$ V-Reversal (🔄):**
  * *Audit Question:* Did the engine exit short exposure at climax and recognize reversal latency?
  * *Key Metrics:* `short_capture`, `short_exit_latency`, `opposite_campaign_recognition_latency`.
  * *Negative Control:* Capitulation $\to$ Cascade Continuation.
* **A05: Blow-Off / Exhaustion (🎈):**
  * *Audit Question:* Did the engine identify parabolic exhaustion without early profit-taking haircut?
  * *Negative Control:* Momentum Acceleration $\to$ Extended Continuation.

### II. Forced-Flow Stress
* **A06: Short/Long Squeeze vs Organic (🧨):**
  * *Audit Question:* Did the engine differentiate forced open-interest clearing from organic spot expansion?
  * *Negative Control:* Organic Spot Expansion $\to$ Sustained OI Growth.
* **A07: Liquidation Cascade / Flash Crash (☢️):**
  * *Audit Question:* Did execution risk, limit fills, and mark prices survive cascade orderbook depletion?
  * *Key Metrics:* `warning_lead_time`, `crash_capture`, `max_heat`, `liquidation_proximity`, `slippage_regret`, `reversal_latency`.
  * *Negative Control:* Standard Volatility Intrabar Wick.

### III. Low-Opportunity / Adversarial
* **A08: Chop / Whipsaw Hell (🪚):**
  * *Audit Question:* Did the engine preserve capital by respecting NO_TRADE superiority in non-directional noise?
  * *Key Metrics:* `no_trade_superiority`, `whipsaw_avoidance_rate`, `fee_drag_preservation`.
  * *Negative Control:* Micro-Range Clean Expansion.
* **A09: Mean-Reversion Range (🧲):**
  * *Audit Question:* Did the engine exploit range boundaries without misclassifying mean reversion as trend inception?
  * *Negative Control:* Range Boundary True Structural Breakout.
* **A12: Manipulation / Structural Breakdown (🎭):**
  * *Audit Question:* Did integrity filters detect anomalous non-organic volume or collateral death spirals?
  * *Negative Control:* Organic High-Volume Price Discovery.

### IV. Portfolio / Derivatives
* **A10: Cross-Asset Rotation / Contagion (🌐):**
  * *Audit Question:* Did portfolio allocation prevent triple-counting systemic beta risk across correlated assets?
  * *Negative Control:* Independent Idiosyncratic Asset Moves.
* **A11: Funding / Basis Dislocation (⚖️):**
  * *Audit Question:* Did the engine detect derivatives crowding stress prior to spot price realization?
  * *Negative Control:* High Funding Sustained Price Trend.

---

## 3. Scorecard & Evaluation Engine Contract

The engine executes via `v8-core allegory-audit` and outputs a cryptographic, Canon-hashed receipt:

```bash
cargo run --manifest-path v8-core/Cargo.toml --bin v8-core -- allegory-audit \
  --tape research/tape/btcusdt-1h-12m/tape.jsonl \
  --out .audit/rust_audit_current/allegory_scorecard.json
```
