//! V8 Judicial Review, Execution Oversight & Agent Accountability Plane (D-134, Rules 36-42).
//!
//! Enforces:
//! 1. Four-Plane Separation of Powers (Constitution -> Judiciary -> Kaizen -> Implementer -> Ledger).
//! 2. Independent Execution Oversight Corps with No-Naked-Veto and Expedited Appeal.
//! 3. Typestate ExecutionMandate with Constitution Tree Hash Pinning.
//! 4. Blind Adversarial Audit and Anti-Clone Diversity.
//! 5. External Constitutional Audit of Kaizen Orchestration.

pub mod mandate;
pub mod veto;
pub mod oversight;
pub mod kaizen_boundary;

#[cfg(test)]
mod tests;

pub use mandate::{ExecutionMandate, MobilizationTier, TaskLease};
pub use veto::{VetoProof, JudicialVetoGate, ExpeditedAppealEngine, VetoDecision};
pub use oversight::{ProceduralCommissioner, TechnicalCommissioner, BlindAuditBundle, JudicialVerdict};
pub use kaizen_boundary::KaizenConstitutionalAuditor;
