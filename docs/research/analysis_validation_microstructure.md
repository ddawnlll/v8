# V8 Research Synthesis: Validation, Microstructure, Simulation, Execution, and Portfolio Selection

## Scope, source hygiene, and evidence boundary

This chapter reviews reading-list items **30–60**. The list has 31 numbered entries but only **28 unique works**: items 40/41 are versions of the same PBO paper, item 59 repeats item 33, and item 60 repeats item 34. All 28 unique full texts were obtained and read. “Accessible” therefore means that a primary full-text PDF was available locally; it does **not** mean that every paper is peer reviewed, that every dataset is public, or that every empirical result is independently reproducible.

Three bibliographic corrections matter:

1. Items **34 and 60** link to arXiv:2507.07107, whose actual title is *Machine Learning Enhanced Multi-Factor Quantitative Trading: A Cross-Sectional Portfolio Optimization Approach with Bias Correction*—not “Quantitative Asset Pricing.”
2. Item **37** is arXiv:2512.12924, *Interpretable Hypothesis-Driven Trading: A Rigorous Walk-Forward Validation Framework*. It is a different work from item 34 despite the supplied text reusing `2512.12924` beside item 34.
3. Item **44** is actually *PredictionMarketBench*, not a general-purpose benchmark for all trading strategies. Its domain is binary prediction-market contracts.

Evidence labels used below:

- **Mechanism evidence** means a paper supplies a defensible causal or structural account.
- **Measurement evidence** means it validates an observable or diagnostic under a stated dataset and clock.
- **Protocol evidence** means it supports a research control, not a trading edge.
- **Illustrative evidence** means a small, synthetic, proprietary, or weakly identified experiment that motivates a test but cannot settle it.

### Evidence-depth audit

| List items | Full-text access | Review depth | Qualification |
|---|---|---|---|
| 30–39 | Primary PDF, 10/10 | Abstract, method, empirical design/results, conclusion/limitations | Several are recent preprints; 34 uses proprietary real data; 38 is a conceptual essay. |
| 40–41 | Primary author PDF plus SSRN record | Full paper including CSCV design, examples, and author-stated misuse/limitations | One unique paper represented twice. |
| 42 | Primary author PDF plus SSRN/DOI records | Full paper including DSR construction, trial-dependence discussion, and conclusion | Published article; still diagnostic rather than a leakage/execution repair. |
| 43–44 | Primary PDF, 2/2 | Abstract, method/data, empirical results, conclusion/limitations | 44 has only four benchmark episodes. |
| 45–58 | Primary PDF, 14/14 | Abstract, data/conditioning variable, main empirical/theoretical result, conclusion/limitations | 50 and 51 are dissertations; 58 is a review; observational impact is not automatically causal. |
| 59–60 | Same primary PDFs as 33 and 34 | Cross-bucket implications reviewed | Duplicate entries, not independent confirmations. |

Thus no assigned work is “abstract-only” in this synthesis. Evidence strength nevertheless varies with design, data access, review status, and identification; full-text access is not a quality grade.

No result in this chapter establishes that V8 is profitable or deployable. A return forecast, a contemporaneous explanatory relationship, a simulator benchmark result, and a realizable net portfolio effect are different objects. V8 must keep them separate.

## What the literature changes in V8

The strongest conclusions are architectural and epistemic:

1. **The research search itself is part of the model.** Trial count, family membership, dependence among variants, parameter changes, and discarded candidates must be append-only research artifacts. PBO and DSR become meaningless when the file drawer is incomplete.
2. **A frozen holdout is necessary but not sufficient.** Repeatedly consulting or reusing it turns it into training data. PBO/DSR diagnose selection; neither repairs leakage, bad fills, missing costs, regime breaks, or a non-causal feature.
3. **Simulation fidelity is claim-relative.** Bar replay can falsify slow, aggressive-order hypotheses but cannot support queue, maker-fill, or sub-second OFI claims. Order-flow papers are chiefly an argument for strict fidelity boundaries, not an entitlement to Level-3 simulation.
4. **Order flow is persistent but impact is state dependent.** Long memory, depth, spread, tick size, news, time of day, the price-changing status of an event, and other assets' flow all matter. A static global OFI coefficient is not an acceptable execution model.
5. **Contemporaneous fit is not forecastability.** Very high OFI-to-price-change \(R^2\) can describe a price-formation identity at the same clock. It does not prove that the value was available early enough to trade.
6. **Impact is not one universal scalar function.** Linear short-horizon OFI laws, transient/history-dependent propagators, sigmoidal aggregate impact, square-root metaorder impact, and cross-impact can all be true under different conditioning variables and aggregation scales.
7. **Execution and alpha are operationally separable, not statistically independent.** Tradability masks, cost/slippage stress, depth and impact conditioning can change both the feature distribution and candidate ranking.
8. **Ranking is mandate- and contention-dependent.** It is justified only when multiple acceptable candidates compete for a real capital/risk/liquidity budget. Small Sharpe differences without paired uncertainty or cost stress are not a ranking foundation.

---

## I. Backtest overfitting, multiple testing, and validation protocols

### 30. Covariance penalties for backtest selection

Koshiyama and Firoozye derive degrees-of-freedom corrections for in-sample correlation/Sharpe estimates and compare naive lag selection, AIC, an implied-Sharpe correction, and an adjusted \(R^2\) criterion across 1,361 equities, currencies, and fixed-income series. The experiment uses expanding in-sample estimation, 21-day OOS batches, an initial 1,008-day window, 18 candidate lag lengths, and both OLS and total least squares. Proposed covariance penalties improve realized OOS Sharpe and alignment between expected and realized Sharpe relative to naive selection; TLS generally penalizes toward smaller lag spaces and outperforms OLS in this design ([arXiv:1905.05023](https://arxiv.org/abs/1905.05023)).

**What is supported.** Complexity-aware objectives can reduce optimism when selecting a linear lag model, and performance estimation should reflect effective degrees of freedom rather than only the winning in-sample statistic.

**Limits.** The method assumes a tractable joint behavior for signal and return and is tested on one linear autoregressive strategy family. The paper uses overlapping expanding evaluations and reports cross-asset paired tests; asset and time dependence make naive precision optimistic. A higher OOS Sharpe within this family is not evidence of an exploitable V8 Expert. The correction does not account for an undisclosed search outside the lag grid, causal-data faults, or execution error.

**V8 implication.** Store both nominal and effective complexity for every Expert/scorer/ranker variant. Use a covariance penalty only as an internal comparator against simpler fixed baselines. It cannot replace chronological frozen OOS, family-wise trial accounting, or simulation certification.

### 31. GAN-generated paths as an anti-overfitting filter

Sun and Lyuu train recurrent GANs on paths generated by geometric Brownian motion and AR(2), then ask whether backtests on generated paths classify buy-and-hold and moving-average strategies similarly to Monte Carlo truth. The GAN reproduces some marginal path properties; confusion matrices show that synthetic-path evaluation can distinguish deliberately positive from null combinations in the controlled toy models ([arXiv:2209.04895](https://arxiv.org/abs/2209.04895)).

**What is supported.** A generative model can be evaluated task-conditionally—by whether strategy rankings or rejection decisions transfer—not merely by adversarial loss or visual similarity.

**Limits.** The paper explicitly notes that an English translation contains outdated claims. The data-generating laws are known, low-dimensional, and stationary; the sample-size finding may itself reflect GAN memorization. GBM/AR(2) omit volatility clustering, jumps, impact, strategic response, cross-asset dependence, queueing, and regime change. Training a generator on one historical realization cannot create independent information about unseen regimes. A synthetic backtest can faithfully reproduce the biases of the source simulator.

**V8 implication.** Synthetic paths are stress tools, never evidence of market edge. Any V8 generator must face task-based posterior predictive checks: tail/dependence statistics, candidate frequency, state occupancy, cost/impact response, and rank preservation on held-out real blocks. Failure of a generator blocks its use; success permits stress testing only.

### 32. Discounting a backtest PnL

Rej, Seager, and Bouchaud model a researcher who modifies an initially valid strategy until it clears a required Sharpe threshold. “Tweaks” flip exposure in selected PnL segments and, by assumption, lower true OOS performance. They derive an overfitting factor—the expected selected in-sample Sharpe divided by expected OOS Sharpe—as a function of true Sharpe, threshold, backtest length, and researcher freedom. Under CTA-like illustrative settings (true Sharpe 0.3–0.5, threshold about 0.7, tweak fraction about 0.05), the factor is around two ([arXiv:1902.01802](https://arxiv.org/abs/1902.01802)).

**What is supported.** Researcher behavior and acceptance thresholds create selection pressure even when each modification has a plausible narrative; low-Sharpe effects are especially vulnerable.

**Limits.** The sign-flip model, Gaussian segment Sharpe approximation, fixed tweak fraction, and assumption that every modification degrades truth are stylized. “Divide backtest PnL by two” is not a universal estimator. Longer history helps only under behavioral and stationarity assumptions.

**V8 implication.** Record mutation lineage and the reason each Expert revision was made. Treat each rescue modification after a failed gate as a new family member and reset the final untouched evaluation. Use the paper as a qualitative prior for skepticism, not a numeric haircut.

### 33. DRL cryptocurrency trading and CSCV/PBO

The FinRL study embeds combinatorially symmetric cross-validation into hyperparameter selection for PPO, TD3, and SAC on five-minute cryptocurrency data. It tries 50 hyperparameter sets drawn from a 2,700-combination space, labels models using PBO with a 10% threshold, and evaluates one short test period during the 2022 crypto drawdown. Reported PBO is 8.0% for PPO, 9.6% for TD3, and 21.3% for SAC; all portfolio returns are negative, with the selected PPO losing less than comparators ([arXiv:2209.05559](https://arxiv.org/abs/2209.05559)).

**What is supported.** DRL outcomes are highly sensitive to hyperparameters; an explicit search-family diagnostic can reject an apparently strong agent. The fact that “least overfit” still lost money is an important distinction between selection stability and economic value.

**Limits.** The test spans only 58 days, the threshold is not a conventional Neyman–Pearson test despite that framing, the CVIX liquidation rule is another design degree of freedom, and execution is not sufficiently specified for maker/queue claims. The authors acknowledge that limit orders, trade closure, a wider universe, and richer features remain future work.

**V8 implication.** This supports V8's decision to exclude learned execution/RL from the initial architecture. If revisited, compare policies across seeds and fixed search budgets, use PBO as a diagnostic, evaluate a deterministic risk policy at matched information/action constraints, and require a certified event ledger.

### 34. Mask-first cross-sectional trading and portfolio optimization

The supplied title is wrong. Du's paper studies a 213-factor, long-only Chinese A-share pipeline with a point-in-time tradability mask, asymmetric MSE, GBM block-bootstrap augmentation, and Ledoit–Wolf/Markowitz allocation. Its key engineering claim is “upstream contamination”: post-hoc removal of price-limit observations fails because rolling operators have already ingested non-executable closes. On the reported real panel, removing the full mask raises apparent IC but lowers realizable IC and Sharpe; the paper uses 5–8 bps linear turnover costs and a 3% weight cap ([arXiv:2507.07107](https://arxiv.org/abs/2507.07107)).

**What is supported.** Tradability is a first-class, monotone data contract that must propagate through feature computation, training labels, portfolio construction, and simulation—not a final row filter. Apparent predictive fit can rise as economic validity falls.

**Limits.** The real dataset is proprietary, its final OOS window is only 2022–2024, the reported development search uses roughly 50 effective configurations, and the cost model is linear and optimistic for size. GBM augmentation understates tails; no live or queue-level evidence exists. Reported DSR cannot correct a bias shared by every configuration.

**V8 implication.** Add `tradable_for_feature`, `tradable_for_decision`, and `tradable_for_execution` fields with reason codes and monotone masks. Ranker inputs and counterfactual labels must exclude unreachable prices. Run a “mask ablation” as a validity test: if removing the mask improves apparent metrics, the pipeline should flag an executable-information contradiction rather than celebrate it.

### 35. GT-Score

GT-Score combines mean return, a z-like benchmark gate, \(R^2\)-style consistency, and downside deviation. It is tested on RSI, MACD, and Bollinger strategies across 50 U.S. large-cap equities, 15 random seeds, 9,000 Monte Carlo optimization trials, and 5,340 walk-forward trials. It retains more of training performance than Sharpe/Sortino/simple-profit objectives, but its raw test return is slightly lower and paired effect sizes are very small. The paper openly reports that walk-forward advantages reverse or disappear in several periods and that the main tables omit transaction costs ([arXiv:2602.00080](https://arxiv.org/abs/2602.00080)).

**What is supported.** An optimization objective can explicitly trade peak return for stability, and period-by-period evidence is more informative than one pooled ratio.

**Limits.** The “98% reduction in overfitting” is a relative increase in the chosen train-to-validation generalization ratio, not a measured 98% reduction in false discoveries. The z gate treats trade returns as approximately IID/Gaussian, there is no embedded multiple-testing correction, daily bars cannot validate execution, and 0–10 bps sensitivity omits spread/impact/liquidity.

**V8 implication.** Do not adopt GT-Score as V8's universal scorer. Reproduce it as a registered baseline beside cost-only, deterministic evidence score, logistic, and shallow-tree baselines. Judge all at matched coverage and with day/session-block uncertainty; reject any objective whose apparent stability comes from suppressing exposure without incremental utility.

### 36. AlgoXpert IS–WFA–OOS protocol

AlgoXpert proposes a chronological deployment workflow: a stable IS plateau, three purged rolling WFA folds, majority-pass plus catastrophic drawdown veto, then a locked one-year OOS. The USDJPY M5 example uses MT5 “Every Tick,” Exness data for 2022–2025, a five-day purge, and predeclared Sharpe/Calmar/drawdown gates. Two of three WFA folds pass and the locked 2025 OOS clears the reported performance gates ([arXiv:2603.09219](https://arxiv.org/abs/2603.09219)).

**What is supported.** Stage gates, parameter locks, plateau selection, explicit failure semantics, normalized state at fold boundaries, and an OOS that is not opened after WFA failure are useful governance patterns.

**Limits.** The claimed execution-aware framework is not execution-validated: no latency or adverse slippage stress was run, one trade-density criterion was not directly reported, only one pair/broker is used, and a striking train/test reversal in fold 1 is left as an audit flag. Four post-validation variants introduce further selection, and small differences are untested.

**V8 implication.** Adopt the decision trace, not its numeric thresholds. A missing gate field is `UNKNOWN`, never implicit `PASS`. Stress execution before any deployment verdict. V8 should be stricter than majority-pass when the failed fold represents a known target regime or when a shared operational invariant fails.

### 37. Interpretable hypothesis-driven walk-forward validation

This separate paper runs 34 quarterly OOS tests from 2015–2024 for five hand-crafted daily-OHLCV hypotheses. It reports 0.55% annualized return, Sharpe 0.33, maximum drawdown −2.76%, and no statistical significance: t-test \(p=0.34\), bootstrap interval crossing zero, permutation \(p=0.98\), and only about 12% power for the observed effect. Performance is negative in low-volatility years and positive in high-volatility years ([arXiv:2512.12924](https://arxiv.org/abs/2512.12924)).

**What is supported.** A useful lab can return a well-instrumented null/insufficient-power result. Regime decomposition can expose that an aggregate statistic hides sign changes.

**Limits.** The label “microstructure signal” is too strong for daily OHLCV. Fixed 5 bp slippage does not model size, spread, or time of day; 34 quarterly observations are weak and regime boundaries are post-hoc. The paper speculates about LLM/RLHF extensions without evidence.

**V8 implication.** Preserve `NO_OPPORTUNITY`, `HINDSIGHT_ONLY`, `WEAKLY_SELECTABLE`, and `FORMALIZATION_CANDIDATE` rather than forcing a binary win. A non-significant but operationally clean experiment should block promotion while remaining a valuable falsification result.

### 38. Markets are hard to predict

Noguer's essay distinguishes no-arbitrage, informational efficiency, predictability, and net exploitability. It uses the \(P\)–\(Q\) wedge, Doob decomposition, filtration-relative prediction, capacity, impact, reflexivity, and regime uncertainty to argue that causal market structure can coexist with very limited scalable net alpha. Its explicit empirical sequence is: prediction → risk adjustment → costs/impact → capacity → OOS survival → live reflexive decay ([arXiv:2606.08209](https://arxiv.org/abs/2606.08209)).

**What is supported.** This is a disciplined taxonomy and a falsification agenda, not new empirical evidence. Volatility/order flow predictability cannot be silently converted into a positive conditional-mean trade claim.

**Limits.** Most results invoked are classical and the unification is conceptual. Entropy identities in stylized lognormal models do not estimate V8's attainable information. “Markets are causal” is not an actionable feature specification.

**V8 implication.** Every claim should name its filtration, action clock, cost/capacity domain, and survival horizon. `mechanism_unknown` is preferable to a causal story inferred from predictive association.

### 39. Analytical IS/OOS Sharpe ratios for linear strategies

Jacquier, Muhle-Karbe, and Zhu derive expected IS and OOS Sharpe ratios for Markowitz portfolios driven by linear predictive signals. Complexity grows with both signals and assets; longer samples and higher true signal strength improve the replication ratio. A commodity-futures simulation with 12 assets and 37 signals gives only about a 30% expected replication ratio after a ten-year backtest. Analytical approximations remain close under AR(1) signals and fat-tailed innovations. A 39-signal, 1926–2024 equity-premium dataset reproduces the predicted complexity/sample-length patterns ([arXiv:2501.03938](https://arxiv.org/abs/2501.03938)).

**What is supported.** There is a quantitative reason to begin V8 with few Experts/features and long defensible histories; cross-sectional dimension consumes sample capacity.

**Limits.** The main formulas are for linear/Gaussian-IID settings. The empirical exercise calibrates implied signal strength partly to realized OOS Sharpe, so it validates relationships more than independent prediction. The paper explicitly sets aside multiple testing, which compounds single-model estimation error.

**V8 implication.** Require a complexity/sample adequacy report before adding features, assets, Experts, or ranker interactions. “More assets” is not free replication when common shocks and correlated flow collapse effective sample size.

### 40. Probability of Backtest Overfitting (PBO/CSCV)—journal/author-PDF record

Items 40 and 41 are the journal/working-paper versions of the same work, not two independent sources. Bailey et al. construct a strategy-by-time performance matrix, enumerate symmetric IS/OOS partitions, select the IS winner, and measure the OOS rank logit. PBO is the fraction whose selected IS winner falls below the OOS median. In their seasonal-strategy example, optimization on a random walk produces an IS Sharpe of 1.27 but PBO around 55% ([author PDF](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf); [SSRN 2326253](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253)).

**What is supported.** PBO directly audits a *selection process* rather than assigning a single-trial p-value to the winner. It is model-free with respect to the chosen performance statistic.

**Limits stated by the authors.** Symmetric splitting may be inappropriate for strongly autocorrelated strategies; all trials must be disclosed; guided-search intermediate iterations require careful definition; PBO does not detect bad costs, look-ahead, or incorrect simulation; breaks outside the sample are invisible; high PBO does not imply every member is unskilled; optimizing to PBO is misuse.

**V8 implication.** Compute PBO only over a preregistered, coherent family after storing the complete family matrix. Never use it to tune Expert/scorer/ranker settings. Report the distribution of OOS degradation and ranks, not only a scalar.

### 41. Probability of Backtest Overfitting—duplicate SSRN working-paper record

Item 41 is SSRN 2326253, the working-paper record for item 40, and supplies no independent replication. Its method, evidence, limitations, and V8 implications are therefore those analyzed under item 40. Preserve both source links for provenance, but count one unique work and one evidential contribution ([SSRN 2326253](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253)).

### 42. Deflated Sharpe Ratio

Bailey and López de Prado combine a probabilistic Sharpe statistic (sample length, skewness, kurtosis) with the expected maximum Sharpe across an effective number of independent trials. DSR asks whether the observed Sharpe exceeds the selection-induced benchmark rather than zero ([author PDF](https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf); [SSRN 2460551](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551); [DOI](https://doi.org/10.3905/jpm.2014.40.5.094)).

**What is supported.** The winning Sharpe, non-normal return moments, track length, dispersion across tried Sharpe values, and the number/dependence of trials jointly determine evidential strength.

**Limits.** Effective independent trial count is difficult to estimate when strategies are correlated and the trial count exceeds sample length. Average correlation captures only linear dependence. DSR relies on the reported family and does not correct leakage, common simulator optimism, time dependence omitted from the Sharpe estimator, cost misspecification, or regime change.

**V8 implication.** DSR is a disclosure-backed diagnostic beside block-bootstrap uncertainty and a final frozen OOS—not a promotion gate by itself. Store trial covariance/lineage so the effective-trial assumption is inspectable.

### 43. High-throughput asset pricing

Chen and Dim apply empirical Bayes to 136,000 long-short accounting-ratio, past-return, and ticker strategies. A rolling, real-time top-1% EB portfolio earns a reported 5.7% annual return from 1983–2020, close to a portfolio of published anomalies; predictability is concentrated in accounting signals, small stocks, and pre-2004. EB predictions are accurate pre-2004 but too optimistic after the apparent structural break. Several stringent finance multiple-testing procedures miss many later OOS performers ([arXiv:2311.10685](https://arxiv.org/abs/2311.10685)).

**What is supported.** Large-scale search can be analyzed coherently if the full cross-sectional distribution is modeled and real-time availability is enforced. Overly conservative control can create large false-negative costs.

**Limits.** Outcomes are gross long-short returns rather than a complete capacity/impact/borrow-cost ledger. Thousands of accounting ratios are highly dependent, the prior can lag a structural break, and performance concentrates before 2004. The result does not license unrestricted V8 search.

**V8 implication.** Family-level empirical Bayes is a possible future research report when V8 genuinely has thousands of comparable candidates. It is premature for the baseline 2–3 Expert design. If used, posterior expected utility must include capacity/cost and time-varying priors, with the frozen holdout kept outside prior fitting.

### 44. PredictionMarketBench

PredictionMarketBench packages order books, trades, lifecycle, and settlement into deterministic event-driven episodes with maker/taker fees, queue-behind-displayed-volume semantics, tool-call budgets, and replayable logs. The initial release has only four January 2026 Kalshi episodes. A simple Bollinger agent gains overall while an active LLM agent loses, but profit is concentrated in one Bitcoin episode ([arXiv:2602.00133](https://arxiv.org/abs/2602.00133)).

**What is supported.** Portable episode manifests, unified clocks, deterministic replay, explicit API/action budgets, maker/taker separation, settlement semantics, and full trajectories are strong benchmark design patterns.

**Limits.** Four episodes cannot support strategy-performance inference. Latency, exact venue priority, counterfactual market response, and strategic interaction are absent; repeated benchmark use invites overfitting. Historical trade-only maker fills still depend on queue assumptions.

**V8 implication.** Mirror the harness structure for Level-3 research only when sequenced L2/trade data exists: episode manifest, event/receive/decision/submission clocks, order state machine, fees, settlement, and deterministic receipts. At Level 1, fail closed on passive/partial/queue claims.

---

## II. Market microstructure, order flow, liquidity, and impact

### 45. Generalized OFI under coarse snapshots

Su et al. note that three-second Chinese order-book snapshots can skip multiple tick movements, violating the event-by-event best-quote construction of classic OFI. Their generalized OFI sums quantities across traversed price levels; a log transform stabilizes depth. On ten CSI 500 constituents, contemporaneous linear fits at 30 seconds, one minute, and five minutes report much higher OOS \(R^2\) for log-GOFI than classic OFI ([arXiv:2112.02947](https://arxiv.org/abs/2112.02947)).

**Evidence and limit.** This is measurement evidence that an OFI definition must match feed granularity. The extremely high fit concerns contemporaneous price change and only ten selected stocks; it may partly reconstruct the same price movement encoded in quote changes. It is not evidence that log-GOFI was known before the move or remains profitable after spread/latency.

**V8 implication.** Every order-flow feature declares feed resolution and whether skipped levels are observable. Use `availability_time`, not exchange timestamp alone. A same-window OFI/return regression belongs to simulator calibration/attribution, not an Expert edge test.

### 46. Unified Hawkes theory of flow, impact, volume, and volatility

Muhle-Karbe et al. separate persistent “core” orders from reactive flow using Hawkes processes. In the scaling limit a single core-persistence parameter \(H_0\) links signed-flow persistence, rough unsigned volume, rough volatility, and power-law impact. Estimates around 0.75–0.8 imply near-square-root impact and rough extraday volatility ([arXiv:2601.23172](https://arxiv.org/abs/2601.23172)).

**Evidence and limit.** The paper gives a coherent structural bridge among stylized facts and uses real signed-flow data for \(H_0\). Many steps are asymptotic/approximate; “core” versus reaction flow is latent, and the volatility mapping concerns extraday scales. It does not identify a tradeable real-time core-flow state.

**V8 implication.** Simulation calibration must jointly test sign autocorrelation, unsigned-volume roughness, price diffusion, and impact—matching one curve is insufficient. Use persistence as a stress dimension, not a constant universal coefficient.

### 47. Artificial market for square-root impact and order imbalance

Barucca et al. simulate a mechanistic metaorder/propagator environment fitted to real data. The artificial market reproduces cross-correlations, square-root-like impact, order-flow imbalance behavior, and shows that public-flow algorithms can reconstruct useful metaorder proxies even without trader IDs ([arXiv:2509.05065](https://arxiv.org/abs/2509.05065)).

**Evidence and limit.** The work is a valuable *model criticism* exercise: approximate analytical results survive simulation of the fuller mechanism. But reproducing stylized facts with fitted parameters does not establish uniqueness; metaorder arrival/size and impact mechanisms are imposed, agents do not supply a full strategic LOB, and synthetic success cannot certify trading economics.

**V8 implication.** An artificial market may be used for metamorphic simulator tests—e.g., increasing core persistence should alter impact/volatility consistently. It must never enlarge permitted economic claims beyond the real tape used for calibration.

### 48. Price impact of order-book events

Cont, Kukanov, and Stoikov define event-level OFI from best-bid/ask price and size changes, aggregating limit orders, cancellations, and market orders. Across 50 U.S. stocks, short-interval mid-price changes are approximately linear in OFI; the slope is inversely related to depth. OFI explains price changes better than trade volume, and coefficients vary systematically with time scale and liquidity ([arXiv:1011.6402](https://arxiv.org/abs/1011.6402); [DOI](https://doi.org/10.1093/jjfinec/nbt003)).

**Evidence and limit.** This is strong measurement evidence for net best-quote flow and depth as local price-formation variables. The relation is mainly contemporaneous; consolidated TAQ does not reveal full queue identity, hidden liquidity, or causal exogenous order shocks. Linear fit at short intervals does not contradict nonlinear metaorder impact.

**V8 implication.** At L2 fidelity, calibrate an impact surface conditional on depth, spread, tick regime, and interval. At bar fidelity, do not backfill OFI or claim it. For an OFI Expert, freeze the feature before the forecast interval and benchmark against a depth-only model.

### 49. Propagators: transient versus history-dependent impact

Taranto et al. compare the transient-impact model, where past trade signs pass through decaying kernels, with a history-dependent model, where the surprise relative to expected order sign has permanent impact. Splitting events into price-changing and non-price-changing trades greatly improves response and signature-plot fits, especially for large-tick stocks; HDIM is theoretically cleaner but only marginally better empirically ([arXiv:1602.02735](https://arxiv.org/abs/1602.02735)).

**Evidence and limit.** Long-memory flow and nearly diffusive prices require liquidity/impact adaptation. Event taxonomy matters more than a fashionable model label. Models remain linear, largely use market orders, and acknowledge nonlinear metaorder impact and omitted limit/cancel events.

**V8 implication.** Simulator validation must distinguish price-changing from non-price-changing events and test negative-lag diagnostics for clock/feedback errors. A fixed per-trade slippage parameter is structurally inadequate for high-frequency work.

### 50. Gerig's hidden-order theory

Gerig's dissertation models the market as translating autocorrelated order flow into approximately uncorrelated returns through history-dependent, asymmetric liquidity. Using LSE brokerage codes as noisy trader proxies, it groups child orders into hidden orders, finds a heavy-tailed size distribution, and reports impact/return patterns closer to a hidden-order information model than a simple autoregressive sign model ([arXiv:0804.3818](https://arxiv.org/abs/0804.3818)).

**Evidence and limit.** It provides an early mechanism tying order splitting, asymmetric liquidity, concave/logarithmic total impact, return tails, and clustered volatility. Brokerage code is not trader identity; the 100-trade grouping rule is heuristic; the work is a 2007 physics dissertation on a small LSE setting and several functional-form debates evolved later.

**V8 implication.** Candidate “pressure” should distinguish persistent parent intent from public reactive flow only as a latent hypothesis. Without participant IDs, call it a proxy, quantify grouping uncertainty, and never treat reconstructed metaorders as ground truth labels.

### 51. Conditional impact dissertation

The thesis behind item 51 reconstructs market orders from 2015 LOBSTER data for four NASDAQ stocks, measures lag-1 response, and compares linear with decision-tree regressions for aggregate impact conditional on OFI. It finds positive immediate response, relation to spread, sublinear aggregate OFI response, and lower test MSE for a decision tree in the TSLA study ([arXiv:2004.08290](https://arxiv.org/abs/2004.08290)).

**Evidence and limit.** It is an accessible dissertation, not broad market evidence. It assumes market orders do not exceed available liquidity, neglects limit-order/cancel impact in part of the analysis, lacks parent-order identity, uses four selected stocks and one period, and does not compare a realistic execution ledger.

**V8 implication.** Tree nonlinearity can be a calibration baseline only after a linear depth/OFI model and time-blocked OOS. V8 should not interpret lower one-step MSE as incremental net utility.

### 52. Online Bayesian change points for order flow and impact

Tsaknaki, Lillo, and Mazzarisi extend Bayesian online change-point detection to Markov and score-driven within-regime dependence. On one month each of MSFT and TSLA order flow aggregated near one and three minutes, their time-varying-correlation model improves one-step OOS MSE over ARMA and IID-BOCPD. Detected regimes show concave price evolution with time/volume and improve online impact forecasts ([arXiv:2307.02375](https://arxiv.org/abs/2307.02375)).

**Evidence and limit.** The study supports online regime uncertainty rather than a fixed regime label. But two stocks/two months, arbitrary aggregation, constant hazard choices, and regimes inferred from the same order flow limit generalization. A detected regime is not proven to be a true metaorder.

**V8 implication.** If a regime feature is tested, MarketState stores the full posterior/run-length uncertainty, model version, and availability clock. Compare against rolling AR/score-driven baselines; promotion requires paired after-cost improvement, not only OFI MSE.

### 53. Intraday return–flow dynamics around macro news

Takahashi estimates a structural VAR identified through heteroskedasticity on one-second S&P 500 E-mini BBO data for 1,490 days (2008–2013), separately by 15-minute interval. Both price impact of OFI and reverse flow response to returns are significant at one-second scale; shocks largely dissipate within a second. Scheduled announcements increase price impact and return volatility while reducing flow impact and flow volatility, consistent with liquidity withdrawal ([arXiv:2508.06788](https://arxiv.org/abs/2508.06788)).

**Evidence and limit.** It directly addresses price/flow simultaneity and supplies a strong reason to condition on event calendar and intraday state. Identification depends on heteroskedasticity/rank assumptions; the data are one futures market ending in 2013; timestamps are only one-second; reported relations are not a net strategy.

**V8 implication.** Scheduled-news state must be point-in-time and calendar-versioned. Cost/impact stress should jump near releases. A feature using contemporaneous price and flow must be lagged beyond receive/decision latency.

### 54. Cross-impact of OFI in equities

Cont, Cucuringu, and Zhang study top-100 S&P 500 names using LOBSTER, 2017–2019. Integrated multi-level own-asset OFI explains contemporaneous returns so well that cross-asset OFI adds little; for future one-minute returns, sparse cross-asset OFI improves OOS \(R^2\) and a gross forecast portfolio relative to own-asset models, but the advantage decays rapidly with horizon. Network structure is low-rank/sectoral ([arXiv:2112.13213](https://arxiv.org/abs/2112.13213); [DOI](https://doi.org/10.1080/14697688.2023.2236159)).

**Evidence and limit.** The economic comparison explicitly ignores trading costs, so the annualized PnL table is not deployability evidence. Synchronous minute aggregation can create lead/lag and Epps effects; universes and LASSO choices consume degrees of freedom; common factors can masquerade as causal cross-impact.

**V8 implication.** Cross-asset state is a conditional experiment. Require synchronized availability, sparse/global-factor baselines, turnover/spread/impact/borrow costs, sector-cluster uncertainty, and proof that net gain survives at actionable latency. It is more relevant to future portfolio contention than to the initial Expert ontology.

### 55. Stochastic OFI response in CSI 300 futures

This paper models OFI as a shock with an Ornstein–Uhlenbeck-like mean-reverting response, possibly driven by heavy-tailed jumps, and couples it to price dynamics. One year of 500 ms CSI 300 futures snapshots is scanned over historical windows and future horizons; the authors report stable OFI sign effects, time-varying strength, and different “efficiency” regimes ([arXiv:2505.17388](https://arxiv.org/abs/2505.17388)).

**Evidence and limit.** The temporal-response question is useful: feature windows and forecast horizons are not interchangeable. But exhaustive horizon/window exploration, LASSO CV, and reported “profit points” need full multiplicity and cost accounting. The paper omits market depth and detailed volatility treatment, and the heavy-tail/OU model is not uniquely identified.

**V8 implication.** Register the horizon surface before OOS and control the entire surface as one family. Prefer stability of sign and effect under time-block replication to the best cell. No “inefficient regime” label may be promoted without net executable evidence.

### 56. Universal scaling and nonlinear aggregate impact

Patzelt and Bouchaud aggregate trades across NASDAQ, Nordic equities, and EUREX futures. After scale adjustment, volume-impact curves are sigmoidal and stable from roughly ten trades to intraday horizons. Extreme same-sign imbalance is associated with *smaller* price movement because abundant/refilled opposite liquidity pins the price; the probability that a trade changes mid-price approaches zero at extreme sign bias ([arXiv:1706.04163](https://arxiv.org/abs/1706.04163); [author PDF](https://www.cfm.com/wp-content/uploads/2022/12/301-2017-Universal-scaling-and-nonlinearity-of-aggregate-price-impact-in-financial-markets.pdf)).

**Evidence and limit.** This strongly contradicts a naive rule “more one-sided public flow ⇒ proportionally larger future return.” Results are observational aggregates without parent IDs; venue fragmentation, hidden liquidity, and conditioning affect curves. Aggregate sign impact differs from isolated causal metaorder impact.

**V8 implication.** Include an interaction between imbalance and opposing depth/refill; stress a saturation/pinning regime. A monotone OFI Expert must be rejected if its effect disappears or reverses conditional on liquidity.

### 57. MTD models for joint price/order-flow dynamics

Taranto et al. model buy/sell × price-changing/non-price-changing events with a generalized Mixture Transition Distribution. Parameter count grows linearly rather than exponentially with lag order. On six U.S. stocks, weakly constrained MTDg models improve one-day-ahead event log loss after ten-day rolling estimation relative to unconditional probabilities and parsimonious variants ([arXiv:1604.07556](https://arxiv.org/abs/1604.07556)).

**Evidence and limit.** A discrete event model is better matched to tick data than a Gaussian VAR and can represent long memory parsimoniously. Residual discrepancies remain; price-changing events are rare; missing book depth is likely material; kernels mix order splitting with reactions/herding and are not causal impulse responses.

**V8 implication.** Use MTDg only as an L2/L3 probabilistic baseline for next-event/fill tasks. Evaluate calibration and log loss by day before economics. Do not import it into bar-level V8 or label its kernel “market reaction.”

### 58. Order flow and price formation review

Lillo reviews LOB mechanisms, econometric/point-process/agent models, long-memory order flow, cross-impact, square-root metaorder impact, and co-impact. A central distinction is that market impact may reflect information, correct forecast by traders, or mechanical supply/demand; observational correlation alone cannot choose among them. Simultaneous metaorders and correlated signs can shift/crowd execution costs ([arXiv:2105.00521](https://arxiv.org/abs/2105.00521)).

**Evidence and limit.** This is a high-quality synthesis, not an independent empirical replication. It emphasizes latent dynamic liquidity and the difficulty of causal identification.

**V8 implication.** Candidate records must distinguish `predictive_association`, `mechanical_impact`, and `causal_mechanism_tested`. Portfolio execution stress should include co-impact and correlated crowding rather than summing independent single-order costs.

### 59. Duplicate of item 33, execution cross-bucket

Item 59 is exactly arXiv:2209.05559 again. Its execution relevance is negative: limit-order setting and trade closure are explicitly future work, so it supplies no evidence for learned V8 execution. Count it once bibliographically and tag it `VALIDATION` plus `EXECUTION_CAUTION`, not as a second source.

### 60. Duplicate of item 34, portfolio cross-bucket

Item 60 again links to arXiv:2507.07107. It is relevant to portfolio behavior because the reported system compares equal-weight top-100, sample-covariance MVO, and Ledoit–Wolf MVO, and caps weights at 3%. But the headline benefit mixes prediction, mask, loss, augmentation, and allocation changes, while real data are proprietary and impact is simplified. Count it once and tag it `VALIDATION`, `TRADABILITY`, and `PORTFOLIO_CONSTRUCTION`.

---

## III. Reconciled contradictions

| Apparent contradiction | Reconciliation | V8 rule |
|---|---|---|
| Short-horizon price change is linear in OFI (48), yet aggregate/metaorder impact is square-root, sigmoidal, or saturated (46, 47, 49, 56, 58). | Conditioning objects differ: best-quote net event flow over short bins, signed trade aggregates, and identified/latent parent orders are not interchangeable. Liquidity adapts with scale and history. | Every impact claim declares event type, conditioning variable, aggregation clock, size normalization, and horizon. |
| Persistent order flow should make returns predictable, yet prices are close to diffusive (46, 49, 50, 57). | Transient/history-dependent impact and asymmetric liquidity offset predictable flow; reaction flow changes the observed law. | Simulator tests must jointly match sign memory and return signature plots. |
| More one-sided flow should move price more, but extreme sign imbalance can pin price (56). | Extreme persistence often co-occurs with opposing visible/hidden liquidity and refill. | Add depth/refill interaction; reject unconditional monotonicity. |
| Cross-asset OFI adds little contemporaneously but helps short-horizon forecasts (54). | Own multi-level OFI absorbs simultaneous common flow; delayed attention/non-synchronicity can leave short lead/lag structure. | Separate contemporaneous attribution from strictly lagged forecast and latency tests. |
| PBO/DSR penalize broad search, while high-throughput EB finds broad search can work (40–43). | Search breadth is not the error; unconditioned selection and biased performance estimates are. Conservative procedures also trade false positives for false negatives. | Register the loss of false acceptance versus false rejection; disclose all trials; keep an untouched final evaluation. |
| Walk-forward/CSCV help, but symmetric or repeated splits can fail (33, 36, 40). | Dependence, state carryover, label overlap, regime boundaries, and reuse determine validity. | Declare the dependence unit, purge logic, state reset, and number of consultations. |
| A generative model can reduce overfitting (31), but synthetic data can amplify model error. | Synthetic paths add conditional variation, not new truth; usefulness is task- and calibration-dependent. | Synthetic evidence may stress or falsify but never certify edge. |
| A tradability mask lowers apparent IC but improves realizable performance (34). | Apparent statistical signal may reside in unreachable states. | Economic observability dominates predictive fit. |
| A ranker can maximize Sharpe while another candidate minimizes drawdown (36), and covariance optimization can beat equal weight (34). | Ranking is conditional on mandate and estimated covariance/cost; small sample instability can reverse order. | Predeclare portfolio utility and compare against deterministic 1/N/risk-budget baselines. |

---

## IV. V8 simulation truth requirements derived from the papers

### A. Fidelity-to-claim matrix

| Claim | Minimum defensible input | Required simulator semantics | Forbidden shortcut |
|---|---|---|---|
| Daily/bar directional Expert after aggressive entry | PIT OHLCV with corporate actions and availability clocks | Next eligible bar fill, both-leg fees/slippage, same-bar ambiguity policy, gaps/timeouts | Filling at decision bar close; using intrabar queue assumptions |
| Tradability/limit-move Expert | Exchange limit/halt/suspension fields known at decision time | Mask propagation through rolling features and target; unreachable order rejection | Post-hoc deletion after features are computed |
| Tick OFI forecast | Sequenced trades/quotes or L2 with receive times | Feature freeze before forecast interval; event ordering; spread/depth-aware aggressive fills | Same-window OFI as a forecast; bar reconstruction |
| Passive maker or fill-probability claim | Sequenced L2, trade prints, venue rules, calibrated queue position | Join/cancel/partial-fill/priority state machine, latency, maker/taker fees | Trade-through fill without queue; unlogged hidden-liquidity assumption |
| Metaorder/square-root impact | Participant/parent labels or explicitly uncertain reconstruction | Child/parent lineage, counterfactual limitation, size/ADV/volatility normalization | Treating public sign runs as true parent orders |
| Cross-impact/crowding | Synchronized multi-asset L2/trades and availability | Joint clocks, portfolio co-impact, correlated cost stress | Independent per-asset slippage addition |

### B. Required validation tests

1. **Causality/clock tests:** perturb future events and prove current MarketState/candidate/order hashes do not change; distinguish exchange, receive, decision, submission, eligibility, fill, and settlement times.
2. **Mask monotonicity:** downstream validity can become stricter but never silently re-enable a masked cell; rolling windows containing unreachable observations follow a preregistered policy.
3. **Event taxonomy:** at L2+, reproduce price-changing/non-price-changing response, sign-memory, depth-conditioned OFI slope, and signature plots before economic use.
4. **Impact stress:** linear, concave, square-root, sigmoidal/saturation, news-widened, and co-impact scenarios; promotion requires the conclusion not depend on an unsupported model.
5. **Queue tests:** no fill without executable contra flow; joining behind depth cannot improve priority; partial fills conserve size/cash; cancel latency is respected.
6. **Research-family receipts:** same data/code/config/seed/ledger hashes reproduce results; hidden/deleted trial detection is a validity failure.
7. **Differential tests:** scalar reference versus accelerated simulator, full-tape versus window replay, and two independent accounting implementations.

---

## V. Hypothesis Lab, scorer, ranker, and execution implications

### Hypothesis Lab

Each lab record should add these fields:

- `research_family_id`, `parent_variant_id`, `trial_index`, `mutation_reason`, `searched_after_failure`;
- `filtration` and all availability clocks;
- `feature_window`, `forecast_horizon`, `holding_horizon`, `purge`, `embargo`, `state_reset`;
- `dependence_unit`, `cluster_unit`, and bootstrap/permutation scheme;
- `tradability_mask_version` and exclusion reasons;
- `simulator_fidelity`, `unsupported_semantics`, `impact_model_family`;
- `gross_utility`, spread, fee, slippage, impact, borrow/funding, capacity, and net utility;
- `PBO`, `DSR`, or EB diagnostics with complete-family coverage assumptions;
- `consultations_of_frozen_holdout` and an automatic invalidation rule after the first authorized verdict.

Promotion still requires a fixed detector versus no-trade, direction-scrambled, cost-stressed, and equal-information global baselines. OFI/state prediction metrics are secondary; the primary comparison is paired net utility at a declared risk/capacity budget.

### Scorer

A scorer should not be optimized on raw Sharpe or “generalization ratio” alone. At matched candidate coverage, compare:

1. deterministic evidence score;
2. cost-only filter;
3. calibrated logistic model;
4. shallow tree;
5. any proposed GT-like or covariance-penalized objective.

Report calibration conditional on time/regime/tradability, expected utility by score decile, selective-risk/coverage curves, turnover and impact. Day/session-block paired uncertainty and an untouched final slice are mandatory. A score that selects fewer trades without improving matched-coverage utility fails.

### Ranker and portfolio layer

Ranking is not admissible until the ledger shows recurring **simultaneous acceptable candidates exceeding a binding resource limit**. Once that precondition holds:

- predeclare the mandate: growth, drawdown control, expected shortfall, liquidity/capacity, or a weighted utility;
- compare accept-all-with-risk-cap, deterministic 1/N, deterministic risk budget, and the learned/proposed ranker;
- model overlap in returns, holding intervals, sector/factor exposure, liquidity, and co-impact;
- use covariance shrinkage and show sensitivity to estimation window and equal-weight baseline;
- evaluate marginal portfolio contribution, not standalone candidate Sharpe;
- report rank stability and the uncertainty of pairwise order; ties/uncertainty should resolve to deterministic risk controls rather than false precision.

### Execution

The microstructure literature supports an execution *research agenda*, not learned execution now. Keep canonical deterministic execution as the comparator. Escalate fidelity only when a specific conclusion changes under supported stress. A learned executor is blocked until:

1. at least one Expert has replicated after-cost value under canonical execution;
2. the simulator passes level-specific truth tests;
3. fixed TWAP/aggressive/passive heuristics at matched information are strong baselines;
4. action/state/order accounting is deterministic and audited;
5. policy evaluation spans seeds, regimes, impact surfaces, latency, and capacity;
6. alpha and executor interaction is measured with a factorial experiment.

---

## VI. Proposed preregistered experiments

### EXP-VAL-01 — Complete-family overfitting audit

**Question:** How much selection degradation exists across all Expert geometries tried?

**Design:** Before final OOS, freeze the candidate-by-day utility matrix. Define coherent families by mechanism. Compute CSCV/PBO, DSR with disclosed effective-trial estimation, and block-bootstrap winner degradation. Compare with a simple one-variant-per-mechanism policy.

**Pass:** The nominated variant retains positive paired net utility on the untouched slice and diagnostics are below preregistered concern thresholds. **Fail:** Any missing trial, final-slice reuse, or conclusion dependent on excluding failed variants invalidates the family.

### EXP-VAL-02 — Complexity/sample-size frontier

**Question:** Do added Experts/features/assets improve OOS value after consuming effective sample size?

**Design:** Nested models with 1, 2, 3 Experts and fixed feature groups; equal information and search budget; plot block-OOS replication ratio against nominal/effective dimension. Include covariance-penalized linear baselines.

**Pass:** Added complexity produces replicated paired improvement, not merely IS Sharpe. **Fail:** replication falls or confidence intervals widen without utility gain.

### EXP-VAL-03 — Tradability-mask ablation

**Question:** Does any apparent signal depend on non-executable observations?

**Design:** Compare no mask, post-hoc row mask, and mask-first propagation. Audit factor values for the full lookback after limit/halt/suspension events. Primary metrics: realizable IC, reject reasons, net utility, and unreachable-order rate.

**Pass:** Mask-first is causally clean and conclusions survive. **Fail:** any accepted order references an unreachable observation; apparent metric improvement with invalid masks is logged as contamination.

### EXP-OFI-01 — Strictly lagged OFI versus contemporaneous attribution

**Question:** Does OFI forecast future returns, or only explain the same price move?

**Design:** With sequenced L2, compute classic, log/generalized, and multi-level OFI on \([t-w,t]\); decisions occur after receive latency; forecast \((t+\ell,t+\ell+h]\). Compare depth-only, own-OFI, cross-OFI, and scrambled-time baselines across horizons. Costs use next executable quote and impact stress.

**Pass:** Repeated positive paired net utility at actionable latency and stable sign across time/assets after family correction. **Fail:** value exists only at \(\ell=0\), only before costs, or only in searched cells.

### EXP-OFI-02 — Liquidity pinning and monotonicity falsification

**Question:** Does one-sided flow have a monotone conditional effect?

**Design:** Stratify by OFI/sign imbalance × opposing depth/refill × spread/tick regime. Fit monotone linear and flexible interaction models on development blocks. Freeze a saturation/pinning alternative.

**Pass:** A conditional form replicates and improves cost-aware prediction. **Fail:** an unconditional monotone Expert is rejected when extreme imbalance is pinned or sign reverses.

### EXP-OFI-03 — News and intraday state

**Question:** Are OFI coefficients stable around scheduled releases and through the day?

**Design:** PIT event calendar; separate pre-, release-, and post-windows; estimate depth, spread, price/flow impact, latency, and forecast utility. Cluster by announcement date. Stress spread/impact using empirical announcement quantiles.

**Pass:** A state-conditioned rule replicates; otherwise news windows become `NO_TRADE` or use larger cost reserves. **Fail:** the detector uses announcement values before release or pooled results hide a negative regime.

### EXP-OFI-04 — Regime posterior versus static model

**Question:** Does online change-point state improve decisions beyond rolling autoregression?

**Design:** BOCPD-IID, Markov BOCPD, score-driven BOCPD, rolling AR, and no-regime baselines. Only posterior/run-length values available at the decision clock. Evaluate OFI log loss first, then paired downstream utility.

**Pass:** Calibration and after-cost utility both improve on untouched assets/months. **Fail:** better OFI MSE without downstream gain, or unstable hazard sensitivity, blocks the feature.

### EXP-SIM-01 — Impact-model sensitivity ladder

**Question:** Does a V8 conclusion depend on linear slippage?

**Design:** Replay the same immutable orders under constant bps, spread/depth-linear, square-root participation, sigmoidal saturation, news stress, and correlated co-impact. Models are calibrated only with supported data; unsupported branches are adverse scenarios, not estimates.

**Pass:** Candidate/ranker verdict is invariant within preregistered plausible bounds. **Fail:** sign/rank changes imply a fidelity block, not parameter averaging.

### EXP-SIM-02 — Synthetic-market metamorphic tests

**Question:** Does the simulator respond coherently to known structural changes?

**Design:** Generate controlled Hawkes/propagator/MTD environments. Increase core-flow persistence, reduce depth, widen spread, add reactive flow, and introduce price-pinning liquidity. Test sign memory, volatility roughness, price diffusion, impact shape, and accounting.

**Pass:** Directional invariants hold and code recovers the known mechanism within tolerance. **Limit:** passing validates implementation behavior only, never market edge.

### EXP-RANK-01 — Contention and marginal portfolio utility

**Question:** Is a ranker needed and, if so, does it beat deterministic allocation?

**Design:** First estimate contention frequency without a ranker. If binding, replay accepted candidates through 1/N, risk parity/budget, capped greedy net utility, shrinkage MVO, and proposed ranker. Costs include correlated co-impact; use paired day-level differences.

**Pass:** Recurring contention plus stable incremental portfolio utility under cost/covariance stress. **Fail:** rare contention, standalone-metric gain only, or rank reversal within uncertainty rejects the ranker.

### EXP-EXEC-01 — Fidelity escalation decision

**Question:** Is Level 1 insufficient for the current Expert conclusion?

**Design:** Compare Level-1 conservative market-style replay with available Level-2 aggressive tick replay on the exact same decision stream. Analyze fill time, spread, slippage, timeout, and rank changes. Do not test passive fills unless Level 3 is certified.

**Pass:** If verdict is stable, retain the cheaper level. **Escalate:** material sign/rank sensitivity with supportable richer data. **Block:** sensitivity depends on queue/passive semantics not in the data.

---

## VII. Final research position

The papers strengthen V8's minimal baseline rather than justify a more complex architecture. The defensible starting point remains:

`point-in-time MarketState → deterministic self-gating Experts → full Candidate lifecycle → deterministic risk/acceptance → canonical Level-1 ledger`.

The literature adds sharper admission conditions:

- **Router:** only after self-gating cost is binding and valuable-candidate recall can be measured.
- **Scorer:** only after matched-coverage paired OOS gain, calibration, and complete-family correction.
- **Ranker:** only after demonstrated portfolio contention and marginal net utility under covariance/co-impact stress.
- **Learned execution/RL:** only after certified Expert value and simulator authority at the required fidelity.
- **OFI/microstructure Expert:** only with sequenced data, explicit availability latency, depth/spread/news conditioning, and strict separation of contemporaneous attribution from forecast.

The decisive lesson is not “use PBO,” “use square-root impact,” or “use OFI.” It is to bind each claim to the data, clock, conditioning variable, search family, simulator level, and portfolio decision that can actually support it. Anything broader is an experiment proposal, not a V8 fact.
