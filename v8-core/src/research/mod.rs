//! Research Integrity & Holdout Management (V8.5 M4 Core Subsystem, D-147, D-149, Rules 11, 17, 18, 34, 35).
//!
//! Provides lineage-aware data role ledgers, irreversible holdout burn receipts, and trial debt tracking.

pub mod data_role;
pub mod holdout;
pub mod statistical_plan;

pub use data_role::{DataRoleLedger, DataSegmentRole};
pub use holdout::HoldoutBurnReceipt;
pub use statistical_plan::StatisticalPlan;
