# Survival, Multi-State Candidate Lifecycles, and Temporal Point Processes

## Scope, source integrity, and claim boundary

This chapter reviews list items 16–29. The list contains fourteen numbered
entries but only **thirteen distinct works**: item 28 is the HTML rendering of
item 24, not another paper. Twelve distinct works were available as full PDFs
locally or from arXiv. Item 27 was available only through its official
OpenReview/NeurIPS page and search-indexed text because the PDF endpoint returned
an anti-bot challenge; its evidence is therefore explicitly limited to the
poster abstract and indexed manuscript excerpts. Item 20 was mislabeled in the
provided list as a “measurement error” paper. Its actual title is *Flexible
multi-state models for interval-censored data: specification, estimation, and an
application to ageing research*.

The reviewed literature supports statistical distinctions and data-contract
requirements. It does **not** establish that V8 has predictive edge, improves
execution, prevents losses, or earns money. Results from medicine, credit,
DeFi lending, and one futures order book are evidence about methods in their own
settings, not evidence about V8 economics. Every proposed transfer below is
labeled as a design implication to test, not as an empirical trading result.

### Source accounting

| Item | Distinct source and access | Evidence status |
|---|---|---|
| 16 | Spadea & Seneviratne, *From Risk to Rescue* ([arXiv:2604.14583](https://arxiv.org/abs/2604.14583)); full PDF | Preprint; simulation study in Aave v3, not V8 evidence |
| 17 | Konstantinov, Efremenko & Utkin, *Survival Analysis as Imprecise Classification with Trainable Kernels* ([arXiv:2506.10140](https://arxiv.org/abs/2506.10140)); full PDF | Preprint; single-event right-censored methods |
| 18 | Green et al., *FinSurvival* ([arXiv:2507.14160](https://arxiv.org/abs/2507.14160)); full PDF | Preprint; open DeFi benchmark with explicit limitations |
| 19 | Groha, Schmon & Gusev, *A General Framework for Survival Analysis and Multi-State Modelling* ([arXiv:2006.04893](https://arxiv.org/abs/2006.04893)); full PDF | Preprint; neural-ODE multi-state method |
| 20 | Machado & van den Hout, *Flexible multi-state models for interval-censored data* ([arXiv:1703.08090](https://arxiv.org/abs/1703.08090)); full PDF | Methodology preprint; list title corrected |
| 21 | Dempsey, *Exchangeable, Markov multi-state survival process* ([arXiv:1810.10598](https://arxiv.org/abs/1810.10598)); full PDF | Theoretical/methodological preprint |
| 22 | Zhong et al., *KANFormer for Predicting Fill Probabilities via Survival Analysis in Limit Order Books* ([arXiv:2512.05734](https://arxiv.org/abs/2512.05734)); full PDF | Preprint; single-instrument, privileged-feature execution study |
| 23 | Asanjarani, Liquet & Nazarathy, *Estimation of Semi-Markov Multi-state Models* ([arXiv:2005.14462](https://arxiv.org/abs/2005.14462)); full PDF | Methodological comparison with reproducible vignette |
| 24 | Rahman & Purushotham, *Pseudo value-based Deep Neural Networks for Multi-state Survival Analysis* ([arXiv:2207.05291](https://arxiv.org/abs/2207.05291)); full PDF | KDD DSHealth workshop paper |
| 25 | Lee & Lee, *A Behavioral Scorecard Model Using Survival Analysis* ([arXiv:2503.05023](https://arxiv.org/abs/2503.05023)); full PDF | Applied preprint; discrete monthly credit setting |
| 26 | Weibull et al., *A multi-state model incorporating estimation of excess hazards and multiple time scales* ([arXiv:2012.13926](https://arxiv.org/abs/2012.13926)); full PDF | Methodological/application preprint |
| 27 | Groha, Gusev & Schmon, *SurviVAEl: Variational Autoencoders for Clustering Time Series* ([OpenReview](https://openreview.net/forum?id=pREEF8_kWNT), [NeurIPS workshop page](https://neurips.cc/virtual/2022/60051)); official abstract and indexed excerpts only | 2022 workshop poster; no verified full-PDF result audit |
| 28 | Same work as item 24, exposed through ar5iv | Duplicate; no independent evidence |
| 29 | Zhou et al., *Advances in Temporal Point Processes: Bayesian, Neural, and LLM Approaches* ([arXiv:2501.14291](https://arxiv.org/abs/2501.14291)); full PDF, published in TMLR 06/2026 | Survey, not a new empirical model validation |

The canonical methodological cross-checks used below are Andersen and Keiding’s
event-history review, which defines multi-state models through transition
intensities and discusses observation patterns
([DOI](https://doi.org/10.1191/0962280202SM276ra)); the maintained `survival`
package competing-risk/multi-state tutorial, which makes Kaplan–Meier and
cumulative incidence special cases of Aalen–Johansen
([CRAN tutorial](https://stat.ethz.ch/CRAN/web/packages/survivalVignettes/vignettes/tutorial.html));
Leung, Elashoff and Afifi’s review of censoring assumptions
([DOI](https://doi.org/10.1146/annurev.publhealth.18.1.83)); and Brown et al.’s
time-rescaling diagnostic for point processes
([paper](https://sites.stat.columbia.edu/liam/teaching/neurostat-fall13/papers/brown-et-al/time-rescaling.pdf)).

## The formal distinctions V8 must preserve

### A lifecycle fact is not automatically a statistical endpoint

Let `CandidateEpisode` be a software object whose state changes are recorded by
an append-only transition log. The current software state can be a deterministic
projection of that log. This does not make the episode a Markov process, a
semi-Markov process, a competing-risk record, or a temporal point process.
Those are alternative statistical models imposed on a specified random
quantity and observation scheme.

For a single terminal event, define latent event time (T), censoring time
(C), observed time (Y=\min(T,C)), and event indicator
(\Delta=1\{T\leq C\}). The survival function and hazard are

\[
S(t\mid x)=P(T>t\mid x), \qquad
\lambda(t\mid x)=\lim_{h\downarrow0}\frac{P(t\leq T<t+h\mid T\geq t,x)}{h}.
\]

Calling a record “expired,” “not executed,” or “rejected” does not determine
whether it is an event, a competing cause, or censoring. That choice depends on
the estimand. If the question is time from `PENDING` to first trigger, expiry
before trigger may be a competing endpoint. If the question is time from order
submission to first fill under the observed order policy, a trader-requested
cancel may be a competing event; treating it as non-informative censoring is a
strong and often implausible assumption because cancel decisions depend on the
same order-book history that governs fill. Item 22 explicitly treats
cancellation or market-close expiry as censoring and assumes conditional
independence of fill and censoring given covariates; that is a model assumption,
not a general property of order data ([arXiv:2512.05734](https://arxiv.org/abs/2512.05734)).

### Competing risks require event causes, not a bag of binary labels

For first terminal time (T) and cause (J\in\{1,\ldots,K\}), the
cause-specific hazard is

\[
\lambda_k(t\mid H_{t-})=
\lim_{h\downarrow0}\frac{P(t\leq T<t+h,J=k\mid T\geq t,H_{t-})}{h},
\]

while the cumulative incidence is

\[
F_k(t)=P(T\leq t,J=k)=\int_0^t S(u-)\lambda_k(u)\,du.
\]

The cause-specific hazard and cumulative incidence answer different questions.
An increase in one cause-specific hazard can reduce the observed cumulative
incidence of another cause by removing episodes from its risk set. Separate
one-vs-rest survival fits are therefore not automatically a coherent joint
competing-risk model. The CRAN tutorial shows that the Aalen–Johansen estimate
is the general state-occupation estimator and reduces to cumulative incidence
for a competing-risk graph
([tutorial](https://stat.ethz.ch/CRAN/web/packages/survivalVignettes/vignettes/tutorial.html)).

V8 must consequently specify, per origin state and estimand, which endpoints
compete. `REJECTED`, `EXPIRED`, `INVALIDATED`, and `ACCEPTED` can compete as
first exits from `PENDING` only if each is mutually exclusive at the timestamp
resolution and the tie policy is predeclared. `ARCHIVED` is a retention action,
not a natural event cause. `CLOSED` is downstream of execution and is not in the
same risk set as a pre-trigger rejection. Mixing all terminal names into one
flat “candidate outcome” destroys the origin state and risk-set definition.

### Multi-state quantities are distinct

For state process (X(t)\in\mathcal S) and allowed edge (j\to k), three
objects must not be conflated:

1. transition intensity (\lambda_{jk}(t\mid H_{t-})), an instantaneous rate
   conditional on occupying (j);
2. transition probability
   (P_{jk}(s,t\mid H_s)=P(X(t)=k\mid X(s)=j,H_s));
3. state-occupation probability (\pi_k(t)=P(X(t)=k)), or its landmark/dynamic
   version conditional on history at (s).

Item 24 explicitly predicts transition probability, state-occupation
probability, and dynamic state-occupation probability as separate targets
([arXiv:2207.05291](https://arxiv.org/abs/2207.05291)). Item 19 solves
Kolmogorov forward equations to connect transition intensities and occupation
probabilities in a continuous-time model
([arXiv:2006.04893](https://arxiv.org/abs/2006.04893)). A score called
“probability of transition” is incomplete unless it names the origin state,
destination, conditioning history, prediction origin, horizon, and estimator.

### Markov, semi-Markov, history-dependent, and deterministic are different

A Markov assumption says that, conditional on current state (and any declared
current covariates/time), earlier trajectory history provides no additional
information about the future. A time-homogeneous continuous-time Markov chain
implies exponential, memoryless holding times. A semi-Markov process retains a
Markov embedded chain of visited states but permits non-exponential holding
times and makes transition risk depend on time since entry into the current
state. A general history-dependent process may depend on the full path. A
deterministic software transition validator is none of these by itself.

Item 23 makes a further distinction that V8 must preserve. Its “Approach I”
uses an embedded transition probability (p_{ij}) and a sojourn distribution
conditional on the next state (j). Its “Approach II” uses transition intensity
(\tilde\alpha_{ij}(u)), conditional only on still occupying (i) after sojourn
time (u). The sojourn hazard conditional on the destination and the
cause-specific transition intensity are not numerically identical; the paper
derives the transformation between them
([arXiv:2005.14462](https://arxiv.org/abs/2005.14462)). A field named merely
`transition_hazard` is therefore underspecified.

### Event time, observation time, and knowledge time are different clocks

At minimum, the data contract needs:

| Clock | Meaning | Why it cannot be collapsed |
|---|---|---|
| `event_time` | When the source event occurred according to the source | Defines physical ordering but may not have been observable then |
| `available_time` | Earliest time the payload was available to the system under the declared feed | Governs point-in-time feature admissibility |
| `ingested_time` | When this installation received/persisted the payload | Measures operational delay and replay differences |
| `knowledge_time` | The ledger time at which the system could legitimately act on the fact | Orders corrections and causal decision views |
| `decision_time` | When an Expert/risk/execution actor made a decision | Defines prediction origin and feature cut |
| `birth_time` and `episode_age` | Candidate origin and elapsed time since origin | Clock-forward survival scale |
| `state_entry_time` and `state_age` | Entry into current lifecycle state and sojourn duration | Clock-reset semi-Markov scale |
| `calendar_time` | Absolute time/regime/season | Allows time-inhomogeneous effects |
| `observation_start` | Start of valid risk-set observation | Required for delayed entry/left truncation |
| `label_horizon_end` | End of the predeclared outcome window | Defines right censoring and maturity |
| `label_available_time` | When all data required to compute the label became available | Prevents mature outcomes leaking backward |

Item 26 is a concrete demonstration that attained age, calendar time, and time
since diagnosis can enter different transition models and cannot be replaced by
one generic timestamp ([arXiv:2012.13926](https://arxiv.org/abs/2012.13926)).
Item 23 distinguishes absolute calendar time from reset sojourn time and notes
that its own comparison assumes time homogeneity. Item 29 carefully distinguishes
(H_{t_n}), history at the last event for the next-event density, from
(H_{t-}), history immediately before arbitrary time (t), for the conditional
intensity ([arXiv:2501.14291](https://arxiv.org/abs/2501.14291)). The exact
software clock names above are a V8 design inference, but the need not to collapse
their semantics follows directly from these different statistical objects and
from point-in-time decision validity.

## Paper-by-paper evidence, limitations, and safe V8 transfer

### 16. *From Risk to Rescue: An Agentic Survival Analysis Framework for Liquidation Prevention*

**What it does.** The paper builds an Aave v3 intervention framework around
separate XGBoost Cox models for event pairs such as borrow-to-liquidation and a
derived fixed-horizon “return period.” It adds a hand-specified temporal trend
score and searches simulated repay/deposit interventions. Evaluation uses
on-chain Aave/Polygon-derived records and a protocol simulator
([arXiv:2604.14583](https://arxiv.org/abs/2604.14583)).

**Reported evidence.** The source reports more than 21.8 million raw records,
90 engineered features, an 8,400-checkpoint pre-filter sample, and a final
4,882-profile high-risk cohort. Liquidation-ending samples deliberately select
the 300 shortest time-to-event cases per pair. Its simulator uses an expanding
effective liquidation threshold, inferred external wallet balances with a 1.5x
safety factor, dust filters, and six detection procedures. It reports simulator
health-factor correlation, liquidation anticipation, a zero simulated worsening
rate, and an 86.83% simulated liquidation reduction in the selected cohort.

**Limits.** These are paired replay outcomes under a constructed simulator, not
observed counterfactual outcomes. The dynamic liquidation boundary, wallet
inference, exclusions, gas assumptions, and intervention feasibility rules are
part of the result-generating mechanism. Selecting imminent liquidations is a
stress-test population, not a population estimate. “Accuracy 69.11%” is not
sufficiently defined to establish survival calibration. Although the paper says
it predicts several event types “simultaneously,” the underlying FinSurvival
tasks are index–outcome pairs; this is not shown to be a coherent joint
competing-risk likelihood. The result cannot validate V8 economics, Candidate
states, or an execution policy.

**Safe transfer.** Keep observed outcomes separate from simulated
counterfactual outcomes; store simulator/config/version with every
counterfactual; predeclare cohort filters; validate simulator state reconstruction
before intervention comparisons; never describe simulated rescue as observed
causal rescue. The paper motivates survival-conditioned monitoring, but does not
select a V8 model.

### 17. *Survival Analysis as Imprecise Classification with Trainable Kernels*

**What it does.** The paper discretizes time into intervals and represents a
right-censored instance by a set of possible probability distributions over
future intervals. Trainable Nadaraya–Watson/attention kernels aggregate these
imprecise labels. Three training variants (iSurvM, iSurvQ, iSurvJ) are compared
with the Beran estimator using C-index and integrated Brier score
([arXiv:2506.10140](https://arxiv.org/abs/2506.10140)).

**Reported evidence.** The authors report improvements over Beran on most real
datasets and synthetic settings, with iSurvJ variants strongest, especially as
dimension and censoring increase. They also show interval-valued survival bands
that contain Beran estimates in examples.

**Limits.** The comparison is primarily against one kernel estimator, not the
full survival-model landscape. Hyperparameter optimization materially affects
results; the neural version may not scale. The study covers small and
middle-dimensional data. Most importantly, the paper explicitly leaves
competing risks and time-varying covariates to future work. Its interval-valued
representation expresses epistemic imprecision under a modeling construction;
it is not automatically a calibrated prediction interval or a V8 reject option.

**Safe transfer.** It supports retaining censored episodes rather than dropping
them and separating an event-time distribution from a binary terminal label.
It does not justify treating `EXPIRED` or `INVALIDATED` as vague probabilities,
nor does it support multi-cause Candidate labels without a new competing-risk
extension and calibration study.

### 18. *FinSurvival: A Suite of Large Scale Survival Modeling Tasks from Finance*

**What it does.** FinSurvival converts public Aave Ethereum transactions into
16 index-event/outcome-event survival tasks (borrow, deposit, repay, withdraw,
liquidation), with temporal and user/market history features. It also creates
binary tasks by thresholding at a restricted mean survival time (RMST)
([arXiv:2507.14160](https://arxiv.org/abs/2507.14160)).

**Reported evidence.** The paper reports 7,698,497 task records, 114,861 users,
60 assets, 128 features, and mean censoring of 81.26%. Features are described as
history summaries “up to” the index transaction. The split is temporal (cutoff
1 July 2022) with end buffers. Classical XGBoost/AFT baselines outperform the
tested deep survival models on the survival tasks; logistic regression and
elastic net lead the RMST-thresholded classification tasks. Performance varies
substantially by event pair.

**Limits.** The paper explicitly states that the reported analysis does **not**
model competing risks, even though its pipeline could be extended to do so.
Pairwise tasks duplicate index events across different outcome definitions and
do not form one joint lifecycle. Classification drops records censored before
the RMST threshold, changing the target population. A single time cutoff plus
buffers does not by itself demonstrate purging of overlapping user/event
histories, account clustering, or availability-time feature lineage. Hand-built
features and protocol/user behavior are domain-specific. The paper’s broad
fairness/privacy statements about public blockchains are not needed for V8 and
should not be inherited.

**Safe transfer.** FinSurvival is strong evidence for keeping index event,
outcome cause, duration, censoring indicator, user/instrument grouping, and
temporal split metadata explicit. It also supplies a useful negative result:
scale does not make a deep model best, and survival and thresholded
classification can rank model families differently. It cannot validate a V8
Candidate graph or allow separate binary event-pair models to be called a
multi-state model.

### 19. *A General Framework for Survival Analysis and Multi-State Modelling*

**What it does.** SurvNODE models cause-specific transition intensities with
neural ordinary differential equations and solves Kolmogorov forward equations
for transition/state probabilities. A latent memory state is offered to relax a
plain Markov representation; a variational extension models individual
uncertainty and clustering
([arXiv:2006.04893](https://arxiv.org/abs/2006.04893)).

**Reported evidence.** The paper reports competitive results on standard
single-event, competing-risk, and simulated multi-state tasks, including
non-proportional and nonlinear settings. It evaluates discrimination and
calibration-oriented quantities and demonstrates trajectory clusters.

**Limits.** The paper’s “assumption free” wording should not be read literally.
It assumes a chosen state graph, likelihood/observation process, censoring
conditions, differentiable parameterization, optimization procedure, and data
generating relation stable enough to generalize. A learned hidden memory state
relaxes a finite observed-state Markov assumption; it does not make causal
history identifiable. Neural flexibility can trade interpretability and sample
efficiency for fit. Medical/synthetic benchmarks do not select this architecture
for V8.

**Safe transfer.** The key contribution for V8 is conceptual: when multiple
transient/absorbing states matter, estimate coherent transition or occupation
quantities instead of fitting disconnected terminal labels. Start with
Aalen–Johansen/Cox or simple semi-Markov baselines; SurvNODE belongs only in a
later complexity ablation.

### 20. *Flexible multi-state models for interval-censored data*

**What it does.** Machado and van den Hout fit continuous-time, first-order
Markov multi-state models when transitions among living states are observed only
at visits, while death times may be exact. Transition-specific Weibull,
Gompertz, or P-spline hazards are estimated by penalized likelihood; uncertainty
in transition probabilities is propagated by simulation
([arXiv:1703.08090](https://arxiv.org/abs/1703.08090)).

**Reported evidence.** The application uses an English ageing cohort with
intermittently observed cognitive states and known death times. The method
constructs likelihood contributions from transition probabilities between
observation times, rather than pretending visit times are exact transition
times. Flexible spline hazards improve time-dependency modeling.

**Limits.** The conditional first-order Markov assumption is explicit. The
observation schedule and covariate convention are part of the likelihood. Spline
smoothness is selected by AIC; extrapolation beyond observed time ranges still
depends on hazard shape. The source has nothing to do with measurement error
despite the list annotation.

**Safe transfer.** If V8 sees only bar-close evidence that a predicate changed
within a bar, it must not silently assign the transition to the close/open as an
exact event. Preserve a transition interval or a stated simulator convention.
This paper supports interval-censored transition handling; it does not prove the
Markov assumption for Candidate episodes.

### 21. *Exchangeable, Markov multi-state survival process*

**What it does.** Dempsey characterizes population-valued processes that are
Markov, invariant to unit relabeling, and consistent under subsampling. It
develops an approximate MCMC scheme for intermittently observed and censored
multi-state paths and applies it to cardiac allograft vasculopathy
([arXiv:1810.10598](https://arxiv.org/abs/1810.10598)).

**Reported evidence.** The theory clarifies how exchangeability and sample-size
consistency constrain a class of population processes. The application has 622
patients with yearly examinations and uses a composable Markov model to adjust
survival estimates for latent disease progression between appointments.

**Limits.** Exchangeability is not a synonym for IID, and its applicability to
V8 is doubtful without conditioning: Candidate episodes differ by instrument,
expert, regime, and concurrency. “Consistency under subsampling” in this theory
implies a lack-of-interference condition; market candidates may interact through
shared events, capacity, or deduplication. The method also assumes
time-homogeneous Markov dynamics and non-informative observation times given
observed history. Those assumptions are substantive, not defaults.

**Safe transfer.** The useful lesson is to state population invariances and
observation-process assumptions explicitly and test dependence. V8 must group
or cluster correlated episodes and must not use this paper to claim arbitrary
candidate relabeling or independence.

### 22. *KANFormer for Predicting Fill Probabilities via Survival Analysis in Limit Order Books*

**What it does.** KANFormer predicts limit-order time to first partial or full
fill. Cancellation or market close before fill is coded as right censoring. The
model combines LOB snapshots, action-type histories, participant-level behavior,
and queue position, and predicts a covariate-dependent Weibull survival curve
([arXiv:2512.05734](https://arxiv.org/abs/2512.05734)).

**Reported evidence.** The data cover front-month CAC 40 index futures over 300
days in 2016–2017, split chronologically into train/validation/test. Across 30
dataset realizations, the paper reports KANFormer RCLL 0.53, IBS 0.027,
integrated AUC 0.76, and C-index 0.72. The AUC/Brier integration window spans
20 horizons only up to the median event-time percentile, with an upper bound of
0.627 seconds. Ablation reports the largest discrimination loss when queue
position is removed.

**Limits.** The Weibull form is assumed for the output. The 30 runs are
warm-started from the first model, so they isolate dataset composition rather
than full training randomness. The paper covers one instrument, venue, period,
and sub-second horizon. It defines any partial fill as the event, so it does not
answer time to complete fill, fill fraction, adverse selection, cancellation
policy, or executable PnL. The authors explicitly note that the full participant
behavior features are not observable by a single market participant. Most
critically, cancel is likely related to fill risk; coding it as independent
censoring requires a conditional-independence argument and sensitivity tests.

**Safe transfer.** Separate `first_fill`, `partial_fill_update`, `full_fill`,
`cancel_request`, `cancel_ack`, and `expiry` events. Store queue information only
when it is genuinely available and calibrated. A fill-survival experiment must
compare observable-only and privileged-feature variants. This study reinforces,
rather than weakens, V8’s rule that passive/queue fill claims require sequenced
L2 plus a separately validated order/fill authority.

### 23. *Estimation of Semi-Markov Multi-state Models*

**What it does.** The paper compares two semi-Markov parameterizations: embedded
transition probabilities plus destination-conditional sojourn distributions,
and transition-specific intensities indexed by time since state entry. It derives
the exact relationship, likelihood implications, interpretations, and software
tradeoffs, with two real-data illustrations
([arXiv:2005.14462](https://arxiv.org/abs/2005.14462)).

**Reported evidence.** Transition-intensity parameterization can split the
likelihood into smaller two-state components when transitions have separate
parameters, enabling standard survival tools. The sojourn-time parameterization
can be more natural when waiting time conditional on destination is the object
of interest. The paper supplies reproducible R code/vignette.

**Limits.** The empirical examples illustrate interpretation rather than
establish universal predictive superiority. The main treatment is parametric and
time-homogeneous; the paper explicitly leaves calendar-time inhomogeneity for
future work. Splitting likelihoods is valid under the declared parameterization,
not permission to ignore dependence or competing risks.

**Safe transfer.** Candidate modeling must carry `state_entry_time` and
`state_age`. Any hazard field must declare whether it conditions on destination.
The cheapest test is not a neural model: compare a clock-forward baseline, a
clock-reset semi-Markov baseline, and a history-feature baseline on the same
folds and estimand.

### 24 and 28. *Pseudo value-based Deep Neural Networks for Multi-state Survival Analysis*

**What it does.** Item 24 proposes `msPseudo`, a feed-forward neural regressor
trained on jackknife pseudo-values for state occupation, dynamic occupation, and
transition probabilities. It selects ordinary Aalen–Johansen under a tested
Markov assumption and landmark Aalen–Johansen when that assumption is rejected.
Item 28 is exactly the same paper in HTML
([arXiv:2207.05291](https://arxiv.org/abs/2207.05291)).

**Reported evidence.** Experiments include four simulated Markov/non-Markov data
generators with 5,000 samples, METABRIC (1,975 patients), and EBMT (2,279
patients). Five runs of five-fold cross-validation evaluate integrated AUC and
Brier score. The paper reports better averaged performance than selected
multi-state baselines and robustness in induced/incremental 75% censoring tests.

**Limits.** This is a short workshop paper. Its pseudo-values inherit the
assumptions and errors of the selected estimator; testing the Markov property and
then choosing an estimator adds a data-dependent selection layer whose
uncertainty is not automatically represented. “Ground truth” for real data is a
pseudo-outcome, not an observed individual probability. Baseline covariates and
preselected horizons dominate the setup. Medical/simulated results do not
validate V8, and the duplicate item adds no evidence.

**Safe transfer.** It supports explicitly naming occupation, dynamic occupation,
and transition targets, testing Markov adequacy, and keeping simple
Aalen–Johansen/landmark baselines. It does not justify a neural scorer before the
state graph, risk sets, observation cuts, and censoring mechanism are stable.

### 25. *A Behavioral Scorecard Model Using Survival Analysis*

**What it does.** This applied paper expands monthly Freddie Mac loan histories
into landmark panels, estimates monthly default hazard with logistic regression,
and maps cumulative default probability to a scorecard
([arXiv:2503.05023](https://arxiv.org/abs/2503.05023)).

**Reported evidence.** Loans originated in 2018–2021 are divided into an
in-sample cohort through June 2021 and a later holdout. Fully exploding the
monthly panels would create roughly 504.6 million rows, so the study uses an
approximately 30.6-million-row weighted sample. It models static, time-varying,
duration, macroeconomic, and seasonal terms; it reports in-sample AUC 0.82 and
out-of-time AUC 0.70 after an offset adjustment.

**Limits.** Bin sizes and sampling weights are described as arbitrary and left
for future work. Repeated landmark rows from one loan are dependent; the paper
examines GEE but retains ordinary logistic regression after a working-correlation
comparison. Monthly discrete-time ties, rare-event separation, chosen spline
terms, score offsets, and a Youden-index cutoff are application decisions.
AUC does not establish probability calibration or intervention utility. The
paper’s scorecard scaling and courtesy-call threshold have no direct V8 meaning.

**Safe transfer.** Landmark rows must carry a prediction-origin identifier,
subject/episode group, sample weight, and horizon. Train/test splits must keep
overlapping landmarks and label intervals from leaking. Discrete-time hazard is
a cheap baseline when the data resolution warrants it, not a universal model.

### 26. *A multi-state model incorporating estimation of excess hazards and multiple time scales*

**What it does.** The paper combines relative survival and multi-state modeling
to partition expected population rates from excess rates, allowing transition
models to use attained age, calendar time, and time since diagnosis
([arXiv:2012.13926](https://arxiv.org/abs/2012.13926)).

**Reported evidence.** A Hodgkin lymphoma application estimates morbidity and
mortality state probabilities, differences across covariates, and proportions
attributed to excess versus expected rates. Flexible parametric hazards and
parametric bootstrap uncertainty are implemented in Stata.

**Limits.** The expected/excess partition requires external population tables
and exchangeability with the reference population after stratification. A causal
treatment interpretation needs further assumptions. The example only uses the
first occurrence of the intermediate disease and notes recurrent events as
future work. Multiple component models must each be checked for fit, and the
latent-time simulation has known interpretive debate.

**Safe transfer.** V8 should not import expected/excess hazard semantics. The
transferable point is only the multiple-time-scale contract and the requirement
to identify which scale drives each transition. Recurrent Candidate episodes
need explicit new episode/parent or recurrent-event semantics rather than
silently overwriting a prior episode.

### 27. *SurviVAEl: Variational Autoencoders for Clustering Time Series*

**What it does.** The official abstract describes a VAE-based multi-state
survival framework intended to quantify predictive uncertainty and cluster
patient trajectories; indexed excerpts indicate latent clusters are summarized
with nonparametric Aalen–Johansen occupation estimates
([OpenReview](https://openreview.net/forum?id=pREEF8_kWNT)).

**Reported evidence.** The accessible official record establishes the method’s
aim and workshop-poster status. It does not expose verified result tables on the
public page. There were zero public OpenReview replies at the time checked.

**Limits.** Because the full PDF could not be independently retrieved through
the verification wall, no numerical result, split, ablation, or limitation claim
should be imported into V8 from this review. A VAE latent cluster is not a
Candidate lifecycle state and need not correspond to a causal or operational
mechanism. Uncertainty in a generative latent representation is not automatically
calibrated event-time uncertainty.

**Safe transfer.** None beyond a low-priority research idea: after an auditable
state graph and simple estimators exist, trajectory clustering could be tested
for descriptive compression. It cannot define the state graph or replace
transition/event evidence.

### 29. *Advances in Temporal Point Processes: Bayesian, Neural, and LLM Approaches*

**What it does.** This 2026 TMLR survey defines unmarked and marked TPPs,
conditional density/intensity parameterizations, likelihood and Bayesian
inference, Hawkes/nonparametric/neural/diffusion/LLM families, benchmarks,
evaluation, applications, and open problems
([arXiv:2501.14291](https://arxiv.org/abs/2501.14291)).

**Core formal evidence.** For ordered events
(\mathcal T=((t_1,k_1),\ldots,(t_N,k_N))) in window ([0,T]), a marked
conditional intensity (\lambda^*(t,k\mid H_{t-})) characterizes expected event
counts by type given the strict past. The log-likelihood is

\[
\sum_{n=1}^{N}\log\lambda^*(t_n,k_n)
-\int_0^T\sum_{k=1}^{K}\lambda^*(u,k)\,du.
\]

The second term matters: learning only at event rows without the no-event
exposure/observation window is not a valid intensity likelihood. A multivariate
Hawkes process decomposes intensity into baseline plus history-triggered kernels,
but its zeros identify Granger non-causality within the model, not intervention
causality.

**Survey evidence.** The review distinguishes next-event time/mark prediction,
long-horizon sequence prediction, retrieval/reasoning tasks, and causal-structure
discovery. It recommends task-aligned metrics rather than likelihood alone and
documents inconsistent preprocessing/splits/metrics as a major field problem.
It also identifies interpretability, long-sequence scaling, continuous-time
integration, sampling efficiency, and multimodal alignment as unresolved.

**Limits.** This is a survey, so statements about model-family superiority
summarize heterogeneous studies rather than one controlled benchmark. Flexible
neural intensity is not causal explanation. Hawkes excitation can reflect a
shared omitted driver. LLM-based retrieval or reasoning over events is not a TPP
unless it defines a coherent stochastic event-time/mark model. The survey does
not show that Candidate transitions require a TPP.

**Safe transfer.** Use a marked TPP only for a predeclared asynchronous recurrent
event task, such as predicting the next admissible lifecycle transition time and
type from a valid history. Start with empirical/renewal/Poisson or simple Hawkes
baselines. Preserve complete observation windows, marks, strict ordering,
simultaneous-event policy, and exposure. Apply time-rescaling or simulation-based
goodness-of-fit diagnostics; Brown et al. show how correctly specified conditional
intensity transforms event times to a unit-rate Poisson process
([paper](https://sites.stat.columbia.edu/liam/teaching/neurostat-fall13/papers/brown-et-al/time-rescaling.pdf)).

## Candidate lifecycle contract: what should change and what should not

### Retain the deterministic control graph, add statistical views beside it

The lifecycle service should continue to validate legal transitions and replay
append-only events. Statistical materializations should be derived views, not a
replacement authority. One log may support several estimands:

| View | Origin/risk set | Endpoint | Censoring/competing causes | Unit |
|---|---|---|---|---|
| Setup completion | `DETECTED` | first `PENDING` | reject as competing; end-of-data censored | episode |
| Trigger process | `PENDING` | first `TRIGGERED` | expiry/invalidation/reject as distinct competing exits | episode or landmark |
| Admission process | `TRIGGERED` | `ACCEPTED` | rejection/invalidation as distinct exits | episode |
| Submission latency | `ACCEPTED` | `ORDER_SUBMITTED` | withdrawal/reject/cancel-plan as specified exits | order plan |
| First-fill process | live submitted order | first positive fill | cancel-ack/expiry as competing events or informative censoring sensitivity | order |
| Completion process | first fill or submission | full requested quantity filled | cancel/reprice/partial remainder explicitly modeled | order revision |
| Position closure | first fill/position open | flat position | forced/manual/risk exits as marks or causes | position |
| Recurrent expert events | observation window | next event time and mark | window end; feed outage separately | instrument–expert stream |

No single `label_status` can encode all these tasks. `MATURE`, `RIGHT_CENSORED`,
and `UNAVAILABLE` describe label observability; `EXPIRED`, `INVALIDATED`, and
`REJECTED` describe lifecycle causes; `NOT_EXECUTED` describes an aggregate fact
whose reason must remain available. Keep these as separate axes.

### Required transition payload

Every transition record should carry at least:

- immutable `candidate_id`, `transition_id`, `transition_sequence`, origin and
  destination states;
- `event_type`, `cause_code`, `actor_type`, `actor_version`, and evidence refs;
- `event_time`, optional interval bounds when exact time is unknown,
  `available_time`, `ingested_time`, and `knowledge_time`;
- `decision_time` for actor decisions, `state_entry_time`, `state_age`,
  `birth_time`, and `episode_age`;
- source/clock precision and simultaneous-event precedence policy;
- observation-window and feed-health status so a missing transition is not
  silently interpreted as survival;
- correction/supersession linkage without rewriting the original event.

For order transitions add order revision, requested/cumulative/remaining
quantity, first/partial/full-fill distinctions, venue event ID, exchange and
receive clocks, cancellation request/ack clocks, and explicit queue-data
provenance. Item 22 demonstrates that queue context can dominate a fill model,
while simultaneously showing why privileged queue/participant features must not
be assumed available ([arXiv:2512.05734](https://arxiv.org/abs/2512.05734)).

### Ties and simultaneous events

At bar resolution, trigger, target, stop, invalidation, and expiry can appear at
the same timestamp. A competing-risk data row requires one first cause, while
the evidence log may retain all source facts. Therefore:

1. retain every source event with its precision;
2. apply a predeclared, versioned precedence only in the derived estimand;
3. mark the result `interval_ambiguous` when source resolution cannot identify
   order;
4. rerun conclusions under plausible alternate precedence rules;
5. never choose the cause from later path or desired outcome.

Item 20 provides the relevant warning: interval-observed transitions require a
transition-probability likelihood or a declared approximation, not fabricated
exact times ([arXiv:1703.08090](https://arxiv.org/abs/1703.08090)).

### Reactivation and recurrence

A no-reactivation state-machine rule is defensible for audit identity, but it is
not a survival theorem. A renewed setup should create a new episode linked by
`parent_candidate_id`/cluster ID. Statistical analysis must then recognize
recurrent and dependent episodes. Item 21’s exchangeability/lack-of-interference
conditions generally should not be assumed, and item 26 explicitly notes that
first-event analysis omits recurrence. Report subject/instrument/event-cluster
groups, episode concurrency, and cluster-aware uncertainty/splits.

## Dataset and event-time contract

### Canonical tables and non-negotiable lineage

The evidence store should expose distinct immutable entities rather than one
wide modeling table:

1. raw source event with payload hash and all source/availability clocks;
2. feature/MarketState value with maximum input availability and build version;
3. Candidate episode birth record;
4. Candidate transition event;
5. order revision/event and fill event;
6. observation-window/feed-health record;
7. outcome view manifest specifying origin, state graph, endpoint causes,
   censoring rule, horizon, simulator if any, and label availability;
8. research materialization manifest with split, groups, weights, and code/data
   hashes.

The outcome view, not the raw lifecycle event, decides whether a fact is an
event, competing cause, or censoring for that estimand. An episode can be
right-censored for “time to close by horizon” while having an observed competing
cause for “first exit from pending.”

### Model-ready units must remain separate

**Episode-at-birth rows** answer questions conditional on birth evidence.
**Landmark rows** answer dynamic questions at a declared observation cut and can
produce many dependent rows per episode. **Transition rows** condition on an
origin state and state-entry/history cut. **Order rows** model order outcomes,
not Candidate quality. **Event-stream windows** support TPPs and must include
zero-event exposure intervals. Mixing these units in one sample without explicit
weights and groups creates target and dependence ambiguity.

Item 25 shows how landmark explosion creates (n(n+1)/2) rows and necessitates
sampling/weights and within-subject dependence controls
([arXiv:2503.05023](https://arxiv.org/abs/2503.05023)). Item 29 shows why a TPP
likelihood needs both event contributions and integrated intensity over the full
window ([arXiv:2501.14291](https://arxiv.org/abs/2501.14291)).

### Censoring and observation policy

Each outcome view must declare:

- event definition and whether first/partial/full event counts;
- time origin, entry time, horizon, and time scale;
- all competing causes and tie policy;
- right-, interval-, or left-censoring representation;
- conditions under which censoring is assumed independent given covariates;
- feed outage/dataset end/user action/order cancel distinctions;
- whether covariates are baseline, external time-varying, or internal
  post-origin variables;
- sensitivity analysis for informative censoring.

Leung et al. emphasize that censoring mechanisms are often unknown and common
methods require ignorability assumptions
([review](https://doi.org/10.1146/annurev.publhealth.18.1.83)). Thus “censored”
cannot be a neutral dumping ground. Data loss is not ordinary survival. Cancel
is not automatically independent censoring. Expiry may be a deterministic
administrative horizon or a substantive competing outcome depending on the
question.

### Split contract

Split by time first, then purge or embargo any row whose feature/history or
label interval crosses the fold boundary. Group all repeated landmarks and
linked/recurrent episodes as declared; report overlap and concurrency. Fit
preprocessing, pseudo-values, censoring weights, baselines, thresholds, and
calibration only on training-available labels. A label joins training only at
`label_available_time`, never merely because its event time lies in the past.

FinSurvival’s temporal split and buffers are a useful starting example, but its
pairwise tasks and high censoring do not demonstrate all these protections
([arXiv:2507.14160](https://arxiv.org/abs/2507.14160)). The TPP survey likewise
identifies inconsistent preprocessing and splits as a major reason published
comparisons fail to accumulate ([arXiv:2501.14291](https://arxiv.org/abs/2501.14291)).

## Contradictions and tensions that must remain visible

1. **Pairwise survival versus joint competing risks.** FinSurvival reports 16
   independent index–outcome tasks and explicitly omits competing risks; *Risk
   to Rescue* describes multi-event risk comparisons. V8 must not infer that
   comparing independently calibrated event-pair return periods yields coherent
   event probabilities.

2. **Censoring versus event cause.** KANFormer treats cancellation and market
   close as censoring under conditional independence. For an endogenous cancel
   policy, cancel is driven by fill-relevant history and can be informative or a
   competing event. Both encodings must be sensitivity-tested.

3. **First-order Markov convenience versus duration dependence.** Item 20 uses a
   first-order Markov likelihood for interval observations; item 23 explains why
   non-exponential sojourns need semi-Markov structure. Neither should be
   silently assumed. `state_age` must be available for the comparison.

4. **“Assumption-free” neural flexibility versus observation assumptions.**
   Items 17 and 19 relax parametric functional forms but still depend on
   censoring, state, time, architecture, and sampling assumptions. Flexible
   approximators do not remove identification requirements.

5. **Ordinary Aalen–Johansen efficiency versus landmark robustness.** Item 24
   uses a data-dependent Markov test to choose AJ or landmark AJ. Estimator
   selection uncertainty and low-power tests can affect pseudo-targets; compare
   both, not only the selected result.

6. **Exchangeability versus market dependence.** Item 21’s relabeling and
   subsampling consistency assumptions are mathematically useful but can fail
   when candidates share a market shock, instrument, Expert, capital constraint,
   or deduplication rule.

7. **Predictive fill evidence versus executable availability.** Item 22’s most
   useful inputs include queue position and participant-level behavior that the
   paper says a single agent cannot observe. Its reported sub-second calibration
   does not authorize V8 passive-fill claims.

8. **Latent clusters versus operational states.** Item 27’s VAE clusters can be
   descriptive trajectory groups; they cannot define legal Candidate states or
   transition authority.

9. **TPP Granger structure versus causal mechanism.** In a multivariate Hawkes
   model, a zero triggering kernel has a Granger interpretation under the model.
   A nonzero kernel can still arise from omitted common causes or nonstationarity;
   it is not an intervention effect.

10. **Ranking versus calibration versus utility.** C-index/AUC measure
    discrimination; Brier/log-likelihood address distributional accuracy under
    censoring assumptions; neither alone establishes a useful decision policy.
    Report both and add task-specific operational error, without translating
    them into economic claims.

## Cheap falsification experiments, ordered before complex modeling

### Contract and data falsifiers

1. **Clock inversion audit.** For every feature and transition, assert
   `event_time <= available_time <= knowledge_time <= decision_time` where that
   ordering is semantically required; record explicit exceptions such as delayed
   corrections instead of coercing them. Rebuild a sample after injecting random
   feed delays and verify no decision view changes before new availability.

2. **Replay determinism.** Shuffle ingestion order, replay by the declared
   `(knowledge_time, transition_sequence)` rule, and assert identical lifecycle
   projections/hashes. Then inject a correction and require append-only
   supersession rather than mutation.

3. **Interval-time falsifier.** Coarsen exact transition times to bars and compare
   (a) fabricated bar-close times, (b) interval-censored likelihood, and (c)
   optimistic/pessimistic tie precedence. If the conclusion moves materially,
   exact-time claims are unsupported.

4. **Missing-feed falsifier.** Delete a contiguous raw-data window. Outcomes must
   become `UNAVAILABLE`/interval-censored according to policy, not “survived,”
   `EXPIRED`, or negative.

5. **Population-unit audit.** Count one episode at birth, all landmark rows, all
   transitions, and all orders separately. Verify that repeated rows retain
   episode/instrument/event-cluster groups and weights.

### Survival and competing-risk falsifiers

6. **Binary-vs-competing-risk sanity check.** On the same `PENDING` cohort,
   compare separate Kaplan–Meier curves that censor alternate exits with an
   Aalen–Johansen cumulative-incidence estimate. Large differences falsify the
   claim that independent binary tasks approximate the lifecycle. The maintained
   survival tutorial provides the baseline estimator
   ([CRAN](https://stat.ethz.ch/CRAN/web/packages/survivalVignettes/vignettes/tutorial.html)).

7. **Event/censor recoding sensitivity.** For order fills, run at least three
   versions: cancel as censoring, cancel as a competing cause, and inverse-
   probability-of-censoring weighting from observable history. If fill curves or
   calibration move materially, independent censoring is not robust.

8. **Clock-forward versus clock-reset.** Fit the same simple transition model
   with episode age, state age, and both. If state-age terms materially improve
   held-out Brier/log score or remove residual duration structure, a Markov
   state-only model is falsified. Use item 23’s parameter distinction
   ([arXiv:2005.14462](https://arxiv.org/abs/2005.14462)).

9. **Markov adequacy check.** Within origin-state/landmark strata, add previous
   state, prior dwell time, transition count, or compact history features to a
   simple model. Held-out improvement or systematic residual differences reject
   the observed-state Markov sufficiency claim. Compare ordinary AJ with
   landmark AJ rather than relying on one low-power pretest.

10. **Proportional-hazards check.** Plot/test time-varying effects and compare
    Cox with a discrete-time or spline-hazard baseline. If effect signs or
    calibration vary by horizon, do not summarize with a single hazard ratio.

11. **Horizon sensitivity.** Predeclare several defensible horizons, report
    risk-set counts and calibration at each, and prevent post-result horizon
    selection. A model that “wins” only at a selected horizon fails a general
    lifecycle claim.

12. **Full-lifecycle versus executed-only ablation.** Fix model family, features,
    split, and mature counterfactual label policy. Compare training on all
    eligible candidates (with proper causes/censoring) against executed-only
    rows. Evaluate calibration and attribution on the same fixed prospective
    cohort. This directly tests whether full lifecycle adds statistical value;
    it does not assume the answer.

13. **Recurrent/dependence falsifier.** Compare naive uncertainty with cluster
    bootstrap or grouped folds by instrument/event cluster/parent episode. A
    material widening or rank reversal falsifies IID reporting.

### Fill and TPP falsifiers

14. **Observable-only fill ablation.** Reproduce a simple Cox/Weibull/discrete
    hazard baseline using only truly available order/book fields; then add queue
    and participant-wide features separately. If gains exist only with
    privileged fields, the deployable fill claim fails. Keep first partial and
    full fill as different endpoints.

15. **TPP necessity test.** Compare empirical mark frequencies plus a renewal or
    inhomogeneous Poisson baseline against a simple Hawkes/TPP on exactly the same
    windows. Require improvement in held-out likelihood *and* task-aligned
    time/mark calibration. If a static or renewal baseline matches it, reject the
    extra TPP complexity.

16. **No-event exposure test.** Train one intentionally wrong event-row-only
    classifier and one proper intensity likelihood with integrated exposure. The
    former should fail count/window calibration. This catches the common mistake
    of calling next-row classification a point-process model.

17. **Time-rescaling diagnostic.** Transform held-out event times through the
    fitted cumulative conditional intensity. Test exponential inter-arrivals and
    uniform transformed CDF values; inspect autocorrelation. Failure falsifies
    the claimed conditional intensity even if next-event MAE is good
    ([Brown et al.](https://sites.stat.columbia.edu/liam/teaching/neurostat-fall13/papers/brown-et-al/time-rescaling.pdf)).

18. **Simultaneous-mark sensitivity.** At the source timestamp resolution,
    compare deterministic mark precedence, compound marks, and small jitter only
    as a diagnostic. Material instability means the chosen continuous-time TPP
    representation is not identified by the data.

19. **History truncation ablation.** Compare last-event, bounded-window, and
    longer-history inputs. If apparent excitation vanishes after adding
    calendar/regime covariates, do not interpret the original Hawkes kernel as a
    mechanism.

20. **Counterfactual/observed separation test.** Change simulator config/hash
    while holding raw history fixed. Only counterfactual outcome records may
    change; observed fills and transitions must remain byte-identical. This
    prevents the intervention simulator pattern in item 16 from overwriting
    observed truth.

## Decision implications for V8

The defensible near-term decision is conservative:

- keep `Candidate != order != fill != outcome` as an audit invariant;
- keep every legal lifecycle transition, including non-executed terminal causes;
- define separate, versioned outcome views rather than one universal quality
  label;
- require explicit origin state, endpoint, cause, clock, horizon, observation
  window, and censoring rule for every survival target;
- add `state_entry_time/state_age` and interval-time support before testing
  semi-Markov or multi-state models;
- use Aalen–Johansen, simple cause-specific/discrete hazards, and renewal/Poisson
  baselines before neural multi-state or TPP models;
- treat cancellations, expiries, feed outages, and administrative archiving as
  different facts;
- keep counterfactual simulator results in a separate outcome authority;
- allow TPP work only for a declared recurrent asynchronous event task with
  complete exposure windows and goodness-of-fit diagnostics;
- retain every economic conclusion as **OPEN**. None of papers 16–29 certifies
  V8 returns, costs, fills, capacity, or robustness.

The literature’s strongest contribution is not a recommendation to add a neural
survival model. It is a specification discipline: decide the risk set, state
graph, time origin, event cause, censoring mechanism, observation process, and
clock semantics before fitting anything. If those are ambiguous, greater model
capacity only makes the ambiguity harder to audit.
