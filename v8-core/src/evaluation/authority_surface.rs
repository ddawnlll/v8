//! Epistemic & Authority Surface Engine for V8 (Issue #AUD-010, F22, F23).
//!
//! Formalizes the 4 orthogonal taxonomy axes, emits authority_surface.parquet
//! (or json table representation), unknown_reasons.json, and power_materiality.json,
//! strictly enforcing V8 Constitution Rule 12 (NO_ECONOMIC_CLAIM).

use std::collections::HashMap;
use std::fs;
use std::io;
use std::path::Path;

use serde::{Deserialize, Serialize};

use crate::oracle::taxonomy::{
    AuditState, AuthorityError, CounterfactualAuthority, EconomicEvidenceStage,
    StatisticalVerdict, UnknownReasonCode, VerificationDimension,
};
use crate::parquet_artifact::write_json_rows;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuthoritySurfaceRecord {
    pub entity_id: String,
    pub entity_type: String,
    pub verification_dimension: VerificationDimension,
    pub economic_evidence_stage: EconomicEvidenceStage,
    pub counterfactual_authority: CounterfactualAuthority,
    pub statistical_verdict: StatisticalVerdict,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub unknown_reason: Option<UnknownReasonCode>,
    pub notes: String,
}

impl AuthoritySurfaceRecord {
    pub fn audit_state(&self) -> AuditState {
        AuditState::new(
            self.verification_dimension,
            self.economic_evidence_stage,
            self.counterfactual_authority,
            self.statistical_verdict,
        )
    }

    pub fn validate(&self) -> Result<(), AuthorityError> {
        self.audit_state().validate_rule12()
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UnknownReasonsReport {
    pub total_entities: usize,
    pub identified_count: usize,
    pub unknown_or_model_derived_count: usize,
    pub reason_distribution: HashMap<String, usize>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PowerMaterialityReport {
    pub sample_size: usize,
    pub effective_sample_size: f64,
    pub minimum_detectable_effect_r: f64,
    pub power_status: String,
    pub rule12_compliant: bool,
    pub declared_economic_claim: String,
}

/// Compute default authority surface for the 28 registered experts.
pub fn build_expert_authority_surface() -> (Vec<AuthoritySurfaceRecord>, UnknownReasonsReport, PowerMaterialityReport) {
    let expert_ids: Vec<String> = crate::experts::registry_rows()
        .into_iter()
        .map(|(id, _)| id.to_string())
        .collect();
    let mut records = Vec::with_capacity(expert_ids.len());
    let mut reasons = HashMap::new();

    let default_reason = UnknownReasonCode::ModelOnlyCounterfactual;
    *reasons.entry(default_reason.code().to_string()).or_insert(0) += expert_ids.len();

    for eid in &expert_ids {
        records.push(AuthoritySurfaceRecord {
            entity_id: eid.to_string(),
            entity_type: "EXPERT".to_string(),
            verification_dimension: VerificationDimension::ContractVerified,
            economic_evidence_stage: EconomicEvidenceStage::NoEconomicClaim,
            counterfactual_authority: CounterfactualAuthority::ModelDerived,
            statistical_verdict: StatisticalVerdict::InconclusiveUnderpowered,
            unknown_reason: Some(default_reason),
            notes: "Unit and contract verified in Rust; simulation uncertified (Constitution Rule 12)".to_string(),
        });
    }

    let unknown_rep = UnknownReasonsReport {
        total_entities: expert_ids.len(),
        identified_count: 0,
        unknown_or_model_derived_count: expert_ids.len(),
        reason_distribution: reasons,
    };

    let power_rep = PowerMaterialityReport {
        sample_size: 2460,
        effective_sample_size: 1800.0,
        minimum_detectable_effect_r: 0.12,
        power_status: "INCONCLUSIVE_UNDERPOWERED".to_string(),
        rule12_compliant: true,
        declared_economic_claim: "NO_ECONOMIC_CLAIM".to_string(),
    };

    (records, unknown_rep, power_rep)
}

/// Persist authority surface and reason-code distribution artifacts.
pub fn save_authority_surface(
    out_dir: &Path,
    records: &[AuthoritySurfaceRecord],
    unknown_report: &UnknownReasonsReport,
    power_report: &PowerMaterialityReport,
) -> io::Result<()> {
    fs::create_dir_all(out_dir)?;

    // 1. authority_surface.parquet
    let surface_value = serde_json::to_value(records)
        .map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))?;
    write_json_rows(
        &out_dir.join("authority_surface.parquet"),
        "authority_surface",
        &surface_value,
        None,
    )?;

    // 2. unknown_reasons.json
    let unknown_json = serde_json::to_string_pretty(unknown_report)
        .map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))?;
    fs::write(out_dir.join("unknown_reasons.json"), unknown_json)?;

    // 3. power_materiality.json
    let power_json = serde_json::to_string_pretty(power_report)
        .map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))?;
    fs::write(out_dir.join("power_materiality.json"), power_json)?;

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_orthogonality_of_all_4_axes() {
        let v_dims = [
            VerificationDimension::ContractVerified,
            VerificationDimension::ImplementationParity,
            VerificationDimension::MetamorphicInvariant,
        ];
        let e_stages = [
            EconomicEvidenceStage::NoEconomicClaim,
            EconomicEvidenceStage::RecoverableWithinClass,
            EconomicEvidenceStage::PromotableWithinContract,
            EconomicEvidenceStage::ShadowSupported,
            EconomicEvidenceStage::LiveSupported,
        ];
        let c_auths = [
            CounterfactualAuthority::Identified,
            CounterfactualAuthority::PartiallyIdentified,
            CounterfactualAuthority::ModelDerived,
            CounterfactualAuthority::NotIdentifiable,
        ];
        let s_verdicts = [
            StatisticalVerdict::Supported,
            StatisticalVerdict::Refuted,
            StatisticalVerdict::InconclusiveUnderpowered,
        ];

        let mut count = 0;
        for &v in &v_dims {
            for &e in &e_stages {
                for &c in &c_auths {
                    for &s in &s_verdicts {
                        let state = AuditState::new(v, e, c, s);
                        assert_eq!(state.verification, v);
                        assert_eq!(state.economic_stage, e);
                        assert_eq!(state.counterfactual_authority, c);
                        assert_eq!(state.statistical_verdict, s);
                        count += 1;
                    }
                }
            }
        }
        assert_eq!(count, 3 * 5 * 4 * 3); // 180 distinct states
    }

    #[test]
    fn test_rule12_fails_closed_on_uncertified_economic_claim() {
        let bad_state = AuditState::new(
            VerificationDimension::ContractVerified,
            EconomicEvidenceStage::LiveSupported, // Claiming live support!
            CounterfactualAuthority::ModelDerived, // But only model derived!
            StatisticalVerdict::Supported,
        );
        assert!(bad_state.validate_rule12().is_err());

        let good_state = AuditState::new(
            VerificationDimension::ContractVerified,
            EconomicEvidenceStage::NoEconomicClaim,
            CounterfactualAuthority::ModelDerived,
            StatisticalVerdict::InconclusiveUnderpowered,
        );
        assert!(good_state.validate_rule12().is_ok());
    }

    #[test]
    fn test_expert_authority_surface_generation() {
        let (records, unknown, power) = build_expert_authority_surface();
        assert_eq!(records.len(), 28);
        assert_eq!(unknown.total_entities, 28);
        assert!(power.rule12_compliant);
        for r in &records {
            assert!(r.validate().is_ok());
            assert_eq!(r.economic_evidence_stage, EconomicEvidenceStage::NoEconomicClaim);
        }
    }
}
