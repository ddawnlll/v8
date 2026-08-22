# V8.3 $1,000 Anatomy Target Prediction Audit & Baseline Reconciliation

## 1. P0 Matched Baseline Audit & Scope
- **Tape Analyzed:** `research/tape/btcusdt-1h-12m/tape.jsonl` (1 Symbol BTCUSDT, 12 Months, 8,760 hours).
- **Explanation of Baseline Differences:**
  - **1-Symbol BTCUSDT 12M Tape (Single-Asset Control):**
    - V8.2 Baseline: 226 Trades, -$59.62 fee drag, -$57.20 Net PnL, 12.59% Max DD.
    - V8.3 Phase I: 38 Campaigns, -$7.20 fee drag, +$34.60 Net PnL, 2.14% Max DD.
  - **4-Symbol Multi-Tape (`multi-1h-dev`):**
    - V8.2 Multi Baseline: 958 Trades, -$111.58 fee drag, -$11.27% Return.
- **Audited Diagnosis:** The single-asset BTCUSDT 12M tape exhibits exact consistency between V8.2 and V8.3 test benches. The uplift is genuine, but insufficient in magnitude (+3.46% vs expected +8–17.5%).

---

## 2. Prediction vs Realized Matrix

| Dimension | Predicted Range | Realized V8.3 Phase I | Verdict |
| :--- | :--- | :--- | :--- |
| **Trade / Campaign Count** | 260–320 | **38** | Severe Under-Instantiation (Coverage Starvation) |
| **Total Fee & Slippage Drag** | ~$135 | **-$7.20** | Substantial Outperformance |
| **Gross Alpha** | +$215–$310 | **+$41.80** | **FAIL (Missed Target)** |
| **Terminal Equity ($1,000 base)** | $1,080–$1,175 | **$1,034.60** | **FAIL** |
| **Net Return** | +8.0%–17.5% | **+3.46%** | **FAIL (Target Miss)** |
| **Max Drawdown (DD)** | < 12.5% | **2.14%** | **PASS (Exceptional Risk Discipline)** |
| **Sub-Friction Trade Ratio** | Sharp Reduction | **0.0%** | **PASS (100% Elimination)** |

---

## 3. The Five Funnel Drop Hypotheses (Root Cause Diagnosis)

1. **H1 — Opportunity Coverage Starvation (Grammar Recall):**
   - The initial `OpportunityGrammar` baseline required $\ge 1.8\sigma$ Bollinger/Z-score breakouts. This only instantiated 38 episodes across 8,760 hours, missing multi-bar structural momentum, consolidation breaks, and volatility cycles.
2. **H2 — Witness Abstention Starvation (Witness Recall):**
   - Legacy experts migrated into witnesses are conservative in declaring `InHabitat`, leading to excessive `ABSTAIN` / `OutOfHabitat` stances.
3. **H3 — Utility Hurdle False Rejections (Hurdle Calibration):**
   - The friction hurdle correctly rejects sub-friction setups, but an over-conservative uncertainty penalty ($5\text{bps} \times (1 + \text{entropy})$) may be rejecting viable positive-expectation setups.
4. **H4 — Reconciliation Loss:**
   - Independent witnesses in separate groups may create mild contradiction entropy, damping actionable support into `Inconclusive`.
5. **H5 — Raw Alpha Deficiency:**
   - The 28 legacy experts may have inherently low standalone predictive edge on 1-hour crypto bars.

---

## 4. Formal Action Plan: V8.3 Phase II — Opportunity Expansion Offensive

Do NOT loosen thresholds arbitrarily or curve-fit.
Instead:
1. Implement the **Opportunity Capture Funnel** measurement engine in Rust (`v8-core/src/opportunity/funnel.rs`).
2. Measure exact drop counts and lost oracle utility across the 7 funnel stages.
3. Systematically expand OpportunityGrammar archetypes (MeanReversion, Multi-Timeframe Trend, Liquidity Compression) to capture valid structural opportunities while maintaining strict 2.14% drawdown containment.
