//! V8 Kaizen Continuous Improvement Engine — Policy Challenger Specification & Parameter Bounds.
//!
//! Owning Authority:
//! - `KAIZEN_ENGINE_SPEC.md` §3 (Hypothesis & Challenger Registry)
//! - `HYPOTHESIS_LAB_PROTOCOL.md` §1–4
//! - arXiv:2606.01650 (*Post-Selection Inference, Covariance Lineage, and Overfitting Penalties in Quantitative Strategy Search*)

use std::collections::HashMap;
use serde::{Deserialize, Serialize};
use sha1::{Digest, Sha1};

use crate::kaizen::diagnosis::{ExpertId, VariantId};
use crate::kaizen::hypothesis::HypothesisError;

/// Discrete parameter range for candidate grids.
///
/// Continuous searches are forbidden without discrete pre-registration (Invariant I1).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct DiscreteParameterRange {
    pub name: String,
    pub discrete_values: Vec<f64>,
}

impl DiscreteParameterRange {
    pub fn new(name: &str, discrete_values: Vec<f64>) -> Result<Self, HypothesisError> {
        if discrete_values.is_empty() {
            return Err(HypothesisError::UnboundedSearchSpace(format!(
                "Parameter '{name}' has empty discrete values"
            )));
        }
        for v in &discrete_values {
            if v.is_nan() || v.is_infinite() {
                return Err(HypothesisError::UnboundedSearchSpace(format!(
                    "Parameter '{name}' contains non-finite value: {v}"
                )));
            }
        }
        Ok(Self {
            name: name.to_string(),
            discrete_values,
        })
    }
}

/// Bounded challenger candidate family specification.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ChallengerFamilySpec {
    pub family_id: String,
    pub base_expert_id: ExpertId,
    pub base_variant_id: VariantId,
    pub description: String,
    pub discrete_parameters: Vec<DiscreteParameterRange>,
    pub is_bounded: bool,
}

/// Concrete instantiated candidate variant within a challenger family.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ChallengerVariant {
    pub variant_id: VariantId,
    pub family_id: String,
    pub parameter_values: HashMap<String, f64>,
    pub variant_hash: String,
}

impl ChallengerFamilySpec {
    pub fn new(
        family_id: &str,
        base_expert_id: &str,
        base_variant_id: &str,
        description: &str,
        discrete_parameters: Vec<DiscreteParameterRange>,
    ) -> Result<Self, HypothesisError> {
        if discrete_parameters.is_empty() {
            return Err(HypothesisError::UnboundedSearchSpace(
                "Challenger family must specify at least one discrete parameter range".to_string(),
            ));
        }

        let spec = Self {
            family_id: family_id.to_string(),
            base_expert_id: base_expert_id.to_string(),
            base_variant_id: base_variant_id.to_string(),
            description: description.to_string(),
            discrete_parameters,
            is_bounded: true,
        };

        spec.validate()?;
        Ok(spec)
    }

    /// Validates finite bounded lattice invariants.
    pub fn validate(&self) -> Result<(), HypothesisError> {
        if !self.is_bounded {
            return Err(HypothesisError::UnboundedSearchSpace(
                "Unbounded parameter space is strictly forbidden".to_string(),
            ));
        }
        if self.discrete_parameters.is_empty() {
            return Err(HypothesisError::UnboundedSearchSpace(
                "Discrete parameters cannot be empty".to_string(),
            ));
        }
        for p in &self.discrete_parameters {
            if p.discrete_values.is_empty() {
                return Err(HypothesisError::UnboundedSearchSpace(format!(
                    "Parameter '{}' has no discrete values",
                    p.name
                )));
            }
        }
        Ok(())
    }

    /// Total number of discrete candidate points in the Cartesian grid.
    pub fn grid_size(&self) -> usize {
        self.discrete_parameters
            .iter()
            .map(|p| p.discrete_values.len())
            .product()
    }

    /// Expands the Cartesian product of discrete parameter points into concrete variants.
    pub fn generate_variants(&self) -> Result<Vec<ChallengerVariant>, HypothesisError> {
        self.validate()?;

        let mut current_configs: Vec<HashMap<String, f64>> = vec![HashMap::new()];

        for param in &self.discrete_parameters {
            let mut next_configs = Vec::new();
            for config in current_configs {
                for &val in &param.discrete_values {
                    let mut extended = config.clone();
                    extended.insert(param.name.clone(), val);
                    next_configs.push(extended);
                }
            }
            current_configs = next_configs;
        }

        let mut variants = Vec::with_capacity(current_configs.len());
        for (idx, params) in current_configs.into_iter().enumerate() {
            let variant_id = format!("{}_var_{:04}", self.family_id, idx);

            // Compute deterministic variant hash from sorted parameter keys and values
            let mut sorted_keys: Vec<&String> = params.keys().collect();
            sorted_keys.sort_unstable();

            let mut hasher = Sha1::new();
            hasher.update(self.family_id.as_bytes());
            hasher.update(self.base_expert_id.as_bytes());
            for k in sorted_keys {
                hasher.update(k.as_bytes());
                hasher.update(params[k].to_le_bytes());
            }
            let digest = hasher.finalize();
            let variant_hash: String = digest.iter().map(|b| format!("{:02x}", b)).collect();

            variants.push(ChallengerVariant {
                variant_id,
                family_id: self.family_id.clone(),
                parameter_values: params,
                variant_hash,
            });
        }

        Ok(variants)
    }
}
