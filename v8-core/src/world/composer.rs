//! Multi-Generator World Composer & Population Partition Manager (D-150, Foundry v2).
//!
//! Composes multi-generator scenarios, manages 3 synthetic populations (Dev, Qualification, Novelty),
//! and evaluates Generative Ensemble agreement.

use serde::{Deserialize, Serialize};
use crate::world::spec::{SyntheticPopulation, WorldBar, WorldFamily, WorldReceipt, WorldSpec};
use crate::world::structural::StructuralWorldGenerator;
use crate::world::stationary_bootstrap::StationaryBootstrapGenerator;
use crate::world::stochastic_vol::StochasticVolatilityGenerator;
use crate::world::surgery::{CounterfactualSurgeryEngine, SurgeryConfig};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum EnsembleAgreementStatus {
    RobustnessPass,
    GeneratorDisagreementContested,
    UniversalFailure,
}

pub struct WorldComposer;

impl WorldComposer {
    /// Generates composed scenario combining structural regime + stochastic vol + surgery.
    pub fn compose_composite_world(
        spec: &WorldSpec,
        source_real_bars: Option<&[WorldBar]>,
    ) -> WorldReceipt {
        match spec.family {
            WorldFamily::StructuralRegime | WorldFamily::JumpCascade => {
                StructuralWorldGenerator::generate(spec)
            }
            WorldFamily::StochasticVolatility => {
                StochasticVolatilityGenerator::generate(spec, 0.02, 0.15, 0.80)
            }
            WorldFamily::StationaryBootstrap => {
                if let Some(src) = source_real_bars {
                    StationaryBootstrapGenerator::generate(src, 24, spec.seed, spec)
                } else {
                    StructuralWorldGenerator::generate(spec)
                }
            }
            WorldFamily::CounterfactualSurgery | WorldFamily::LiquidityStressWorld => {
                if let Some(src) = source_real_bars {
                    let cfg = SurgeryConfig::default();
                    CounterfactualSurgeryEngine::apply_multi_axis_surgery(src, &cfg, spec.seed, spec)
                } else {
                    StructuralWorldGenerator::generate(spec)
                }
            }
            _ => StructuralWorldGenerator::generate(spec),
        }
    }

    /// Evaluates policy agreement across 5 diverse generator families.
    pub fn evaluate_ensemble_agreement(
        passed_families: &[WorldFamily],
        required_threshold: usize,
    ) -> EnsembleAgreementStatus {
        if passed_families.len() >= required_threshold {
            EnsembleAgreementStatus::RobustnessPass
        } else if passed_families.is_empty() {
            EnsembleAgreementStatus::UniversalFailure
        } else {
            EnsembleAgreementStatus::GeneratorDisagreementContested
        }
    }
}
