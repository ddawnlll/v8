# V8 Kaizen Experimentation, Beliefs & Sandboxing Protocol (v8.kaizen.sandbox.v1)

**Status:** ACTIVE_POLICY & NORMATIVE_GOVERNANCE  
**Scope:** Defines the core epistemic beliefs, isolated sandboxing environments, architectural experimentation workflows, and promotion gates for autonomous Kaizen agents and human quantitative researchers.

---

## 1. Core Epistemic Beliefs & Axioms (The Kaizen Creed)

1. **Axiom 1 — Zero Unearned Alpha (Anti-Hallucination & Anti-Overfitting):**
   * High backtest Sharpe without an identified structural market mechanism (liquidity asymmetry, inventory imbalance, forced liquidation, regime transition) is classified as statistical noise.
   * Hardcoding metrics or tuning parameters directly on holdout data is strictly forbidden (`V8_CONSTITUTION` Rule 12).

2. **Axiom 2 — One-Variable-at-a-Time (OVAT) & Factorial Isolation:**
   * An architectural or strategy change must isolate its moving parts. When testing an exit policy, geometry parameters, or regime filter, all other components must remain locked to their baseline state.

3. **Axiom 3 — Strict Sandbox Isolation (Zero Mutation of Active Runtime):**
   * Outcome data or experimental challenger code NEVER mutates an active production runtime (`LEARNING_PROTOCOL` §1).
   * All experimental mutations must occur in isolated sandboxes (`.audit/sandbox/<experiment_id>/` or isolated git worktrees).

4. **Axiom 4 — Comparative Falsification Gate (The Kaizen Differential):**
   * No architectural proposal is accepted without an automated comparative audit (`tools/compare_audits.py`) proving statistically significant progression over the baseline across:
     $$\Delta \text{Net PnL} > 0, \quad \Delta \text{Profit Factor} > 0, \quad \Delta \text{Max Drawdown} \le 0, \quad \text{Regressed Experts} == 0$$

5. **Axiom 5 — Attribution Validity & Fee Conservation:**
   * A strategy is only viable if its gross alpha survives real-world exchange frictions (Binance VIP0 taker fees, lot step rounding, margin locks, funding rates). Dimensionless $R$-space gains that evaporate in $\text{USDT}$-space are rejected.

---

## 2. Sandboxing Architecture & Environments

When a Kaizen Agent initiates an experiment, it operates within an isolated sandbox environment:

```
                                 PRODUCTION PLANE (Locked / Frozen)
                                 ├── v8-core/ (Authoritative Rust Engine)
                                 └── .audit/rust_audit_current/ (Current Baseline)
                                                 │
                                                 │ 1. Fork Sandbox
                                                 ▼
                             KAIZEN SANDBOX ENVIRONMENT (Isolated)
                             ├── Path: .audit/sandbox/<experiment_id>/
                             │   ├── hypothesis.json (Preregistered Belief & Plan)
                             │   ├── diff/ (Isolated source patches / parameters)
                             │   ├── run_out/ (Isolated execution ledgers)
                             │   └── candidate_receipt.json
                             │
                             │ 2. Execute & Audit
                             ▼
                             tools/compare_audits.py --base <baseline> --target <sandbox>
                             │
                             │ 3. Automated Kaizen Decision
                             ▼
              ┌─────────────────────────────────────────────────────────────┐
              │                     PROMOTION GATES                         │
              ├─────────────────────────────────────────────────────────────┤
              │ [REJECT]     : Net PnL drops or Regressed Experts > 0       │
              │ [QUARANTINE] : High Sharpe but sample size N < 30           │
              │ [SHADOW]     : Outperforms in HighVol but untested in Chop  │
              │ [PROMOTE]    : Pareto dominant + passes White's Reality Ck  │
              └─────────────────────────────────────────────────────────────┘
```

---

## 3. Structured Hypothesis Proposal Schema (`hypothesis.json`)

Every experiment must begin with a preregistered hypothesis file:

```json
{
  "$schema": "https://v8.project/schemas/kaizen_hypothesis_v1.json",
  "experiment_id": "exp_20260819_m8_trailing_stop",
  "author": "agent:kaizen_scout_1",
  "belief_statement": "Replacing static 1:1 TP/SL with ATR-based trailing stop (M8) allows trend continuation trades to capture >3R moves during HighVol regimes without increasing Chop loss.",
  "target_experts": ["bollinger_breakout", "fib_retracement_continuation"],
  "independent_variable": "exit_policy = M8_DYNAMIC_ASYMMETRIC",
  "control_variables": {
    "entry_rules": "UNMODIFIED",
    "fee_tier": "VIP0",
    "risk_fraction": 0.02
  },
  "falsification_criteria": {
    "min_net_pnl_lift_usdt": 50.0,
    "max_acceptable_drawdown_pct": 20.0,
    "max_regressed_expert_count": 0
  }
}
```

---

## 4. Promotion Lifecycle & Automated Governance

| Promotion Stage | Automated Criteria | Action |
| :--- | :--- | :--- |
| **`REJECT`** | $\Delta \text{Net PnL} < 0$ or Reality Check $p > 0.05$ | Sandbox is purged. Failure logged to `benchmark_ledger.jsonl`. |
| **`QUARANTINE`** | $\Delta \text{Net PnL} > 0$ but $N < 30$ trades | Marked experimental; excluded from production allocator. |
| **`SHADOW`** | Profitable in HighVol, marginal in Chop | Admitted only with active `MarketRegimeGate` coupling. |
| **`PROMOTE`** | Pareto dominant across all metrics + Bit-exact check | Merged into `v8-core/src/`, snapshot committed to `.audit/history/`. |

---

## 5. Kaizen Agent Execution Flow

1. **Step 1 — Hypothesize:** Formulate `hypothesis.json` with clear falsification boundaries.
2. **Step 2 — Sandbox Run:** Execute in `.audit/sandbox/<experiment_id>/` without touching production files.
3. **Step 3 — Compare:** Run `python tools/compare_audits.py --base baseline --target sandbox --json`.
4. **Step 4 — Decide:** Emit `KaizenDecision` (REJECT / PROMOTE). If PROMOTE, run full CI test battery (`cargo test`, `reproduce_rust_audit.py`) and snapshot to `.audit/history/`.
