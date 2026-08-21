# Canonical Cancer Taxonomy & Extreme-Move Campaign Audit

**Status:** RATIFIED AUDIT (D-123)  
**Owning Authority:** `docs/contracts/VENUE_AND_CAPITAL_SIMULATION_SPEC.md`, `TARGET_ORACLE_SPEC.md` §12, `docs/audits/CANONICAL_CANCERS_AND_MEGA_MOVE_AUDIT.accp.yaml`  
**Academic References:** arXiv:1603.06183 (Risk-Constrained Kelly), arXiv:2602.11708 (AdaptiveTrend), arXiv:2402.05272 (Jump Models), arXiv:1904.04912 (Deep Momentum Networks).

---

## 1. Executive Diagnosis

This audit ratifies the **6 Canonical Root Cancers** of the V8 quantitative research platform and establishes the **05–06 February 2026 BTC Mega Attack (Bars 5250–5310)** as the official empirical Ground Truth benchmark.

### The 6 Canonical Cancers
1. **KANSER-01 — Capital & Lot Quantization Paralysis:** Fixed 0.5% risk on drawndown capital drops below legal venue lot steps (0.001 BTC), causing 32,428 silent rejections (`QUANTITY_ROUNDS_TO_ZERO`).
2. **KANSER-02 — Tail Clipping Exit Geometry:** Fixed 1R/2R take-profit cuts off the fat right tail; 79% of target exits continued past +2R with post-exit MFE averaging +4.5R.
3. **KANSER-03 — Expert Funnel Collapse & Contention:** 42,647 triggers produce 14,766 dedup suppressions and only 2 admitted trades; 28 sensors act as competing traders rather than cooperative evidence detectors.
4. **KANSER-04 — Portfolio Context & Regime Blindness:** Absence of soft Bayesian risk multipliers; hard routers induce latency and truncate the first 30–50% of major trend breakouts.
5. **KANSER-05 — Alpha / Mechanical Floor Deficiency:** Unhedged raw signals indistinguishable from zero-skill random nulls; large-move detection recall must be measured before complex routing.
6. **KANSER-06 — Data & Sponsorship Blindness:** 1h OHLCV + funding tape lacks open interest, liquidation clusters, and order flow sponsorship.

---

## 2. Ground Truth Benchmark: 05–06 February 2026 Episode

- **Crash Phase (Bars 5255 $\to$ 5279):** $73,137.40 \to 62,868.10 \text{ \$}$ (-14.04% in 24 hours).
- **V-Dip Rebound (Bars 5279 $\to$ 5303):** $62,868.10 \to 70,544.50 \text{ \$}$ (+12.21% in 24 hours).
- **Observed Behavior:** 191 candidate signals generated $\to$ **0 trades executed** due to lot discretization lockout.
- **Remediation Target:** Capture $\ge 65\%$ of both moves via Quantization-Aware Sizing, Campaign Aggregation, and Chandelier Trailing Exit.

---

## 3. Mathematical Specifications

### A. Boyd Dynamic Liquidity Floor
$$CashFloor_t = \max\left(VenueFloor_t, \; MarginStress_t, \; NextTradeFloor_t, \; FeeFundingBuffer_t\right)$$
$$DeployableEquity_t = Equity_t - CashFloor_t$$

### B. Quantization-Aware Risk Budgeting
$$MinimumExecutableRisk_{USDT} = StepSize \times |Entry - StructuralStop| + Fees + Slippage$$
$$\text{Gate: } MinimumExecutableRisk \le AllowedCampaignRisk \implies \text{Admit 1 Lot}$$

### C. Tail Capture Efficiency (TCE)
$$TCE = \frac{\sum \text{Realized Favorable Move}}{\sum \text{Maximum Available Favorable Move (MFE)}}$$
