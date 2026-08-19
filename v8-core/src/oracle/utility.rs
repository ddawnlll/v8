//! Versioned, lexicographic UtilityContract (TARGET_ORACLE_SPEC §7).

#![allow(dead_code)]

use serde::{Deserialize, Serialize};

use super::taxonomy::OracleRefusal;

#[derive(Debug, Clone, Eq, PartialEq, Serialize, Deserialize)]
pub struct ModelIds {
    pub fee_model_id: String,
    pub funding_model_id: String,
    pub slippage_model_id: String,
    pub impact_model_id: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct HardConstraints {
    pub drawdown_max: f64,
    pub tail_risk_max: f64,
    pub capacity_max: f64,
    pub portfolio_heat_max: f64,
    pub coverage_min: f64,
    pub operational_rule_id: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ScalarPenalties {
    pub names: Vec<String>,
    pub weights: Vec<f64>,
    pub sensitivity_band: Vec<(f64, f64)>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct UtilityContract {
    pub contract_id: String,
    pub version: String,
    pub primary_objective: String,
    pub horizon: String,
    pub accounting_currency: String,
    pub models: ModelIds,
    pub hard_constraints: HardConstraints,
    pub optional_scalar_penalties: Option<ScalarPenalties>,
    pub stress_grid_id: String,
    pub effective_from: i64,
}

impl UtilityContract {
    /// Validate the declared feasible set only.  This type intentionally has
    /// no policy ranking or selection operation.
    pub fn validate(&self) -> Result<(), OracleRefusal> {
        let c = &self.hard_constraints;
        let complete = !self.contract_id.is_empty()
            && !self.version.is_empty()
            && self.primary_objective == "AFTER_COST_NET_UTILITY"
            && !self.horizon.is_empty()
            && !self.accounting_currency.is_empty()
            && !self.models.fee_model_id.is_empty()
            && !self.models.funding_model_id.is_empty()
            && !self.models.slippage_model_id.is_empty()
            && !self.models.impact_model_id.is_empty()
            && !c.operational_rule_id.is_empty()
            && !self.stress_grid_id.is_empty();
        let feasible = c.drawdown_max >= 0.0
            && c.tail_risk_max >= 0.0
            && c.capacity_max > 0.0
            && c.portfolio_heat_max > 0.0
            && (0.0..=1.0).contains(&c.coverage_min);
        let penalties_ok = self.optional_scalar_penalties.as_ref().is_none_or(|p| {
            p.names.len() == p.weights.len()
                && p.names.len() == p.sensitivity_band.len()
                && p.weights.iter().all(|w| w.is_finite())
                && p.sensitivity_band
                    .iter()
                    .all(|(lo, hi)| lo.is_finite() && hi.is_finite() && lo <= hi)
        });
        if complete && feasible && penalties_ok {
            Ok(())
        } else {
            Err(OracleRefusal::ConstraintInfeasible)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn valid() -> UtilityContract {
        UtilityContract {
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
                coverage_min: 0.1,
                operational_rule_id: "ops-v1".into(),
            },
            optional_scalar_penalties: None,
            stress_grid_id: "stress-v1".into(),
            effective_from: 1,
        }
    }

    #[test]
    fn contract_rejects_incomplete_or_infeasible_constraints_without_ranking() {
        let mut c = valid();
        assert_eq!(c.validate(), Ok(()));
        c.hard_constraints.coverage_min = 1.1;
        assert_eq!(c.validate(), Err(OracleRefusal::ConstraintInfeasible));
        c.hard_constraints.coverage_min = 0.1;
        c.models.impact_model_id.clear();
        assert_eq!(c.validate(), Err(OracleRefusal::ConstraintInfeasible));
    }
}
