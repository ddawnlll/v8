//! V8.5 D-153 Benchmark Fabric Module.
//!
//! Provides canonical benchmark evaluation ontology, scoring, execution,
//! qualification gating, external parity adapters, and diagnostic outcome projection.

pub mod types;
pub mod case;
pub mod receipt;
pub mod ledger;
pub mod scoring;
pub mod population;
pub mod synthetic;
pub mod external;
pub mod projection;
pub mod kaizen_feed;
pub mod observation;
pub mod runner;
pub mod report;

pub use types::*;
pub use case::*;
pub use receipt::*;
pub use ledger::*;
pub use scoring::*;
pub use population::*;
pub use synthetic::*;
pub use external::*;
pub use projection::*;
pub use kaizen_feed::*;
pub use observation::*;
pub use runner::*;
pub use report::*;
