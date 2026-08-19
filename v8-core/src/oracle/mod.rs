//! Target Oracle O0-O1 substrate (TARGET_ORACLE_SPEC §§1-7, §17-19).
//!
//! This module owns only taxonomy, typed contracts, PIT adaptation, and the
//! finite measurement-frame grammar.  Support/authority classification,
//! coverage, evidence-bundle serialization, and policy evaluation remain
//! deliberately absent until O2-O3.

pub mod artifacts;
pub mod information;
pub mod opportunity;
pub mod taxonomy;
pub mod utility;
