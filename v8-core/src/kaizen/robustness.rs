//! V8 Kaizen Continuous Improvement Engine — Robustness Surface & Plateau/Cliff Analysis.
//!
//! Owning Authority:
//! - `KAIZEN_ENGINE_SPEC.md` §4 (DEV Robustness Surfaces)
//! - `EVALUATION_EVIDENCE_SYSTEM.md` §4 (`robustness/parameter_surface.parquet`)
//! - arXiv:2603.09219 (*AlgoXpert: Finding Parameter Plateaus and Preventing Fragility Cliffs*)

use std::collections::HashMap;
use serde::{Deserialize, Serialize};

use crate::kaizen::challenger::ChallengerFamilySpec;
use crate::kaizen::diagnosis::VariantId;
use crate::kaizen::hypothesis::HypothesisError;

pub type MetricId = String;

/// Typed verdicts for robustness surface analysis.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum RobustnessVerdict {
    /// Wide parameter neighborhood maintains stable high utility without collapse.
    Plateau,
    /// Neighborhood exhibits sharp degradation or catastrophic cliff collapse (> max_cliff_drop).
    Cliff,
    /// Point or neighborhood fails the fundamental utility floor (e.g. net expectancy <= 0).
    NonViable,
    /// Insufficient sample size / trade count across the evaluation window (N < min_events_n).
    InsufficientN,
}

/// Utility-contract plateau and cliff criteria.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PlateauCriterion {
    pub primary_utility: MetricId,
    pub utility_floor: f64,
    pub secondary_stability_metric: Option<MetricId>,
    pub secondary_floor: Option<f64>,
    pub alpha: Option<f64>,
    pub max_cliff_drop: f64,
    pub min_events_n: u64,
    pub epsilon_floor: f64,
}

impl Default for PlateauCriterion {
    fn default() -> Self {
        Self {
            primary_utility: "net_expectancy_r".to_string(),
            utility_floor: 0.0,
            secondary_stability_metric: Some("sharpe".to_string()),
            secondary_floor: Some(0.0),
            alpha: Some(0.90),
            max_cliff_drop: 0.30,
            min_events_n: 30,
            epsilon_floor: 0.01,
        }
    }
}

/// A discrete point on the finite parameter lattice.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct RobustnessPoint {
    pub variant_id: VariantId,
    pub parameter_values: HashMap<String, f64>,
    pub coordinate: Vec<usize>,
    pub event_count: u64,
    pub primary_utility_value: f64,
    pub secondary_metric_value: Option<f64>,
    pub neighbor_indices: Vec<usize>,
}

/// Evaluation assessment for an individual lattice point.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PointAssessment {
    pub point_idx: usize,
    pub variant_id: VariantId,
    pub primary_utility: f64,
    pub max_neighbor_relative_drop: f64,
    pub verdict: RobustnessVerdict,
}

/// Finite preregistered parameter surface lattice.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct RobustnessSurface {
    pub points: Vec<RobustnessPoint>,
    pub grid_dimensions: Vec<usize>,
}

impl RobustnessSurface {
    /// Builds a finite parameter surface from a challenger family spec and evaluated metric maps.
    pub fn build_from_evaluations(
        spec: &ChallengerFamilySpec,
        evaluations: &HashMap<VariantId, (u64, f64, Option<f64>)>, // variant_id -> (event_count, primary_u, secondary_m)
    ) -> Result<Self, HypothesisError> {
        spec.validate()?;

        let dims: Vec<usize> = spec
            .discrete_parameters
            .iter()
            .map(|p| p.discrete_values.len())
            .collect();

        let total_points = spec.grid_size();
        if total_points < 2 {
            return Err(HypothesisError::UnboundedSearchSpace(
                "Robustness lattice must contain at least 2 discrete points (Invariant I1)".to_string(),
            ));
        }

        let variants = spec.generate_variants()?;
        let mut points = Vec::with_capacity(total_points);

        // Precompute multi-index strides for Cartesian coordinate mapping
        let num_dims = dims.len();

        for (flat_idx, variant) in variants.into_iter().enumerate() {
            // Compute multi-dimensional coordinate from flat_idx
            let mut coord = vec![0usize; num_dims];
            let mut rem = flat_idx;
            for d in (0..num_dims).rev() {
                coord[d] = rem % dims[d];
                rem /= dims[d];
            }

            let (event_count, primary_u, secondary_m) = evaluations
                .get(&variant.variant_id)
                .copied()
                .unwrap_or((0, 0.0, None));

            points.push(RobustnessPoint {
                variant_id: variant.variant_id,
                parameter_values: variant.parameter_values,
                coordinate: coord,
                event_count,
                primary_utility_value: primary_u,
                secondary_metric_value: secondary_m,
                neighbor_indices: Vec::new(),
            });
        }

        // Connect immediate 1-hop lattice neighbors along each dimension
        for i in 0..total_points {
            let mut neighbors = Vec::new();
            for d in 0..num_dims {
                // Predecessor along dimension d
                if points[i].coordinate[d] > 0 {
                    let mut neighbor_coord = points[i].coordinate.clone();
                    neighbor_coord[d] -= 1;
                    if let Some(n_idx) = find_point_by_coord(&points, &dims, &neighbor_coord) {
                        neighbors.push(n_idx);
                    }
                }
                // Successor along dimension d
                if points[i].coordinate[d] + 1 < dims[d] {
                    let mut neighbor_coord = points[i].coordinate.clone();
                    neighbor_coord[d] += 1;
                    if let Some(n_idx) = find_point_by_coord(&points, &dims, &neighbor_coord) {
                        neighbors.push(n_idx);
                    }
                }
            }
            points[i].neighbor_indices = neighbors;
        }

        Ok(Self {
            points,
            grid_dimensions: dims,
        })
    }
}

fn find_point_by_coord(
    _points: &[RobustnessPoint],
    dims: &[usize],
    coord: &[usize],
) -> Option<usize> {
    let mut flat = 0usize;
    let mut mult = 1usize;
    for d in (0..dims.len()).rev() {
        if coord[d] >= dims[d] {
            return None;
        }
        flat += coord[d] * mult;
        mult *= dims[d];
    }
    Some(flat)
}

/// Robustness campaign receipt.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct RobustnessCampaignReceipt {
    pub family_id: String,
    pub criterion: PlateauCriterion,
    pub total_points: usize,
    pub peak_point_idx: usize,
    pub peak_utility: f64,
    pub overall_verdict: RobustnessVerdict,
    pub point_assessments: Vec<PointAssessment>,
}

/// Robustness campaign analyzer.
pub struct RobustnessCampaign;

impl RobustnessCampaign {
    /// Computes robust relative degradation with absolute floor fallback epsilon_floor:
    ///
    /// RelativeDrop = (U_peak - U_neighbor) / max(U_peak, epsilon_floor)
    pub fn compute_relative_drop(u_peak: f64, u_neighbor: f64, epsilon_floor: f64) -> f64 {
        let eff_floor = if epsilon_floor.is_nan() || epsilon_floor <= 0.0 {
            1e-4
        } else {
            epsilon_floor
        };
        let denom = u_peak.max(eff_floor);
        (u_peak - u_neighbor) / denom
    }

    /// Evaluates parameter surface robustness across the preregistered lattice.
    pub fn evaluate(
        family_id: &str,
        surface: &RobustnessSurface,
        criterion: &PlateauCriterion,
    ) -> Result<RobustnessCampaignReceipt, HypothesisError> {
        if surface.points.is_empty() {
            return Err(HypothesisError::UnboundedSearchSpace(
                "Surface contains zero points".to_string(),
            ));
        }

        let mut point_assessments = Vec::with_capacity(surface.points.len());
        let mut best_peak_idx = 0usize;
        let mut best_peak_utility = f64::NEG_INFINITY;

        // 1. Initial per-point floor and support evaluation
        for (idx, p) in surface.points.iter().enumerate() {
            if p.primary_utility_value > best_peak_utility {
                best_peak_utility = p.primary_utility_value;
                best_peak_idx = idx;
            }
        }

        // 2. Point-level neighborhood and plateau/cliff analysis
        for (idx, p) in surface.points.iter().enumerate() {
            if p.event_count < criterion.min_events_n {
                point_assessments.push(PointAssessment {
                    point_idx: idx,
                    variant_id: p.variant_id.clone(),
                    primary_utility: p.primary_utility_value,
                    max_neighbor_relative_drop: 0.0,
                    verdict: RobustnessVerdict::InsufficientN,
                });
                continue;
            }

            if p.primary_utility_value < criterion.utility_floor {
                point_assessments.push(PointAssessment {
                    point_idx: idx,
                    variant_id: p.variant_id.clone(),
                    primary_utility: p.primary_utility_value,
                    max_neighbor_relative_drop: 0.0,
                    verdict: RobustnessVerdict::NonViable,
                });
                continue;
            }

            if let Some(sec_floor) = criterion.secondary_floor {
                if let Some(sec_val) = p.secondary_metric_value {
                    if sec_val < sec_floor {
                        point_assessments.push(PointAssessment {
                            point_idx: idx,
                            variant_id: p.variant_id.clone(),
                            primary_utility: p.primary_utility_value,
                            max_neighbor_relative_drop: 0.0,
                            verdict: RobustnessVerdict::NonViable,
                        });
                        continue;
                    }
                }
            }

            let mut max_rel_drop = 0.0f64;
            let mut is_cliff = false;

            for &n_idx in &p.neighbor_indices {
                let neighbor = &surface.points[n_idx];
                let drop = Self::compute_relative_drop(
                    p.primary_utility_value,
                    neighbor.primary_utility_value,
                    criterion.epsilon_floor,
                );

                if drop > max_rel_drop {
                    max_rel_drop = drop;
                }

                if drop > criterion.max_cliff_drop {
                    is_cliff = true;
                }
            }

            let verdict = if is_cliff {
                RobustnessVerdict::Cliff
            } else if let Some(alpha) = criterion.alpha {
                let alpha_floor = alpha * p.primary_utility_value;
                let mut meets_alpha_plateau = true;
                for &n_idx in &p.neighbor_indices {
                    let neighbor = &surface.points[n_idx];
                    if neighbor.primary_utility_value < alpha_floor
                        || neighbor.primary_utility_value < criterion.utility_floor
                    {
                        meets_alpha_plateau = false;
                        break;
                    }
                }
                if meets_alpha_plateau {
                    RobustnessVerdict::Plateau
                } else {
                    RobustnessVerdict::Cliff
                }
            } else {
                RobustnessVerdict::Plateau
            };

            point_assessments.push(PointAssessment {
                point_idx: idx,
                variant_id: p.variant_id.clone(),
                primary_utility: p.primary_utility_value,
                max_neighbor_relative_drop: max_rel_drop,
                verdict,
            });
        }

        // Overall campaign verdict reflects the peak candidate's robustness
        let overall_verdict = point_assessments[best_peak_idx].verdict;

        Ok(RobustnessCampaignReceipt {
            family_id: family_id.to_string(),
            criterion: criterion.clone(),
            total_points: surface.points.len(),
            peak_point_idx: best_peak_idx,
            peak_utility: best_peak_utility,
            overall_verdict,
            point_assessments,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::kaizen::challenger::DiscreteParameterRange;

    fn sample_spec() -> ChallengerFamilySpec {
        let p1 = DiscreteParameterRange::new("length", vec![10.0, 20.0, 30.0]).unwrap();
        let p2 = DiscreteParameterRange::new("mult", vec![1.5, 2.0, 2.5]).unwrap();
        ChallengerFamilySpec::new(
            "bb_plateau_test",
            "bollinger_breakout",
            "v1",
            "Plateau robustness test",
            vec![p1, p2],
        )
        .unwrap()
    }

    #[test]
    fn test_plateau_classification_success() {
        let spec = sample_spec();
        let variants = spec.generate_variants().unwrap();

        // All points viable and stable around peak (0.50 to 0.46) -> alpha = 0.90 * 0.50 = 0.45
        let mut evaluations = HashMap::new();
        for v in variants {
            evaluations.insert(v.variant_id, (50u64, 0.48, Some(1.5)));
        }

        let surface = RobustnessSurface::build_from_evaluations(&spec, &evaluations).unwrap();
        let criterion = PlateauCriterion::default();

        let receipt = RobustnessCampaign::evaluate("bb_plateau_test", &surface, &criterion).unwrap();

        assert_eq!(receipt.overall_verdict, RobustnessVerdict::Plateau);
    }

    #[test]
    fn test_cliff_veto_with_epsilon_floor_protection() {
        let spec = sample_spec();
        let variants = spec.generate_variants().unwrap();

        let mut evaluations = HashMap::new();
        // Peak is near zero (0.005), but neighbor collapses to -0.05
        for (i, v) in variants.iter().enumerate() {
            let u = if i == 4 { 0.005 } else { -0.05 };
            evaluations.insert(v.variant_id.clone(), (50u64, u, Some(0.1)));
        }

        let surface = RobustnessSurface::build_from_evaluations(&spec, &evaluations).unwrap();
        let criterion = PlateauCriterion {
            utility_floor: -1.0, // Allow observing drop without failing utility floor immediately
            epsilon_floor: 0.01,
            ..Default::default()
        };

        let receipt = RobustnessCampaign::evaluate("bb_plateau_test", &surface, &criterion).unwrap();

        // Relative drop: (0.005 - (-0.05)) / max(0.005, 0.01) = 0.055 / 0.01 = 5.5 (> 0.30)
        assert_eq!(receipt.overall_verdict, RobustnessVerdict::Cliff);
    }

    #[test]
    fn test_negative_utility_points_are_non_viable() {
        let spec = sample_spec();
        let variants = spec.generate_variants().unwrap();

        let mut evaluations = HashMap::new();
        for v in variants {
            evaluations.insert(v.variant_id, (50u64, -0.15, Some(-0.5)));
        }

        let surface = RobustnessSurface::build_from_evaluations(&spec, &evaluations).unwrap();
        let criterion = PlateauCriterion::default();

        let receipt = RobustnessCampaign::evaluate("bb_plateau_test", &surface, &criterion).unwrap();

        assert_eq!(receipt.overall_verdict, RobustnessVerdict::NonViable);
    }

    #[test]
    fn test_insufficient_n_fails_closed() {
        let spec = sample_spec();
        let variants = spec.generate_variants().unwrap();

        let mut evaluations = HashMap::new();
        for v in variants {
            evaluations.insert(v.variant_id, (10u64, 0.50, Some(1.8))); // 10 < min_events_n (30)
        }

        let surface = RobustnessSurface::build_from_evaluations(&spec, &evaluations).unwrap();
        let criterion = PlateauCriterion::default();

        let receipt = RobustnessCampaign::evaluate("bb_plateau_test", &surface, &criterion).unwrap();

        assert_eq!(receipt.overall_verdict, RobustnessVerdict::InsufficientN);
    }
}
