# V8 Evidence Matrix

| Area | Literature support | Project evidence | V8 disposition |
|---|---|---|---|
| Liquidity, order flow, volatility context | Yes; Source Map S1–S4 | No V8-specific result | Use as hypotheses, not indicators-to-trade |
| Trader cognition | Conditions for expertise and decision theory | No trader study | Grammar is a formal design aid only |
| Candidate lifecycle | Event-sourcing and censoring support auditability | V7 found state-machine/no-trade reporting failures | PROVISIONAL; run lifecycle ablation |
| Point-in-time State | PIT/revision risks documented | V7 causal contracts | LOCKED validity invariant |
| Expert decomposition | No direct trading proof | No relevant comparison | OPEN; paired global-baseline test |
| Router | MoE has starvation/false-negative risks | No router test | Exclude from baseline |
| Scorer | Selective prediction/meta-label analogies | Abstention pitfalls observed | Deferred pending fixed-coverage gain |
| Ranker | Portfolio interaction is real | No capacity-contestion evidence | Deferred |
| Execution simulation | Cost/impact theory and event sequencing | V7 has strong controls but failed authority certification | Level 1 comparator only; no economics claim |
| Inference | Dependence and search bias methods exist | V7 used clustered/scrambled diagnostics | Mandatory protocol, not decorative statistics |
| Portfolio risk caps | 1/N beats estimation-heavy allocation (DeMiguel 2009); vol targeting unproven in crypto perps | No V8 result | Deterministic heat/1R caps are baseline (D-023); learned allocation deferred |
| Regime filtering | Mechanical masks reduce contamination (Du 2025) vs learned regime filters overfit OOS (Novy-Marx 2015) | No V8 result | Split: mechanical mask = data-plane baseline (D-024); learned labels = router-gated (O-015) |
| Active position management | Conflicting: stop overlays help momentum crashes (Han/Zhou/Zhu 2016; Sadaqat 2023) vs cost drag (Kaminski-Lo 2013; López de Prado 2018) | No V8 result | O-013, only under pessimistic intrabar assumption |
| Selection bias | MNAR/OPE: rejected-action counterfactuals are biased without correction (Narita 2022) | Rejected candidates carry NOT_EXECUTED outcomes | Diagnostic only (O-014); correction layer gated |

## Citation verification (2026-08-01)

Two arXiv IDs from an external synthesis were checked against this corpus's
own reading list and corrected:

- `arXiv:2209.05559` is **Deep Reinforcement Learning for Cryptocurrency
  Trading: A Practical Approach to Address Backtest Overfitting** (reading
  list #33), NOT Narita et al.'s off-policy evaluation paper. The OPE framing
  remains methodologically relevant but must be cited from its real source.
- `arXiv:2507.07107` is **Machine Learning Enhanced Multi-Factor Quantitative
  Asset Pricing** (reading list #34); its exact claims were not verified
  against a full-text source in this pass.

Converging literature gaps — two independent searches reached the same four
walls; recorded as OPEN, never filled by analogy:

1. The magnitude of intrabar path-ambiguity bias is unmeasured (only
   practitioner warnings exist).
2. No peer-reviewed evidence on drawdown-conditioned sizing in crypto perps.
3. No study measures the strategy-level effect of a funding-window veto.
4. No financial OPE application exists for capacity/exposure-rejected trades.

Detailed citations are in [SOURCE_MAP.md](SOURCE_MAP.md), and local evidence limits are in [PROJECT_EVIDENCE_AUDIT.md](PROJECT_EVIDENCE_AUDIT.md).
