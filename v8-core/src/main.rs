//! V8.2 compute plane CLI (COMPUTE_CORE_SPEC §2, §6).
//!
//! One evaluation request per invocation: the control plane writes a
//! request.json, the compute plane reads it, and the boundary is the artifact
//! files it writes — never an FFI call (no-callback invariant, D-078).
//!
//! Subcommands are separately dispatchable so each kernel stays independently
//! attributable (COMPUTE_SCHEDULING_SPEC §2):
//!
//! ```text
//! v8-core ingest <request.json>       S0: Dataset ingest -> dataset artifact
//! v8-core features <request.json>     S1: FeatureStore + StateView values
//! v8-core predicate-check <ir> <in>   S2: compiled still_valid IR evaluator
//! v8-core replay <request.json>       S2: ReplayKernel outcomes
//! v8-core cube <request.json>         S3: CubeReducer + reduced tables
//! v8-core evaluate <request.json>     S4: ExpertPlane -> candidates -> reduce
//! ```
//!
//! `threads` and `engine` are scheduling details and never appear in any hash
//! (PARITY_AND_IDENTITY_SPEC G5; COMPUTE_SCHEDULING_SPEC §1).

mod data;
mod evidence;
mod experts;
mod hash;
mod jsonx;
mod simulator;
mod state;

use std::path::PathBuf;

use serde_json::Value;

const USAGE: &str = "v8-core <subcommand> <request.json|...>

subcommands:
  ingest          ingest a tape into a Dataset and write the dataset artifact
  features        compute FeatureStore/StateView values (stage S1)
  predicate-check evaluate compiled still_valid IR bytes (stage S2)
  replay          run the ReplayKernel over a candidate batch (stage S2)
  cube            stream the Outcome Cube to reduced tables (stage S3)
  evaluate        run the full ExpertPlane -> candidates -> reduce loop (stage S4)";

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() < 2 {
        eprintln!("{USAGE}");
        std::process::exit(2);
    }
    let code = match args[1].as_str() {
        "ingest" => cmd_ingest(&args[2..]),
        "features" => cmd_features(&args[2..]),
        "predicate-check" => cmd_predicate_check(&args[2..]),
        "replay" => cmd_replay(&args[2..]),
        other => {
            eprintln!("unknown subcommand: {other}\n\n{USAGE}");
            2
        }
    };
    std::process::exit(code);
}

/// A request file: the compiled evaluation request the control plane writes.
#[derive(Debug, serde::Deserialize)]
struct Request {
    tape_path: PathBuf,
    out_dir: PathBuf,
    #[serde(default = "default_threads")]
    threads: usize,
    #[serde(default = "default_engine")]
    engine: String,
    /// ExperimentManifest fields; consumed from S1 (features/state identity).
    #[serde(default)]
    #[allow(dead_code)]
    manifest: Value,
    #[serde(default)]
    tier: String,
    #[serde(default)]
    universe: Vec<String>,
    #[serde(default = "default_interval")]
    base_interval: String,
    #[serde(default = "default_depth")]
    history_depth: usize,
}

fn default_threads() -> usize {
    1
}
fn default_engine() -> String {
    "cpu".to_string()
}
fn default_interval() -> String {
    "1h".to_string()
}
fn default_depth() -> usize {
    state::HISTORY_DEPTH_DEFAULT
}

fn load_request(path: &str) -> Result<Request, String> {
    let bytes = std::fs::read(path).map_err(|e| format!("cannot read request {path}: {e}"))?;
    serde_json::from_slice(&bytes).map_err(|e| format!("cannot parse request {path}: {e}"))
}

/// Read a JSONL tape into parsed `TapeRow`s using the Python-json-compatible
/// parser (the tape is written by CPython `json.dumps`, which may emit
/// `NaN`/`Infinity` literals that strict JSON rejects).
fn read_tape(path: &PathBuf) -> Result<Vec<data::TapeRow>, String> {
    let text = std::fs::read_to_string(path).map_err(|e| format!("cannot read tape {path:?}: {e}"))?;
    let mut rows = Vec::new();
    for (i, line) in text.lines().enumerate() {
        if line.trim().is_empty() {
            continue;
        }
        let parsed = jsonx::parse_line(line).map_err(|e| format!("tape line {}: {e}", i + 1))?;
        let row = data::TapeRow::from_parts(&parsed.value, parsed.nonfinite)
            .map_err(|e| format!("tape line {}: {e}", i + 1))?;
        rows.push(row);
    }
    Ok(rows)
}

fn cmd_ingest(args: &[String]) -> i32 {
    if args.len() != 1 {
        eprintln!("usage: v8-core ingest <request.json>");
        return 2;
    }
    let req = match load_request(&args[0]) {
        Ok(r) => r,
        Err(e) => {
            eprintln!("error: {e}");
            return 1;
        }
    };
    if req.threads == 0 {
        eprintln!("error: threads must be >= 1");
        return 1;
    }
    if req.engine != "cpu" {
        eprintln!("error: unknown engine {:?} (only cpu exists)", req.engine);
        return 1;
    }
    match ingest(&req) {
        Ok(summary) => {
            println!("{}", serde_json::to_string(&summary).unwrap());
            0
        }
        Err(e) => {
            eprintln!("error: {e}");
            1
        }
    }
}

fn ingest(req: &Request) -> Result<Value, String> {
    let rows = read_tape(&req.tape_path)?;
    let ds = data::Dataset::from_rows(rows).map_err(|e| e.to_string())?;

    std::fs::create_dir_all(&req.out_dir).map_err(|e| format!("out_dir: {e}"))?;

    // Dataset artifact: the tape echo, one row per tape record in canonical
    // replay order, so the round-trip preserves every field of every row
    // (S0 gate: "tape round-trips; clocks preserved").
    let mut art = evidence::Artifact::new(
        "dataset",
        if req.tier.is_empty() { "VALUES" } else { &req.tier },
        serde_json::json!({
            "tape_path": req.tape_path.to_string_lossy(),
            "engine": req.engine,
            "hash_encoding": hash::HASH_ENCODING,
        }),
        "event_time,available_time,venue_sequence",
    );
    let c_source = art.add_column("source", evidence::DType::DictStr);
    let c_channel = art.add_column("channel", evidence::DType::DictStr);
    let c_instrument = art.add_column("instrument", evidence::DType::DictStr);
    let c_event_time = art.add_column("event_time", evidence::DType::I64);
    let c_available_time = art.add_column("available_time", evidence::DType::I64);
    let c_ingested_time = art.add_column("ingested_time", evidence::DType::I64);
    let c_venue_sequence = art.add_column("venue_sequence", evidence::DType::I64);
    let c_event_id = art.add_column("event_id", evidence::DType::DictStr);
    let c_payload = art.add_column("payload", evidence::DType::DictStr);

    for r in &ds.rows {
        // The payload column is a canonical JSON echo of the raw payload. The
        // parity harness parses it and compares VALUES bit-for-bit; the text
        // itself is not compared (float rendering differs across runtimes).
        art.columns[c_source].push_str(&r.source);
        art.columns[c_channel].push_str(&r.channel);
        art.columns[c_instrument].push_str(&r.instrument);
        art.columns[c_event_time].push_i64(r.event_time);
        art.columns[c_available_time].push_i64(r.available_time);
        art.columns[c_ingested_time].push_i64(r.ingested_time);
        art.columns[c_venue_sequence].push_i64(r.venue_sequence);
        art.columns[c_event_id].push_str(&r.event_id);
        let payload_text = serde_json::to_string(&r.payload).map_err(|e| e.to_string())?;
        art.columns[c_payload].push_str(&payload_text);
        art.end_row();
    }

    let artifact_path = req.out_dir.join("dataset.v82");
    art.write(&artifact_path).map_err(|e| format!("write artifact: {e}"))?;
    let fingerprint = evidence::fingerprint(&artifact_path).map_err(|e| e.to_string())?;

    let mut symbols: Vec<Value> = Vec::new();
    for b in &ds.bars {
        symbols.push(serde_json::json!({
            "symbol": b.symbol,
            "bars": b.closes.len(),
        }));
    }
    let summary = serde_json::json!({
        "subcommand": "ingest",
        "rows": ds.n_rows,
        "symbols": symbols,
        "artifact": artifact_path.to_string_lossy(),
        "artifact_fingerprint": fingerprint,
        "threads": req.threads,
    });
    Ok(summary)
}

// ---------------------------------------------------------------------------
// S1: FeatureStore + StateView -> per-symbol state artifacts
// ---------------------------------------------------------------------------

fn cmd_features(args: &[String]) -> i32 {
    if args.len() != 1 {
        eprintln!("usage: v8-core features <request.json>");
        return 2;
    }
    let req = match load_request(&args[0]) {
        Ok(r) => r,
        Err(e) => {
            eprintln!("error: {e}");
            return 1;
        }
    };
    if req.engine != "cpu" {
        eprintln!("error: unknown engine {:?} (only cpu exists)", req.engine);
        return 1;
    }
    match features(&req) {
        Ok(summary) => {
            println!("{}", serde_json::to_string(&summary).unwrap());
            0
        }
        Err(e) => {
            eprintln!("error: {e}");
            1
        }
    }
}

fn features(req: &Request) -> Result<Value, String> {
    let rows = read_tape(&req.tape_path)?;
    let ds = data::Dataset::from_rows(rows).map_err(|e| e.to_string())?;
    let stores = state::build_stores(&ds);
    std::fs::create_dir_all(&req.out_dir).map_err(|e| format!("out_dir: {e}"))?;

    // Universe: requested symbols, else every symbol with bars (deterministic:
    // the dataset's sorted symbol order).
    let universe: Vec<String> = if req.universe.is_empty() {
        stores.iter().map(|s| s.symbol.clone()).collect()
    } else {
        req.universe.clone()
    };
    let univ_refs: Vec<&str> = universe.iter().map(|s| s.as_str()).collect();

    let mut artifacts = Vec::new();
    for store in &stores {
        let sym = &store.symbol;
        if !universe.iter().any(|u| u == sym) {
            continue;
        }
        let path = req.out_dir.join(format!("state-{sym}.v82"));
        let mut art = evidence::Artifact::new(
            "state",
            if req.tier.is_empty() { "VALUES" } else { &req.tier },
            serde_json::json!({
                "symbol": sym,
                "base_interval": req.base_interval,
                "history_depth": req.history_depth,
                "hash_encoding": hash::HASH_ENCODING,
            }),
            "bar_index,as_of",
        );
        let c_bar = art.add_column("bar_index", evidence::DType::I64);
        let c_asof = art.add_column("as_of", evidence::DType::I64);
        let c_sid = art.add_column("state_id", evidence::DType::DictStr);
        let c_q = art.add_column("state_quality", evidence::DType::DictStr);
        let c_missing = art.add_column("missing_symbols", evidence::DType::DictStr);

        // Fixed column set: every declared feature name, in FEATURE_NAMES
        // order; absent features mark all their columns invalid.
        let mut value_cols: Vec<usize> = Vec::new();
        let mut qual_cols: Vec<usize> = Vec::new();
        let mut null_cols: Vec<usize> = Vec::new();
        let mut group_cols: Vec<usize> = Vec::new();
        let mut ver_cols: Vec<usize> = Vec::new();
        let mut dtype_cols: Vec<usize> = Vec::new();
        let mut avail_cols: Vec<usize> = Vec::new();
        for name in state::FEATURE_NAMES {
            let structured = state::feature_dtype(name) != "float";
            value_cols.push(art.add_column(
                &format!("{name}.value"),
                if structured { evidence::DType::DictStr } else { evidence::DType::F64 },
            ));
            qual_cols.push(art.add_column(&format!("{name}.quality"), evidence::DType::DictStr));
            null_cols.push(art.add_column(&format!("{name}.null_reason"), evidence::DType::DictStr));
            group_cols.push(art.add_column(&format!("{name}.group"), evidence::DType::DictStr));
            ver_cols.push(art.add_column(&format!("{name}.version"), evidence::DType::DictStr));
            dtype_cols.push(art.add_column(&format!("{name}.dtype"), evidence::DType::DictStr));
            avail_cols.push(art.add_column(&format!("{name}.max_available"), evidence::DType::I64));
        }

        let n_bars = store.closes.len();
        for i in 0..n_bars {
            let t = i + 1;
            let as_of = store.avail[i];
            let feats = state::state_features(store, t, as_of, req.history_depth);
            let lineage = state::v82_lineage_hash(&feats, sym);
            let sid = state::v82_state_id(as_of, &univ_refs.iter().map(|s| s.to_string()).collect::<Vec<_>>(), &lineage);
            let quality = if feats.iter().any(|f| f.quality == "DEGRADED") { "DEGRADED" } else { "COMPLETE" };

            art.columns[c_bar].push_i64(i as i64);
            art.columns[c_asof].push_i64(as_of);
            art.columns[c_sid].push_str(&sid);
            art.columns[c_q].push_str(quality);
            art.columns[c_missing].push_str("");

            // Emitted features by bare name.
            let mut by_name: std::collections::HashMap<&str, &state::Feature> =
                std::collections::HashMap::new();
            for f in &feats {
                by_name.insert(f.name.as_str(), f);
            }
            for (k, name) in state::FEATURE_NAMES.iter().enumerate() {
                let f = by_name.get(name);
                let structured = state::feature_dtype(name) != "float";
                match f {
                    Some(feat) => {
                        // A degraded feature (value None) has an ABSENT value:
                        // the value column carries no number (MARKET_STATE
                        // CONTRACT §4 — null is not zero), while the metadata
                        // columns stay valid.
                        let value_absent = feat.value.is_null();
                        if structured {
                            let text = serde_json::to_string(&feat.value).map_err(|e| e.to_string())?;
                            art.columns[value_cols[k]].push_str(&text);
                        } else if value_absent {
                            art.columns[value_cols[k]].push_f64(0.0);
                            art.columns[value_cols[k]].push_absent();
                        } else {
                            art.columns[value_cols[k]].push_f64(feat.value.as_f64().unwrap_or(0.0));
                        }
                        art.columns[qual_cols[k]].push_str(&feat.quality);
                        match &feat.null_reason {
                            Some(r) => art.columns[null_cols[k]].push_str(r),
                            None => {
                                art.columns[null_cols[k]].push_str("");
                                art.columns[null_cols[k]].push_absent();
                            }
                        }
                        art.columns[group_cols[k]].push_str(&feat.group);
                        art.columns[ver_cols[k]].push_str(&feat.feature_version);
                        art.columns[dtype_cols[k]].push_str(&feat.dtype);
                        art.columns[avail_cols[k]].push_i64(feat.max_input_available_time);
                    }
                    None => {
                        // Feature absent at this bar: every column invalid.
                        if structured {
                            art.columns[value_cols[k]].push_str("");
                            art.columns[value_cols[k]].push_absent();
                        } else {
                            art.columns[value_cols[k]].push_f64(0.0);
                            art.columns[value_cols[k]].push_absent();
                        }
                        art.columns[qual_cols[k]].push_str("");
                        art.columns[qual_cols[k]].push_absent();
                        art.columns[null_cols[k]].push_str("");
                        art.columns[null_cols[k]].push_absent();
                        art.columns[group_cols[k]].push_str("");
                        art.columns[group_cols[k]].push_absent();
                        art.columns[ver_cols[k]].push_str("");
                        art.columns[ver_cols[k]].push_absent();
                        art.columns[dtype_cols[k]].push_str("");
                        art.columns[dtype_cols[k]].push_absent();
                        art.columns[avail_cols[k]].push_i64(0);
                        art.columns[avail_cols[k]].push_absent();
                    }
                }
            }
            art.end_row();
        }
        art.write(&path).map_err(|e| format!("write state artifact: {e}"))?;
        let fp = evidence::fingerprint(&path).map_err(|e| e.to_string())?;
        artifacts.push(serde_json::json!({
            "symbol": sym,
            "bars": n_bars,
            "artifact": path.to_string_lossy(),
            "fingerprint": fp,
        }));
    }
    Ok(serde_json::json!({
        "subcommand": "features",
        "artifacts": artifacts,
        "threads": req.threads,
    }))
}

// ---------------------------------------------------------------------------
// S2: predicate IR evaluation + ReplayKernel
// ---------------------------------------------------------------------------

fn cmd_predicate_check(args: &[String]) -> i32 {
    if args.len() != 2 {
        eprintln!("usage: v8-core predicate-check <ir.json> <inputs.json>");
        return 2;
    }
    let read = |p: &str| -> Result<Value, String> {
        let bytes = std::fs::read(p).map_err(|e| format!("cannot read {p}: {e}"))?;
        serde_json::from_slice(&bytes).map_err(|e| format!("cannot parse {p}: {e}"))
    };
    let ir = match read(&args[0]) {
        Ok(v) => v,
        Err(e) => {
            eprintln!("error: {e}");
            return 1;
        }
    };
    let inputs = match read(&args[1]) {
        Ok(v) => v,
        Err(e) => {
            eprintln!("error: {e}");
            return 1;
        }
    };
    // Batch mode: {"cases": [inputs...]} evaluates each case; otherwise the
    // file is a single inputs object. One result per line.
    let cases: Vec<Value> = match inputs.get("cases") {
        Some(arr) => arr.as_array().cloned().unwrap_or_default(),
        None => vec![inputs.clone()],
    };
    let mut results = Vec::with_capacity(cases.len());
    for case in &cases {
        let direction = case["direction"].as_str().unwrap_or("LONG").to_string();
        let geom = case.get("geometry").and_then(|g| g.as_object())
            .cloned().unwrap_or_default();
        let live: std::collections::HashMap<String, f64> = case.get("live")
            .and_then(|l| l.as_object())
            .map(|m| m.iter().filter_map(|(k, v)| v.as_f64().map(|x| (k.clone(), x))).collect())
            .unwrap_or_default();
        let windows: std::collections::HashMap<String, f64> = case.get("windows")
            .and_then(|w| w.as_object())
            .map(|m| m.iter().filter_map(|(k, v)| v.as_f64().map(|x| (k.clone(), x))).collect())
            .unwrap_or_default();
        let history: Vec<[f64; 6]> = case.get("history").and_then(|h| h.as_array())
            .map(|arr| arr.iter().filter_map(|row| {
                let a = row.as_array()?;
                Some([a[0].as_f64()?, a[1].as_f64()?, a[2].as_f64()?,
                      a[3].as_f64()?, a[4].as_f64()?, a[5].as_f64()?])
            }).collect())
            .unwrap_or_default();
        let ctx = experts::predicate::FeatCtx {
            live: &|name| live.get(name).copied(),
            live_window: &|name, n| windows.get(&format!("{name}_{n}")).copied()
                .or_else(|| windows.get(&format!("{name}{n}")).copied()),
            history: &|| Some(history.clone()),
        };
        let result = experts::predicate::evaluate(&ir, &geom, &direction, &ctx);
        results.push(if result { "true" } else { "false" });
    }
    for r in results {
        println!("{r}");
    }
    0
}

/// The compiled evaluation request for the ReplayKernel: a candidate batch.
#[derive(Debug, serde::Deserialize)]
struct ReplayRequest {
    tape_path: PathBuf,
    out_dir: PathBuf,
    /// Consumed from S4 (candidate population across symbols).
    #[serde(default)]
    #[allow(dead_code)]
    universe: Vec<String>,
    #[serde(default = "default_threads")]
    #[allow(dead_code)]
    threads: usize,
    #[serde(default)]
    manifest: Value,
    #[serde(default)]
    #[allow(dead_code)]
    tier: String,
    /// Filled by the request writer from the Python side.
    #[serde(default)]
    candidates: Vec<Value>,
}

fn cmd_replay(args: &[String]) -> i32 {
    if args.len() != 1 {
        eprintln!("usage: v8-core replay <request.json>");
        return 2;
    }
    let bytes = match std::fs::read(&args[0]) {
        Ok(b) => b,
        Err(e) => {
            eprintln!("error: cannot read request: {e}");
            return 1;
        }
    };
    let req: ReplayRequest = match serde_json::from_slice(&bytes) {
        Ok(r) => r,
        Err(e) => {
            eprintln!("error: cannot parse request: {e}");
            return 1;
        }
    };
    match replay(&req) {
        Ok(summary) => {
            println!("{}", serde_json::to_string(&summary).unwrap());
            0
        }
        Err(e) => {
            eprintln!("error: {e}");
            1
        }
    }
}

fn replay(req: &ReplayRequest) -> Result<Value, String> {
    let rows = read_tape(&req.tape_path)?;
    let ds = data::Dataset::from_rows(rows).map_err(|e| e.to_string())?;
    let stores = state::build_stores(&ds);
    std::fs::create_dir_all(&req.out_dir).map_err(|e| format!("out_dir: {e}"))?;

    let m = &req.manifest;
    let sim = simulator::SimulatorParams::from_json(m);
    // Tape-driven funding schedule (D-041): (boundary_time_ns, rate) pairs
    // from the tape's funding channel, sorted by boundary time. Schedule
    // VALUES are tape data, never manifest data.
    let mut funding_schedule: Vec<(i64, f64)> = ds.rows.iter()
        .filter(|r| r.channel == "funding")
        .map(|r| (r.event_time, r.payload["funding_rate"].as_f64().unwrap_or(0.0)))
        .collect();
    funding_schedule.sort_by_key(|(t, _)| *t);
    let mut results = Vec::new();
    for cand in &req.candidates {
        let symbol = cand["symbol"].as_str().unwrap_or("").to_string();
        let store = stores.iter().find(|s| s.symbol == symbol).ok_or_else(|| {
            format!("replay: no bars for symbol {symbol}")
        })?;
        let draft = simulator::Draft {
            direction: cand["direction"].as_str().unwrap_or("LONG").to_string(),
            birth_time: cand["birth_time"].as_i64().unwrap_or(0),
            risk_geometry: cand.get("geometry").and_then(|g| g.as_object())
                .cloned().unwrap_or_default(),
        };
        let start = cand["entry_bar_index"].as_u64().unwrap_or(0) as usize;
        let window_end = cand["window_end"].as_u64()
            .unwrap_or(store.closes.len() as u64) as usize;
        let ir = cand.get("predicate_ir").cloned();
        let kernel = simulator::ReplayKernel {
            round_trip_cost_r: sim.round_trip_cost_r,
            funding_rate_r: sim.funding_rate_r,
            funding_hours: sim.funding_hours,
            fill_policy: sim.fill_policy,
            funding_schedule: &funding_schedule,
            round_trip_cost_bps: sim.round_trip_cost_bps,
            bars: store_bars(&ds, &symbol),
            store,
        };
        let out = kernel.run(&draft, start, window_end, ir.as_ref()).map_err(|e| e.to_string())?;
        results.push(serde_json::json!({
            "symbol": symbol,
            "entry_bar_index": start,
            "endpoint": out.endpoint,
            "net_r": out.net_r,
            "label_status": out.label_status,
            "horizon_bars": out.horizon_bars,
            "label_available_time": out.label_available_time,
            "mae_r": out.mae_r,
            "mfe_r": out.mfe_r,
            "ambiguous_bars": out.ambiguous_bars,
            "entry_price": out.entry_price,
            "risk_unit_price": out.risk_unit_price,
            "market_move_r": out.market_move_r,
        }));
    }
    Ok(serde_json::json!({ "subcommand": "replay", "results": results }))
}

/// The kernel needs the symbol's columnar bars; they live in the Dataset.
fn store_bars<'a>(ds: &'a data::Dataset, symbol: &str) -> &'a data::SymbolBars {
    ds.bars.iter().find(|b| b.symbol == symbol).unwrap()
}
