//! Dataset: columnar OHLCV + the three clocks, one allocation per symbol
//! (COMPUTE_CORE_SPEC §4; DATASET_SPEC).
//!
//! A `Dataset` is built once per symbol per request. It ingests a verified
//! tape (JSONL `TapeRow` records), fails closed on anything the V8.0 decision
//! path refuses (`_validate_tape_rows`, src/v8/lab.py), and holds rows in the
//! canonical replay order `(event_time, available_time, venue_sequence)`
//! (PERSISTENCE_REPLAY_SPEC §4). The three clocks are never collapsed
//! (MARKET_STATE_CONTRACT §1).
//!
//! Fail-closed classifications are mirrored verbatim from the V8.0 oracle so
//! G6 (failure modes agree) compares equal classification strings.

use std::collections::BTreeMap;

use serde_json::Value;

use crate::jsonx::NonFinite;

/// A parsed tape row, mirroring `schema.TapeRow`. `nonfinite` records the JSON
/// paths of Python-style non-finite literals found by the lenient parser
/// (`jsonx`); it is empty for every tape that passes validation, so it never
/// enters an artifact.
#[derive(Debug, Clone)]
pub struct TapeRow {
    pub source: String,
    pub channel: String,
    pub instrument: String,
    pub event_time: i64,
    pub available_time: i64,
    pub ingested_time: i64,
    pub venue_sequence: i64,
    pub event_id: String,
    pub payload: Value,
    pub nonfinite: Vec<NonFinite>,
}

impl TapeRow {
    pub fn from_parts(v: &Value, nonfinite: Vec<NonFinite>) -> Result<TapeRow, DatasetError> {
        let obj = v
            .as_object()
            .ok_or_else(|| DatasetError::Malformed("tape row is not a JSON object".to_string()))?;
        let get_str = |k: &str| -> Result<String, DatasetError> {
            obj.get(k)
                .and_then(|x| x.as_str())
                .map(|s| s.to_string())
                .ok_or_else(|| {
                    DatasetError::Malformed(format!("tape row missing string field {k}"))
                })
        };
        let get_i64 = |k: &str| -> Result<i64, DatasetError> {
            obj.get(k).and_then(|x| x.as_i64()).ok_or_else(|| {
                DatasetError::Malformed(format!("tape row missing integer field {k}"))
            })
        };
        Ok(TapeRow {
            source: get_str("source")?,
            channel: get_str("channel")?,
            instrument: get_str("instrument")?,
            event_time: get_i64("event_time")?,
            available_time: get_i64("available_time")?,
            ingested_time: get_i64("ingested_time")?,
            venue_sequence: get_i64("venue_sequence")?,
            event_id: get_str("event_id")?,
            payload: obj.get("payload").cloned().unwrap_or(Value::Null),
            nonfinite,
        })
    }

    /// True when a non-finite literal was found at `payload.<field>`.
    fn payload_nonfinite(&self, field: &str) -> bool {
        let want = format!("payload.{field}");
        self.nonfinite.iter().any(|n| n.path == want)
    }
}

/// Fail-closed classification for a tape the compute plane refuses. The
/// message mirrors the V8.0 oracle's ValueError text so G6 can compare
/// classifications verbatim.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum DatasetError {
    /// Malformed JSON / missing required fields.
    Malformed(String),
    /// `_validate_tape_rows` classification (src/v8/lab.py).
    Tape(String),
}

impl std::fmt::Display for DatasetError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            DatasetError::Malformed(m) => write!(f, "malformed: {m}"),
            DatasetError::Tape(m) => write!(f, "{m}"),
        }
    }
}

impl std::error::Error for DatasetError {}

/// Validate one row exactly as `_validate_tape_rows` does (src/v8/lab.py).
fn validate_row(r: &TapeRow) -> Result<(), DatasetError> {
    match r.channel.as_str() {
        "kline" => {
            // A Python non-finite literal in any OHLC field classifies as
            // "non-finite OHLC" before the numeric reads (the oracle parses
            // the NaN fine and only the validation rejects it).
            for f in ["open", "high", "low", "close"] {
                if r.payload_nonfinite(f) {
                    return Err(DatasetError::Tape(format!(
                        "kline {}: non-finite OHLC",
                        r.event_id
                    )));
                }
            }
            let p = &r.payload;
            let num = |f: &str| -> Result<f64, DatasetError> {
                p.get(f).and_then(|x| x.as_f64()).ok_or_else(|| {
                    DatasetError::Tape(format!("kline {}: missing or non-numeric OHLC", r.event_id))
                })
            };
            let (o, h, l, c) = (num("open")?, num("high")?, num("low")?, num("close")?);
            if o.min(h).min(l).min(c) <= 0.0 {
                return Err(DatasetError::Tape(format!(
                    "kline {}: non-positive OHLC ({o}, {h}, {l}, {c})",
                    r.event_id
                )));
            }
            if h < o.max(c) || l > o.min(c) || h < l {
                return Err(DatasetError::Tape(format!(
                    "kline {}: OHLC invariant violation (high={h} low={l} open={o} close={c})",
                    r.event_id
                )));
            }
            if let Some(vol) = p.get("volume") {
                let v = vol.as_f64().ok_or_else(|| {
                    DatasetError::Tape(format!("kline {}: non-finite volume", r.event_id))
                })?;
                if !v.is_finite() || v < 0.0 {
                    return Err(DatasetError::Tape(format!(
                        "kline {}: negative or non-finite volume",
                        r.event_id
                    )));
                }
            }
            Ok(())
        }
        "funding" => {
            if r.payload_nonfinite("funding_rate") {
                return Err(DatasetError::Tape(format!(
                    "funding {}: non-finite rate",
                    r.event_id
                )));
            }
            let p = &r.payload;
            let rate = p
                .get("funding_rate")
                .and_then(|x| x.as_f64())
                .ok_or_else(|| {
                    DatasetError::Tape(format!(
                        "funding {}: missing or non-numeric rate",
                        r.event_id
                    ))
                })?;
            if rate.abs() > 0.10 {
                return Err(DatasetError::Tape(format!(
                    "funding {}: implausible rate {rate}",
                    r.event_id
                )));
            }
            Ok(())
        }
        _ => Ok(()), // non-kline, non-funding channels pass through unvalidated
    }
}

/// Closed kline bars for one symbol, in canonical replay order.
#[derive(Debug)]
pub struct SymbolBars {
    pub symbol: String,
    pub opens: Vec<f64>,
    pub highs: Vec<f64>,
    pub lows: Vec<f64>,
    pub closes: Vec<f64>,
    pub volumes: Vec<f64>,
    pub event_times: Vec<i64>,
    pub available_times: Vec<i64>,
    pub ingested_times: Vec<i64>,
    pub venue_sequences: Vec<i64>,
    pub event_ids: Vec<String>,
    /// Index of each bar's source row in `Dataset::rows`.
    #[allow(dead_code)] // S1 lineage: consumed raw rows for input_lineage_hash
    pub row_indices: Vec<usize>,
}

#[derive(Debug)]
pub struct Dataset {
    /// Every row in canonical replay order.
    pub rows: Vec<TapeRow>,
    /// Per-symbol closed-kline bars, symbols in sorted order.
    pub bars: Vec<SymbolBars>,
    /// The tape as parsed, in sorted (event, available, sequence) order.
    pub n_rows: usize,
}

impl Dataset {
    /// Ingest a tape of parsed rows. Fails closed on any row the V8.0 oracle
    /// refuses (`_validate_tape_rows`); dedups by (source, event_id) exactly
    /// like `AppendOnlyLog.append` (first occurrence wins, the store's inbox);
    /// and holds the surviving rows in the canonical replay order
    /// `(event_time, available_time, venue_sequence)` (PERSISTENCE_REPLAY_SPEC
    /// §4). An unsorted input batch is sorted, not rejected — that is what
    /// `replay_tape` does; the "unsorted" fail-closed case belongs to the
    /// state layer, not the tape layer.
    pub fn from_rows(mut rows: Vec<TapeRow>) -> Result<Dataset, DatasetError> {
        for r in &rows {
            validate_row(r)?;
        }
        // Dedup by (source, event_id), first occurrence wins — mirrors
        // AppendOnlyLog.append's inbox.
        let mut inbox: std::collections::HashSet<(String, String)> =
            std::collections::HashSet::new();
        rows.retain(|r| inbox.insert((r.source.clone(), r.event_id.clone())));
        // Canonical replay order.
        rows.sort_by(|a, b| {
            (a.event_time, a.available_time, a.venue_sequence).cmp(&(
                b.event_time,
                b.available_time,
                b.venue_sequence,
            ))
        });

        // Per-symbol closed kline bars; one allocation per symbol. Symbol
        // order is sorted for determinism (BTreeMap keeps it).
        let mut by_symbol: BTreeMap<String, Vec<usize>> = BTreeMap::new();
        for (i, r) in rows.iter().enumerate() {
            if r.channel == "kline"
                && r.payload.get("closed").and_then(|c| c.as_bool()) == Some(true)
            {
                by_symbol.entry(r.instrument.clone()).or_default().push(i);
            }
        }
        let mut bars = Vec::new();
        for (symbol, idxs) in by_symbol {
            let mut b = SymbolBars {
                symbol,
                opens: Vec::with_capacity(idxs.len()),
                highs: Vec::with_capacity(idxs.len()),
                lows: Vec::with_capacity(idxs.len()),
                closes: Vec::with_capacity(idxs.len()),
                volumes: Vec::with_capacity(idxs.len()),
                event_times: Vec::with_capacity(idxs.len()),
                available_times: Vec::with_capacity(idxs.len()),
                ingested_times: Vec::with_capacity(idxs.len()),
                venue_sequences: Vec::with_capacity(idxs.len()),
                event_ids: Vec::with_capacity(idxs.len()),
                row_indices: idxs.clone(),
            };
            for i in &idxs {
                let r = &rows[*i];
                let p = &r.payload;
                b.opens.push(p["open"].as_f64().unwrap_or(0.0));
                b.highs.push(p["high"].as_f64().unwrap_or(0.0));
                b.lows.push(p["low"].as_f64().unwrap_or(0.0));
                b.closes.push(p["close"].as_f64().unwrap_or(0.0));
                b.volumes.push(p["volume"].as_f64().unwrap_or(0.0));
                b.event_times.push(r.event_time);
                b.available_times.push(r.available_time);
                b.ingested_times.push(r.ingested_time);
                b.venue_sequences.push(r.venue_sequence);
                b.event_ids.push(r.event_id.clone());
            }
            bars.push(b);
        }
        let n_rows = rows.len();
        Ok(Dataset { rows, bars, n_rows })
    }

    /// Symbol whose closed bars are at `bars[i]`.
    #[allow(dead_code)] // S1 feature store
    pub fn symbol(&self, i: usize) -> &str {
        &self.bars[i].symbol
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn kline_row(id: &str, sym: &str, t: i64, o: f64, h: f64, l: f64, c: f64, vol: f64) -> TapeRow {
        TapeRow {
            source: "binance-um".into(),
            channel: "kline".into(),
            instrument: sym.into(),
            event_time: t,
            available_time: t + 1,
            ingested_time: t + 2,
            venue_sequence: 1,
            event_id: id.into(),
            payload: json!({"open": o, "high": h, "low": l, "close": c,
                            "volume": vol, "closed": true}),
            nonfinite: vec![],
        }
    }

    #[test]
    fn validates_ohlc_invariants_like_oracle() {
        // h < max(o,c) must fail with the oracle's classification text.
        let bad = vec![kline_row("b1", "SOLUSDT", 1, 100.0, 90.0, 95.0, 99.0, 1.0)];
        match Dataset::from_rows(bad) {
            Err(DatasetError::Tape(m)) => {
                assert!(m.contains("OHLC invariant violation"), "got: {m}")
            }
            other => panic!("expected Tape error, got {other:?}"),
        }
    }

    #[test]
    fn rejects_non_finite_ohlc() {
        // A Python-written tape carries NaN as a bare literal; the lenient
        // parser records it and validation classifies it "non-finite OHLC"
        // exactly like the oracle.
        let line = r#"{"source":"binance-um","channel":"kline","instrument":"SOLUSDT","event_time":1,"available_time":2,"ingested_time":3,"venue_sequence":1,"event_id":"b1","payload":{"open":NaN,"high":100.0,"low":95.0,"close":99.0,"volume":1.0,"closed":true}}"#;
        let parsed = crate::jsonx::parse_line(line).unwrap();
        let row = TapeRow::from_parts(&parsed.value, parsed.nonfinite).unwrap();
        match Dataset::from_rows(vec![row]) {
            Err(DatasetError::Tape(m)) => assert!(m.contains("non-finite"), "got: {m}"),
            other => panic!("expected Tape error, got {other:?}"),
        }
    }

    #[test]
    fn rejects_funding_implausible_rate() {
        let rows = vec![TapeRow {
            source: "binance-um".into(),
            channel: "funding".into(),
            instrument: "SOLUSDT".into(),
            event_time: 1,
            available_time: 2,
            ingested_time: 3,
            venue_sequence: 1,
            event_id: "f1".into(),
            payload: json!({"funding_rate": 0.5}),
            nonfinite: vec![],
        }];
        match Dataset::from_rows(rows) {
            Err(DatasetError::Tape(m)) => assert!(m.contains("implausible rate"), "got: {m}"),
            other => panic!("expected Tape error, got {other:?}"),
        }
    }

    #[test]
    fn sorts_into_canonical_replay_order() {
        // Ingestion order differs from replay order; Dataset must sort.
        let rows = vec![
            kline_row("a", "SOLUSDT", 30, 1.0, 2.0, 0.5, 1.5, 1.0),
            kline_row("b", "SOLUSDT", 10, 1.0, 2.0, 0.5, 1.5, 1.0),
            kline_row("c", "SOLUSDT", 20, 1.0, 2.0, 0.5, 1.5, 1.0),
        ];
        let d = Dataset::from_rows(rows).unwrap();
        let ids: Vec<&str> = d.rows.iter().map(|r| r.event_id.as_str()).collect();
        assert_eq!(ids, vec!["b", "c", "a"]);
    }

    #[test]
    fn closed_only_bars_are_columnar() {
        let mut rows = vec![
            kline_row("a", "SOLUSDT", 10, 1.0, 2.0, 0.5, 1.5, 1.0),
            kline_row("b", "SOLUSDT", 20, 1.0, 2.0, 0.5, 1.5, 1.0),
        ];
        // An open (unclosed) bar must not feed the feature columns.
        rows[1].payload["closed"] = json!(false);
        let d = Dataset::from_rows(rows).unwrap();
        assert_eq!(d.rows.len(), 2, "all rows retained for round-trip");
        assert_eq!(d.bars.len(), 1);
        assert_eq!(d.bars[0].closes, vec![1.5]);
    }

    #[test]
    fn dedups_by_source_event_id_first_wins() {
        // Duplicate (source, event_id) rows are dropped by the store inbox;
        // the first occurrence survives. This mirrors AppendOnlyLog.append.
        let rows = vec![
            kline_row("s:1", "SOLUSDT", 10, 1.0, 2.0, 0.5, 1.5, 1.0),
            kline_row("s:1", "SOLUSDT", 20, 2.0, 3.0, 1.5, 2.5, 1.0),
        ];
        let d = Dataset::from_rows(rows).unwrap();
        assert_eq!(d.n_rows, 1);
        assert_eq!(d.rows[0].event_time, 10);
    }
}
