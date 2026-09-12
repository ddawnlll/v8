# arXiv / web sweep — economy surface: market impact, capacity, costs, MinTRL

- Task: `t_93d68ab4` (board `v8`, profile `v8-scout`) — owner sleep-shift 1/3
- Date: 2026-09-12 · branch `wt/t_93d68ab4` · base `b0ee7883`
- Scope: transaction-cost models; market-impact / capacity estimation from L2; funding-rate finality; MinTRL estimators; venue-fee / implementation-shortfall calibration.
- Related open issues: #382 (capacity + market impact from L2), #378 (MinTRL), #385 (operating net + venue-cost calibration), #393 (economic evidence gate).
- Hard boundaries observed here: **no code changes, no economic claim, no synthetic input**. This is a research map, not an architecture decision and not evidence of edge. Every citation below was fetched and its content read on 2026-09-12; every referenced artifact exists (see §7).

## 0. Reading conventions

Classification labels follow `docs/research/SOURCE_MAP.md` (largest single prior art on this file's question):

| Label | Meaning |
|---|---|
| `LITERATURE_SUPPORTED` | The cited source supports the stated mechanism at the stated scope. |
| `DESIGN_INFERENCE` | A defensible engineering inference from the source, not a result in it. |
| `PROVISIONAL_DECISION` | Reasonable, but needs a v8 ablation before it binds anything. |
| `OPEN_QUESTION` | No source found; do not treat as settled. |
| `REJECTED_OPTION` | Explicitly not to be used as v8 evidence (with the reason). |
| `DATA_BLOCKED` | The v8 input needed to use the source does not exist in the current data surface. |

Present v8-next surfaces referenced below (all committed at `f41d58c2`, unchanged by this task):
`v8-next/src/v8_next/evaluation/capacity.py`, `.../costs.py`, `.../mintrl.py`,
`.../economic_benchmark.py::capacity_table` (line 3681).

## Topic 1 — Transaction-cost / execution models

### 1.1 Almgren & Chriss (2000), *Optimal execution of portfolio transactions*
- Journal of Risk 3(2): 5–39. Locator verified through arXiv:1111.6826 §1–2 and its reference list.
- Key structure: total execution cost is decomposed into a **permanent** component (linear in size, moves the price for everyone) and a **temporary** component (proportional to the trading rate, decays afterwards); the optimum minimises expected cost plus a risk-aversion × execution-variance penalty. With linear impact the optimal schedule is front-loaded and decays exponentially; the solution family is a cost-vs-risk **frontier**, not a single number.
- Assumptions that travel badly: arithmetic (not log) price, fixed horizon, exogenous linear impact, no order-book depth or queueing.
- Maps to v8-next: nothing directly. It is the reference *decomposition* (permanent vs temporary vs spread vs fees) that `costs.py` must not collapse into one scalar.
- Does **not** map: no v8 execution schedule exists, and the model's linear-impact premise is contradicted by §2.1 below.

### 1.2 Almgren (2003), *Optimal execution with nonlinear impact functions and trading-enhanced risk*
- Applied Mathematical Finance 10(1): 1–18; content read through the review in arXiv:1111.6826.
- Impact per share is taken as a **power law of the trading rate** (exponent arbitrary, so the square-root law of §2.1 is inside the family); a "characteristic time" replaces the constant of the linear model and shrinks as execution proceeds.
- Marzo, Ritelli & Zagaglia (2011), arXiv:1111.6826, show Almgren's solution method assumes zero initial trading rate (`v₀ = 0`); with positive initial trades the problem needs a hypergeometric/shooting solution and the optimum changes materially. → **the closed form is not a safe transplant.**
- Maps: `DESIGN_INFERENCE` only — if a capacity model is ever fitted, it must state whether the impact exponent is estimated or assumed, and the "no trading at t=0" corner must be excluded, not silently used.

### 1.3 Curato, Gatheral & Lillo (2014), *Optimal execution with nonlinear transient market impact*
- arXiv:1412.4839. Model: `S(t) = S₀ + ∫₀ᵗ f(ẋ(s)) G(t−s) ds + ∫σ dW(s)` — instantaneous impact `f(·)` convolved with a decay kernel `G(·)`.
- Findings that matter operationally: with concave instantaneous impact the cost landscape is **rugged**, brute-force optimisation produces alternating buy/sell bursts, and for strong nonlinearity those bursts carry **negative expected cost** — i.e. the model admits price manipulation. The authors regularise by adding a bid-ask spread cost, or by forcing convexity of instantaneous impact at high trading rates.
- Maps to v8: `REJECTED_OPTION` for any fitted nonlinear transient-impact model that is not accompanied by an explicit spread-cost or convexity guard. A capacity/impact module that can manufacture negative-cost round trips is a money machine, not a measurement.

## Topic 2 — Market impact and capacity estimation from L2

### 2.1 Tóth, Lempérière, Deremble, de Lataillade, Kockelkoren, Potters & Bouchaud (2011), *Anomalous price impact and the critical nature of liquidity in financial markets*
- Phys. Rev. X 1: 021006; arXiv:1105.1694.
- Formula: `Δ ≈ Y·σ·√(Q/V)` — impact measured as a fraction of daily volatility scales with the **square root** of metaorder size relative to daily volume, `Y` of order unity. Marginal impact `∝ Q^(−1/2)`: it *diverges* for small orders instead of vanishing.
- Consequence that inverts the usual capacity intuition: linear-in-notional extrapolation is wrong in both directions. It understates the cost of tiny orders and overstates the marginal cost of large ones; neither a 10× nor a 100× row is recoverable by scaling.
- Maps to v8: `DESIGN_INFERENCE` — the square-root shape is a *sanity check* on any measured participation/cost curve, never a coefficient to hardcode (`Y` is venue-, horizon- and regime-specific).

### 2.2 Cont, Kukanov & Stoikov (2014), *The price impact of order book events*
- Journal of Financial Econometrics 12(1): 47–88; arXiv:1011.6402 (DOI 10.1093/jjfinec/nbt003).
- Formula: `ΔP_k = β·OFI_k + ε_k`, with **order flow imbalance** `OFI` built from changes in the best-bid/ask queue sizes, treating market orders, limit orders and cancellations by their net effect on the queue. `β ∝ 1/depth`: the impact coefficient is the reciprocal of available depth. Average R² ≈ 65% across 50 US stocks, stable across sub-samples and stocks.
- Crucial negative result for v8: after controlling for OFI, **trade volume adds almost nothing**, and the "square-root law in volume" is largely an artefact of regressing price on volume instead of imbalance. The volume-based relation is the noisier one.
- Maps to v8 (#382): this is the single most directly actionable item in this memo. `LITERATURE_SUPPORTED` that event-time L2 quote sequencing (best bid/ask price+size updates) is the *minimum* input from which a real impact coefficient can be estimated — far less data than "full L2 depth", but still event-sequenced quotes.
- Does **not** map: v8's evaluation tape is 1h OHLCV (`capacity_table` documents this). No OFI, no queue updates → the coefficient is `DATA_BLOCKED`, not "approximately zero".

### 2.3 Vodret, Mastromatteo, Tóth & Benzaquen (2021), *Do fundamentals shape the price response? A critical assessment of linear impact models*
- arXiv:2112.04245.
- Finding: at high frequency the price response to **signed order flow** is sub-linear; at low frequency it is **linear** in order-flow imbalance. A microfounded stationary-Kyle model and the phenomenological propagator model predict the *same shape* at high frequency and disagree only on magnitude, by an amount tied to excess volatility (`Σ_SK⁰ < Σ_F⁰ < Σ_emp`).
- Maps to v8: `DESIGN_INFERENCE` — an impact exponent estimated on one horizon class must not be reused at another. Any future `capacity.py` coefficient must carry the sampling horizon in its identity (the same discipline `MinTRLPlan.interval_unit` already imposes).

### 2.4 Moallemi & Yuan, *A Model for Queue Position Valuation in a Limit Order Book*
- Working paper, `moallemi.com/ciamac/papers/queue-value-2016.pdf` (read; also presented at the Institut Louis Bachelier microstructure seminar).
- Formula: order value `V(q, δ) = α(q)·δ − β(q)`, where `q` is queue position, `δ` is the liquidity premium (spread share), `α(q) = P(τ_q < ∞)` is the fill probability (non-increasing in `q`, converging to `P(price jump > 0)`) and `β(q)` is the adverse-selection cost conditional on a fill (increasing in `q`). In their NASDAQ ITCH validation, front-of-queue value is comparable to the bid-ask spread for some names — queue position cannot be neglected.
- Inputs required: market-by-order (event-level) data plus jump/trade/cancel arrival-rate ratios and a linear impact coefficient λ.
- Maps to v8 (#382): `DATA_BLOCKED`. v8 has no MBO/MBP capture; nothing in `capacity.py` measures queue position, and it must not be imputed.

### 2.5 Lokin & Yu (2024), *Fill Probabilities in a Limit Order Book with State-Dependent Stochastic Order Flows*
- arXiv:2403.02572.
- Semi-analytical fill probabilities for orders at the best quote and one level deeper, under order-flow intensities that depend on the book state; calibrated on real FX spot LOB data. Empirical note: fill probabilities **beyond one tick from the best quote are typically negligible**.
- Design consequence: marginal value of deep-book data is low for *fill probability*; what matters is state dependence at the touch and honest sequencing. (Their §1 also cites Fabre & Ragel, arXiv:2307.04863, for empirical state-dependent execution probability — both links live.)
- Maps to v8: `DESIGN_INFERENCE` — a future capture plan should prioritise top-of-book event data, not full depth, and fill probability must be *estimated* from observed fills; `capacity.py` already refuses to publish a capacity row without `filled_qty`/`fill_price`, which is the correct fail-closed posture.

### 2.6 Capacity economics — four sources, all with unported assumptions
- **Bonelli, Landier, Simon & Thesmar (2019)**, *The Capacity of Trading Strategies*, SSRN 2585399 (HEC Paris Research Paper FIN-2015-1089). Closed-form scale-to-performance frontier from a Garleanu–Pedersen-style dynamic model. Reported comparative statics: capacity elasticity **1** with respect to the price-impact/liquidity parameter and **2** with respect to the speed of signal mean-reversion, so fast-decaying signals have capacities orders of magnitude smaller; capacity rose in the 2000s with liquidity.
- **Chan (2021)**, *Market Impact Decay and Capacity*, SSRN 3911635. Impact decays over **weeks**, not intraday; because trades become more autocorrelated as capital grows, slow decay implies capacity estimates **significantly lower** than prior studies. Numerical (not closed-form) methodology, flexible to any impact specification.
- **Cartea, Cucuringu, Jin & Zhu**, *Bottom-Up Capacity Constraints and the Limits of Anomaly Profitability*, SSRN (2025) / FoFI-2026 working-paper PDF. Closest to #382's literal requirement: bottom-up capacity in dollars, per-stock trade size `S_i,t = min(δ·ADV_i,t·|r̂|·100, φ·ADV_i,t, Cap)` with participation cap φ (baseline φ = 5% ADV, Cap = $1M, δ = 1% per 1% predicted return), plus an ex-ante cost filter that drops trades whose expected return does not cover estimated cost. Reported: capacity constraints alone cut strategy Sharpe by ~40% in-sample and ~22% out-of-sample **before** costs.
- **Frazzini, Israel & Moskowitz**, *Trading Costs* (AQR working paper; SSRN 3229719). $1.7tn of **live** executions, 21 developed equity markets, 1998–2016, implementation-shortfall methodology. Reported: mean market impact ≈ 9.97 bp and mean implementation shortfall ≈ 11.02 bp (value-weighted 15.14 / 16.06 bp); ~85% of measured impact is *permanent* — only ≈1.26 bp reverses over the next 24h. A cost model fitted to realised fills beats theory-calibrated models out of sample against independent broker data.
- Cross-cutting `DESIGN_INFERENCE` for v8: capacity is a **per-venue, per-horizon, per-participation-rate** object that must be measured from fills and ADV on the actual tape. Every closed form above carries equity-microstructure parameters (κ, λ, ADV, per-stock signals) that do not transport to crypto perps, and Chan's result says the decay assumption dominates the answer.
- `REJECTED_OPTION`: scaling a notional-proportional cost row, or porting a published capacity formula, as a v8 capacity statement. `DATA_BLOCKED` until sequenced quote/fill/ADV observations exist.

## Topic 3 — Funding-rate finality

### 3.1 He, Manela, Ross & von Wachter (2022, rev. 2024), *Fundamentals of Perpetual Futures*
- arXiv:2212.06888.
- Contract mechanics as documented there: funding is paid **every 8 hours** (1/1095 year) and is approximately the average futures-vs-spot spread over the prior 8 hours; longs pay shorts when the futures price is above spot; exchanges apply a clamp for small deviations.
- Theory: no-arbitrage price under **random-maturity** arbitrage (time-to-maturity is random because a perpetual never expires), and no-arbitrage **bounds** when a round-trip cost `C` applies. Funding-rate arbitrage is *not* risk-free: there is no fixed expiry at which the trade is guaranteed to unwind profitably.
- Empirical: mean absolute deviation ≈ 60%–90% **per year** across currencies (large vs FX); deviations decline ~11%/yr as capital enters; decomposition of the strategy return into price-convergence versus funding-payment components (their Table 13), i.e. funding is a separately attributable P&L channel.
- Cost tiers used: high-cost retail tier = 6.75 bp spot + 1.44 bp futures per leg; reported strategy Sharpe 1.8 at the highest Binance cost tier, up to ~3.5 for fee-free participants.
- Maps to v8 (#385): `LITERATURE_SUPPORTED` that **funding is a settlement-period, separately reconcilable cashflow** and that a funding P&L must be attributed to settlement intervals, not to a price-PnL residual. `PROVISIONAL_DECISION` that a v8 funding cell may only be populated from settlement records; the existing `funding_cost: float | None` with `NOT_MEASURED` states is the right shape.

### 3.2 Schmeling, Schrimpf & Todorov (BIS WP 1087, *Crypto carry*, April 2023 rev. October 2025)
- https://www.bis.org/publ/work1087.htm (redirects to the publication page; content read).
- Reported: crypto carry averages above 10% p.a. and has exceeded 40% p.a.; it is driven by trend-chasing leveraged demand plus *scarce arbitrage capital* under regulatory/margin frictions (no cross-margining between spot and CME futures), not by interest-rate differentials.
- Directly relevant to "finality": high carry **predicts liquidations of short-futures positions** (the cash-and-carry leg) and predicts future price crashes. The trade can be right on funding and still be force-closed before settlement economics accrue.
- Maps to v8: `LITERATURE_SUPPORTED` that a funding carry cell without an interim margin/liquidation channel is an incomplete accounting; `DESIGN_INFERENCE` that any future operating-net receipt should keep funding carry and margin/liquidation events as separate, separately-sourced components.

### 3.3 Zhivkov (2026), *The Two-Tiered Structure of Cryptocurrency Funding Rate Markets*
- Mathematics 14(2): 346, DOI 10.3390/math14020346. 35.7M one-minute observations, 26 venues (11 CEX / 15 DEX), 749 symbols, 8 consecutive days.
- Reported: 17% of observations show spreads ≥ 20 bp, but only **40% of top opportunities are profitable after transaction costs and spread reversals**; forced exits occur in 95% of simulated delta-neutral portfolios; information flow runs CEX→DEX only.
- Maps to v8: `LITERATURE_SUPPORTED` for the distinction between a **quoted funding spread** and a **realised funding P&L**. An 8-day window over 26 venues is also a reminder that venue-comparability (interval, clamp, index) is part of the identity, not a formatting detail — the same discipline `MinTRLPlan.interval_unit`/`annualization_factor` already imposes on horizon evidence.

### 3.4 Pindza (2026), *CEX–DEX funding rate arbitrage as a basis trade* (Digital Finance, DOI 10.1007/s42521-026-00213-3)
- Design: Binance funding for BTC/ETH/SOL 2021–2024 plus **synthetic DEX funding rates** constructed to isolate oracle lag, structural spread and DEX noise; five-component variance decomposition, Brinson-style PnL attribution, Cox survival model for liquidation, CVaR venue allocation.
- Reported: net returns driven mainly by funding carry but "highly assumption-sensitive"; funding + residual market risk dominate variance; leverage dominates liquidation hazard.
- Maps to v8: the *framing* (funding carry / basis convergence / slippage / fees / liquidation as separate attributed lines) is `DESIGN_INFERENCE`-compatible with #385; the **synthetic DEX rates** are `REJECTED_OPTION` as v8 evidence. This paper is a labelled example of the class of study v8 must not copy: synthetic inputs, no certified edge.

## Topic 4 — MinTRL estimators

### 4.1 Bailey & López de Prado (2012), *The Sharpe Ratio Efficient Frontier* (SSRN 1821643)
- Probabilistic Sharpe Ratio `PSR(SR*) = Φ[(ŜR − SR*)/σ(ŜR)]` with
  `σ(ŜR) = √[(1 − γ̂₃·SR + ((γ̂₄−1)/4)·SR²)/(T−1)]`, γ̂₃ skewness, γ̂₄ kurtosis.
- Minimum Track Record Length (the estimator #378 names):
  `MinTRL = 1 + (1 − γ̂₃·SR* + ((γ̂₄−1)/4)·SR*²)·(z_α / (ŜR − SR*))²`.
- Properties: monotone in the target/null gap, longer when returns are left-skewed or fat-tailed or the confidence is higher; no power term; it is a **single-trial** horizon, explicitly a minimum — more trials require more.

### 4.2 Bailey & López de Prado (2014), *The Deflated Sharpe Ratio* (J. Portfolio Management 40(5): 94–107)
- `SR₀ = √V[ŜR_n]·((1−γ)Φ⁻¹(1−1/N) + γΦ⁻¹(1−1/(Ne)))` — the expected maximum Sharpe under N independent trials; then `DSR = Φ((ŜR* − SR₀)√(T−1) / √(1 − γ̂₃SR₀ + ((γ̂₄−1)/4)SR₀²))`, i.e. PSR with the threshold replaced by the selection-bias threshold.
- Requires two self-reported, unauditable inputs: N (number of trials) and V[ŜR_n] (dispersion across trials).

### 4.3 Bailey, Borwein, López de Prado & Zhu (2014), *Pseudo-Mathematics and Financial Charlatanism* (Notices of the AMS 61(5): 458–, DOI 10.1090/noti1105)
- Sibling notion: **Minimum Backtest Length** — grows with the number of configurations tried, so a short backtest plus a wide search cannot contain its own evidence. Under memory effects (serial dependence) overfitting produces **negative** expected out-of-sample return, not merely zero.

### 4.4 Lo (2002), *The Statistics of Sharpe Ratios* (Financial Analysts Journal)
- The sampling distribution of ŜR depends on serial correlation; annualisation and interval choice change the estimand. PSR/DSR/MinTRL all inherit an IID-ish assumption, so a dependence term must be declared rather than assumed away.

### 4.5 Independent critique of DSR (sharperat.io, *Do not deflate I: The effects of reality on the deflated Sharpe ratio*)
- Argument, with simulation: the maximum of N Gaussians is Gumbel, not Normal, so DSR is **not uniform under the null** and is therefore not a calibrated p-value; in their simulations type-I rates are *below* nominal (conservative) and vary with the observed N; the expected-maximum subtraction is "probably wrong"; the effective-trial-count correction `N̂ = ρ + (1−ρ)M` is itself estimated on thin data.
- Maps to v8: `DESIGN_INFERENCE` — DSR may be used as a *deflation diagnostic*, not as a hypothesis test with a nominal level, and never as the economic verdict. The binding control remains Constitution Rule 12 + the multiplicity ledger (`NO_ECONOMIC_CLAIM` until a valid authority receipt exists).

### 4.6 Reconciliation with the current v8-next implementation
`v8-next/src/v8_next/evaluation/mintrl.py` implements a **declared power-based required-N**:
`required = ceil((z_{1−α/2} + z_power)² · variance · dependence_factor / (SR_target − SR_null)²)`, with `MinTRLPlan` freezing `target_sharpe, null_sharpe, confidence, power, variance, dependence_factor, interval_unit, annualization_factor, method_version` and failing closed (`UNSUPPORTED` without a plan, `UNDERPOWERED` below the horizon).

Concrete deltas against §4.1 that #378 should decide explicitly:
1. the implemented z-term is `z_{1−α/2} + z_power` (a two-sided size + power expression); the Bailey–LdP closed form uses a single `z_α` and **no power term**;
2. the implemented estimator does not consume skewness/kurtosis, so the non-normality adjustment of §4.1/§4.2 is absent;
3. the closed form carries a `+1` sample-correction that the implementation omits.

None of these is a defect claim — the plan *declares* a model — but two estimators with the same name and different identities is exactly the ambiguity #378's invariant R1 ("target, null, alpha/confidence, power, variance and dependence assumptions are explicit") is meant to remove. `PROVISIONAL_DECISION`: pick one identity per `method_version` and cross-check it against the published closed form on independent analytic cases. MinTRL remains horizon evidence: it is not a strategy pass and its output stays descriptive.

## Topic 5 — Venue-fee and implementation-shortfall calibration

### 5.1 Perold (1988), *The Implementation Shortfall: Paper vs. Reality*
- Journal of Portfolio Management 14(3): 4–9 (publisher record: HBS faculty listing + ProQuest).
- Definition that everything downstream uses: total implementation shortfall = **execution cost** (fills vs the decision/benchmark price) **+ opportunity cost** of what was not executed. The benchmark price must be the decision price, and it must be named.

### 5.2 Frazzini, Israel & Moskowitz, *Trading Costs* — see §2.6
- Provides the modern empirical calibration of Perold's measure from live fills, including the permanent/temporary split (~85% permanent) and the finding that realised-fill models dominate theory-based cost models out of sample.

### 5.3 Malinova & Park (2015), *Subsidizing Liquidity: The Impact of Make/Take Fees on Market Quality*
- Journal of Finance 70(2): 509–536, DOI 10.1111/jofi.12230 (Toronto Stock Exchange fee-composition change).
- Result: after a fee-composition change, posted quotes adjust and posted spreads decline, but **transaction costs for liquidity demanders are unaffected once fees are taken into account**; aggressive-order use rises (retail especially) and adverse-selection costs fall.
- Maps to v8 (#385): a fee *schedule* is not a cost *measurement*, and fee changes move who pays rather than the net. Binding a benchmark receipt to a configured fee constant (`--taker-fee`) is not venue calibration.

### 5.4 Battalio, Corwin & Jennings (2016), *Can Brokers Have It All? On the Relation between Make-Take Fees and Limit Order Execution Quality*
- Journal of Finance 71(5): 2193–2238, DOI 10.1111/jofi.12422.
- Result: limit-order execution quality (fill likelihood, fill speed, realised spread) is **negatively related to the take fee** of the venue: similarly priced orders on high-rebate/high-take-fee venues fill less often and in worse conditions. Routing to maximise rebates does not maximise execution quality.
- Maps to v8 (#385/#382): a single scalar `taker_fee` collapses venue heterogeneity and cannot represent realised execution quality; fee tier, venue and fill outcome must travel together in the receipt.

### 5.5 SEC Division of Trading and Markets memorandum to the Equity Market Structure Advisory Committee (20 October 2015), *Maker-Taker Fees on Equities Exchanges*
- `https://www.sec.gov/spotlight/emsac/memo-maker-taker-fees-on-equities-exchanges.pdf` (content read).
- Structural facts: under Reg NMS Rule 610 access fees are capped at $0.003/share; rebates are funded out of take fees; fee filings are immediately effective, so schedules are venue-specific and change frequently.
- Maps to v8: `LITERATURE_SUPPORTED` that **fee schedules are dated, venue-specific artifacts**. A cost receipt without (venue, tier, effective date, source artifact) is not a receipt.

### 5.6 Reconciliation with the current v8-next implementation
`v8-next/src/v8_next/evaluation/costs.py` (committed at `f41d58c2`) already occupies the right slot:
- `calibrate_venue_cost(fills, source_artifact)` verifies the artifact binding, then computes `fee_rate = Σfee/Σqty` and `fill_vs_mid_bps = mean(|fill_price − reference_mid|/reference_mid·1e4)`; returns `DATA_BLOCKED` when there are no fills **or** no `reference_mid` rows.
- `compute_operating_net(...)` builds `strategy_net = transaction_pnl + funding − explicit_fees` (fees skipped when `price_pnl_already_net_of_friction`), `operating_net = strategy_net − Σoperating_costs`, fails closed on missing funding/fees/expenses or currency mismatch, and always returns `status = NO_ECONOMIC_CLAIM`.
- Gaps relative to §5.1–5.5, all `OPEN_QUESTION` for #385 rather than defects: no maker/taker separation, no venue/tier/effective-date identity on the fee rate, no permanent-vs-temporary split of the fill-vs-mid friction (so no reversion test), and `price_pnl_already_net_of_friction` is a caller-declared flag that is not machine-verified — that flag is the only thing standing between the ledger and a spread double-count.

## 6. Mapping summary (issue → what is available → what stays blocked)

| Issue | Source-supported core | v8-next surface today | Status |
|---|---|---|---|
| #382 capacity/impact from L2 | OFI→price linearity with slope ∝ 1/depth (Cont et al.); √-law shape as sanity check (Tóth et al.); participation caps + ex-ante cost filter (Cartea et al.); ADV/participation capacity needs fills (Frazzini et al., Chan) | `capacity.py` accepts sequenced `mid/spread/adv_qty/requested_qty/filled_qty/fill_price`; `capacity_table()` remains linear accounting rows with an explicit UNMODELED list | measurable **only** with a real L2/fill capture; otherwise `DATA_BLOCKED` (no invented coefficients) |
| #378 MinTRL | PSR/MinTRL closed form (Bailey & LdP 2012); DSR threshold (2014); MinBTL (2014); dependence via Lo (2002) | `mintrl.py` plan + fail-closed statuses | estimable, but **identity must be declared**: implementation ≠ published closed form (§4.6) |
| #385 operating net + venue costs | Perold shortfall; live-fill IS/MI and permanent-vs-temporary split (Frazzini et al.); fee ≠ cost (Malinova & Park); fill quality ∝ −take fee (Battalio et al.); dated venue fee schedules (SEC 2015) | `costs.py` calibration + operating-net with `ArtifactBinding` and fail-closed states | measurable given venue receipts; venue/tier/date identity and the double-count flag are open |
| #393 economic evidence gate | DSR is multiplicity evidence, not edge; and per §4.5 not a calibrated p-value; backtest overfitting can be *negatively* predictive (Bailey et al. 2014) | Rule 12 status vocabulary + gate machinery | unchanged: **`NO_ECONOMIC_CLAIM`**; this memo mints nothing |

Does-not-map list (collected):
- any hardcoded impact coefficient (Tóth `Y`, Cont `β`, Almgren exponent) — `REJECTED_OPTION`;
- equity-anomaly capacity formulas transported to crypto perps (Bonelli et al., Cartea et al.) — `DESIGN_INFERENCE` at best, `DATA_BLOCKED` for parameters;
- nonlinear transient-impact fits without a spread/convexity guard (Curato–Gatheral–Lillo) — `REJECTED_OPTION`;
- queue-position value without MBO data (Moallemi–Yuan) — `DATA_BLOCKED`;
- synthetic DEX funding rates as funding evidence (Pindza) — `REJECTED_OPTION`;
- a quoted funding spread *or* a configured fee constant presented as realised cost — `REJECTED_OPTION`;
- DSR/MinTRL read as an edge verdict or as a p-value with a nominal level — `REJECTED_OPTION`;
- linear 1×/10×/100× notional rows read as capacity validation (already labelled UNMODELED in `capacity_table`) — `REJECTED_OPTION`.

## 7. Citation verification record (all checks run 2026-09-12)

Method: HTTP status via `curl -L` plus, for every artifact whose existence or content is asserted above, a content fetch whose text was read in this session. Where a publisher blocked automated fetch (403/405 = bot wall, not a 404), existence is established by the returned publisher metadata or an independent index record, and that is stated rather than hidden.

| # | Artifact | Check | Result |
|---|---|---|---|
| 1 | arXiv:1105.1694 (Tóth et al.) | GET | 200, abstract+body read |
| 2 | arXiv:1011.6402 (Cont et al.) | GET | 200, abstract+journal ref (JFEC 12(1):47–88, DOI 10.1093/jjfinec/nbt003) read |
| 3 | arXiv:1111.6826 (Marzo et al.) | GET | 200, body read (incl. Almgren 2003 citation record) |
| 4 | arXiv:1412.4839 (Curato, Gatheral, Lillo) | GET | 200, abstract+model section read |
| 5 | arXiv:2212.06888 (He, Manela, Ross, von Wachter) | GET | 200, authors/mechanics/tables read |
| 6 | arXiv:2403.02572 (Lokin & Yu) | GET | 200, abstract+§1 read |
| 7 | arXiv:2112.04245 (Vodret et al.) | GET | 200, authors+abstract read |
| 8 | arXiv:2307.04863 (Fabre & Ragel) | GET | 200 (existence); content relied on only as cited by #6 |
| 9 | BIS WP 1087 *Crypto carry* | GET + content | 200 (redirect to publications page), authors + focus/findings read |
| 10 | davidhbailey.com/dhbpapers/deflated-sharpe.pdf | GET | 200; PDF text read (DSR/SR₀ definitions, MinTRL keywords) |
| 11 | SSRN 1821643 (Sharpe Ratio Efficient Frontier) | GET | 403 bot-block; title + abstract + venue confirmed from the SSRN listing's indexed metadata |
| 12 | SSRN 2585399 (Capacity of Trading Strategies) | GET + content | 403 on curl, **content extracted**: authors Bonelli/Landier/Simon/Thesmar, HEC FIN-2015-1089 |
| 13 | SSRN 3911635 (Market Impact Decay and Capacity) | GET + content | 403 on curl, **content extracted**: author Hector Chan, abstract read |
| 14 | SSRN 3229719 / AQR *Trading Costs* | GET | AQR page 200 (authors Frazzini/Israel/Moskowitz, Working Paper Aug 2018); SSRN copy 403 |
| 15 | AQR PDF *Trading Costs of Asset Pricing Anomalies* | GET + content | 200, IS/MI numbers and permanent/temporary split read |
| 16 | FoFI-2026-059 PDF (Cartea et al.) | GET + content | 200, author list + abstract + participation formula read |
| 17 | Moallemi & Yuan queue-value PDF | GET + content | 200, value function + calibration table read |
| 18 | SEC EMSAC maker-taker memo (2015) | GET + content | curl 403, **content extracted**: DTM memorandum, Rule 610 cap, fee-filing mechanics |
| 19 | AMS Notices 61(5) *Pseudo-Mathematics* | GET + content | curl 403, **content extracted**: four authors, MinBTL discussion, DOI 10.1090/noti1105 |
| 20 | DOI 10.1111/jofi.12230 (Malinova & Park 2015) | GET | 403 bot-block; publisher metadata (authors, JF 70(2):509–536, DOI) and the SEC-hosted companion material confirm existence |
| 21 | DOI 10.1111/jofi.12422 (Battalio, Corwin & Jennings 2016) | GET + content | publisher page 403; **SEC-hosted preprint content read** (authors, abstract, hypotheses) |
| 22 | DOI 10.3390/math14020346 (Zhivkov 2026) | GET | mdpi.com 403 bot-block; MDPI listing + RePEc record (Mathematics 14(2):346, author, abstract) confirm existence |
| 23 | DOI 10.1007/s42521-026-00213-3 (Pindza 2026) | GET + content | 200, author + abstract + synthetic-rate design read |
| 24 | Perold (1988) | GET | HBS faculty page 405 to automated fetch; citation string (JPM 14(3):4–9) confirmed from the HBS listing and a ProQuest record |
| 25 | sharperat.io *Do not deflate I* | content | page content read (simulation-based DSR critique) |

No reference above was constructed from memory without a fetch. Where a formula is quoted, it is quoted as it appears in the fetched artifact; where the artifact's own notation differs from v8's, the discrepancy is named (§4.6).

## 8. Open questions and suggested follow-ups (no work done here)

1. **Which MinTRL identity is authoritative?** (#378) The published closed form and the implemented power-based estimator differ (§4.6). Pick one per `method_version`, cross-check against analytic reference cases, and state that MinTRL is horizon evidence only.
2. **What is the minimum viable microstructure capture for #382?** On this evidence (Cont et al. for impact, Lokin & Yu for fill probability) top-of-book **event-sequenced** quotes plus observed fills dominate full-depth capture; a capture plan should be justified against those two papers rather than against "L2" as a label.
3. **Fee identity** (#385): should `VenueCostReceipt` carry venue, tier and effective date, and should `price_pnl_already_net_of_friction` become machine-verified rather than caller-declared? (Double-count risk, §5.6.)
4. **Funding attribution** (#385/#393): the durable separation is transaction P&L / funding carry / explicit fees / operating costs / margin-liquidation events (§3.2, §3.4), with funding populated only from settlement records.
5. **Multiplicity binding** (#393): DSR's N and V are self-reported (§4.2, §4.5). If they are to be used at all, they must be produced by v8's own multiplicity ledger, not typed in by a worker.

Boundary statement: this memo is navigation, not evidence. Per the V8 Constitution's authority hierarchy it cannot be a completion receipt for any economic claim; nothing in it may be promoted out of `NO_ECONOMIC_CLAIM`, and no coefficient quoted here may enter a runtime path.
