//! Narrow, availability-gated adapter over the existing FeatureStore state
//! surface (TARGET_ORACLE_SPEC §4).

#![allow(dead_code)]

use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};

use crate::state::Feature;

use super::taxonomy::OracleRefusal;

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct InformationField {
    pub name: String,
    pub value: serde_json::Value,
    pub event_time: i64,
    pub knowledge_time: i64,
    pub availability_time: i64,
    pub source_id: String,
    pub source_version: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct InformationSet {
    pub decision_time: i64,
    fields: BTreeMap<String, InformationField>,
}

impl InformationSet {
    pub fn new(decision_time: i64) -> Self {
        Self {
            decision_time,
            fields: BTreeMap::new(),
        }
    }

    pub fn insert(&mut self, field: InformationField) -> Result<(), OracleRefusal> {
        if field.knowledge_time > self.decision_time || field.availability_time > self.decision_time
        {
            return Err(OracleRefusal::MissingDecisionTimeData);
        }
        self.fields.insert(field.name.clone(), field);
        Ok(())
    }

    pub fn get(&self, name: &str) -> Option<&InformationField> {
        self.fields.get(name)
    }

    pub fn names(&self) -> impl Iterator<Item = &str> {
        self.fields.keys().map(String::as_str)
    }

    pub fn value_f64(&self, name: &str) -> Option<f64> {
        self.get(name).and_then(|field| field.value.as_f64())
    }
}

pub struct InformationAdapter;

impl InformationAdapter {
    /// Adapt an already-computed state feature without creating another
    /// MarketState/feature store. `max_input_available_time` is the existing
    /// state surface's PIT availability boundary and is used for both known
    /// and available clocks at this narrow adapter boundary.
    pub fn feature(
        feature: &Feature,
        event_time: i64,
        decision_time: i64,
        source_id: &str,
    ) -> Result<InformationField, OracleRefusal> {
        if feature.max_input_available_time > decision_time || feature.value.is_null() {
            return Err(OracleRefusal::MissingDecisionTimeData);
        }
        Ok(InformationField {
            name: feature.name.clone(),
            value: feature.value.clone(),
            event_time,
            knowledge_time: feature.max_input_available_time,
            availability_time: feature.max_input_available_time,
            source_id: source_id.to_string(),
            source_version: feature.feature_version.clone(),
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn future_known_or_unavailable_fields_cannot_enter_information_set() {
        let mut information = InformationSet::new(100);
        let future = InformationField {
            name: "future_return".into(),
            value: serde_json::json!(1.0),
            event_time: 101,
            knowledge_time: 101,
            availability_time: 101,
            source_id: "tape".into(),
            source_version: "v1".into(),
        };
        assert_eq!(
            information.insert(future),
            Err(OracleRefusal::MissingDecisionTimeData)
        );
        assert!(information.get("future_return").is_none());
    }
}
