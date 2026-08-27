//! Market World Foundry v2 (V8.5 M2b Core Subsystem, D-147, D-149, D-150).
//!
//! 14 Generator fleet, Hawkes processes, cross-asset copulas, stationary bootstrap,
//! path topology, multi-axis surgery, adversarial reverse-stress search, and 3-population isolation.

pub mod composer;
pub mod cross_asset;
pub mod learned;
pub mod metamorphic;
pub mod passport;
pub mod path_topology;
pub mod resample;
pub mod reverse_stress;
pub mod spec;
pub mod stationary_bootstrap;
pub mod stochastic_vol;
pub mod structural;
pub mod surgery;

pub use composer::{EnsembleAgreementStatus, WorldComposer};
pub use cross_asset::CrossAssetContagionGenerator;
pub use learned::LearnedChallengerGenerator;
pub use metamorphic::{MetamorphicTransform, MetamorphicWorldGenerator};
pub use passport::GeneratorPassport;
pub use path_topology::{PathGeometryType, PathTopologyGenerator};
pub use resample::BlockResampleGenerator;
pub use reverse_stress::{MinimalDefeaterReceipt, ReverseStressSearchEngine, ReverseStressVector};
pub use spec::{
    MultiAssetBarSnapshot, MultiAssetWorldReceipt, SyntheticPopulation, WorldBar, WorldFamily,
    WorldReceipt, WorldSpec,
};
pub use stationary_bootstrap::StationaryBootstrapGenerator;
pub use stochastic_vol::StochasticVolatilityGenerator;
pub use structural::{MarketRegimeState, RegimeTransitionMatrix, StructuralWorldGenerator};
pub use surgery::{CounterfactualSurgeryEngine, SurgeryConfig};
