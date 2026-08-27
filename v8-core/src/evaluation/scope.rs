//! Opportunity Universe Breadth vs Capital Allocation Diagnostics (D-147, D-149, M2).
//!
//! Invariant: Broad opportunity universe may legally produce zero allocations or single-asset
//! allocation without failing qualification (Anti-Forced-Diversification Rule / AF-T10).

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Diagnostic tracking of universe candidates vs executed capital allocation.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ScopeDiagnostics {
    pub universe_id: String,
    pub total_universe_symbols: usize,
    pub symbol_candidates_count: HashMap<String, usize>,
    pub symbol_allocated_capital: HashMap<String, f64>,
}

impl ScopeDiagnostics {
    pub fn new(universe_id: String, symbols: Vec<String>) -> Self {
        let mut symbol_candidates_count = HashMap::new();
        let mut symbol_allocated_capital = HashMap::new();
        for s in &symbols {
            symbol_candidates_count.insert(s.clone(), 0);
            symbol_allocated_capital.insert(s.clone(), 0.0);
        }

        Self {
            universe_id,
            total_universe_symbols: symbols.len(),
            symbol_candidates_count,
            symbol_allocated_capital,
        }
    }

    /// Records allocation. Single-asset allocation is fully legal even in a multi-symbol universe.
    pub fn record_allocation(&mut self, symbol: &str, candidates: usize, capital: f64) {
        self.symbol_candidates_count.insert(symbol.to_string(), candidates);
        self.symbol_allocated_capital.insert(symbol.to_string(), capital);
    }

    /// Verifies that single-asset or zero allocation is legal and never causes an invariant error.
    pub fn is_legal_scope_state(&self) -> bool {
        // Zero allocations or single-asset allocation are valid states when no edge exists
        true
    }
}
