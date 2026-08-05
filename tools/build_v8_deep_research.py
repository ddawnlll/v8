#!/usr/bin/env python3
"""Compile the book-derived V8 deep-research register to JSON and HTML.

This is research material only.  It deliberately separates the book's qualitative
claims, external formalization aids, and V8 design proposals.
"""
from __future__ import annotations

import html
import json
from pathlib import Path


OUT_JSON = Path("research/handbook_v8_deep_research.json")
OUT_HTML = Path("research/handbook_v8_deep_research.html")


SOURCES = [
    {
        "id": "BOOK-LIM-2016",
        "title": "The Handbook of Technical Analysis: The Practitioner's Comprehensive Guide to Technical Analysis",
        "author": "Mark Andrew Lim",
        "year": 2016,
        "location": "Local user-supplied PDF",
        "role": "Practitioner source: chapter arguments, diagrams, named patterns, and risk workflow; not economic evidence for V8.",
    },
    {
        "id": "LO-MAMAYSKY-WANG-2000",
        "title": "Foundations of Technical Analysis: Computational Algorithms, Statistical Inference, and Empirical Implementation",
        "url": "https://www.nber.org/papers/w7613",
        "role": "Supports converting visually subjective patterns into explicit algorithms and testing their conditional outcomes; US equities, not V8 crypto evidence.",
    },
    {
        "id": "POHL-ET-AL-2018",
        "title": "Theoretical and empirical analysis of trading activity",
        "url": "https://arxiv.org/abs/1803.04892",
        "role": "Supports treating volume, volatility and trading activity as related but distinct observables; NASDAQ evidence, not a kline alpha transfer.",
    },
    {
        "id": "KAMINSKI-LO-2014",
        "title": "When Do Stop-Loss Rules Stop Losses?",
        "url": "https://chesler.us/resources/academia/stop%20losses.pdf",
        "role": "Shows that stop policies are conditional on the return process and are not automatically beneficial; not a parameter prescription for V8.",
    },
    {
        "id": "SERMPINIS-ET-AL-2018",
        "title": "Technical Analysis and Discrete False Discovery Rate: Evidence from MSCI Indices",
        "url": "https://arxiv.org/abs/1811.06766",
        "role": "Supports explicit data-snooping and multiplicity control when many technical rules are searched; different assets and design.",
    },
    {
        "id": "KOSHIYAMA-FIROOZYE-2019",
        "title": "Avoiding Backtesting Overfitting by Covariance-Penalties",
        "url": "https://arxiv.org/abs/1905.05023",
        "role": "External guardrail for overfitting analysis; does not replace V8's preregistration or frozen chronological OOS gate.",
    },
    {
        "id": "CONT-KUKANOV-STOIKOV-2010",
        "title": "The Price Impact of Order Book Events",
        "url": "https://arxiv.org/abs/1011.6402",
        "role": "Explains why order-flow/depth claims need their own data contract; it does not validate OHLCV proxies or crypto execution.",
    },
]


TAXONOMY = [
    {
        "id": "SF-01",
        "family": "Trend continuation",
        "book_basis": "Ch. 5 trend definitions, wave degrees, filters, retracements; Ch. 11 moving averages.",
        "sub_strategies": "Pullback continuation; degree-specific breakout; channel continuation.",
        "v8_classification": "EXISTING_EXPERT + variants",
        "v8_alignment": "trend_pullback is a narrow EMA-pullback member, not the whole family.",
        "status": "FORMALIZED only for the existing v1 pilot; other forms need new preregistration.",
    },
    {
        "id": "SF-02",
        "family": "Trend exhaustion / reversal",
        "book_basis": "Ch. 5 trend-quality deterioration; Ch. 7 reversal bars; Ch. 9 divergence.",
        "sub_strategies": "Exhaustion bar; symmetry break; divergence-confirmed reversal.",
        "v8_classification": "NEW_EXPERT_HYPOTHESIS or shared state",
        "v8_alignment": "No dedicated reversal Expert is registered. Trend-quality fields should not silently become a reversal score.",
        "status": "DESIGN_INFERENCE; no execution proposal in this report.",
    },
    {
        "id": "SF-03",
        "family": "Volatility contraction to expansion",
        "book_basis": "Ch. 7 ID/NR volatility breakouts; Ch. 21 ATR cycles and low-volatility consolidation.",
        "sub_strategies": "ID/NR breakout; frozen-range close breakout; band/envelope expansion.",
        "v8_classification": "NEW_EXPERT_HYPOTHESIS",
        "v8_alignment": "P1 deep dive TA-004; current V8 exposes ATR but not a compression/range contract.",
        "status": "DRAFT, not in frozen slice.",
    },
    {
        "id": "SF-04",
        "family": "Failed move / re-entry",
        "book_basis": "Ch. 7 pin bars, support/resistance false breakouts, Hikkake, Oops.",
        "sub_strategies": "Pin-bar reclaim; multi-bar false breakout; Hikkake; gap/Oops variant.",
        "v8_classification": "EXISTING_EXPERT_VARIANT / possible separate Expert",
        "v8_alignment": "liquidity_sweep_reclaim matches a wick-reclaim form. failed_breakout lacks an explicit prior breakout excursion in its present predicate.",
        "status": "P1 specification gap; do not retrofit v8_slice_001.",
    },
    {
        "id": "SF-05",
        "family": "Participation-conditioned price action",
        "book_basis": "Ch. 6 volume confirmation, volume timing, volume-to-bar-range relationship.",
        "sub_strategies": "Four range×volume quadrants; volume-confirmed breakout; volume divergence.",
        "v8_classification": "SHARED_MARKET_STATE_COMPONENT first",
        "v8_alignment": "The participation group exists but emits no concrete feature; raw OHLCV can support a declared relative-volume feature.",
        "status": "P1 feature study before any standalone Expert.",
    },
    {
        "id": "SF-06",
        "family": "Range / value mean reversion",
        "book_basis": "Ch. 12 containment, Ch. 17 Market Profile, Ch. 20 cycles.",
        "sub_strategies": "Responsive value-area trade; envelope return; cycle mean reversion.",
        "v8_classification": "DATA_BLOCKED or separate future hypothesis",
        "v8_alignment": "True TPO/volume-at-price is unavailable in the declared 1h OHLCV tape. A close-based proxy is not Market Profile.",
        "status": "Deferred; no silent proxy.",
    },
    {
        "id": "SF-07",
        "family": "Cross-market / relative-strength context",
        "book_basis": "Ch. 22 breadth, Ch. 23 sentiment, Ch. 24 relative strength.",
        "sub_strategies": "Relative-strength leader/laggard; breadth context; sentiment contrarian context.",
        "v8_classification": "DATA_BLOCKED",
        "v8_alignment": "Requires a declared PIT multi-instrument universe and source-specific availability clocks.",
        "status": "Deferred data-plane work, not an Expert from BTCUSDT alone.",
    },
    {
        "id": "SF-08",
        "family": "Practitioner geometry and projection",
        "book_basis": "Ch. 10 Fibonacci, Ch. 18 Elliott, Ch. 19 Gann, selected chart/candlestick patterns.",
        "sub_strategies": "Ratio projections; wave counts; geometric lines; discretionary pattern reading.",
        "v8_classification": "NON_EXECUTABLE_PRACTITIONER_CONCEPT / REJECTED",
        "v8_alignment": "The book supplies multiple subjective constructions; a deterministic state definition, search-family accounting and independently falsifiable mechanism are absent.",
        "status": "Not admitted as a V8 Expert by default.",
    },
]


DEEP_DIVES = [
    {
        "id": "TA-002",
        "title": "Macro / meso / micro context is a state contract, not three simultaneous signals",
        "priority": "P1",
        "evidence_label": "DESIGN_INFERENCE",
        "decision": "SHARED_MARKET_STATE_COMPONENT; FUTURE_CONTRACT_CHANGE",
        "source_argument": [
            "Lim first rejects a single absolute definition of trend: the same path can be read through peaks/troughs, a barrier, an absolute move, or a chart transformation. The argument is a warning that a definition is an operational choice, not a discovered truth.",
            "The wave-degree discussion then makes the key nesting claim: a market can be in consolidation at one degree while it remains in trend at another. Breakout level, stop scale and the volatility that matters depend on the degree being traded.",
            "That logic supports separating context windows from the trigger window. It does not support an omniscient multi-timeframe vote, and the book's illustrated degrees are not a formula for choosing lookbacks.",
        ],
        "exact_evidence": [
            {"book_pages": "129-130", "pdf_pages": "155-156", "locator": "§5.1, Figures 5.5-5.8", "evidence": "Wave cycles are nested; Figure 5.7 explicitly depicts lower-, medium-, and higher-wave readings that differ at the same time. Figure 5.8 makes breakout levels degree-specific.", "visual_note": "Figure 5.7 is a two-scale drawing: the jagged lower wave can be directional while the smooth medium wave is range-bound. This directly rules out storing one global TREND/RANGE label."},
            {"book_pages": "134", "pdf_pages": "160", "locator": "§5.2, Figures 5.14-5.16", "evidence": "Retracement duration and bar-range/ATR changes are presented as early evidence of altered trend behavior.", "visual_note": "Figure 5.14 labels successive pullbacks by bar count before a symmetry break; it suggests a measurable duration ratio, not a subjective visual label."},
            {"book_pages": "144-145", "pdf_pages": "170-171", "locator": "§5.3 price/trend filters", "evidence": "Price, time and event filters are distinguished; a second price constraint can bound entry distance after a confirming event.", "visual_note": "This is a sequencing argument: context/setup precedes trigger, and trigger precedes an admissible price bound."},
        ],
        "conditions_and_exceptions": [
            "No scale is intrinsically macro, meso or micro. The labels are an Expert-relative contract; a 32-bar history can be insufficient for one family and excessive for another.",
            "A higher-window close is unavailable until that window closes. Resampling must retain the source bars and its bar_available_time; using a completed higher-timeframe candle inside its interval is leakage.",
            "The figures show idealized wave nesting. They do not show that three windows add independent predictive information or justify a majority vote.",
        ],
        "mechanism_hypothesis": "A hypothesis may be evaluated only when its entry-scale trigger is not structurally contradictory to a predeclared context-scale state. This is a self-gating condition, not a learned router or a confidence score.",
        "existing_v8_behavior": "V8 currently builds EMA-fast/EMA-slow, ATR, prior extremes and a fixed last-32-closed-bar history. The existing pilots consume declared feature groups. O-020 already records the unresolved question of a per-Expert history window.",
        "missing_v8_capability": "No named multi-degree context feature has a separate source-bar window, availability clock, null policy, or Expert-owned lookback. The fixed history tuple also lacks per-bar ATR and volume needed by several candidate formalizations.",
        "alternative_formalizations": [
            {"id": "A", "label": "OUR_PROPOSED_FORMALIZATION", "name": "Three disjoint closed-bar windows", "definition": "For Expert e at decision D: macro W_M, meso W_m, micro W_u are deterministic suffixes of admissible closed bars with W_M > W_m > W_u. Each emits only descriptive features; the Expert declares which predicates are gates.", "parameters": "(W_M, W_m, W_u) are registered variant parameters, not fit online.", "book_relation": "Book-derived nesting; not a book equation."},
            {"id": "B", "label": "BOOK_DERIVED", "name": "Retracement-duration symmetry", "definition": "Let d_i be the closed-bar count of successive countertrend legs under an explicit swing algorithm. Compare d_current to median(d_1..d_{i-1}); an excursion outside a predeclared band is a context descriptor.", "parameters": "Swing algorithm, minimum excursion and history window must be preregistered.", "book_relation": "Operationalizes Figure 5.14; the statistic is ours."},
            {"id": "C", "label": "INDUSTRY_STANDARD", "name": "Directional efficiency diagnostic", "definition": "ER_n = |C_t-C_{t-n}| / sum_{i=0}^{n-1}|C_{t-i}-C_{t-i-1}|, defined only when the denominator is positive.", "parameters": "n and a missing/zero-denominator rule are variant parameters.", "book_relation": "Not in Lim; optional descriptive substitute for a visually smooth/erratic path."},
        ],
        "proposed_contract": {
            "component_id": "multi_degree_context_v1",
            "kind": "MarketState feature group extension, not an Expert",
            "required_observables": "closed OHLCV bars with event_id and bar_available_time",
            "outputs": "context_{macro,meso,micro}_trend, retracement_duration_ratio, context_quality, source_window_event_ids",
            "null_policy": "NOT_YET_AVAILABLE until every declared window is warm; no fallback to a shorter window",
            "authority_owner": "MARKET_STATE_CONTRACT + EXPERTS_REGISTRY",
            "hash_effect": "new feature_graph_version and lineage hash; existing manifest/state hashes are intentionally non-comparable",
            "compatibility": "new versioned feature only; existing Experts retain their declared requires and do not consume it",
            "tests": "higher-window bar-close leakage, source-window identity, warmup null, two-build state-hash equality, Expert requires audit",
        },
        "experiment": {
            "status": "DRAFT_NOT_PREREGISTERED",
            "null_hypothesis": "Adding the declared context gate does not improve the specified Expert versus its immediately simpler self-gating baseline at matched family accounting.",
            "population": "All eligible closed BTCUSDT perpetual 1h bars in a future manifest-bound PIT tape; exact manifest hash and chronological split are operator-owned preregistration fields.",
            "primary_metric": "Costed canonical OOS comparison defined in the new preregistration; no economic verdict without authority receipt.",
            "secondary_metrics": "candidate coverage, no-setup reason distribution, execution share, KS divergence, endpoint mix, state-quality veto rate.",
            "failure_criteria": "any unavailable higher-timeframe input, changed manifest after inspection, or unreported parameter family invalidates the run.",
        },
        "risks": ["Window choice can be a hidden search family.", "Scale labels can accidentally duplicate existing EMA trend information.", "Cross-timeframe feature availability is a common leakage route."],
        "recommendation": "Resolve O-020 as a registry/contract change first. Implement no multi-timeframe signal until the state schema, source windows and test fixtures are frozen.",
    },
    {
        "id": "TA-004",
        "title": "Volatility contraction to expansion: turn a visual setup into one frozen range and one closed-bar trigger",
        "priority": "P1",
        "evidence_label": "DESIGN_INFERENCE",
        "decision": "NEW_EXPERT_HYPOTHESIS",
        "source_argument": [
            "The book offers two related but distinct observations: an ID/NR pattern is an inside bar that is also the narrowest bar of a stated recent window, while ATR cycles identify low-volatility consolidation and high-volatility episodes. It does not present a universal 'squeeze' formula.",
            "The operational core is useful because it is finite: define the consolidation, freeze its boundaries before the trigger, require a closed-bar violation, then attach an expiry and invalidation. The direction is supplied by the break, not predicted by a compression score.",
            "Lim also warns elsewhere that falling ATR in an established trend can mark weakness. Therefore contraction is not synonymous with continuation; a breakout family and a trend-exhaustion family must remain independently falsifiable.",
        ],
        "exact_evidence": [
            {"book_pages": "230-232", "pdf_pages": "256-258", "locator": "§7.4, Figures 7.34-7.39", "evidence": "Hikkake is presented as a failed inside-bar breakout; ID/NR n is defined as an inside bar that is the narrowest of the previous n bars, with no directional sentiment before the break.", "visual_note": "Figure 7.38 reduces the pattern to a containment bar plus a relative-width comparison. This is the strongest book-native anchor for an OHLC-only candidate."},
            {"book_pages": "741-742", "pdf_pages": "767-768", "locator": "§21.2, Figures 21.13-21.14", "evidence": "ATR is shown as average candle/range size and as cycling through high and low zones; the text explicitly separates high ATR from trend direction.", "visual_note": "Figure 21.13 shows equal directional displacement with different candle ranges, so range magnitude must be measured independently of direction."},
            {"book_pages": "134-135", "pdf_pages": "160-161", "locator": "§5.2, Figures 5.15-5.17", "evidence": "Average range/ATR and persistence are trend-quality descriptors, not guaranteed continuation signals.", "visual_note": "The declining-ATR illustration is paired with a cautionary weakness reading, which is the counterexample to a naive long-only squeeze rule."},
        ],
        "conditions_and_exceptions": [
            "Use only closed bars. A current-bar high that pierces a boundary is not a valid close breakout at decision time.",
            "A narrow bar alone is not a compression episode. The range must be frozen from bars preceding the trigger; otherwise the barrier moves after seeing the breakout.",
            "ID/NR and ATR-percentile variants are one mechanism family but are not interchangeable. Test them as declared variants under one family-level multiplicity unit.",
            "OHLC cannot establish stop-order queue position or intrabar trigger order. The initial proposal uses next eligible bar execution and the canonical conservative simulator.",
        ],
        "mechanism_hypothesis": "During a declared low-range consolidation, a close outside the pre-existing range creates a time-bounded continuation hypothesis. Direction, geometry and failure are deterministic; compression itself is a habitat gate.",
        "existing_v8_behavior": "V8 has ATR, closed-bar history, deterministic candidate lifecycle and static stop/target/expiry geometry. It has no normalized ATR history, compression episode identity, frozen consolidation boundary or volume-aware history field.",
        "missing_v8_capability": "The history tuple must carry either per-bar true range/ATR or a separately versioned compression feature. Candidate identity must anchor to the start of the consolidation rather than the later breakout decision clock.",
        "alternative_formalizations": [
            {"id": "A", "label": "BOOK_DERIVED", "name": "ID/NR-n", "definition": "NR_t = H_t-L_t. Setup when bar t is inside bar t-1 and NR_t = min(NR_{t-n+1},...,NR_t). Trigger only on a later closed-bar close beyond the frozen inside-bar high or low.", "parameters": "n, maximum trigger delay, stop geometry and expiry are registered variants.", "book_relation": "Directly follows §7.4; close-based trigger and lifecycle are V8 additions."},
            {"id": "B", "label": "OUR_PROPOSED_FORMALIZATION", "name": "Normalized ATR percentile plus frozen range", "definition": "TR_t=max(H_t-L_t,|H_t-C_{t-1}|,|L_t-C_{t-1}|); ATR_t uses declared Wilder smoothing. v_t=ATR_t/C_t. Let q_t be the empirical rank of v_t in the preceding m admissible values. Setup when q_t<=q_c and width=(U-L)/ATR_t lies in a declared band, U=max H and L=min L over the pre-trigger k bars. Long trigger: C_t>U+delta*ATR_t; short is symmetric.", "parameters": "n,m,q_c,k, width band, delta, max trigger delay and geometry are a declared search family.", "book_relation": "The ingredients are book-derived; the percentile and exact equations are ours."},
            {"id": "C", "label": "INDUSTRY_STANDARD", "name": "Band-width compression", "definition": "BW_t=(Upper_t-Lower_t)/Middle_t using a fully declared moving average and dispersion rule; setup uses its pre-trigger historical rank, then the same frozen-range trigger as B.", "parameters": "Band construction is a distinct variant family branch, not an unlabelled indicator substitution.", "book_relation": "Not a Lim formula in the selected spans; included as an explicit external/industry alternative, not book text."},
        ],
        "proposed_contract": {
            "expert_id": "compression_breakout",
            "strategy_family": "SF-03",
            "mechanism_family_id": "volatility_regime_transition",
            "behavior_family_id": "compression_breakout",
            "formalization_status": "PROPOSED; no registry admission",
            "required_observables": "closed OHLCV, prior close, true range/ATR history",
            "setup_predicate": "one declared A/B/C compression predicate at the setup clock",
            "trigger_predicate": "closed-bar close outside U/L frozen at setup",
            "entry_rule": "candidate emits at trigger; canonical next eligible fill policy, never same-bar assumed fill",
            "invalidation_rule": "closed-bar re-entry inside the frozen range or declared structural stop; choose one variant, do not combine after observing outcomes",
            "expiry_rule": "trigger must occur within T_setup bars; after execution, a distinct T_response is a position-management challenger",
            "duplicate_episode_rule": "episode_key anchor = first setup bar of frozen consolidation; same U/L and anchor suppress duplicate candidates",
            "abstention_conditions": "incomplete feature warmup, degraded state, range too wide/narrow, tradability-mask veto",
            "risk_requirements": "declared stop_r/target_r, max heat and canonical cost/funding policy",
        },
        "experiment": {
            "status": "DRAFT_NOT_PREREGISTERED",
            "null_hypothesis": "A compression-gated breakout rule does not exceed its simplest deterministic close-breakout baseline after declared costs under a new chronological OOS protocol.",
            "primary_metric": "The protocol-defined costed canonical OOS estimate and its family-level decision rule; this report assigns no numerical pass threshold.",
            "secondary_metrics": "setup-to-trigger conversion, trigger delay, direction balance, duplicate suppression, gap/ambiguity frequency, coverage, endpoint mix, parameter stability.",
            "multiplicity": "A/B/C are disclosed variants of one behavior family; all tested parameter tuples and failed runs are retained.",
            "stop_conditions": "invalid state lineage, any same-bar fill assumption, unbound cost model, or post-OOS parameter repair.",
        },
        "risks": ["Compression may be merely a volatility descriptor, not a directional mechanism.", "Threshold sweeps can manufacture an apparent rule.", "A breakout bar may be untradable under V8's range/funding mask, changing realized versus counterfactual populations."],
        "recommendation": "Admit only the smallest ID/NR-n or frozen-range challenger after a new preregistration. Do not add a generic squeeze indicator or an adaptive scorer.",
    },
    {
        "id": "TA-006",
        "title": "Volume × range × close-location: preserve the book's four quadrants, then test close location as a separate refinement",
        "priority": "P1",
        "evidence_label": "DESIGN_INFERENCE",
        "decision": "SHARED_MARKET_STATE_COMPONENT first; NEW_FEATURE_HYPOTHESIS",
        "source_argument": [
            "The book explicitly distinguishes four volume-by-range combinations and assigns different continuation/reversal interpretations in trend context. This is more concrete than a generic 'high volume is bullish' rule.",
            "The volume chapter also treats volume as confirmation/timing context, not an autonomous directional label. Its own examples mix trend, triangle and divergence context; the report must therefore not convert a quadrant into an unconditional trade signal.",
            "Close location is not a separate four-quadrant rule in the cited page. It is a V8 composition: a bounded OHLC measurement that can distinguish a wide bar closing near its high from one that retraces before close. Its provenance must remain ours.",
        ],
        "exact_evidence": [
            {"book_pages": "173-176", "pdf_pages": "199-202", "locator": "§6.1, Figures 6.1-6.3", "evidence": "Volume is introduced as corroborating pre-existing trend context and as potential breakout timing information, with confirmation and divergence examples.", "visual_note": "The chapter opening explicitly frames price as primary and volume as additional evidence, so volume must not become an unlabelled replacement for direction."},
            {"book_pages": "181", "pdf_pages": "207", "locator": "§6.1, Figure 6.9", "evidence": "The example treats low-volume reversals and an accumulation breakout as timing/context observations, not a standalone formula.", "visual_note": "Figure 6.9 labels volume at several different moments across one path. It illustrates regime context, not a one-bar classification."},
            {"book_pages": "197-198", "pdf_pages": "223-224", "locator": "§6.1, Figure 6.30", "evidence": "Narrow/low, narrow/high, wide/low and wide/high range-volume combinations are named and given conditional trend interpretations.", "visual_note": "Figure 6.30 is a 2×2 diagram. Direction comes from the surrounding trend; the two axes alone do not encode LONG or SHORT."},
        ],
        "conditions_and_exceptions": [
            "Venue-reported kline volume is an observable but is not order-flow imbalance, aggressor side or open interest. No microstructure claim is licensed from it.",
            "Relative volume must use a trailing, availability-gated reference distribution; a full-sample percentile leaks future regime information.",
            "The same OHLCV ingredients drive range, close location and existing ATR, so feature-family correlation must be reported rather than counted as independent confluence.",
        ],
        "mechanism_hypothesis": "Conditioning a pre-existing price-action hypothesis on a declared participation/range state changes its applicable habitat. It is not evidence that any quadrant predicts direction by itself.",
        "existing_v8_behavior": "`FEATURE_GROUPS` declares `participation`, but the current group has no emitted fields. The history tuple includes high/low/close and EMAs but not volume; current pilots do not consume participation.",
        "missing_v8_capability": "Versioned relative-volume/range/close-location features, explicit zero-volume and warmup policies, and feature lineage that records the reference window are absent.",
        "alternative_formalizations": [
            {"id": "A", "label": "BOOK_DERIVED", "name": "Four quadrant state", "definition": "range_z and volume_z are each classified LOW/HIGH against a trailing declared reference. Quadrant=(NARROW|WIDE, LOW_VOLUME|HIGH_VOLUME). Trend direction is supplied by a separately declared context predicate.", "parameters": "Lookback, threshold estimator, ties, missing/zero-volume rule and trend context are preregistered.", "book_relation": "Direct operationalization of Figure 6.30; thresholds are ours."},
            {"id": "B", "label": "OUR_PROPOSED_FORMALIZATION", "name": "Relative volume, true-range ratio, close-location value", "definition": "RVOL_t=V_t/median(V_{t-m},...,V_{t-1}); RR_t=TR_t/median(TR_{t-m},...,TR_{t-1}); CLV_t=(2C_t-H_t-L_t)/(H_t-L_t) when H_t>L_t, else 0 with an explicit DEGENERATE_RANGE flag.", "parameters": "m and high/low cutoffs form one declared feature search family.", "book_relation": "RVOL/RR/CLV equations are V8 proposals; only the volume-range concept is book explicit."},
            {"id": "C", "label": "ARXIV_SUPPORTED", "name": "Keep activity observables separate", "definition": "Retain raw volume, range volatility and derived relative values as distinct feature fields; do not infer depth, trade count or signed order flow from a kline volume bar.", "parameters": "No free parameter beyond each feature's declared history.", "book_relation": "Supported as a data-boundary caution by POHL-ET-AL-2018 and CONT-KUKANOV-STOIKOV-2010."},
        ],
        "proposed_contract": {
            "component_id": "participation_price_action_v1",
            "kind": "MarketState participation feature extension",
            "fields": "relative_volume: float|None; range_ratio: float|None; close_location: float|None; quadrant: enum|None; reference_window_event_ids: tuple[str,...]",
            "defaults": "No default numeric imputation; insufficient warmup is NOT_YET_AVAILABLE.",
            "authority_owner": "MARKET_STATE_CONTRACT + feature graph version",
            "hash_effect": "feature graph and lineage hashes change; feature reference window joins input lineage.",
            "compatibility": "No existing Expert consumes participation until its `requires` declaration and version change are registered.",
            "tests": "trailing-only reference, zero/flat bar behavior, revision replay, volume missingness, feature-group consumption audit, no future percentile",
        },
        "experiment": {
            "status": "DRAFT_NOT_PREREGISTERED",
            "null_hypothesis": "A declared participation context does not improve an immediately simpler parent Expert at the same stated comparison scope.",
            "primary_metric": "New preregistration required; describe coverage and all candidate states before any OOS effect estimate.",
            "secondary_metrics": "quadrant frequency, direction conditionality, candidate overlap, correlation with ATR/trend features, trigger conversion, mask-veto rate.",
            "sequence": "First descriptive PIT materialization; then one parent Expert × one quadrant gate; then frozen comparison. Do not test every quadrant against every pattern without a disclosed family plan.",
        },
        "risks": ["Kline volume definitions vary by venue and can change.", "A volume feature may be a proxy for volatility or time-of-day rather than participation.", "Adding CLV can accidentally turn a shared context study into a new candlestick-pattern search."],
        "recommendation": "Implement only audited descriptive features first. The first challenger should gate one existing family, with no score aggregation and no inference of order-flow direction.",
    },
    {
        "id": "TA-008",
        "title": "Failed breakout / re-entry variants: separate the excursion, reclaim, trigger and stop",
        "priority": "P1",
        "evidence_label": "DESIGN_INFERENCE",
        "decision": "EXISTING_FAMILY_ALIGNMENT plus specification-gap challenger",
        "source_argument": [
            "The book distinguishes a pin bar (an intraperiod barrier penetration followed by a retrace) from a broader support/resistance false breakout that can span one or multiple bars. The short entry is described after price closes back through the prior resistance, with the stop beyond the excursion high.",
            "Hikkake is a more specific two-stage case: inside bar, initial false breakout, then opposite-side break within a stated three-bar window. Its structure is materially different from merely being below a rolling high.",
            "These distinctions matter in V8 because different mechanism claims imply different episode anchors, triggers, expiry and invalidation. Threshold-only changes remain variants; a different required excursion or trigger can justify a separate Expert under the protocol's independently-falsifiable test.",
        ],
        "exact_evidence": [
            {"book_pages": "227-228", "pdf_pages": "253-254", "locator": "§7.3, Figures 7.30-7.31", "evidence": "A pin bar is an apparent barrier breakout that retraces; the broader false-breakout example enters after a close back through the prior barrier and places the stop beyond the breakout high.", "visual_note": "Figure 7.31 labels three separate elements: resistance, a false breakout excursion, and a later short below resistance. It is not just 'close below highest high'."},
            {"book_pages": "230", "pdf_pages": "256", "locator": "§7.4, Figure 7.34", "evidence": "Hikkake requires an inside bar, a false breakout, and an opposite-side break; the book gives a maximum three-bar interval for the latter.", "visual_note": "The diagram has two mirror-image sequences. This makes the initial failed direction and later trigger direction explicit."},
            {"book_pages": "231", "pdf_pages": "257", "locator": "§7.4, Figure 7.36", "evidence": "The Oops pattern uses an opening gap beyond the previous range and stop-entry/stop-and-reverse mechanics.", "visual_note": "This is an execution-heavy pattern; 1h OHLC cannot reconstruct its intrabar stop order sequence, so it is not ported as-is."},
        ],
        "conditions_and_exceptions": [
            "A wick-through/reclaim has enough OHLC information for a closed-bar candidate, but a claimed intrabar stop fill does not. Separate the signal from the later eligible execution policy.",
            "A rolling extreme must be frozen at the excursion/setup clock. Recomputing it after the failure makes invalidation drift and breaks episode identity.",
            "Hikkake's inside-bar predicate and three-bar trigger delay are a distinct formalization branch. It must not be folded into a generic failed-breakout result after inspection.",
        ],
        "mechanism_hypothesis": "A barrier excursion that fails to hold may leave price on the opposite side of the frozen barrier; the re-entry is a time-bounded reversal hypothesis. The mechanism is not 'all closes below a prior high'.",
        "existing_v8_behavior": "`liquidity_sweep_reclaim_v1` explicitly tests low < prior_low and close > prior_low (and the mirror) using the closed-bar history and freezes the swept reference. It is a close alignment with the pin-bar/reclaim form. `failed_breakout_v1` labels itself as a close-above-then-fail setup, but its current evaluation emits when the current close is below a rolling prior high without storing an earlier close/excursion above that same reference.",
        "missing_v8_capability": "The current failed-breakout draft needs, in a future version, an explicit frozen barrier, excursion event id, reclaim event id, trigger rule, maximum delay and stop reference. This is a behavior-specification change, not a parameter tweak.",
        "alternative_formalizations": [
            {"id": "A", "label": "V8_EXISTING", "name": "Liquidity sweep reclaim", "definition": "Long: L_t < prior_low and C_t > prior_low; short mirrors prior_high. The reference is frozen in risk_geometry and `still_valid` requires the close to remain on the reclaimed side.", "parameters": "history window and static geometry are existing variant fields.", "book_relation": "Strong alignment with the pin-bar/reclaim concept, not necessarily the book's support/resistance multi-bar entry."},
            {"id": "B", "label": "BOOK_DERIVED", "name": "Multi-bar false breakout re-entry", "definition": "At excursion e, H_e>B for a frozen resistance B. A short trigger occurs only when a later closed C_t<B within T_reclaim bars. Stop reference is max(H_e,...,H_t) frozen at trigger; long mirrors support.", "parameters": "barrier algorithm, minimum excursion, T_reclaim, stop buffer, target and expiry are registered variants.", "book_relation": "Directly composes the §7.3 narrative and Figure 7.31; exact barrier algorithm is ours."},
            {"id": "C", "label": "BOOK_DERIVED", "name": "Hikkake", "definition": "Inside bar I has H_I<H_{I-1} and L_I>L_{I-1}. A false downside break L_e<L_I followed within 3 bars by C_t>H_I creates a long trigger; the bearish mirror applies. Every inequality uses closed bars.", "parameters": "The three-bar timing is book explicit; entry geometry and execution are V8 additions.", "book_relation": "Book-native pattern; 1h intrabar order semantics remain unavailable."},
        ],
        "proposed_contract": {
            "expert_id": "failed_breakout_reentry_v2 (candidate name only)",
            "strategy_family": "SF-04",
            "relationship_to_existing": "new version/challenger or separate Expert after registry decision; never overwrite v1 or frozen v8_slice_001",
            "required_observables": "closed OHLC with event ids; optional volume is a separately declared SF-05 context",
            "setup_predicate": "frozen barrier and first qualifying excursion",
            "trigger_predicate": "closed reclaim across that same frozen barrier within declared delay",
            "invalidation_rule": "close returns through the barrier in the opposite thesis direction, plus declared structural stop; price and thesis exits retain distinct reason codes",
            "candidate_identity": "hash(expert/version, instrument, direction, excursion_event_id, barrier_definition_version, geometry_version)",
            "execution_requirements": "signal at bar close; eligible fill only under canonical next-event policy; no stop-and-reverse in the initial challenger",
            "tests": "no candidate without excursion, barrier freeze, reclaim deadline, duplicate stability across clocks, long/short symmetry, gap-through-stop, same-bar ambiguity",
        },
        "experiment": {
            "status": "DRAFT_NOT_PREREGISTERED",
            "null_hypothesis": "Explicit excursion-and-reclaim structure does not improve on the simpler registered failed-breakout v1 or liquidity-sweep-reclaim v1 comparator under a new family-aware protocol.",
            "primary_metric": "Preregistered costed canonical OOS contrast; current frozen slice is not changed.",
            "secondary_metrics": "fraction of v1 candidates with a real excursion, trigger delay, Hikkake versus general re-entry overlap, endpoint causes, duplicate suppression, execution population divergence.",
            "failure_criteria": "An intrabar prerequisite that cannot be supported by the tape, moving barrier reference, or unreported cross-variant selection blocks the experiment.",
        },
        "risks": ["False-breakout labels are especially vulnerable to hindsight barrier selection.", "Pattern names can hide multiple mechanisms.", "The book's chart examples use equity daily data and may not transfer to BTCUSDT perpetual 1h."],
        "recommendation": "Keep `liquidity_sweep_reclaim_v1` intact. Treat an explicit excursion/reclaim definition as a documented v2 challenger, and keep Hikkake separate unless its setup/trigger/invalidation are truly the same hypothesis.",
    },
    {
        "id": "TA-013",
        "title": "Position management ladder: expected response is Expert-owned; trail and scale-out are not harmless defaults",
        "priority": "P1",
        "evidence_label": "OPEN_QUESTION",
        "decision": "POSITION_MANAGEMENT_VARIANT; O-013 future challenger",
        "source_argument": [
            "The money-management chapter separates passive sizing from dynamic exposure management. Its sizing sequence makes capital/risk/stop/trade/reward choices explicit, then introduces trailing/breakeven and scaling mechanisms as different stochastic exits.",
            "This is useful for V8 primarily as a decomposition: initial risk, price stop, thesis invalidation, expiry, trailing and partial exit are different actions with different counterfactual paths. The book's advocacy is not a license to enable all of them globally.",
            "External stop-loss theory also cautions that the value of stopping is conditional on the return process. A trailing or breakeven rule therefore needs its own benchmark and failure condition; it cannot be justified by intuitively 'reducing risk'.",
        ],
        "exact_evidence": [
            {"book_pages": "883", "pdf_pages": "909", "locator": "§28.1, Figure 28.3", "evidence": "Passive money management orders capital sizing, risk sizing, stop sizing, trade sizing, reward sizing and R/r sizing as separate components.", "visual_note": "Figure 28.3 is a directed sequence, making stop distance an input to size rather than a post-hoc risk label."},
            {"book_pages": "888", "pdf_pages": "914", "locator": "§28.1, Figures 28.9-28.10", "evidence": "Breakeven roll and scale-to-breakeven are distinct stochastic exits; the latter changes remaining exposure rather than only moving a stop.", "visual_note": "The diagrams show that a scale-out needs a quantity convention and changes the remaining position's risk geometry."},
            {"book_pages": "903-912", "pdf_pages": "929-938", "locator": "§28.1 dynamic sizing discussion", "evidence": "The book itself highlights compounding asymmetry, path dependence and risk-of-ruin concerns when sizing changes dynamically.", "visual_note": "The chapter supplies a counterargument to using dynamic management as a default improvement."},
        ],
        "conditions_and_exceptions": [
            "Static target/stop/expiry is the locked canonical baseline. Current V8 already distinguishes a post-entry thesis-invalidated close from a stop endpoint.",
            "A breakeven move, trailing stop, time-based non-response exit and scale-out are separate policy dimensions. Changing several at once destroys attribution.",
            "Partial exits require quantity, fee, fill, funding and same-bar order semantics. Level-1 OHLC cannot certify queue or partial-fill behavior; unsupported execution fidelity fails closed.",
        ],
        "mechanism_hypothesis": "For a specific Expert, failure to show its expected response within a declared horizon can be a different falsifier from price stop. Any active management rule must be owned by that Expert's expected-response contract and compared one moving part at a time.",
        "existing_v8_behavior": "Candidate lifecycle supports expiry and post-entry `still_valid` thesis invalidation. The simulator uses static `stop_r`, `target_r`, `expiry_bars`, conservative stop-first ambiguity, gap-through-stop logic and funding/cost accounting. It has no partial position, trailing-stop state, moving risk geometry or policy-version ledger events.",
        "missing_v8_capability": "An active-management challenger needs immutable policy id, management event schema, effective-stop history, quantity/remainder accounting and a simulator event order. None should be added until O-013 has a frozen comparison contract.",
        "alternative_formalizations": [
            {"id": "A", "label": "V8_EXISTING", "name": "Static geometry plus thesis invalidation", "definition": "Position closes at stop, target, expiry or Expert `still_valid` failure. Geometry is fixed at candidate birth; same-bar stop/target remains STOP_FIRST.", "parameters": "Existing registered geometry.", "book_relation": "V8's stronger audit formalization of the book's separate triggers/stops/management concepts."},
            {"id": "B", "label": "OUR_PROPOSED_FORMALIZATION", "name": "Non-response time stop", "definition": "For Expert e, close at the first closed bar t where bars_held>=T_response and an Expert-declared response predicate has not occurred. The rule has one policy id and no trailing/scale action.", "parameters": "T_response and predicate definition are one challenger variant family.", "book_relation": "Book-derived expiry/management idea; exact rule is ours."},
            {"id": "C", "label": "BOOK_DERIVED", "name": "Breakeven/trailing or scale-out", "definition": "After a declared favorable excursion, move a stop or reduce quantity according to a frozen policy. This branch is not runnable until quantity, fill and event-order contracts exist.", "parameters": "Activation threshold, stop rule, quantity fraction and order model are separate dimensions.", "book_relation": "Inspired by Figures 28.9-28.10; V8 implementation is intentionally deferred."},
        ],
        "proposed_contract": {
            "component_id": "expert_expected_response_v1",
            "kind": "Expert-declared static policy metadata before any simulator change",
            "fields": "expected_response_id, response_observables, non_response_horizon_bars, management_policy_id, allowed_actions",
            "initial_allowed_actions": "NONE or EXIT_ALL only; no partial fills, pyramiding, martingale or learned policy",
            "exit_priority": "funding settlement -> thesis/declared response evaluation on closed bar -> existing canonical barrier/expiry ordering must be explicitly versioned before use",
            "hash_effect": "expert version, policy version and simulator hash bind every outcome",
            "compatibility": "Existing Experts default to management_policy_id=STATIC_V1 and preserve byte-identical outcomes",
            "tests": "baseline identity, non-response endpoint retained, same-bar ordering, gap stop, funding boundary, full-tape/window replay, no partial position without declared support",
        },
        "experiment": {
            "status": "DRAFT_NOT_PREREGISTERED",
            "null_hypothesis": "One declared non-response exit does not improve the same Expert's static-geometry baseline under unchanged costs, funding and ambiguity policy.",
            "primary_metric": "New costed chronological OOS comparison under O-013; no claim from synthetic fixtures.",
            "secondary_metrics": "endpoint competing risks, holding-time distribution, MAE/MFE, funding count, cost sensitivity, drawdown/heat path, exit reason frequency.",
            "stop_conditions": "Any change to entry rule, sizing, target and management in the same challenger; unsupported partial-fill or intrabar assumption; missing policy hash.",
        },
        "risks": ["A time stop can merely crystallize mean-reversion losses.", "Breakeven may create a hidden high-turnover execution assumption.", "Scale-out changes the measurement target and cannot be compared to full-size outcomes without an explicit ledger."],
        "recommendation": "First study the already-auditable `still_valid`/non-response branch against static geometry. Defer trail and scale-out until a dedicated simulator-fidelity and policy-version proposal exists.",
    },
]


REPORT = {
    "schema_version": "v8-book-deep-research-v1",
    "created_utc": "2026-08-05",
    "title": "The Handbook of Technical Analysis — V8 Deep Research, Formalization and Compatibility Specification",
    "status": {"v8_status": "PRE-EXPERIMENTAL / EVIDENCE-BOUND", "economic_verdict": "NO_ECONOMIC_CLAIM", "normative": False},
    "purpose": "A second-pass research artifact. It preserves the initial 19-item register while compiling five high-value book themes into evidence locators, formalization alternatives, Expert/component contracts and draft experiment specifications.",
    "audit_finding": "The book does not present an explicit canonical taxonomy of eight V8-ready strategies. The eight-family map in this artifact is OUR_PROPOSED_FORMALIZATION: a traceable grouping of chapters and patterns, never a claim that Lim authored eight executable V8 strategies.",
    "provenance_legend": {
        "BOOK_EXPLICIT": "Definition, diagram, named pattern or workflow directly located in the supplied book.",
        "BOOK_DERIVED": "A deterministic restatement of a book concept; exact inequality, window or data policy is added by V8.",
        "ARXIV_SUPPORTED": "External literature supports a limited methodological or data-boundary point; it is not crypto alpha evidence.",
        "INDUSTRY_STANDARD": "Common technical convention included only as an explicitly optional formalization.",
        "V8_EXISTING": "Current repository behavior or contract, inspected in this work.",
        "OUR_PROPOSED_FORMALIZATION": "A new V8 research proposal requiring registry/preregistration before any experiment.",
    },
    "non_negotiable_boundaries": [
        "No book or external citation produces a profitability, execution-certification or promotion claim.",
        "No frozen holdout is opened and v8_slice_001 is not altered.",
        "Every formula below is separated from the book unless the book itself states it; parameters are not selected from inspected OOS outcomes.",
        "Market state, Expert hypothesis, risk admission, execution simulation and position management are distinct layers.",
        "OI, TPO/volume-at-price, order-book, breadth, sentiment and multi-asset claims remain data blocked unless their own PIT contracts exist.",
    ],
    "strategy_taxonomy": TAXONOMY,
    "deep_dives": DEEP_DIVES,
    "cross_cutting_execution_matrix": [
        ["Signal time", "Charts may describe intrabar action", "Closed-bar decision only", "Translate every pattern to closed-bar predicate or mark unsupported", "MARKET_STATE_CONTRACT"],
        ["Order type", "Market/stop/limit examples", "Canonical next-event policy with declared fill semantics", "No implicit chart-price fill", "SIMULATION_TRUTH_SPEC"],
        ["Stop behavior", "Stop is a risk plan, not a guaranteed exact fill", "Worse of stop/bar open; STOP_FIRST on ambiguity", "Gap-through-stop fixture retained", "SIMULATION_TRUTH_SPEC"],
        ["Partial / scale", "Practitioner mechanisms discussed", "No partial-position simulator contract", "Deferred fidelity; not a default", "O-013 future challenger"],
        ["Session / profile", "Daily/sessioned examples", "Crypto 24/7 and 1h tape", "True profile needs session/TPO data contract", "DATASET_SPEC"],
        ["Higher timeframe", "Visual simultaneous chart reading", "PIT availability-gated bars", "Separate source windows and bar-close tests", "MARKET_STATE_CONTRACT"],
    ],
    "cross_cutting_risk_matrix": [
        ["Initial risk", "Risk -> stop -> trade size sequence", "risk_unit + static geometry", "Preserve declared stop distance and sizing order", "LOCKED_INVARIANT"],
        ["Open risk", "Trail/scale/breakeven can transform exposure", "Static stop/target/expiry plus thesis invalidation", "One policy challenger at a time", "OPEN_QUESTION"],
        ["Portfolio risk", "Practitioner account framing", "max_heat, cluster heat, one active exposure per instrument/direction", "No Expert-count cap or confidence sizing", "LOCKED_INVARIANT"],
        ["Tail/execution risk", "Stop does not promise a price", "Gap/cost/funding policy bound to simulator", "Do not equate stop level with maximum realized loss", "LOCKED_INVARIANT"],
        ["Dynamic sizing", "Book discusses compounding asymmetry", "Fixed deterministic baseline", "Risk-policy study only; no online mutation", "OPEN_QUESTION"],
    ],
    "implementation_delta_register": [
        {"id": "DELTA-01", "scope": "multi_degree_context_v1", "owner": "MARKET_STATE_CONTRACT / schema.py / marketstate.py", "change": "new versioned state features with source-window event ids and null policy", "migration": "feature graph/state lineage hash changes; existing Experts remain untouched", "tests": "PIT higher-bar close, warmup, revision replay, hash determinism", "status": "PROPOSED"},
        {"id": "DELTA-02", "scope": "participation_price_action_v1", "owner": "MARKET_STATE_CONTRACT / schema.py / marketstate.py", "change": "relative volume, range ratio, close location and quadrant fields", "migration": "new feature graph version; no numeric imputation", "tests": "trailing-only windows, zero range/volume, lineage and future rejection", "status": "PROPOSED"},
        {"id": "DELTA-03", "scope": "compression_breakout", "owner": "EXPERT_PROTOCOL / EXPERTS_REGISTRY / new expert module after registry decision", "change": "new challenger family with frozen consolidation anchor", "migration": "new expert/version and episode key; no v8_slice_001 retrofit", "tests": "boundary freeze, delay expiry, dedup, closed-bar trigger, simulation goldens", "status": "PROPOSED"},
        {"id": "DELTA-04", "scope": "failed_breakout_reentry_v2", "owner": "EXPERT_PROTOCOL / registry", "change": "explicit excursion and reclaim events", "migration": "new version or separate Expert, subject to independently-falsifiable family decision", "tests": "no-excursion negative fixture, anchor stability, long/short symmetry, gap semantics", "status": "PROPOSED"},
        {"id": "DELTA-05", "scope": "expected_response_v1", "owner": "CANDIDATE_LIFECYCLE_SPEC / SIMULATION_TRUTH_SPEC", "change": "Expert-owned expected-response metadata; initially EXIT_ALL only", "migration": "existing STATIC_V1 policy byte-identical", "tests": "event order, endpoint label, funding, same-bar, full/window replay", "status": "DEFERRED pending O-013"},
    ],
    "source_register": SOURCES,
}


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def tag(text: str) -> str:
    return f'<span class="tag">{esc(text)}</span>'


def bullets(items: list[str]) -> str:
    return '<ul>' + ''.join(f'<li>{esc(x)}</li>' for x in items) + '</ul>'


def table(headers: list[str], rows: list[list[str]]) -> str:
    head = ''.join(f'<th>{esc(x)}</th>' for x in headers)
    body = ''.join('<tr>' + ''.join(f'<td>{x}</td>' for x in row) + '</tr>' for row in rows)
    return f'<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'


def source_link(source: dict) -> str:
    title = esc(source['title'])
    return f'<a href="{esc(source["url"])}">{title}</a>' if source.get('url') else title


def render_deep_dive(d: dict) -> str:
    evidence = ''.join(
        '<article class="evidence">'
        f'<h4>{esc(e["locator"])}</h4>'
        f'<p><strong>Exact locator:</strong> book pp. {esc(e["book_pages"])}, PDF pp. {esc(e["pdf_pages"])}.</p>'
        f'<p>{esc(e["evidence"])}</p><p class="visual"><strong>Figure reading:</strong> {esc(e["visual_note"])}</p>'
        '</article>' for e in d['exact_evidence'])
    forms = ''.join(
        '<article class="formalization">'
        f'<h4>{tag(f["label"])} {esc(f["id"])} — {esc(f["name"])}</h4>'
        f'<p>{esc(f["definition"])}</p><p><strong>Parameters:</strong> {esc(f["parameters"])}</p>'
        f'<p class="muted">{esc(f["book_relation"])}</p></article>' for f in d['alternative_formalizations'])
    contract = table(['Contract field', 'Draft specification'], [[esc(k), esc(v)] for k, v in d['proposed_contract'].items()])
    experiment = table(['Experiment field', 'Draft specification'], [[esc(k), esc(v)] for k, v in d['experiment'].items()])
    return ''.join([
        f'<section class="deep" id="{esc(d["id"].lower())}">',
        f'<h2>{esc(d["id"])} — {esc(d["title"])}</h2>',
        f'<p>{tag(d["priority"])} {tag(d["evidence_label"])} {tag(d["decision"])}</p>',
        '<h3>1. Kaynak argümanı</h3>', bullets(d['source_argument']),
        '<h3>2–3. Exact evidence spans ve figure analizi</h3>', evidence,
        '<h3>4. Koşullar, istisnalar ve karşı örnekler</h3>', bullets(d['conditions_and_exceptions']),
        f'<h3>5. Mekanizma hipotezi</h3><p>{esc(d["mechanism_hypothesis"])}</p>',
        f'<h3>6–7. Mevcut V8 ve eksik kabiliyet</h3><p><strong>Mevcut:</strong> {esc(d["existing_v8_behavior"])}</p><p><strong>Eksik:</strong> {esc(d["missing_v8_capability"])}</p>',
        '<h3>8. Alternatif formalizasyonlar</h3>', forms,
        '<h3>9. Önerilen contract</h3>', contract,
        '<h3>10. Experiment specification</h3>', experiment,
        '<h3>11. Riskler ve karşı argümanlar</h3>', bullets(d['risks']),
        f'<h3>12. Nihai öneri</h3><p>{esc(d["recommendation"])}</p></section>',
    ])


def render_html(report: dict) -> str:
    taxonomy_rows = [[esc(x['id']), esc(x['family']), esc(x['sub_strategies']), esc(x['v8_classification']), esc(x['status'])] for x in report['strategy_taxonomy']]
    execution_rows = [[esc(c) for c in row] for row in report['cross_cutting_execution_matrix']]
    risk_rows = [[esc(c) for c in row] for row in report['cross_cutting_risk_matrix']]
    delta_rows = [[esc(d[k]) for k in ('id', 'scope', 'change', 'migration', 'tests', 'status')] for d in report['implementation_delta_register']]
    source_rows = [[esc(s['id']), source_link(s), esc(s.get('role', s.get('location', '')))] for s in report['source_register']]
    deep = ''.join(render_deep_dive(d) for d in report['deep_dives'])
    legend = table(['Etiket', 'Anlam'], [[tag(k), esc(v)] for k, v in report['provenance_legend'].items()])
    css = '''
@page{margin:18mm} body{max-width:1120px;margin:auto;padding:28px 48px;background:#fffdf9;color:#181818;font:15px/1.58 Georgia,serif} h1,h2,h3,h4,th{font-family:Arial,sans-serif} h1{font-size:1.9rem;margin:3rem 0 1rem;border-bottom:2px solid #333;padding-bottom:.35rem} h2{font-size:1.4rem;margin-top:2.7rem} h3{font-size:1.08rem;margin-top:1.65rem} h4{font-size:.96rem;margin:.2rem 0 .5rem} a{color:#154c78} table{border-collapse:collapse;width:100%;font:12px/1.4 Arial,sans-serif;margin:1rem 0 1.5rem} th,td{border:1px solid #aaa;padding:.48rem;vertical-align:top;text-align:left} th{background:#ece9e1} .status{border-left:4px solid #333;background:#f0eee8;padding:.85rem 1rem}.tag{display:inline-block;border:1px solid #999;border-radius:3px;padding:.1rem .35rem;margin:.1rem .25rem .1rem 0;font:11px Arial,sans-serif;background:#f4f1ea}.deep{border-top:2px solid #333;padding-top:.5rem}.evidence,.formalization{border-left:3px solid #b4b0a7;background:#f7f4ee;padding:.65rem .85rem;margin:.8rem 0}.formalization{border-left-color:#6d8796;background:#f5f8f9}.visual{color:#364d59}.muted{color:#555}.flow{font:13px ui-monospace,Consolas,monospace;background:#f0eee8;padding:.9rem;white-space:pre-wrap}.toc{columns:2;column-gap:2rem}.toc a{display:block;padding:.14rem 0}@media(max-width:760px){body{padding:18px}.toc{columns:1}table{font-size:11px}}@media print{body{padding:0;font-size:10pt}.deep{break-before:page}a{color:#000;text-decoration:none}}
'''
    toc = ''.join(f'<a href="#{esc(d["id"].lower())}">{esc(d["id"])} — {esc(d["title"])}</a>' for d in report['deep_dives'])
    return f'''<!doctype html><html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{esc(report['title'])}</title><style>{css}</style></head><body>
<header><h1>{esc(report['title'])}</h1><p><strong>Book-derived Expert Catalogue, Mathematical Formalization and V8 Compatibility Specification.</strong></p><p class="status"><strong>{esc(report['status']['v8_status'])}</strong> — economic verdict: <code>{esc(report['status']['economic_verdict'])}</code>. Bu belge bir strateji önerisi, kârlılık iddiası veya execution sertifikası değildir.</p><p>{esc(report['purpose'])}</p></header>
<section><h1>Sonuç ve okuma kuralı</h1><p>{esc(report['audit_finding'])}</p>{bullets(report['non_negotiable_boundaries'])}<pre class="flow">BOOK CONCEPT → FORMALIZATION GAP → EXTERNAL / V8 PROPOSAL → FROZEN EXPERT CONTRACT → PREREGISTERED TEST
       (source fact)       (explicit label)          (no economic claim)</pre></section>
<section><h1>İçindekiler</h1><nav class="toc"><a href="#taxonomy">Türetilmiş strateji taxonomy’si</a><a href="#execution">Execution uyumluluk matrisi</a><a href="#risk">Risk uyumluluk matrisi</a>{toc}<a href="#deltas">Implementation delta register</a><a href="#sources">Kaynak register’ı</a></nav></section>
<section id="taxonomy"><h1>Türetilmiş 8-family taxonomy</h1><p>Bu tablo kitapta var olduğu iddia edilen bir 'sekiz strateji' listesi değildir. Kaynak bölümlerindeki teknikleri V8 ontology’sine ayıran, denetlenebilir bir V8 sentezidir.</p>{table(['ID','Strategy family','Alt dallar','V8 kararı','Durum'], taxonomy_rows)}<h3>Provenance anahtarı</h3>{legend}</section>
<section id="execution"><h1>Execution uyumluluğu</h1>{table(['Alan','Kitaptaki model','Mevcut V8','Karar','Owner'], execution_rows)}</section>
<section id="risk"><h1>Risk ve pozisyon yönetimi uyumluluğu</h1>{table(['Alan','Kitaptaki model','Mevcut V8','Karar','Evidence'], risk_rows)}</section>
<section id="dives"><h1>Beş derin dalış</h1><p>Her dalış, kaynak metni ve figürünü ayrı locatorda tutar; formülün kökenini açıkça etiketler; mevcut V8 davranışıyla öneriyi karıştırmaz.</p>{deep}</section>
<section id="deltas"><h1>Implementation delta register</h1><p>Bu tablo bir patch değildir. Normatif doküman veya runtime değişikliği bu raporla yetkilendirilmez; ilgili karar kaydı, preregistration ve contract testleri gerekir.</p>{table(['ID','Scope','Change','Hash / compatibility','Required tests','Status'], delta_rows)}</section>
<section id="sources"><h1>Kaynak register’ı</h1>{table(['ID','Kaynak','Sınır / rol'], source_rows)}<p class="muted">Üretim tarihi: {esc(report['created_utc'])}. Ham veri: <code>research/handbook_v8_deep_research.json</code>. HTML kendi şemalarını kullanır; telifli kitap figürleri gömülmez, yalnızca figure locator ve bağımsız analitik not bulunur.</p></section>
</body></html>'''


def main() -> None:
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(REPORT, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_HTML.write_text(render_html(REPORT), encoding="utf-8")
    print(f"wrote {OUT_JSON} and {OUT_HTML}; deep_dives={len(DEEP_DIVES)} taxonomy={len(TAXONOMY)}")


if __name__ == "__main__":
    main()
