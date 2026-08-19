//! V8 Evaluation Evidence System — Deterministic Schema Cache Builder (v8.eval.v1 §4, §24).
//!
//! Precomputes column statistics, distributions, quantiles, and null rates
//! for autonomous research agent queries in pure Rust.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::io;
use std::path::Path;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ColumnStatistics {
    pub dtype: String,
    pub row_count: usize,
    pub null_count: usize,
    pub null_rate: f64,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub mean: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub std: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub min: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub p1: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub p25: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub p50: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub p75: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub p99: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub max: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub cardinality: Option<usize>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct TableStatistics {
    pub file_name: String,
    pub relative_path: String,
    pub total_rows: usize,
    pub total_columns: usize,
    pub columns: HashMap<String, ColumnStatistics>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct SchemaCache {
    pub schema: String,
    pub root_dir: String,
    pub tables: HashMap<String, TableStatistics>,
}

impl SchemaCache {
    pub fn new(root_dir: &str) -> Self {
        Self {
            schema: "v8.eval.v1.schema_cache".to_string(),
            root_dir: root_dir.to_string(),
            tables: HashMap::new(),
        }
    }

    pub fn add_table(&mut self, rel_path: &str, table_stats: TableStatistics) {
        self.tables.insert(rel_path.to_string(), table_stats);
    }

    pub fn save(&self, path: &Path) -> io::Result<()> {
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent)?;
        }
        let json = serde_json::to_string_pretty(self)
            .map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))?;
        fs::write(path, json)
    }
}

pub fn compute_numeric_col_stats(dtype: &str, values: &[f64]) -> ColumnStatistics {
    let row_count = values.len();
    if values.is_empty() {
        return ColumnStatistics {
            dtype: dtype.to_string(),
            row_count: 0,
            null_count: 0,
            null_rate: 0.0,
            mean: None,
            std: None,
            min: None,
            p1: None,
            p25: None,
            p50: None,
            p75: None,
            p99: None,
            max: None,
            cardinality: None,
        };
    }

    let mut sorted = values.to_vec();
    sorted.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));

    let n = values.len() as f64;
    let mean = values.iter().sum::<f64>() / n;
    let variance = if values.len() > 1 {
        values.iter().map(|v| (v - mean).powi(2)).sum::<f64>() / (n - 1.0)
    } else {
        0.0
    };
    let std = variance.sqrt();

    let p_idx = |pct: f64| -> usize {
        let idx = (n * (pct / 100.0)) as usize;
        idx.min(values.len() - 1)
    };

    ColumnStatistics {
        dtype: dtype.to_string(),
        row_count,
        null_count: 0,
        null_rate: 0.0,
        mean: Some(mean),
        std: Some(std),
        min: Some(sorted[0]),
        p1: Some(sorted[p_idx(1.0)]),
        p25: Some(sorted[p_idx(25.0)]),
        p50: Some(sorted[p_idx(50.0)]),
        p75: Some(sorted[p_idx(75.0)]),
        p99: Some(sorted[p_idx(99.0)]),
        max: Some(*sorted.last().unwrap()),
        cardinality: None,
    }
}
