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

mod candidate;
mod data;
mod evidence;
mod experts;
mod hash;
mod jsonx;
mod regret;
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
  evaluate-check  batch per-bar ExpertPlane draft check (stage S4)
  registry        print the 28-expert dispatch table with ported flags (S4)";

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
        "cube" => cmd_cube(&args[2..]),
        "evaluate-check" => cmd_evaluate_check(&args[2..]),
        "registry" => cmd_registry(),
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

fn push_opt_f64(col: &mut evidence::Column, v: Option<f64>) {
    match v {
        Some(x) => col.push_f64(x),
        None => {
            col.push_f64(0.0);
            col.push_absent();
        }
    }
}

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

// ---------------------------------------------------------------------------
// S3: CubeReducer + streaming regret
// ---------------------------------------------------------------------------

fn cmd_cube(args: &[String]) -> i32 {
    if args.len() != 1 {
        eprintln!("usage: v8-core cube <request.json>");
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
    match cube(&req) {
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

/// The request payload for one Candidate's cube cells.
#[derive(serde::Deserialize)]
struct CubeCandidate {
    candidate_id: String,
    symbol: String,
    direction: String,
    birth_time: i64,
    geometry: serde_json::Map<String, Value>,
    entry_bar_index: Option<u64>,
    window_end: Option<u64>,
    predicate_ir: Option<Value>,
}

fn cube(req: &ReplayRequest) -> Result<Value, String> {
    let rows = read_tape(&req.tape_path)?;
    let ds = data::Dataset::from_rows(rows).map_err(|e| e.to_string())?;
    let stores = state::build_stores(&ds);
    std::fs::create_dir_all(&req.out_dir).map_err(|e| format!("out_dir: {e}"))?;

    let sim = simulator::SimulatorParams::from_json(&req.manifest);
    let mut funding_schedule: Vec<(i64, f64)> = ds.rows.iter()
        .filter(|r| r.channel == "funding")
        .map(|r| (r.event_time, r.payload["funding_rate"].as_f64().unwrap_or(0.0)))
        .collect();
    funding_schedule.sort_by_key(|(t, _)| *t);

    let mut art = evidence::Artifact::new(
        "cube-reduced",
        if req.tier.is_empty() { "VALUES" } else { &req.tier },
        serde_json::json!({ "hash_encoding": hash::HASH_ENCODING,
                            "generator_version": regret::GENERATOR_VERSION }),
        "candidate_id",
    );
    let c_cid = art.add_column("candidate_id", evidence::DType::DictStr);
    let c_mid = art.add_column("manifest_id", evidence::DType::DictStr);
    let c_aid = art.add_column("actual_action_id", evidence::DType::DictStr);
    let c_au = art.add_column("actual_utility", evidence::DType::F64);
    let c_bu = art.add_column("best_utility", evidence::DType::F64);
    let c_tie = art.add_column("tie_cardinality", evidence::DType::I64);
    let c_gap = art.add_column("legal_hindsight_gap", evidence::DType::F64);
    let c_gs = art.add_column("gap_status", evidence::DType::DictStr);
    let c_reason = art.add_column("abstention_reason", evidence::DType::DictStr);
    let c_nt = art.add_column("no_trade_value", evidence::DType::F64);
    let c_ok = art.add_column("n_ok", evidence::DType::I64);
    let c_ce = art.add_column("n_censored", evidence::DType::I64);
    let c_uf = art.add_column("n_undefined_future", evidence::DType::I64);
    let c_ne = art.add_column("n_not_evaluable_action", evidence::DType::I64);
    let c_ne2 = art.add_column("n_no_entry", evidence::DType::I64);

    let mut n_candidates = 0usize;
    for raw in &req.candidates {
        let cand: CubeCandidate = serde_json::from_value(raw.clone())
            .map_err(|e| format!("cube candidate parse: {e}"))?;
        let store = stores.iter().find(|s| s.symbol == cand.symbol)
            .ok_or_else(|| format!("cube: no bars for symbol {}", cand.symbol))?;
        let kernel = simulator::ReplayKernel {
            round_trip_cost_r: sim.round_trip_cost_r,
            funding_rate_r: sim.funding_rate_r,
            funding_hours: sim.funding_hours,
            fill_policy: sim.fill_policy,
            funding_schedule: &funding_schedule,
            round_trip_cost_bps: sim.round_trip_cost_bps,
            bars: store_bars(&ds, &cand.symbol),
            store,
        };

        let manifest = regret::generate_legal_actions(&cand.geometry);
        let entry_idx = match cand.entry_bar_index {
            Some(i) => i as usize,
            None => {
                // NO_ENTRY cell for every action; the gap is
                // NOT_APPLICABLE_NO_ACTUAL_ACTION (no actual entry bar).
                let cells: Vec<regret::Cell> = manifest.actions.iter().map(|a| {
                    regret::Cell { action_id: a.action_id.clone(),
                                   status: regret::CELL_NO_ENTRY,
                                   reason: "candidate has no actual entry bar".into(),
                                   net_utility: None }
                }).collect();
                write_reduced(&mut art, &cand, &manifest, &cells,
                              &[c_cid, c_mid, c_aid, c_au, c_bu, c_tie, c_gap,
                                c_gs, c_reason, c_nt, c_ok, c_ce, c_uf, c_ne, c_ne2])?;
                n_candidates += 1;
                continue;
            }
        };
        let window_end = cand.window_end.unwrap_or(store.closes.len() as u64) as usize;

        let mut cells = Vec::with_capacity(manifest.actions.len());
        for a in &manifest.actions {
            if a.kind == "NO_TRADE" {
                cells.push(regret::Cell {
                    action_id: a.action_id.clone(),
                    status: regret::CELL_OK,
                    reason: String::new(),
                    net_utility: Some(0.0),
                });
                continue;
            }
            if window_end.saturating_sub(entry_idx) <= regret::MIN_FUTURE_BARS {
                cells.push(regret::Cell {
                    action_id: a.action_id.clone(),
                    status: regret::CELL_UNDEFINED_FUTURE,
                    reason: format!("fewer than {} bars of future after the entry bar — the simulator would return a manufactured EXPIRY value", regret::MIN_FUTURE_BARS + 1),
                    net_utility: None,
                });
                continue;
            }
            let mut geom = cand.geometry.clone();
            for (k, v) in &a.override_geom {
                geom.insert(k.clone(), v.clone());
            }
            let draft = simulator::Draft {
                direction: cand.direction.clone(),
                birth_time: cand.birth_time,
                risk_geometry: geom,
            };
            let out = match kernel.run(&draft, entry_idx, window_end, cand.predicate_ir.as_ref()) {
                Ok(o) => o,
                Err(e) => {
                    cells.push(regret::Cell {
                        action_id: a.action_id.clone(),
                        status: regret::CELL_NOT_EVALUABLE_ACTION,
                        reason: format!("replay raised: {e}"),
                        net_utility: None,
                    });
                    continue;
                }
            };
            if out.label_status == "NOT_EXECUTED" {
                cells.push(regret::Cell {
                    action_id: a.action_id.clone(),
                    status: regret::CELL_NOT_EVALUABLE_ACTION,
                    reason: "action never filled on this tape (e.g. FILL_AT_LIMIT never traded through)".into(),
                    net_utility: None,
                });
                continue;
            }
            let status = if out.label_status == "MATURE" { regret::CELL_OK } else { regret::CELL_CENSORED };
            cells.push(regret::Cell {
                action_id: a.action_id.clone(),
                status,
                reason: if status == regret::CELL_OK { String::new() } else {
                    "replay reached tape end before a terminal endpoint".into()
                },
                net_utility: Some(out.net_r),
            });
        }

        write_reduced(&mut art, &cand, &manifest, &cells,
                      &[c_cid, c_mid, c_aid, c_au, c_bu, c_tie, c_gap,
                        c_gs, c_reason, c_nt, c_ok, c_ce, c_uf, c_ne, c_ne2])?;
        n_candidates += 1;
    }

    let artifact_path = req.out_dir.join("cube-reduced.v82");
    art.write(&artifact_path).map_err(|e| format!("write cube artifact: {e}"))?;
    Ok(serde_json::json!({
        "subcommand": "cube",
        "candidates": n_candidates,
        "artifact": artifact_path.to_string_lossy(),
        "fingerprint": evidence::fingerprint(&artifact_path).unwrap_or_default(),
    }))
}

#[allow(clippy::too_many_arguments)]
fn write_reduced(
    art: &mut evidence::Artifact,
    cand: &CubeCandidate,
    manifest: &regret::Manifest,
    cells: &[regret::Cell],
    cols: &[usize; 15],
) -> Result<(), String> {
    let row = regret::compute_gap(&cand.candidate_id, manifest, cells);
    let [c_cid, c_mid, c_aid, c_au, c_bu, c_tie, c_gap, c_gs, c_reason,
         c_nt, c_ok, c_ce, c_uf, c_ne, c_no_entry] = *cols;
    art.columns[c_cid].push_str(&row.candidate_id);
    art.columns[c_mid].push_str(&row.manifest_id);
    match &row.actual_action_id {
        Some(a) => art.columns[c_aid].push_str(a),
        None => { art.columns[c_aid].push_str(""); art.columns[c_aid].push_absent(); }
    }
    push_opt_f64(&mut art.columns[c_au], row.actual_utility);
    push_opt_f64(&mut art.columns[c_bu], row.best_utility);
    art.columns[c_tie].push_i64(row.tie_cardinality as i64);
    push_opt_f64(&mut art.columns[c_gap], row.legal_hindsight_gap);
    art.columns[c_gs].push_str(row.gap_status);
    art.columns[c_reason].push_str(&row.abstention_reason);
    push_opt_f64(&mut art.columns[c_nt], row.no_trade_value);
    let n = |s: &str| *row.counts.get(s).unwrap_or(&0) as i64;
    art.columns[c_ok].push_i64(n(regret::CELL_OK));
    art.columns[c_ce].push_i64(n(regret::CELL_CENSORED));
    art.columns[c_uf].push_i64(n(regret::CELL_UNDEFINED_FUTURE));
    art.columns[c_ne].push_i64(n(regret::CELL_NOT_EVALUABLE_ACTION));
    art.columns[c_no_entry].push_i64(n(regret::CELL_NO_ENTRY));
    art.end_row();
    Ok(())
}

// ---------------------------------------------------------------------------
// S4: ExpertPlane (evaluate ports)
// ---------------------------------------------------------------------------

fn cmd_evaluate_check(args: &[String]) -> i32 {
    if args.len() != 1 {
        eprintln!("usage: v8-core evaluate-check <request.json>");
        return 2;
    }
    let bytes = match std::fs::read(&args[0]) {
        Ok(b) => b,
        Err(e) => {
            eprintln!("error: cannot read request: {e}");
            return 1;
        }
    };
    #[derive(serde::Deserialize)]
    struct EvalCheckReq {
        tape_path: PathBuf,
        universe: Vec<String>,
        #[serde(default)]
        expert_id: String,
        #[serde(default)]
        bar_index: usize,
        history_depth: Option<usize>,
    }
    let req: EvalCheckReq = match serde_json::from_slice(&bytes) {
        Ok(r) => r,
        Err(e) => {
            eprintln!("error: cannot parse request: {e}");
            return 1;
        }
    };
    let rows = match read_tape(&req.tape_path) {
        Ok(r) => r,
        Err(e) => { eprintln!("error: {e}"); return 1; }
    };
    let ds = match data::Dataset::from_rows(rows) {
        Ok(d) => d,
        Err(e) => { eprintln!("error: {e}"); return 1; }
    };
    let stores = state::build_stores(&ds);
    let sym = req.universe.first().cloned().unwrap_or_else(|| "SOLUSDT".to_string());
    let store = match stores.iter().find(|s| s.symbol == sym) {
        Some(s) => s,
        None => { eprintln!("error: no bars for {sym}"); return 1; }
    };
    // Batch mode: {"cases": [{"expert_id","bar_index"}...]} — one result per
    // case; otherwise the request is a single (expert_id, bar_index).
    let cases: Vec<(String, usize)> = match req2_cases(&bytes) {
        Some(c) => c,
        None => vec![(req.expert_id.clone(), req.bar_index)],
    };
    let mut results = Vec::with_capacity(cases.len());
    for (eid, bar_index) in cases {
        let t = bar_index + 1;
        let as_of = store.avail[bar_index];
        let feats = state::state_features(store, t, as_of, req.history_depth.unwrap_or(32));
        let mut map = std::collections::HashMap::new();
        for f in &feats {
            map.insert(f.name.clone(), f.clone());
        }
        let hist = state::history_bars(store, t, req.history_depth.unwrap_or(32));
        let fm = experts::base::FeatMap { features: &map, history: hist, as_of, symbol: &sym };
        let ev = experts::evaluate(&eid, &fm);
        results.push(serde_json::json!({
            "expert_id": eid,
            "bar_index": bar_index,
            "as_of": as_of,
            "applicability": ev.applicability,
            "decision": ev.decision,
            "draft": ev.draft.as_ref().map(|d| serde_json::json!({
                "direction": d.direction,
                "birth_time": d.birth_time,
                "risk_geometry": d.risk_geometry,
            })),
            "setup_anchor_event_id": ev.setup_anchor_event_id,
            "setup_fingerprint": ev.setup_fingerprint,
        }));
    }
    println!("{}", serde_json::to_string(&serde_json::json!({"results": results})).unwrap());
    0
}

/// The 28-expert dispatch table with ported flags — the parity harness
/// derives its PORTED set from this (S4 gate; parallel-safe: the harness
/// never hand-maintains the list).
fn cmd_registry() -> i32 {
    let rows: Vec<_> = experts::registry_rows().iter()
        .map(|(id, p)| serde_json::json!({"expert_id": id, "ported": p}))
        .collect();
    println!("{}", serde_json::to_string(&serde_json::json!({"registry": rows})).unwrap());
    0
}

fn req2_cases(bytes: &[u8]) -> Option<Vec<(String, usize)>> {
    let v: serde_json::Value = serde_json::from_slice(bytes).ok()?;
    let cases = v.get("cases")?.as_array()?;
    Some(cases.iter().filter_map(|c| {
        Some((c.get("expert_id")?.as_str()?.to_string(),
              c.get("bar_index")?.as_u64()? as usize))
    }).collect())
}
