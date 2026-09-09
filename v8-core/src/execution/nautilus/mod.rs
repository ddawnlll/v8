//! Native NautilusTrader integration module for V8.
//!
//! Replaces legacy simulated execution and second accounting engine with
//! production-grade event-driven NautilusTrader 0.63.0 matching, portfolio,
//! and accounting subsystems.

pub mod data;
pub mod runner;
pub mod strategy;

pub use runner::run_nautilus_simulation;
