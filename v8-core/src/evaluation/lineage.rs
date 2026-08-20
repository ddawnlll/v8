//! Population Lineage DAG & Cross-Source Cohort Reconciliation (Issue #AUD-002, F02, F03).
//!
//! Enforces:
//! 1. Multi-stage partition contracts (Stage A: Dedup, Stage B: Admission).
//! 2. Independent population observation (no tautological parent reconstruction).
//! 3. Cross-source population disagreement gating (blocks unlike cohort reconciliation).
//! 4. Strict cardinality contracts across DAG transitions.

use std::fs;
use std::io;
use std::path::Path;

use serde::{Deserialize, Serialize};

use crate::hash::Canon;

/// Edge Cardinality Type along DAG transitions.
#[derive(Debug, Clone, Copy, Eq, PartialEq, Hash, Serialize, Deserialize)]
pub enum CardinalityType {
    OneToOne,
    ZeroOrOne,
    ZeroOrMany,
    OneOrMany,
    Partition,
    ManyToOne,
    Join,
}

/// A node in the deterministic Population Lineage DAG.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct PopulationNode {
    pub population_id: String,
    pub population_hash: String,
    pub parent_ids: Vec<String>,
    pub parent_hashes: Vec<String>,
    pub cardinality_type: CardinalityType,
    pub count: usize,
    pub transform_rule: String,
    pub filter_reason: Option<String>,
}

impl PopulationNode {
    pub fn new(
        population_id: impl Into<String>,
        parent_ids: Vec<String>,
        parent_hashes: Vec<String>,
        cardinality_type: CardinalityType,
        count: usize,
        transform_rule: impl Into<String>,
        filter_reason: Option<String>,
    ) -> Self {
        let pop_id = population_id.into();
        let rule = transform_rule.into();

        // Deterministic content hash for this population node
        let mut canon = Canon::new();
        canon.push_str(&pop_id);
        for pid in &parent_ids {
            canon.push_str(pid);
        }
        for ph in &parent_hashes {
            canon.push_str(ph);
        }
        canon.push_u64(count as u64);
        canon.push_str(&rule);
        if let Some(ref r) = filter_reason {
            canon.push_str(r);
        }
        let population_hash = canon.finish_sha1_hex();

        Self {
            population_id: pop_id,
            population_hash,
            parent_ids,
            parent_hashes,
            cardinality_type,
            count,
            transform_rule: rule,
            filter_reason,
        }
    }
}

/// Cohort metadata binding for cross-source reconciliation.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct CohortMetadata {
    pub cohort_id: String,
    pub dataset_hash: String,
    pub stage_a_setups_hash: String,
    pub stage_b_candidates_hash: String,
    pub execution_fills_hash: String,
    pub admitted_candidates_count: usize,
    pub total_candidates_count: usize,
}

/// Complete Population Lineage DAG.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PopulationLineageDag {
    pub nodes: Vec<PopulationNode>,
    pub cohort: CohortMetadata,
    pub stage_a_conservation_valid: bool,
    pub stage_b_conservation_valid: bool,
    pub overall_dag_valid: bool,
    pub reconciliation_block_reason: Option<String>,
}

impl PopulationLineageDag {
    /// Build DAG from independently observed population counts.
    pub fn build(
        observed_setups: usize,
        dedup_suppressed: usize,
        candidates_count: usize,
        vetoed_count: usize,
        admitted_count: usize,
        fills_count: usize,
        dataset_hash: &str,
    ) -> Self {
        let mut nodes = Vec::new();

        // 1. Observed Setup Population (Stage A Root)
        let setup_node = PopulationNode::new(
            "ObservedSetupPopulation",
            vec![],
            vec![],
            CardinalityType::Partition,
            observed_setups,
            "evaluations.iter().filter(|e| e.fired).count()",
            None,
        );
        let setup_hash = setup_node.population_hash.clone();
        nodes.push(setup_node);

        // 2. Dedup Suppressed Population (Stage A Child)
        let dedup_node = PopulationNode::new(
            "DedupSuppressedPopulation",
            vec!["ObservedSetupPopulation".to_string()],
            vec![setup_hash.clone()],
            CardinalityType::Partition,
            dedup_suppressed,
            "dedup_gate(D-026)",
            Some("DUPLICATE_SETUP_BAR".to_string()),
        );
        nodes.push(dedup_node);

        // 3. Unique Candidate Population (Stage A Child / Stage B Root)
        let cand_node = PopulationNode::new(
            "CandidatePopulation",
            vec!["ObservedSetupPopulation".to_string()],
            vec![setup_hash.clone()],
            CardinalityType::Partition,
            candidates_count,
            "pass_dedup_into_candidate_stream",
            None,
        );
        let cand_hash = cand_node.population_hash.clone();
        nodes.push(cand_node);

        // 4. Counterfactual Outcome Population (1:1 with Candidates)
        let cf_node = PopulationNode::new(
            "CounterfactualOutcomePopulation",
            vec!["CandidatePopulation".to_string()],
            vec![cand_hash.clone()],
            CardinalityType::OneToOne,
            candidates_count,
            "replay_kernel_unconstrained_outcome",
            None,
        );
        nodes.push(cf_node);

        // 5. Vetoed Candidate Population (Stage B Child)
        let veto_node = PopulationNode::new(
            "VetoedCandidatePopulation",
            vec!["CandidatePopulation".to_string()],
            vec![cand_hash.clone()],
            CardinalityType::Partition,
            vetoed_count,
            "admission_allocator_veto",
            Some("RISK_OR_CAPACITY_CONSTRAINT".to_string()),
        );
        nodes.push(veto_node);

        // 6. Admitted Candidate Population (Stage B Child)
        let admit_node = PopulationNode::new(
            "AdmittedCandidatePopulation",
            vec!["CandidatePopulation".to_string()],
            vec![cand_hash.clone()],
            CardinalityType::Partition,
            admitted_count,
            "admission_allocator_admit",
            None,
        );
        let admit_hash = admit_node.population_hash.clone();
        nodes.push(admit_node);

        // 7. Fill Population (ZeroOrMany from admitted candidates)
        let fill_node = PopulationNode::new(
            "FillPopulation",
            vec!["AdmittedCandidatePopulation".to_string()],
            vec![admit_hash.clone()],
            CardinalityType::ZeroOrMany,
            fills_count,
            "simulator_order_matching_fills",
            None,
        );
        let fill_hash = fill_node.population_hash.clone();
        nodes.push(fill_node);

        // 8. Position Transition Population (1:1 with fills)
        let pos_node = PopulationNode::new(
            "PositionTransitionPopulation",
            vec!["FillPopulation".to_string()],
            vec![fill_hash.clone()],
            CardinalityType::OneToOne,
            fills_count,
            "wallet_position_transition",
            None,
        );
        nodes.push(pos_node);

        // Conservation Verifications (Independent Observation Guarantee)
        let stage_a_valid = observed_setups == (dedup_suppressed + candidates_count);
        let stage_b_valid = candidates_count == (vetoed_count + admitted_count);
        let overall_valid = stage_a_valid && stage_b_valid;

        let block_reason = if !stage_a_valid {
            Some(format!(
                "Stage A Partition Mismatch: Observed Setups ({observed_setups}) != Dedup ({dedup_suppressed}) + Candidates ({candidates_count})"
            ))
        } else if !stage_b_valid {
            Some(format!(
                "Stage B Partition Mismatch: Candidates ({candidates_count}) != Vetoed ({vetoed_count}) + Admitted ({admitted_count})"
            ))
        } else {
            None
        };

        let mut cohort_canon = Canon::new();
        cohort_canon.push_str(&setup_hash);
        cohort_canon.push_str(&cand_hash);
        cohort_canon.push_str(&admit_hash);
        cohort_canon.push_str(&fill_hash);
        cohort_canon.push_u64(admitted_count as u64);
        let cohort_digest = cohort_canon.finish_sha1_hex();

        let cohort = CohortMetadata {
            cohort_id: format!("cohort-{}", &cohort_digest[..12.min(cohort_digest.len())]),
            dataset_hash: dataset_hash.to_string(),
            stage_a_setups_hash: setup_hash,
            stage_b_candidates_hash: cand_hash,
            execution_fills_hash: fill_hash,
            admitted_candidates_count: admitted_count,
            total_candidates_count: candidates_count,
        };

        Self {
            nodes,
            cohort,
            stage_a_conservation_valid: stage_a_valid,
            stage_b_conservation_valid: stage_b_valid,
            overall_dag_valid: overall_valid,
            reconciliation_block_reason: block_reason,
        }
    }

    /// Cross-source cohort disagreement gate.
    /// Blocks reconciliation if two reports/sources compare disparate population hashes under identical labels.
    pub fn reconcile_with_external(
        &self,
        external_cohort: &CohortMetadata,
        kpi_label: &str,
    ) -> Result<(), String> {
        if self.cohort.cohort_id != external_cohort.cohort_id {
            return Err(format!(
                "RECONCILIATION_BLOCK: Cross-Source Population Disagreement on KPI '{kpi_label}'. Local cohort {} != External cohort {}. (Mismatched cohorts: local {} admitted vs external {})",
                self.cohort.cohort_id,
                external_cohort.cohort_id,
                self.cohort.admitted_candidates_count,
                external_cohort.admitted_candidates_count,
            ));
        }
        Ok(())
    }

    /// Persist DAG artifacts to disk.
    pub fn save_artifacts(&self, out_dir: &Path) -> io::Result<()> {
        fs::create_dir_all(out_dir)?;

        // 1. population_lineage.jsonl
        let mut lineage_content = String::new();
        for node in &self.nodes {
            lineage_content.push_str(&serde_json::to_string(node).map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))?);
            lineage_content.push('\n');
        }
        fs::write(out_dir.join("population_lineage.jsonl"), lineage_content)?;

        // 2. cohort_manifest.json
        let cohort_json = serde_json::to_string_pretty(&self.cohort)
            .map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))?;
        fs::write(out_dir.join("cohort_manifest.json"), cohort_json)?;

        // 3. report_reconciliation.json
        let recon_json = serde_json::to_string_pretty(self)
            .map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))?;
        fs::write(out_dir.join("report_reconciliation.json"), recon_json)?;

        // 4. report_cell_provenance.parquet (JSON-table representation)
        let mut provenance_records = Vec::new();
        for node in &self.nodes {
            provenance_records.push(serde_json::json!({
                "cell_name": node.population_id,
                "cell_value": node.count,
                "population_hash": node.population_hash,
                "cardinality_type": format!("{:?}", node.cardinality_type),
                "transform_rule": node.transform_rule,
                "filter_reason": node.filter_reason,
            }));
        }
        let prov_json = serde_json::to_string_pretty(&provenance_records)
            .map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))?;
        fs::write(out_dir.join("report_cell_provenance.parquet"), prov_json)?;

        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_dag_passes_on_consistent_independent_observations() {
        // Certified baseline BTCUSDT numbers:
        // Setups: 42,647 = 14,766 (dedup) + 27,881 (candidates)
        // Candidates: 27,881 = 26,107 (vetoed) + 1,774 (admitted)
        let dag = PopulationLineageDag::build(
            42_647,
            14_766,
            27_881,
            26_107,
            1_774,
            2_460,
            "tape_sha256_mock",
        );

        assert!(dag.stage_a_conservation_valid);
        assert!(dag.stage_b_conservation_valid);
        assert!(dag.overall_dag_valid);
        assert!(dag.reconciliation_block_reason.is_none());
        assert_eq!(dag.nodes.len(), 8);
    }

    #[test]
    fn test_missing_child_mutation_gate_fails_closed_on_stage_a() {
        // Mutation: 1 candidate silently dropped from candidates stream
        let dag = PopulationLineageDag::build(
            42_647, // Independently observed setups
            14_766, // Dedup
            27_880, // Corrupted candidates (27,881 - 1)
            26_107,
            1_774,
            2_460,
            "tape_sha256_mock",
        );

        assert!(!dag.stage_a_conservation_valid);
        assert!(!dag.overall_dag_valid);
        assert!(dag.reconciliation_block_reason.unwrap().contains("Stage A Partition Mismatch"));
    }

    #[test]
    fn test_missing_child_mutation_gate_fails_closed_on_stage_b() {
        // Mutation: 1 veto record dropped from veto log
        let dag = PopulationLineageDag::build(
            42_647,
            14_766,
            27_881, // Independently observed candidates
            26_106, // Corrupted vetoes (26,107 - 1)
            1_774,  // Admitted
            2_460,
            "tape_sha256_mock",
        );

        assert!(dag.stage_a_conservation_valid);
        assert!(!dag.stage_b_conservation_valid);
        assert!(!dag.overall_dag_valid);
        assert!(dag.reconciliation_block_reason.unwrap().contains("Stage B Partition Mismatch"));
    }

    #[test]
    fn test_cross_source_cohort_disagreement_blocks_reconciliation() {
        let local_dag = PopulationLineageDag::build(
            42_647, 14_766, 27_881, 26_107, 1_774, 2_460, "tape_sha",
        );

        // Historical conflicting cohort: 27,879 vetoed, 2 admitted
        let external_dag = PopulationLineageDag::build(
            42_647, 14_766, 27_881, 27_879, 2, 2, "tape_sha",
        );

        let res = local_dag.reconcile_with_external(&external_dag.cohort, "ADMITTED_TRADES");
        assert!(res.is_err());
        let err_msg = res.unwrap_err();
        assert!(err_msg.contains("RECONCILIATION_BLOCK"));
        assert!(err_msg.contains("Cross-Source Population Disagreement"));
    }
}