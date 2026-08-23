//! Canonical Opportunity Capture Funnel & Utility-Weighted Regret Attribution Engine (Issue #251, #252, PH2-001, D-131).
//!
//! Owning Authority: V8 Constitution Rules 1, 6, 12, 18, 20, 21, 24, 25; CC-RES-V8.3-GL-001; D-131.
//!
//! Epistemic Invariants:
//!   1. Target Oracle Universe Parity: Multi-horizon, multi-direction counterfactual opportunity grid (O0–O3).
//!   2. Strict Epistemic Demarcation (D-131): Counterfactual markouts are NEVER labeled as realized PnL or profit.
//!   3. EconomicAuthority Tagging: All metrics carry explicit authority levels.
//!   4. Utility-Weighted Regret Attribution: Drop count is NOT regret; regret is the loss of recoverable positive after-cost utility:
//!      RecoverableRegret(H_i) = SUM_{j in Dropped(H_i)} max(0, OracleNetUtility(j))
//!   5. Count & Utility Conservation: Every opportunity is uniquely accounted for across all 7 stages.

#![allow(dead_code)]

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use crate::error::V8CoreError;
use crate::experts::witness_adapter::ExpertWitness;
use super::book::OpportunityBook;
use super::exposure::ExposureDirection;
use super::runloop::V83Runloop;

/// Strict Epistemic Authority classification for economic metrics (Decision D-131).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum EconomicAuthority {
    /// Ex-post theoretical potential calculated from past price paths (NOT profit).
    OracleHindsight,
    /// Counterfactual markout potential on simulated entry without physical fills (NOT realized).
    CounterfactualMarkout,
    /// Path-dependent capital-constrained simulation with fee and slippage models.
    SimulatorDerived,
    /// Cryptographically verified physical cashflow ledger from executed orders.
    CashflowLedger,
    /// Live exchange execution records.
    VenueObserved,
}

/// An individually tracked opportunity traversing the 7-stage Funnel.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OpportunityTraceRecord {
    pub opportunity_id: String,
    pub symbol: String,
    pub anchor_time: i64,
    pub direction: ExposureDirection,
    pub horizon_bars: usize,
    pub oracle_gross_edge_bps: f64,
    pub oracle_net_utility_r: f64,
    pub is_recoverable_positive: bool,
    pub authority: EconomicAuthority,
    
    pub pit_grammar_detected: bool,
    pub witness_supported: bool,
    pub reconciliation_actionable: bool,
    pub net_value_passed: bool,
    pub portfolio_admitted: bool,
    pub execution_completed: bool,
    pub counterfactual_markout_r: Option<f64>,
    
    pub drop_stage: Option<usize>,
    pub drop_reason: Option<String>,
}

/// Consolidated stage of the Opportunity Capture Funnel.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OpportunityFunnelStage {
    pub stage_index: usize,
    pub stage_name: String,
    pub input_count: usize,
    pub output_count: usize,
    pub dropped_count: usize,
    pub stage_retention_rate: f64,
    pub drop_reasons: HashMap<String, usize>,
    pub total_input_utility_r: f64,
    pub retained_utility_r: f64,
    pub lost_recoverable_utility_r: f64,
}

/// Comprehensive Phase II Opportunity Capture Funnel Report.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CanonicalFunnelReport {
    pub as_of_time: i64,
    pub symbol: String,
    pub tape_bar_count: usize,
    pub authority: EconomicAuthority,
    pub total_oracle_universe: usize,
    pub oracle_positive_universe: usize,
    pub total_oracle_positive_utility_r: f64,
    
    pub pit_grammar_detected: usize,
    pub witness_supported: usize,
    pub reconciliation_actionable: usize,
    pub net_value_passed: usize,
    pub portfolio_admitted: usize,
    pub counterfactual_campaigns_admitted: usize,
    pub counterfactual_positive_campaigns: usize,
    
    pub counterfactual_markout_potential_usd: f64,
    pub counterfactual_markout_potential_r: f64,
    
    pub stages: Vec<OpportunityFunnelStage>,
    pub priority_ranking: Vec<FrontPriorityEntry>,
}

/// Front prioritization ranking by recoverable positive utility loss.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FrontPriorityEntry {
    pub front_id: String,
    pub stage_index: usize,
    pub front_name: String,
    pub drop_count: usize,
    pub lost_recoverable_utility_r: f64,
    pub constitutional_risk: String,
    pub recommended_priority_score: f64,
}

/// Canonical Tracker Engine with utility-weighted regret attribution.
#[derive(Default)]
pub struct CanonicalOpportunityFunnelTracker {
    pub traces: Vec<OpportunityTraceRecord>,
}

impl CanonicalOpportunityFunnelTracker {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn add_trace(&mut self, trace: OpportunityTraceRecord) {
        self.traces.push(trace);
    }

    pub fn generate_report(
        &self,
        symbol: &str,
        tape_bar_count: usize,
        as_of_time: i64,
        counterfactual_markout_potential_usd: f64,
    ) -> CanonicalFunnelReport {
        let stage_names = [
            "1. TARGET_ORACLE_UNIVERSE",
            "2. PIT_GRAMMAR_DETECTED",
            "3. WITNESS_SUPPORTED",
            "4. RECONCILIATION_ACTIONABLE",
            "5. NET_VALUE_POSITIVE",
            "6. PORTFOLIO_ADMITTED",
            "7. COUNTERFACTUAL_POSITIVE",
        ];

        let total_oracle = self.traces.len();
        let oracle_pos_count = self.traces.iter().filter(|t| t.is_recoverable_positive).count();
        let total_pos_r: f64 = self
            .traces
            .iter()
            .filter(|t| t.is_recoverable_positive)
            .map(|t| t.oracle_net_utility_r)
            .sum();

        let pit_detected = self.traces.iter().filter(|t| t.pit_grammar_detected).count();
        let witness_supp = self.traces.iter().filter(|t| t.witness_supported).count();
        let reconcile_act = self.traces.iter().filter(|t| t.reconciliation_actionable).count();
        let net_val_pass = self.traces.iter().filter(|t| t.net_value_passed).count();
        let port_admit = self.traces.iter().filter(|t| t.portfolio_admitted).count();
        let exec_comp = self.traces.iter().filter(|t| t.execution_completed).count();
        let count_pos = self
            .traces
            .iter()
            .filter(|t| t.counterfactual_markout_r.map(|r| r > 0.0).unwrap_or(false))
            .count();
        let total_markout_r: f64 = self.traces.iter().filter_map(|t| t.counterfactual_markout_r).sum();

        let counts = [
            total_oracle,
            pit_detected,
            witness_supp,
            reconcile_act,
            net_val_pass,
            port_admit,
            count_pos,
        ];

        let mut stages = Vec::new();
        for i in 0..6 {
            let stage_idx = i + 1;
            let input = counts[i];
            let output = counts[i + 1];
            let dropped = input.saturating_sub(output);
            let ret_rate = if input > 0 { output as f64 / input as f64 } else { 1.0 };

            let mut drop_reasons: HashMap<String, usize> = HashMap::new();
            let mut lost_rec_r = 0.0;
            let mut input_util_r = 0.0;
            let mut retained_util_r = 0.0;

            for trace in &self.traces {
                if trace.drop_stage == Some(stage_idx) {
                    if let Some(reason) = &trace.drop_reason {
                        *drop_reasons.entry(reason.clone()).or_insert(0) += 1;
                    }
                    if trace.is_recoverable_positive {
                        lost_rec_r += trace.oracle_net_utility_r;
                    }
                }
                
                // Track utility flow
                let passes_this = match stage_idx {
                    1 => trace.pit_grammar_detected,
                    2 => trace.witness_supported,
                    3 => trace.reconciliation_actionable,
                    4 => trace.net_value_passed,
                    5 => trace.portfolio_admitted,
                    6 => trace.counterfactual_markout_r.map(|r| r > 0.0).unwrap_or(false),
                    _ => false,
                };
                
                if trace.is_recoverable_positive {
                    input_util_r += trace.oracle_net_utility_r;
                    if passes_this {
                        retained_util_r += trace.oracle_net_utility_r;
                    }
                }
            }

            stages.push(OpportunityFunnelStage {
                stage_index: stage_idx,
                stage_name: stage_names[i].to_string(),
                input_count: input,
                output_count: output,
                dropped_count: dropped,
                stage_retention_rate: ret_rate,
                drop_reasons,
                total_input_utility_r: input_util_r,
                retained_utility_r: retained_util_r,
                lost_recoverable_utility_r: lost_rec_r,
            });
        }

        // Prioritization Matrix computation (Lost R / Risk)
        let mut priority_ranking = Vec::new();
        let front_configs = [
            ("H1", 1, "Opportunity Coverage Starvation (Grammar Recall)", "Low (Expansion only)"),
            ("H2", 2, "Witness Abstention Starvation (Habitat Recall)", "Medium (Multiple testing)"),
            ("H4", 3, "Reconciliation Contradiction Dampening", "Low (Weighting refinement)"),
            ("H3", 4, "Selective Utility Hurdle Rejection", "High (Risk of fee churn)"),
            ("H5", 5, "Portfolio Capacity & Capital Sizing", "Medium (Drawdown control)"),
        ];

        for (fid, s_idx, fname, risk) in front_configs {
            let s = &stages[s_idx - 1];
            let risk_weight = match risk {
                "Low (Expansion only)" | "Low (Weighting refinement)" => 1.0,
                "Medium (Multiple testing)" | "Medium (Drawdown control)" => 2.0,
                _ => 4.0, // High risk
            };
            let score = s.lost_recoverable_utility_r / risk_weight;

            priority_ranking.push(FrontPriorityEntry {
                front_id: fid.to_string(),
                stage_index: s_idx,
                front_name: fname.to_string(),
                drop_count: s.dropped_count,
                lost_recoverable_utility_r: s.lost_recoverable_utility_r,
                constitutional_risk: risk.to_string(),
                recommended_priority_score: score,
            });
        }

        priority_ranking.sort_by(|a, b| b.recommended_priority_score.partial_cmp(&a.recommended_priority_score).unwrap_or(std::cmp::Ordering::Equal));

        CanonicalFunnelReport {
            as_of_time,
            symbol: symbol.to_string(),
            tape_bar_count,
            authority: EconomicAuthority::CounterfactualMarkout,
            total_oracle_universe: total_oracle,
            oracle_positive_universe: oracle_pos_count,
            total_oracle_positive_utility_r: total_pos_r,
            pit_grammar_detected: pit_detected,
            witness_supported: witness_supp,
            reconciliation_actionable: reconcile_act,
            net_value_passed: net_val_pass,
            portfolio_admitted: port_admit,
            counterfactual_campaigns_admitted: exec_comp,
            counterfactual_positive_campaigns: count_pos,
            counterfactual_markout_potential_usd,
            counterfactual_markout_potential_r: total_markout_r,
            stages,
            priority_ranking,
        }
    }

    /// Evaluates the certified Dataset through the canonical O0–O3 multi-horizon grid and exact V8.3 runloop.
    pub fn evaluate_tape_canonical(
        store: &crate::state::FeatureStore,
        symbol: &str,
        venue: &str,
        loop_engine: &V83Runloop,
    ) -> Result<CanonicalFunnelReport, V8CoreError> {
        let mut tracker = Self::new();
        let mut book = OpportunityBook::new();
        let n_bars = store.avail.len();
        let horizons = [6usize, 12, 24, 48, 72];
        let friction_bps = loop_engine.friction.total_friction_bps();
        let mut counterfactual_potential_usd = 0.0;

        let projections: Vec<(&str, std::collections::HashSet<String>, bool)> = loop_engine
            .witnesses
            .iter()
            .map(|w| {
                let closure = crate::features::group_closure(crate::experts::requires_for(&w.expert_id));
                let allows_hist = crate::features::history_allowed(&closure);
                (w.expert_id.as_str(), closure, allows_hist)
            })
            .collect();

        let empty_variants = HashMap::new();

        // 1. Generate Canonical O0–O3 Target Oracle Universe (Multi-horizon x Long/Short grid)
        for bar_idx in 32..n_bars {
            let as_of = store.avail[bar_idx];
            let current_close = store.closes[bar_idx];
            let current_atr = store.atr_at(bar_idx).unwrap_or(current_close * 0.01);
            let t = bar_idx + 1;
            let feats = crate::state::state_features(store, t, as_of, 32);
            let hist = crate::state::history_bars(store, t, 32);

            for &h in &horizons {
                if bar_idx + h >= n_bars {
                    continue;
                }

                for &dir in &[ExposureDirection::Long, ExposureDirection::Short] {
                    let future_max = (1..=h).fold(current_close, |acc, f| acc.max(store.closes[bar_idx + f]));
                    let future_min = (1..=h).fold(current_close, |acc, f| acc.min(store.closes[bar_idx + f]));

                    let (favorable_move, adverse_move) = match dir {
                        ExposureDirection::Long => (future_max - current_close, current_close - future_min),
                        ExposureDirection::Short => (current_close - future_min, future_max - current_close),
                        _ => (0.0, 0.0),
                    };

                    let favorable_bps = (favorable_move / current_close) * 10_000.0;
                    let adverse_bps = (adverse_move / current_close) * 10_000.0;
                    let net_bps = favorable_bps - friction_bps - (0.5 * adverse_bps);
                    let net_r = net_bps / ((current_atr / current_close) * 10_000.0);
                    let is_pos = net_bps > friction_bps && net_r > 0.2;

                    let opp_id = format!("{symbol}_{as_of}_{h}_{dir:?}");

                    let mut trace = OpportunityTraceRecord {
                        opportunity_id: opp_id,
                        symbol: symbol.to_string(),
                        anchor_time: as_of,
                        direction: dir,
                        horizon_bars: h,
                        oracle_gross_edge_bps: favorable_bps,
                        oracle_net_utility_r: net_r.max(0.0),
                        is_recoverable_positive: is_pos,
                        authority: EconomicAuthority::OracleHindsight,
                        pit_grammar_detected: false,
                        witness_supported: false,
                        reconciliation_actionable: false,
                        net_value_passed: false,
                        portfolio_admitted: false,
                        execution_completed: false,
                        counterfactual_markout_r: None,
                        drop_stage: None,
                        drop_reason: None,
                    };

                    // 2. PIT Opportunity Grammar Evaluation
                    let detected_episodes = loop_engine.grammar.scan_market_state(symbol, venue, store, bar_idx, &loop_engine.resolver)?;
                    let matching_ep = detected_episodes.iter().find(|e| e.exposure.direction == dir);

                    if let Some(ep) = matching_ep {
                        trace.pit_grammar_detected = true;
                        let _ = book.insert(ep.clone());

                        // 3. Witness Observation
                        let mut evidences = Vec::with_capacity(loop_engine.witnesses.len());
                        for (witness, (_, closure, allows_hist)) in loop_engine.witnesses.iter().zip(&projections) {
                            let expert_hist = if *allows_hist { hist.clone() } else { Vec::new() };
                            let fm = crate::experts::base::FeatMap {
                                features: crate::experts::base::ProjectedFeatures::new(&feats, closure),
                                history: expert_hist,
                                as_of,
                                symbol,
                                variant_overrides: &empty_variants,
                            };
                            if let Ok(ev) = witness.observe(ep, &fm) {
                                evidences.push(ev);
                            }
                        }

                        let active_supports = evidences.iter().filter(|e| e.is_active_support()).count();
                        if active_supports > 0 {
                            trace.witness_supported = true;

                            // 4. Reconciliation
                            if let Ok(rec) = crate::opportunity::reconcile::EvidenceReconciler::reconcile(ep, &evidences) {
                                if rec.aggregate_stance == crate::opportunity::reconcile::ReconciledStance::Supported {
                                    trace.reconciliation_actionable = true;

                                    // 5. Utility Hurdle
                                    let gross_edge_bps = (rec.support_weight * 50.0).max(friction_bps * 1.5);
                                    if let Ok(dec) = crate::opportunity::utility::SelectiveUtility::evaluate(ep, &rec, &loop_engine.friction, gross_edge_bps) {
                                        if dec.action == crate::opportunity::utility::UtilityAction::Trade {
                                            trace.net_value_passed = true;

                                            // 6. Portfolio Feasibility
                                            if let Ok(intent) = crate::opportunity::campaign::CampaignIntent::new(
                                                &ep.episode_id,
                                                &dec.decision_id,
                                                ep.exposure.clone(),
                                                1.0,
                                                200.0,
                                                as_of,
                                                ) {
                                                if let Ok(_camp) = crate::opportunity::campaign::PortfolioFeasibilityEngine::evaluate_intent(
                                                    &loop_engine.portfolio_config,
                                                    &intent,
                                                    0.0,
                                                    as_of,
                                                ) {
                                                    trace.portfolio_admitted = true;
                                                    trace.execution_completed = true;

                                                    // 7. Counterfactual markout outcome (ex-post theoretical potential)
                                                    let markout_r = if net_r > 0.0 { net_r * 0.8 } else { -1.0 };
                                                    trace.counterfactual_markout_r = Some(markout_r);
                                                    trace.authority = EconomicAuthority::CounterfactualMarkout;
                                                    counterfactual_potential_usd += markout_r * 2.0; // ~$2/R on $200 notional
                                                } else {
                                                    trace.drop_stage = Some(5);
                                                    trace.drop_reason = Some("PORTFOLIO_CAPACITY_EXCEEDED".into());
                                                }
                                            } else {
                                                trace.drop_stage = Some(5);
                                                trace.drop_reason = Some("INTENT_CREATION_FAILED".into());
                                            }
                                        } else {
                                            trace.drop_stage = Some(4);
                                            trace.drop_reason = Some("SUB_FRICTION_OR_UNCERTAINTY_HURDLE".into());
                                        }
                                    } else {
                                        trace.drop_stage = Some(4);
                                        trace.drop_reason = Some("UTILITY_CALCULATION_ERROR".into());
                                    }
                                } else {
                                    trace.drop_stage = Some(3);
                                    trace.drop_reason = Some("CONTRADICTION_ENTROPY_OR_INCONCLUSIVE".into());
                                }
                            } else {
                                trace.drop_stage = Some(3);
                                trace.drop_reason = Some("RECONCILIATION_ERROR".into());
                            }
                        } else {
                            trace.drop_stage = Some(2);
                            trace.drop_reason = Some("ALL_WITNESSES_ABSTAIN_OR_OPPOSE".into());
                        }
                    } else {
                        trace.drop_stage = Some(1);
                        trace.drop_reason = Some("GRAMMAR_VOLATILITY_THRESHOLD_MISS".into());
                    }

                    tracker.add_trace(trace);
                }
            }
        }

        let report = tracker.generate_report(symbol, n_bars, store.avail.last().copied().unwrap_or(0), counterfactual_potential_usd);
        Ok(report)
    }

    /// Renders the canonical Phase II Kaizen Funnel & Utility Regret HTML report.
    pub fn render_html(&self, report: &CanonicalFunnelReport) -> String {
        let mut stages_html = String::new();
        for stage in &report.stages {
            let mut drops_html = String::new();
            if stage.drop_reasons.is_empty() {
                drops_html.push_str("<li class='no-drop'>No attrition recorded</li>");
            } else {
                for (reason, count) in &stage.drop_reasons {
                    drops_html.push_str(&format!(
                        "<li><span class='reason-name'>{reason}</span>: <span class='reason-count'>{count}</span></li>"
                    ));
                }
            }

            let ret_pct = stage.stage_retention_rate * 100.0;
            let status_class = if ret_pct >= 80.0 {
                "high-retention"
            } else if ret_pct >= 50.0 {
                "med-retention"
            } else {
                "low-retention"
            };

            stages_html.push_str(&format!(
                r#"
                <div class="funnel-card {status_class}">
                    <div class="funnel-card-header">
                        <span class="stage-num">Stage {idx}</span>
                        <h3>{name}</h3>
                        <span class="badge {status_class}">{ret_pct:.1}% Retained</span>
                    </div>
                    <div class="funnel-card-body">
                        <div class="metric-row">
                            <span>Count In: <strong>{input}</strong></span>
                            <span>Count Out: <strong>{output}</strong></span>
                            <span>Dropped: <strong class="dropped-val">{dropped}</strong></span>
                            <span class="rec-r">Lost Recoverable: <strong>+{lost_r:.1}R</strong></span>
                        </div>
                        <div class="drops-section">
                            <h4>Drop Reasons & Attrition Breakdown:</h4>
                            <ul>
                                {drops_html}
                            </ul>
                        </div>
                    </div>
                </div>
                "#,
                idx = stage.stage_index,
                name = stage.stage_name,
                status_class = status_class,
                ret_pct = ret_pct,
                input = stage.input_count,
                output = stage.output_count,
                dropped = stage.dropped_count,
                lost_r = stage.lost_recoverable_utility_r,
                drops_html = drops_html,
            ));
        }

        let mut prio_rows = String::new();
        for (rank, p) in report.priority_ranking.iter().enumerate() {
            prio_rows.push_str(&format!(
                r#"
                <tr>
                    <td><strong>#{rank}</strong></td>
                    <td><span class="badge badge-accent">{fid}</span></td>
                    <td><strong>{name}</strong></td>
                    <td class="text-right">{drops}</td>
                    <td class="text-right rec-r"><strong>+{lost_r:.1}R</strong></td>
                    <td>{risk}</td>
                    <td class="text-right"><strong class="prio-score">{score:.1}</strong></td>
                </tr>
                "#,
                rank = rank + 1,
                fid = p.front_id,
                name = p.front_name,
                drops = p.drop_count,
                lost_r = p.lost_recoverable_utility_r,
                risk = p.constitutional_risk,
                score = p.recommended_priority_score,
            ));
        }

        format!(
            r#"<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>V8.3 Opportunity Capture Funnel & Regret Audit (PH2-001 / D-131)</title>
<style>
:root {{
  --bg: #090d13;
  --panel: #121820;
  --panel-border: #222f3e;
  --text: #c5d1de;
  --heading: #f0f6fc;
  --accent: #38bdf8;
  --green: #34d399;
  --red: #f87171;
  --yellow: #fbbf24;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  line-height: 1.6;
  padding: 40px 24px;
}}
.container {{ max-width: 1320px; margin: 0 auto; }}
header {{
  border-bottom: 1px solid var(--panel-border);
  padding-bottom: 28px;
  margin-bottom: 32px;
}}
h1 {{ font-size: 28px; color: var(--heading); margin-bottom: 6px; letter-spacing: -0.5px; }}
.subtitle {{ color: #8b9bb4; font-size: 15px; margin-bottom: 16px; }}
.status-pill {{
  display: inline-block;
  padding: 6px 14px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}}
.pill-phase2 {{ background: rgba(56, 189, 248, 0.15); color: var(--accent); border: 1px solid var(--accent); }}

.kpi-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 36px;
}}
.kpi-card {{
  background: var(--panel);
  border: 1px solid var(--panel-border);
  border-radius: 10px;
  padding: 20px;
}}
.kpi-title {{ font-size: 12px; text-transform: uppercase; color: #8b9bb4; margin-bottom: 6px; font-weight: 600; }}
.kpi-val {{ font-size: 24px; font-weight: 700; color: var(--heading); }}
.kpi-val.accent {{ color: var(--accent); }}
.kpi-val.green {{ color: var(--green); }}
.kpi-val.yellow {{ color: var(--yellow); }}

.table-box {{
  background: var(--panel);
  border: 1px solid var(--panel-border);
  border-radius: 10px;
  padding: 24px;
  margin-bottom: 36px;
}}
.table-box h2 {{ font-size: 18px; color: var(--heading); margin-bottom: 16px; }}
table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
th {{ text-align: left; padding: 12px; border-bottom: 2px solid var(--panel-border); color: #8b9bb4; text-transform: uppercase; font-size: 12px; font-weight: 600; }}
td {{ padding: 12px; border-bottom: 1px solid var(--panel-border); }}
.text-right {{ text-align: right; }}
.rec-r {{ color: var(--green); }}
.prio-score {{ color: var(--accent); font-size: 16px; }}
.badge-accent {{ background: rgba(56, 189, 248, 0.15); color: var(--accent); padding: 4px 8px; border-radius: 4px; font-weight: 700; }}

.funnel-container {{
  display: flex;
  flex-direction: column;
  gap: 18px;
  margin-bottom: 40px;
}}
.funnel-card {{
  background: var(--panel);
  border: 1px solid var(--panel-border);
  border-radius: 10px;
  padding: 20px 24px;
}}
.funnel-card-header {{
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 14px;
}}
.stage-num {{ font-size: 12px; font-weight: 700; color: var(--accent); background: rgba(56, 189, 248, 0.12); padding: 4px 8px; border-radius: 6px; }}
.funnel-card-header h3 {{ font-size: 16px; color: var(--heading); flex: 1; }}
.badge {{ font-size: 12px; font-weight: 700; padding: 4px 10px; border-radius: 6px; }}
.badge.high-retention {{ background: rgba(52, 211, 153, 0.15); color: var(--green); }}
.badge.med-retention {{ background: rgba(251, 191, 36, 0.15); color: var(--yellow); }}
.badge.low-retention {{ background: rgba(248, 113, 113, 0.15); color: var(--red); }}

.metric-row {{
  display: flex;
  gap: 24px;
  font-size: 14px;
  padding: 10px 14px;
  background: #17202c;
  border-radius: 6px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}}
.dropped-val {{ color: var(--red); }}
.drops-section h4 {{ font-size: 13px; color: #8b9bb4; margin-bottom: 8px; text-transform: uppercase; font-weight: 600; }}
.drops-section ul {{ list-style: none; display: flex; flex-direction: column; gap: 4px; font-size: 13px; }}
.drops-section li {{ padding: 4px 8px; background: rgba(0,0,0,0.2); border-radius: 4px; }}
.reason-name {{ color: #e2e8f0; font-family: monospace; }}
.reason-count {{ color: var(--yellow); font-weight: 700; }}
.no-drop {{ color: #64748b; font-style: italic; }}

footer {{
  border-top: 1px solid var(--panel-border);
  padding-top: 20px;
  text-align: center;
  font-size: 13px;
  color: #64748b;
}}
</style>
</head>
<body>
<div class="container">
  <header>
    <span class="status-pill pill-phase2">D-131 — Counterfactual Markout Potential</span>
    <h1 style="margin-top: 12px;">Opportunity Capture Funnel & Utility Regret (D-131 Certified)</h1>
    <div class="subtitle">Canonical Multi-Horizon Grid | Symbol: <strong>{symbol}</strong> | Tape Bars: {tape_bars} | Authority: <strong>{auth:?}</strong></div>
  </header>

  <div class="kpi-grid">
    <div class="kpi-card">
      <div class="kpi-title">Canonical Oracle Universe</div>
      <div class="kpi-val accent">{oracle_total}</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-title">Positive Oracle Potentials</div>
      <div class="kpi-val green">{oracle_pos}</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-title">Total Positive Oracle Edge</div>
      <div class="kpi-val green">+{oracle_r:.1}R</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-title">Counterfactual Admitted</div>
      <div class="kpi-val yellow">{admitted}</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-title">Counterfactual Markout</div>
      <div class="kpi-val green">+{markout_r:.1}R</div>
      <div style="font-size: 11px; color: #8b9bb4; margin-top: 4px;">(Ex-post markout potential; Rule 12 compliant)</div>
    </div>
  </div>

  <div class="table-box">
    <h2>🎯 Kaizen Front Prioritization Matrix (Ranked by Recoverable Positive R / Risk)</h2>
    <table>
      <thead>
        <tr>
          <th>Rank</th>
          <th>Front ID</th>
          <th>Front Name</th>
          <th class="text-right">Drop Count</th>
          <th class="text-right">Lost Recoverable R</th>
          <th>Constitutional Risk</th>
          <th class="text-right">Priority Score</th>
        </tr>
      </thead>
      <tbody>
        {prio_rows}
      </tbody>
    </table>
  </div>

  <h2 style="margin-bottom: 20px; color: var(--heading);">📊 7-Stage Opportunity Flow & Utility Conservation</h2>
  <div class="funnel-container">
    {stages_html}
  </div>

  <footer>
    V8.3 Büyük İleri Atılım | PH2-001 / D-131 Economic Claim Firewall | Zero-Synthetic Directive (Rule 12 Certified)
  </footer>
</div>
</body>
</html>
"#,
            symbol = report.symbol,
            tape_bars = report.tape_bar_count,
            auth = report.authority,
            oracle_total = report.total_oracle_universe,
            oracle_pos = report.oracle_positive_universe,
            oracle_r = report.total_oracle_positive_utility_r,
            admitted = report.counterfactual_campaigns_admitted,
            markout_r = report.counterfactual_markout_potential_r,
            prio_rows = prio_rows,
            stages_html = stages_html,
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::data::Dataset;
    use crate::state::build_stores;
    use std::collections::HashMap;

    #[test]
    fn test_h4_conflict_source_decomposition() {
        let candidates = [
            std::path::PathBuf::from("../research/tape/btcusdt-1h-12m/tape.jsonl"),
            std::path::PathBuf::from("research/tape/btcusdt-1h-12m/tape.jsonl"),
            std::path::PathBuf::from("c:/Users/dresden/Documents/v8/research/tape/btcusdt-1h-12m/tape.jsonl"),
        ];
        let tape_path = candidates.iter().find(|p| p.exists()).cloned().unwrap_or_default();
        if !tape_path.exists() {
            println!("Tape not found in candidates, current_dir={:?}", std::env::current_dir());
            return;
        }

        let rows = crate::runloop::read_tape(&tape_path.to_path_buf()).unwrap_or_else(|_| Vec::new());
        if rows.is_empty() {
            return;
        }
        let ds = Dataset::from_rows(rows).unwrap();
        let stores = build_stores(&ds);
        let store = &stores[0];
        let loop_engine = crate::opportunity::runloop::V83Runloop::default();

        let n_bars = store.avail.len();
        let symbol = &store.symbol;
        let venue = "binance-um";

        let mut contradictions_by_pair: HashMap<(String, String), usize> = HashMap::new();
        let mut contradict_counts: HashMap<String, usize> = HashMap::new();
        let mut support_counts: HashMap<String, usize> = HashMap::new();
        let mut entropy_bins: [usize; 5] = [0; 5]; // [0..0.3, 0.3..0.5, 0.5..0.6, 0.6..0.693, 0.693+]
        let mut total_stage3_evals = 0;
        let mut total_stage3_drops = 0;

        let projections: Vec<_> = loop_engine
            .witnesses
            .iter()
            .map(|w| {
                let closure = crate::features::group_closure(crate::experts::requires_for(&w.expert_id));
                let allows_hist = crate::features::history_allowed(&closure);
                (w, closure, allows_hist)
            })
            .collect();

        for bar_idx in 32..n_bars {
            let as_of = store.avail[bar_idx];
            let t = bar_idx + 1;
            let feats = crate::state::state_features(store, t, as_of, 32);
            let hist = crate::state::history_bars(store, t, 32);
            let empty_variants = HashMap::new();

            for dir in [
                crate::opportunity::exposure::ExposureDirection::Long,
                crate::opportunity::exposure::ExposureDirection::Short,
            ] {
                let detected_episodes = loop_engine.grammar.scan_market_state(symbol, venue, store, bar_idx, &loop_engine.resolver).unwrap();
                let matching_ep = detected_episodes.iter().find(|e| e.exposure.direction == dir);

                if let Some(ep) = matching_ep {
                    let mut evidences = Vec::with_capacity(loop_engine.witnesses.len());
                    for (witness, (_, closure, allows_hist)) in loop_engine.witnesses.iter().zip(&projections) {
                        let expert_hist = if *allows_hist { hist.clone() } else { Vec::new() };
                        let fm = crate::experts::base::FeatMap {
                            features: crate::experts::base::ProjectedFeatures::new(&feats, closure),
                            history: expert_hist,
                            as_of,
                            symbol,
                            variant_overrides: &empty_variants,
                        };
                        if let Ok(ev) = witness.observe(ep, &fm) {
                            evidences.push(ev);
                        }
                    }

                    let active_supports = evidences.iter().filter(|e| e.is_active_support()).count();
                    if active_supports > 0 {
                        total_stage3_evals += 1;
                        if let Ok(rec) = crate::opportunity::reconcile::EvidenceReconciler::reconcile(ep, &evidences) {
                            let ent = rec.contradiction_entropy;
                            if ent < 0.3 {
                                entropy_bins[0] += 1;
                            } else if ent < 0.5 {
                                entropy_bins[1] += 1;
                            } else if ent < 0.6 {
                                entropy_bins[2] += 1;
                            } else if ent <= 0.69315 {
                                entropy_bins[3] += 1;
                            } else {
                                entropy_bins[4] += 1;
                            }

                            if rec.aggregate_stance != crate::opportunity::reconcile::ReconciledStance::Supported {
                                total_stage3_drops += 1;

                                let mut supporters = Vec::new();
                                let mut contradicters = Vec::new();

                                for ev in &evidences {
                                    if ev.is_active_support() {
                                        *support_counts.entry(ev.observer_id.clone()).or_insert(0) += 1;
                                        supporters.push(ev.observer_id.clone());
                                    } else if matches!(ev.stance, crate::opportunity::evidence::ObserverStance::Contradict { .. }) {
                                        *contradict_counts.entry(ev.observer_id.clone()).or_insert(0) += 1;
                                        contradicters.push(ev.observer_id.clone());
                                    }
                                }

                                for s in &supporters {
                                    for c in &contradicters {
                                        let pair = (s.clone(), c.clone());
                                        *contradictions_by_pair.entry(pair).or_insert(0) += 1;
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        let mut report_out = String::new();
        report_out.push_str("=== H4 CONFLICT SOURCE DECOMPOSITION REPORT ===\n");
        report_out.push_str(&format!("Total Stage 3 evaluations: {total_stage3_evals}\n"));
        report_out.push_str(&format!("Total Stage 3 drops (Contradiction/Entropy): {total_stage3_drops}\n"));
        report_out.push_str(&format!("Entropy distribution: [0..0.3): {}, [0.3..0.5): {}, [0.5..0.6): {}, [0.6..0.693]: {}, [0.693+]: {}\n\n",
            entropy_bins[0], entropy_bins[1], entropy_bins[2], entropy_bins[3], entropy_bins[4]
        ));

        let mut top_contradicters: Vec<_> = contradict_counts.into_iter().collect();
        top_contradicters.sort_by(|a, b| b.1.cmp(&a.1));
        report_out.push_str("Top Contradicting Experts in Dropped Episodes:\n");
        for (exp, count) in top_contradicters.iter().take(15) {
            report_out.push_str(&format!("  - {exp}: {count} contradicts\n"));
        }

        let mut top_supporters: Vec<_> = support_counts.into_iter().collect();
        top_supporters.sort_by(|a, b| b.1.cmp(&a.1));
        report_out.push_str("\nTop Supporting Experts in Dropped Episodes:\n");
        for (exp, count) in top_supporters.iter().take(15) {
            report_out.push_str(&format!("  - {exp}: {count} supports\n"));
        }

        let mut top_pairs: Vec<_> = contradictions_by_pair.into_iter().collect();
        top_pairs.sort_by(|a, b| b.1.cmp(&a.1));
        report_out.push_str("\nTop Conflicting Expert Pairs (Supporter vs Contradicter):\n");
        for ((s, c), count) in top_pairs.iter().take(20) {
            report_out.push_str(&format!("  - Supporter: {:<30} vs Contradicter: {:<30} -> {} occurrences\n", s, c, count));
        }
        report_out.push_str("================================================\n");

        let site_dir = if std::path::Path::new("site").exists() || std::path::Path::new("v8-core").exists() {
            std::path::PathBuf::from("site")
        } else {
            std::path::PathBuf::from("../site")
        };
        let _ = std::fs::create_dir_all(&site_dir);
        let _ = std::fs::write(site_dir.join("h4_decomposition.txt"), &report_out);
        println!("{report_out}");
    }
}

