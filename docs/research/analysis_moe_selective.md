# Mixture-of-Experts, Routing, and Selective Prediction: Evidence Review for V8

## Scope, source audit, and evidentiary standard

This note covers list items 1–15 in the user-supplied reading list: eight listed entries on mixture-of-experts (MoE), routing, and conditional computation, and seven entries on selective prediction, reject options, and calibration. Item 6 is not a separate paper: it is the HTML rendering of item 2, arXiv:2507.11181. The assigned set therefore contains **15 list entries but 14 unique papers**. All 14 unique PDFs were accessible and downloaded; no assigned source is inaccessible. The exact arXiv metadata was also retrieved from the arXiv API on 2026-07-31.

The review distinguishes three evidence classes:

- **Direct empirical evidence:** an evaluated model, dataset, comparison, or ablation reported by the paper itself.
- **Direct theoretical evidence:** a theorem under explicit assumptions. A theorem about an idealized classification distribution is not treated as empirical evidence for markets.
- **Secondary synthesis:** a survey or tutorial's account of other papers. This is useful for taxonomy and failure-mode discovery, but it does not add an independent successful experiment.

The V8 conclusions below are deliberately narrow. None of these papers tests V8, proves that a Router creates trading edge, proves that Experts specialize by economic mechanism, or establishes that a `NO_TRADE` rule improves after-cost portfolio utility. Transfers from language/image classification to trading are marked as design inferences requiring V8-specific experiments.

## Executive findings for V8

1. **The literature supports conditional computation as a design family, not a V8 Router.** MoE can expand parameter capacity while activating a subset of modules, but the benefit is conditional on heterogeneous structure, routing quality, training dynamics, and systems constraints. For V8's planned two or three cheap deterministic Experts, there is no demonstrated compute bottleneck that warrants a learned Router before those Experts are run.

2. **Routing is not synonymous with semantic specialization.** The strongest counterexample in this set is Mixtral: expert assignment showed little topic-level differentiation across ArXiv, GitHub, PubMed, philosophy, and Wikipedia; it showed more syntactic and sequential locality. The later four-model analysis also concludes that it is premature to say MoE LLMs learn heterogeneous experts. V8 must measure specialization by counterfactual economic behavior, not by router entropy, balanced loads, expert IDs, or attractive visual clusters.

3. **The theoretical case for specialization is conditional, not universal.** Chen et al. prove and demonstrate specialization when the data contain a particular cluster structure, nonlinear CNN Experts can learn cluster-specific signals, and a specified optimization procedure is used. On ordinary CIFAR-10, MoE did not improve on the single models; on a constructed rotated task with strong cluster structure it did. This directly supports V8's current requirement to test Expert decomposition against an equal-information global baseline.

4. **Load balance is a systems objective, not evidence of useful expertise.** Balancing can prevent collapse and hardware bottlenecks, but it can also oppose natural task/expert alignment. With a small V8 Expert set, forcing uniform selection would be unjustified unless a binding capacity constraint is first demonstrated.

5. **`NO_TRADE` should be formalized as a selective decision with an explicit objective.** Cost-based rejection, maximum coverage under a risk ceiling, and minimum risk under a coverage floor share a Bayes-optimal ordering in the idealized theory, but they encode different operating choices. V8 should predeclare the economic loss of a false trade, the opportunity cost of abstention, or a target coverage/risk constraint rather than treating “confidence above threshold” as self-justifying.

6. **Ranking quality matters more than probability calibration for a fixed-coverage gate, but calibration still matters for guarantees.** Franc et al. show that a proper uncertainty score need only preserve conditional-risk ordering to construct an optimal selector. Feng et al. find that the classifier's own maximum softmax score outperforms separate selection heads on their image tasks. Yet Franc et al. also show learned loss-ranking scores can beat native margins or maximum class probability, especially for SVMs. V8 therefore needs a paired comparison, not a doctrinal choice between “native score” and “learned Scorer.”

7. **Conformal guarantees are not automatically available under market drift.** The conformal paper derives singleton-error guarantees under exchangeability and carefully distinguishes online from offline inductive settings. Serial dependence, adaptive retraining, nonstationarity, asset selection, and transaction-cost labels can violate or complicate those assumptions. Any V8 conformal overlay must state the precise exchangeability or weighted/block-conformal argument; otherwise it is a diagnostic, not a distribution-free guarantee.

8. **The two time-series papers answer different questions.** Inácio et al. learn an ex-ante rank of forecasting difficulty and use it for deployment-time rejection. Fu et al. mask uncertain/anomalous timesteps during model training to reduce overfitting; it is not a live abstention mechanism. Fu et al. explicitly warn that masking may compromise extreme-event prediction, a material risk for financial systems.

9. **Current V8 baseline decisions remain defensible and are strengthened by this review.** Run the small deterministic self-gating Expert set, log every evaluation and Candidate, and defer Router and learned Scorer. Admit a Router only if it preserves near-perfect valuable-Candidate recall while producing a binding operational gain. Admit a Scorer or `NO_TRADE` gate only at matched coverage and only on repeated chronological OOS after-cost utility, calibration, and stability evidence.

## Paper-by-paper analysis

### 1. Mu and Lin — comprehensive MoE survey (arXiv:2503.07137)

**Source and evidence type.** Siyuan Mu and Sen Lin, *A Comprehensive Survey of Mixture-of-Experts: Algorithms, Theory, and Applications* (first posted 2025; reviewed version v4 dated 2026). [arXiv abstract](https://arxiv.org/abs/2503.07137). This is a broad survey, not a new routing experiment.

**What the paper contributes.** The paper organizes MoE around gating functions, Expert networks, routing, training strategy, and system design, then surveys continual, meta-, multi-task, reinforcement, and federated learning applications. It usefully separates architectural capacity from sparse activation and catalogs recurring problems: unstable training, expert-load imbalance, possible collapse, communication and memory overhead, heuristic Expert-count choices, and weak theory for modern deep MoE routing.

**Evidence relevant to V8.** The survey supports treating `Router`, `Expert`, training, and systems scheduling as separate design problems. It also supports monitoring over-reliance on a few Experts and treating dynamic capacity as a possible experiment. Most importantly, its future-work section does not portray the number of Experts, degree of specialization, or routing policy as solved choices. It calls for adaptive load balancing, dynamic capacity, principled Expert-count selection, and stronger interpretability/theory.

**Limitations and non-transfer.** The paper is predominantly a secondary catalog and does not describe a systematic-review search protocol that would let a reader estimate publication-selection bias. Its examples are dominated by large neural models where Expert-parallel communication and parameter activation are primary constraints. V8's initial Experts are small executable hypotheses, not interchangeable FFN blocks; the survey cannot justify a learned V8 Router or a specific top-k rule. Its broad statements that MoE improves efficiency/performance inherit the conditions and baselines of cited studies.

**V8 use.** Use it as a taxonomy and risk checklist. Do not count it as independent evidence that V8 should implement MoE. It supports logging per-Expert load, overlap, routing stability, failure-to-route, and compute/latency, but V8 should not add balancing loss or dynamic capacity until a measurable constraint exists.

### 2. Zhang et al. — MoE in LLMs review (arXiv:2507.11181)

**Source and evidence type.** Danyang Zhang, Junhao Song, Ziqian Bi, Xinyuan Song, Yingfang Yuan, Tianyang Wang, Joe Yeong, and Junfeng Hao, *Mixture of Experts in Large Language Models* (2025). [arXiv abstract](https://arxiv.org/abs/2507.11181). Survey/review.

**What the paper contributes.** It reviews sparse gating, hierarchical MoE, expert routing, multimodal/multitask use, deployment, calibration, and aggregation. It emphasizes that model capacity can be decoupled from active inference parameters, but also identifies expert diversity, reliable calibration, stable routing, and inference aggregation as unresolved practical requirements. The review discusses irregular memory access, cross-device communication, batching instability, hardware under-utilization, and reproducibility costs that raw active-parameter counts do not capture.

**Evidence relevant to V8.** The useful V8 lesson is architectural separation: a gating mechanism can save computation yet still reduce model quality through bad assignments, and sparse activation creates its own operational state. A Router should therefore be assessed on both exclusion quality and operational benefit. The paper's emphasis on calibration and aggregation also argues against interpreting router scores as Candidate-quality probabilities without a separate calibration test.

**Limitations and non-transfer.** This paper synthesizes LLM work and offers no V8-like economic evaluation. Parameter count and token routing are not analogous to after-cost trade selection in a way that preserves the reported LLM benefits. Some claimed industrial examples are difficult to audit because training data, routing details, or model recipes are not public. The review is not an independent replication of those systems.

**V8 use.** Keep Router score, Expert output, Candidate evidence, and Scorer output as distinct logged fields. A learned gate must not silently become the economic quality score.

### 3. Chen et al. — theory of MoE specialization (arXiv:2208.02813)

**Source and evidence type.** Zixiang Chen, Yihe Deng, Yue Wu, Quanquan Gu, and Yuanzhi Li, *Towards Understanding Mixture of Experts in Deep Learning* (2022). [arXiv abstract](https://arxiv.org/abs/2208.02813). Direct theory plus synthetic, image, and language experiments.

**Method and direct evidence.** The paper constructs a binary classification distribution containing cluster-center patches, cluster-specific label-signal patches, feature-noise patches, and Gaussian noise. Under this distribution:

- Theorem 4.1 gives a negative result: when feature signal and feature noise have the same strength distribution, a single two-layer CNN, regardless of activation function or width, cannot exceed 87.5% test accuracy.
- Theorem 4.2, under detailed sample-size, initialization, width, learning-rate, and optimization conditions, shows a sparsely gated nonlinear MoE can approach 100% accuracy. The proof describes an exploration stage in which Experts specialize according to initialization, then a router-learning stage in which cluster-center features route observations to the corresponding Expert group.
- In the principal synthetic settings, nonlinear MoE obtained 99.46% ± 0.55 and 98.09% ± 1.27 accuracy, with dispatch entropy near zero; linear MoE obtained 92.99% ± 2.11 and 88.48% ± 1.96 with much higher dispatch entropy. Single nonlinear models obtained 79.48% and 72.29%.
- On standard CIFAR-10, MoE and single-model accuracy were essentially equal or MoE slightly worse: for example ResNet18 95.51% ± 0.31 versus MoE 95.32% ± 0.68. On constructed CIFAR-10-Rotate, where the task has a stronger latent cluster structure, MoE improved ResNet18 from 88.23% ± 0.96 to 92.60% ± 2.01 and likewise improved the smaller backbones.
- A multilingual sentiment experiment improved accuracy only modestly, from 74.13% to 76.22%, while the router largely partitioned examples by language.

**Interpretation.** This paper provides the clearest evidence in the set that MoE advantage depends on exploitable heterogeneity and appropriate Expert nonlinearity. It also shows that representational capacity alone is insufficient: a mixture of linear Experts could represent the synthetic target but failed to recover the intended clusters as effectively during training.

**Limitations.** The theorem applies to a highly structured orthogonal patch model, two-layer CNN Experts, normalized gradient descent, specific routing noise/early stopping, and asymptotic parameter conditions. It is not a general theorem that MoE discovers real economic regimes. The real-data experiments are small relative to contemporary LLMs and the rotated task is deliberately engineered to contain clustering. Dispatch entropy near zero demonstrates concentrated assignment, not economic correctness. No transaction costs, temporal dependence, distribution shift, or selective trading decision is studied.

**V8 use.** Treat “Experts beat global model” as an empirical hypothesis. Before learning a Router, test whether the proposed behavior habitats are separable using decision-time variables and whether each Expert has incremental conditional utility. Include an Expert-swap test: on the Router-assigned subset, compare the assigned Expert with every other Expert and with the global baseline. A low-entropy routing distribution without this counterfactual advantage fails to establish specialization.

### 4. Lo et al. — post-hoc analysis of four MoE LLMs (arXiv:2406.18219)

**Source and evidence type.** Ka Man Lo, Zeyu Huang, Zihan Qiu, Zili Wang, and Jie Fu, *A Closer Look into Mixture-of-Experts in Large Language Models* (first posted 2024; v3 2025). [arXiv abstract](https://arxiv.org/abs/2406.18219). Direct observational analysis plus a limited architecture experiment.

**Method and direct evidence.** The authors analyze Mixtral 8x7B, Mixtral 8x22B, DeepSeekMoE, and Grok-1 using parameter cosine similarity, output similarity/norms, gate embeddings, and layer position. They report:

- correlations between gate embeddings and Expert activation matrices, motivating a view of individual FFN neurons as finer-grained Experts;
- gate choices that often favor Experts with larger output norms in Mixtral and DeepSeekMoE;
- Expert parameter/output similarity generally decreases in deeper layers, then increases in the final layer;
- Mixtral Experts are more mutually similar than the from-scratch DeepSeek/Grok Experts, leading to a stated conjecture—not a demonstrated fact—that Mixtral may have used an upcycling-like initialization;
- six 24-layer, 3.6B-parameter models trained on roughly 120B tokens, where replacing one MoE layer with a dense layer generally hurt more when the replacement occurred later, except that the final-layer replacement slightly improved average results. This supports their layer-dependent allocation hypothesis only at that tested scale and recipe.

**Interpretation.** The paper undermines a naive modularity story. Parameter diversity, behavioral diversity, routing choices, and human-interpretable specialization are different quantities. It closes by saying it is premature to conclude whether current MoE systems genuinely learn heterogeneous Experts.

**Limitations.** The authors list incomplete coverage of routing strategies and architecture variants, reliance mainly on cosine similarity, and limited analysis after fine-tuning. Observations are correlational. Larger output norm may correlate with gate choice without being the correct objective for trade utility. The layer experiment does not isolate all possible changes and is far removed from V8's non-layered Expert architecture.

**V8 use.** Do not define specialization from parameter distance or selection frequency. Use outcome-conditioned, counterfactual specialization measures. If V8 ever learns Expert representations jointly, compare from-scratch versus shared/upcycled initialization and record whether shared initialization produces redundant Experts.

### 5. Cai et al. — LLM MoE survey (arXiv:2407.06204)

**Source and evidence type.** Weilin Cai, Juyong Jiang, Fan Wang, Jing Tang, Sunghun Kim, and Jiayi Huang, *A Survey on Mixture of Experts in Large Language Models* (first posted 2024; v3 2025). [arXiv abstract](https://arxiv.org/abs/2407.06204). Survey and taxonomy.

**What the paper contributes.** This survey distinguishes dense, token-choice, Expert-choice, non-trainable, and soft/merging gates; Expert architecture/count/size/frequency; shared Experts; dense-to-sparse and sparse-to-dense training; and system-level compute, communication, and storage. It documents several important tensions:

- token-choice routing usually needs auxiliary balancing losses, but balancing importance does not guarantee equal token counts;
- capacity limits can drop tokens and introduce position bias (including “drop-towards-the-end”);
- routing may specialize early and largely by token identity rather than context;
- balancing loss can conflict with task-specific allocation in multi-task settings;
- top-k, Expert-choice, soft routing, and fixed/non-trainable routing make different quality–stability–systems trade-offs.

**Limitations.** It is a wide secondary survey with heterogeneous benchmarks and rapidly changing systems. Reported hyperparameters are not evidence that the same coefficients or gate families work outside LLM training. “Industry predominant” is an adoption statement, not an optimality result. No economic or temporal decision problem is evaluated.

**V8 use.** If routing is tested, separate token/candidate choice from Expert-capacity scheduling. Do not drop Candidates silently when a capacity limit is hit; log them as explicit `REJECTED`/`SUPPRESSED` events with reason. Compare fixed habitat routing with learned routing rather than assuming learning is superior.

### 6. Duplicate HTML entry for Zhang et al. (arXiv:2507.11181v1)

**Source status.** *Mixture of Experts in Large Language Models (HTML version)* is the HTML representation of item 2, not another paper. [arXiv HTML](https://arxiv.org/html/2507.11181v1). It has the same title, authors, and underlying work as item 2; v1 versus the reviewed PDF's v2 may differ editorially.

**Evidence treatment.** Count once. The HTML page can improve accessibility and section-level linking but contributes no independent experiment, theory, or replication. Any bibliography or “number of papers read” statement should report 15 assigned entries, 14 unique papers.

### 7. Jiang et al. — Mixtral 8x7B technical report (arXiv:2401.04088)

**Source and evidence type.** Albert Q. Jiang et al., *Mixtral of Experts* (2024). [arXiv abstract](https://arxiv.org/abs/2401.04088). Direct model report with benchmark and routing analysis.

**Method and direct evidence.** Mixtral replaces every transformer FFN sub-block with eight SwiGLU Experts and uses a linear router with softmax over the top two logits for each token. Each token accesses 13B active parameters from a model with roughly 47B sparse parameters. In the authors' evaluation pipeline, Mixtral matched or exceeded Llama 2 70B on most reported benchmarks while using fewer active parameters: MMLU 70.6% versus 69.9%, MBPP 60.7% versus 49.8%, MATH 28.4% versus 13.8%, and GSM8K 74.4% versus 69.6%. The report explicitly notes that active parameter count omits memory cost, hardware utilization, routing overhead, and increased memory loads; sparse MoE is especially suited to batched workloads.

The routing analysis is more important for V8 than the headline benchmarks. Expert-selection proportions across ArXiv, GitHub, PubMed Abstracts, PhilPapers, StackExchange, Gutenberg, and Wikipedia were broadly similar. The authors observed more syntactic behavior and high consecutive-token locality in middle/later layers. For first-choice routing, same-Expert repetition was about 24–28% in layer 15 versus a 12.5% random reference; considering either of two choices, repetition was roughly 62–67% versus a roughly 46% random reference. They conclude selection aligns more with syntax than domain in the shown examples.

**Limitations.** This is a technical report from the model builder, not a controlled MoE-versus-dense experiment matched on training data, total parameters, wall-clock budget, and memory. Training data/computation details are incomplete. Many benchmark comparisons differ in model family and pretraining. The routing analysis is described as small, examines selected layers and datasets, and does not connect routing patterns causally to benchmark gains. LLM token-routing efficiency does not imply Candidate-routing value.

**V8 use.** Preserve the current all-cheap-Experts baseline. If learned routing is introduced, test semantic/economic alignment directly: assigned Expert identity should predict mechanism/habitat and incremental net utility after controlling for common state. Also measure burst/locality effects because correlated sequential assignments could overload a route or concentrate risk even if average loads look balanced.

### 8. Scardapane et al. — conditional-computation tutorial (arXiv:2403.07965)

**Source and evidence type.** Simone Scardapane, Alessandro Baiocchi, Alessio Devoto, Valerio Marsocci, Pasquale Minervini, and Jary Pomponi, *Conditional computation in neural networks: principles and research trends* (2024). [arXiv abstract](https://arxiv.org/abs/2403.07965). Tutorial/survey.

**What the paper contributes.** The paper provides a common formalism for dynamic input sparsity (token selection), width sparsity (MoE), and depth sparsity (early exits). It distinguishes hard/discrete routing, including Gumbel-softmax approximations, from soft routing/merging. Its synthesis highlights fixed accuracy–compute trade-offs, routing collapse, load imbalance, local rather than globally optimized routing, and the lack of mature specialization/generalization metrics.

The specialization section is unusually cautious: hard routing can facilitate specialization, but learned routing has sometimes underperformed fixed routing; many decisions can ignore context and become fixed early in training. The paper also notes that routing plots are useful for diagnosis but lack principled benchmarks and can become unmanageable with many modules.

**Limitations.** No new controlled MoE experiment establishes which conditional-computation family is best. Examples span vision, language, and networks with different objectives. FLOP reductions do not guarantee latency or economic utility. The tutorial expressly leaves global routing, elastic inference budgets, and specialization measurement open.

**V8 use.** This supports comparing a deterministic pre-router with a learned router and keeping `NO_TRADE`/early-exit behavior observable. For V8, “early exit” should mean an explicit reason-coded Expert evaluation, never a missing record. Fixed coverage and fixed compute budgets must be reported alongside quality.

### 9. Feng et al. — classifier-derived selective scores (arXiv:2206.09034)

**Source and evidence type.** Leo Feng, Mohamed Osama Ahmed, Hossein Hajimirsadeghi, and Amir Abdi, *Towards Better Selective Classification* (arXiv 2022; ICLR 2023). [arXiv abstract](https://arxiv.org/abs/2206.09034). Direct image-classification experiments.

**Method and direct evidence.** The paper compares SelectiveNet's selection head, Deep Gamblers' abstention logit, and Self-Adaptive Training's abstention logit with a simple classifier-derived score: maximum class softmax probability (“Softmax Response,” SR). It argues that the specialist architectures improve the underlying classifier but their separate selection mechanisms add another generalization failure point. Their procedure discards the external selection output, ranks cases by SR, and chooses a threshold on validation data for target coverage. They also add entropy-minimization regularization during training.

On ImageNet100, replacing the original mechanism with SR reduced selective error across most coverages. Examples include SelectiveNet at 80% coverage, 6.00% to 4.47%; Self-Adaptive Training, 5.20% to 4.46%; and at 60% coverage, SAT 1.72% to 1.37%. At very low coverage SelectiveNet itself failed dramatically, whereas SAT remained usable. Across ImageNet subsets with 25–175 classes, SAT plus entropy minimization and SR improved reported error at 30%, 50%, and 70% coverage; the paper reports relative gains as high as 80–85% in selected comparisons. Experiments include CIFAR-10, ImageNet/ImageNet100 subsets, StanfordCars, and Food101.

**Limitations.** This is classification under mostly IID image benchmarks, with threshold calibration assuming validation and test come from the same distribution. The authors explicitly acknowledge that OOD test data can invalidate target coverage, and that selective classification can magnify class/group disparities. SR need not be probabilistically calibrated; for fixed coverage it mainly needs a useful ordering. Entropy minimization can create overconfidence under shift. Reported relative improvements can look large when baseline error is small. None of the tasks contains transaction costs, asymmetric opportunity costs, serial dependence, or portfolio constraints.

**V8 use.** Include the Expert's native evidence/score as a strong no-extra-model baseline for Scorer experiments. Calibrate thresholds inside each chronological training fold only. Report achieved versus target coverage and risk by asset, direction, liquidity, volatility, and time regime so that aggregate improvements cannot hide selective exclusion.

### 10. Franc, Prusa, and Voracek — optimal reject strategies (arXiv:2101.12523)

**Source and evidence type.** Vojtech Franc, Daniel Prusa, and Vaclav Voracek, *Optimal strategies for reject option classifiers* (arXiv 2021; later JMLR 2023). [arXiv abstract](https://arxiv.org/abs/2101.12523). Direct theory plus benchmark experiments.

**Theory.** The paper formalizes three objectives:

- **cost-based:** minimize expected prediction loss plus a fixed rejection cost;
- **bounded-improvement:** maximize coverage subject to a selective-risk ceiling;
- **bounded-coverage:** minimize selective risk subject to a coverage floor.

For known data-generating distribution, the three yield the same class of optimal strategy: a Bayes classifier plus a randomized Bayes selection function. Accept below a conditional-risk threshold, reject above, and randomize on exact ties. A “proper uncertainty score” need not estimate the exact risk; it is sufficient that it preserve its ordering. The paper connects the entire risk–coverage curve to the bounded-coverage solutions and interprets AuRC as average selective risk under a uniformly selected target coverage.

The authors propose loss regression and SELE, a smooth pairwise ranking proxy for AuRC. They prove Fisher consistency for the proper-risk ordering. Their SELE loss is within a factor of two of empirical AuRC under the given setup and avoids explicit sorting in optimization.

**Direct empirical evidence.** On 11 classification datasets, SELE had average AuRC rank 1.36 on logistic regression versus 2.73 for maximum class probability and 1.09 on SVM versus 2.82 for margin. It significantly beat MCP and regression for logistic regression, and beat SVM margin/regression under the paper's Nemenyi comparisons, although individual datasets such as COVTYPE or PENDIGIT show learned scores are not uniformly best. Learned gains over a calibrated probabilistic classifier were more moderate than gains over a discriminative SVM margin. On 11 ordinal-regression datasets both learned scores beat the native margin baseline; a structured-output face-landmark task also improved.

**Limitations.** Bayes equivalence assumes the relevant distribution/conditional risk and loss are well defined. Fisher consistency is asymptotic and does not guarantee finite-sample, shifted, or dependent-market performance. AuRC weights coverage levels uniformly, which may not reflect V8 economics. The benchmark splits are not financial walk-forward tests. A scalar uncertainty ranking cannot by itself handle changing capital constraints, interactions among simultaneous Candidates, or execution costs unless those are part of the target loss.

**V8 use.** Define the V8 Scorer target as an estimate or ranking of **conditional economic loss**, not generic classification error. Compare native evidence, loss regression, a pairwise ranking loss, logistic, and shallow tree at the same Candidate universe and coverage. Use economic utility at predeclared coverage as primary; AuRC or a utility–coverage curve is a diagnostic.

### 11. Inácio et al. — selective time-series forecasting via meta-learning (arXiv:2606.23448)

**Source and evidence type.** Ricardo Inácio, Vitor Cerqueira, Marília Barandas, and Carlos Soares, *Selective Time Series Forecasting via Metalearning* (2026). [arXiv abstract](https://arxiv.org/abs/2606.23448). Direct rolling-origin and transfer experiments.

**Method.** The method predicts whether a forecast origin will be difficult before issuing the forecast. A CatBoost meta-model maps TSFEL descriptors of the recent lag window—trend, seasonality, temporal, spectral, and complexity features—to the within-series empirical percentile of historical forecast error. Percentile normalization aims to remove scale and support cross-series transfer. Forecast errors are obtained with rolling-origin evaluation. At inference, origins with predicted error percentile above a threshold are rejected. The design is separate from the forecaster and can operate zero-shot or after adapting on earlier target-domain origins.

**Direct evidence.** The study uses M1, M3, and Tourism monthly/quarterly series; NHITS and KAN forecasters; horizons 6 monthly or 4 quarterly; and source→target pairs M3→M1 and M1→Tourism. Grouped cross-validation keeps origins from a series together. In-domain Spearman correlations between predicted and realized error rank were 0.71–0.90. Zero-shot transfer degraded correlation and AUCO, while adaptation on 30% of target origins improved correlation and AUCO in all reported cases. For example, M3-monthly→M1-monthly with KAN improved Spearman from 0.628 zero-shot to 0.820 adapted and AUCO from 0.043 to 0.013; with NHITS, 0.571 to 0.812 and 0.045 to 0.013.

At the base level, adapted rejection reduced sMAPE monotonically across reported rejection fractions and generally had the smallest gap to an oracle. For Tourism monthly KAN, keep-all sMAPE 0.288 fell to 0.215 after rejecting 40%, while residual-scale reached 0.228 and prediction-interval width worsened to 0.325. Similar patterns were reported for NHITS and quarterly data. A series-level bootstrap found the method closer to oracle than all baselines except one NHITS/M1-quarterly residual-scale comparison (p=0.191).

**Limitations.** The authors explicitly state that the method depends on representative meta-training data, becomes less reliable for short domains, predicts relative risk rather than calibrated uncertainty, and supplies no formal guarantee. The datasets are low-frequency benchmark series, not high-frequency markets. Target adaptation uses labeled earlier origins and must be implemented causally. Forecasting error is not trade utility; a period can be hard to forecast yet still offer a robust directional or volatility trade, and vice versa. The baseline set is limited.

**V8 use.** A close V8 analogue is an ex-ante “candidate difficulty” meta-model built only from admissible state and trained on rolling outcomes. Test it only after deterministic Experts exist, against native evidence and residual/state-quality heuristics. Normalize targets within asset or declared peer group cautiously: percentile normalization improves transfer but discards absolute economic magnitude.

### 12. Fu et al. — selective learning for deep forecasting (arXiv:2510.25207)

**Source and evidence type.** Yisong Fu, Zezhi Shao, Chengqing Yu, Yujie Li, Zhulin An, Qi Wang, Yongjun Xu, and Fei Wang, *Selective Learning for Deep Time Series Forecasting* (NeurIPS 2025). [arXiv abstract](https://arxiv.org/abs/2510.25207). Direct training-method experiments plus a bounded variance-estimation result.

**Method.** This paper does **not** reject forecasts at deployment. It changes the training loss by masking time points deemed non-generalizable. An uncertainty mask estimates residual entropy from overlapping sliding-window predictions. An anomaly mask uses a lightweight model's estimated residual lower bound and masks points whose current residual is close to that bound. The model computes MSE only on the retained timesteps. A theorem bounds the difference between the historical residual-variance estimate and the variance under the current model under Lipschitz, bounded-residual, bounded-gradient, learning-rate, and update-gap assumptions.

**Direct evidence.** Across eight datasets (four ETT variants, Electricity, Exchange, Weather, ILI), four horizons, and six backbones, the authors report improvements in all 192 backbone/dataset/horizon cases, averaged over three runs. Mean MSE reductions include 37.4% for Informer, 15.6% for Crossformer, 8.4% for TimesNet, 6.5% for iTransformer, and 4.3% for TimeMixer. Ablations on ETTh1, ETTm2, Electricity, and Weather show the dual mask beating either single mask and equal-rate random masking. Zero-shot ETT transfer also improved.

**Crucial limitations.** The paper's appendix shows uncertainty masking can hurt a clean synthetic dataset: MSE increased from 0.0295 to 0.0475 at only 5% uncertainty masking and much more at larger ratios. The authors warn that the dual mask may remove rare extreme events and compromise extreme-event forecasting. Mask ratios are important tuned hyperparameters; on Exchange, a 90% anomaly mask reportedly performed best, which would be especially dangerous to copy into trading without tail-specific validation. The method is currently in-domain and not directly compatible with large foundation-model pretraining. The theorem bounds an estimator discrepancy under strong assumptions; it does not prove that masked observations are economically irrelevant.

**V8 use.** Do not cite this as evidence for `NO_TRADE`. It motivates a separate Expert-training robustness experiment only. Any V8 masking study must preserve a tail-event holdout and test crisis/large-move recall, downside utility, and calibration. Training points masked by the method must remain in the audit ledger; they cannot disappear from the Candidate universe.

### 13. Hallberg Szabadváry et al. — conformal reject guarantees (arXiv:2506.21802)

**Source and evidence type.** Johan Hallberg Szabadváry, Tuwe Löfström, Ulf Johansson, Cecilia Sönströd, Ernst Ahlberg, and Lars Carlsson, *Classification with Reject Option: Distribution-free Error Guarantees via Conformal Prediction* (2025). [arXiv abstract](https://arxiv.org/abs/2506.21802). Direct probability derivation plus numerical illustrations.

**Method and theorem.** In binary classification, a conformal predictor may output an empty set, a singleton, or both labels. The proposed rejector accepts only singleton sets. Empty sets are interpreted as novelty rejection and two-label sets as ambiguity rejection. For an online smoothed conformal predictor under exchangeability, if `E` is the event of an empty set, `S` a singleton, and the conformal significance is ε, Proposition 2 gives singleton error probability

`σ = (ε − P(E)) / P(S)`.

The identity follows because empty predictions are always conformal errors and double predictions never are. Empirically, `(nε − e)/s` estimates the singleton error rate. The paper corrects prior use of this formula in offline inductive conformal prediction: offline validity is training-conditional/PAC-like, depends on calibration size and a confidence parameter δ, and does not inherit the exact independent online error process without adjustment.

**Direct evidence.** Numerical illustrations cover full conformal prediction on QSAR biodegradation, offline inductive conformal prediction on Spambase, and batch inductive conformal prediction on a binarized California Housing task. They demonstrate that not all reject rates are achievable and the same reject rate can arise from different ε values with different error rates. In one full-conformal example, at most about 40% of observations yielded singleton predictions, so the minimum reject rate was about 60%. The authors also note that the estimator becomes noisy when accepted singleton counts are small.

**Limitations.** The guarantee requires the relevant exchangeability setup, correct online/offline formula, and sufficiently many singleton predictions. It concerns label-set coverage/error, not after-cost utility. The paper only directly treats binary classification; it suggests one-vs-all for multiclass. Full conformal prediction can be computationally impractical. Market sequences are nonstationary and dependent, and V8 selection/retraining may be adaptive. The theorem does not grant coverage after arbitrary asset filtering, threshold tuning on the test period, or data revisions.

**V8 use.** Conformal prediction is a possible safety overlay, not a default guarantee. If tested, define a cost-sensitive binary target such as `counterfactual_net_utility > 0` under the canonical simulator, fit/calibrate within chronological folds, and accept only a positive singleton. Report empty versus ambiguous rejection separately. Unless exchangeability or an appropriate time-series conformal method is justified, label results “empirical conformal diagnostic,” not “distribution-free guaranteed.”

### 14. Zhang, Wang, and Qiao — multicategory reject and refine (arXiv:1701.02265)

**Source and evidence type.** Chong Zhang, Wenbo Wang, and Xingye Qiao, *On Reject and Refine Options in Multicategory Classification* (2017). [arXiv abstract](https://arxiv.org/abs/1701.02265). Direct theory, simulations, and real-data studies.

**Method and evidence.** The paper develops angle-based margin classifiers with a bent loss. A reject outcome is used when all class margins are near zero. A novel refine outcome returns a subset of plausible classes and rules out implausible ones. Proposition 2 states the multiclass Chow/Bayes rule under a 0-d-1 loss: predict the most probable class only when its probability exceeds `1-d`, otherwise reject. The authors show their margin-derived reject region generally does not equal the multiclass Bayes region, but construct tight inner/outer bounds through slope parameters `a1` and `a2`.

Theoretical results cover excess-risk convergence with growing dimension and class count and faster rates under a low-noise assumption. Simulations and real-data experiments compare regular, reject-only, and reject-plus-refine classifiers. The reported value of refinement is high set coverage of the true class on deliberately ambiguous subsets. For example, in one four-class simulation the regular classifier's error on the refine subset was 45.89%, while the reject-and-refine method's mis-refinement rate was 1.581%; however, a set-valued prediction is easier than an exact label and must not be compared as if the outputs had equal informativeness.

**Limitations.** Results depend on margin loss, angle coding, tuning of reject cost and thresholds, and mostly IID classification. The refine set changes the action space and loss; its low mis-refinement rate is not directly comparable to top-1 error. The Bayes-region approximation is not exact in the multiclass case. No temporal, economic, or portfolio process is tested.

**V8 use.** The refine concept is a design analogy for retaining an ambiguous setup as `DETECTED` or `PENDING` with explicit plausible directions/mechanisms while forbidding order submission until a single trigger is satisfied. It does not justify executing a set-valued trade. Preserve the distinction among `NOT_APPLICABLE`, ambiguous evidence, and strong negative evidence rather than collapsing them into one `NO_TRADE` code.

### 15. Ramaswamy, Tewari, and Agarwal — consistent multiclass rejection (arXiv:1505.04137)

**Source and evidence type.** Harish G. Ramaswamy, Ambuj Tewari, and Shivani Agarwal, *Consistent Algorithms for Multiclass Classification with a Reject Option* (2015). [arXiv abstract](https://arxiv.org/abs/1505.04137). Direct theory and small benchmark experiments.

**Theory.** Under abstain loss with misclassification cost 1 and abstention cost α, the Bayes rule predicts the maximum-posterior class when that posterior is at least `1-α` and abstains otherwise. The paper shows that Crammer-Singer and one-versus-all hinge surrogates become consistent for α=1/2 when paired with rejection-aware prediction rules rather than ordinary argmax. It introduces a binary-encoded-prediction (BEP) convex surrogate operating in `ceil(log2 n)` dimensions instead of `n`, and derives excess-risk transform bounds. Generalizations cover α in `[0, 1/2]`.

**Direct empirical evidence.** Synthetic and UCI multiclass experiments compare Crammer-Singer, one-versus-all, and BEP at fixed reject proportions (0%, 20%, 40%). BEP is reported as comparable to one-versus-all and better than Crammer-Singer in the shown experiments, with shorter training because it learns logarithmically many functions. The empirical section is a proof of concept, not an exhaustive modern benchmark.

**Limitations.** The main surrogate results are restricted to α≤1/2; the paper explicitly leaves α>1/2 as future work. The cost ratio must be meaningful and stable. Consistency is asymptotic, and fixed rejection proportions in IID classification do not resolve market drift or utility. Binary encoding can impose an arbitrary class code; V8 Expert mechanisms are not merely class labels.

**V8 use.** A reject decision must be part of the trained/evaluated loss and prediction rule; adding a confidence threshold to an arbitrary score need not be consistent with the intended economic objective. V8 should express trade, wrong-direction trade, and `NO_TRADE` costs explicitly and test sensitivity over a predeclared economically plausible range.

## Cross-paper synthesis for V8 components

### Router

**What is supported.** Sparse gates can reduce active computation and increase capacity in large neural systems. Router collapse, uneven load, capacity overflow, early/frozen assignment, token-identity routing, and systems overhead are recurrent problems. Fixed routing can be competitive with or better than learned routing in some settings. Routing can discover meaningful clusters when the data and Experts have suitable structure.

**What is not supported.** No paper establishes that a Router improves an ensemble of two or three cheap deterministic trading Experts. No paper shows that a gate trained on predictive loss preserves rare, high-utility Candidates. No paper equates balanced Expert loads with useful specialization.

**V8 decision.** Preserve D-004: no Router in the initial baseline. A “pre-router” may be tested later as a separately versioned exclusion policy. It must produce an explicit `ExpertSkipped` record with score, threshold, reason, model version, and counterfactual Expert evaluation in the experiment so false exclusions can be measured.

### Experts

**What is supported.** MoE is most plausible when there is stable, exploitable heterogeneity; the Chen et al. CIFAR contrast shows little benefit without it and more benefit on a task engineered with a clear cluster structure. Nonlinear or expressive Experts and training dynamics matter. Post-hoc parameter/routing visualizations are insufficient to establish functional specialization.

**V8 decision.** An Expert remains a versioned executable hypothesis with its own habitat/setup/trigger/invalidation/expiry. Start with deterministic self-gating Experts and an equal-information global comparator. Require assignment-specific counterfactual advantage, not only different outputs.

### Candidate Scorer

**What is supported.** For selective decisions, cases should be ordered by conditional risk. A classifier-native score can be a powerful baseline; a learned loss-ranking score can add value when native scores rank risk poorly. External selection heads can fail separately from the predictor. Threshold calibration is part of the method, not a reporting afterthought.

**V8 decision.** Preserve D-007: no learned Scorer initially. The deterministic evidence score is the baseline. When tested, keep the Candidate universe fixed and compare scorers at exactly matched coverage. The target must incorporate canonical after-cost utility and, where relevant, drawdown/tail loss—not merely direction accuracy.

### `NO_TRADE`

**What is supported.** Abstention is an explicit action with a cost or coverage/risk constraint. Coverage and selective risk form a curve, not a single accuracy number. Rejection can be separated by cause (ambiguity versus novelty). Thresholds can fail under distribution shift, and low coverage can hide systematic exclusion.

**V8 decision.** `NO_TRADE` is not missing data, a dropped row, or an Expert that was never invoked. Represent at least: `NOT_APPLICABLE`, `INSUFFICIENT_EVIDENCE`, `AMBIGUOUS_DIRECTION`, `STATE_INVALID/DEGRADED`, `RISK_REJECTED`, `CAPACITY_REJECTED`, and `SCORER_REJECTED`. Each is a logged evaluation or lifecycle transition. Choose the operating point from a preregistered economic objective and measure realized coverage.

## Contradictions and tensions that V8 must preserve

| Tension | Evidence on one side | Evidence on the other side | V8 resolution |
|---|---|---|---|
| MoE induces specialization | Chen et al. prove/observe cluster specialization under a constructed distribution; multilingual routing aligns partly with language. | Mixtral finds little domain-level routing; Lo et al. say heterogeneous expertise remains unproven. | Specialization is a hypothesis. Require Expert-swap and conditional-utility tests. |
| Learned routing is preferable | MoE success commonly uses trainable gates. | Conditional-computation survey reports learned routing can be suboptimal to fixed routing; routing may ignore context/freeze early. | Compare all-Experts, fixed habitat, and learned router on the same events. |
| Balanced load is desirable | It prevents collapse and device bottlenecks. | Balancing can oppose task alignment; uniform traffic is not specialization. | Treat balance as a constraint/diagnostic, never a primary quality metric. |
| Native confidence is enough | Feng et al. show SR beats separate heads across their image benchmarks. | Franc et al. show learned SELE/loss scores can beat MCP/margins, especially for SVMs. | Native evidence is mandatory baseline; admit learned score only by paired OOS gain. |
| Confidence guarantees rejection quality | Conformal singleton predictions have a derived error rate under exchangeability. | Offline formulas need correction; achievable coverage may be limited; market shift violates naive assumptions. | State assumptions; otherwise report empirical coverage only. |
| Selective learning improves robustness | Fu et al. improve average forecasting error by masking uncertain/anomalous timesteps. | The same paper shows uncertainty masking harms clean data and warns about lost extreme-event capacity. | Tail-preservation and crisis recall are veto metrics. Do not equate training mask with `NO_TRADE`. |
| Transferable forecastability exists | Inácio et al. obtain useful zero-shot ranking and strong adapted results. | Zero-shot performance degrades; method has no probabilistic guarantee and relies on representative meta-data. | Use rolling domain-adapted challenger; fail closed when drift/feature-support tests breach. |
| One scalar operating objective suffices | Bayes theory unifies cost, risk ceiling, and coverage floor via the same conditional-risk order. | Practical thresholds and economic trade-offs differ; portfolio contention is not pointwise. | Scorer ranks Candidates; portfolio admission remains a separate risk/capacity action. |

## Concrete experiment program

### Experiment R1 — Is any Router justified?

**Question.** Can a cheap gate skip Expert evaluations without losing economically valuable Candidates?

**Arms.** (A) run all deterministic Experts; (B) fixed deterministic habitat pre-router; (C) logistic gate; (D) shallow tree gate. Do not add a deep Router until a simpler learned gate passes.

**Unit and split.** Decision clock × instrument, with grouped chronological folds, purge/embargo over Candidate outcome horizons, and an untouched final period. Fit thresholds and transforms inside each training fold. Preserve asset/session dependence in uncertainty estimates.

**Primary veto metric.** Recall of `valuable_candidate`, defined before the test as a Candidate whose canonical counterfactual net utility exceeds the preregistered economic threshold. Require the near-perfect recall level specified before seeing OOS results; report a one-sided lower confidence bound. A single high-severity missed tail Candidate may trigger qualitative review.

**Secondary metrics.** Expert evaluations avoided, wall-clock p50/p95/p99 latency, CPU/memory, valuable-Candidate precision, false exclusions by Expert/asset/regime, Candidate overlap, after-cost utility of the downstream fixed policy, load burstiness, and routing stability. “Balanced routing” and “fewer evaluations” cannot compensate for failure of the recall gate.

**Admission.** Only if C or D beats B and A on a binding operational constraint while meeting valuable-Candidate recall and not reducing paired OOS net utility. Otherwise retain A.

### Experiment E1 — Do Experts specialize economically?

**Question.** Does the proposed Expert decomposition add value beyond one global rule/model with the same decision-time information?

**Arms.** Each Expert on every eligible event; all other Experts counterfactually on that event; equal-information global baseline; scrambled habitat labels; pooled multi-task model if applicable.

**Metrics.** Conditional after-cost utility, Brier/log loss for predeclared Candidate labels, calibration, valuable-Candidate recall, and event count. Define a specialization matrix `U[i,j]`: utility of Expert `i` on events assigned to habitat `j`. Useful specialization requires a stable diagonal advantage versus off-diagonal Experts and global baseline, not merely different signal frequency. Report block-bootstrap intervals and multiplicity-adjusted family tests.

**Admission.** Retain an Expert only if its mechanism-specific diagonal advantage replicates. If Experts are redundant, merge/simplify. If no Expert beats global, reject H3 for that tested family.

### Experiment S1 — Does a Scorer improve selection at fixed coverage?

**Question.** Given a frozen Candidate universe, does a learned score improve economic selection?

**Arms.** Random ordering; deterministic evidence score; cost-only score; native model probability/response; logistic conditional-loss model; shallow tree; pairwise loss-ranking model inspired by SELE.

**Protocol.** Evaluate at fixed coverages such as 10/25/50/75/100% chosen in advance and at an economically chosen operating coverage. Every score sees identical Candidates and admissible features. Threshold calibration occurs only on rolling training/calibration windows.

**Primary outcome.** Paired difference in canonical after-cost utility at the operating coverage. Report utility–coverage and risk–coverage curves, but do not select the best coverage on frozen OOS. Secondary outcomes: calibration of conditional loss, expected calibration error with uncertainty, tail loss, turnover/cost, achieved coverage, and stability by asset/regime.

**Admission.** Repeated chronological OOS gain over deterministic evidence at matched coverage, with stable calibration and no unacceptable subgroup/tail degradation. “Fewer trades” alone is a fail.

### Experiment N1 — Choose the `NO_TRADE` objective

**Question.** Which explicit abstention formulation matches V8's economics?

**Arms.** Cost-based rule with preregistered abstention cost; bounded-risk rule maximizing coverage subject to a net-loss ceiling; bounded-coverage rule minimizing net loss above a minimum activity rate. Use the same score ordering where possible so the test isolates operating-point policy.

**Metrics.** Coverage, selective net loss/utility, opportunity cost of rejected profitable Candidates, avoided loss from rejected bad Candidates, turnover, tail drawdown contribution, and reason-code distribution. Report cost sensitivity across an economically defensible grid fixed before OOS.

**Admission.** The chosen rule must remain acceptable across the predeclared cost range and chronological replications. If the operating point is unstable, retain deterministic fail-closed rules and do not promote a learned `NO_TRADE` threshold.

### Experiment N2 — Forecastability meta-gate challenger

**Question.** Can ex-ante state structure rank Candidate outcome risk across assets/regimes?

**Design.** Adapt Inácio et al.: rolling-origin outcomes; PIT features only; within-asset or within-peer-group percentile target plus an absolute-utility target; grouped folds; zero-shot asset/regime evaluation followed by causal adaptation using only earlier target observations.

**Baselines.** State-quality rule, recent residual scale, prediction interval width if legitimately produced, deterministic evidence, random, and oracle (diagnostic only).

**Vetoes.** No use of realized horizon data in meta-features; no silent target-domain fine-tuning; no claim of calibrated uncertainty from rank correlation. Reject if zero-shot/adapted performance falls below deterministic evidence or if gains come only from suppressing high-volatility profitable events.

### Experiment N3 — Conformal diagnostic

**Question.** Can a conformal set-valued classifier yield useful, empirically stable positive singleton decisions?

**Design.** Define labels under the canonical simulator; separate calibration window; positive singleton → eligible, negative singleton → explicit negative, empty → novelty/invalid-state `NO_TRADE`, double → ambiguity `NO_TRADE`. Track online, offline, and batch-update formulas correctly.

**Metrics.** Empirical singleton error, acceptance coverage, empty/double proportions, interval/set size, calibration size, and error by temporal block. Compare with plain score threshold at matched coverage.

**Claim discipline.** Use “distribution-free” only if the precise exchangeability/validity theorem applies to the implemented sequence. Otherwise describe it as conformalized empirical selection.

### Experiment T1 — Selective training without tail erasure

**Question.** Does training-time timestep masking improve an Expert without destroying rare-event sensitivity?

**Arms.** No mask; random mask; uncertainty mask; anomaly mask; dual mask. Ratios fixed/tuned only in training folds.

**Metrics.** Average predictive loss, Candidate utility, calibration, extreme-move recall, worst-decile loss, crisis-window performance, and count/outcome of masked observations. Extreme-event recall and downside utility are veto metrics.

**Admission.** Average MSE or accuracy improvement is insufficient. Promote only if tail/crisis metrics remain within preregistered non-inferiority bounds and economic OOS utility improves.

## Required logging additions implied by the review

For each Expert evaluation or skip, retain `expert_id/version`, `market_state_id`, eligibility, native evidence score, Router score/version if any, invoked/skipped, skip reason, compute time, and counterfactual output in evaluation runs. For each Scorer/`NO_TRADE` decision, retain score, calibration-window identifier, threshold, target and achieved coverage, decision reason, and whether rejection is ambiguity, novelty/data quality, risk, or capacity. Never infer rejection from absence.

Add monitoring for per-Expert load and burstiness, assignment stability, Expert-output overlap, valuable-Candidate false negatives, per-group coverage, and drift in score/outcome ordering. These are diagnostics; component admission remains tied to paired OOS economic outcomes.

## References

1. Siyuan Mu and Sen Lin (2025). *A Comprehensive Survey of Mixture-of-Experts: Algorithms, Theory, and Applications*. [arXiv:2503.07137](https://arxiv.org/abs/2503.07137).
2. Danyang Zhang, Junhao Song, Ziqian Bi, Xinyuan Song, Yingfang Yuan, Tianyang Wang, Joe Yeong, and Junfeng Hao (2025). *Mixture of Experts in Large Language Models*. [arXiv:2507.11181](https://arxiv.org/abs/2507.11181).
3. Zixiang Chen, Yihe Deng, Yue Wu, Quanquan Gu, and Yuanzhi Li (2022). *Towards Understanding Mixture of Experts in Deep Learning*. [arXiv:2208.02813](https://arxiv.org/abs/2208.02813).
4. Ka Man Lo, Zeyu Huang, Zihan Qiu, Zili Wang, and Jie Fu (2024). *A Closer Look into Mixture-of-Experts in Large Language Models*. [arXiv:2406.18219](https://arxiv.org/abs/2406.18219).
5. Weilin Cai, Juyong Jiang, Fan Wang, Jing Tang, Sunghun Kim, and Jiayi Huang (2024). *A Survey on Mixture of Experts in Large Language Models*. [arXiv:2407.06204](https://arxiv.org/abs/2407.06204).
6. Duplicate rendering of reference 2. [arXiv HTML:2507.11181v1](https://arxiv.org/html/2507.11181v1).
7. Albert Q. Jiang et al. (2024). *Mixtral of Experts*. [arXiv:2401.04088](https://arxiv.org/abs/2401.04088).
8. Simone Scardapane, Alessandro Baiocchi, Alessio Devoto, Valerio Marsocci, Pasquale Minervini, and Jary Pomponi (2024). *Conditional computation in neural networks: principles and research trends*. [arXiv:2403.07965](https://arxiv.org/abs/2403.07965).
9. Leo Feng, Mohamed Osama Ahmed, Hossein Hajimirsadeghi, and Amir Abdi (2022/2023). *Towards Better Selective Classification*. [arXiv:2206.09034](https://arxiv.org/abs/2206.09034).
10. Vojtech Franc, Daniel Prusa, and Vaclav Voracek (2021; JMLR 2023). *Optimal strategies for reject option classifiers*. [arXiv:2101.12523](https://arxiv.org/abs/2101.12523).
11. Ricardo Inácio, Vitor Cerqueira, Marília Barandas, and Carlos Soares (2026). *Selective Time Series Forecasting via Metalearning*. [arXiv:2606.23448](https://arxiv.org/abs/2606.23448).
12. Yisong Fu, Zezhi Shao, Chengqing Yu, Yujie Li, Zhulin An, Qi Wang, Yongjun Xu, and Fei Wang (2025). *Selective Learning for Deep Time Series Forecasting*. [arXiv:2510.25207](https://arxiv.org/abs/2510.25207).
13. Johan Hallberg Szabadváry, Tuwe Löfström, Ulf Johansson, Cecilia Sönströd, Ernst Ahlberg, and Lars Carlsson (2025). *Classification with Reject Option: Distribution-free Error Guarantees via Conformal Prediction*. [arXiv:2506.21802](https://arxiv.org/abs/2506.21802).
14. Chong Zhang, Wenbo Wang, and Xingye Qiao (2017). *On Reject and Refine Options in Multicategory Classification*. [arXiv:1701.02265](https://arxiv.org/abs/1701.02265).
15. Harish G. Ramaswamy, Ambuj Tewari, and Shivani Agarwal (2015). *Consistent Algorithms for Multiclass Classification with a Reject Option*. [arXiv:1505.04137](https://arxiv.org/abs/1505.04137).

## Final decision implications

- **Router:** remain absent from the baseline. The literature makes routing failure modes concrete but does not satisfy V8 admission rule O-004.
- **Experts:** proceed with a small deterministic self-gating set and an equal-information global comparator. Treat economic specialization as unproven until Experiment E1.
- **Scorer:** remain absent initially. Native deterministic evidence is the mandatory baseline; learned conditional-loss ranking is a later challenger under S1.
- **`NO_TRADE`:** make it explicit, costed, calibrated, reason-coded, and audited. It is a decision, not a missing event. Choose cost/risk/coverage operating rules before OOS and measure actual coverage and rejected opportunity cost.
- **Conformal or meta-learning additions:** experiments only. Neither the distribution-free classification theorem nor low-frequency forecasting transfer results can be imported as a production guarantee for dependent, nonstationary trading data.
