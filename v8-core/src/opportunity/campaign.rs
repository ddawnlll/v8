//! Execution Campaign & Portfolio Allocation Intent (Issue #231, #238, D-130).
//!
//! Owning Authority: V8 Constitution Rules 16, 25, 26.
//!
//! Constitutional Execution Topology:
//!   Reconciled Opportunity -> Selective Utility -> Portfolio Feasibility(CampaignIntent) -> ExecutionCampaign

use serde::{Deserialize, Serialize};
use crate::error::V8CoreError;
use crate::hash::Canon;
use super::exposure::EconomicExposureStructure;

/// Lifecycle status of an execution campaign.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub enum CampaignStatus {
    PendingAdmission,
    Active,
    Completed,
    Invalidated,
    Vetoed,
}

/// Execution leg within an authorized campaign.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct CampaignLeg {
    pub symbol: String,
    pub venue: String,
    pub target_size: f64,
    pub target_price: Option<f64>,
    pub filled_size: f64,
    pub average_fill_price: f64,
}

impl CampaignLeg {
    pub fn new(symbol: impl Into<String>, venue: impl Into<String>, target_size: f64, target_price: Option<f64>) -> Self {
        Self {
            symbol: symbol.into(),
            venue: venue.into(),
            target_size,
            target_price,
            filled_size: 0.0,
            average_fill_price: 0.0,
        }
    }
}

/// Campaign Intent emitted prior to portfolio feasibility check.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct CampaignIntent {
    pub intent_id: String,
    pub opportunity_id: String,
    pub decision_id: String,
    pub exposure: EconomicExposureStructure,
    pub requested_risk_r: f64,
    pub notional_budget_usdt: f64,
    pub created_time: i64,
}

impl CampaignIntent {
    pub fn new(
        opportunity_id: impl Into<String>,
        decision_id: impl Into<String>,
        exposure: EconomicExposureStructure,
        requested_risk_r: f64,
        notional_budget_usdt: f64,
        created_time: i64,
    ) -> Result<Self, V8CoreError> {
        let opportunity_id = opportunity_id.into();
        let decision_id = decision_id.into();

        if requested_risk_r <= 0.0 {
            return Err(V8CoreError::CampaignLifecycleError(format!(
                "requested_risk_r ({requested_risk_r}) must be positive"
            )));
        }

        let mut intent = Self {
            intent_id: String::new(),
            opportunity_id,
            decision_id,
            exposure,
            requested_risk_r,
            notional_budget_usdt,
            created_time,
        };
        intent.intent_id = intent.compute_id();
        Ok(intent)
    }

    pub fn compute_id(&self) -> String {
        let mut c = Canon::new();
        c.push_str("CampaignIntent");
        c.push_str(&self.opportunity_id);
        c.push_str(&self.decision_id);
        c.push_str(&self.exposure.exposure_id);
        c.push_f64(self.requested_risk_r);
        c.push_f64(self.notional_budget_usdt);
        c.push_i64(self.created_time);
        c.finish_blake3_hex()
    }
}

/// Execution Campaign (Primitive 6 of 7).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ExecutionCampaign {
    pub campaign_id: String,
    pub intent_id: String,
    pub opportunity_id: String,
    pub exposure: EconomicExposureStructure,
    pub allocated_capital_usdt: f64,
    pub target_risk_r: f64,
    pub legs: Vec<CampaignLeg>,
    pub status: CampaignStatus,
    pub invalidation_conditions: Vec<String>,
    pub start_time: i64,
    pub close_time: Option<i64>,
}

impl ExecutionCampaign {
    /// Instantiates an ExecutionCampaign strictly after portfolio approval.
    pub fn new(
        intent: &CampaignIntent,
        allocated_capital_usdt: f64,
        target_risk_r: f64,
        legs: Vec<CampaignLeg>,
        invalidation_conditions: Vec<String>,
        start_time: i64,
    ) -> Result<Self, V8CoreError> {
        if allocated_capital_usdt <= 0.0 {
            return Err(V8CoreError::CampaignLifecycleError(
                "allocated_capital_usdt must be positive".to_string(),
            ));
        }
        if legs.is_empty() {
            return Err(V8CoreError::CampaignLifecycleError(
                "Campaign legs cannot be empty".to_string(),
            ));
        }

        let mut campaign = Self {
            campaign_id: String::new(),
            intent_id: intent.intent_id.clone(),
            opportunity_id: intent.opportunity_id.clone(),
            exposure: intent.exposure.clone(),
            allocated_capital_usdt,
            target_risk_r,
            legs,
            status: CampaignStatus::PendingAdmission,
            invalidation_conditions,
            start_time,
            close_time: None,
        };
        campaign.campaign_id = campaign.compute_id();
        Ok(campaign)
    }

    pub fn compute_id(&self) -> String {
        let mut c = Canon::new();
        c.push_str("ExecutionCampaign");
        c.push_str(&self.intent_id);
        c.push_str(&self.opportunity_id);
        c.push_str(&self.exposure.exposure_id);
        c.push_f64(self.allocated_capital_usdt);
        c.push_f64(self.target_risk_r);
        c.push_str(&format!("{:?}", self.status));
        c.push_i64(self.start_time);
        
        c.push_list();
        c.push_count(self.legs.len());
        for leg in &self.legs {
            c.push_str(&leg.symbol);
            c.push_str(&leg.venue);
            c.push_f64(leg.target_size);
        }
        c.finish_blake3_hex()
    }
}

/// Portfolio feasibility parameters.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PortfolioFeasibilityConfig {
    pub max_gross_notional_usdt: f64,
    pub max_risk_per_opportunity_r: f64,
    pub max_underlying_concentration: f64,
    pub initial_cash_usdt: f64,
}

impl Default for PortfolioFeasibilityConfig {
    fn default() -> Self {
        Self {
            max_gross_notional_usdt: 1000.0,
            max_risk_per_opportunity_r: 1.0,
            max_underlying_concentration: 0.35,
            initial_cash_usdt: 1000.0,
        }
    }
}

/// Engine evaluating portfolio admission feasibility before instantiating an ExecutionCampaign.
pub struct PortfolioFeasibilityEngine;

impl PortfolioFeasibilityEngine {
    pub fn evaluate_intent(
        config: &PortfolioFeasibilityConfig,
        intent: &CampaignIntent,
        current_committed_notional: f64,
        start_time: i64,
    ) -> Result<ExecutionCampaign, V8CoreError> {
        let proposed_notional = intent.notional_budget_usdt;
        if current_committed_notional + proposed_notional > config.max_gross_notional_usdt {
            return Err(V8CoreError::CampaignLifecycleError(format!(
                "Portfolio capacity exceeded: current={current_committed_notional} + proposed={proposed_notional} > max={}",
                config.max_gross_notional_usdt
            )));
        }

        let allocated_capital = proposed_notional.min(config.initial_cash_usdt * config.max_underlying_concentration);
        let target_risk = intent.requested_risk_r.min(config.max_risk_per_opportunity_r);

        let mut legs = Vec::new();
        for leg in &intent.exposure.legs {
            legs.push(CampaignLeg::new(
                &leg.symbol,
                &leg.venue,
                leg.weight.abs() * allocated_capital,
                None,
            ));
        }

        ExecutionCampaign::new(
            intent,
            allocated_capital,
            target_risk,
            legs,
            vec!["MAX_LOSS_STOP".to_string(), "HORIZON_EXPIRY".to_string()],
            start_time,
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::opportunity::exposure::{EconomicExposureStructure, ExposureDirection};

    #[test]
    fn test_portfolio_feasibility_admission_and_capacity_bound() {
        let exp = EconomicExposureStructure::single_perp(
            "BTCUSDT",
            "BTC",
            "binance-um",
            "USDT",
            ExposureDirection::Long,
        )
        .unwrap();

        let intent = CampaignIntent::new(
            "opp_1",
            "dec_1",
            exp.clone(),
            1.0,
            250.0,
            1_000_000,
        )
        .unwrap();

        let config = PortfolioFeasibilityConfig::default();

        // 1. Within capacity
        let camp = PortfolioFeasibilityEngine::evaluate_intent(&config, &intent, 500.0, 1_000_000).unwrap();
        assert_eq!(camp.opportunity_id, "opp_1");
        assert_eq!(camp.legs.len(), 1);
        assert_eq!(camp.legs[0].symbol, "BTCUSDT");

        // 2. Capacity exceeded -> fails closed
        let breach = PortfolioFeasibilityEngine::evaluate_intent(&config, &intent, 900.0, 1_000_000);
        assert!(breach.is_err());
    }
}
