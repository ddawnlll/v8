# V8 Reading List — ordered by research purpose

This is a compact working bibliography for converting the provisional brief into a falsifiable monograph. Read the primary items before design synthesis; the final two items are implementation guidance and should not be used as economic evidence.

## 1. Market mechanisms and state variables

1. **Brandt, M. & Kavajecz, K. (2003), “Price Discovery in the U.S. Treasury Market: The Impact of Orderflow and Liquidity on the Yield Curve.”** [NBER working paper PDF](https://www.nber.org/system/files/working_papers/w9529/w9529.pdf)  
   Relevance: anchor for the distinction between information/order flow, liquidity, and price discovery. Use when defining what `flow` and `liquidity` mean, and when rejecting indicator-only explanations.

2. **Vayanos, D. & Wang, J. (2012), “Market Liquidity — Theory and Empirical Evidence.”** [MIT-hosted working paper PDF](https://web.mit.edu/wangj/www/pap/VayanosWang12Empirical.pdf)  
   Relevance: theory/empirics of liquidity supply, demand, and price effects. Use for cost, capacity, dealer/inventory, and state-variable rationale.

3. **Andersen, T., Bollerslev, T., Christoffersen, P. & Diebold, F. (2005), “Volatility Forecasting.”** [NBER WP 11188 PDF](https://www.nber.org/system/files/working_papers/w11188/w11188.pdf)  
   Relevance: supports persistent conditional volatility and activity. Use to motivate volatility context, not a particular threshold taxonomy.

4. **Khandani, A. & Lo, A. (2008), “What Happened to the Quants in August 2007?”** [MIT PDF](https://web.mit.edu/Alo/www/Papers/august07b_2.pdf)  
   Relevance: evidence consistent with forced deleveraging and temporary dislocation. Use as a cautionary mechanism source for “dislocation,” not as evidence that a liquidation detector will be profitable.

5. **Auer, R., Tercero-Lucas, D. & Tolle, M. (2025 revision), “Crypto carry.”** [BIS working paper page](https://www.bis.org/publ/work1087.htm)  
   Relevance: native crypto evidence on spot/derivative basis and institutional constraints. Use when considering funding/basis fields; validate current version/date when citing.

6. **Moskowitz, T., Ooi, Y. & Pedersen, L. (2012), “Time Series Momentum.”** [DOI record](https://doi.org/10.1016/j.jfineco.2011.11.003)  
   Relevance: broad empirical motivation for testing continuation effects. Scope is diversified futures, so V8 must not extrapolate it to a specific crypto timeframe without its own OOS evidence.

## 2. Candidate quality, abstention, and probability claims

7. **Geifman, Y. & El-Yaniv, R. (2017), “Selective Classification for Deep Neural Networks.”** [arXiv record](https://arxiv.org/abs/1705.08500)  
   Relevance: formal language for accepting/rejecting predictions and evaluating the coverage–risk trade-off. Translate carefully: V8 must measure economic utility as well as predictive risk.

8. **scikit-learn, “Probability calibration.”** [maintained documentation](https://scikit-learn.org/stable/modules/calibration.html)  
   Relevance: practical requirements for calibrated probabilities, reliability curves, and cross-validated calibration. Use for claims such as `p_trigger` or `P(net R > 0)`.

9. **López de Prado, M. (2018), *Advances in Financial Machine Learning*.** [SSRN record](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3104847)  
   Relevance: source of the meta-labeling pattern behind a secondary quality model. Treat as a proposed method to test, not a proof that meta-labeling creates alpha.

## 3. Execution, validation, and anti-overfitting controls

10. **Almgren, R. & Chriss, N. (2000), “Optimal Execution of Portfolio Transactions.”** [paper PDF](https://quantitativebrokers.com/s/Optimal-Execution-of-Portfolio-Transaction-_-AlmgrenChriss-1999.pdf)  
    Relevance: formal expected-cost/risk trade-off. Use to justify modeling execution costs and keeping an execution policy explicit/versioned during alpha experiments.

11. **U.S. Securities and Exchange Commission, “Disclosure of Order Execution Information” (proposal).** [SEC PDF](https://www.sec.gov/files/rules/proposed/2022/34-96493.pdf)  
    Relevance: a primary regulatory discussion of why execution-quality measurement is non-trivial. Equity-market scope; use only as a measurement principle, not crypto-market evidence.

12. **Novy-Marx, R. (2015), “Backtesting Strategies Based on Multiple Signals.”** [NBER page](https://www.nber.org/papers/w21329)  
    Relevance: direct warning that combining/signed/tuned signals can produce striking but spurious in-sample results. Required reading before calling parameter variants separate experts.

13. **Bailey, D. et al. (2015), “The Probability of Backtest Overfitting.”** [SSRN record](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253)  
    Relevance: finance-specific framework for assessing selection-induced overfitting. Pair with walk-forward and a locked final holdout; PBO is a diagnostic, not a guarantee.

14. **Simonian, J. (2024), *Investment Model Validation*.** [CFA Institute PDF](https://rpc.cfainstitute.org/sites/default/files/-/media/documents/article/rf-brief/investment-model-validation.pdf)  
    Relevance: implementation-minded validation governance, data lineage, stress and deployment concerns. Secondary/practitioner source—do not use as proof of market mechanisms.

## 4. Cognition: terminology only, not profitability evidence

15. **Kochenderfer, M. (2015), *Decision Making Under Uncertainty: Theory and Application*.** [Stanford-hosted PDF](https://web.stanford.edu/group/sisl/public/dmu.pdf)  
    Relevance: formal vocabulary for state, uncertainty, action, and outcome. It can help constrain a “trader decision grammar,” but it does not validate discretionary trader narratives or V8 behavior families.

## Reading sequence for the next research phase

Read 1–5 to write the economic-mechanism ontology; 7–9 before specifying the scorer’s labels and metrics; 10–14 before finalizing simulation and promotion gates; 15 only when translating human workflow into auditable objects.  Every proposed expert should cite one mechanism source from section 1, then carry its own formalization and OOS experiment rather than inheriting a citation as proof.
