//! Target Oracle O0-O3 substrate (TARGET_ORACLE_SPEC §§1-10, §16-19).
//!
//! This module owns taxonomy, typed contracts, PIT adaptation, the finite
//! measurement-frame grammar, support/authority classification, representational
//! coverage reconciliation, and evidence-bundle serialization.
//! Regret attribution (O4) and Target-policy optimization (O5) remain
//! deliberately absent.

pub mod artifacts;
pub mod authority;
pub mod coverage;
pub mod episode;
pub mod independence;
pub mod information;
pub mod opportunity;
pub mod support;
pub mod taxonomy;
pub mod utility;
