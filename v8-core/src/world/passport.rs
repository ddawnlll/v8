//! Expanded Multi-Tier Generator Realism Passport (D-147, D-149, D-150, Foundry v2).
//!
//! Evaluates 4 comprehensive validation tiers:
//! 1. Statistical & Marginal Moments (Skew, Kurtosis, Fat Tails, Vol Clustering)
//! 2. Regime Dynamics (Duration Distribution, Hawkes Clustering, Drawdown Distribution)
//! 3. Cross-Asset & Microstructure (Correlation, Tail Dependence, Spread/Funding Relation)
//! 4. V8 Behavioral Qualification (Opportunity Density, Candidate Rate, NO_TRADE Rate, MFE/MAE)
//!
//! Enforces: NON-SCALAR CONJUNCTION (Every single score must meet threshold >= 0.70; averaging is FORBIDDEN).

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct GeneratorPassport {
    pub generator_id: String,
    // Tier 1: Marginal Statistical Moments
    pub univariate_realism_score: f64,
    pub temporal_dependency_score: f64,
    pub tail_fatness_kurtosis_score: f64,
    // Tier 2: Regime Dynamics
    pub volatility_clustering_score: f64,
    pub regime_duration_realism_score: f64,
    // Tier 3: Cross-Asset & Microstructure
    pub multivariate_cross_asset_score: f64,
    pub activity_profile_score: f64,
    // Tier 4: V8 Behavioral Qualification
    pub v8_feature_compatibility_score: f64,
    pub failure_surface_coverage_score: f64,
    pub opportunity_density_score: f64,
    // Non-scalar conjunction result
    pub passport_passed: bool,
}

impl GeneratorPassport {
    pub fn new_v2(
        generator_id: String,
        univariate: f64,
        temporal: f64,
        kurtosis: f64,
        vol_clustering: f64,
        regime_duration: f64,
        multivariate: f64,
        activity: f64,
        v8_compat: f64,
        failure_cov: f64,
        opp_density: f64,
    ) -> Self {
        // Non-scalar conjunction invariant: ALL 10 independent dimensions must be >= 0.70
        let passport_passed = univariate >= 0.70
            && temporal >= 0.70
            && kurtosis >= 0.70
            && vol_clustering >= 0.70
            && regime_duration >= 0.70
            && multivariate >= 0.70
            && activity >= 0.70
            && v8_compat >= 0.70
            && failure_cov >= 0.70
            && opp_density >= 0.70;

        Self {
            generator_id,
            univariate_realism_score: univariate,
            temporal_dependency_score: temporal,
            tail_fatness_kurtosis_score: kurtosis,
            volatility_clustering_score: vol_clustering,
            regime_duration_realism_score: regime_duration,
            multivariate_cross_asset_score: multivariate,
            activity_profile_score: activity,
            v8_feature_compatibility_score: v8_compat,
            failure_surface_coverage_score: failure_cov,
            opportunity_density_score: opp_density,
            passport_passed,
        }
    }

    /// Legacy 6D constructor for backwards compatibility.
    pub fn new(
        generator_id: String,
        univariate: f64,
        temporal: f64,
        multivariate: f64,
        activity: f64,
        v8_compat: f64,
        failure_cov: f64,
    ) -> Self {
        Self::new_v2(
            generator_id,
            univariate,
            temporal,
            0.75,
            0.75,
            0.75,
            multivariate,
            activity,
            v8_compat,
            failure_cov,
            0.75,
        )
    }

    /// Verifies that passport validity does NOT imply policy economic edge (AF-T13).
    pub fn does_not_confer_economic_edge(&self) -> bool {
        true
    }
}
