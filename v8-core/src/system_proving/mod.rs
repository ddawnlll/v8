//! Full-Chain System Proving Ground (V8.5 M3 Core Subsystem, D-147, D-149, Rules 19, 20).
//!
//! Evaluates the full multi-expert, risk, execution, and double-entry ledger pipeline.

pub mod attribution;
pub mod metrics;
pub mod receipt;
pub mod run;

pub use attribution::{FailureAttributionBreakdown, FailureDomain};
pub use metrics::SystemRobustnessVector;
pub use receipt::SystemProvingGroundReceipt;
pub use run::SystemProvingGroundRunner;
