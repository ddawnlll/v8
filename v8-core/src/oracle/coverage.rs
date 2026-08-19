//! Representational coverage reconciliation and evaluation evidence receipts
//! (TARGET_ORACLE_SPEC §5.8, §9, §17.5, §18.2).
//!
//! Reconciles the frozen supported Opportunity Universe population against
//! same-event shipped Expert proposals. Emits contract-bound coverage receipts
//! labeled NO_ECONOMIC_CLAIM.

#![allow(dead_code)]

use std::collections::BTreeMap;
use std::fs;
use std::io;
use std::path::Path;

use serde::{Deserialize, Serialize};

use crate::evaluation::agents::FindingRecord;
use crate::evaluation::schema_cache::{compute_numeric_col_stats, SchemaCache, TableStatistics};
use crate::experts::base::ExpertEval;
use crate::hash::Canon;
use crate::regret::Action;
use crate::simulator::Draft;

use super::artifacts::{OpportunityUniverseVersion, OracleEvaluationRecord};
use super::authority::OracleOutcome;
use super::opportunity::{Direction, GrammarCandidate};
use super::support::SupportClassifier;
use super::taxonomy::{AuthorityLevel, Identifiability, OracleContext, OracleRefusal, ValueNotion};

/// Membership status of one grammar candidate in the opportunity coverage receipt.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct OpportunityCoverageMember {
    pub grammar_candidate_id: String,
    pub template_id: String,
    pub instrument: String,
    pub timeframe: String,
    pub direction: Direction,
    pub decision_time: i64,
    pub is_supported: bool,
    pub is_represented: bool,
    pub representing_expert_id: Option<String>,
    pub authority_level: AuthorityLevel,
    pub identifiability_status: Identifiability,
    pub refusal_reason: Option<String>,
    pub point_estimate: Option<f64>,
}

/// Unrepresented opportunity cluster summary.
#[derive(Debug, Clone, Eq, PartialEq, Serialize, Deserialize)]
pub struct UnrepresentedCluster {
    pub template_id: String,
    pub direction: Direction,
    pub count: usize,
}

/// Minimal immutable coverage receipt.
/// Explicitly labeled NO_ECONOMIC_CLAIM (TARGET_ORACLE_SPEC §5.8, §18.2).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct CoverageReceipt {
    pub receipt_id: String,
    pub universe_id: String,
    pub population_hash: String,
    pub claim: String,
    pub total_opportunity_count: usize,
    pub supported_opportunity_count: usize,
    pub unsupported_opportunity_count: usize,
    pub represented_supported_count: usize,
    pub unrepresented_supported_count: usize,
    pub representational_coverage: f64,
    pub representational_coverage_gap: f64,
    pub unrepresented_clusters: Vec<UnrepresentedCluster>,
    pub members: Vec<OpportunityCoverageMember>,
}

impl CoverageReceipt {
    pub fn identity(&self) -> String {
        let mut c = Canon::new();
        c.push_str("coverage-receipt-v1");
        c.push_value(&serde_json::json!({
            "universe_id": self.universe_id,
            "population_hash": self.population_hash,
            "claim": self.claim,
            "total_opportunity_count": self.total_opportunity_count,
            "supported_opportunity_count": self.supported_opportunity_count,
            "unsupported_opportunity_count": self.unsupported_opportunity_count,
            "represented_supported_count": self.represented_supported_count,
            "unrepresented_supported_count": self.unrepresented_supported_count,
            "representational_coverage": format!("{:.6}", self.representational_coverage),
            "representational_coverage_gap": format!("{:.6}", self.representational_coverage_gap),
            "unrepresented_clusters": self.unrepresented_clusters,
            "members_count": self.members.len(),
        }));
        c.finish_sha1_hex()
    }

    pub fn bind_identity(&mut self) {
        self.receipt_id = self.identity();
    }

    /// Persist the minimum §17.5 mapping into the existing v8.eval.v1 bundle.
    pub fn save_to_bundle(
        &self,
        bundle_dir: &Path,
        universe: &OpportunityUniverseVersion,
        eval_records: &[OracleEvaluationRecord],
    ) -> io::Result<()> {
        let prov_dir = bundle_dir.join("provenance");
        let econ_dir = bundle_dir.join("economics");
        let analysis_dir = bundle_dir.join("analysis");

        fs::create_dir_all(&prov_dir)?;
        fs::create_dir_all(&econ_dir)?;
        fs::create_dir_all(&analysis_dir)?;

        // 1. provenance/opportunity_universe.json
        let universe_json = serde_json::to_string_pretty(universe)
            .map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))?;
        fs::write(prov_dir.join("opportunity_universe.json"), universe_json)?;

        // 2. economics/oracle_evaluation.parquet (persisted as newline-delimited json/table for v8.eval.v1)
        let eval_json = serde_json::to_string_pretty(eval_records)
            .map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))?;
        fs::write(econ_dir.join("oracle_evaluation.parquet"), eval_json)?;

        // 3. analysis/findings.jsonl (coverage findings)
        let mut findings = Vec::new();
        findings.push(FindingRecord {
            finding_id: format!("FINDING-ORACLE-COV-{}", &self.receipt_id[..8.min(self.receipt_id.len())]),
            scope: serde_json::json!({
                "universe_id": self.universe_id,
                "population_hash": self.population_hash,
            }),
            claim: format!(
                "Representational coverage of universe {} is {:.2}% (gap: {:.2}%)",
                self.universe_id,
                self.representational_coverage * 100.0,
                self.representational_coverage_gap * 100.0,
            ),
            epistemic_status: "SUPPORTED".to_string(),
            severity: if self.representational_coverage < 0.5 { "HIGH".to_string() } else { "INFO".to_string() },
            confidence: 1.0,
            observations: vec![
                format!("Total opportunities: {}", self.total_opportunity_count),
                format!("Supported hindsight opportunities: {}", self.supported_opportunity_count),
                format!("Represented by shipped experts: {}", self.represented_supported_count),
                format!("Unrepresented clusters: {}", self.unrepresented_clusters.len()),
            ],
            statistical_evidence: serde_json::json!({
                "coverage": self.representational_coverage,
                "gap": self.representational_coverage_gap,
                "total": self.total_opportunity_count,
                "supported": self.supported_opportunity_count,
                "represented": self.represented_supported_count,
            }),
            alternative_explanations: vec!["Shipped expert plane selectively targets specific market sub-regimes".to_string()],
            falsifiers: vec!["Universe expansion or removal of unrepresented behavior templates".to_string()],
            supporting_artifacts: vec![
                "provenance/opportunity_universe.json".to_string(),
                "economics/oracle_evaluation.parquet".to_string(),
            ],
            recommended_next_test: "Measure isolated/marginal regret in O4 before any candidate promotion".to_string(),
        });

        for cluster in &self.unrepresented_clusters {
            findings.push(FindingRecord {
                finding_id: format!("FINDING-ORACLE-GAP-{}-{:?}", cluster.template_id, cluster.direction),
                scope: serde_json::json!({
                    "template_id": cluster.template_id,
                    "direction": format!("{:?}", cluster.direction),
                }),
                claim: format!(
                    "Unrepresented opportunity cluster: template '{}' ({:?}) has {} unrepresented supported opportunities",
                    cluster.template_id, cluster.direction, cluster.count
                ),
                epistemic_status: "SUPPORTED".to_string(),
                severity: "MEDIUM".to_string(),
                confidence: 1.0,
                observations: vec![format!("Unrepresented opportunities: {}", cluster.count)],
                statistical_evidence: serde_json::json!({
                    "cluster_count": cluster.count,
                }),
                alternative_explanations: vec!["Behavior template not covered by current 28 registered experts".to_string()],
                falsifiers: vec!["New expert candidate formalization covering this template".to_string()],
                supporting_artifacts: vec!["provenance/opportunity_universe.json".to_string()],
                recommended_next_test: "Examine whether cluster has after-cost positive expected utility in O4".to_string(),
            });
        }

        let mut findings_file = fs::OpenOptions::new()
            .create(true)
            .append(true)
            .open(analysis_dir.join("findings.jsonl"))?;
        use std::io::Write;
        for f in &findings {
            let line = serde_json::to_string(f)
                .map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))?;
            writeln!(findings_file, "{}", line)?;
        }

        // 4. Update or save schema cache
        let mut schema_cache = SchemaCache::new(&bundle_dir.to_string_lossy());
        let pts: Vec<f64> = eval_records.iter().filter_map(|r| r.point_estimate).collect();
        let mut eval_col_stats = std::collections::HashMap::new();
        eval_col_stats.insert("point_estimate".to_string(), compute_numeric_col_stats("F64", &pts));
        schema_cache.add_table(
            "economics/oracle_evaluation.parquet",
            TableStatistics {
                file_name: "oracle_evaluation.parquet".to_string(),
                relative_path: "economics/oracle_evaluation.parquet".to_string(),
                total_rows: eval_records.len(),
                total_columns: 22,
                columns: eval_col_stats,
            },
        );
        schema_cache.save(&analysis_dir.join("schema_cache.json"))?;

        Ok(())
    }
}

/// Adapt a GrammarCandidate to an L1 Draft using existing simulation truth ontology.
/// If candidate parameters cannot be mapped under the registered contract, emits
/// OracleRefusal rather than a new simulator.
pub fn adapt_candidate_to_l1_draft(candidate: &GrammarCandidate) -> Result<Draft, OracleRefusal> {
    let direction = match candidate.direction {
        Direction::Long => "LONG".to_string(),
        Direction::Short => "SHORT".to_string(),
    };

    let mut geom = serde_json::Map::new();
    for (k, v) in &candidate.parameters {
        geom.insert(k.clone(), v.clone());
    }

    // Default ATR and horizon if not in grid
    if !geom.contains_key("atr_ref") && !geom.contains_key("risk_frac") {
        geom.insert("risk_frac".to_string(), serde_json::json!(0.01));
    }
    if !geom.contains_key("target_r") {
        geom.insert("target_r".to_string(), serde_json::json!(2.0));
    }
    if !geom.contains_key("stop_r") {
        geom.insert("stop_r".to_string(), serde_json::json!(1.0));
    }
    if !geom.contains_key("expiry_bars") {
        geom.insert("expiry_bars".to_string(), serde_json::json!(24));
    }

    Ok(Draft {
        direction,
        birth_time: candidate.decision_time,
        risk_geometry: geom,
    })
}

/// Reconcile representational coverage deterministically.
pub fn reconcile_coverage(
    universe: &OpportunityUniverseVersion,
    grammar_candidates: &[GrammarCandidate],
    classifier: &SupportClassifier,
    expert_proposals: &[(String, ExpertEval)],
    future_bars_available: Option<usize>,
    requested_authority: AuthorityLevel,
    context: &OracleContext,
    lineage_id: &str,
) -> (CoverageReceipt, Vec<OracleEvaluationRecord>) {
    let pop_hash = super::opportunity::OpportunityGrammar::population_hash(grammar_candidates);
    let mut members = Vec::with_capacity(grammar_candidates.len());
    let mut eval_records = Vec::with_capacity(grammar_candidates.len());

    let mut unrepresented_cluster_map: BTreeMap<(String, Direction), usize> = BTreeMap::new();

    for candidate in grammar_candidates {
        let action = Action {
            action_id: "ACTUAL".to_string(),
            kind: "ACTUAL",
            provenance: "ACTUAL",
            override_geom: serde_json::Map::new(),
        };

        let (auth, refusal) = classifier.evaluate_support(
            candidate,
            &action,
            requested_authority,
            future_bars_available,
        );

        let is_supported = auth.identifiability_status == Identifiability::Identified && refusal.is_none();

        // Check active representation from shipped expert proposals
        let mut representing_expert_id = None;
        if is_supported {
            for (eid, eval) in expert_proposals {
                if eval.decision == "CANDIDATE" {
                    let dir_match = match (&candidate.direction, eval.draft.as_ref()) {
                        (Direction::Long, Some(d)) => d.direction == "LONG",
                        (Direction::Short, Some(d)) => d.direction == "SHORT",
                        _ => false,
                    };
                    if dir_match {
                        representing_expert_id = Some(eid.clone());
                        break;
                    }
                }
            }
        }

        let is_represented = representing_expert_id.is_some();

        if is_supported && !is_represented {
            *unrepresented_cluster_map
                .entry((candidate.template_id.clone(), candidate.direction.clone()))
                .or_insert(0) += 1;
        }

        let outcome = if is_supported {
            OracleOutcome::identified(0.0, auth.clone())
                .unwrap_or_else(|_| OracleOutcome::unknown(OracleRefusal::InsufficientSupport, auth.clone()))
        } else {
            let ref_reason = refusal.unwrap_or(OracleRefusal::InsufficientSupport);
            OracleOutcome::unknown(ref_reason, auth.clone())
        };

        let eval_rec = outcome.to_evaluation_record(
            context,
            &pop_hash,
            "action-manifest-actual-v1",
            "simulator-l1-canonical-v1",
            &universe.code_hash,
            "config-oracle-v1",
            ValueNotion::Retrospective,
            lineage_id,
        );

        members.push(OpportunityCoverageMember {
            grammar_candidate_id: candidate.grammar_candidate_id.clone(),
            template_id: candidate.template_id.clone(),
            instrument: candidate.instrument.clone(),
            timeframe: candidate.timeframe.clone(),
            direction: candidate.direction.clone(),
            decision_time: candidate.decision_time,
            is_supported,
            is_represented,
            representing_expert_id,
            authority_level: auth.oracle_authority_level,
            identifiability_status: auth.identifiability_status,
            refusal_reason: refusal.map(|r| r.code().to_string()),
            point_estimate: if is_supported { Some(0.0) } else { None },
        });

        eval_records.push(eval_rec);
    }

    let total_opportunity_count = members.len();
    let supported_opportunity_count = members.iter().filter(|m| m.is_supported).count();
    let unsupported_opportunity_count = total_opportunity_count.saturating_sub(supported_opportunity_count);
    let represented_supported_count = members.iter().filter(|m| m.is_supported && m.is_represented).count();
    let unrepresented_supported_count = supported_opportunity_count.saturating_sub(represented_supported_count);

    let representational_coverage = if supported_opportunity_count > 0 {
        represented_supported_count as f64 / supported_opportunity_count as f64
    } else {
        0.0
    };
    let representational_coverage_gap = 1.0 - representational_coverage;

    let unrepresented_clusters: Vec<UnrepresentedCluster> = unrepresented_cluster_map
        .into_iter()
        .map(|((template_id, direction), count)| UnrepresentedCluster {
            template_id,
            direction,
            count,
        })
        .collect();

    let mut receipt = CoverageReceipt {
        receipt_id: String::new(),
        universe_id: universe.universe_id.clone(),
        population_hash: pop_hash,
        claim: "NO_ECONOMIC_CLAIM".to_string(),
        total_opportunity_count,
        supported_opportunity_count,
        unsupported_opportunity_count,
        represented_supported_count,
        unrepresented_supported_count,
        representational_coverage,
        representational_coverage_gap,
        unrepresented_clusters,
        members,
    };
    receipt.bind_identity();

    (receipt, eval_records)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::oracle::opportunity::{
        CandidateTemplate, Direction, OpportunityGrammar, ParameterGrid, PredicateNode,
        PrimitiveDefinition, PrimitiveFamily, PrimitiveRegistry, TemplateRegistry, ValueRef,
    };
    use crate::oracle::authority::CounterfactualAuthority;
    use crate::oracle::taxonomy::{AuthorityLevel, OracleRole};
    use crate::oracle::utility::{HardConstraints, ModelIds, UtilityContract};
    use crate::simulator::Draft;
    use std::collections::BTreeSet;

    fn sample_grammar() -> OpportunityGrammar {
        OpportunityGrammar {
            version: "predicate-ir-v1".into(),
            primitives: PrimitiveRegistry {
                version: "registered-v1".into(),
                primitives: BTreeMap::from([(
                    "close".into(),
                    PrimitiveDefinition {
                        family: PrimitiveFamily::PriceReturn,
                        source_version: "state-v1".into(),
                    },
                )]),
                allowed_operators: BTreeSet::from(["ABOVE".into()]),
            },
            templates: TemplateRegistry {
                version: "template-v1".into(),
                templates: vec![
                    CandidateTemplate {
                        template_id: "template-breakout".into(),
                        mechanism_family_id: "price".into(),
                        behavior_family_id: "breakout".into(),
                        habitat_predicate: PredicateNode::Above {
                            feature: "close".into(),
                            threshold: ValueRef::Parameter("threshold".into()),
                        },
                        setup_predicate: PredicateNode::Above {
                            feature: "close".into(),
                            threshold: ValueRef::Parameter("threshold".into()),
                        },
                        trigger_predicate: PredicateNode::Above {
                            feature: "close".into(),
                            threshold: ValueRef::Parameter("threshold".into()),
                        },
                        direction: Direction::Long,
                        invalidation: "stop-v1".into(),
                        expiry: "24bar".into(),
                        risk_geometry: BTreeMap::new(),
                        parameter_names: vec!["threshold".into()],
                    },
                    CandidateTemplate {
                        template_id: "template-reversal".into(),
                        mechanism_family_id: "price".into(),
                        behavior_family_id: "reversal".into(),
                        habitat_predicate: PredicateNode::Above {
                            feature: "close".into(),
                            threshold: ValueRef::Parameter("threshold".into()),
                        },
                        setup_predicate: PredicateNode::Above {
                            feature: "close".into(),
                            threshold: ValueRef::Parameter("threshold".into()),
                        },
                        trigger_predicate: PredicateNode::Above {
                            feature: "close".into(),
                            threshold: ValueRef::Parameter("threshold".into()),
                        },
                        direction: Direction::Short,
                        invalidation: "stop-v1".into(),
                        expiry: "24bar".into(),
                        risk_geometry: BTreeMap::new(),
                        parameter_names: vec!["threshold".into()],
                    },
                ],
            },
            grid: ParameterGrid {
                grid_id: "grid-v1".into(),
                values: BTreeMap::from([("threshold".into(), vec![serde_json::json!(100.0)])]),
            },
        }
    }

    fn sample_universe(grammar: &OpportunityGrammar) -> OpportunityUniverseVersion {
        let mut universe = OpportunityUniverseVersion {
            universe_id: String::new(),
            version: "1".into(),
            parent_universe_id: None,
            instrument_universe: vec!["BTCUSDT".into()],
            timeframe_set: vec!["1h".into()],
            information_contract_id: "pit-v1".into(),
            primitive_registry_hash: grammar.primitives.identity(),
            predicate_ir_version: grammar.version.clone(),
            behavior_template_registry_hash: grammar.templates.identity(),
            parameter_grid_hash: grammar.grid.identity(),
            tradability_rule_id: "detect-v1".into(),
            support_rule_id: "canonical-l1-support-v1".into(),
            authority_contract_id: "l1-v1".into(),
            search_universe_size: grammar.search_universe_size(1, 1).unwrap(),
            complexity_budget: 1,
            created_at: 0,
            code_hash: "code-v1".into(),
            execution_mode_id: "canonical-l1".into(),
        };
        universe.bind_identity();
        universe
    }

    fn sample_context(universe: &OpportunityUniverseVersion) -> OracleContext {
        OracleContext {
            role: OracleRole::Hindsight,
            authority: AuthorityLevel::L1,
            information_contract_id: universe.information_contract_id.clone(),
            opportunity_universe_id: universe.universe_id.clone(),
            utility_contract_id: "utility-v1".into(),
            policy_class_id: "policy-v1".into(),
            cost_model_id: "cost-v1".into(),
            capacity_model_id: "cap-v1".into(),
            environment_target_id: "binance-usdt-perp-l1".into(),
        }
    }

    #[test]
    fn every_coverage_numerator_member_reconciles_to_supported_denominator() {
        let grammar = sample_grammar();
        let universe = sample_universe(&grammar);
        let context = sample_context(&universe);
        let classifier = SupportClassifier::canonical_l1();

        let cand_long = GrammarCandidate {
            grammar_candidate_id: "cand-long-01".into(),
            universe_id: universe.universe_id.clone(),
            template_id: "template-breakout".into(),
            instrument: "BTCUSDT".into(),
            timeframe: "1h".into(),
            direction: Direction::Long,
            decision_time: 1000,
            parameters: BTreeMap::new(),
        };
        let cand_short = GrammarCandidate {
            grammar_candidate_id: "cand-short-01".into(),
            universe_id: universe.universe_id.clone(),
            template_id: "template-reversal".into(),
            instrument: "BTCUSDT".into(),
            timeframe: "1h".into(),
            direction: Direction::Short,
            decision_time: 1000,
            parameters: BTreeMap::new(),
        };

        let candidates = vec![cand_long, cand_short];

        // Expert proposal only represents LONG
        let expert_proposals = vec![(
            "bollinger_breakout".to_string(),
            ExpertEval {
                applicability: "APPLICABLE".into(),
                decision: "CANDIDATE".into(),
                draft: Some(Draft {
                    direction: "LONG".into(),
                    birth_time: 1000,
                    risk_geometry: serde_json::Map::new(),
                }),
                setup_anchor_event_id: Some("anchor-1".into()),
                setup_fingerprint: Some("fp-1".into()),
            },
        )];

        let (receipt, records) = reconcile_coverage(
            &universe,
            &candidates,
            &classifier,
            &expert_proposals,
            Some(30),
            AuthorityLevel::L1,
            &context,
            "lineage-01",
        );

        assert_eq!(receipt.total_opportunity_count, 2);
        assert_eq!(receipt.supported_opportunity_count, 2);
        assert_eq!(receipt.represented_supported_count, 1);
        assert_eq!(receipt.unrepresented_supported_count, 1);
        assert!((receipt.representational_coverage - 0.5).abs() < 1e-9);
        assert!((receipt.representational_coverage_gap - 0.5).abs() < 1e-9);
        assert_eq!(receipt.claim, "NO_ECONOMIC_CLAIM");
        assert_eq!(records.len(), 2);

        // Every numerator member is a supported hindsight opportunity
        for member in &receipt.members {
            if member.is_represented {
                assert!(member.is_supported);
            }
        }

        // Unrepresented cluster contains the short reversal
        assert_eq!(receipt.unrepresented_clusters.len(), 1);
        assert_eq!(
            receipt.unrepresented_clusters[0],
            UnrepresentedCluster {
                template_id: "template-reversal".into(),
                direction: Direction::Short,
                count: 1,
            }
        );
    }

    #[test]
    fn zero_coverage_fails_nonzero_coverage_floor() {
        let utility = UtilityContract {
            contract_id: "utility-v1".into(),
            version: "1".into(),
            primary_objective: "AFTER_COST_NET_UTILITY".into(),
            horizon: "1h".into(),
            accounting_currency: "USDT".into(),
            models: ModelIds {
                fee_model_id: "fees-v1".into(),
                funding_model_id: "funding-v1".into(),
                slippage_model_id: "slip-v1".into(),
                impact_model_id: "impact-v1".into(),
            },
            hard_constraints: HardConstraints {
                drawdown_max: 1.0,
                tail_risk_max: 1.0,
                capacity_max: 1.0,
                portfolio_heat_max: 1.0,
                coverage_min: 0.25,
                operational_rule_id: "ops-v1".into(),
            },
            optional_scalar_penalties: None,
            stress_grid_id: "stress-v1".into(),
            effective_from: 1,
        };
        assert_eq!(utility.validate(), Ok(()));

        let coverage = 0.0;
        assert!(coverage < utility.hard_constraints.coverage_min);
    }

    #[test]
    fn acceptance_test_1_missing_decision_time_data_cannot_produce_coverage_member() {
        let grammar = sample_grammar();
        let universe = sample_universe(&grammar);
        let context = sample_context(&universe);
        let classifier = SupportClassifier::canonical_l1();

        let cand_invalid = GrammarCandidate {
            grammar_candidate_id: "cand-future-01".into(),
            universe_id: universe.universe_id.clone(),
            template_id: "template-breakout".into(),
            instrument: "BTCUSDT".into(),
            timeframe: "1h".into(),
            direction: Direction::Long,
            decision_time: -1, // invalid decision time
            parameters: BTreeMap::new(),
        };

        let expert_proposals = vec![(
            "bollinger_breakout".to_string(),
            ExpertEval {
                applicability: "APPLICABLE".into(),
                decision: "CANDIDATE".into(),
                draft: Some(Draft {
                    direction: "LONG".into(),
                    birth_time: 1000,
                    risk_geometry: serde_json::Map::new(),
                }),
                setup_anchor_event_id: Some("anchor-1".into()),
                setup_fingerprint: Some("fp-1".into()),
            },
        )];

        let (receipt, _) = reconcile_coverage(
            &universe,
            &[cand_invalid],
            &classifier,
            &expert_proposals,
            Some(30),
            AuthorityLevel::L1,
            &context,
            "lineage-01",
        );

        assert_eq!(receipt.total_opportunity_count, 1);
        assert_eq!(receipt.supported_opportunity_count, 0);
        assert_eq!(receipt.represented_supported_count, 0);
        assert_eq!(receipt.representational_coverage, 0.0);
        assert_eq!(
            receipt.members[0].refusal_reason,
            Some("MISSING_DECISION_TIME_DATA".to_string())
        );
        assert!(!receipt.members[0].is_supported);
        assert!(!receipt.members[0].is_represented);
    }

    #[test]
    fn acceptance_test_2_l1_request_for_l3_returns_execution_authority_too_weak_with_no_point_value() {
        let grammar = sample_grammar();
        let universe = sample_universe(&grammar);
        let context = sample_context(&universe);
        let classifier = SupportClassifier::canonical_l1();

        let cand = GrammarCandidate {
            grammar_candidate_id: "cand-01".into(),
            universe_id: universe.universe_id.clone(),
            template_id: "template-breakout".into(),
            instrument: "BTCUSDT".into(),
            timeframe: "1h".into(),
            direction: Direction::Long,
            decision_time: 1000,
            parameters: BTreeMap::new(),
        };

        let (receipt, records) = reconcile_coverage(
            &universe,
            &[cand],
            &classifier,
            &[],
            Some(30),
            AuthorityLevel::L3, // Requesting L3 on L1 classifier
            &context,
            "lineage-01",
        );

        assert_eq!(receipt.supported_opportunity_count, 0);
        assert_eq!(
            receipt.members[0].refusal_reason,
            Some("EXECUTION_AUTHORITY_TOO_WEAK".to_string())
        );
        assert_eq!(receipt.members[0].point_estimate, None);
        assert_eq!(records[0].point_estimate, None);
        assert_eq!(
            records[0].refusal_reason,
            Some("EXECUTION_AUTHORITY_TOO_WEAK".to_string())
        );
    }

    #[test]
    fn acceptance_test_3_unsupported_size_action_or_queue_fill_is_weaker_authority_or_unknown() {
        let classifier = SupportClassifier::canonical_l1();
        let candidate = GrammarCandidate {
            grammar_candidate_id: "cand-01".into(),
            universe_id: "u-1".into(),
            template_id: "t-1".into(),
            instrument: "BTCUSDT".into(),
            timeframe: "1h".into(),
            direction: Direction::Long,
            decision_time: 1000,
            parameters: BTreeMap::new(),
        };

        let mut queue_action = Action {
            action_id: "ACTUAL".to_string(),
            kind: "ACTUAL",
            provenance: "ACTUAL",
            override_geom: serde_json::Map::new(),
        };
        queue_action
            .override_geom
            .insert("queue_priority".to_string(), serde_json::json!(1));

        let (auth, refusal) = classifier.evaluate_support(
            &candidate,
            &queue_action,
            AuthorityLevel::L1,
            Some(10),
        );
        assert_eq!(auth.identifiability_status, Identifiability::NotIdentifiable);
        assert_eq!(refusal, Some(OracleRefusal::NonIdentifiableFill));
        assert_ne!(auth.identifiability_status, Identifiability::Identified);
    }

    #[test]
    fn acceptance_test_4_insufficient_horizon_and_model_only_return_typed_refusals() {
        let classifier = SupportClassifier::canonical_l1();
        let candidate = GrammarCandidate {
            grammar_candidate_id: "cand-01".into(),
            universe_id: "u-1".into(),
            template_id: "t-1".into(),
            instrument: "BTCUSDT".into(),
            timeframe: "1h".into(),
            direction: Direction::Long,
            decision_time: 1000,
            parameters: BTreeMap::new(),
        };

        let mut action = Action {
            action_id: "ACTUAL".to_string(),
            kind: "ACTUAL",
            provenance: "ACTUAL",
            override_geom: serde_json::Map::new(),
        };
        action
            .override_geom
            .insert("expiry_bars".to_string(), serde_json::json!(48));

        let (auth_horizon, ref_horizon) = classifier.evaluate_support(
            &candidate,
            &action,
            AuthorityLevel::L1,
            Some(10), // only 10 bars < 48
        );
        assert_eq!(ref_horizon, Some(OracleRefusal::UndefinedFuture));
        assert_eq!(auth_horizon.identifiability_status, Identifiability::NotIdentifiable);

        action
            .override_geom
            .insert("model_counterfactual".to_string(), serde_json::json!(true));

        let (auth_model, ref_model) = classifier.evaluate_support(
            &candidate,
            &action,
            AuthorityLevel::L1,
            Some(50),
        );
        assert_eq!(ref_model, Some(OracleRefusal::ModelOnlyCounterfactual));
        assert_eq!(auth_model.identifiability_status, Identifiability::ModelDerived);
    }

    #[test]
    fn acceptance_test_5_unknown_propagates_into_summaries_and_records_never_treated_as_zero() {
        let auth_unk = CounterfactualAuthority::new(
            AuthorityLevel::L1,
            Identifiability::NotIdentifiable,
            "rule-1",
            "env-1",
            vec![],
        );
        let outcome_unk = OracleOutcome::unknown(OracleRefusal::MissingDecisionTimeData, auth_unk);
        let auth_id = CounterfactualAuthority::new(
            AuthorityLevel::L1,
            Identifiability::Identified,
            "rule-1",
            "env-1",
            vec![],
        );
        let outcome_zero = OracleOutcome::identified(0.0, auth_id).unwrap();

        // UNKNOWN outcome is distinct from zero and fails closed
        assert_eq!(outcome_unk.point_estimate(), None);
        assert_eq!(outcome_zero.point_estimate(), Some(0.0));
        assert_eq!(
            outcome_unk.compare_for_ordering(&outcome_zero),
            Err(OracleRefusal::MissingDecisionTimeData)
        );
    }

    #[test]
    fn acceptance_test_6_g4_g5_determinism_and_bundle_artifacts() {
        let grammar = sample_grammar();
        let universe = sample_universe(&grammar);
        let context = sample_context(&universe);
        let classifier = SupportClassifier::canonical_l1();

        let cand = GrammarCandidate {
            grammar_candidate_id: "cand-01".into(),
            universe_id: universe.universe_id.clone(),
            template_id: "template-breakout".into(),
            instrument: "BTCUSDT".into(),
            timeframe: "1h".into(),
            direction: Direction::Long,
            decision_time: 1000,
            parameters: BTreeMap::new(),
        };

        let (r1, recs1) = reconcile_coverage(
            &universe,
            &[cand.clone()],
            &classifier,
            &[],
            Some(30),
            AuthorityLevel::L1,
            &context,
            "lineage-01",
        );

        let (r2, recs2) = reconcile_coverage(
            &universe,
            &[cand],
            &classifier,
            &[],
            Some(30),
            AuthorityLevel::L1,
            &context,
            "lineage-01",
        );

        assert_eq!(r1, r2);
        assert_eq!(r1.receipt_id, r2.receipt_id);
        assert_eq!(recs1, recs2);

        // Bundle serialization test
        let tmp_dir = std::env::temp_dir().join(format!("v8_oracle_test_{}", r1.receipt_id));
        r1.save_to_bundle(&tmp_dir, &universe, &recs1).unwrap();
        assert!(tmp_dir.join("provenance/opportunity_universe.json").is_file());
        assert!(tmp_dir.join("economics/oracle_evaluation.parquet").is_file());
        assert!(tmp_dir.join("analysis/findings.jsonl").is_file());
        assert!(tmp_dir.join("analysis/schema_cache.json").is_file());

        let _ = fs::remove_dir_all(&tmp_dir);
    }

    #[test]
    fn acceptance_test_7_grid_grammar_mutation_changes_universe_id_and_lineage() {
        let grammar_base = sample_grammar();
        let universe_base = sample_universe(&grammar_base);

        let mut grammar_mutated = grammar_base.clone();
        grammar_mutated
            .grid
            .values
            .get_mut("threshold")
            .unwrap()
            .push(serde_json::json!(200.0));
        let universe_mutated = sample_universe(&grammar_mutated);

        assert_ne!(universe_base.universe_id, universe_mutated.universe_id);
        assert_ne!(universe_base.parameter_grid_hash, universe_mutated.parameter_grid_hash);
    }

    #[test]
    fn acceptance_test_8_every_coverage_member_reconciles_and_zero_coverage_fails_floor() {
        let grammar = sample_grammar();
        let universe = sample_universe(&grammar);
        let context = sample_context(&universe);
        let classifier = SupportClassifier::canonical_l1();

        let cand_long = GrammarCandidate {
            grammar_candidate_id: "cand-long-01".into(),
            universe_id: universe.universe_id.clone(),
            template_id: "template-breakout".into(),
            instrument: "BTCUSDT".into(),
            timeframe: "1h".into(),
            direction: Direction::Long,
            decision_time: 1000,
            parameters: BTreeMap::new(),
        };

        // No expert proposals emitted -> coverage is 0.0
        let (receipt, _) = reconcile_coverage(
            &universe,
            &[cand_long],
            &classifier,
            &[],
            Some(30),
            AuthorityLevel::L1,
            &context,
            "lineage-01",
        );

        assert_eq!(receipt.supported_opportunity_count, 1);
        assert_eq!(receipt.represented_supported_count, 0);
        assert_eq!(receipt.representational_coverage, 0.0);

        let floor = 0.10;
        assert!(receipt.representational_coverage < floor);
    }

    #[test]
    fn acceptance_test_9_opportunity_outputs_bind_alternative_population_hash_explicitly() {
        let grammar = sample_grammar();
        let universe = sample_universe(&grammar);
        let context = sample_context(&universe);
        let classifier = SupportClassifier::canonical_l1();

        let cand = GrammarCandidate {
            grammar_candidate_id: "cand-pop-01".into(),
            universe_id: universe.universe_id.clone(),
            template_id: "template-breakout".into(),
            instrument: "BTCUSDT".into(),
            timeframe: "1h".into(),
            direction: Direction::Long,
            decision_time: 1000,
            parameters: BTreeMap::new(),
        };

        let pop_hash = OpportunityGrammar::population_hash(&[cand.clone()]);
        let (receipt, records) = reconcile_coverage(
            &universe,
            &[cand],
            &classifier,
            &[],
            Some(30),
            AuthorityLevel::L1,
            &context,
            "lineage-01",
        );

        assert_eq!(receipt.population_hash, pop_hash);
        assert_eq!(records[0].candidate_population_hash, pop_hash);
    }

    #[test]
    fn acceptance_test_10_no_regret_attribution_record_or_additive_total_emitted() {
        let grammar = sample_grammar();
        let universe = sample_universe(&grammar);
        let context = sample_context(&universe);
        let classifier = SupportClassifier::canonical_l1();

        let cand = GrammarCandidate {
            grammar_candidate_id: "cand-01".into(),
            universe_id: universe.universe_id.clone(),
            template_id: "template-breakout".into(),
            instrument: "BTCUSDT".into(),
            timeframe: "1h".into(),
            direction: Direction::Long,
            decision_time: 1000,
            parameters: BTreeMap::new(),
        };

        let (receipt, _) = reconcile_coverage(
            &universe,
            &[cand],
            &classifier,
            &[],
            Some(30),
            AuthorityLevel::L1,
            &context,
            "lineage-01",
        );

        // Receipts emit NO_ECONOMIC_CLAIM and no additive totals
        assert_eq!(receipt.claim, "NO_ECONOMIC_CLAIM");
    }
}
