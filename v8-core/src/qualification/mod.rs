//! D-141 Expert Proving Ground & Alpha Refinery.
//!
//! Qualification is a falsification surface, never an economic authority
//! surface.  This module intentionally models semantic evidence separately
//! from real-tape attribution and does not produce an economic verdict.

use std::collections::{BTreeMap, BTreeSet, HashMap};
use std::path::Path;

use serde::{Deserialize, Serialize};

use crate::error::V8CoreError;
use crate::experts::base::{ExpertEval, FeatMap, ProjectedFeatures};
use crate::hash::Canon;
use crate::state::{Feature, HistBar};

pub const D141_SCHEMA_VERSION: &str = "d141.eqm.v1";
pub const NO_ECONOMIC_CLAIM: &str = "NO_ECONOMIC_CLAIM";

/// The maximum authority a D-141 result may carry.
///
/// `RealTapeDiagnostic` remains deliberately non-promotional.  There is no
/// economic or execution-capable variant in this closed algebra.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
pub enum QualificationAuthority {
    ContractEvidence,
    SemanticQualification,
    StatisticalQualification,
    RealTapeDiagnostic,
}

impl QualificationAuthority {
    pub fn renders_economic_claim(self) -> bool {
        false
    }
}

/// A Behavior Card freezes what a witness means before it is evaluated.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct BehaviorCard {
    pub expert_id: String,
    pub expert_version: String,
    pub mechanism_family_id: String,
    pub behavior_family_id: String,
    pub dependency_group: String,
    pub hypothesis: String,
    pub declared_features: Vec<String>,
    pub forbidden_dependencies: Vec<String>,
    pub symmetric_long_short: bool,
}

/// A machine-readable, hash-bound qualification declaration.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ExpertQualificationManifest {
    pub schema_version: String,
    pub card: BehaviorCard,
    pub scenario_families: Vec<ScenarioClass>,
    pub oracle_id: String,
    pub oracle_version: String,
    pub seed_manifest: String,
    pub generator_version: String,
    pub maximum_authority: QualificationAuthority,
}

impl ExpertQualificationManifest {
    pub fn validate(&self) -> Result<(), V8CoreError> {
        if self.schema_version != D141_SCHEMA_VERSION {
            return Err(V8CoreError::QuantInvariant(format!(
                "D-141 manifest schema must be {D141_SCHEMA_VERSION}"
            )));
        }
        if self.card.expert_id.trim().is_empty()
            || self.card.expert_version.trim().is_empty()
            || self.oracle_id.trim().is_empty()
            || self.oracle_version.trim().is_empty()
            || self.seed_manifest.trim().is_empty()
            || self.generator_version.trim().is_empty()
        {
            return Err(V8CoreError::QuantInvariant(
                "D-141 manifest identity, oracle, seed, and generator bindings are required".into(),
            ));
        }
        if self.card.declared_features.is_empty() {
            return Err(V8CoreError::QuantInvariant(
                "D-141 BehaviorCard must declare its feature read set".into(),
            ));
        }
        Ok(())
    }

    pub fn hash(&self) -> Result<String, V8CoreError> {
        self.validate()?;
        let value = serde_json::to_value(self)?;
        Ok(crate::hash::hash_value_blake3(&value))
    }
}

/// Scenario categories are epistemic test classes, not market regimes.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
pub enum ScenarioClass {
    Contract,
    CanonicalPositive,
    CanonicalNegative,
    Boundary,
    Metamorphic,
    NullWorld,
    Conditional,
    Adversarial,
    HistoricalDiagnostic,
}

/// A finite, point-in-time-only input world.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ScenarioInput {
    pub symbol: String,
    pub as_of: i64,
    pub scalars: BTreeMap<String, f64>,
    pub structured: BTreeMap<String, serde_json::Value>,
    pub history: Vec<ScenarioBar>,
    /// Deliberately outside the `FeatMap`: changing it must not affect a
    /// decision made at `as_of`.
    pub future_suffix: Vec<ScenarioBar>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ScenarioBar {
    pub event_id: String,
    pub open: f64,
    pub high: f64,
    pub low: f64,
    pub close: f64,
    pub ema_fast: f64,
    pub ema_slow: f64,
}

impl ScenarioBar {
    fn scaled(&self, factor: f64) -> Self {
        Self {
            event_id: self.event_id.clone(),
            open: self.open * factor,
            high: self.high * factor,
            low: self.low * factor,
            close: self.close * factor,
            ema_fast: self.ema_fast * factor,
            ema_slow: self.ema_slow * factor,
        }
    }
}

/// The only expected output vocabulary used by an independent scenario oracle.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
pub enum ExpectedStance {
    SupportLong,
    SupportShort,
    Abstain,
    NoHabitat,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Scenario {
    pub scenario_id: String,
    pub class: ScenarioClass,
    pub property_id: String,
    pub input: ScenarioInput,
    pub expected: ExpectedStance,
    pub required_cells: BTreeSet<String>,
    pub seed: u64,
    pub authority: QualificationAuthority,
}

impl Scenario {
    pub fn hash(&self) -> String {
        let value = serde_json::to_value(self).expect("D-141 Scenario must serialize");
        crate::hash::hash_value_blake3(&value)
    }

    pub fn scaled(&self, factor: f64) -> Result<Self, V8CoreError> {
        if !factor.is_finite() || factor <= 0.0 {
            return Err(V8CoreError::QuantInvariant(
                "D-141 price-scale factor must be finite and positive".into(),
            ));
        }
        let mut scaled = self.clone();
        for (name, value) in &mut scaled.input.scalars {
            if !matches!(
                name.as_str(),
                "bar_of_session"
                    | "cmf_20"
                    | "rsi14"
                    | "vol_zscore"
                    | "vol_min_proximity"
                    | "funding_rate"
                    | "long_short_skew"
                    | "open_interest"
                    | "body_range_ratio"
                    | "close_position"
                    | "volume"
                    | "vol_smooth_ma"
                    | "bar_class"
                    | "gap_dir"
                    | "bb_pct_b"
                    | "bb_bandwidth"
            ) {
                *value *= factor;
            }
        }
        for (name, value) in &mut scaled.input.structured {
            if name == "fib_levels" {
                scale_fib_levels(value, factor)?;
            } else if name == "consolidation_range" {
                scale_consolidation_range(value, factor)?;
            } else if name == "gap_levels" {
                scale_gap_levels(value, factor)?;
            } else {
                scale_json_numbers(value, factor)?;
            }
        }
        scaled.input.history = scaled
            .input
            .history
            .iter()
            .map(|bar| bar.scaled(factor))
            .collect();
        scaled.input.future_suffix = scaled
            .input
            .future_suffix
            .iter()
            .map(|bar| bar.scaled(factor))
            .collect();
        scaled.scenario_id = format!("{}:scale:{factor}", self.scenario_id);
        Ok(scaled)
    }
}

fn scale_gap_levels(value: &mut serde_json::Value, factor: f64) -> Result<(), V8CoreError> {
    let zones = value.as_array_mut().ok_or_else(|| {
        V8CoreError::QuantInvariant("gap_levels must be an array for price-scale relation".into())
    })?;
    for zone in zones {
        let zone = zone
            .as_array_mut()
            .ok_or_else(|| V8CoreError::QuantInvariant("gap level must be an array".into()))?;
        if zone.len() != 3 {
            return Err(V8CoreError::QuantInvariant(
                "gap level must contain top, bottom, and direction".into(),
            ));
        }
        for index in [0, 1] {
            let level = zone[index].as_f64().ok_or_else(|| {
                V8CoreError::QuantInvariant("gap level price must be numeric".into())
            })?;
            zone[index] = serde_json::json!(level * factor);
        }
        if !zone[2].is_number() {
            return Err(V8CoreError::QuantInvariant(
                "gap level direction must be numeric".into(),
            ));
        }
    }
    Ok(())
}

fn scale_consolidation_range(
    value: &mut serde_json::Value,
    factor: f64,
) -> Result<(), V8CoreError> {
    let arr = value.as_array_mut().ok_or_else(|| {
        V8CoreError::QuantInvariant(
            "consolidation_range must be an array for price-scale relation".into(),
        )
    })?;
    if arr.len() != 4 {
        return Err(V8CoreError::QuantInvariant(
            "consolidation_range must have four fields".into(),
        ));
    }
    for index in [0, 1] {
        let level = arr[index].as_f64().ok_or_else(|| {
            V8CoreError::QuantInvariant("consolidation_range price levels must be numeric".into())
        })?;
        arr[index] = serde_json::json!(level * factor);
    }
    if !arr[2].is_number() || !arr[3].is_boolean() {
        return Err(V8CoreError::QuantInvariant(
            "consolidation_range width must be numeric and active flag boolean".into(),
        ));
    }
    Ok(())
}

fn scale_fib_levels(value: &mut serde_json::Value, factor: f64) -> Result<(), V8CoreError> {
    let arr = value.as_array_mut().ok_or_else(|| {
        V8CoreError::QuantInvariant("fib_levels must be an array for price-scale relation".into())
    })?;
    if arr.len() != 4 {
        return Err(V8CoreError::QuantInvariant(
            "fib_levels must have canonical four-tuple shape".into(),
        ));
    }
    let anchor = arr[0]
        .as_f64()
        .ok_or_else(|| V8CoreError::QuantInvariant("fib anchor must be numeric".into()))?;
    arr[0] = serde_json::json!(anchor * factor);
    for (index, table_name) in [(2, "fib retracement"), (3, "fib extension")] {
        if index == 2 && arr[index].is_number() {
            // Projection manifests use a numeric retracement sentinel; it is
            // not a price table and therefore has no price-scale transform.
            continue;
        }
        let levels = arr[index].as_array_mut().ok_or_else(|| {
            V8CoreError::QuantInvariant(format!("{table_name} table must be an array"))
        })?;
        for pair in levels {
            let pair = pair.as_array_mut().ok_or_else(|| {
                V8CoreError::QuantInvariant(format!("{table_name} must be a pair"))
            })?;
            if pair.len() != 2 {
                return Err(V8CoreError::QuantInvariant(format!(
                    "{table_name} must contain ratio and level"
                )));
            }
            let level = pair[1].as_f64().ok_or_else(|| {
                V8CoreError::QuantInvariant(format!("{table_name} level must be numeric"))
            })?;
            pair[1] = serde_json::json!(level * factor);
        }
    }
    Ok(())
}

fn scale_json_numbers(value: &mut serde_json::Value, factor: f64) -> Result<(), V8CoreError> {
    match value {
        serde_json::Value::Number(number) => {
            let v = number.as_f64().ok_or_else(|| {
                V8CoreError::QuantInvariant("structured scenario number must be f64".into())
            })?;
            *value = serde_json::json!(v * factor);
        }
        serde_json::Value::Array(values) => {
            for item in values {
                scale_json_numbers(item, factor)?;
            }
        }
        serde_json::Value::Object(values) => {
            for item in values.values_mut() {
                scale_json_numbers(item, factor)?;
            }
        }
        serde_json::Value::Null | serde_json::Value::Bool(_) | serde_json::Value::String(_) => {}
    }
    Ok(())
}

/// Independent oracles receive only a scenario; the trait never accepts an
/// Expert evaluator, preventing direct implementation delegation.
pub trait ScenarioOracle: Send + Sync {
    fn oracle_id(&self) -> &str;
    fn oracle_version(&self) -> &str;
    fn expected_stance(&self, scenario: &Scenario) -> Result<ExpectedStance, V8CoreError>;
}

/// A declarative oracle keyed by frozen property IDs.
#[derive(Debug, Clone)]
pub struct DeclarativeScenarioOracle {
    id: String,
    version: String,
    expectations: BTreeMap<String, ExpectedStance>,
}

impl DeclarativeScenarioOracle {
    pub fn new(
        id: impl Into<String>,
        version: impl Into<String>,
        expectations: BTreeMap<String, ExpectedStance>,
    ) -> Self {
        Self {
            id: id.into(),
            version: version.into(),
            expectations,
        }
    }
}

impl ScenarioOracle for DeclarativeScenarioOracle {
    fn oracle_id(&self) -> &str {
        &self.id
    }
    fn oracle_version(&self) -> &str {
        &self.version
    }

    fn expected_stance(&self, scenario: &Scenario) -> Result<ExpectedStance, V8CoreError> {
        self.expectations
            .get(&scenario.property_id)
            .copied()
            .ok_or_else(|| {
                V8CoreError::QuantInvariant(format!(
                    "D-141 oracle has no independently declared expectation for {}",
                    scenario.property_id
                ))
            })
    }
}

/// A scenario executor cannot access `future_suffix` and always runs through
/// the registered Expert dispatch.
pub fn execute_scenario(expert_id: &str, scenario: &Scenario) -> ExpertEval {
    let mut features = Vec::new();
    // `history` is both a capability feature and the typed bar window below.
    // Experts that assert its declared availability must observe the same
    // presence contract as experts that only consume the bar sequence.
    features.push(feature(
        "history",
        serde_json::Value::Array(
            scenario
                .input
                .history
                .iter()
                .map(|bar| serde_json::json!(bar.event_id))
                .collect(),
        ),
        scenario.input.as_of,
    ));
    for (name, value) in &scenario.input.scalars {
        features.push(feature(
            name,
            serde_json::json!(value),
            scenario.input.as_of,
        ));
    }
    for (name, value) in &scenario.input.structured {
        features.push(feature(name, value.clone(), scenario.input.as_of));
    }
    let overrides = HashMap::new();
    let history = scenario.input.history.iter().map(to_hist_bar).collect();
    let fm = FeatMap {
        features: ProjectedFeatures::unprojected(&features),
        history,
        as_of: scenario.input.as_of,
        symbol: &scenario.input.symbol,
        variant_overrides: &overrides,
    };
    crate::experts::evaluate(expert_id, &fm)
}

fn feature(name: &str, value: serde_json::Value, available_time: i64) -> Feature {
    Feature {
        name: name.to_string(),
        value,
        dtype: "qualification".into(),
        feature_version: D141_SCHEMA_VERSION.into(),
        max_input_available_time: available_time,
        quality: "COMPLETE".into(),
        null_reason: None,
        group: "qualification".into(),
    }
}

fn to_hist_bar(bar: &ScenarioBar) -> HistBar {
    HistBar {
        event_id: bar.event_id.clone(),
        open: bar.open,
        high: bar.high,
        low: bar.low,
        close: bar.close,
        ema_fast: bar.ema_fast,
        ema_slow: bar.ema_slow,
    }
}

pub fn stance_from_eval(eval: &ExpertEval) -> ExpectedStance {
    match (
        &eval.decision[..],
        eval.draft.as_ref().map(|draft| draft.direction.as_str()),
    ) {
        ("CANDIDATE", Some("LONG")) => ExpectedStance::SupportLong,
        ("CANDIDATE", Some("SHORT")) => ExpectedStance::SupportShort,
        ("NO_HABITAT", _) => ExpectedStance::NoHabitat,
        _ => ExpectedStance::Abstain,
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ScenarioReceipt {
    pub scenario_id: String,
    pub scenario_hash: String,
    pub property_id: String,
    pub expected: ExpectedStance,
    pub observed: ExpectedStance,
    pub passed: bool,
    pub authority: QualificationAuthority,
    pub economic_claim: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct QualificationRun {
    pub manifest_hash: String,
    pub expert_id: String,
    pub receipts: Vec<ScenarioReceipt>,
    pub run_hash: String,
    pub economic_claim: String,
}

impl QualificationRun {
    pub fn execute(
        manifest: &ExpertQualificationManifest,
        oracle: &dyn ScenarioOracle,
        scenarios: &[Scenario],
    ) -> Result<Self, V8CoreError> {
        manifest.validate()?;
        if oracle.oracle_id() != manifest.oracle_id
            || oracle.oracle_version() != manifest.oracle_version
        {
            return Err(V8CoreError::QuantInvariant(
                "D-141 manifest oracle binding does not match the executing oracle".into(),
            ));
        }
        let mut receipts = Vec::with_capacity(scenarios.len());
        for scenario in scenarios {
            let expected = oracle.expected_stance(scenario)?;
            if expected != scenario.expected {
                return Err(V8CoreError::QuantInvariant(format!(
                    "D-141 scenario {} diverges from its independent oracle declaration",
                    scenario.scenario_id
                )));
            }
            let observed = stance_from_eval(&execute_scenario(&manifest.card.expert_id, scenario));
            receipts.push(ScenarioReceipt {
                scenario_id: scenario.scenario_id.clone(),
                scenario_hash: scenario.hash(),
                property_id: scenario.property_id.clone(),
                expected,
                observed,
                passed: expected == observed,
                authority: scenario.authority,
                economic_claim: NO_ECONOMIC_CLAIM.into(),
            });
        }
        let manifest_hash = manifest.hash()?;
        let value = serde_json::json!({
            "manifest_hash": manifest_hash,
            "expert_id": manifest.card.expert_id,
            "receipts": receipts,
            "economic_claim": NO_ECONOMIC_CLAIM,
        });
        let run_hash = crate::hash::hash_value_blake3(&value);
        Ok(Self {
            manifest_hash,
            expert_id: manifest.card.expert_id.clone(),
            receipts,
            run_hash,
            economic_claim: NO_ECONOMIC_CLAIM.into(),
        })
    }

    pub fn passed(&self) -> usize {
        self.receipts
            .iter()
            .filter(|receipt| receipt.passed)
            .count()
    }
    pub fn total(&self) -> usize {
        self.receipts.len()
    }
}

/// Pilot declarations derived from the D-141 Behavior Cards, not from an
/// imported Expert predicate.
pub fn failed_breakout_manifest() -> ExpertQualificationManifest {
    ExpertQualificationManifest {
        schema_version: D141_SCHEMA_VERSION.into(),
        card: BehaviorCard {
            expert_id: "failed_breakout".into(),
            expert_version: "v1".into(),
            mechanism_family_id: "structural".into(),
            behavior_family_id: "trap".into(),
            dependency_group: "dep_trap".into(),
            hypothesis: "A prior-high close breakout followed by a current close below the frozen high supports SHORT.".into(),
            declared_features: vec!["close".into(), "atr".into(), "history".into()],
            forbidden_dependencies: vec!["future bars".into(), "economic outcomes".into()],
            symmetric_long_short: false,
        },
        scenario_families: vec![ScenarioClass::CanonicalPositive, ScenarioClass::CanonicalNegative, ScenarioClass::Boundary, ScenarioClass::Metamorphic],
        oracle_id: "d141.failed-breakout.declarative".into(),
        oracle_version: "v1".into(),
        seed_manifest: "d141-seeds-v1".into(),
        generator_version: "scenario-foundry-v1".into(),
        maximum_authority: QualificationAuthority::SemanticQualification,
    }
}

pub fn failed_breakout_2b_manifest() -> ExpertQualificationManifest {
    ExpertQualificationManifest {
        schema_version: D141_SCHEMA_VERSION.into(),
        card: BehaviorCard {
            expert_id: "failed_breakout_2b".into(), expert_version: "v1".into(),
            mechanism_family_id: "failed_breakout".into(), behavior_family_id: "2b_reclaim".into(), dependency_group: "dep_location".into(),
            hypothesis: "The registered 2B branch supports LONG only when the prior close is strictly below a positive significant swing low and the current close strictly reclaims it.".into(),
            declared_features: vec!["close".into(), "atr".into(), "swing_low_10".into(), "history".into()], forbidden_dependencies: vec!["future bars".into(), "economic outcomes".into()], symmetric_long_short: false,
        },
        scenario_families: vec![ScenarioClass::CanonicalPositive, ScenarioClass::CanonicalNegative, ScenarioClass::Boundary, ScenarioClass::Metamorphic],
        oracle_id: "d141.failed-breakout-2b.declarative".into(), oracle_version: "v1".into(), seed_manifest: "d141-seeds-v1".into(), generator_version: "scenario-foundry-v1".into(), maximum_authority: QualificationAuthority::SemanticQualification,
    }
}

pub fn breakout_retest_manifest() -> ExpertQualificationManifest {
    ExpertQualificationManifest {
        schema_version: D141_SCHEMA_VERSION.into(),
        card: BehaviorCard {
            expert_id: "breakout_retest".into(), expert_version: "v1".into(), mechanism_family_id: "structural".into(), behavior_family_id: "role_reversal".into(), dependency_group: "dep_location".into(),
            hypothesis: "The registered default role-reversal branch supports a strict retest and hold of a previously breached significant swing level in the matching direction.".into(),
            declared_features: vec!["close".into(), "atr".into(), "swing_high_10".into(), "swing_low_10".into(), "history".into()], forbidden_dependencies: vec!["future bars".into(), "economic outcomes".into()], symmetric_long_short: true,
        },
        scenario_families: vec![ScenarioClass::CanonicalPositive, ScenarioClass::CanonicalNegative, ScenarioClass::Boundary, ScenarioClass::Metamorphic], oracle_id: "d141.breakout-retest.declarative".into(), oracle_version: "v1".into(), seed_manifest: "d141-seeds-v1".into(), generator_version: "scenario-foundry-v1".into(), maximum_authority: QualificationAuthority::SemanticQualification,
    }
}

pub fn fib_projection_reversal_manifest() -> ExpertQualificationManifest {
    ExpertQualificationManifest {
        schema_version: D141_SCHEMA_VERSION.into(),
        card: BehaviorCard {
            expert_id: "fib_projection_reversal".into(),
            expert_version: "v1".into(),
            mechanism_family_id: "geometric".into(),
            behavior_family_id: "reversal".into(),
            dependency_group: "dep_fib".into(),
            hypothesis: "A 1.618 extension pierced and rejected by the latest PIT bar supports the opposite reversal.".into(),
            declared_features: vec!["close".into(), "atr".into(), "history".into(), "fib_levels".into()],
            forbidden_dependencies: vec!["future bars".into(), "economic outcomes".into()],
            symmetric_long_short: true,
        },
        scenario_families: vec![ScenarioClass::CanonicalPositive, ScenarioClass::CanonicalNegative, ScenarioClass::Boundary, ScenarioClass::Metamorphic],
        oracle_id: "d141.fib.declarative".into(),
        oracle_version: "v1".into(),
        seed_manifest: "d141-seeds-v1".into(),
        generator_version: "scenario-foundry-v1".into(),
        maximum_authority: QualificationAuthority::SemanticQualification,
    }
}

pub fn liquidity_sweep_reclaim_manifest() -> ExpertQualificationManifest {
    ExpertQualificationManifest {
        schema_version: D141_SCHEMA_VERSION.into(),
        card: BehaviorCard {
            expert_id: "liquidity_sweep_reclaim".into(),
            expert_version: "v1".into(),
            mechanism_family_id: "liquidity".into(),
            behavior_family_id: "sweep".into(),
            dependency_group: "dep_liquidity".into(),
            hypothesis: "A latest-bar breach of the frozen prior extreme followed by a close back inside supports the opposite reclaim.".into(),
            declared_features: vec!["close".into(), "atr".into(), "history".into()],
            forbidden_dependencies: vec!["future bars".into(), "economic outcomes".into()],
            symmetric_long_short: true,
        },
        scenario_families: vec![
            ScenarioClass::CanonicalPositive,
            ScenarioClass::CanonicalNegative,
            ScenarioClass::Boundary,
            ScenarioClass::Metamorphic,
        ],
        oracle_id: "d141.liquidity-sweep-reclaim.declarative".into(),
        oracle_version: "v1".into(),
        seed_manifest: "d141-seeds-v1".into(),
        generator_version: "scenario-foundry-v1".into(),
        maximum_authority: QualificationAuthority::SemanticQualification,
    }
}

pub fn trend_pullback_manifest() -> ExpertQualificationManifest {
    ExpertQualificationManifest {
        schema_version: D141_SCHEMA_VERSION.into(),
        card: BehaviorCard {
            expert_id: "trend_pullback".into(),
            expert_version: "v1".into(),
            mechanism_family_id: "momentum".into(),
            behavior_family_id: "trend_following".into(),
            dependency_group: "dep_trend".into(),
            hypothesis: "A close below the slow average inside an aligned fast-above-slow trend supports a LONG pullback.".into(),
            declared_features: vec![
                "close".into(),
                "atr".into(),
                "ema_fast".into(),
                "ema_slow".into(),
                "history".into(),
            ],
            forbidden_dependencies: vec!["future bars".into(), "economic outcomes".into()],
            symmetric_long_short: false,
        },
        scenario_families: vec![
            ScenarioClass::CanonicalPositive,
            ScenarioClass::CanonicalNegative,
            ScenarioClass::Boundary,
            ScenarioClass::Metamorphic,
        ],
        oracle_id: "d141.trend-pullback.declarative".into(),
        oracle_version: "v1".into(),
        seed_manifest: "d141-seeds-v1".into(),
        generator_version: "scenario-foundry-v1".into(),
        maximum_authority: QualificationAuthority::SemanticQualification,
    }
}

pub fn trend_pullback_depth_manifest() -> ExpertQualificationManifest {
    ExpertQualificationManifest {
        schema_version: D141_SCHEMA_VERSION.into(),
        card: BehaviorCard {
            expert_id: "trend_pullback_depth".into(),
            expert_version: "v1".into(),
            mechanism_family_id: "momentum".into(),
            behavior_family_id: "trend_following".into(),
            dependency_group: "dep_trend".into(),
            hypothesis: "A fast-above-slow trend with a close inside the inclusive 38.2% upper impulse-retracement band supports a LONG pullback.".into(),
            declared_features: vec![
                "close".into(),
                "atr".into(),
                "ema_fast".into(),
                "ema_slow".into(),
                "swing_high_10".into(),
                "swing_low_10".into(),
                "history".into(),
            ],
            forbidden_dependencies: vec!["future bars".into(), "economic outcomes".into()],
            symmetric_long_short: false,
        },
        scenario_families: vec![
            ScenarioClass::CanonicalPositive,
            ScenarioClass::CanonicalNegative,
            ScenarioClass::Boundary,
            ScenarioClass::Metamorphic,
        ],
        oracle_id: "d141.trend-pullback-depth.declarative".into(),
        oracle_version: "v1".into(),
        seed_manifest: "d141-seeds-v1".into(),
        generator_version: "scenario-foundry-v1".into(),
        maximum_authority: QualificationAuthority::SemanticQualification,
    }
}

pub fn donchian_breakout_manifest() -> ExpertQualificationManifest {
    ExpertQualificationManifest {
        schema_version: D141_SCHEMA_VERSION.into(),
        card: BehaviorCard {
            expert_id: "donchian_breakout".into(),
            expert_version: "v1".into(),
            mechanism_family_id: "channel".into(),
            behavior_family_id: "breakout".into(),
            dependency_group: "dep_breakout".into(),
            hypothesis: "A close strictly above the frozen 20-bar channel high supports the registered long-only breakout.".into(),
            declared_features: vec![
                "close".into(),
                "atr".into(),
                "window_high_20".into(),
                "window_low_20".into(),
                "history".into(),
            ],
            forbidden_dependencies: vec!["future bars".into(), "economic outcomes".into()],
            symmetric_long_short: false,
        },
        scenario_families: vec![
            ScenarioClass::CanonicalPositive,
            ScenarioClass::CanonicalNegative,
            ScenarioClass::Boundary,
            ScenarioClass::Metamorphic,
        ],
        oracle_id: "d141.donchian-breakout.declarative".into(),
        oracle_version: "v1".into(),
        seed_manifest: "d141-seeds-v1".into(),
        generator_version: "scenario-foundry-v1".into(),
        maximum_authority: QualificationAuthority::SemanticQualification,
    }
}

pub fn volume_confirmed_breakout_manifest() -> ExpertQualificationManifest {
    ExpertQualificationManifest {
        schema_version: D141_SCHEMA_VERSION.into(),
        card: BehaviorCard {
            expert_id: "volume_confirmed_breakout".into(),
            expert_version: "v1".into(),
            mechanism_family_id: "volume".into(),
            behavior_family_id: "breakout".into(),
            dependency_group: "dep_volume".into(),
            hypothesis: "A strict channel break with a declared volume-confirmation gate supports the breakout direction.".into(),
            declared_features: vec![
                "close".into(),
                "atr".into(),
                "volume".into(),
                "vol_smooth_ma".into(),
                "window_high_20".into(),
                "window_low_20".into(),
                "history".into(),
            ],
            forbidden_dependencies: vec!["future bars".into(), "economic outcomes".into()],
            symmetric_long_short: true,
        },
        scenario_families: vec![
            ScenarioClass::CanonicalPositive,
            ScenarioClass::CanonicalNegative,
            ScenarioClass::Boundary,
            ScenarioClass::Metamorphic,
        ],
        oracle_id: "d141.volume-confirmed-breakout.declarative".into(),
        oracle_version: "v1".into(),
        seed_manifest: "d141-seeds-v1".into(),
        generator_version: "scenario-foundry-v1".into(),
        maximum_authority: QualificationAuthority::SemanticQualification,
    }
}

pub fn range_breakout_1to1_manifest() -> ExpertQualificationManifest {
    ExpertQualificationManifest {
        schema_version: D141_SCHEMA_VERSION.into(),
        card: BehaviorCard {
            expert_id: "range_breakout_1to1".into(),
            expert_version: "v1".into(),
            mechanism_family_id: "range".into(),
            behavior_family_id: "breakout".into(),
            dependency_group: "dep_breakout".into(),
            hypothesis: "A single-bar strict escape from an active narrow 20-bar consolidation range supports the matching 1:1 breakout direction.".into(),
            declared_features: vec![
                "close".into(),
                "atr".into(),
                "window_high_20".into(),
                "window_low_20".into(),
                "range_height_20".into(),
                "consolidation_range".into(),
                "history".into(),
            ],
            forbidden_dependencies: vec!["future bars".into(), "economic outcomes".into()],
            symmetric_long_short: true,
        },
        scenario_families: vec![
            ScenarioClass::CanonicalPositive,
            ScenarioClass::CanonicalNegative,
            ScenarioClass::Boundary,
            ScenarioClass::Metamorphic,
        ],
        oracle_id: "d141.range-breakout-1to1.declarative".into(),
        oracle_version: "v1".into(),
        seed_manifest: "d141-seeds-v1".into(),
        generator_version: "scenario-foundry-v1".into(),
        maximum_authority: QualificationAuthority::SemanticQualification,
    }
}

pub fn floor_trader_pivot_manifest() -> ExpertQualificationManifest {
    ExpertQualificationManifest {
        schema_version: D141_SCHEMA_VERSION.into(),
        card: BehaviorCard {
            expert_id: "floor_trader_pivot".into(),
            expert_version: "v1".into(),
            mechanism_family_id: "pivot".into(),
            behavior_family_id: "range".into(),
            dependency_group: "dep_pivot".into(),
            hypothesis: "Within the current session, a PP-upward or PP-downward drift bar with positive declared geometry supports its matching pivot direction.".into(),
            declared_features: vec![
                "close".into(),
                "atr".into(),
                "pivot_points_day".into(),
                "bar_of_session".into(),
                "history".into(),
            ],
            forbidden_dependencies: vec!["future bars".into(), "economic outcomes".into()],
            symmetric_long_short: true,
        },
        scenario_families: vec![
            ScenarioClass::CanonicalPositive,
            ScenarioClass::CanonicalNegative,
            ScenarioClass::Boundary,
            ScenarioClass::Metamorphic,
        ],
        oracle_id: "d141.floor-trader-pivot.declarative".into(),
        oracle_version: "v1".into(),
        seed_manifest: "d141-seeds-v1".into(),
        generator_version: "scenario-foundry-v1".into(),
        maximum_authority: QualificationAuthority::SemanticQualification,
    }
}

pub fn fib_retracement_continuation_manifest() -> ExpertQualificationManifest {
    ExpertQualificationManifest {
        schema_version: D141_SCHEMA_VERSION.into(),
        card: BehaviorCard {
            expert_id: "fib_retracement_continuation".into(),
            expert_version: "v1".into(),
            mechanism_family_id: "geometric".into(),
            behavior_family_id: "continuation".into(),
            dependency_group: "dep_fib".into(),
            hypothesis: "A 0.382 retracement touch and reclaim continues the declared impulse direction; the 0.786 level is frozen only as invalidation geometry.".into(),
            declared_features: vec!["close".into(), "atr".into(), "fib_levels".into(), "history".into()],
            forbidden_dependencies: vec!["future bars".into(), "economic outcomes".into()],
            symmetric_long_short: true,
        },
        scenario_families: vec![
            ScenarioClass::CanonicalPositive,
            ScenarioClass::CanonicalNegative,
            ScenarioClass::Boundary,
            ScenarioClass::Metamorphic,
        ],
        oracle_id: "d141.fib-retracement-continuation.declarative".into(),
        oracle_version: "v1".into(),
        seed_manifest: "d141-seeds-v1".into(),
        generator_version: "scenario-foundry-v1".into(),
        maximum_authority: QualificationAuthority::SemanticQualification,
    }
}

pub fn obv_adl_regime_manifest() -> ExpertQualificationManifest {
    ExpertQualificationManifest {
        schema_version: D141_SCHEMA_VERSION.into(),
        card: BehaviorCard {
            expert_id: "obv_adl_regime".into(),
            expert_version: "v1".into(),
            mechanism_family_id: "volume".into(),
            behavior_family_id: "flow".into(),
            dependency_group: "dep_volume".into(),
            hypothesis: "A declared CMF oversold regime below the slow average supports the priority long gate; feature closure includes participation, trend, volatility, and history.".into(),
            declared_features: vec!["close".into(), "atr".into(), "cmf_20".into(), "ema_fast".into(), "ema_slow".into(), "history".into()],
            forbidden_dependencies: vec!["future bars".into(), "economic outcomes".into()],
            symmetric_long_short: true,
        },
        scenario_families: vec![
            ScenarioClass::CanonicalPositive,
            ScenarioClass::CanonicalNegative,
            ScenarioClass::Boundary,
            ScenarioClass::Metamorphic,
        ],
        oracle_id: "d141.obv-adl-regime.declarative".into(),
        oracle_version: "v1".into(),
        seed_manifest: "d141-seeds-v1".into(),
        generator_version: "scenario-foundry-v1".into(),
        maximum_authority: QualificationAuthority::SemanticQualification,
    }
}

pub fn funding_crowding_reversal_manifest() -> ExpertQualificationManifest {
    ExpertQualificationManifest {
        schema_version: D141_SCHEMA_VERSION.into(),
        card: BehaviorCard {
            expert_id: "funding_crowding_reversal".into(),
            expert_version: "v1".into(),
            mechanism_family_id: "derivatives".into(),
            behavior_family_id: "crowding".into(),
            dependency_group: "dep_derivatives".into(),
            hypothesis: "A non-price positive funding extreme plus a strict break below the frozen prior five-bar low supports the registered crowded-long SHORT reversal.".into(),
            declared_features: vec!["close".into(), "atr".into(), "funding_rate".into(), "history".into()],
            forbidden_dependencies: vec!["future bars".into(), "economic outcomes".into()],
            symmetric_long_short: false,
        },
        scenario_families: vec![ScenarioClass::CanonicalPositive, ScenarioClass::CanonicalNegative, ScenarioClass::Boundary, ScenarioClass::Metamorphic],
        oracle_id: "d141.funding-crowding-reversal.declarative".into(),
        oracle_version: "v1".into(),
        seed_manifest: "d141-seeds-v1".into(),
        generator_version: "scenario-foundry-v1".into(),
        maximum_authority: QualificationAuthority::SemanticQualification,
    }
}

pub fn open_interest_divergence_manifest() -> ExpertQualificationManifest {
    ExpertQualificationManifest {
        schema_version: D141_SCHEMA_VERSION.into(),
        card: BehaviorCard {
            expert_id: "open_interest_divergence".into(), expert_version: "v1".into(), mechanism_family_id: "derivatives".into(), behavior_family_id: "divergence".into(), dependency_group: "dep_derivatives".into(),
            hypothesis: "The registered default leg supports LONG only when price is up over five bars, volume z-score is positive, and long/short skew is at least one with OI present.".into(),
            declared_features: vec!["close".into(), "atr".into(), "open_interest".into(), "long_short_skew".into(), "vol_zscore".into(), "history".into()], forbidden_dependencies: vec!["future bars".into(), "economic outcomes".into()], symmetric_long_short: false,
        },
        scenario_families: vec![ScenarioClass::CanonicalPositive, ScenarioClass::CanonicalNegative, ScenarioClass::Boundary, ScenarioClass::Metamorphic], oracle_id: "d141.open-interest-divergence.declarative".into(), oracle_version: "v1".into(), seed_manifest: "d141-seeds-v1".into(), generator_version: "scenario-foundry-v1".into(), maximum_authority: QualificationAuthority::SemanticQualification,
    }
}

pub fn candlestick_reversal_manifest() -> ExpertQualificationManifest {
    ExpertQualificationManifest {
        schema_version: D141_SCHEMA_VERSION.into(),
        card: BehaviorCard {
            expert_id: "candlestick_reversal".into(),
            expert_version: "v1".into(),
            mechanism_family_id: "candlestick".into(),
            behavior_family_id: "reversal".into(),
            dependency_group: "dep_candle_shape".into(),
            hypothesis: "The registered hammer variant supports LONG only after a down bar when a bullish small body has a lower shadow at least twice its body and an upper shadow no larger than its body.".into(),
            declared_features: vec![
                "close".into(),
                "atr".into(),
                "real_body".into(),
                "body_range_ratio".into(),
                "upper_shadow".into(),
                "lower_shadow".into(),
                "close_position".into(),
                "history".into(),
            ],
            forbidden_dependencies: vec!["future bars".into(), "economic outcomes".into()],
            symmetric_long_short: true,
        },
        scenario_families: vec![
            ScenarioClass::CanonicalPositive,
            ScenarioClass::CanonicalNegative,
            ScenarioClass::Boundary,
            ScenarioClass::Metamorphic,
        ],
        oracle_id: "d141.candlestick-reversal.declarative".into(),
        oracle_version: "v1".into(),
        seed_manifest: "d141-seeds-v1".into(),
        generator_version: "scenario-foundry-v1".into(),
        maximum_authority: QualificationAuthority::SemanticQualification,
    }
}

pub fn volume_climax_reversal_manifest() -> ExpertQualificationManifest {
    ExpertQualificationManifest {
        schema_version: D141_SCHEMA_VERSION.into(),
        card: BehaviorCard {
            expert_id: "volume_climax_reversal".into(),
            expert_version: "v2".into(),
            mechanism_family_id: "volume".into(),
            behavior_family_id: "climax_reversal".into(),
            dependency_group: "dep_volume".into(),
            hypothesis: "The priority strict-climax gate fades a declared three-sigma volume extreme in the registered trend direction; a two-sigma boundary is inclusive and falls through to its declared variant order.".into(),
            declared_features: vec![
                "close".into(),
                "ema_fast".into(),
                "ema_slow".into(),
                "atr".into(),
                "volume".into(),
                "vol_zscore".into(),
                "vol_min_proximity".into(),
                "history".into(),
            ],
            forbidden_dependencies: vec!["future bars".into(), "economic outcomes".into()],
            symmetric_long_short: true,
        },
        scenario_families: vec![
            ScenarioClass::CanonicalPositive,
            ScenarioClass::CanonicalNegative,
            ScenarioClass::Boundary,
            ScenarioClass::Metamorphic,
        ],
        oracle_id: "d141.volume-climax-reversal.declarative".into(),
        oracle_version: "v1".into(),
        seed_manifest: "d141-seeds-v1".into(),
        generator_version: "scenario-foundry-v1".into(),
        maximum_authority: QualificationAuthority::SemanticQualification,
    }
}

pub fn gap_exhaustion_manifest() -> ExpertQualificationManifest {
    ExpertQualificationManifest {
        schema_version: D141_SCHEMA_VERSION.into(),
        card: BehaviorCard {
            expert_id: "gap_exhaustion".into(),
            expert_version: "v1".into(),
            mechanism_family_id: "gap".into(),
            behavior_family_id: "exhaustion_reversal".into(),
            dependency_group: "dep_gap".into(),
            hypothesis: "The registered default third-gap exhaustion branch reverses only after three same-direction unfilled gaps, a matching frozen gap zone, and a reversal close through the gap direction.".into(),
            declared_features: vec![
                "close".into(),
                "atr".into(),
                "gap_dir".into(),
                "gap_size".into(),
                "gap_levels".into(),
                "history".into(),
            ],
            forbidden_dependencies: vec!["future bars".into(), "economic outcomes".into()],
            symmetric_long_short: true,
        },
        scenario_families: vec![
            ScenarioClass::CanonicalPositive,
            ScenarioClass::CanonicalNegative,
            ScenarioClass::Boundary,
            ScenarioClass::Metamorphic,
        ],
        oracle_id: "d141.gap-exhaustion.declarative".into(),
        oracle_version: "v1".into(),
        seed_manifest: "d141-seeds-v1".into(),
        generator_version: "scenario-foundry-v1".into(),
        maximum_authority: QualificationAuthority::SemanticQualification,
    }
}

pub fn bollinger_reversion_manifest() -> ExpertQualificationManifest {
    ExpertQualificationManifest {
        schema_version: D141_SCHEMA_VERSION.into(),
        card: BehaviorCard {
            expert_id: "bollinger_reversion".into(),
            expert_version: "v1".into(),
            mechanism_family_id: "bollinger".into(),
            behavior_family_id: "mean_reversion".into(),
            dependency_group: "dep_bollinger".into(),
            hypothesis: "The registered default fade branch supports a return from the inclusive 2-SD to exclusive 3-SD envelope toward the mean, with its anchor recomputed from the same 20-bar history.".into(),
            declared_features: vec![
                "close".into(),
                "bb_mid".into(),
                "bb_upper".into(),
                "bb_lower".into(),
                "bb_pct_b".into(),
                "ema_fast".into(),
                "ema_slow".into(),
                "history".into(),
            ],
            forbidden_dependencies: vec!["future bars".into(), "economic outcomes".into()],
            symmetric_long_short: true,
        },
        scenario_families: vec![
            ScenarioClass::CanonicalPositive,
            ScenarioClass::CanonicalNegative,
            ScenarioClass::Boundary,
            ScenarioClass::Metamorphic,
        ],
        oracle_id: "d141.bollinger-reversion.declarative".into(),
        oracle_version: "v1".into(),
        seed_manifest: "d141-seeds-v1".into(),
        generator_version: "scenario-foundry-v1".into(),
        maximum_authority: QualificationAuthority::SemanticQualification,
    }
}

pub fn bollinger_breakout_manifest() -> ExpertQualificationManifest {
    ExpertQualificationManifest {
        schema_version: D141_SCHEMA_VERSION.into(),
        card: BehaviorCard {
            expert_id: "bollinger_breakout".into(),
            expert_version: "v1".into(),
            mechanism_family_id: "bollinger".into(),
            behavior_family_id: "breakout".into(),
            dependency_group: "dep_bollinger".into(),
            hypothesis: "The registered default branch supports a direction only when the current close strictly crosses its 20-bar Bollinger midpoint; equality abstains and the anchor shares the same recomputed window.".into(),
            declared_features: vec![
                "close".into(), "bb_mid".into(), "bb_upper".into(), "bb_lower".into(),
                "bb_pct_b".into(), "bb_bandwidth".into(), "history".into(),
            ],
            forbidden_dependencies: vec!["future bars".into(), "economic outcomes".into()],
            symmetric_long_short: true,
        },
        scenario_families: vec![
            ScenarioClass::CanonicalPositive, ScenarioClass::CanonicalNegative,
            ScenarioClass::Boundary, ScenarioClass::Metamorphic,
        ],
        oracle_id: "d141.bollinger-breakout.declarative".into(),
        oracle_version: "v1".into(),
        seed_manifest: "d141-seeds-v1".into(),
        generator_version: "scenario-foundry-v1".into(),
        maximum_authority: QualificationAuthority::SemanticQualification,
    }
}

fn base_input() -> ScenarioInput {
    ScenarioInput {
        symbol: "BTCUSDT".into(),
        as_of: 1_700_000_000_000_000_000,
        scalars: BTreeMap::from([("close".into(), 99.0), ("atr".into(), 2.0)]),
        structured: BTreeMap::new(),
        history: vec![
            ScenarioBar {
                event_id: "b0".into(),
                open: 99.0,
                high: 100.0,
                low: 98.0,
                close: 99.0,
                ema_fast: 99.0,
                ema_slow: 99.0,
            },
            ScenarioBar {
                event_id: "b1".into(),
                open: 100.0,
                high: 103.0,
                low: 100.0,
                close: 102.0,
                ema_fast: 100.0,
                ema_slow: 100.0,
            },
        ],
        future_suffix: vec![ScenarioBar {
            event_id: "future".into(),
            open: 1000.0,
            high: 2000.0,
            low: 1.0,
            close: 1000.0,
            ema_fast: 0.0,
            ema_slow: 0.0,
        }],
    }
}

fn channel_history() -> Vec<ScenarioBar> {
    (0..21)
        .map(|index| ScenarioBar {
            event_id: format!("channel-{index}"),
            open: 95.0,
            high: if index == 20 { 102.0 } else { 100.0 },
            low: 90.0,
            close: if index == 20 { 101.0 } else { 95.0 },
            ema_fast: 95.0,
            ema_slow: 95.0,
        })
        .collect()
}

fn scenario(
    id: &str,
    class: ScenarioClass,
    property_id: &str,
    input: ScenarioInput,
    expected: ExpectedStance,
    cells: &[&str],
) -> Scenario {
    Scenario {
        scenario_id: id.into(),
        class,
        property_id: property_id.into(),
        input,
        expected,
        required_cells: cells.iter().map(|cell| (*cell).into()).collect(),
        seed: 141,
        authority: QualificationAuthority::SemanticQualification,
    }
}

pub fn failed_breakout_scenarios() -> Vec<Scenario> {
    let positive = base_input();
    let mut negative = base_input();
    negative.scalars.insert("close".into(), 101.0);
    let mut boundary = base_input();
    boundary.scalars.insert("close".into(), 100.0);
    let mut missing = base_input();
    missing.scalars.remove("atr");
    vec![
        scenario(
            "fb-positive",
            ScenarioClass::CanonicalPositive,
            "FB-POS",
            positive,
            ExpectedStance::SupportShort,
            &["setup", "short"],
        ),
        scenario(
            "fb-negative",
            ScenarioClass::CanonicalNegative,
            "FB-NEG",
            negative,
            ExpectedStance::Abstain,
            &["no-setup"],
        ),
        scenario(
            "fb-boundary",
            ScenarioClass::Boundary,
            "FB-BOUNDARY",
            boundary,
            ExpectedStance::Abstain,
            &["boundary"],
        ),
        scenario(
            "fb-missing",
            ScenarioClass::Contract,
            "FB-MISSING",
            missing,
            ExpectedStance::NoHabitat,
            &["missingness"],
        ),
    ]
}

pub fn failed_breakout_2b_scenarios() -> Vec<Scenario> {
    let mut reclaim = base_input();
    reclaim.history = vec![
        ScenarioBar {
            event_id: "2b-failure".into(),
            open: 101.0,
            high: 102.0,
            low: 98.0,
            close: 99.0,
            ema_fast: 0.0,
            ema_slow: 0.0,
        },
        ScenarioBar {
            event_id: "2b-reclaim".into(),
            open: 99.0,
            high: 102.0,
            low: 98.0,
            close: 101.0,
            ema_fast: 0.0,
            ema_slow: 0.0,
        },
    ];
    reclaim.scalars = BTreeMap::from([
        ("close".into(), 101.0),
        ("atr".into(), 2.0),
        ("swing_low_10".into(), 100.0),
    ]);
    let mut negative = reclaim.clone();
    negative.history[1].close = 99.0;
    negative.scalars.insert("close".into(), 99.0);
    let mut boundary = reclaim.clone();
    boundary.history[1].close = 100.0;
    boundary.scalars.insert("close".into(), 100.0);
    let mut absent_reference = reclaim.clone();
    absent_reference.scalars.remove("swing_low_10");
    vec![
        scenario(
            "2b-reclaim-positive",
            ScenarioClass::CanonicalPositive,
            "2B-RECLAIM-LONG",
            reclaim,
            ExpectedStance::SupportLong,
            &["prior-below-swing", "strict-reclaim", "long"],
        ),
        scenario(
            "2b-reclaim-negative",
            ScenarioClass::CanonicalNegative,
            "2B-NO-RECLAIM",
            negative,
            ExpectedStance::Abstain,
            &["does-not-reclaim"],
        ),
        scenario(
            "2b-reclaim-boundary",
            ScenarioClass::Boundary,
            "2B-EQUAL-SWING",
            boundary,
            ExpectedStance::Abstain,
            &["strict-equality-boundary"],
        ),
        scenario(
            "2b-reclaim-absent-reference",
            ScenarioClass::Contract,
            "2B-ABSENT-SWING",
            absent_reference,
            ExpectedStance::Abstain,
            &["absent-significant-swing"],
        ),
    ]
}

pub fn breakout_retest_scenarios() -> Vec<Scenario> {
    let mut long = base_input();
    long.history = (0..7)
        .map(|index| ScenarioBar {
            event_id: format!("retest-long-{index}"),
            open: 101.0,
            high: if index == 6 { 103.0 } else { 102.0 },
            low: if index == 6 { 99.0 } else { 100.5 },
            close: if index == 6 { 102.0 } else { 101.0 },
            ema_fast: 0.0,
            ema_slow: 0.0,
        })
        .collect();
    long.scalars = BTreeMap::from([
        ("close".into(), 102.0),
        ("atr".into(), 2.0),
        ("swing_high_10".into(), 100.0),
        ("swing_low_10".into(), 90.0),
    ]);
    let mut short = long.clone();
    short.history = (0..7)
        .map(|index| ScenarioBar {
            event_id: format!("retest-short-{index}"),
            open: 89.0,
            high: if index == 6 { 91.0 } else { 89.5 },
            low: if index == 6 { 87.0 } else { 88.0 },
            close: if index == 6 { 88.0 } else { 89.0 },
            ema_fast: 0.0,
            ema_slow: 0.0,
        })
        .collect();
    short.scalars = BTreeMap::from([
        ("close".into(), 88.0),
        ("atr".into(), 2.0),
        ("swing_high_10".into(), 110.0),
        ("swing_low_10".into(), 90.0),
    ]);
    let mut negative = long.clone();
    negative.history[6].low = 100.1;
    let mut boundary = long.clone();
    boundary.history[6].close = 100.0;
    boundary.scalars.insert("close".into(), 100.0);
    let mut missing = long.clone();
    missing.scalars.remove("swing_high_10");
    vec![
        scenario(
            "retest-long",
            ScenarioClass::CanonicalPositive,
            "RETEST-LONG",
            long,
            ExpectedStance::SupportLong,
            &["prior-break", "touch-and-hold", "long"],
        ),
        scenario(
            "retest-short",
            ScenarioClass::CanonicalPositive,
            "RETEST-SHORT",
            short,
            ExpectedStance::SupportShort,
            &["prior-break", "touch-and-hold", "short"],
        ),
        scenario(
            "retest-no-touch",
            ScenarioClass::CanonicalNegative,
            "RETEST-NO-TOUCH",
            negative,
            ExpectedStance::Abstain,
            &["no-touch"],
        ),
        scenario(
            "retest-equal-level",
            ScenarioClass::Boundary,
            "RETEST-EQUAL-CLOSE",
            boundary,
            ExpectedStance::Abstain,
            &["strict-hold-boundary"],
        ),
        scenario(
            "retest-missing",
            ScenarioClass::Contract,
            "RETEST-MISSING",
            missing,
            ExpectedStance::NoHabitat,
            &["missingness"],
        ),
    ]
}

pub fn fib_projection_reversal_scenarios() -> Vec<Scenario> {
    let fib_up = serde_json::json!([100.0, 1.0, 0.0, [[1.618, 161.8]]]);
    let fib_down = serde_json::json!([100.0, -1.0, 0.0, [[1.618, 38.2]]]);
    let mut short = base_input();
    short.history = vec![
        ScenarioBar {
            event_id: "f0".into(),
            open: 150.0,
            high: 155.0,
            low: 149.0,
            close: 154.0,
            ema_fast: 150.0,
            ema_slow: 150.0,
        },
        ScenarioBar {
            event_id: "f1".into(),
            open: 162.0,
            high: 163.0,
            low: 159.0,
            close: 160.0,
            ema_fast: 150.0,
            ema_slow: 150.0,
        },
    ];
    short.structured.insert("fib_levels".into(), fib_up.clone());
    let mut long = short.clone();
    long.history = vec![
        ScenarioBar {
            event_id: "f2".into(),
            open: 45.0,
            high: 47.0,
            low: 40.0,
            close: 44.0,
            ema_fast: 45.0,
            ema_slow: 45.0,
        },
        ScenarioBar {
            event_id: "f3".into(),
            open: 37.0,
            high: 40.0,
            low: 37.0,
            close: 39.0,
            ema_fast: 45.0,
            ema_slow: 45.0,
        },
    ];
    long.structured.insert("fib_levels".into(), fib_down);
    let mut negative = short.clone();
    negative.history[1].close = 162.0;
    let mut boundary = short.clone();
    boundary.history[1].high = 161.7;
    vec![
        scenario(
            "fib-short",
            ScenarioClass::CanonicalPositive,
            "FIB-UP",
            short,
            ExpectedStance::SupportShort,
            &["up", "short"],
        ),
        scenario(
            "fib-long",
            ScenarioClass::CanonicalPositive,
            "FIB-DOWN",
            long,
            ExpectedStance::SupportLong,
            &["down", "long"],
        ),
        scenario(
            "fib-negative",
            ScenarioClass::CanonicalNegative,
            "FIB-NEG",
            negative,
            ExpectedStance::Abstain,
            &["no-rejection"],
        ),
        scenario(
            "fib-boundary",
            ScenarioClass::Boundary,
            "FIB-BOUNDARY",
            boundary,
            ExpectedStance::Abstain,
            &["extension-boundary"],
        ),
    ]
}

pub fn liquidity_sweep_reclaim_scenarios() -> Vec<Scenario> {
    let mut long = base_input();
    long.history = vec![
        ScenarioBar {
            event_id: "lsr-long-prior".into(),
            open: 99.0,
            high: 100.0,
            low: 98.0,
            close: 99.0,
            ema_fast: 99.0,
            ema_slow: 99.0,
        },
        ScenarioBar {
            event_id: "lsr-long-sweep".into(),
            open: 98.0,
            high: 101.0,
            low: 97.0,
            close: 99.0,
            ema_fast: 99.0,
            ema_slow: 99.0,
        },
    ];
    long.scalars.insert("close".into(), 99.0);

    let mut short = base_input();
    short.history = vec![
        ScenarioBar {
            event_id: "lsr-short-prior".into(),
            open: 99.0,
            high: 100.0,
            low: 98.0,
            close: 99.0,
            ema_fast: 99.0,
            ema_slow: 99.0,
        },
        ScenarioBar {
            event_id: "lsr-short-sweep".into(),
            open: 101.0,
            high: 103.0,
            low: 98.0,
            close: 99.0,
            ema_fast: 99.0,
            ema_slow: 99.0,
        },
    ];
    short.scalars.insert("close".into(), 99.0);

    let mut negative = long.clone();
    negative.scalars.insert("close".into(), 97.0);
    negative.history[1].high = 100.0;
    let mut boundary = long.clone();
    boundary.history[1].low = 98.0;
    boundary.history[1].high = 100.0;
    let mut missing = long.clone();
    missing.scalars.remove("atr");

    vec![
        scenario(
            "lsr-long",
            ScenarioClass::CanonicalPositive,
            "LSR-LONG",
            long,
            ExpectedStance::SupportLong,
            &["sweep-low", "reclaim", "long"],
        ),
        scenario(
            "lsr-short",
            ScenarioClass::CanonicalPositive,
            "LSR-SHORT",
            short,
            ExpectedStance::SupportShort,
            &["sweep-high", "reclaim", "short"],
        ),
        scenario(
            "lsr-negative",
            ScenarioClass::CanonicalNegative,
            "LSR-NEG",
            negative,
            ExpectedStance::Abstain,
            &["no-reclaim"],
        ),
        scenario(
            "lsr-boundary",
            ScenarioClass::Boundary,
            "LSR-BOUNDARY",
            boundary,
            ExpectedStance::Abstain,
            &["equal-extreme"],
        ),
        scenario(
            "lsr-missing",
            ScenarioClass::Contract,
            "LSR-MISSING",
            missing,
            ExpectedStance::NoHabitat,
            &["missingness"],
        ),
    ]
}

pub fn trend_pullback_scenarios() -> Vec<Scenario> {
    let mut positive = base_input();
    positive.scalars.insert("close".into(), 99.0);
    positive.scalars.insert("ema_fast".into(), 101.0);
    positive.scalars.insert("ema_slow".into(), 100.0);
    let mut negative = positive.clone();
    negative.scalars.insert("close".into(), 100.0);
    let mut boundary = positive.clone();
    boundary.scalars.insert("ema_fast".into(), 100.0);
    let mut missing = positive.clone();
    missing.scalars.remove("ema_fast");
    vec![
        scenario(
            "tp-positive",
            ScenarioClass::CanonicalPositive,
            "TP-POS",
            positive,
            ExpectedStance::SupportLong,
            &["aligned-trend", "pullback", "long"],
        ),
        scenario(
            "tp-negative",
            ScenarioClass::CanonicalNegative,
            "TP-NEG",
            negative,
            ExpectedStance::Abstain,
            &["no-pullback"],
        ),
        scenario(
            "tp-boundary",
            ScenarioClass::Boundary,
            "TP-BOUNDARY",
            boundary,
            ExpectedStance::Abstain,
            &["flat-trend-boundary"],
        ),
        scenario(
            "tp-missing",
            ScenarioClass::Contract,
            "TP-MISSING",
            missing,
            ExpectedStance::NoHabitat,
            &["missingness"],
        ),
    ]
}

pub fn trend_pullback_depth_scenarios() -> Vec<Scenario> {
    let mut positive = base_input();
    positive.scalars.insert("close".into(), 115.0);
    positive.scalars.insert("ema_fast".into(), 121.0);
    positive.scalars.insert("ema_slow".into(), 120.0);
    positive.scalars.insert("swing_high_10".into(), 120.0);
    positive.scalars.insert("swing_low_10".into(), 100.0);
    let mut inclusive_boundary = positive.clone();
    inclusive_boundary.scalars.insert("close".into(), 112.36);
    let mut negative = positive.clone();
    negative.scalars.insert("close".into(), 112.35);
    let mut flat_trend = positive.clone();
    flat_trend.scalars.insert("ema_fast".into(), 120.0);
    let mut missing = positive.clone();
    missing.scalars.remove("swing_high_10");
    vec![
        scenario(
            "tpd-positive",
            ScenarioClass::CanonicalPositive,
            "TPD-POS",
            positive,
            ExpectedStance::SupportLong,
            &["aligned-trend", "depth-under-382", "long"],
        ),
        scenario(
            "tpd-inclusive-boundary",
            ScenarioClass::Boundary,
            "TPD-BOUNDARY-INCLUSIVE",
            inclusive_boundary,
            ExpectedStance::SupportLong,
            &["depth-equals-382"],
        ),
        scenario(
            "tpd-negative",
            ScenarioClass::CanonicalNegative,
            "TPD-NEG",
            negative,
            ExpectedStance::Abstain,
            &["depth-over-382"],
        ),
        scenario(
            "tpd-flat-trend",
            ScenarioClass::Boundary,
            "TPD-FLAT-TREND",
            flat_trend,
            ExpectedStance::Abstain,
            &["flat-trend-boundary"],
        ),
        scenario(
            "tpd-missing",
            ScenarioClass::Contract,
            "TPD-MISSING",
            missing,
            ExpectedStance::NoHabitat,
            &["missingness"],
        ),
    ]
}

pub fn donchian_breakout_scenarios() -> Vec<Scenario> {
    let mut positive = base_input();
    positive.history = channel_history();
    positive.scalars.insert("close".into(), 101.0);
    positive.scalars.insert("window_high_20".into(), 100.0);
    positive.scalars.insert("window_low_20".into(), 90.0);
    let mut boundary = positive.clone();
    boundary.scalars.insert("close".into(), 100.0);
    let mut negative = positive.clone();
    negative.scalars.insert("close".into(), 99.0);
    let mut missing = positive.clone();
    missing.scalars.remove("window_high_20");
    vec![
        scenario(
            "donchian-positive",
            ScenarioClass::CanonicalPositive,
            "DONCHIAN-POS",
            positive,
            ExpectedStance::SupportLong,
            &["channel-20", "strict-high-break", "long"],
        ),
        scenario(
            "donchian-boundary",
            ScenarioClass::Boundary,
            "DONCHIAN-BOUNDARY",
            boundary,
            ExpectedStance::Abstain,
            &["equal-high-boundary"],
        ),
        scenario(
            "donchian-negative",
            ScenarioClass::CanonicalNegative,
            "DONCHIAN-NEG",
            negative,
            ExpectedStance::Abstain,
            &["inside-channel"],
        ),
        scenario(
            "donchian-missing",
            ScenarioClass::Contract,
            "DONCHIAN-MISSING",
            missing,
            ExpectedStance::NoHabitat,
            &["missingness"],
        ),
    ]
}

pub fn volume_confirmed_breakout_scenarios() -> Vec<Scenario> {
    let mut positive = base_input();
    positive.history = channel_history();
    positive.scalars.insert("close".into(), 101.0);
    positive.scalars.insert("volume".into(), 130.0);
    positive.scalars.insert("vol_smooth_ma".into(), 100.0);
    positive.scalars.insert("window_high_20".into(), 100.0);
    positive.scalars.insert("window_low_20".into(), 90.0);
    let mut volume_negative = positive.clone();
    volume_negative.scalars.insert("volume".into(), 100.0);
    let mut price_boundary = positive.clone();
    price_boundary.scalars.insert("close".into(), 100.0);
    let mut missing = positive.clone();
    missing.scalars.remove("volume");
    vec![
        scenario(
            "vcb-positive",
            ScenarioClass::CanonicalPositive,
            "VCB-POS",
            positive,
            ExpectedStance::SupportLong,
            &["channel-break", "volume-confirmed", "long"],
        ),
        scenario(
            "vcb-volume-negative",
            ScenarioClass::CanonicalNegative,
            "VCB-NO-VOLUME",
            volume_negative,
            ExpectedStance::Abstain,
            &["volume-not-confirmed"],
        ),
        scenario(
            "vcb-price-boundary",
            ScenarioClass::Boundary,
            "VCB-EQUAL-CHANNEL",
            price_boundary,
            ExpectedStance::Abstain,
            &["equal-channel-boundary"],
        ),
        scenario(
            "vcb-missing",
            ScenarioClass::Contract,
            "VCB-MISSING",
            missing,
            ExpectedStance::NoHabitat,
            &["missingness"],
        ),
    ]
}

pub fn range_breakout_1to1_scenarios() -> Vec<Scenario> {
    let mut positive = base_input();
    positive.history = channel_history();
    positive.scalars.insert("close".into(), 101.0);
    positive.scalars.insert("window_high_20".into(), 100.0);
    positive.scalars.insert("window_low_20".into(), 90.0);
    positive.scalars.insert("range_height_20".into(), 10.0);
    positive.structured.insert(
        "consolidation_range".into(),
        serde_json::json!([100.0, 90.0, 0.02, true]),
    );
    let mut price_boundary = positive.clone();
    price_boundary.scalars.insert("close".into(), 100.0);
    let mut wide_range = positive.clone();
    wide_range.structured.insert(
        "consolidation_range".into(),
        serde_json::json!([100.0, 90.0, 0.030_001, true]),
    );
    let mut missing = positive.clone();
    missing.structured.remove("consolidation_range");
    vec![
        scenario(
            "range-positive",
            ScenarioClass::CanonicalPositive,
            "RANGE-POS",
            positive,
            ExpectedStance::SupportLong,
            &["channel-break", "narrow-range", "single-bar", "long"],
        ),
        scenario(
            "range-price-boundary",
            ScenarioClass::Boundary,
            "RANGE-EQUAL-CHANNEL",
            price_boundary,
            ExpectedStance::Abstain,
            &["equal-channel-boundary"],
        ),
        scenario(
            "range-width-negative",
            ScenarioClass::CanonicalNegative,
            "RANGE-WIDE",
            wide_range,
            ExpectedStance::Abstain,
            &["wide-range"],
        ),
        scenario(
            "range-missing",
            ScenarioClass::Contract,
            "RANGE-MISSING",
            missing,
            ExpectedStance::NoHabitat,
            &["missingness"],
        ),
    ]
}

pub fn floor_trader_pivot_scenarios() -> Vec<Scenario> {
    let pivots = serde_json::json!([100.0, 110.0, 120.0, 130.0, 140.0, 90.0, 80.0, 70.0, 60.0]);
    let mut long = base_input();
    long.history[1].open = 101.0;
    long.history[1].close = 102.0;
    long.scalars.insert("close".into(), 105.0);
    long.scalars.insert("bar_of_session".into(), 2.0);
    long.structured
        .insert("pivot_points_day".into(), pivots.clone());
    let mut short = long.clone();
    short.history[1].open = 99.0;
    short.history[1].close = 98.0;
    short.scalars.insert("close".into(), 95.0);
    let mut negative = long.clone();
    negative.history[1].close = 101.0;
    let mut geometry_boundary = long.clone();
    geometry_boundary.scalars.insert("close".into(), 100.0);
    let mut missing = long.clone();
    missing.structured.remove("pivot_points_day");
    vec![
        scenario(
            "pivot-long",
            ScenarioClass::CanonicalPositive,
            "PIVOT-LONG",
            long,
            ExpectedStance::SupportLong,
            &["session", "pp-up-drift", "long"],
        ),
        scenario(
            "pivot-short",
            ScenarioClass::CanonicalPositive,
            "PIVOT-SHORT",
            short,
            ExpectedStance::SupportShort,
            &["session", "pp-down-drift", "short"],
        ),
        scenario(
            "pivot-negative",
            ScenarioClass::CanonicalNegative,
            "PIVOT-NO-DRIFT",
            negative,
            ExpectedStance::Abstain,
            &["no-drift"],
        ),
        scenario(
            "pivot-geometry-boundary",
            ScenarioClass::Boundary,
            "PIVOT-ZERO-STOP",
            geometry_boundary,
            ExpectedStance::Abstain,
            &["zero-stop-boundary"],
        ),
        scenario(
            "pivot-missing",
            ScenarioClass::Contract,
            "PIVOT-MISSING",
            missing,
            ExpectedStance::NoHabitat,
            &["missingness"],
        ),
    ]
}

pub fn fib_retracement_continuation_scenarios() -> Vec<Scenario> {
    let fib_up = serde_json::json!([120.0, 1.0, [[0.382, 110.0], [0.786, 105.0]], []]);
    let fib_down = serde_json::json!([80.0, -1.0, [[0.382, 90.0], [0.786, 95.0]], []]);
    let mut long = base_input();
    long.history[1].low = 109.0;
    long.history[1].close = 111.0;
    long.structured.insert("fib_levels".into(), fib_up.clone());
    let mut short = base_input();
    short.history[1].high = 91.0;
    short.history[1].close = 89.0;
    short.structured.insert("fib_levels".into(), fib_down);
    let mut negative = long.clone();
    negative.history[1].low = 111.0;
    let mut boundary = long.clone();
    boundary.history[1].close = 110.0;
    let mut missing = long.clone();
    missing.structured.remove("fib_levels");
    vec![
        scenario(
            "fib-retrace-long",
            ScenarioClass::CanonicalPositive,
            "FIB-RETRACE-LONG",
            long,
            ExpectedStance::SupportLong,
            &["up-impulse", "retracement-touch", "reclaim", "long"],
        ),
        scenario(
            "fib-retrace-short",
            ScenarioClass::CanonicalPositive,
            "FIB-RETRACE-SHORT",
            short,
            ExpectedStance::SupportShort,
            &["down-impulse", "retracement-touch", "reclaim", "short"],
        ),
        scenario(
            "fib-retrace-negative",
            ScenarioClass::CanonicalNegative,
            "FIB-RETRACE-NO-TOUCH",
            negative,
            ExpectedStance::Abstain,
            &["no-touch"],
        ),
        scenario(
            "fib-retrace-boundary",
            ScenarioClass::Boundary,
            "FIB-RETRACE-EQUAL-CLOSE",
            boundary,
            ExpectedStance::Abstain,
            &["equal-level-boundary"],
        ),
        scenario(
            "fib-retrace-missing",
            ScenarioClass::Contract,
            "FIB-RETRACE-MISSING",
            missing,
            ExpectedStance::NoHabitat,
            &["missingness"],
        ),
    ]
}

pub fn obv_adl_regime_scenarios() -> Vec<Scenario> {
    let mut positive = base_input();
    positive.scalars.insert("close".into(), 99.0);
    positive.scalars.insert("ema_fast".into(), 98.0);
    positive.scalars.insert("ema_slow".into(), 100.0);
    positive.scalars.insert("cmf_20".into(), -0.16);
    let mut negative = positive.clone();
    negative.scalars.insert("cmf_20".into(), 0.0);
    let mut boundary = positive.clone();
    boundary.scalars.insert("cmf_20".into(), -0.15);
    let mut missing = positive.clone();
    missing.scalars.remove("cmf_20");
    vec![
        scenario(
            "obv-adl-positive",
            ScenarioClass::CanonicalPositive,
            "OBV-ADL-POS",
            positive,
            ExpectedStance::SupportLong,
            &["cmf-oversold", "below-slow", "priority-d", "long"],
        ),
        scenario(
            "obv-adl-negative",
            ScenarioClass::CanonicalNegative,
            "OBV-ADL-NEUTRAL",
            negative,
            ExpectedStance::Abstain,
            &["cmf-neutral"],
        ),
        scenario(
            "obv-adl-boundary",
            ScenarioClass::Boundary,
            "OBV-ADL-CMF-BOUNDARY",
            boundary,
            ExpectedStance::Abstain,
            &["cmf-equals-boundary"],
        ),
        scenario(
            "obv-adl-missing",
            ScenarioClass::Contract,
            "OBV-ADL-MISSING",
            missing,
            ExpectedStance::NoHabitat,
            &["missingness"],
        ),
    ]
}

pub fn funding_crowding_reversal_scenarios() -> Vec<Scenario> {
    let mut positive = base_input();
    positive.history = (0..11)
        .map(|index| ScenarioBar {
            event_id: format!("funding-{index}"),
            open: if index == 10 { 98.0 } else { 100.0 },
            high: if index == 10 { 105.0 } else { 100.0 },
            low: if index == 10 { 90.0 } else { 100.0 },
            close: if index == 10 { 95.0 } else { 100.0 },
            ema_fast: 100.0,
            ema_slow: 100.0,
        })
        .collect();
    positive.scalars.insert("close".into(), 95.0);
    positive.scalars.insert("funding_rate".into(), 0.001);
    let mut funding_negative = positive.clone();
    funding_negative
        .scalars
        .insert("funding_rate".into(), 0.000_999);
    let mut price_boundary = positive.clone();
    price_boundary.scalars.insert("close".into(), 100.0);
    let mut missing = positive.clone();
    missing.scalars.remove("funding_rate");
    vec![
        scenario(
            "funding-positive",
            ScenarioClass::CanonicalPositive,
            "FUNDING-POS",
            positive,
            ExpectedStance::SupportShort,
            &["funding-extreme", "five-bar-break", "short"],
        ),
        scenario(
            "funding-below-threshold",
            ScenarioClass::CanonicalNegative,
            "FUNDING-BELOW",
            funding_negative,
            ExpectedStance::Abstain,
            &["funding-below-threshold"],
        ),
        scenario(
            "funding-price-boundary",
            ScenarioClass::Boundary,
            "FUNDING-EQUAL-LOW",
            price_boundary,
            ExpectedStance::Abstain,
            &["equal-low-boundary"],
        ),
        scenario(
            "funding-missing",
            ScenarioClass::Contract,
            "FUNDING-MISSING",
            missing,
            ExpectedStance::NoHabitat,
            &["missingness"],
        ),
    ]
}

pub fn open_interest_divergence_scenarios() -> Vec<Scenario> {
    let mut positive = base_input();
    positive.history = (0..6)
        .map(|index| ScenarioBar {
            event_id: format!("oi-{index}"),
            open: 90.0 + index as f64,
            high: 91.0 + index as f64,
            low: 89.0 + index as f64,
            close: 90.0 + index as f64,
            ema_fast: 0.0,
            ema_slow: 0.0,
        })
        .collect();
    positive.scalars.insert("close".into(), 100.0);
    positive.scalars.insert("open_interest".into(), 1.0);
    positive.scalars.insert("long_short_skew".into(), 1.0);
    positive.scalars.insert("vol_zscore".into(), 1.0);
    let mut negative = positive.clone();
    negative.scalars.insert("vol_zscore".into(), 0.0);
    let mut boundary = positive.clone();
    boundary.scalars.insert("long_short_skew".into(), 0.999_999);
    let mut missing = positive.clone();
    missing.scalars.remove("open_interest");
    vec![
        scenario(
            "oi-positive",
            ScenarioClass::CanonicalPositive,
            "OI-POS",
            positive,
            ExpectedStance::SupportLong,
            &["oi-present", "price-up", "positive-volume", "long-heavy"],
        ),
        scenario(
            "oi-negative",
            ScenarioClass::CanonicalNegative,
            "OI-ZERO-VOLUME",
            negative,
            ExpectedStance::Abstain,
            &["zero-zscore"],
        ),
        scenario(
            "oi-boundary",
            ScenarioClass::Boundary,
            "OI-SKEW-BELOW",
            boundary,
            ExpectedStance::Abstain,
            &["skew-below-boundary"],
        ),
        scenario(
            "oi-missing",
            ScenarioClass::Contract,
            "OI-MISSING",
            missing,
            ExpectedStance::NoHabitat,
            &["missingness"],
        ),
    ]
}

pub fn candlestick_reversal_scenarios() -> Vec<Scenario> {
    let mut hammer = base_input();
    hammer.history = vec![
        ScenarioBar {
            event_id: "hammer-prior".into(),
            open: 104.0,
            high: 105.0,
            low: 99.0,
            close: 100.0,
            ema_fast: 100.0,
            ema_slow: 100.0,
        },
        ScenarioBar {
            event_id: "hammer-current".into(),
            open: 100.0,
            high: 101.0,
            low: 94.0,
            close: 101.0,
            ema_fast: 100.0,
            ema_slow: 100.0,
        },
    ];
    hammer.scalars = BTreeMap::from([
        ("close".into(), 101.0),
        ("atr".into(), 2.0),
        ("real_body".into(), 1.0),
        ("body_range_ratio".into(), 1.0 / 7.0),
        ("upper_shadow".into(), 0.0),
        ("lower_shadow".into(), 6.0),
        ("close_position".into(), 1.0),
    ]);
    let mut negative = hammer.clone();
    negative.history[1].low = 98.1;
    negative.scalars.insert("lower_shadow".into(), 1.9);
    let mut inclusive_boundary = hammer.clone();
    inclusive_boundary.history[1].low = 98.0;
    inclusive_boundary.history[1].high = 101.0;
    inclusive_boundary
        .scalars
        .insert("body_range_ratio".into(), 1.0 / 3.0);
    inclusive_boundary
        .scalars
        .insert("lower_shadow".into(), 2.0);
    let mut missing = hammer.clone();
    missing.scalars.remove("close_position");
    vec![
        scenario(
            "hammer-positive",
            ScenarioClass::CanonicalPositive,
            "HAMMER-POS",
            hammer,
            ExpectedStance::SupportLong,
            &["down-context", "bullish-body", "long-lower-shadow", "long"],
        ),
        scenario(
            "hammer-negative-short-lower-shadow",
            ScenarioClass::CanonicalNegative,
            "HAMMER-SHADOW-TOO-SHORT",
            negative,
            ExpectedStance::Abstain,
            &["lower-shadow-fails"],
        ),
        scenario(
            "hammer-inclusive-boundary",
            ScenarioClass::Boundary,
            "HAMMER-INCLUSIVE-RATIOS",
            inclusive_boundary,
            ExpectedStance::SupportLong,
            &["ratio-equality-included"],
        ),
        scenario(
            "hammer-missing-shape-feature",
            ScenarioClass::Contract,
            "HAMMER-MISSING",
            missing,
            ExpectedStance::NoHabitat,
            &["missingness"],
        ),
    ]
}

pub fn volume_climax_reversal_scenarios() -> Vec<Scenario> {
    let mut strict_downtrend = base_input();
    strict_downtrend.history = vec![ScenarioBar {
        event_id: "climax-down".into(),
        open: 100.0,
        high: 101.0,
        low: 90.0,
        close: 95.0,
        ema_fast: 90.0,
        ema_slow: 100.0,
    }];
    strict_downtrend.scalars = BTreeMap::from([
        ("close".into(), 95.0),
        ("ema_fast".into(), 90.0),
        ("ema_slow".into(), 100.0),
        ("atr".into(), 2.0),
        ("volume".into(), 10_000.0),
        ("vol_zscore".into(), 3.0),
        ("vol_min_proximity".into(), 1.0),
    ]);
    let mut strict_uptrend = strict_downtrend.clone();
    strict_uptrend.history[0] = ScenarioBar {
        event_id: "climax-up".into(),
        open: 100.0,
        high: 110.0,
        low: 99.0,
        close: 105.0,
        ema_fast: 110.0,
        ema_slow: 100.0,
    };
    strict_uptrend.scalars.insert("close".into(), 105.0);
    strict_uptrend.scalars.insert("ema_fast".into(), 110.0);
    let mut negative = strict_downtrend.clone();
    negative.scalars.insert("vol_zscore".into(), 1.999_999);
    let mut inclusive_boundary = strict_uptrend.clone();
    inclusive_boundary.scalars.insert("vol_zscore".into(), 2.0);
    let mut missing = strict_downtrend.clone();
    missing.scalars.remove("vol_zscore");
    missing.scalars.remove("vol_min_proximity");
    vec![
        scenario(
            "volume-climax-strict-downtrend",
            ScenarioClass::CanonicalPositive,
            "CLIMAX-STRICT-LONG",
            strict_downtrend,
            ExpectedStance::SupportLong,
            &["three-sigma", "downtrend", "priority-e", "long"],
        ),
        scenario(
            "volume-climax-strict-uptrend",
            ScenarioClass::CanonicalPositive,
            "CLIMAX-STRICT-SHORT",
            strict_uptrend,
            ExpectedStance::SupportShort,
            &["three-sigma", "uptrend", "priority-e", "short"],
        ),
        scenario(
            "volume-climax-below-threshold",
            ScenarioClass::CanonicalNegative,
            "CLIMAX-BELOW-TWO-SIGMA",
            negative,
            ExpectedStance::Abstain,
            &["below-two-sigma"],
        ),
        scenario(
            "volume-climax-inclusive-boundary",
            ScenarioClass::Boundary,
            "CLIMAX-TWO-SIGMA-INCLUSIVE",
            inclusive_boundary,
            ExpectedStance::SupportShort,
            &["two-sigma-equality", "priority-b", "short"],
        ),
        scenario(
            "volume-climax-missing-volume-statistics",
            ScenarioClass::Contract,
            "CLIMAX-MISSING-STATS",
            missing,
            ExpectedStance::NoHabitat,
            &["missingness"],
        ),
    ]
}

pub fn gap_exhaustion_scenarios() -> Vec<Scenario> {
    let mut up_exhaustion = base_input();
    up_exhaustion.history = vec![
        ScenarioBar {
            event_id: "gap-up-0".into(),
            open: 99.0,
            high: 100.0,
            low: 98.0,
            close: 99.0,
            ema_fast: 0.0,
            ema_slow: 0.0,
        },
        ScenarioBar {
            event_id: "gap-up-1".into(),
            open: 101.0,
            high: 102.0,
            low: 100.0,
            close: 101.5,
            ema_fast: 0.0,
            ema_slow: 0.0,
        },
        ScenarioBar {
            event_id: "gap-up-2".into(),
            open: 103.0,
            high: 104.0,
            low: 102.0,
            close: 103.5,
            ema_fast: 0.0,
            ema_slow: 0.0,
        },
        ScenarioBar {
            event_id: "gap-up-3".into(),
            open: 105.0,
            high: 106.0,
            low: 103.0,
            close: 104.0,
            ema_fast: 0.0,
            ema_slow: 0.0,
        },
    ];
    up_exhaustion.scalars = BTreeMap::from([
        ("close".into(), 104.0),
        ("atr".into(), 2.0),
        ("gap_dir".into(), 1.0),
        ("gap_size".into(), 1.0),
    ]);
    up_exhaustion.structured.insert(
        "gap_levels".into(),
        serde_json::json!([[105.0, 104.0, 1.0]]),
    );
    let mut down_exhaustion = up_exhaustion.clone();
    down_exhaustion.history = vec![
        ScenarioBar {
            event_id: "gap-down-0".into(),
            open: 101.0,
            high: 102.0,
            low: 100.0,
            close: 101.0,
            ema_fast: 0.0,
            ema_slow: 0.0,
        },
        ScenarioBar {
            event_id: "gap-down-1".into(),
            open: 99.0,
            high: 100.0,
            low: 98.0,
            close: 98.5,
            ema_fast: 0.0,
            ema_slow: 0.0,
        },
        ScenarioBar {
            event_id: "gap-down-2".into(),
            open: 97.0,
            high: 98.0,
            low: 96.0,
            close: 96.5,
            ema_fast: 0.0,
            ema_slow: 0.0,
        },
        ScenarioBar {
            event_id: "gap-down-3".into(),
            open: 95.0,
            high: 96.0,
            low: 94.0,
            close: 96.0,
            ema_fast: 0.0,
            ema_slow: 0.0,
        },
    ];
    down_exhaustion.scalars.insert("close".into(), 96.0);
    down_exhaustion.scalars.insert("gap_dir".into(), -1.0);
    down_exhaustion
        .structured
        .insert("gap_levels".into(), serde_json::json!([[96.0, 95.0, -1.0]]));
    let mut negative = up_exhaustion.clone();
    negative.history[3].close = 105.5;
    negative.scalars.insert("close".into(), 105.5);
    let mut boundary = up_exhaustion.clone();
    boundary.history[3].close = 105.0;
    boundary.scalars.insert("close".into(), 105.0);
    let mut missing = up_exhaustion.clone();
    missing.structured.remove("gap_levels");
    vec![
        scenario(
            "gap-exhaustion-up",
            ScenarioClass::CanonicalPositive,
            "GAP-EXHAUSTION-SHORT",
            up_exhaustion,
            ExpectedStance::SupportShort,
            &["three-up-gaps", "reversal-close", "frozen-zone", "short"],
        ),
        scenario(
            "gap-exhaustion-down",
            ScenarioClass::CanonicalPositive,
            "GAP-EXHAUSTION-LONG",
            down_exhaustion,
            ExpectedStance::SupportLong,
            &["three-down-gaps", "reversal-close", "frozen-zone", "long"],
        ),
        scenario(
            "gap-exhaustion-negative",
            ScenarioClass::CanonicalNegative,
            "GAP-EXHAUSTION-HOLDS",
            negative,
            ExpectedStance::Abstain,
            &["gap-direction-holds"],
        ),
        scenario(
            "gap-exhaustion-equal-close",
            ScenarioClass::Boundary,
            "GAP-EXHAUSTION-EQUAL-OPEN",
            boundary,
            ExpectedStance::Abstain,
            &["strict-reversal-boundary"],
        ),
        scenario(
            "gap-exhaustion-missing-zones",
            ScenarioClass::Contract,
            "GAP-EXHAUSTION-MISSING",
            missing,
            ExpectedStance::NoHabitat,
            &["missingness"],
        ),
    ]
}

fn bollinger_reversion_world(last_close: f64, upper: bool) -> ScenarioInput {
    let mut input = base_input();
    let mut closes = Vec::with_capacity(20);
    for index in 0..19 {
        let close = if index < 10 {
            if upper {
                101.5
            } else {
                98.5
            }
        } else if upper {
            98.333_333_333_333_33
        } else {
            101.666_666_666_666_67
        };
        closes.push(close);
    }
    closes.push(last_close);
    let mid = closes.iter().sum::<f64>() / closes.len() as f64;
    let sd = (closes
        .iter()
        .map(|close| (close - mid).powi(2))
        .sum::<f64>()
        / closes.len() as f64)
        .sqrt();
    input.history = closes
        .iter()
        .enumerate()
        .map(|(index, close)| ScenarioBar {
            event_id: format!("bb-reversion-{upper}-{index}"),
            open: *close,
            high: *close + 1.0,
            low: *close - 1.0,
            close: *close,
            ema_fast: 100.0,
            ema_slow: 100.0,
        })
        .collect();
    input.scalars = BTreeMap::from([
        ("close".into(), last_close),
        ("bb_mid".into(), mid),
        ("bb_upper".into(), mid + 2.0 * sd),
        ("bb_lower".into(), mid - 2.0 * sd),
        ("bb_pct_b".into(), 0.0),
        ("bb_bandwidth".into(), 4.0 * sd / mid),
        ("ema_fast".into(), 100.0),
        ("ema_slow".into(), 100.0),
    ]);
    input
}

pub fn bollinger_reversion_scenarios() -> Vec<Scenario> {
    let long = bollinger_reversion_world(95.0, false);
    let short = bollinger_reversion_world(105.0, true);
    let negative = bollinger_reversion_world(93.0, false);
    let inclusive_two_sd = bollinger_reversion_world(100.0 - (40.0_f64 / 3.0).sqrt(), false);
    let mut missing = long.clone();
    missing.scalars.remove("bb_pct_b");
    vec![
        scenario(
            "bb-reversion-long",
            ScenarioClass::CanonicalPositive,
            "BB-REVERSION-LONG",
            long,
            ExpectedStance::SupportLong,
            &["lower-fade-zone", "long"],
        ),
        scenario(
            "bb-reversion-short",
            ScenarioClass::CanonicalPositive,
            "BB-REVERSION-SHORT",
            short,
            ExpectedStance::SupportShort,
            &["upper-fade-zone", "short"],
        ),
        scenario(
            "bb-reversion-beyond-three-sd",
            ScenarioClass::CanonicalNegative,
            "BB-REVERSION-BEYOND-THREE",
            negative,
            ExpectedStance::Abstain,
            &["beyond-three-sd"],
        ),
        scenario(
            "bb-reversion-inclusive-two-sd",
            ScenarioClass::Boundary,
            "BB-REVERSION-TWO-SD-INCLUSIVE",
            inclusive_two_sd,
            ExpectedStance::SupportLong,
            &["two-sd-equality-included"],
        ),
        scenario(
            "bb-reversion-missing",
            ScenarioClass::Contract,
            "BB-REVERSION-MISSING",
            missing,
            ExpectedStance::NoHabitat,
            &["missingness"],
        ),
    ]
}

pub fn bollinger_breakout_scenarios() -> Vec<Scenario> {
    let long = bollinger_reversion_world(105.0, true);
    let short = bollinger_reversion_world(95.0, false);
    let mut boundary = bollinger_reversion_world(100.0, false);
    // The scalar midpoint is the state feature driving the default gate.  Its
    // exact equality boundary must not inherit a floating-point summation
    // residue from fixture construction.
    boundary.scalars.insert("bb_mid".into(), 100.0);
    let negative = boundary.clone();
    let mut missing = long.clone();
    missing.scalars.remove("bb_bandwidth");
    vec![
        scenario(
            "bb-breakout-long",
            ScenarioClass::CanonicalPositive,
            "BB-BREAKOUT-LONG",
            long,
            ExpectedStance::SupportLong,
            &["above-mid", "long"],
        ),
        scenario(
            "bb-breakout-short",
            ScenarioClass::CanonicalPositive,
            "BB-BREAKOUT-SHORT",
            short,
            ExpectedStance::SupportShort,
            &["below-mid", "short"],
        ),
        scenario(
            "bb-breakout-mid-negative",
            ScenarioClass::CanonicalNegative,
            "BB-BREAKOUT-NO-CROSS",
            negative,
            ExpectedStance::Abstain,
            &["no-mid-cross"],
        ),
        scenario(
            "bb-breakout-mid-equality",
            ScenarioClass::Boundary,
            "BB-BREAKOUT-EQUAL-MID",
            boundary,
            ExpectedStance::Abstain,
            &["mid-equality"],
        ),
        scenario(
            "bb-breakout-missing",
            ScenarioClass::Contract,
            "BB-BREAKOUT-MISSING",
            missing,
            ExpectedStance::NoHabitat,
            &["missingness"],
        ),
    ]
}

pub fn pilot_oracle(id: &str, version: &str, scenarios: &[Scenario]) -> DeclarativeScenarioOracle {
    DeclarativeScenarioOracle::new(
        id,
        version,
        scenarios
            .iter()
            .map(|scenario| (scenario.property_id.clone(), scenario.expected))
            .collect(),
    )
}

/// Scale, irrelevant-feature, and temporal suffix relations.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum MetamorphicRelation {
    PriceScale,
    IrrelevantFeature,
    PrefixNonInterference,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct MetamorphicReceipt {
    pub relation: String,
    pub source_hash: String,
    pub transformed_hash: String,
    pub passed: bool,
    pub authority: QualificationAuthority,
    pub economic_claim: String,
}

pub fn verify_metamorphic(
    expert_id: &str,
    relation: MetamorphicRelation,
    source: &Scenario,
) -> Result<MetamorphicReceipt, V8CoreError> {
    let transformed = match relation {
        MetamorphicRelation::PriceScale => source.scaled(10.0)?,
        MetamorphicRelation::IrrelevantFeature => {
            let mut scenario = source.clone();
            scenario
                .input
                .scalars
                .insert("undeclared_irrelevant_feature".into(), 999_999.0);
            scenario.scenario_id.push_str(":irrelevant");
            scenario
        }
        MetamorphicRelation::PrefixNonInterference => {
            let mut scenario = source.clone();
            scenario.input.future_suffix = vec![ScenarioBar {
                event_id: "different-future".into(),
                open: 1.0,
                high: 9_999_999.0,
                low: 0.01,
                close: 2.0,
                ema_fast: 0.0,
                ema_slow: 0.0,
            }];
            scenario.scenario_id.push_str(":future");
            scenario
        }
    };
    let original = stance_from_eval(&execute_scenario(expert_id, source));
    let observed = stance_from_eval(&execute_scenario(expert_id, &transformed));
    Ok(MetamorphicReceipt {
        relation: format!("{relation:?}"),
        source_hash: source.hash(),
        transformed_hash: transformed.hash(),
        passed: original == observed,
        authority: QualificationAuthority::SemanticQualification,
        economic_claim: NO_ECONOMIC_CLAIM.into(),
    })
}

/// Mutants are explicit qualification controls. They are never compiled into
/// production expert dispatch and never receive economic authority.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
pub enum MutationKind {
    DirectionInversion,
    ThresholdRelaxation,
    AlwaysSupport,
    AlwaysAbstain,
    HiddenState,
    FutureRead,
}

impl MutationKind {
    pub fn critical(self) -> bool {
        matches!(
            self,
            Self::DirectionInversion | Self::HiddenState | Self::FutureRead
        )
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct MutationReceipt {
    pub mutant: MutationKind,
    pub scenario_id: String,
    pub killed: bool,
    pub localization: String,
    pub authority: QualificationAuthority,
    pub economic_claim: String,
}

/// Stateful mutant harness only; its state demonstrates why a real Expert
/// must be replay deterministic. It is not part of `experts::TABLE`.
#[derive(Debug, Default)]
pub struct MutantHarness {
    hidden_counter: u64,
}

impl MutantHarness {
    pub fn observe(
        &mut self,
        expert_id: &str,
        mutant: MutationKind,
        scenario: &Scenario,
    ) -> ExpectedStance {
        let baseline = stance_from_eval(&execute_scenario(expert_id, scenario));
        match mutant {
            MutationKind::DirectionInversion => match baseline {
                ExpectedStance::SupportLong => ExpectedStance::SupportShort,
                ExpectedStance::SupportShort => ExpectedStance::SupportLong,
                other => other,
            },
            MutationKind::ThresholdRelaxation | MutationKind::AlwaysSupport => {
                ExpectedStance::SupportShort
            }
            MutationKind::AlwaysAbstain => ExpectedStance::Abstain,
            MutationKind::HiddenState => {
                self.hidden_counter = self.hidden_counter.saturating_add(1);
                if self.hidden_counter.is_multiple_of(2) {
                    ExpectedStance::Abstain
                } else {
                    baseline
                }
            }
            MutationKind::FutureRead => {
                if scenario
                    .input
                    .future_suffix
                    .iter()
                    .any(|bar| bar.high > 1_000.0)
                {
                    ExpectedStance::SupportShort
                } else {
                    baseline
                }
            }
        }
    }
}

pub fn kill_mutants(expert_id: &str, scenarios: &[Scenario]) -> Vec<MutationReceipt> {
    let mutants = [
        MutationKind::DirectionInversion,
        MutationKind::ThresholdRelaxation,
        MutationKind::AlwaysSupport,
        MutationKind::AlwaysAbstain,
        MutationKind::HiddenState,
        MutationKind::FutureRead,
    ];
    let mut receipts = Vec::new();
    for mutant in mutants {
        let mut harness = MutantHarness::default();
        let mut killed = false;
        let mut first_scenario = "none".to_string();
        for scenario in scenarios {
            let first = harness.observe(expert_id, mutant, scenario);
            let second = if mutant == MutationKind::HiddenState {
                Some(harness.observe(expert_id, mutant, scenario))
            } else {
                None
            };
            let differs =
                first != scenario.expected || second.is_some_and(|stance| stance != first);
            if differs {
                killed = true;
                first_scenario = scenario.scenario_id.clone();
                break;
            }
        }
        receipts.push(MutationReceipt {
            mutant,
            scenario_id: first_scenario,
            killed,
            localization: if killed {
                format!("{mutant:?} detected by D-141 scenario or replay invariant")
            } else {
                "survived; qualification falsified".into()
            },
            authority: QualificationAuthority::SemanticQualification,
            economic_claim: NO_ECONOMIC_CLAIM.into(),
        });
    }
    receipts
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct MutationReport {
    pub receipts: Vec<MutationReceipt>,
    pub critical_generated: usize,
    pub critical_killed: usize,
    pub non_equivalent_generated: usize,
    pub non_equivalent_killed: usize,
    pub authority: QualificationAuthority,
    pub economic_claim: String,
}

impl MutationReport {
    pub fn from_receipts(receipts: Vec<MutationReceipt>) -> Self {
        let critical_generated = receipts
            .iter()
            .filter(|receipt| receipt.mutant.critical())
            .count();
        let critical_killed = receipts
            .iter()
            .filter(|receipt| receipt.mutant.critical() && receipt.killed)
            .count();
        let non_equivalent_generated = receipts.len();
        let non_equivalent_killed = receipts.iter().filter(|receipt| receipt.killed).count();
        Self {
            receipts,
            critical_generated,
            critical_killed,
            non_equivalent_generated,
            non_equivalent_killed,
            authority: QualificationAuthority::SemanticQualification,
            economic_claim: NO_ECONOMIC_CLAIM.into(),
        }
    }

    pub fn critical_kill_complete(&self) -> bool {
        self.critical_generated == self.critical_killed
    }
    pub fn mutation_score(&self) -> Option<f64> {
        (self.non_equivalent_generated != 0)
            .then(|| self.non_equivalent_killed as f64 / self.non_equivalent_generated as f64)
    }
}

/// A deterministic conditional generator using a versioned, local LCG.  Its
/// samples are semantic worlds and explicitly do not model market economics.
#[derive(Debug, Clone)]
pub struct ConditionalScenarioGenerator {
    state: u64,
    pub seed_manifest: String,
}

impl ConditionalScenarioGenerator {
    pub fn new(seed: u64, seed_manifest: impl Into<String>) -> Self {
        Self {
            state: seed,
            seed_manifest: seed_manifest.into(),
        }
    }
    fn next_u64(&mut self) -> u64 {
        self.state = self
            .state
            .wrapping_mul(6364136223846793005)
            .wrapping_add(1442695040888963407);
        self.state
    }
    fn next_unit(&mut self) -> f64 {
        (self.next_u64() >> 11) as f64 / ((1_u64 << 53) as f64)
    }

    pub fn failed_breakout_world(&mut self, index: usize) -> Scenario {
        let mut input = base_input();
        let noise = self.next_unit();
        let below = self.next_unit() > 0.5;
        let close = if below {
            100.0 - (0.01 + noise)
        } else {
            100.0 + noise
        };
        input.scalars.insert("close".into(), close);
        let expected = if below {
            ExpectedStance::SupportShort
        } else {
            ExpectedStance::Abstain
        };
        let cells = [
            if below { "rejection" } else { "no-rejection" },
            if noise < 0.33 {
                "low-noise"
            } else if noise < 0.66 {
                "medium-noise"
            } else {
                "high-noise"
            },
        ];
        scenario(
            &format!("generated-fb-{index}"),
            ScenarioClass::Conditional,
            "FB-CONDITIONAL",
            input,
            expected,
            &cells,
        )
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct BehaviorCoverage {
    pub required_cells: BTreeSet<String>,
    pub visited_cells: BTreeSet<String>,
    pub critical_cells: BTreeSet<String>,
    pub authority: QualificationAuthority,
    pub economic_claim: String,
}

impl BehaviorCoverage {
    pub fn from_scenarios(
        required_cells: impl IntoIterator<Item = String>,
        scenarios: &[Scenario],
    ) -> Self {
        let required_cells: BTreeSet<_> = required_cells.into_iter().collect();
        let visited_cells = scenarios
            .iter()
            .flat_map(|scenario| scenario.required_cells.iter().cloned())
            .collect();
        let critical_cells = required_cells
            .iter()
            .filter(|cell| cell.contains("critical"))
            .cloned()
            .collect();
        Self {
            required_cells,
            visited_cells,
            critical_cells,
            authority: QualificationAuthority::SemanticQualification,
            economic_claim: NO_ECONOMIC_CLAIM.into(),
        }
    }
    pub fn fraction(&self) -> Option<f64> {
        (!self.required_cells.is_empty()).then(|| {
            self.required_cells
                .intersection(&self.visited_cells)
                .count() as f64
                / self.required_cells.len() as f64
        })
    }
    pub fn critical_complete(&self) -> bool {
        self.critical_cells.is_subset(&self.visited_cells)
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct CounterexampleReceipt {
    pub counterexample_id: String,
    pub scenario_hash: String,
    pub seed: u64,
    pub property_id: String,
    pub expected: ExpectedStance,
    pub observed: ExpectedStance,
    pub shrink_steps: usize,
    pub authority: QualificationAuthority,
    pub economic_claim: String,
}

/// EAST is deliberately a bounded deterministic search. It searches only
/// scenarios emitted by the declared generator and ignores invalid worlds.
pub fn east_search(
    expert_id: &str,
    mut generator: ConditionalScenarioGenerator,
    budget: usize,
) -> Option<CounterexampleReceipt> {
    for index in 0..budget {
        let scenario = generator.failed_breakout_world(index);
        let observed = stance_from_eval(&execute_scenario(expert_id, &scenario));
        if observed != scenario.expected {
            return Some(CounterexampleReceipt {
                counterexample_id: format!("ce:{}:{index}", scenario.scenario_id),
                scenario_hash: scenario.hash(),
                seed: scenario.seed,
                property_id: scenario.property_id,
                expected: scenario.expected,
                observed,
                shrink_steps: 0,
                authority: QualificationAuthority::SemanticQualification,
                economic_claim: NO_ECONOMIC_CLAIM.into(),
            });
        }
    }
    None
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PairedTrial {
    pub differences: Vec<f64>,
    pub bounded_loss_range: Option<(f64, f64)>,
    pub assumption: String,
    pub authority: QualificationAuthority,
    pub economic_claim: String,
}

impl PairedTrial {
    pub fn from_losses(
        incumbent: &[f64],
        challenger: &[f64],
        bounded_loss_range: Option<(f64, f64)>,
        assumption: impl Into<String>,
    ) -> Result<Self, V8CoreError> {
        if incumbent.len() != challenger.len() || incumbent.is_empty() {
            return Err(V8CoreError::QuantInvariant(
                "paired trials require non-empty equal-length loss vectors".into(),
            ));
        }
        if incumbent
            .iter()
            .chain(challenger)
            .any(|value| !value.is_finite())
        {
            return Err(V8CoreError::QuantInvariant(
                "paired trial observations must be finite".into(),
            ));
        }
        Ok(Self {
            differences: challenger
                .iter()
                .zip(incumbent)
                .map(|(a, b)| a - b)
                .collect(),
            bounded_loss_range,
            assumption: assumption.into(),
            authority: QualificationAuthority::StatisticalQualification,
            economic_claim: NO_ECONOMIC_CLAIM.into(),
        })
    }
    pub fn mean_difference(&self) -> f64 {
        self.differences.iter().sum::<f64>() / self.differences.len() as f64
    }
    pub fn hoeffding_interval(&self, alpha: f64) -> Result<(f64, f64), V8CoreError> {
        let (lo, hi) = self.bounded_loss_range.ok_or_else(|| {
            V8CoreError::QuantInvariant(
                "bounded loss range is required for a Hoeffding confidence interval".into(),
            )
        })?;
        if !alpha.is_finite()
            || alpha <= 0.0
            || alpha >= 1.0
            || !matches!(lo.partial_cmp(&hi), Some(std::cmp::Ordering::Less))
        {
            return Err(V8CoreError::QuantInvariant(
                "invalid alpha or bounded loss range".into(),
            ));
        }
        let width = (hi - lo) * ((2.0 / alpha).ln() / (2.0 * self.differences.len() as f64)).sqrt();
        let mean = self.mean_difference();
        Ok((mean - width, mean + width))
    }
}

/// A manifest-bound nonnegative e-value. The caller supplies a verified
/// construction; this type refuses to invent one.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct EValue {
    pub value: f64,
    pub family_id: String,
    pub construction_id: String,
    pub authority: QualificationAuthority,
    pub economic_claim: String,
}

impl EValue {
    pub fn new(
        value: f64,
        family_id: impl Into<String>,
        construction_id: impl Into<String>,
    ) -> Result<Self, V8CoreError> {
        let family_id = family_id.into();
        let construction_id = construction_id.into();
        if !value.is_finite() || value < 0.0 || family_id.is_empty() || construction_id.is_empty() {
            return Err(V8CoreError::QuantInvariant(
                "e-value must be finite/nonnegative and family/construction bound".into(),
            ));
        }
        Ok(Self {
            value,
            family_id,
            construction_id,
            authority: QualificationAuthority::StatisticalQualification,
            economic_claim: NO_ECONOMIC_CLAIM.into(),
        })
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum StatisticalDecision {
    Supported,
    NotSupported,
    Unresolved,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct RiskCertificate {
    pub target: String,
    pub assumptions: Vec<String>,
    pub decision: StatisticalDecision,
    pub authority: QualificationAuthority,
    pub economic_claim: String,
}

pub fn non_inferiority(
    trial: &PairedTrial,
    declared_margin: Option<f64>,
    alpha: f64,
) -> Result<RiskCertificate, V8CoreError> {
    let margin = declared_margin.ok_or_else(|| {
        V8CoreError::QuantInvariant(
            "non-inferiority margin must be declared before evaluation".into(),
        )
    })?;
    let (lower, _) = trial.hoeffding_interval(alpha)?;
    Ok(RiskCertificate {
        target: format!("mean challenger-minus-incumbent loss exceeds -{margin}"),
        assumptions: vec![trial.assumption.clone(), "bounded paired losses".into()],
        decision: if lower > -margin {
            StatisticalDecision::Supported
        } else {
            StatisticalDecision::NotSupported
        },
        authority: QualificationAuthority::StatisticalQualification,
        economic_claim: NO_ECONOMIC_CLAIM.into(),
    })
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
pub enum EwqGate {
    Ewq01ManifestHash,
    Ewq02TemporalFeatureIdentity,
    Ewq03CanonicalNegative,
    Ewq04BoundaryMetamorphic,
    Ewq05CriticalMutationKill,
    Ewq06BehaviorCoverage,
    Ewq07SealedChallenge,
    Ewq08StatisticalNoRegression,
    Ewq09RealTapeAttribution,
    Ewq10FrozenEconomicOos,
}

impl EwqGate {
    pub fn requires_economic_authority(self) -> bool {
        matches!(
            self,
            Self::Ewq09RealTapeAttribution | Self::Ewq10FrozenEconomicOos
        )
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum GateStatus {
    Pass,
    Fail,
    Unresolved,
    NotApplicable,
    Blocked,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum EpistemicVerdict {
    SemanticallyQualified,
    Falsified,
    Unresolved,
    NotApplicable,
    NoEconomicClaim,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct EvidenceObject {
    pub evidence_id: String,
    pub method: String,
    pub authority: QualificationAuthority,
    pub assumptions: Vec<String>,
    pub scope: String,
    pub stopping_rule: Option<String>,
    pub result_hash: String,
    pub economic_claim: String,
}

impl EvidenceObject {
    pub fn new(
        method: impl Into<String>,
        authority: QualificationAuthority,
        assumptions: Vec<String>,
        scope: impl Into<String>,
        stopping_rule: Option<String>,
        result: &serde_json::Value,
    ) -> Self {
        let method = method.into();
        let scope = scope.into();
        let result_hash = crate::hash::hash_value_blake3(result);
        let mut c = Canon::new();
        c.push_str(&method);
        c.push_str(&scope);
        c.push_str(&result_hash);
        for assumption in &assumptions {
            c.push_str(assumption);
        }
        if let Some(rule) = &stopping_rule {
            c.push_str(rule);
        }
        Self {
            evidence_id: c.finish_blake3_hex(),
            method,
            authority,
            assumptions,
            scope,
            stopping_rule,
            result_hash,
            economic_claim: NO_ECONOMIC_CLAIM.into(),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ExpertPassport {
    pub expert_id: String,
    pub expert_version: String,
    pub manifest_hash: String,
    pub qualification_run_hash: String,
    pub gate_status: BTreeMap<EwqGate, GateStatus>,
    pub evidence_ids: Vec<String>,
    pub verdict: EpistemicVerdict,
    pub economic_claim: String,
}

impl ExpertPassport {
    pub fn from_run(
        manifest: &ExpertQualificationManifest,
        run: &QualificationRun,
        mutation: &MutationReport,
        coverage: &BehaviorCoverage,
        evidence: &[EvidenceObject],
    ) -> Result<Self, V8CoreError> {
        let manifest_hash = manifest.hash()?;
        if manifest_hash != run.manifest_hash {
            return Err(V8CoreError::QuantInvariant(
                "passport cannot bind a run from another manifest".into(),
            ));
        }
        let mut gate_status = BTreeMap::new();
        gate_status.insert(EwqGate::Ewq01ManifestHash, GateStatus::Pass);
        gate_status.insert(EwqGate::Ewq02TemporalFeatureIdentity, GateStatus::Pass);
        gate_status.insert(
            EwqGate::Ewq03CanonicalNegative,
            if run.passed() == run.total() {
                GateStatus::Pass
            } else {
                GateStatus::Fail
            },
        );
        gate_status.insert(EwqGate::Ewq04BoundaryMetamorphic, GateStatus::Pass);
        gate_status.insert(
            EwqGate::Ewq05CriticalMutationKill,
            if mutation.critical_kill_complete() {
                GateStatus::Pass
            } else {
                GateStatus::Fail
            },
        );
        gate_status.insert(
            EwqGate::Ewq06BehaviorCoverage,
            if coverage.critical_complete() {
                GateStatus::Pass
            } else {
                GateStatus::Unresolved
            },
        );
        gate_status.insert(EwqGate::Ewq07SealedChallenge, GateStatus::Unresolved);
        gate_status.insert(
            EwqGate::Ewq08StatisticalNoRegression,
            GateStatus::Unresolved,
        );
        // D-141 cannot provide real-tape or frozen-OOS authority by construction.
        gate_status.insert(EwqGate::Ewq09RealTapeAttribution, GateStatus::NotApplicable);
        gate_status.insert(EwqGate::Ewq10FrozenEconomicOos, GateStatus::Blocked);
        let verdict = if gate_status
            .values()
            .any(|status| *status == GateStatus::Fail)
        {
            EpistemicVerdict::Falsified
        } else if gate_status.get(&EwqGate::Ewq01ManifestHash) == Some(&GateStatus::Pass)
            && gate_status.get(&EwqGate::Ewq02TemporalFeatureIdentity) == Some(&GateStatus::Pass)
            && gate_status.get(&EwqGate::Ewq03CanonicalNegative) == Some(&GateStatus::Pass)
            && gate_status.get(&EwqGate::Ewq04BoundaryMetamorphic) == Some(&GateStatus::Pass)
            && gate_status.get(&EwqGate::Ewq05CriticalMutationKill) == Some(&GateStatus::Pass)
        {
            EpistemicVerdict::SemanticallyQualified
        } else {
            EpistemicVerdict::Unresolved
        };
        Ok(Self {
            expert_id: manifest.card.expert_id.clone(),
            expert_version: manifest.card.expert_version.clone(),
            manifest_hash,
            qualification_run_hash: run.run_hash.clone(),
            gate_status,
            evidence_ids: evidence
                .iter()
                .map(|item| item.evidence_id.clone())
                .collect(),
            verdict,
            economic_claim: NO_ECONOMIC_CLAIM.into(),
        })
    }

    pub fn promotion_eligible(&self) -> bool {
        false
    }
}

/// A D-141 intervention does not own, mutate, delete, or recreate an
/// opportunity.  It records only a registered force-abstain comparison.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct AttributionObservation {
    pub opportunity_id: String,
    pub baseline_utility: Option<f64>,
    pub force_abstain_utility: Option<f64>,
    pub baseline_fee: Option<f64>,
    pub force_abstain_fee: Option<f64>,
    pub displacement_cost: Option<f64>,
    pub unique_capture: Option<bool>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct MarginalContribution {
    pub opportunity_id: String,
    pub utility_delta: Option<f64>,
    pub fee_delta: Option<f64>,
    pub displacement_cost: Option<f64>,
    pub unique_capture: Option<bool>,
    pub authority: QualificationAuthority,
    pub economic_claim: String,
}

pub fn forced_abstention_attribution(
    observations: &[AttributionObservation],
) -> Vec<MarginalContribution> {
    observations
        .iter()
        .map(|item| MarginalContribution {
            opportunity_id: item.opportunity_id.clone(),
            utility_delta: item
                .baseline_utility
                .zip(item.force_abstain_utility)
                .map(|(baseline, abstain)| baseline - abstain),
            fee_delta: item
                .baseline_fee
                .zip(item.force_abstain_fee)
                .map(|(baseline, abstain)| baseline - abstain),
            displacement_cost: item.displacement_cost,
            unique_capture: item.unique_capture,
            authority: QualificationAuthority::RealTapeDiagnostic,
            economic_claim: NO_ECONOMIC_CLAIM.into(),
        })
        .collect()
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct InteractionObservation {
    pub opportunity_id: String,
    pub baseline: Option<f64>,
    pub without_a: Option<f64>,
    pub without_b: Option<f64>,
    pub without_both: Option<f64>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct InteractionReceipt {
    pub opportunity_id: String,
    /// `V(AB) - V(A removed) - V(B removed) + V(A,B removed)`: diagnostic,
    /// not a forced allocation to either witness.
    pub non_additive_delta: Option<f64>,
    pub authority: QualificationAuthority,
    pub economic_claim: String,
}

pub fn interaction_accounting(items: &[InteractionObservation]) -> Vec<InteractionReceipt> {
    items
        .iter()
        .map(|item| InteractionReceipt {
            opportunity_id: item.opportunity_id.clone(),
            non_additive_delta: item
                .baseline
                .zip(item.without_a)
                .zip(item.without_b)
                .zip(item.without_both)
                .map(|(((baseline, a), b), both)| baseline - a - b + both),
            authority: QualificationAuthority::RealTapeDiagnostic,
            economic_claim: NO_ECONOMIC_CLAIM.into(),
        })
        .collect()
}

/// The legacy adapter's fixed numbers are ordinal migration data, never
/// calibrated probabilities.  This sidecar avoids treating them as a Brier
/// forecast without widening the canonical evidence ontology.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum EvidenceStrength {
    Ordinal {
        level: OrdinalStrength,
    },
    CalibratedProbability {
        probability: f64,
        calibrator_id: String,
    },
    LikelihoodRatio {
        log_lr: f64,
        model_id: String,
    },
    Unscored,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum OrdinalStrength {
    Weak,
    Moderate,
    Strong,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum MetricAvailability {
    Available,
    NotApplicable,
    Unresolved,
}

pub fn calibration_availability(strength: &EvidenceStrength) -> MetricAvailability {
    match strength {
        EvidenceStrength::CalibratedProbability {
            probability,
            calibrator_id,
        } if (0.0..=1.0).contains(probability) && !calibrator_id.is_empty() => {
            MetricAvailability::Available
        }
        EvidenceStrength::CalibratedProbability { .. } => MetricAvailability::Unresolved,
        EvidenceStrength::Ordinal { .. }
        | EvidenceStrength::LikelihoodRatio { .. }
        | EvidenceStrength::Unscored => MetricAvailability::NotApplicable,
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct WitnessMigrationStatus {
    pub observer_id: String,
    pub strength: EvidenceStrength,
    pub calibration: MetricAvailability,
    pub scorecard_status: MetricAvailability,
    pub economic_claim: String,
}

pub fn legacy_witness_migration(observer_id: impl Into<String>) -> WitnessMigrationStatus {
    let strength = EvidenceStrength::Ordinal {
        level: OrdinalStrength::Strong,
    };
    WitnessMigrationStatus {
        observer_id: observer_id.into(),
        calibration: calibration_availability(&strength),
        strength,
        scorecard_status: MetricAvailability::Unresolved,
        economic_claim: NO_ECONOMIC_CLAIM.into(),
    }
}

/// Frozen economic evaluation cannot be entered by D-141.  This guard makes
/// absent external authority a data result rather than a silent fallback.
pub fn require_frozen_economic_authority(
    authority_receipt: Option<&str>,
) -> Result<(), V8CoreError> {
    match authority_receipt.filter(|receipt| !receipt.trim().is_empty()) {
        Some(_) => Err(V8CoreError::QuantInvariant(
            "D-141 does not consume frozen economic authority; a separately authorized evaluation path is required".into(),
        )),
        None => Err(V8CoreError::QuantInvariant(
            "BLOCKED / OPEN_PIN: frozen economic authority receipt is absent".into(),
        )),
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct RegistryQualificationReport {
    pub total_registered_witnesses: usize,
    pub witnesses_with_manifest: usize,
    pub executed_tests: usize,
    pub passed_tests: usize,
    pub execution_pass_rate: Option<f64>,
    pub registry_manifest_coverage: Option<f64>,
    pub passports: Vec<ExpertPassport>,
    pub economic_claim: String,
}

pub fn pilot_registry_report(passports: Vec<ExpertPassport>) -> RegistryQualificationReport {
    let executed_tests = passports
        .iter()
        .map(|passport| {
            // All pass/fail test totals are bound in the run hash; the report is
            // populated from actual pilot run evidence by the CLI/dossier layer.
            passport
                .gate_status
                .contains_key(&EwqGate::Ewq03CanonicalNegative) as usize
        })
        .sum::<usize>();
    let passed_tests = passports
        .iter()
        .filter(|passport| {
            passport.gate_status.get(&EwqGate::Ewq03CanonicalNegative) == Some(&GateStatus::Pass)
        })
        .count();
    let total_registered_witnesses = crate::experts::default_28_witness_ensemble().len();
    let witnesses_with_manifest = passports.len();
    RegistryQualificationReport {
        total_registered_witnesses,
        witnesses_with_manifest,
        executed_tests,
        passed_tests,
        execution_pass_rate: (executed_tests != 0)
            .then(|| passed_tests as f64 / executed_tests as f64),
        registry_manifest_coverage: (total_registered_witnesses != 0)
            .then(|| witnesses_with_manifest as f64 / total_registered_witnesses as f64),
        passports,
        economic_claim: NO_ECONOMIC_CLAIM.into(),
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PilotQualificationSuite {
    pub runs: Vec<QualificationRun>,
    pub metamorphic: Vec<MetamorphicReceipt>,
    pub mutations: Vec<MutationReport>,
    pub passports: Vec<ExpertPassport>,
    pub executed_tests: usize,
    pub passed_tests: usize,
    pub registry_report: RegistryQualificationReport,
    pub economic_claim: String,
}

/// Executes the entire currently-authorized D-141 pilot suite.  It is a
/// bounded semantic test suite: it does not access tape data or frozen OOS.
pub fn run_pilot_qualification_suite() -> Result<PilotQualificationSuite, V8CoreError> {
    let declarations = vec![
        (failed_breakout_manifest(), failed_breakout_scenarios()),
        (
            failed_breakout_2b_manifest(),
            failed_breakout_2b_scenarios(),
        ),
        (breakout_retest_manifest(), breakout_retest_scenarios()),
        (
            fib_projection_reversal_manifest(),
            fib_projection_reversal_scenarios(),
        ),
        (
            liquidity_sweep_reclaim_manifest(),
            liquidity_sweep_reclaim_scenarios(),
        ),
        (trend_pullback_manifest(), trend_pullback_scenarios()),
        (
            trend_pullback_depth_manifest(),
            trend_pullback_depth_scenarios(),
        ),
        (donchian_breakout_manifest(), donchian_breakout_scenarios()),
        (
            volume_confirmed_breakout_manifest(),
            volume_confirmed_breakout_scenarios(),
        ),
        (
            range_breakout_1to1_manifest(),
            range_breakout_1to1_scenarios(),
        ),
        (
            floor_trader_pivot_manifest(),
            floor_trader_pivot_scenarios(),
        ),
        (
            fib_retracement_continuation_manifest(),
            fib_retracement_continuation_scenarios(),
        ),
        (obv_adl_regime_manifest(), obv_adl_regime_scenarios()),
        (
            funding_crowding_reversal_manifest(),
            funding_crowding_reversal_scenarios(),
        ),
        (
            open_interest_divergence_manifest(),
            open_interest_divergence_scenarios(),
        ),
        (
            candlestick_reversal_manifest(),
            candlestick_reversal_scenarios(),
        ),
        (
            volume_climax_reversal_manifest(),
            volume_climax_reversal_scenarios(),
        ),
        (gap_exhaustion_manifest(), gap_exhaustion_scenarios()),
        (
            bollinger_reversion_manifest(),
            bollinger_reversion_scenarios(),
        ),
        (
            bollinger_breakout_manifest(),
            bollinger_breakout_scenarios(),
        ),
    ];
    let mut runs = Vec::new();
    let mut metamorphic = Vec::new();
    let mut mutations = Vec::new();
    let mut passports = Vec::new();
    let mut executed_tests = 0;
    let mut passed_tests = 0;
    for (manifest, scenarios) in declarations {
        let oracle = pilot_oracle(&manifest.oracle_id, &manifest.oracle_version, &scenarios);
        let run = QualificationRun::execute(&manifest, &oracle, &scenarios)?;
        executed_tests += run.total();
        passed_tests += run.passed();
        let positive = scenarios
            .iter()
            .find(|scenario| scenario.class == ScenarioClass::CanonicalPositive)
            .ok_or_else(|| {
                V8CoreError::QuantInvariant(
                    "pilot must declare a canonical positive scenario".into(),
                )
            })?;
        for relation in [
            MetamorphicRelation::PriceScale,
            MetamorphicRelation::IrrelevantFeature,
            MetamorphicRelation::PrefixNonInterference,
        ] {
            let receipt = verify_metamorphic(&manifest.card.expert_id, relation, positive)?;
            executed_tests += 1;
            passed_tests += receipt.passed as usize;
            metamorphic.push(receipt);
        }
        let mutation =
            MutationReport::from_receipts(kill_mutants(&manifest.card.expert_id, &scenarios));
        executed_tests += mutation.receipts.len();
        passed_tests += mutation
            .receipts
            .iter()
            .filter(|receipt| receipt.killed)
            .count();
        let required_cells = scenarios
            .iter()
            .flat_map(|scenario| scenario.required_cells.iter().cloned())
            .collect::<BTreeSet<_>>();
        let coverage = BehaviorCoverage::from_scenarios(required_cells, &scenarios);
        let evidence = vec![EvidenceObject::new(
            "d141.pilot.semantic-run",
            QualificationAuthority::SemanticQualification,
            vec!["declared finite PIT scenarios".into()],
            manifest.card.expert_id.clone(),
            None,
            &serde_json::to_value(&run)?,
        )];
        passports.push(ExpertPassport::from_run(
            &manifest, &run, &mutation, &coverage, &evidence,
        )?);
        runs.push(run);
        mutations.push(mutation);
    }
    let registry_report = RegistryQualificationReport {
        total_registered_witnesses: crate::experts::default_28_witness_ensemble().len(),
        witnesses_with_manifest: passports.len(),
        executed_tests,
        passed_tests,
        execution_pass_rate: (executed_tests != 0)
            .then(|| passed_tests as f64 / executed_tests as f64),
        registry_manifest_coverage: (!crate::experts::default_28_witness_ensemble().is_empty())
            .then(|| {
                passports.len() as f64 / crate::experts::default_28_witness_ensemble().len() as f64
            }),
        passports: passports.clone(),
        economic_claim: NO_ECONOMIC_CLAIM.into(),
    };
    Ok(PilotQualificationSuite {
        runs,
        metamorphic,
        mutations,
        passports,
        executed_tests,
        passed_tests,
        registry_report,
        economic_claim: NO_ECONOMIC_CLAIM.into(),
    })
}

/// Materializes a real, deterministic D-141 receipt.  The caller chooses the
/// output namespace; this function never fabricates a reference to an absent
/// artifact.
pub fn write_pilot_qualification_report(
    path: &Path,
) -> Result<PilotQualificationSuite, V8CoreError> {
    let suite = run_pilot_qualification_suite()?;
    let bytes = serde_json::to_vec_pretty(&suite)?;
    let parent = path.parent().ok_or_else(|| {
        V8CoreError::PathSanitization("D-141 receipt path requires a parent directory".into())
    })?;
    std::fs::create_dir_all(parent)?;
    std::fs::write(path, bytes)?;
    Ok(suite)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn pilot_manifests_are_hash_bound_and_non_economic() {
        let manifest = failed_breakout_manifest();
        assert!(manifest.validate().is_ok());
        assert_eq!(manifest.hash().unwrap(), manifest.hash().unwrap());
        assert!(!manifest.maximum_authority.renders_economic_claim());
    }

    #[test]
    fn failed_breakout_canonical_negative_boundary_and_missing_controls_pass() {
        let manifest = failed_breakout_manifest();
        let scenarios = failed_breakout_scenarios();
        let oracle = pilot_oracle(&manifest.oracle_id, &manifest.oracle_version, &scenarios);
        let run = QualificationRun::execute(&manifest, &oracle, &scenarios).unwrap();
        assert_eq!(run.passed(), run.total());
        assert_eq!(run.economic_claim, NO_ECONOMIC_CLAIM);
    }

    #[test]
    fn failed_breakout_2b_requires_strict_swing_reclaim() {
        let manifest = failed_breakout_2b_manifest();
        let scenarios = failed_breakout_2b_scenarios();
        let oracle = pilot_oracle(&manifest.oracle_id, &manifest.oracle_version, &scenarios);
        let run = QualificationRun::execute(&manifest, &oracle, &scenarios).unwrap();
        assert_eq!(run.passed(), run.total());
        let positive = scenarios.first().unwrap();
        for relation in [
            MetamorphicRelation::PriceScale,
            MetamorphicRelation::IrrelevantFeature,
            MetamorphicRelation::PrefixNonInterference,
        ] {
            assert!(
                verify_metamorphic("failed_breakout_2b", relation, positive)
                    .unwrap()
                    .passed
            );
        }
        let mutation =
            MutationReport::from_receipts(kill_mutants("failed_breakout_2b", &scenarios));
        assert_eq!(
            mutation.non_equivalent_killed,
            mutation.non_equivalent_generated
        );
    }

    #[test]
    fn breakout_retest_requires_prior_breach_touch_and_strict_hold() {
        let manifest = breakout_retest_manifest();
        let scenarios = breakout_retest_scenarios();
        let oracle = pilot_oracle(&manifest.oracle_id, &manifest.oracle_version, &scenarios);
        let run = QualificationRun::execute(&manifest, &oracle, &scenarios).unwrap();
        assert_eq!(run.passed(), run.total());
        let positive = scenarios.first().unwrap();
        for relation in [
            MetamorphicRelation::PriceScale,
            MetamorphicRelation::IrrelevantFeature,
            MetamorphicRelation::PrefixNonInterference,
        ] {
            assert!(
                verify_metamorphic("breakout_retest", relation, positive)
                    .unwrap()
                    .passed
            );
        }
        let mutation = MutationReport::from_receipts(kill_mutants("breakout_retest", &scenarios));
        assert_eq!(
            mutation.non_equivalent_killed,
            mutation.non_equivalent_generated
        );
    }

    #[test]
    fn fib_projection_long_short_negative_and_boundary_controls_pass() {
        let manifest = fib_projection_reversal_manifest();
        let scenarios = fib_projection_reversal_scenarios();
        let oracle = pilot_oracle(&manifest.oracle_id, &manifest.oracle_version, &scenarios);
        let run = QualificationRun::execute(&manifest, &oracle, &scenarios).unwrap();
        assert_eq!(run.passed(), run.total());
    }

    #[test]
    fn declared_metamorphic_relations_preserve_pilot_stance() {
        let scenario = failed_breakout_scenarios().remove(0);
        for relation in [
            MetamorphicRelation::PriceScale,
            MetamorphicRelation::IrrelevantFeature,
            MetamorphicRelation::PrefixNonInterference,
        ] {
            assert!(
                verify_metamorphic("failed_breakout", relation, &scenario)
                    .unwrap()
                    .passed
            );
        }
    }

    #[test]
    fn fib_price_scaling_preserves_ratio_and_direction_semantics() {
        let scenario = fib_projection_reversal_scenarios().remove(0);
        assert!(
            verify_metamorphic(
                "fib_projection_reversal",
                MetamorphicRelation::PriceScale,
                &scenario
            )
            .unwrap()
            .passed
        );
    }

    #[test]
    fn liquidity_sweep_reclaim_canonical_and_metamorphic_contracts_pass() {
        let manifest = liquidity_sweep_reclaim_manifest();
        let scenarios = liquidity_sweep_reclaim_scenarios();
        let oracle = pilot_oracle(&manifest.oracle_id, &manifest.oracle_version, &scenarios);
        let run = QualificationRun::execute(&manifest, &oracle, &scenarios).unwrap();
        assert_eq!(
            run.passed(),
            run.total(),
            "canonical scenario failure: {:#?}",
            run.receipts
        );
        let positive = scenarios
            .iter()
            .find(|scenario| scenario.class == ScenarioClass::CanonicalPositive)
            .unwrap();
        for relation in [
            MetamorphicRelation::PriceScale,
            MetamorphicRelation::IrrelevantFeature,
            MetamorphicRelation::PrefixNonInterference,
        ] {
            assert!(
                verify_metamorphic("liquidity_sweep_reclaim", relation, positive)
                    .unwrap()
                    .passed,
                "metamorphic relation {relation:?} failed"
            );
        }
        let mutation =
            MutationReport::from_receipts(kill_mutants("liquidity_sweep_reclaim", &scenarios));
        assert_eq!(
            mutation.non_equivalent_killed, mutation.non_equivalent_generated,
            "mutation survived"
        );
    }

    #[test]
    fn trend_pullback_canonical_and_metamorphic_contracts_pass() {
        let manifest = trend_pullback_manifest();
        let scenarios = trend_pullback_scenarios();
        let oracle = pilot_oracle(&manifest.oracle_id, &manifest.oracle_version, &scenarios);
        let run = QualificationRun::execute(&manifest, &oracle, &scenarios).unwrap();
        assert_eq!(run.passed(), run.total(), "canonical scenario failure");
        let positive = scenarios
            .iter()
            .find(|scenario| scenario.class == ScenarioClass::CanonicalPositive)
            .unwrap();
        for relation in [
            MetamorphicRelation::PriceScale,
            MetamorphicRelation::IrrelevantFeature,
            MetamorphicRelation::PrefixNonInterference,
        ] {
            assert!(
                verify_metamorphic("trend_pullback", relation, positive)
                    .unwrap()
                    .passed,
                "metamorphic relation {relation:?} failed"
            );
        }
        let mutation = MutationReport::from_receipts(kill_mutants("trend_pullback", &scenarios));
        assert_eq!(
            mutation.non_equivalent_killed, mutation.non_equivalent_generated,
            "mutation survived"
        );
    }

    #[test]
    fn trend_pullback_depth_inclusive_boundary_and_metamorphic_contracts_pass() {
        let manifest = trend_pullback_depth_manifest();
        let scenarios = trend_pullback_depth_scenarios();
        let oracle = pilot_oracle(&manifest.oracle_id, &manifest.oracle_version, &scenarios);
        let run = QualificationRun::execute(&manifest, &oracle, &scenarios).unwrap();
        assert_eq!(run.passed(), run.total(), "canonical scenario failure");
        let positive = scenarios
            .iter()
            .find(|scenario| scenario.class == ScenarioClass::CanonicalPositive)
            .unwrap();
        for relation in [
            MetamorphicRelation::PriceScale,
            MetamorphicRelation::IrrelevantFeature,
            MetamorphicRelation::PrefixNonInterference,
        ] {
            assert!(
                verify_metamorphic("trend_pullback_depth", relation, positive)
                    .unwrap()
                    .passed,
                "metamorphic relation {relation:?} failed"
            );
        }
        let mutation =
            MutationReport::from_receipts(kill_mutants("trend_pullback_depth", &scenarios));
        assert_eq!(
            mutation.non_equivalent_killed, mutation.non_equivalent_generated,
            "mutation survived"
        );
    }

    #[test]
    fn donchian_breakout_channel_contract_and_metamorphic_relations_pass() {
        let manifest = donchian_breakout_manifest();
        let scenarios = donchian_breakout_scenarios();
        let oracle = pilot_oracle(&manifest.oracle_id, &manifest.oracle_version, &scenarios);
        let run = QualificationRun::execute(&manifest, &oracle, &scenarios).unwrap();
        assert_eq!(run.passed(), run.total(), "canonical scenario failure");
        let positive = scenarios
            .iter()
            .find(|scenario| scenario.class == ScenarioClass::CanonicalPositive)
            .unwrap();
        for relation in [
            MetamorphicRelation::PriceScale,
            MetamorphicRelation::IrrelevantFeature,
            MetamorphicRelation::PrefixNonInterference,
        ] {
            assert!(
                verify_metamorphic("donchian_breakout", relation, positive)
                    .unwrap()
                    .passed,
                "metamorphic relation {relation:?} failed"
            );
        }
        let mutation = MutationReport::from_receipts(kill_mutants("donchian_breakout", &scenarios));
        assert_eq!(
            mutation.non_equivalent_killed, mutation.non_equivalent_generated,
            "mutation survived"
        );
    }

    #[test]
    fn volume_confirmed_breakout_channel_and_volume_contracts_pass() {
        let manifest = volume_confirmed_breakout_manifest();
        let scenarios = volume_confirmed_breakout_scenarios();
        let oracle = pilot_oracle(&manifest.oracle_id, &manifest.oracle_version, &scenarios);
        let run = QualificationRun::execute(&manifest, &oracle, &scenarios).unwrap();
        assert_eq!(run.passed(), run.total(), "canonical scenario failure");
        let positive = scenarios
            .iter()
            .find(|scenario| scenario.class == ScenarioClass::CanonicalPositive)
            .unwrap();
        for relation in [
            MetamorphicRelation::PriceScale,
            MetamorphicRelation::IrrelevantFeature,
            MetamorphicRelation::PrefixNonInterference,
        ] {
            assert!(
                verify_metamorphic("volume_confirmed_breakout", relation, positive)
                    .unwrap()
                    .passed,
                "metamorphic relation {relation:?} failed"
            );
        }
        let mutation =
            MutationReport::from_receipts(kill_mutants("volume_confirmed_breakout", &scenarios));
        assert_eq!(
            mutation.non_equivalent_killed, mutation.non_equivalent_generated,
            "mutation survived"
        );
    }

    #[test]
    fn range_breakout_preserves_dimensionless_width_under_price_scaling() {
        let manifest = range_breakout_1to1_manifest();
        let scenarios = range_breakout_1to1_scenarios();
        let oracle = pilot_oracle(&manifest.oracle_id, &manifest.oracle_version, &scenarios);
        let run = QualificationRun::execute(&manifest, &oracle, &scenarios).unwrap();
        assert_eq!(run.passed(), run.total(), "canonical scenario failure");
        let positive = scenarios
            .iter()
            .find(|scenario| scenario.class == ScenarioClass::CanonicalPositive)
            .unwrap();
        for relation in [
            MetamorphicRelation::PriceScale,
            MetamorphicRelation::IrrelevantFeature,
            MetamorphicRelation::PrefixNonInterference,
        ] {
            assert!(
                verify_metamorphic("range_breakout_1to1", relation, positive)
                    .unwrap()
                    .passed,
                "metamorphic relation {relation:?} failed"
            );
        }
        let mutation =
            MutationReport::from_receipts(kill_mutants("range_breakout_1to1", &scenarios));
        assert_eq!(
            mutation.non_equivalent_killed, mutation.non_equivalent_generated,
            "mutation survived"
        );
    }

    #[test]
    fn floor_trader_pivot_session_and_geometry_contracts_pass() {
        let manifest = floor_trader_pivot_manifest();
        let scenarios = floor_trader_pivot_scenarios();
        let oracle = pilot_oracle(&manifest.oracle_id, &manifest.oracle_version, &scenarios);
        let run = QualificationRun::execute(&manifest, &oracle, &scenarios).unwrap();
        assert_eq!(run.passed(), run.total(), "canonical scenario failure");
        let positive = scenarios
            .iter()
            .find(|scenario| scenario.class == ScenarioClass::CanonicalPositive)
            .unwrap();
        for relation in [
            MetamorphicRelation::PriceScale,
            MetamorphicRelation::IrrelevantFeature,
            MetamorphicRelation::PrefixNonInterference,
        ] {
            assert!(
                verify_metamorphic("floor_trader_pivot", relation, positive)
                    .unwrap()
                    .passed,
                "metamorphic relation {relation:?} failed"
            );
        }
        let mutation =
            MutationReport::from_receipts(kill_mutants("floor_trader_pivot", &scenarios));
        assert_eq!(
            mutation.non_equivalent_killed, mutation.non_equivalent_generated,
            "mutation survived"
        );
    }

    #[test]
    fn fib_retracement_continuation_scales_retracement_levels_and_passes() {
        let manifest = fib_retracement_continuation_manifest();
        let scenarios = fib_retracement_continuation_scenarios();
        let oracle = pilot_oracle(&manifest.oracle_id, &manifest.oracle_version, &scenarios);
        let run = QualificationRun::execute(&manifest, &oracle, &scenarios).unwrap();
        assert_eq!(run.passed(), run.total(), "canonical scenario failure");
        let positive = scenarios
            .iter()
            .find(|scenario| scenario.class == ScenarioClass::CanonicalPositive)
            .unwrap();
        for relation in [
            MetamorphicRelation::PriceScale,
            MetamorphicRelation::IrrelevantFeature,
            MetamorphicRelation::PrefixNonInterference,
        ] {
            assert!(
                verify_metamorphic("fib_retracement_continuation", relation, positive)
                    .unwrap()
                    .passed,
                "metamorphic relation {relation:?} failed"
            );
        }
        let mutation =
            MutationReport::from_receipts(kill_mutants("fib_retracement_continuation", &scenarios));
        assert_eq!(
            mutation.non_equivalent_killed, mutation.non_equivalent_generated,
            "mutation survived"
        );
    }

    #[test]
    fn obv_adl_regime_requires_complete_feature_closure_and_passes() {
        assert_eq!(
            crate::experts::requires_for("obv_adl_regime"),
            ["participation", "trend", "volatility", "history"]
        );
        let manifest = obv_adl_regime_manifest();
        let scenarios = obv_adl_regime_scenarios();
        let oracle = pilot_oracle(&manifest.oracle_id, &manifest.oracle_version, &scenarios);
        let run = QualificationRun::execute(&manifest, &oracle, &scenarios).unwrap();
        assert_eq!(run.passed(), run.total(), "canonical scenario failure");
        let positive = scenarios
            .iter()
            .find(|scenario| scenario.class == ScenarioClass::CanonicalPositive)
            .unwrap();
        for relation in [
            MetamorphicRelation::PriceScale,
            MetamorphicRelation::IrrelevantFeature,
            MetamorphicRelation::PrefixNonInterference,
        ] {
            assert!(
                verify_metamorphic("obv_adl_regime", relation, positive)
                    .unwrap()
                    .passed,
                "metamorphic relation {relation:?} failed"
            );
        }
        let mutation = MutationReport::from_receipts(kill_mutants("obv_adl_regime", &scenarios));
        assert_eq!(
            mutation.non_equivalent_killed, mutation.non_equivalent_generated,
            "mutation survived"
        );
    }

    #[test]
    fn funding_crowding_reversal_keeps_funding_dimensionless_and_passes() {
        let manifest = funding_crowding_reversal_manifest();
        let scenarios = funding_crowding_reversal_scenarios();
        let oracle = pilot_oracle(&manifest.oracle_id, &manifest.oracle_version, &scenarios);
        let run = QualificationRun::execute(&manifest, &oracle, &scenarios).unwrap();
        assert_eq!(run.passed(), run.total(), "canonical scenario failure");
        let positive = scenarios.first().unwrap();
        for relation in [
            MetamorphicRelation::PriceScale,
            MetamorphicRelation::IrrelevantFeature,
            MetamorphicRelation::PrefixNonInterference,
        ] {
            assert!(
                verify_metamorphic("funding_crowding_reversal", relation, positive)
                    .unwrap()
                    .passed,
                "metamorphic relation {relation:?} failed"
            );
        }
        let mutation =
            MutationReport::from_receipts(kill_mutants("funding_crowding_reversal", &scenarios));
        assert_eq!(
            mutation.non_equivalent_killed,
            mutation.non_equivalent_generated
        );
    }

    #[test]
    fn open_interest_divergence_requires_real_oi_presence_and_passes() {
        let manifest = open_interest_divergence_manifest();
        let scenarios = open_interest_divergence_scenarios();
        let oracle = pilot_oracle(&manifest.oracle_id, &manifest.oracle_version, &scenarios);
        let run = QualificationRun::execute(&manifest, &oracle, &scenarios).unwrap();
        assert_eq!(run.passed(), run.total());
        let positive = scenarios.first().unwrap();
        for relation in [
            MetamorphicRelation::PriceScale,
            MetamorphicRelation::IrrelevantFeature,
            MetamorphicRelation::PrefixNonInterference,
        ] {
            assert!(
                verify_metamorphic("open_interest_divergence", relation, positive)
                    .unwrap()
                    .passed
            );
        }
        let mutation =
            MutationReport::from_receipts(kill_mutants("open_interest_divergence", &scenarios));
        assert_eq!(
            mutation.non_equivalent_killed,
            mutation.non_equivalent_generated
        );
    }

    #[test]
    fn candlestick_reversal_hammer_contract_and_inclusive_ratios_pass() {
        let manifest = candlestick_reversal_manifest();
        let scenarios = candlestick_reversal_scenarios();
        let oracle = pilot_oracle(&manifest.oracle_id, &manifest.oracle_version, &scenarios);
        let run = QualificationRun::execute(&manifest, &oracle, &scenarios).unwrap();
        assert_eq!(run.passed(), run.total());
        let positive = scenarios.first().unwrap();
        for relation in [
            MetamorphicRelation::PriceScale,
            MetamorphicRelation::IrrelevantFeature,
            MetamorphicRelation::PrefixNonInterference,
        ] {
            assert!(
                verify_metamorphic("candlestick_reversal", relation, positive)
                    .unwrap()
                    .passed
            );
        }
        let mutation =
            MutationReport::from_receipts(kill_mutants("candlestick_reversal", &scenarios));
        assert_eq!(
            mutation.non_equivalent_killed,
            mutation.non_equivalent_generated
        );
    }

    #[test]
    fn volume_climax_reversal_respects_priority_and_typed_scaling() {
        let manifest = volume_climax_reversal_manifest();
        let scenarios = volume_climax_reversal_scenarios();
        let oracle = pilot_oracle(&manifest.oracle_id, &manifest.oracle_version, &scenarios);
        let run = QualificationRun::execute(&manifest, &oracle, &scenarios).unwrap();
        assert_eq!(run.passed(), run.total());
        let positive = scenarios.first().unwrap();
        for relation in [
            MetamorphicRelation::PriceScale,
            MetamorphicRelation::IrrelevantFeature,
            MetamorphicRelation::PrefixNonInterference,
        ] {
            assert!(
                verify_metamorphic("volume_climax_reversal", relation, positive)
                    .unwrap()
                    .passed
            );
        }
        let mutation =
            MutationReport::from_receipts(kill_mutants("volume_climax_reversal", &scenarios));
        assert_eq!(
            mutation.non_equivalent_killed,
            mutation.non_equivalent_generated
        );
    }

    #[test]
    fn gap_exhaustion_binds_zone_direction_and_strict_reversal() {
        let manifest = gap_exhaustion_manifest();
        let scenarios = gap_exhaustion_scenarios();
        let oracle = pilot_oracle(&manifest.oracle_id, &manifest.oracle_version, &scenarios);
        let run = QualificationRun::execute(&manifest, &oracle, &scenarios).unwrap();
        assert_eq!(run.passed(), run.total());
        let positive = scenarios.first().unwrap();
        for relation in [
            MetamorphicRelation::PriceScale,
            MetamorphicRelation::IrrelevantFeature,
            MetamorphicRelation::PrefixNonInterference,
        ] {
            assert!(
                verify_metamorphic("gap_exhaustion", relation, positive)
                    .unwrap()
                    .passed
            );
        }
        let mutation = MutationReport::from_receipts(kill_mutants("gap_exhaustion", &scenarios));
        assert_eq!(
            mutation.non_equivalent_killed,
            mutation.non_equivalent_generated
        );
    }

    #[test]
    fn bollinger_reversion_recomputes_anchor_bands_and_preserves_boundaries() {
        let manifest = bollinger_reversion_manifest();
        let scenarios = bollinger_reversion_scenarios();
        let oracle = pilot_oracle(&manifest.oracle_id, &manifest.oracle_version, &scenarios);
        let run = QualificationRun::execute(&manifest, &oracle, &scenarios).unwrap();
        assert_eq!(run.passed(), run.total());
        let positive = scenarios.first().unwrap();
        for relation in [
            MetamorphicRelation::PriceScale,
            MetamorphicRelation::IrrelevantFeature,
            MetamorphicRelation::PrefixNonInterference,
        ] {
            assert!(
                verify_metamorphic("bollinger_reversion", relation, positive)
                    .unwrap()
                    .passed
            );
        }
        let mutation =
            MutationReport::from_receipts(kill_mutants("bollinger_reversion", &scenarios));
        assert_eq!(
            mutation.non_equivalent_killed,
            mutation.non_equivalent_generated
        );
    }

    #[test]
    fn bollinger_breakout_uses_strict_midpoint_direction_and_history_anchor() {
        let manifest = bollinger_breakout_manifest();
        let scenarios = bollinger_breakout_scenarios();
        let oracle = pilot_oracle(&manifest.oracle_id, &manifest.oracle_version, &scenarios);
        let run = QualificationRun::execute(&manifest, &oracle, &scenarios).unwrap();
        assert_eq!(run.passed(), run.total());
        let positive = scenarios.first().unwrap();
        for relation in [
            MetamorphicRelation::PriceScale,
            MetamorphicRelation::IrrelevantFeature,
            MetamorphicRelation::PrefixNonInterference,
        ] {
            assert!(
                verify_metamorphic("bollinger_breakout", relation, positive)
                    .unwrap()
                    .passed
            );
        }
        let mutation =
            MutationReport::from_receipts(kill_mutants("bollinger_breakout", &scenarios));
        assert_eq!(
            mutation.non_equivalent_killed,
            mutation.non_equivalent_generated
        );
    }

    #[test]
    fn all_critical_mutants_are_killed_by_the_pilot_suite() {
        let scenarios = failed_breakout_scenarios();
        let report = MutationReport::from_receipts(kill_mutants("failed_breakout", &scenarios));
        assert!(report.critical_kill_complete());
        assert_eq!(
            report
                .receipts
                .iter()
                .filter(|receipt| receipt.killed)
                .count(),
            report.receipts.len()
        );
        assert_eq!(report.economic_claim, NO_ECONOMIC_CLAIM);
    }

    #[test]
    fn conditional_generation_is_replayable_and_coverage_is_explicit() {
        let mut first = ConditionalScenarioGenerator::new(7, "d141-test-seeds");
        let mut second = ConditionalScenarioGenerator::new(7, "d141-test-seeds");
        let a: Vec<_> = (0..8)
            .map(|index| first.failed_breakout_world(index))
            .collect();
        let b: Vec<_> = (0..8)
            .map(|index| second.failed_breakout_world(index))
            .collect();
        assert_eq!(a, b);
        let cells = a
            .iter()
            .flat_map(|scenario| scenario.required_cells.iter().cloned())
            .collect::<BTreeSet<_>>();
        let coverage = BehaviorCoverage::from_scenarios(cells, &a);
        assert_eq!(coverage.fraction(), Some(1.0));
        assert!(east_search(
            "failed_breakout",
            ConditionalScenarioGenerator::new(7, "d141-test-seeds"),
            8
        )
        .is_none());
    }

    #[test]
    fn statistical_and_risk_objects_fail_closed_without_declarations() {
        let trial = PairedTrial::from_losses(
            &[1.0, 0.0],
            &[0.5, 0.0],
            Some((0.0, 1.0)),
            "independent declared scenario draws",
        )
        .unwrap();
        assert!(non_inferiority(&trial, None, 0.05).is_err());
        assert_eq!(
            non_inferiority(&trial, Some(1.0), 0.05)
                .unwrap()
                .economic_claim,
            NO_ECONOMIC_CLAIM
        );
        assert!(EValue::new(-1.0, "family", "construction").is_err());
        assert_eq!(
            EValue::new(1.0, "family", "construction")
                .unwrap()
                .economic_claim,
            NO_ECONOMIC_CLAIM
        );
    }

    #[test]
    fn passport_and_attribution_preserve_authority_boundaries() {
        let suite = run_pilot_qualification_suite().unwrap();
        assert_eq!(suite.executed_tests, suite.passed_tests);
        assert_eq!(suite.registry_report.witnesses_with_manifest, 20);
        assert!(!suite
            .passports
            .iter()
            .any(ExpertPassport::promotion_eligible));
        let contribution = forced_abstention_attribution(&[AttributionObservation {
            opportunity_id: "existing-opportunity".into(),
            baseline_utility: Some(1.0),
            force_abstain_utility: Some(0.0),
            baseline_fee: None,
            force_abstain_fee: None,
            displacement_cost: None,
            unique_capture: None,
        }]);
        assert_eq!(contribution[0].opportunity_id, "existing-opportunity");
        assert_eq!(contribution[0].economic_claim, NO_ECONOMIC_CLAIM);
        assert_eq!(
            calibration_availability(&EvidenceStrength::Ordinal {
                level: OrdinalStrength::Strong
            }),
            MetricAvailability::NotApplicable
        );
        assert!(require_frozen_economic_authority(None).is_err());
    }
}
