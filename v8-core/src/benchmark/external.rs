//! Disagreement detection (D-153 §§2.6, 4.6; BFS-009, BFS-015).
//!
//! # What was removed, and why (#329)
//!
//! This file used to carry `CommodityExecutionAdapter`, `LeanParityAdapter`,
//! `SkfolioParityAdapter`, `VectorBtParityAdapter` and `ExecutionParityReport`.
//! They are deleted, not fixed, because their `evaluate_parity(policy_id)` could
//! not be repaired in place:
//!
//! - the `policy_id` argument was bound as `_policy_id` and discarded, so the
//!   "policy-bound" claim in D-153 §2.6 was structurally absent;
//! - each compared two hardcoded arrays written in the same function
//!   (e.g. `[0.012, -0.005, …]` against `[0.0121, -0.0049, …]`) that are neither
//!   V8 output nor the named engine's output, chosen to land inside that
//!   adapter's own tolerance, so `parity_passed` was `true` by construction and
//!   no input could make it `false`;
//! - `fill_timing_mae_ms` was the literal `0.0`, which reads as "measured, zero
//!   timing error" for a quantity never observed — an absence disguised as a
//!   perfect result, against AGENTS.md's anti-synthetic-data rule;
//! - `maximum_drawdown_discrepancy_bps` was `pnl_discrepancy_bps * 1.5` (or
//!   `* 1.2`, `* 1.1`) — arithmetic on an unrelated quantity dressed up as a
//!   drawdown measurement;
//! - `parity_passed` was decided by a bps tolerance, which
//!   `PARITY_AND_IDENTITY_SPEC` §3 forbids ("tolerance-based comparison is not
//!   permitted anywhere in the parity path").
//!
//! Replacements live in [`crate::benchmark::parity`]: adapters there consume
//! physically verified trade-ledger artifacts, bind policy/case/engine/mapping
//! identity into a [`ParityReceipt`], compare by IEEE-754 bit pattern, and yield
//! `DataBlocked` rather than a pass when data is absent.
//!
//! The detector below survives because the semantic checks it performs are real
//! invariants. `check_order_semantics` now consults
//! [`SemanticMapping::default`] instead of a private list, so there is one
//! declaration of supported order types in the crate.

use crate::benchmark::parity::{ParityReceipt, SemanticMapping};

/// Detects divergence, terminal-sign reversals, and unsupported semantics
/// (D-153 §2.6; BFS-009, BFS-015).
pub struct DisagreementDetector;

impl DisagreementDetector {
    /// Fail if a completed parity run did not reach exact agreement.
    ///
    /// `DataBlocked` is an `Err` here rather than a silent pass: an adapter that
    /// could not read its artifacts has not established parity, and callers that
    /// treat "no evidence" as "no disagreement" is exactly the bug this path used
    /// to have.
    pub fn assert_parity(receipt: &ParityReceipt) -> Result<(), String> {
        if !receipt.verify_identity() {
            return Err(format!(
                "Parity receipt identity does not match its inputs ({}): \
                 the receipt was edited after it was computed",
                receipt.parity_identity
            ));
        }
        match &receipt.outcome {
            crate::benchmark::parity::ParityOutcome::ExactMatch => Ok(()),
            other => Err(format!(
                "Parity not established for {} ({}): {}",
                receipt.engine.identity(),
                other.code(),
                other.detail()
            )),
        }
    }

    /// Detects terminal PnL sign disagreement between V8 and external referee (BFS-009).
    pub fn check_sign_agreement(
        native_terminal_pnl: f64,
        external_terminal_pnl: f64,
    ) -> Result<(), String> {
        if (native_terminal_pnl > 0.0 && external_terminal_pnl < 0.0)
            || (native_terminal_pnl < 0.0 && external_terminal_pnl > 0.0)
        {
            return Err("Execution parity failure: terminal PnL sign disagreement between V8 and external referee (BFS-009)".into());
        }
        Ok(())
    }

    /// Verifies external order execution semantics against the registered
    /// mapping (BFS-015).
    pub fn check_order_semantics(order_type: &str) -> Result<(), String> {
        if SemanticMapping::default().supports_order_type(order_type) {
            Ok(())
        } else {
            Err(format!(
                "Unsupported external order semantics: {order_type} (BFS-015)"
            ))
        }
    }
}
