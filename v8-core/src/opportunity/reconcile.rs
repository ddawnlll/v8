//! Dependence-Aware Evidence Reconciliation & Reconciled Opportunity State (Issue #231, #236, D-130).
//!
//! Owning Authority: V8 Constitution Rules 6, 14, 20, 22.
//!
//! Reconciler Invariants:
//!   1. Exact observer clone collapse: N duplicate experts produce marginal epistemic gain of 0 (N_eff = 1.0).
//!   2. Contradiction preservation: simultaneous Support and Contradict stances do not cancel into a fake majority.
//!   3. Anti-Ranker Guarantee: zero global candidate ranking, zero shared scoring across distinct opportunities.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use crate::error::V8CoreError;
use crate::hash::Canon;
use super::evidence::{ObserverEvidence, ObserverStance, HabitatAssessment};
use super::book::OpportunityEpisode;

/// Reconciled aggregate stance.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub enum ReconciledStance {
    Supported,
    Contradicted,
    Inconclusive,
    Indeterminate,
}

/// Reconciled Opportunity State (Primitive 5 of 7).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ReconciledOpportunityState {
    pub reconciled_id: String,
    pub opportunity_id: String,
    pub aggregate_stance: ReconciledStance,
    pub effective_observer_count: f64,
    pub support_weight: f64,
    pub contradict_weight: f64,
    pub abstention_weight: f64,
    pub contradiction_entropy: f64,
    pub net_confidence: f64,
    pub reconciliation_time: i64,
    pub participating_evidence_ids: Vec<String>,
}

impl ReconciledOpportunityState {
    /// Computes cryptographic BLAKE3 identity for ReconciledOpportunityState.
    pub fn compute_id(&self) -> String {
        let mut c = Canon::new();
        c.push_str("ReconciledOpportunityState");
        c.push_str(&self.opportunity_id);
        c.push_str(&format!("{:?}", self.aggregate_stance));
        c.push_f64(self.effective_observer_count);
        c.push_f64(self.support_weight);
        c.push_f64(self.contradict_weight);
        c.push_f64(self.abstention_weight);
        c.push_f64(self.contradiction_entropy);
        c.push_f64(self.net_confidence);
        c.push_i64(self.reconciliation_time);
        
        c.push_list();
        c.push_count(self.participating_evidence_ids.len());
        for id in &self.participating_evidence_ids {
            c.push_str(id);
        }
        c.finish_blake3_hex()
    }
}

/// Dependence-aware Evidence Reconciler.
pub struct EvidenceReconciler;

impl EvidenceReconciler {
    /// Reconciles an array of observer evidence stances for a given opportunity episode.
    pub fn reconcile(
        episode: &OpportunityEpisode,
        evidence_list: &[ObserverEvidence],
    ) -> Result<ReconciledOpportunityState, V8CoreError> {
        if evidence_list.is_empty() {
            let mut state = ReconciledOpportunityState {
                reconciled_id: String::new(),
                opportunity_id: episode.episode_id.clone(),
                aggregate_stance: ReconciledStance::Indeterminate,
                effective_observer_count: 0.0,
                support_weight: 0.0,
                contradict_weight: 0.0,
                abstention_weight: 0.0,
                contradiction_entropy: 0.0,
                net_confidence: 0.0,
                reconciliation_time: episode.as_of_time,
                participating_evidence_ids: Vec::new(),
            };
            state.reconciled_id = state.compute_id();
            return Ok(state);
        }

        // Group evidence by dependency_group to discount clone correlation (Rule 20 / Rule 22)
        let mut group_map: HashMap<String, Vec<&ObserverEvidence>> = HashMap::new();
        let mut participating_ids: Vec<String> = Vec::new();

        for ev in evidence_list {
            if ev.opportunity_id != episode.episode_id {
                return Err(V8CoreError::WitnessReconciliationError(format!(
                    "Evidence opportunity_id ({}) does not match episode ({})",
                    ev.opportunity_id, episode.episode_id
                )));
            }
            participating_ids.push(ev.evidence_id.clone());
            group_map
                .entry(ev.dependency_group.clone())
                .or_default()
                .push(ev);
        }
        participating_ids.sort();

        let mut total_support = 0.0;
        let mut total_contradict = 0.0;
        let mut total_abstain = 0.0;
        let mut n_effective_groups = 0.0;

        for (_group, group_evidences) in group_map {
            // For each dependency group, collapse duplicates: effective group weight = 1.0
            n_effective_groups += 1.0;
            let group_size = group_evidences.len() as f64;

            let mut grp_sup = 0.0;
            let mut grp_con = 0.0;
            let mut grp_abs = 0.0;

            for ev in group_evidences {
                // If out of habitat, treat strictly as abstention (Rule 21)
                if ev.habitat_assessment == HabitatAssessment::OutOfHabitat
                    || ev.habitat_assessment == HabitatAssessment::Contraindicated
                {
                    grp_abs += 1.0;
                    continue;
                }

                match &ev.stance {
                    ObserverStance::Support { confidence, .. } => {
                        let conf = confidence.clamp(0.0, 1.0) * (1.0 - ev.uncertainty);
                        grp_sup += conf;
                    }
                    ObserverStance::Contradict { severity, .. } => {
                        let sev = severity.clamp(0.0, 1.0) * (1.0 - ev.uncertainty);
                        grp_con += sev;
                    }
                    ObserverStance::Abstain { .. } => {
                        grp_abs += 1.0;
                    }
                    ObserverStance::Unknown { .. } => {
                        grp_abs += 0.5;
                    }
                }
            }

            // Normalize intra-group contribution by group size so N clones give 1.0 total power
            total_support += grp_sup / group_size;
            total_contradict += grp_con / group_size;
            total_abstain += grp_abs / group_size;
        }

        // Calculate contradiction entropy (Shannon-like entropy over support vs contradict)
        let total_active = total_support + total_contradict;
        let contradiction_entropy = if total_active > 1e-9 {
            let p_sup = total_support / total_active;
            let p_con = total_contradict / total_active;
            let mut ent = 0.0;
            if p_sup > 1e-9 {
                ent -= p_sup * p_sup.ln();
            }
            if p_con > 1e-9 {
                ent -= p_con * p_con.ln();
            }
            ent
        } else {
            0.0
        };

        let net_confidence = if total_active > 1e-9 {
            (total_support - total_contradict) / (total_support + total_contradict + total_abstain)
        } else {
            0.0
        };

        let aggregate_stance = if total_contradict > total_support {
            ReconciledStance::Contradicted
        } else if total_support > total_contradict && contradiction_entropy < 0.5 {
            ReconciledStance::Supported
        } else if total_active < 1e-9 {
            ReconciledStance::Indeterminate
        } else {
            ReconciledStance::Inconclusive
        };

        let mut state = ReconciledOpportunityState {
            reconciled_id: String::new(),
            opportunity_id: episode.episode_id.clone(),
            aggregate_stance,
            effective_observer_count: n_effective_groups,
            support_weight: total_support,
            contradict_weight: total_contradict,
            abstention_weight: total_abstain,
            contradiction_entropy,
            net_confidence,
            reconciliation_time: episode.as_of_time,
            participating_evidence_ids: participating_ids,
        };
        state.reconciled_id = state.compute_id();
        Ok(state)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::opportunity::book::IdentityStatus;
    use crate::opportunity::evidence::AbstentionReason;
    use crate::opportunity::exposure::{EconomicExposureStructure, ExposureDirection};

    fn make_test_episode() -> OpportunityEpisode {
        let exp = EconomicExposureStructure::single_perp(
            "BTCUSDT",
            "BTC",
            "binance-um",
            "USDT",
            ExposureDirection::Long,
        )
        .unwrap();

        OpportunityEpisode::new(
            exp,
            1_000_000,
            2_000_000,
            24,
            IdentityStatus::Canonical,
            "state_hash",
            "lineage_hash",
        )
        .unwrap()
    }

    #[test]
    fn test_exact_observer_clone_collapse_n_eff_equals_one() {
        let ep = make_test_episode();

        // 10 identical clone observers in the same dependency group
        let mut evidences = Vec::new();
        for i in 0..10 {
            evidences.push(
                ObserverEvidence::new(
                    &ep.episode_id,
                    format!("trend_clone_{i}"),
                    "v1",
                    "momentum",
                    "trend",
                    "dep_trend_group", // Same dependency group
                    ObserverStance::Support {
                        confidence: 0.90,
                        expected_edge_r: 0.50,
                    },
                    HabitatAssessment::InHabitat,
                    0.10,
                    1_000_000,
                    "lineage",
                )
                .unwrap(),
            );
        }

        let reconciled = EvidenceReconciler::reconcile(&ep, &evidences).unwrap();

        // Invariant: N identical clones in 1 group collapse to exactly N_eff = 1.0
        assert_eq!(reconciled.effective_observer_count, 1.0);
        // Intra-group support normalized to 0.81 (0.90 * 0.90 uncertainty discount)
        assert!((reconciled.support_weight - 0.81).abs() < 1e-6);
        assert_eq!(reconciled.aggregate_stance, ReconciledStance::Supported);
    }

    #[test]
    fn test_severe_contradiction_dampens_to_inconclusive() {
        let ep = make_test_episode();

        let evidences = vec![
            ObserverEvidence::new(
                &ep.episode_id,
                "expert_bull",
                "v1",
                "momentum",
                "trend",
                "group_a",
                ObserverStance::Support {
                    confidence: 0.85,
                    expected_edge_r: 0.40,
                },
                HabitatAssessment::InHabitat,
                0.10,
                1_000_000,
                "lineage",
            )
            .unwrap(),
            ObserverEvidence::new(
                &ep.episode_id,
                "expert_bear",
                "v1",
                "volatility",
                "reversal",
                "group_b",
                ObserverStance::Contradict {
                    reason: "Massive overhead resistance".to_string(),
                    severity: 0.85,
                },
                HabitatAssessment::InHabitat,
                0.10,
                1_000_000,
                "lineage",
            )
            .unwrap(),
        ];

        let reconciled = EvidenceReconciler::reconcile(&ep, &evidences).unwrap();

        assert_eq!(reconciled.effective_observer_count, 2.0);
        assert!(reconciled.contradiction_entropy > 0.60); // High entropy due to severe contradiction
        assert_eq!(reconciled.aggregate_stance, ReconciledStance::Inconclusive);
    }

    #[test]
    fn test_abstention_does_not_corrupt_clean_support() {
        let ep = make_test_episode();

        let mut evidences = vec![ObserverEvidence::new(
            &ep.episode_id,
            "expert_active",
            "v1",
            "momentum",
            "trend",
            "group_a",
            ObserverStance::Support {
                confidence: 0.90,
                expected_edge_r: 0.50,
            },
            HabitatAssessment::InHabitat,
            0.10,
            1_000_000,
            "lineage",
        )
        .unwrap()];

        // 3 abstaining out-of-habitat witnesses
        for i in 0..3 {
            evidences.push(
                ObserverEvidence::new(
                    &ep.episode_id,
                    format!("expert_abs_{i}"),
                    "v1",
                    "derivatives",
                    "crowding",
                    format!("group_abs_{i}"),
                    ObserverStance::Abstain {
                        reason: AbstentionReason::RegimeMismatch,
                    },
                    HabitatAssessment::OutOfHabitat,
                    0.50,
                    1_000_000,
                    "lineage",
                )
                .unwrap(),
            );
        }

        let reconciled = EvidenceReconciler::reconcile(&ep, &evidences).unwrap();
        assert_eq!(reconciled.contradict_weight, 0.0);
        assert_eq!(reconciled.contradiction_entropy, 0.0);
        assert!((reconciled.support_weight - 0.81).abs() < 1e-6);
    }
}
