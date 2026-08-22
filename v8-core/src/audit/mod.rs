//! Central Constitutional Audit Kernel (D-132, Rules 28-35, PH2-003A.2).
//!
//! Enforces:
//! 1. Autonomous, non-optional inline auditing across all computation stages.
//! 2. Separation of powers: IMPLEMENTER != AUDITOR != VERDICT AUTHORITY.
//! 3. 8-Point Automated Audit-of-Audit Sabotage Test Suite.

pub mod authority;
pub mod lineage;
pub mod cashflow;
pub mod reconciliation;
pub mod independence;
pub mod sabotage;
