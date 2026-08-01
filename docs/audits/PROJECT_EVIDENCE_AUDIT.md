# Project Evidence Audit — V6/V7/V8

**Audit scope.** This is a cross-version evidence inventory for the V8 research
program, not a V7 postmortem and not an economic claim. It reads the provisional
V8 architecture brief (`v8-0.2.html`) against the versioned V7 materials that
are present in this checkout. No V6 directory, file, commit reference, or other
V6 artifact was found in `/Users/hootie/src/v8` on 2026-07-31. Consequently,
there is no file-grounded V6 conclusion.

## Evidence standard

| Label | Meaning in this audit |
|---|---|
| **File-grounded fact** | Directly stated by, or mechanically represented in, a named local artifact. It is not automatically independently reproduced by this audit. |
| **Interpretation** | A conclusion drawn by comparing file-grounded facts. It must not be promoted as a measured result without the cited artifacts and a rerun. |
| **Unverified proposal** | Architecture or experiment described in V8 or a V7 target spec, with no admissible outcome evidence in the reviewed files. |

The strongest available economic-certification record is still
`v7/specs/simulation_authority_certification_v1.json`: `status: FAIL`,
`autopilot_permission: BLOCKED`, `economic_verdict: INVALID_NOT_CERTIFIED`, and
`profitability_claim: FORBIDDEN`. Therefore no project file reviewed here
supports a profitability claim.

## File-grounded empirical results and engineering observations

### 1. P1 Tier-B Lite direction/execution campaign

Source: `v7/docs/P1_TIER_B_LITE_FINDINGS.md` (session dated 2026-07-27/28).
The document says all reported campaign figures are development OOF or temporal
holdout and that its frozen tail was not opened.

| Observation reported by the artifact | Status and limiting condition |
|---|---|
| Numpy logistic temporal holdout accuracy was 0.5087 vs 0.5033 majority; Ridge signed-terminal-return OOS IC was +0.015; shuffled-label canary uplift was +1.18pp; GRU OOF accuracy was 0.470–0.486. | File-grounded diagnostic measurements. They do not pass the campaign’s 0.60 directional gate. |
| Upside and downside excursion ICs were +0.124 and +0.152, respectively, while signed-return IC was +0.015. | File-grounded: path magnitude was more predictable than direction for this feature set and sample. It does **not** demonstrate tradable edge. |
| 36 breakout-executor configurations on 271,021 development events all lost −14.6 to −23.6 bps/trade at the stated cost model. | File-grounded diagnostic result, specific to the executor, features, horizon, data, and cost assumptions. |
| In deterministic replay across 85 symbols, immediate directional expectancy was −0.61146 R/directive and direction-scrambled control was −0.60802; confidence delay was −0.00212 R/directive and −0.5435 R/trade when it traded. | File-grounded campaign result. The document reports failed economic gates and says abstention made per-directive comparisons misleading. |
| Long-horizon point estimates became positive in some 24h/48h cells, but every reported day-clustered 95% confidence interval contained zero. | File-grounded diagnostic result, not validation of long-horizon profitability. The horizons are outside the then-locked 5m/15m/1h authority. |
| An 83-rule conditioning screen produced zero positive holdout net expectancies and zero clustered intervals excluding zero. | The source itself classifies this as scratch analysis, not committed authority-hashed evidence; it is a lead for preregistration, not a decision record. |

**Interpretation.** The admissible project evidence rejects *this specific* P1
proposition: bar-derived Tier-B Lite features at the tested 75-minute,
16-bps-round-trip setting did not supply enough directional after-cost signal.
It does not reject all behavioral structure, all conditional strategies, or
Candidate Episodes generally. The V8 architecture must not treat the P1 failure
as proof either for or against expert decomposition.

### 2. Engineering failures caught by verification

Source: `v7/docs/P1_TIER_B_LITE_FINDINGS.md`.

| File-grounded failure | What the source says caught or constrained it | Architecture implication (interpretation) |
|---|---|---|
| Nine initially unexecuted campaign/simulation paths contained defects, including missing imports, an unrunnable Modal CLI, missing replay manifest/authority sidecar, a meaningless shuffled-label canary, and Decimal conversion failure for NumPy scalars. | End-to-end campaign execution and fail-closed checks exposed them. | A declared workflow is not evidence that the workflow runs; V8 needs runnable vertical-slice gates before adding components. |
| A windowed replay omitted a funding settlement exactly at the terminal boundary, creating a mismatch with full-tape replay. | Differential replay found the discrepancy; the bound was made inclusive and 59 adapter/simulator contract tests reportedly passed. | Boundary-policy tests and full-versus-window replay are justified locked checks for any canonical simulator. |
| Execution-RL code had six additional defects and had never run; cost calls passed arguments incorrectly, evaluator/mask contracts disagreed, and the path duplicated economic logic. | Smoke execution after repair ran 780 episodes, 2,539 steps, and 2,000 gradient updates. | Smoke completion establishes executability only; it is not economics or policy validation. |
| The RL sampler used fixed-stride bar windows and neither directives nor the detector, despite `SYSTEM.md` describing directive-to-tracker-to-policy episodes. | Source-code audit in the findings document. | Do not use that RL result as evidence about a sniper, router, or Candidate Episode design. |
| The RL state machine never reached `ACTIVE`; HOLD/REDUCE was unreachable. A later zero-result was traced to an ARMED/WAIT state-machine contradiction, and reporting of zero trades was repaired to `DEGENERATE_NO_TRADE`. | Forced synthetic trades, action histograms, and state-path audit. | Lifecycle claims require transition coverage plus funnel metrics; `NO_TRADE`/zero reward must carry provenance. |

### 3. Successful engineering patterns with explicit limits

| Pattern | File-grounded support | Limit |
|---|---|---|
| Fail-closed data and authority binding | `v7/README.md`, `v7/RESEARCH_PROTOCOL.md`, and V7 specs bind intervals, hashes, manifests, OOF/frozen split rules, and reject missing authority sidecars. | Certification says frozen OOS isolation was convention, not an enforced read-only evaluator mount. |
| Canonical scalar simulation with an independent decimal test oracle | Certification records scalar golden tests, 36 modal tests passing, an oracle, outcome hash, and ledger reconciliation. | The same certification identifies unresolved parallel economic paths and marks the P1 economic verdict invalid/not certified. |
| Differential replay and scrambled-direction control | Findings reports full/window replay catching a funding-boundary error and reports a direction-scrambled control alongside the model side. | Results only assess the defined P1 replay/policy setting; controls do not validate V8’s proposed experts. |
| Clustered uncertainty and overlap awareness | Findings re-prices long holds with day-clustered bootstrap and non-overlapping subsampling, rejecting naive t-statistic confidence. | The document labels several horizon/cost screens scratch analyses, requiring rerun in the campaign harness. |
| Separation of forecast from hard risk authority | `execution_rl_policy_v1.json` gives snipers forecast-only outputs and reserves deterministic limits for risk. | The same target design leaves trade-side, timing and management to an unvalidated RL policy; it is a gated target architecture, not an achieved capability. |
| Compute correctness over speed | `V7_COMPUTE_INFRASTRUCTURE_V1.md` requires CPU reference, no silent CUDA fallback, exact label/simulation fields, and parity gates. | README/Operator Tests state many long, hardware-dependent, CUDA, stress, and economic gates were operator-owned or not run during packaging. |

## Cross-file contradictions and stale authorities

| Files in tension | File-grounded contradiction | Required handling |
|---|---|---|
| `v7/specs/simulation_authority_certification_v1.json` vs `v7/docs/P1_TIER_B_LITE_FINDINGS.md` | Certification says P1 adapter/replay integration and single economic API are unresolved; the later findings document says the adapter/replay were implemented and run, but expressly says certification should not self-update and remains stale. | Treat certification as the current blocking authority until an independent operator reruns and updates it. The findings may guide that rerun, not override it. |
| `v7/SYSTEM.md` / `execution_rl_policy_v1.json` vs findings §8 | Target design says sniper directive → tracker → execution policy with ongoing position management; the audit says implemented RL sampled arbitrary bar windows and could not enter `ACTIVE`. | Label current RL as standalone, incomplete bar-trading experimentation. Do not represent it as integrated Candidate execution. |
| V8 `Candidate ≠ order` / independent execution language vs V7 policy authority | V8 frames a Candidate and canonical lifecycle execution; V7 target policy grants execution RL all side, target exposure, and order decisions. | This is a design incompatibility to resolve experimentally: choose a fixed/canonical executor for attribution first, or explicitly define the learned executor’s counterfactual attribution contract. |
| V8 independent execution claim vs V8’s own caveat in the master goal | The master prompt says alpha and execution may interact and must not be assumed statistically independent. | Preserve only operational separation/attribution as a provisional invariant; do not claim statistical independence. |
| V8’s candidate-centric, behavior-expert architecture vs current evidence | V8 calls H1/H2/H3/H5/H6 provisional/open; V7 P1 measured a direction-neutral bar feature campaign, not behavior-specific experts or full candidate lifecycles. | No V7 result validates routing, expert specialization, candidate scoring, or ranking. Start each with its stated cheapest baseline. |

## V8 claim disposition

This table classifies the *present project evidence*, not the broader literature.

| V8 element | Evidence classification | Audit conclusion |
|---|---|---|
| Candidate is a lifecycle-bearing hypothesis rather than automatically an order | **DESIGN_INFERENCE** with supportive engineering rationale | Retain as a testable data/attribution design: log triggered, expired, invalidated, and rejected candidates. No project file shows it improves returns or calibration yet. |
| MarketState as leakage-safe shared context | **PROVISIONAL_DECISION** | V7 already has causal-feature and authority disciplines that can support it. No tested MarketState schema or comparison against raw features is present. |
| Behavior-specific Experts beat a global model | **OPEN_QUESTION** | P1’s global/directional weakness is insufficient evidence for specialization. Require equal-data, equal-cost OOS comparison. |
| Self-gating vs explicit router | **OPEN_QUESTION** | V8 identifies compute/recall/duplication trade-offs, but no empirical comparison exists. Start self-gating if inexpensive, then test routing only if it has a measurable objective. |
| Candidate scorer increases quality rather than merely reducing trades | **OPEN_QUESTION** | V7 documents the exact abstention pitfall. Compare matched coverage and per-trade economics/calibration, not per-directive expectancy alone. |
| Cross-candidate ranking | **PROVISIONAL_DECISION / conditional** | Only justified when acceptable candidates compete for a defined scarce-capital/portfolio constraint. Do not implement first. |
| Canonical, source-provenanced execution and deterministic hard risk | **LOCKED_INVARIANT candidate** | This is the strongest project-supported engineering principle, but authority certification must be independently renewed before treating it as certified. |
| Learned execution RL | **REJECTED_OPTION for the initial V8 baseline** | It is a gated V7 target with integration/state-machine failures and no admissible economic result. Reintroduce only after a positive deterministic baseline and a single certified economic authority. |
| High-resolution Tier-A/S data | **DESIGN_INFERENCE** | V7 evidence motivates testing richer flow/L1 information because bars were weak, but no Tier-A/S economic PASS is supplied. Data quality and causal construction must be gated before an edge claim. |

## Minimum evidence-gated V8 starting point

The following is an interpretation/recommendation derived from the audit, not a
claim that V8 will work:

1. Build 2–3 deterministic, self-gating behavior definitions that emit
   `Candidate | None`; record every lifecycle terminal state, including no
   trigger and pre-entry invalidation.
2. Use one versioned, deterministic execution policy and one source-provenanced
   economic ledger. Validate full-tape/window equivalence, funding boundaries,
   costs, fills, and zero-trade reporting.
3. Pre-register the horizon, costs, universe, baseline, frozen split,
   coverage-matched metrics, clustering unit, and promotion gate. Do not open a
   frozen holdout to repair a rejected development hypothesis.
4. Test each add-on against the immediately simpler baseline: expert versus
   global; full lifecycle versus trade-only; scorer versus raw candidates;
   ranker only under capital contention; adaptive execution versus canonical
   execution.
5. Block learned routing, learned scoring, ranking, and RL execution whenever
   the preceding component lacks an incremental frozen-OOS gain or the economic
   authority is uncertified.

## Audit boundaries

- This audit did not find V6 artifacts, so it makes no V6-versus-V7 causal or
  historical assertion.
- It did not rerun campaign data, replay, GPU, or operator-owned validation;
  reported numerical results retain the evidence status assigned by their source
  files.
- The audit found the workspace root is not itself a Git repository. V7 is a
  nested repository, so provenance checks should be run there and recorded with
  its commit and artifact hashes.
