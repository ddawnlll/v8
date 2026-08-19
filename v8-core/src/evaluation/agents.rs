//! V8 Evaluation Evidence System — Scout -> Investigator -> Decision Agent Harness (v8.eval.v1 §13, §18, §24).
//!
//! Autonomous multi-agent scientific investigation pipeline in pure Rust.

#![allow(dead_code)]

use serde::{Deserialize, Serialize};
use std::fs;
use std::io::{self, Write};
use std::path::Path;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct HypothesisRecord {
    pub hypothesis_id: String,
    pub parent_hypothesis: Option<String>,
    pub created_by: String,
    pub created_at_run: String,
    pub status: String,
    pub claim: String,
    pub preregistered_test: serde_json::Value,
    pub evidence_for: Vec<String>,
    pub evidence_against: Vec<String>,
    pub falsification_criterion: String,
    pub derived_challengers: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct FindingRecord {
    pub finding_id: String,
    pub scope: serde_json::Value,
    pub claim: String,
    pub epistemic_status: String,
    pub severity: String,
    pub confidence: f64,
    pub observations: Vec<String>,
    pub statistical_evidence: serde_json::Value,
    pub alternative_explanations: Vec<String>,
    pub falsifiers: Vec<String>,
    pub supporting_artifacts: Vec<String>,
    pub recommended_next_test: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct AnomalyRecord {
    pub anomaly_id: String,
    pub category: String,
    pub subcategory: String,
    pub description: String,
    pub severity: String,
    pub affected_cohort: serde_json::Value,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct RecommendationRecord {
    pub recommendation_id: String,
    pub title: String,
    pub rationale: String,
    pub target_expert: String,
    pub proposed_parameter_patch: serde_json::Value,
    pub expected_improvement_r: f64,
}

pub fn run_triage_agent(
    setups_triggered: usize,
    vetoed_risk_capacity: usize,
    n_trades: usize,
    n_stop_too_tight: usize,
    n_bad_entry: usize,
) -> Vec<AnomalyRecord> {
    let mut anomalies = Vec::new();
    let mut idx = 1;

    // 1. Veto rate anomaly
    if setups_triggered > 10 && (vetoed_risk_capacity as f64 / setups_triggered as f64) > 0.90 {
        anomalies.push(AnomalyRecord {
            anomaly_id: format!("A-{idx:04}"),
            category: "ADMISSION".to_string(),
            subcategory: "exposure_conflict_block".to_string(),
            description: format!(
                "Extreme admission veto rate ({vetoed_risk_capacity}/{setups_triggered} = {:.1}%)",
                (vetoed_risk_capacity as f64 / setups_triggered as f64) * 100.0
            ),
            severity: "HIGH".to_string(),
            affected_cohort: serde_json::json!({"funnel": "S5_VETO"}),
        });
        idx += 1;
    }

    // 2. Stop too tight path anomaly
    if n_trades > 0 && (n_stop_too_tight as f64 / n_trades as f64) > 0.20 {
        anomalies.push(AnomalyRecord {
            anomaly_id: format!("A-{idx:04}"),
            category: "EXIT".to_string(),
            subcategory: "stop_too_tight".to_string(),
            description: format!(
                "{n_stop_too_tight}/{n_trades} ({:.1}%) trades hit SL then reached >= +1.0R post-stop MFE",
                (n_stop_too_tight as f64 / n_trades as f64) * 100.0
            ),
            severity: "HIGH".to_string(),
            affected_cohort: serde_json::json!({"metric": "post_exit_mfe_r"}),
        });
        idx += 1;
    }

    // 3. Bad entry path anomaly
    if n_trades > 0 && (n_bad_entry as f64 / n_trades as f64) > 0.25 {
        anomalies.push(AnomalyRecord {
            anomaly_id: format!("A-{idx:04}"),
            category: "SIGNAL".to_string(),
            subcategory: "directional_inversion".to_string(),
            description: format!(
                "{n_bad_entry}/{n_trades} ({:.1}%) trades suffered immediate MAE with zero favorable movement",
                (n_bad_entry as f64 / n_trades as f64) * 100.0
            ),
            severity: "MEDIUM".to_string(),
            affected_cohort: serde_json::json!({"metric": "time_to_mae"}),
        });
        idx += 1;
    }

    // 4. Sample size
    if n_trades < 30 {
        anomalies.push(AnomalyRecord {
            anomaly_id: format!("A-{idx:04}"),
            category: "STATISTICS".to_string(),
            subcategory: "insufficient_sample_n".to_string(),
            description: format!("Low trade sample size (N={n_trades} < 30) limits statistical confidence"),
            severity: "MEDIUM".to_string(),
            affected_cohort: serde_json::json!({"total_trades": n_trades}),
        });
    }

    anomalies
}

pub fn run_scout_agents(
    run_id: &str,
    anomalies: &[AnomalyRecord],
) -> Vec<HypothesisRecord> {
    let mut hypotheses = Vec::new();
    let mut idx = 1;

    for a in anomalies {
        if a.subcategory == "stop_too_tight" {
            hypotheses.push(HypothesisRecord {
                hypothesis_id: format!("H-{idx:04}"),
                parent_hypothesis: None,
                created_by: "agent:scout-exit-paths".to_string(),
                created_at_run: run_id.to_string(),
                status: "PROPOSED".to_string(),
                claim: "Current stop-loss geometry truncates positive trade trajectories prematurely.".to_string(),
                preregistered_test: serde_json::json!({
                    "cohort_filter": "path_classification == 'STOP_TOO_TIGHT'",
                    "counterfactual_variant": "stop_multiplier = 1.5",
                    "primary_metric": "net_expectancy_R",
                    "required_n": 20,
                    "significance_threshold_p": 0.05
                }),
                evidence_for: vec![a.description.clone()],
                evidence_against: vec![],
                falsification_criterion: "Effect must hold with bootstrap p < 0.05 on out-of-sample partition.".to_string(),
                derived_challengers: vec![format!("EXP-CHALLENGER-STOP-WIDER-{idx:03}")],
            });
            idx += 1;
        } else if a.subcategory == "exposure_conflict_block" {
            hypotheses.push(HypothesisRecord {
                hypothesis_id: format!("H-{idx:04}"),
                parent_hypothesis: None,
                created_by: "agent:scout-engine-data".to_string(),
                created_at_run: run_id.to_string(),
                status: "PROPOSED".to_string(),
                claim: "High capacity saturation / existing exposure blocks potentially profitable setups.".to_string(),
                preregistered_test: serde_json::json!({
                    "cohort_filter": "veto_stage == 'RISK_GATE'",
                    "counterfactual_variant": "max_cluster_heat = 2.0",
                    "primary_metric": "portfolio_net_R",
                    "required_n": 50,
                    "significance_threshold_p": 0.05
                }),
                evidence_for: vec![a.description.clone()],
                evidence_against: vec![],
                falsification_criterion: "Portfolio drawdown must not exceed 2x under relaxed heat.".to_string(),
                derived_challengers: vec![format!("EXP-CHALLENGER-HEAT-RELAX-{idx:03}")],
            });
            idx += 1;
        }
    }

    hypotheses
}

pub fn run_investigator_agents(
    hypotheses: &[HypothesisRecord],
    n_trades: usize,
    n_stop_too_tight: usize,
    bootstrap_p_val: f64,
    stop_too_tight_mean_mfe: Option<f64>,
) -> Vec<FindingRecord> {
    let mut findings = Vec::new();
    let mut idx = 1;

    for h in hypotheses {
        if h.claim.contains("stop-loss geometry") {
            let stt_ratio = if n_trades > 0 { n_stop_too_tight as f64 / n_trades as f64 } else { 0.0 };
            let supported = stt_ratio > 0.15 && n_stop_too_tight >= 5;
            let sample_confidence = if n_trades >= 30 { 0.70 } else { (n_trades as f64 / 30.0) * 0.50 };

            findings.push(FindingRecord {
                finding_id: format!("F-{idx:04}"),
                scope: serde_json::json!({"expert": "all", "component": "exit_geometry"}),
                claim: h.claim.clone(),
                epistemic_status: if supported { "SUPPORTED_DIAGNOSTIC" } else { "INSUFFICIENT_EVIDENCE" }.to_string(),
                severity: if supported { "MEDIUM" } else { "LOW" }.to_string(),
                confidence: if supported { sample_confidence } else { 0.20 },
                observations: vec![
                    format!("{n_stop_too_tight}/{n_trades} ({:.1}%) trades satisfied STOP_TOO_TIGHT criteria.", stt_ratio * 100.0),
                    format!("Bootstrap p-value: {:.4}.", bootstrap_p_val),
                ],
                statistical_evidence: serde_json::json!({
                    "n": n_trades,
                    "n_affected": n_stop_too_tight,
                    "stt_ratio": stt_ratio,
                    "bootstrap_p_value": bootstrap_p_val,
                    "post_exit_mfe_r": stop_too_tight_mean_mfe,
                }),
                alternative_explanations: vec![
                    "High volatility regime expansion after trade exit.".to_string(),
                    "Intrabar high/low touch ordering ambiguity.".to_string(),
                ],
                falsifiers: vec![
                    "Effect vanishes under pessimistic intrabar barrier ordering.".to_string(),
                    "Effect fails to replicate on OOS partition.".to_string(),
                ],
                supporting_artifacts: vec![
                    "statistics/bootstrap.json".to_string(),
                    "analysis/anomalies.jsonl".to_string(),
                ],
                recommended_next_test: h.derived_challengers.first().cloned().unwrap_or_else(|| "RETEST".to_string()),
            });
            idx += 1;
        }
    }

    findings
}

pub fn run_decision_agent(
    findings: &[FindingRecord],
) -> Vec<RecommendationRecord> {
    let mut recs = Vec::new();
    let mut idx = 1;

    for f in findings {
        if f.epistemic_status == "SUPPORTED_DIAGNOSTIC" && f.claim.contains("stop") {
            recs.push(RecommendationRecord {
                recommendation_id: format!("REC-{idx:04}"),
                title: "Widen stop multiplier by 1.5x on high-volatility setups (Candidate Challenger)".to_string(),
                rationale: format!("Supported by Diagnostic Finding {}: {}", f.finding_id, f.observations.first().cloned().unwrap_or_default()),
                target_expert: "all".to_string(),
                proposed_parameter_patch: serde_json::json!({"stop_multiplier": 1.5}),
                expected_improvement_r: 0.0, // Zero until formal counterfactual rerun is executed (Constitution Rule 12)
            });
            idx += 1;
        }
    }

    recs
}

pub fn save_jsonl<T: Serialize>(records: &[T], path: &Path) -> io::Result<()> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    let mut file = fs::File::create(path)?;
    for r in records {
        let line = serde_json::to_string(r)
            .map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))?;
        writeln!(file, "{}", line)?;
    }
    Ok(())
}
