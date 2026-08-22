//! Double-Entry Cashflow Conservation Auditor (D-132, Rule 9 & Rule 12).

#[derive(Debug, Clone, PartialEq)]
pub struct CashflowConservationReport {
    pub passed: bool,
    pub initial_equity: f64,
    pub final_equity: f64,
    pub sum_realized_cashflows: f64,
    pub sum_open_position_values: f64,
    pub discrepancy: f64,
}

pub struct CashflowAuditor;

impl CashflowAuditor {
    pub const CONSERVATION_EPSILON: f64 = 1e-8;

    /// Validates double-entry accounting conservation:
    /// Final_Equity == Initial_Equity + Net_Cashflows + Open_Positions_Unrealized
    pub fn audit_conservation(
        initial_equity: f64,
        final_equity: f64,
        net_cashflows: &[f64],
        open_positions_unrealized: f64,
    ) -> Result<CashflowConservationReport, String> {
        let sum_cf: f64 = net_cashflows.iter().sum();
        let expected_final = initial_equity + sum_cf + open_positions_unrealized;
        let discrepancy = (final_equity - expected_final).abs();

        let report = CashflowConservationReport {
            passed: discrepancy <= Self::CONSERVATION_EPSILON,
            initial_equity,
            final_equity,
            sum_realized_cashflows: sum_cf,
            sum_open_position_values: open_positions_unrealized,
            discrepancy,
        };

        if !report.passed {
            return Err(format!(
                "CASHFLOW_CONSERVATION_VIOLATION: Initial={initial_equity}, Final={final_equity}, SumCF={sum_cf}, Discrepancy={discrepancy}"
            ));
        }

        Ok(report)
    }
}
