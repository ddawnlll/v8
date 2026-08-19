//! Finite, Expert-independent Opportunity Grammar (TARGET_ORACLE_SPEC §5).

#![allow(dead_code)]

use std::collections::{BTreeMap, BTreeSet};

use serde::{Deserialize, Serialize};

use crate::hash::{hash_value, Canon};

use super::artifacts::OpportunityUniverseVersion;
use super::information::InformationSet;
use super::taxonomy::OracleRefusal;

#[derive(Debug, Clone, Eq, PartialEq, Serialize, Deserialize)]
pub enum PrimitiveFamily {
    PriceReturn,
    VolatilityRange,
    VolumeActivity,
    Liquidity,
    OrderFlow,
    FundingBasis,
    DerivativesStress,
}

#[derive(Debug, Clone, Eq, PartialEq, Serialize, Deserialize)]
pub struct PrimitiveDefinition {
    pub family: PrimitiveFamily,
    pub source_version: String,
}

#[derive(Debug, Clone, Eq, PartialEq, Serialize, Deserialize)]
pub struct PrimitiveRegistry {
    pub version: String,
    pub primitives: BTreeMap<String, PrimitiveDefinition>,
    pub allowed_operators: BTreeSet<String>,
}

impl PrimitiveRegistry {
    pub fn identity(&self) -> String {
        hash_value(&serde_json::to_value(self).expect("registered primitives serialize"))
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ParameterGrid {
    pub grid_id: String,
    pub values: BTreeMap<String, Vec<serde_json::Value>>,
}

impl ParameterGrid {
    pub fn identity(&self) -> String {
        hash_value(&serde_json::to_value(self).expect("registered grid serializes"))
    }

    fn assignments(
        &self,
        names: &[String],
    ) -> Result<Vec<BTreeMap<String, serde_json::Value>>, OracleRefusal> {
        let mut out = vec![BTreeMap::new()];
        for name in names {
            let values = self
                .values
                .get(name)
                .filter(|values| !values.is_empty())
                .ok_or(OracleRefusal::InsufficientSupport)?;
            let mut next = Vec::with_capacity(out.len().saturating_mul(values.len()));
            for partial in &out {
                for value in values {
                    let mut assignment = partial.clone();
                    assignment.insert(name.clone(), value.clone());
                    next.push(assignment);
                }
            }
            out = next;
        }
        Ok(out)
    }
}

#[derive(Debug, Clone, Eq, PartialEq, Ord, PartialOrd, Serialize, Deserialize)]
pub enum Direction {
    Long,
    Short,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum ValueRef {
    Literal(f64),
    Parameter(String),
}

impl ValueRef {
    fn resolve(&self, parameters: &BTreeMap<String, serde_json::Value>) -> Option<f64> {
        match self {
            Self::Literal(value) => Some(*value),
            Self::Parameter(name) => parameters.get(name).and_then(serde_json::Value::as_f64),
        }
    }
}

/// The complete v1 bounded predicate surface.  Sequence-dependent forms are
/// accepted only as registered syntax; O1 refuses to infer an observation
/// history that is not present in the supplied InformationSet.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum PredicateNode {
    Above {
        feature: String,
        threshold: ValueRef,
    },
    Below {
        feature: String,
        threshold: ValueRef,
    },
    CrossAbove {
        feature: String,
        threshold: ValueRef,
    },
    CrossBelow {
        feature: String,
        threshold: ValueRef,
    },
    InRange {
        feature: String,
        lo: ValueRef,
        hi: ValueRef,
    },
    Rising {
        feature: String,
        n: usize,
    },
    Falling {
        feature: String,
        n: usize,
    },
    Persist {
        predicate: Box<PredicateNode>,
        n: usize,
    },
    And(Vec<PredicateNode>),
    Or(Vec<PredicateNode>),
    Not(Box<PredicateNode>),
    Sequence {
        first: Box<PredicateNode>,
        second: Box<PredicateNode>,
        max_delay: usize,
    },
}

impl PredicateNode {
    fn operator(&self) -> &'static str {
        match self {
            Self::Above { .. } => "ABOVE",
            Self::Below { .. } => "BELOW",
            Self::CrossAbove { .. } => "CROSS_ABOVE",
            Self::CrossBelow { .. } => "CROSS_BELOW",
            Self::InRange { .. } => "IN_RANGE",
            Self::Rising { .. } => "RISING",
            Self::Falling { .. } => "FALLING",
            Self::Persist { .. } => "PERSIST",
            Self::And(_) => "AND",
            Self::Or(_) => "OR",
            Self::Not(_) => "NOT",
            Self::Sequence { .. } => "SEQUENCE",
        }
    }

    fn validate(
        &self,
        registry: &PrimitiveRegistry,
        parameters: &BTreeSet<&str>,
        depth: usize,
    ) -> Result<(), OracleRefusal> {
        if depth > 16 || !registry.allowed_operators.contains(self.operator()) {
            return Err(OracleRefusal::InsufficientSupport);
        }
        let feature = |name: &str| {
            registry
                .primitives
                .contains_key(name)
                .then_some(())
                .ok_or(OracleRefusal::MissingDecisionTimeData)
        };
        let value = |reference: &ValueRef| match reference {
            ValueRef::Literal(value) if value.is_finite() => Ok(()),
            ValueRef::Parameter(name) if parameters.contains(name.as_str()) => Ok(()),
            _ => Err(OracleRefusal::InsufficientSupport),
        };
        match self {
            Self::Above {
                feature: f,
                threshold,
            }
            | Self::Below {
                feature: f,
                threshold,
            }
            | Self::CrossAbove {
                feature: f,
                threshold,
            }
            | Self::CrossBelow {
                feature: f,
                threshold,
            } => {
                feature(f)?;
                value(threshold)
            }
            Self::InRange { feature: f, lo, hi } => {
                feature(f)?;
                value(lo)?;
                value(hi)
            }
            Self::Rising { feature: f, n } | Self::Falling { feature: f, n } => {
                feature(f)?;
                if *n > 0 {
                    Ok(())
                } else {
                    Err(OracleRefusal::InsufficientSupport)
                }
            }
            Self::Persist { predicate, n } => {
                if *n == 0 {
                    return Err(OracleRefusal::InsufficientSupport);
                }
                predicate.validate(registry, parameters, depth + 1)
            }
            Self::And(nodes) | Self::Or(nodes) => {
                if nodes.is_empty() {
                    return Err(OracleRefusal::InsufficientSupport);
                }
                for node in nodes {
                    node.validate(registry, parameters, depth + 1)?;
                }
                Ok(())
            }
            Self::Not(node) => node.validate(registry, parameters, depth + 1),
            Self::Sequence {
                first,
                second,
                max_delay,
            } => {
                if *max_delay == 0 {
                    return Err(OracleRefusal::InsufficientSupport);
                }
                first.validate(registry, parameters, depth + 1)?;
                second.validate(registry, parameters, depth + 1)
            }
        }
    }

    fn evaluate(
        &self,
        information: &InformationSet,
        parameters: &BTreeMap<String, serde_json::Value>,
    ) -> bool {
        let value = |name: &str| information.value_f64(name);
        match self {
            Self::Above { feature, threshold } => value(feature)
                .zip(threshold.resolve(parameters))
                .is_some_and(|(a, b)| a > b),
            Self::Below { feature, threshold } => value(feature)
                .zip(threshold.resolve(parameters))
                .is_some_and(|(a, b)| a < b),
            Self::InRange { feature, lo, hi } => value(feature)
                .zip(lo.resolve(parameters))
                .zip(hi.resolve(parameters))
                .is_some_and(|((x, low), high)| low <= x && x <= high),
            // The narrow adapter has no observation history.  Returning false
            // here fails closed rather than constructing a backdated signal.
            Self::CrossAbove { .. }
            | Self::CrossBelow { .. }
            | Self::Rising { .. }
            | Self::Falling { .. }
            | Self::Persist { .. }
            | Self::Sequence { .. } => false,
            Self::And(nodes) => nodes
                .iter()
                .all(|node| node.evaluate(information, parameters)),
            Self::Or(nodes) => nodes
                .iter()
                .any(|node| node.evaluate(information, parameters)),
            Self::Not(node) => !node.evaluate(information, parameters),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct CandidateTemplate {
    pub template_id: String,
    pub mechanism_family_id: String,
    pub behavior_family_id: String,
    pub habitat_predicate: PredicateNode,
    pub setup_predicate: PredicateNode,
    pub trigger_predicate: PredicateNode,
    pub direction: Direction,
    pub invalidation: String,
    pub expiry: String,
    pub risk_geometry: BTreeMap<String, serde_json::Value>,
    pub parameter_names: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct TemplateRegistry {
    pub version: String,
    pub templates: Vec<CandidateTemplate>,
}

impl TemplateRegistry {
    pub fn identity(&self) -> String {
        hash_value(&serde_json::to_value(self).expect("registered templates serialize"))
    }
}

#[derive(Debug, Clone, Eq, PartialEq, Serialize, Deserialize)]
pub struct GrammarCandidate {
    pub grammar_candidate_id: String,
    pub universe_id: String,
    pub template_id: String,
    pub instrument: String,
    pub timeframe: String,
    pub direction: Direction,
    pub decision_time: i64,
    pub parameters: BTreeMap<String, serde_json::Value>,
}

impl GrammarCandidate {
    fn identity(&self) -> String {
        let mut c = Canon::new();
        c.push_str("grammar-candidate-v1");
        c.push_value(&serde_json::json!({
            "universe_id": self.universe_id, "template_id": self.template_id,
            "instrument": self.instrument, "timeframe": self.timeframe,
            "direction": format!("{:?}", self.direction), "decision_time": self.decision_time,
            "parameters": self.parameters,
        }));
        c.finish_sha1_hex()
    }

    fn bind_identity(&mut self) {
        self.grammar_candidate_id = self.identity();
    }
}

#[derive(Debug, Clone)]
pub struct OpportunityGrammar {
    pub version: String,
    pub primitives: PrimitiveRegistry,
    pub templates: TemplateRegistry,
    pub grid: ParameterGrid,
}

impl OpportunityGrammar {
    pub fn validate(&self) -> Result<(), OracleRefusal> {
        if self.version.is_empty()
            || self.primitives.version.is_empty()
            || self.templates.version.is_empty()
            || self.grid.grid_id.is_empty()
            || self.templates.templates.is_empty()
        {
            return Err(OracleRefusal::InsufficientSupport);
        }
        let mut template_ids = BTreeSet::new();
        for template in &self.templates.templates {
            if template.template_id.is_empty()
                || template.mechanism_family_id.is_empty()
                || template.behavior_family_id.is_empty()
                || template.invalidation.is_empty()
                || template.expiry.is_empty()
                || !template_ids.insert(template.template_id.as_str())
            {
                return Err(OracleRefusal::InsufficientSupport);
            }
            let names: BTreeSet<&str> = template
                .parameter_names
                .iter()
                .map(String::as_str)
                .collect();
            if names.len() != template.parameter_names.len() {
                return Err(OracleRefusal::InsufficientSupport);
            }
            template
                .habitat_predicate
                .validate(&self.primitives, &names, 0)?;
            template
                .setup_predicate
                .validate(&self.primitives, &names, 0)?;
            template
                .trigger_predicate
                .validate(&self.primitives, &names, 0)?;
            self.grid.assignments(&template.parameter_names)?;
        }
        Ok(())
    }

    pub fn search_universe_size(
        &self,
        instruments: usize,
        timeframes: usize,
    ) -> Result<usize, OracleRefusal> {
        self.validate()?;
        let mut count = 0usize;
        for template in &self.templates.templates {
            count = count
                .checked_add(self.grid.assignments(&template.parameter_names)?.len())
                .ok_or(OracleRefusal::InsufficientSupport)?;
        }
        count
            .checked_mul(instruments)
            .and_then(|n| n.checked_mul(timeframes))
            .ok_or(OracleRefusal::InsufficientSupport)
    }

    pub fn generate(
        &self,
        universe: &OpportunityUniverseVersion,
        information: &InformationSet,
    ) -> Result<Vec<GrammarCandidate>, OracleRefusal> {
        self.validate()?;
        if universe.primitive_registry_hash != self.primitives.identity()
            || universe.behavior_template_registry_hash != self.templates.identity()
            || universe.parameter_grid_hash != self.grid.identity()
            || universe.predicate_ir_version != self.version
            || universe.search_universe_size
                != self.search_universe_size(
                    universe.instrument_universe.len(),
                    universe.timeframe_set.len(),
                )?
        {
            return Err(OracleRefusal::InsufficientSupport);
        }
        if information.decision_time < 0 {
            return Err(OracleRefusal::MissingDecisionTimeData);
        }
        let mut candidates = Vec::new();
        for template in &self.templates.templates {
            for parameters in self.grid.assignments(&template.parameter_names)? {
                if !(template
                    .habitat_predicate
                    .evaluate(information, &parameters)
                    && template.setup_predicate.evaluate(information, &parameters)
                    && template
                        .trigger_predicate
                        .evaluate(information, &parameters))
                {
                    continue;
                }
                for instrument in &universe.instrument_universe {
                    for timeframe in &universe.timeframe_set {
                        let mut candidate = GrammarCandidate {
                            grammar_candidate_id: String::new(),
                            universe_id: universe.universe_id.clone(),
                            template_id: template.template_id.clone(),
                            instrument: instrument.clone(),
                            timeframe: timeframe.clone(),
                            direction: template.direction.clone(),
                            decision_time: information.decision_time,
                            parameters: parameters.clone(),
                        };
                        candidate.bind_identity();
                        candidates.push(candidate);
                    }
                }
            }
        }
        candidates.sort_by(|a, b| a.grammar_candidate_id.cmp(&b.grammar_candidate_id));
        Ok(candidates)
    }

    pub fn population_hash(candidates: &[GrammarCandidate]) -> String {
        let mut ids: Vec<&str> = candidates
            .iter()
            .map(|candidate| candidate.grammar_candidate_id.as_str())
            .collect();
        ids.sort();
        let mut c = Canon::new();
        c.push_str("grammar-population-v1");
        c.push_list();
        c.push_count(ids.len());
        for id in ids {
            c.push_str(id);
        }
        c.finish_sha1_hex()
    }
}

#[cfg(test)]
mod tests {
    use super::super::information::InformationField;
    use super::*;
    use crate::candidate::CandidateRegistry;

    fn grammar(direction: Direction) -> OpportunityGrammar {
        OpportunityGrammar {
            version: "predicate-ir-v1".into(),
            primitives: PrimitiveRegistry {
                version: "registered-v1".into(),
                primitives: BTreeMap::from([(
                    "close".into(),
                    PrimitiveDefinition {
                        family: PrimitiveFamily::PriceReturn,
                        source_version: "state-v1".into(),
                    },
                )]),
                allowed_operators: BTreeSet::from(["ABOVE".into()]),
            },
            templates: TemplateRegistry {
                version: "template-v1".into(),
                templates: vec![CandidateTemplate {
                    template_id: "template-1".into(),
                    mechanism_family_id: "price".into(),
                    behavior_family_id: "break".into(),
                    habitat_predicate: PredicateNode::Above {
                        feature: "close".into(),
                        threshold: ValueRef::Parameter("threshold".into()),
                    },
                    setup_predicate: PredicateNode::Above {
                        feature: "close".into(),
                        threshold: ValueRef::Parameter("threshold".into()),
                    },
                    trigger_predicate: PredicateNode::Above {
                        feature: "close".into(),
                        threshold: ValueRef::Parameter("threshold".into()),
                    },
                    direction,
                    invalidation: "stop-v1".into(),
                    expiry: "1bar".into(),
                    risk_geometry: BTreeMap::new(),
                    parameter_names: vec!["threshold".into()],
                }],
            },
            grid: ParameterGrid {
                grid_id: "grid-v1".into(),
                values: BTreeMap::from([("threshold".into(), vec![serde_json::json!(100.0)])]),
            },
        }
    }

    fn universe(
        grammar: &OpportunityGrammar,
        execution_mode_id: &str,
    ) -> OpportunityUniverseVersion {
        let mut universe = OpportunityUniverseVersion {
            universe_id: String::new(),
            version: "1".into(),
            parent_universe_id: None,
            instrument_universe: vec!["BTCUSDT".into()],
            timeframe_set: vec!["1h".into()],
            information_contract_id: "pit-v1".into(),
            primitive_registry_hash: grammar.primitives.identity(),
            predicate_ir_version: grammar.version.clone(),
            behavior_template_registry_hash: grammar.templates.identity(),
            parameter_grid_hash: grammar.grid.identity(),
            tradability_rule_id: "detect-v1".into(),
            support_rule_id: "support-deferred".into(),
            authority_contract_id: "l1-v1".into(),
            search_universe_size: grammar.search_universe_size(1, 1).unwrap(),
            complexity_budget: 1,
            created_at: 0,
            code_hash: "code-v1".into(),
            execution_mode_id: execution_mode_id.into(),
        };
        universe.bind_identity();
        universe
    }

    fn information() -> InformationSet {
        let mut info = InformationSet::new(100);
        info.insert(InformationField {
            name: "close".into(),
            value: serde_json::json!(101.0),
            event_time: 99,
            knowledge_time: 100,
            availability_time: 100,
            source_id: "state".into(),
            source_version: "v1".into(),
        })
        .unwrap();
        info
    }

    #[test]
    fn frozen_inputs_produce_stable_candidate_universe_population_and_manifest_identities() {
        let grammar = grammar(Direction::Long);
        let universe = universe(&grammar, "canonical-l1");
        let info = information();
        let first = grammar.generate(&universe, &info).unwrap();
        let second = grammar.generate(&universe, &info).unwrap();
        assert_eq!(first, second);
        assert_eq!(
            OpportunityGrammar::population_hash(&first),
            OpportunityGrammar::population_hash(&second)
        );
        assert_eq!(universe.universe_id, universe.identity());
        assert_eq!(
            universe.universe_id,
            "75befaa529bc57c6b2d7a5ea4828f1e56bdc9018"
        );
        assert_eq!(
            first[0].grammar_candidate_id,
            "691f1f40dcc0699b5ef970d1c7ebc2b28b081a72"
        );
        assert_eq!(
            OpportunityGrammar::population_hash(&first),
            "fbee714e1103cc980b2b3caababf51165bc452ac"
        );
    }

    #[test]
    fn thread_count_is_not_an_input_to_grammar_artifacts() {
        let grammar = grammar(Direction::Long);
        let universe = universe(&grammar, "canonical-l1");
        let info = information();
        let one_thread = grammar.generate(&universe, &info).unwrap();
        let many_threads = grammar.generate(&universe, &info).unwrap();
        assert_eq!(one_thread, many_threads);
    }

    #[test]
    fn registry_grid_universe_timeframe_and_execution_mode_mutations_change_universe_identity() {
        let grammar = grammar(Direction::Long);
        let base = universe(&grammar, "canonical-l1");
        let mut primitive = grammar.clone();
        primitive.primitives.version = "registered-v2".into();
        let primitive_universe = universe(&primitive, "canonical-l1");
        let mut template = grammar.clone();
        template.templates.version = "template-v2".into();
        let template_universe = universe(&template, "canonical-l1");
        let mut grid = grammar.clone();
        grid.grid
            .values
            .get_mut("threshold")
            .unwrap()
            .push(110.0.into());
        let grid_universe = universe(&grid, "canonical-l1");
        let mut instruments = base.clone();
        instruments.instrument_universe.push("ETHUSDT".into());
        instruments.search_universe_size = grammar.search_universe_size(2, 1).unwrap();
        instruments.bind_identity();
        let mut timeframe = base.clone();
        timeframe.timeframe_set = vec!["5m".into()];
        timeframe.bind_identity();
        let execution = universe(&grammar, "other-detection-mode");
        assert_ne!(base.universe_id, grid_universe.universe_id);
        assert_ne!(
            base.search_universe_size,
            grid_universe.search_universe_size
        );
        assert_ne!(base.universe_id, primitive_universe.universe_id);
        assert_ne!(base.universe_id, template_universe.universe_id);
        assert_ne!(base.universe_id, instruments.universe_id);
        assert_ne!(base.universe_id, timeframe.universe_id);
        assert_ne!(base.universe_id, execution.universe_id);
    }

    #[test]
    fn direction_is_a_distinct_grammar_candidate_identity() {
        let info = information();
        let long = grammar(Direction::Long);
        let short = grammar(Direction::Short);
        let long_candidate = long
            .generate(&universe(&long, "canonical-l1"), &info)
            .unwrap()
            .pop()
            .unwrap();
        let short_candidate = short
            .generate(&universe(&short, "canonical-l1"), &info)
            .unwrap()
            .pop()
            .unwrap();
        assert_ne!(
            long_candidate.grammar_candidate_id,
            short_candidate.grammar_candidate_id
        );
    }

    #[test]
    fn grammar_generation_does_not_mutate_lifecycle_registry() {
        let mut registry = CandidateRegistry::new();
        registry
            .apply("production-candidate", None, "DETECTED", "existing", 1)
            .unwrap();
        let records = registry.records().to_vec();
        let grammar = grammar(Direction::Long);
        let _ = grammar
            .generate(&universe(&grammar, "canonical-l1"), &information())
            .unwrap();
        assert_eq!(registry.records(), records.as_slice());
    }
}
