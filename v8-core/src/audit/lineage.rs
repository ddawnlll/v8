//! Point-In-Time (PIT) & Zero-Leakage Lineage Auditor (D-132, Rule 3).

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LineageAuditReport {
    pub passed: bool,
    pub records_checked: usize,
    pub pit_leak_violations: Vec<String>,
}

pub struct LineageAuditor;

impl LineageAuditor {
    /// Validates that no feature or input record has availability time exceeding the decision clock.
    pub fn audit_pit_causality(
        decision_clock: i64,
        input_available_times: &[(String, i64)],
    ) -> Result<(), String> {
        for (name, avail_time) in input_available_times {
            if *avail_time > decision_clock {
                return Err(format!(
                    "PIT_FUTURE_LEAKAGE: Input '{name}' available at {avail_time} > decision clock {decision_clock}"
                ));
            }
        }
        Ok(())
    }
}
