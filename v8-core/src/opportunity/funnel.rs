//! Opportunity Capture Funnel & Attrition Diagnostic Engine (V8.3 Phase II).
//!
//! Owning Authority: V8 Constitution Rules 6, 12, 18, 20, 21, 24, 25; CC-RES-V8.3-GL-001.
//!
//! Funnel Topology:
//!   Stage 1: TARGET ORACLE UNIVERSE (Ex-post counterfactual upper bound)
//!   Stage 2: PIT GRAMMAR DETECTED (Causal structural episode instantiation)
//!   Stage 3: INFORMATIVE WITNESS SUPPORT (At least one high-conviction in-habitat witness)
//!   Stage 4: RECONCILIATION ACTIONABLE (Aggregate stance = Supported, entropy < threshold)
//!   Stage 5: NET VALUE POSITIVE (Gross edge > Friction + Uncertainty hurdle)
//!   Stage 6: PORTFOLIO ADMISSIBLE (Within risk, margin, and concentration bounds)
//!   Stage 7: EXECUTED & REALIZED POSITIVE (Replay completed with net profit)

#![allow(dead_code)]

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// One stage of the Opportunity Capture Funnel.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OpportunityFunnelStage {
    pub stage_index: usize,
    pub stage_name: String,
    pub input_count: usize,
    pub output_count: usize,
    pub dropped_count: usize,
    pub stage_retention_rate: f64,
    pub drop_reasons: HashMap<String, usize>,
    pub potential_utility_r: f64,
    pub lost_utility_r: f64,
}

/// Consolidated Opportunity Capture Funnel Report.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OpportunityCaptureFunnelReport {
    pub as_of_time: i64,
    pub symbol: String,
    pub total_oracle_universe: usize,
    pub pit_grammar_detected: usize,
    pub informative_witness_supported: usize,
    pub reconciliation_actionable: usize,
    pub net_value_positive: usize,
    pub portfolio_admitted: usize,
    pub execution_completed: usize,
    pub realized_positive: usize,
    pub stages: Vec<OpportunityFunnelStage>,
}

impl OpportunityCaptureFunnelReport {
    pub fn overall_capture_efficiency(&self) -> f64 {
        if self.total_oracle_universe == 0 {
            0.0
        } else {
            self.realized_positive as f64 / self.total_oracle_universe as f64
        }
    }
}

/// Engine for recording and analyzing the 7-stage opportunity capture funnel.
#[derive(Default)]
pub struct OpportunityFunnelTracker {
    pub oracle_opportunities: usize,
    pub pit_detected: usize,
    pub witness_supported: usize,
    pub reconcile_actionable: usize,
    pub net_value_passed: usize,
    pub portfolio_admitted: usize,
    pub executed_completed: usize,
    pub realized_positive: usize,
    pub drop_tallies: [HashMap<String, usize>; 7],
}

impl OpportunityFunnelTracker {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn record_oracle_opportunity(&mut self) {
        self.oracle_opportunities += 1;
    }

    pub fn record_pit_detection(&mut self) {
        self.pit_detected += 1;
    }

    pub fn record_pit_drop(&mut self, reason: impl Into<String>) {
        *self.drop_tallies[0].entry(reason.into()).or_insert(0) += 1;
    }

    pub fn record_witness_support(&mut self) {
        self.witness_supported += 1;
    }

    pub fn record_witness_drop(&mut self, reason: impl Into<String>) {
        *self.drop_tallies[1].entry(reason.into()).or_insert(0) += 1;
    }

    pub fn record_reconcile_actionable(&mut self) {
        self.reconcile_actionable += 1;
    }

    pub fn record_reconcile_drop(&mut self, reason: impl Into<String>) {
        *self.drop_tallies[2].entry(reason.into()).or_insert(0) += 1;
    }

    pub fn record_net_value_passed(&mut self) {
        self.net_value_passed += 1;
    }

    pub fn record_net_value_drop(&mut self, reason: impl Into<String>) {
        *self.drop_tallies[3].entry(reason.into()).or_insert(0) += 1;
    }

    pub fn record_portfolio_admitted(&mut self) {
        self.portfolio_admitted += 1;
    }

    pub fn record_portfolio_drop(&mut self, reason: impl Into<String>) {
        *self.drop_tallies[4].entry(reason.into()).or_insert(0) += 1;
    }

    pub fn record_execution(&mut self, is_positive: bool) {
        self.executed_completed += 1;
        if is_positive {
            self.realized_positive += 1;
        } else {
            *self.drop_tallies[5].entry("NEGATIVE_REALIZED_OUTCOME".to_string()).or_insert(0) += 1;
        }
    }

    pub fn generate_report(&self, symbol: &str, as_of_time: i64) -> OpportunityCaptureFunnelReport {
        let stage_names = [
            "1. TARGET_ORACLE_UNIVERSE",
            "2. PIT_GRAMMAR_DETECTED",
            "3. WITNESS_SUPPORTED",
            "4. RECONCILIATION_ACTIONABLE",
            "5. NET_VALUE_POSITIVE",
            "6. PORTFOLIO_ADMITTED",
            "7. REALIZED_POSITIVE",
        ];

        let counts = [
            self.oracle_opportunities,
            self.pit_detected,
            self.witness_supported,
            self.reconcile_actionable,
            self.net_value_passed,
            self.portfolio_admitted,
            self.realized_positive,
        ];

        let mut stages = Vec::new();
        for i in 0..6 {
            let input = counts[i];
            let output = counts[i + 1];
            let dropped = input.saturating_sub(output);
            let ret_rate = if input > 0 { output as f64 / input as f64 } else { 1.0 };

            stages.push(OpportunityFunnelStage {
                stage_index: i + 1,
                stage_name: stage_names[i].to_string(),
                input_count: input,
                output_count: output,
                dropped_count: dropped,
                stage_retention_rate: ret_rate,
                drop_reasons: self.drop_tallies[i].clone(),
                potential_utility_r: 0.0,
                lost_utility_r: 0.0,
            });
        }

        OpportunityCaptureFunnelReport {
            as_of_time,
            symbol: symbol.to_string(),
            total_oracle_universe: self.oracle_opportunities,
            pit_grammar_detected: self.pit_detected,
            informative_witness_supported: self.witness_supported,
            reconciliation_actionable: self.reconcile_actionable,
            net_value_positive: self.net_value_passed,
            portfolio_admitted: self.portfolio_admitted,
            execution_completed: self.executed_completed,
            realized_positive: self.realized_positive,
            stages,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_funnel_tracking_and_retention_computation() {
        let mut tracker = OpportunityFunnelTracker::new();

        // 100 Oracle Opportunities
        for _ in 0..100 {
            tracker.record_oracle_opportunity();
        }

        // 60 Detected by Grammar (40 missed due to H1 recall)
        for _ in 0..60 {
            tracker.record_pit_detection();
        }
        for _ in 0..40 {
            tracker.record_pit_drop("GRAMMAR_VOLATILITY_THRESHOLD_MISS");
        }

        // 45 Supported by Witnesses (15 dropped due to H2 abstention)
        for _ in 0..45 {
            tracker.record_witness_support();
        }
        for _ in 0..15 {
            tracker.record_witness_drop("WITNESS_OUT_OF_HABITAT");
        }

        // 40 Actionable in Reconciliation (5 dropped due to H4 contradiction)
        for _ in 0..40 {
            tracker.record_reconcile_actionable();
        }
        for _ in 0..5 {
            tracker.record_reconcile_drop("CONTRADICTION_ENTROPY_HIGH");
        }

        // 35 Passed Net Value Hurdle (5 dropped due to H3 sub-friction)
        for _ in 0..35 {
            tracker.record_net_value_passed();
        }
        for _ in 0..5 {
            tracker.record_net_value_drop("SUB_FRICTION_HURDLE");
        }

        // 30 Admitted to Portfolio (5 dropped due to capacity)
        for _ in 0..30 {
            tracker.record_portfolio_admitted();
        }
        for _ in 0..5 {
            tracker.record_portfolio_drop("MAX_CONCENTRATION_REACHED");
        }

        // 25 Realized Positive (5 stopped out)
        for _ in 0..25 {
            tracker.record_execution(true);
        }
        for _ in 0..5 {
            tracker.record_execution(false);
        }

        let report = tracker.generate_report("BTCUSDT", 1_000_000);
        assert_eq!(report.total_oracle_universe, 100);
        assert_eq!(report.realized_positive, 25);
        assert_eq!(report.overall_capture_efficiency(), 0.25);
        assert_eq!(report.stages.len(), 6);
        assert_eq!(report.stages[0].dropped_count, 40);
        assert_eq!(report.stages[0].stage_retention_rate, 0.60);
    }
}
