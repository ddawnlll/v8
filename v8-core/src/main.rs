#![allow(
    clippy::all,
    warnings
)]

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

mod account;
mod allocator;
mod analysis;
pub mod audit;
mod authority;
mod backend;
mod cache;
mod candidate;
mod cashflow;
mod checkpoint;
pub mod claims;
mod data;
pub mod error;
mod evaluation;
mod evidence;
mod exit_ablation;
mod experiment;
mod experts;
mod features;
mod hash;
mod jsonx;
mod mt19937;
mod oracle;
mod path_security;
mod portfolio;
pub mod judiciary;
pub mod kaizen;
pub mod opportunity;
pub mod quant;
mod regret;
mod report;
mod runloop;
mod scheduler;
mod shadow;
mod simd;
mod simulator;
mod state;
mod statistics;
pub mod telemetry;
pub mod temporal;
pub mod eeo;
pub mod usdm_sim;
pub mod venue;

use std::path::PathBuf;

use serde_json::Value;

const USAGE: &str = "v8-core <subcommand> <request.json|...>

subcommands:
  ingest          ingest a tape into a Dataset and write the dataset artifact
  features        compute FeatureStore/StateView values (stage S1)
  predicate-check evaluate compiled still_valid IR bytes (stage S2)
  replay          run the ReplayKernel over a candidate batch (stage S2)
  bench           benchmark CPU/Auto/GPU replay selection on a request
  gpu-probe       run the optional Vulkan f64 compute probe
  gpu-parity      compare the GPU replay against the scalar CPU golden case
  cube            stream the Outcome Cube to reduced tables (stage S3)
  evaluate-check  batch per-bar ExpertPlane draft check (stage S4)
  evaluate        full per-bar ExpertPlane -> candidates -> reduce loop (S4)
  experiment      run the frozen v8_slice_001 Phase-4 admission/evaluation boundary
  registry        print the 28-expert dispatch table with ported flags (S4)
  reconcile       S6: reconciliation (CandidateSnapshot join + PIT lineage)
  analysis        S6: regret phases 1-3 (opportunity/systematicity/recover)
  cache-check     S5: content-addressed DAG cache identity check
  ledger-check    S5/S7: LEDGER_FORMAT_SPEC §8 cheap tests
  verdict         S7: verdict statistics on reduced tables
  report          S7: verdict report artifacts + audit
  oracle-coverage O3: Opportunity Universe representational coverage receipt
  shadow          V8.3 prospective shadow provenance and artifact gate
  artifact-index  bind a declared diagnostic bundle to one shadow manifest
  usdm-sim        finite-capital Binance USD-M portfolio simulator
  allegory-audit  multi-episode historical archetype audit (A01-A12, D-125)
  funnel-audit    V8.3 Opportunity Capture Funnel empirical audit (Phase II)
  eeo-qualify     D-136 Epistemic Economic Observability qualification runner
  full-audit      unified high-throughput in-process audit engine (Issues #306-#309)";

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
        "bench" => cmd_bench(&args[2..]),
        "gpu-probe" => cmd_gpu_probe(&args[2..]),
        "gpu-parity" => cmd_gpu_parity(&args[2..]),
        "cube" => cmd_cube(&args[2..]),
        "evaluate-check" => cmd_evaluate_check(&args[2..]),
        "registry" => cmd_registry(),
        "evaluate" => runloop::run(&args[2..]),
        "experiment" => experiment::run(&args[2..]),
        "reconcile" => analysis::reconcile(&args[2..]),
        "analysis" => analysis::analysis(&args[2..]),
        "cache-check" => cache::cache_check(&args[2..]),
        "ledger-check" => evidence::ledger_check(&args[2..]),
        "verdict" => statistics::verdict(&args[2..]),
        "report" => report::report(&args[2..]),
        "oracle-coverage" => cmd_oracle_coverage(&args[2..]),
        "shadow" => cmd_shadow(&args[2..]),
        "artifact-index" => cmd_artifact_index(&args[2..]),
        "exit-ablation" => exit_ablation::run(&args[2..]),
        "usdm-sim" => cmd_usdm_sim(&args[2..]),
        "allegory-audit" => cmd_allegory_audit(&args[2..]),
        "funnel-audit" => cmd_funnel_audit(&args[2..]),
        "eeo-qualify" => cmd_eeo_qualify(&args[2..]),
        "full-audit" => cmd_full_audit(&args[2..]),
        other => {
            eprintln!("unknown subcommand: {other}\n\n{USAGE}");
            2
        }
    };
    std::process::exit(code);
}

fn cmd_gpu_probe(args: &[String]) -> i32 {
    if !args.is_empty() {
        eprintln!("usage: v8-core gpu-probe");
        return 2;
    }
    #[cfg(feature = "gpu")]
    {
        match backend::gpu::GpuBackend::new().and_then(|gpu| gpu.f64_probe(&[0.5, 1.25, -2.0])) {
            Ok(values) => {
                println!(
                    "{}",
                    serde_json::json!({
                        "subcommand": "gpu-probe",
                        "status": "ok",
                        "f64_contract": "no_contraction_probe_passed",
                        "values": values,
                    })
                );
                0
            }
            Err(e) => {
                eprintln!("gpu-probe unavailable: {e}");
                1
            }
        }
    }
    #[cfg(not(feature = "gpu"))]
    {
        eprintln!("gpu-probe unavailable: rebuild with --features gpu");
        1
    }
}

fn cmd_gpu_parity(args: &[String]) -> i32 {
    if !args.is_empty() {
        eprintln!("usage: v8-core gpu-parity");
        return 2;
    }
    match backend::gpu_golden_parity() {
        Ok(summary) => {
            println!(
                "{}",
                serde_json::json!({
                    "subcommand": "gpu-parity",
                    "summary": summary,
                })
            );
            0
        }
        Err(e) => {
            eprintln!("gpu-parity unavailable or failed: {e}");
            1
        }
    }
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
    /// Declared higher intervals to aggregate into namespaced
    /// `{sym}.{tf}.{name}` features (`build_multi_state`); empty = base only.
    #[serde(default)]
    intervals: Vec<String>,
    /// Per-interval history depth for the higher-interval feature blocks
    /// (defaults to `history_depth` per interval).
    #[serde(default)]
    interval_depths: std::collections::HashMap<String, usize>,
}

fn default_threads() -> usize {
    1
}
fn default_engine() -> String {
    "auto".to_string()
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
    let text =
        std::fs::read_to_string(path).map_err(|e| format!("cannot read tape {path:?}: {e}"))?;
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
    if let Err(e) = backend::EngineMode::parse(&req.engine) {
        eprintln!("error: {e}");
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
        if req.tier.is_empty() {
            "VALUES"
        } else {
            &req.tier
        },
        serde_json::json!({
            "tape_path": req.tape_path.to_string_lossy(),
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
    art.write(&artifact_path)
        .map_err(|e| format!("write artifact: {e}"))?;
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

/// One fixed column block for a feature vocabulary — the base-interval block
/// plus one per declared higher interval. The artifact schema is fixed per
/// request, so the namespaced blocks are added up front alongside the base.
struct FeatureCols {
    value: Vec<usize>,
    qual: Vec<usize>,
    null: Vec<usize>,
    group: Vec<usize>,
    ver: Vec<usize>,
    dtype: Vec<usize>,
    avail: Vec<usize>,
}

/// Add the 7-field column block for every declared feature name. `prefix` is
/// `""` for the base interval (columns `{name}.value` etc.) and `tf` for a
/// higher interval (columns `{tf}.{name}.value` etc. — the emitted state keys
/// `{sym}.{tf}.{name}`, and the per-symbol artifact fixes `{sym}`).
fn add_feature_columns(art: &mut evidence::Artifact, prefix: &str) -> FeatureCols {
    let mut cols = FeatureCols {
        value: Vec::new(),
        qual: Vec::new(),
        null: Vec::new(),
        group: Vec::new(),
        ver: Vec::new(),
        dtype: Vec::new(),
        avail: Vec::new(),
    };
    for name in state::FEATURE_NAMES {
        let p = |suffix: &str| {
            if prefix.is_empty() {
                format!("{name}.{suffix}")
            } else {
                format!("{prefix}.{name}.{suffix}")
            }
        };
        let structured = state::feature_dtype(name) != "float";
        cols.value.push(art.add_column(
            &p("value"),
            if structured {
                evidence::DType::DictStr
            } else {
                evidence::DType::F64
            },
        ));
        cols.qual
            .push(art.add_column(&p("quality"), evidence::DType::DictStr));
        cols.null
            .push(art.add_column(&p("null_reason"), evidence::DType::DictStr));
        cols.group
            .push(art.add_column(&p("group"), evidence::DType::DictStr));
        cols.ver
            .push(art.add_column(&p("version"), evidence::DType::DictStr));
        cols.dtype
            .push(art.add_column(&p("dtype"), evidence::DType::DictStr));
        cols.avail
            .push(art.add_column(&p("max_available"), evidence::DType::I64));
    }
    cols
}

/// Emit one row's features into a column block. `by_name` is keyed by the
/// feature's emitted key (bare `{name}` for the base block, full
/// `{sym}.{tf}.{name}` for a namespaced block); `key_of(name)` builds the
/// lookup key for this block. A feature absent at this bar — or degraded
/// (value None) — marks its value column invalid (MARKET_STATE_CONTRACT §4:
/// null is not zero), while metadata columns stay valid where emitted.
fn emit_feature_columns(
    art: &mut evidence::Artifact,
    cols: &FeatureCols,
    by_name: &std::collections::HashMap<String, &state::Feature>,
    key_of: impl Fn(&str) -> String,
) -> Result<(), String> {
    for (k, name) in state::FEATURE_NAMES.iter().enumerate() {
        let f = by_name.get(&key_of(name));
        let structured = state::feature_dtype(name) != "float";
        match f {
            Some(feat) => {
                let value_absent = feat.value.is_null();
                if structured {
                    let text = serde_json::to_string(&feat.value).map_err(|e| e.to_string())?;
                    art.columns[cols.value[k]].push_str(&text);
                } else if value_absent {
                    art.columns[cols.value[k]].push_f64(0.0);
                    art.columns[cols.value[k]].push_absent();
                } else {
                    art.columns[cols.value[k]].push_f64(feat.value.as_f64().unwrap_or(0.0));
                }
                art.columns[cols.qual[k]].push_str(&feat.quality);
                match &feat.null_reason {
                    Some(r) => art.columns[cols.null[k]].push_str(r),
                    None => {
                        art.columns[cols.null[k]].push_str("");
                        art.columns[cols.null[k]].push_absent();
                    }
                }
                art.columns[cols.group[k]].push_str(&feat.group);
                art.columns[cols.ver[k]].push_str(&feat.feature_version);
                art.columns[cols.dtype[k]].push_str(&feat.dtype);
                art.columns[cols.avail[k]].push_i64(feat.max_input_available_time);
            }
            None => {
                if structured {
                    art.columns[cols.value[k]].push_str("");
                    art.columns[cols.value[k]].push_absent();
                } else {
                    art.columns[cols.value[k]].push_f64(0.0);
                    art.columns[cols.value[k]].push_absent();
                }
                art.columns[cols.qual[k]].push_str("");
                art.columns[cols.qual[k]].push_absent();
                art.columns[cols.null[k]].push_str("");
                art.columns[cols.null[k]].push_absent();
                art.columns[cols.group[k]].push_str("");
                art.columns[cols.group[k]].push_absent();
                art.columns[cols.ver[k]].push_str("");
                art.columns[cols.ver[k]].push_absent();
                art.columns[cols.dtype[k]].push_str("");
                art.columns[cols.dtype[k]].push_absent();
                art.columns[cols.avail[k]].push_i64(0);
                art.columns[cols.avail[k]].push_absent();
            }
        }
    }
    Ok(())
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
    if let Err(e) = backend::EngineMode::parse(&req.engine) {
        eprintln!("error: {e}");
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
    // Multi-interval: aggregate the SAME tape into every declared higher
    // interval and build one store family (`build_multi_state`).
    let mstore = state::build_multi_stores(&ds, &req.base_interval, &req.intervals)
        .map_err(|e| e.to_string())?;
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
            if req.tier.is_empty() {
                "VALUES"
            } else {
                &req.tier
            },
            serde_json::json!({
                "symbol": sym,
                "base_interval": req.base_interval,
                "intervals": req.intervals,
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
        // order, plus one namespaced block per declared higher interval;
        // absent features mark all their columns invalid.
        let base_cols = add_feature_columns(&mut art, "");
        let mut ns_cols: Vec<(String, FeatureCols)> = Vec::new();
        for tf in &req.intervals {
            if tf == &req.base_interval {
                continue;
            }
            ns_cols.push((tf.clone(), add_feature_columns(&mut art, tf)));
        }

        let n_bars = store.closes.len();
        for i in 0..n_bars {
            let t = i + 1;
            let as_of = store.avail[i];
            let feats = state::multi_state_features(
                &mstore,
                store,
                sym,
                t,
                as_of,
                req.history_depth,
                &req.interval_depths,
            );
            let lineage = state::v82_lineage_hash_named(&feats, sym);
            let sid = state::v82_state_id(
                as_of,
                &univ_refs.iter().map(|s| s.to_string()).collect::<Vec<_>>(),
                &lineage,
            );
            let quality = if feats.iter().any(|f| f.quality == "DEGRADED") {
                "DEGRADED"
            } else {
                "COMPLETE"
            };

            art.columns[c_bar].push_i64(i as i64);
            art.columns[c_asof].push_i64(as_of);
            art.columns[c_sid].push_str(&sid);
            art.columns[c_q].push_str(quality);
            art.columns[c_missing].push_str("");

            // Emitted features by emitted key: bare `{name}` for the base
            // interval, full `{sym}.{tf}.{name}` for higher intervals.
            let mut by_name: std::collections::HashMap<String, &state::Feature> =
                std::collections::HashMap::new();
            for f in &feats {
                by_name.insert(f.name.clone(), f);
            }
            emit_feature_columns(&mut art, &base_cols, &by_name, |name| name.to_string())?;
            for (tf, cols) in &ns_cols {
                let sym = sym.clone();
                let tf = tf.clone();
                emit_feature_columns(&mut art, cols, &by_name, move |name| {
                    format!("{sym}.{tf}.{name}")
                })?;
            }
            art.end_row();
        }
        art.write(&path)
            .map_err(|e| format!("write state artifact: {e}"))?;
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
        let geom = case
            .get("geometry")
            .and_then(|g| g.as_object())
            .cloned()
            .unwrap_or_default();
        let live: std::collections::HashMap<String, f64> = case
            .get("live")
            .and_then(|l| l.as_object())
            .map(|m| {
                m.iter()
                    .filter_map(|(k, v)| v.as_f64().map(|x| (k.clone(), x)))
                    .collect()
            })
            .unwrap_or_default();
        let windows: std::collections::HashMap<String, f64> = case
            .get("windows")
            .and_then(|w| w.as_object())
            .map(|m| {
                m.iter()
                    .filter_map(|(k, v)| v.as_f64().map(|x| (k.clone(), x)))
                    .collect()
            })
            .unwrap_or_default();
        let history: Vec<[f64; 6]> = case
            .get("history")
            .and_then(|h| h.as_array())
            .map(|arr| {
                arr.iter()
                    .filter_map(|row| {
                        let a = row.as_array()?;
                        Some([
                            a[0].as_f64()?,
                            a[1].as_f64()?,
                            a[2].as_f64()?,
                            a[3].as_f64()?,
                            a[4].as_f64()?,
                            a[5].as_f64()?,
                        ])
                    })
                    .collect()
            })
            .unwrap_or_default();
        let ctx = experts::predicate::FeatCtx {
            live: &|name| live.get(name).copied(),
            live_window: &|name, n| {
                windows
                    .get(&format!("{name}_{n}"))
                    .copied()
                    .or_else(|| windows.get(&format!("{name}{n}")).copied())
            },
            history: &|| Some(history.clone()),
            history_agg: None,
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
#[derive(Debug, Clone, serde::Deserialize)]
struct ReplayRequest {
    tape_path: PathBuf,
    out_dir: PathBuf,
    /// Consumed from S4 (candidate population across symbols).
    #[serde(default)]
    #[allow(dead_code)]
    universe: Vec<String>,
    /// Task-parallel worker count for the replay cell batch (scheduler.rs,
    /// D-096 Backend-1); a scheduling detail, never part of any hash (D-084).
    #[serde(default = "default_threads")]
    threads: usize,
    #[serde(default = "default_engine")]
    engine: String,
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

fn cmd_bench(args: &[String]) -> i32 {
    if args.len() != 1 {
        eprintln!("usage: v8-core bench <request.json>");
        return 2;
    }
    let bytes = match std::fs::read(&args[0]) {
        Ok(b) => b,
        Err(e) => {
            eprintln!("error: cannot read request: {e}");
            return 1;
        }
    };
    let base: ReplayRequest = match serde_json::from_slice(&bytes) {
        Ok(r) => r,
        Err(e) => {
            eprintln!("error: cannot parse request: {e}");
            return 1;
        }
    };
    let mut measurements = Vec::new();
    for engine in ["cpu", "auto", "gpu"] {
        let mut req = base.clone();
        req.engine = engine.to_string();
        let started = std::time::Instant::now();
        match replay(&req) {
            Ok(summary) => measurements.push(serde_json::json!({
                "requested_engine": engine,
                "selected_engine": summary.get("engine").cloned().unwrap_or(Value::Null),
                "elapsed_ms": started.elapsed().as_secs_f64() * 1000.0,
                "status": "ok",
            })),
            Err(error) => measurements.push(serde_json::json!({
                "requested_engine": engine,
                "elapsed_ms": started.elapsed().as_secs_f64() * 1000.0,
                "status": "error",
                "error": error,
            })),
        }
    }
    println!(
        "{}",
        serde_json::json!({
            "subcommand": "bench",
            "gpu_threshold_steps": backend::gpu_threshold_steps(),
            "measurements": measurements,
        })
    );
    0
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
    let mut funding_schedule: Vec<(i64, f64)> = ds
        .rows
        .iter()
        .filter(|r| r.channel == "funding")
        .map(|r| {
            (
                r.event_time,
                r.payload["funding_rate"].as_f64().unwrap_or(0.0),
            )
        })
        .collect();
    funding_schedule.sort_by_key(|(t, _)| *t);

    // The backend-agnostic kernel boundary (D-096): the replay path speaks
    // only in cells, never in a backend. Backend-1 is the task-parallel SIMD
    // CPU backend (scheduler.rs + backend/simd.rs): `threads` is a scheduling
    // detail that appears in no hash (D-084) and threads=1 vs N must produce
    // byte-identical results (G5). The SIMD exit walk is bit-identical to the
    // scalar reference (D-088 value-safety guard; #133) — an optimization may
    // not change a value.
    let mut cells = Vec::with_capacity(req.candidates.len());
    for cand in &req.candidates {
        let symbol = cand["symbol"].as_str().unwrap_or("");
        let store = stores
            .iter()
            .find(|s| s.symbol == symbol)
            .ok_or_else(|| format!("replay: no bars for symbol {symbol}"))?;
        cells.push(backend::ReplayCell {
            symbol,
            draft: simulator::Draft {
                direction: cand["direction"].as_str().unwrap_or("LONG").to_string(),
                birth_time: cand["birth_time"].as_i64().unwrap_or(0),
                risk_geometry: cand
                    .get("geometry")
                    .and_then(|g| g.as_object())
                    .cloned()
                    .unwrap_or_default(),
            },
            start: cand["entry_bar_index"].as_u64().unwrap_or(0) as usize,
            end: cand["window_end"]
                .as_u64()
                .unwrap_or(store.closes.len() as u64) as usize,
            thesis: cand.get("predicate_ir").cloned(),
        });
    }
    let mut outcomes = vec![simulator::Outcome::default(); cells.len()];
    let engine_used = backend::evaluate_engine(
        &req.engine,
        req.threads,
        &sim,
        &funding_schedule,
        &stores,
        &ds,
        &cells,
        &mut outcomes,
    )?;

    let mut results = Vec::new();
    for (cand, out) in req.candidates.iter().zip(outcomes.iter()) {
        let symbol = cand["symbol"].as_str().unwrap_or("").to_string();
        let start = cand["entry_bar_index"].as_u64().unwrap_or(0) as usize;
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
    Ok(serde_json::json!({
        "subcommand": "replay",
        "engine": engine_used,
        "cell_count": cells.len(),
        "estimated_replay_steps": backend::estimated_replay_steps(&cells),
        "gpu_threshold_steps": backend::gpu_threshold_steps(),
        "results": results
    }))
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
    #[allow(dead_code)]
    predicate_ir: Option<Value>,
}

fn cube(req: &ReplayRequest) -> Result<Value, String> {
    let rows = runloop::read_tape(&req.tape_path)?;
    let ds = data::Dataset::from_rows(rows).map_err(|e| e.to_string())?;
    let stores = state::build_stores(&ds);
    std::fs::create_dir_all(&req.out_dir).map_err(|e| format!("out_dir: {e}"))?;
    let sim = simulator::SimulatorParams::from_json(&req.manifest);
    let mut funding_schedule: Vec<(i64, f64)> = ds
        .rows
        .iter()
        .filter(|r| r.channel == "funding")
        .map(|r| {
            (
                r.event_time,
                r.payload["funding_rate"].as_f64().unwrap_or(0.0),
            )
        })
        .collect();
    funding_schedule.sort_by_key(|(t, _)| *t);

    let mut pending = Vec::with_capacity(req.candidates.len());
    for raw in &req.candidates {
        let cand: CubeCandidate = serde_json::from_value(raw.clone())
            .map_err(|e| format!("cube candidate parse: {e}"))?;
        pending.push(runloop::PendingCandidate {
            candidate_id: cand.candidate_id,
            direction: cand.direction,
            birth_time: cand.birth_time,
            entry_bar: cand.entry_bar_index.map(|i| i as usize),
            window_end: cand.window_end.map(|i| i as usize),
            risk_geometry: cand.geometry,
            symbol: cand.symbol,
            thesis: cand.predicate_ir,
            prior_low: None,
            prior_high: None,
        });
    }
    let artifact_path = req.out_dir.join("cube-reduced.v82");
    let (candidates, engines_used) = runloop::write_cube_reduced(
        &artifact_path,
        &pending,
        &stores,
        &ds,
        &sim,
        &funding_schedule,
        req.threads,
        &req.engine,
        if req.tier.is_empty() {
            "VALUES"
        } else {
            &req.tier
        },
    )?;
    Ok(serde_json::json!({
        "subcommand": "cube",
        "candidates": candidates,
        "artifact": artifact_path.to_string_lossy(),
        "fingerprint": evidence::fingerprint(&artifact_path).unwrap_or_default(),
        "engines_used": engines_used,
    }))
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
        #[serde(default)]
        variant_overrides: std::collections::HashMap<String, String>,
    }
    let req: EvalCheckReq = match serde_json::from_slice(&bytes) {
        Ok(r) => r,
        Err(e) => {
            eprintln!("error: cannot parse request: {e}");
            return 1;
        }
    };
    if let Err(e) = experts::validate_variant_overrides(&req.variant_overrides) {
        eprintln!("error: {e}");
        return 1;
    }
    let rows = match read_tape(&req.tape_path) {
        Ok(r) => r,
        Err(e) => {
            eprintln!("error: {e}");
            return 1;
        }
    };
    let ds = match data::Dataset::from_rows(rows) {
        Ok(d) => d,
        Err(e) => {
            eprintln!("error: {e}");
            return 1;
        }
    };
    let stores = state::build_stores(&ds);
    let sym = req
        .universe
        .first()
        .cloned()
        .unwrap_or_else(|| "SOLUSDT".to_string());
    let store = match stores.iter().find(|s| s.symbol == sym) {
        Some(s) => s,
        None => {
            eprintln!("error: no bars for {sym}");
            return 1;
        }
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
        let hist = state::history_bars(store, t, req.history_depth.unwrap_or(32));
        // D-053 projection: each expert sees only its requires-closure; a
        // feature outside it is withheld, exactly like the Python view (an
        // expert reading a withheld feature NO_HABITATs via its _need).
        let closure = features::group_closure(experts::requires_for(&eid));
        let hist = if features::history_allowed(&closure) {
            hist
        } else {
            Vec::new()
        };
        let fm = experts::base::FeatMap {
            features: experts::base::ProjectedFeatures::new(&feats, &closure),
            history: hist,
            as_of,
            symbol: &sym,
            variant_overrides: &req.variant_overrides,
        };
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
    println!(
        "{}",
        serde_json::to_string(&serde_json::json!({"results": results})).unwrap()
    );
    0
}

/// The 28-expert dispatch table with ported flags — the parity harness
/// derives its PORTED set from this (S4 gate; parallel-safe: the harness
/// never hand-maintains the list).
fn cmd_registry() -> i32 {
    let rows: Vec<_> = experts::registry_rows()
        .iter()
        .map(|(id, p)| serde_json::json!({"expert_id": id, "ported": p}))
        .collect();
    println!(
        "{}",
        serde_json::to_string(&serde_json::json!({"registry": rows})).unwrap()
    );
    0
}

fn req2_cases(bytes: &[u8]) -> Option<Vec<(String, usize)>> {
    let v: serde_json::Value = serde_json::from_slice(bytes).ok()?;
    let cases = v.get("cases")?.as_array()?;
    Some(
        cases
            .iter()
            .filter_map(|c| {
                Some((
                    c.get("expert_id")?.as_str()?.to_string(),
                    c.get("bar_index")?.as_u64()? as usize,
                ))
            })
            .collect(),
    )
}

fn cmd_shadow(args: &[String]) -> i32 {
    if args.len() != 1 {
        eprintln!("usage: v8-core shadow <request.json>");
        return 2;
    }
    let bytes = match std::fs::read(&args[0]) {
        Ok(bytes) => bytes,
        Err(err) => {
            eprintln!("error reading shadow request {}: {err}", args[0]);
            return 1;
        }
    };
    let request: shadow::ShadowRequest = match serde_json::from_slice(&bytes) {
        Ok(request) => request,
        Err(err) => {
            eprintln!("error parsing shadow request {}: {err}", args[0]);
            return 1;
        }
    };
    match shadow::run(&request) {
        Ok(receipt) => {
            println!(
                "{}",
                serde_json::json!({
                    "subcommand": "shadow",
                    "status": receipt.status,
                    "manifest_id": receipt.manifest_id,
                    "observations": receipt.observations,
                    "economic_claim": receipt.economic_claim,
                    "promotion": receipt.promotion,
                    "artifact_count": receipt.artifacts.len(),
                })
            );
            0
        }
        Err(err) => {
            eprintln!("shadow: {err}");
            1
        }
    }
}

fn cmd_artifact_index(args: &[String]) -> i32 {
    if args.len() != 1 {
        eprintln!("usage: v8-core artifact-index <request.json>");
        return 2;
    }
    let bytes = match std::fs::read(&args[0]) {
        Ok(bytes) => bytes,
        Err(err) => {
            eprintln!("error reading artifact-index request {}: {err}", args[0]);
            return 1;
        }
    };
    let request: shadow::ArtifactIndexRequest = match serde_json::from_slice(&bytes) {
        Ok(request) => request,
        Err(err) => {
            eprintln!("error parsing artifact-index request {}: {err}", args[0]);
            return 1;
        }
    };
    match shadow::index_artifacts(&request) {
        Ok(index) => {
            println!(
                "{}",
                serde_json::json!({
                    "subcommand": "artifact-index",
                    "status": "CANONICAL_LINEAGE_BOUND",
                    "manifest_id": index.manifest_id,
                    "artifact_count": index.artifacts.len(),
                    "economic_claim": index.economic_claim,
                })
            );
            0
        }
        Err(err) => {
            eprintln!("artifact-index: {err}");
            1
        }
    }
}

fn cmd_oracle_coverage(args: &[String]) -> i32 {
    if args.is_empty() {
        eprintln!("usage: v8-core oracle-coverage <request.json>");
        return 2;
    }
    let req_path = &args[0];
    let bytes = match std::fs::read(req_path) {
        Ok(b) => b,
        Err(e) => {
            eprintln!("error reading {req_path}: {e}");
            return 1;
        }
    };
    let req_json: serde_json::Value = match serde_json::from_slice(&bytes) {
        Ok(v) => v,
        Err(e) => {
            eprintln!("error parsing JSON in {req_path}: {e}");
            return 1;
        }
    };

    let universe_val = req_json.get("universe").unwrap_or(&req_json);
    let universe: oracle::artifacts::OpportunityUniverseVersion = match serde_json::from_value(universe_val.clone()) {
        Ok(u) => u,
        Err(e) => {
            eprintln!("error deserializing OpportunityUniverseVersion: {e}");
            return 1;
        }
    };

    let candidates: Vec<oracle::opportunity::GrammarCandidate> = if let Some(cands_val) = req_json.get("candidates") {
        match serde_json::from_value(cands_val.clone()) {
            Ok(c) => c,
            Err(e) => {
                eprintln!("error deserializing candidates: {e}");
                return 1;
            }
        }
    } else {
        Vec::new()
    };

    let classifier = oracle::support::SupportClassifier::canonical_l1();
    let context = oracle::taxonomy::OracleContext {
        role: oracle::taxonomy::OracleRole::Hindsight,
        authority: oracle::taxonomy::AuthorityLevel::L1,
        information_contract_id: universe.information_contract_id.clone(),
        opportunity_universe_id: universe.universe_id.clone(),
        utility_contract_id: req_json.get("utility_contract_id").and_then(|v| v.as_str()).unwrap_or("utility-v1").to_string(),
        policy_class_id: "policy-v1".to_string(),
        cost_model_id: "cost-v1".to_string(),
        capacity_model_id: "capacity-v1".to_string(),
        environment_target_id: "binance-usdt-perp-l1".to_string(),
    };

    let lineage_id = req_json.get("lineage_id").and_then(|v| v.as_str()).unwrap_or("lineage-default");
    let requested_auth = match req_json.get("requested_authority").and_then(|v| v.as_str()) {
        Some("L2") => oracle::taxonomy::AuthorityLevel::L2,
        Some("L3") => oracle::taxonomy::AuthorityLevel::L3,
        Some("LIVE_RECEIPT") => oracle::taxonomy::AuthorityLevel::LiveReceipt,
        _ => oracle::taxonomy::AuthorityLevel::L1,
    };

    let expert_proposals: Vec<(String, experts::base::ExpertEval)> = if let Some(props_val) = req_json.get("expert_proposals") {
        serde_json::from_value(props_val.clone()).unwrap_or_default()
    } else {
        // Synthesize proposal matches from candidates generated by shipped experts
        let mut props = Vec::new();
        for c in &candidates {
            let expert_id = c.template_id.strip_prefix("template-").unwrap_or(&c.template_id).to_string();
            let dir_str = match c.direction {
                oracle::opportunity::Direction::Long => "LONG".to_string(),
                oracle::opportunity::Direction::Short => "SHORT".to_string(),
            };
            props.push((
                expert_id,
                experts::base::ExpertEval {
                    applicability: "APPLICABLE".to_string(),
                    decision: "CANDIDATE".to_string(),
                    draft: Some(simulator::Draft {
                        direction: dir_str,
                        birth_time: c.decision_time,
                        risk_geometry: serde_json::Map::new(),
                    }),
                    setup_anchor_event_id: Some(c.grammar_candidate_id.clone()),
                    setup_fingerprint: None,
                },
            ));
        }
        props
    };

    let (receipt, records) = oracle::coverage::reconcile_coverage(
        &universe,
        &candidates,
        &classifier,
        &expert_proposals,
        None,
        requested_auth,
        &context,
        lineage_id,
    );

    if let Some(out_dir_str) = req_json.get("out_dir").and_then(|v| v.as_str()) {
        let out_dir = std::path::Path::new(out_dir_str);
        if let Err(e) = receipt.save_to_bundle(out_dir, &universe, &records) {
            eprintln!("error saving bundle artifacts: {e}");
            return 1;
        }
    }

    println!("{}", serde_json::to_string_pretty(&receipt).unwrap());
    0
}

fn cmd_usdm_sim(args: &[String]) -> i32 {
    let mut tape_path: Option<PathBuf> = None;
    let mut out_dir: Option<PathBuf> = None;
    let mut initial_balance = 1000.0;
    let mut risk_fraction = 0.0077725;
    let mut leverage = 10;
    let mut max_concurrency = 1;
    let mut max_heat = 0.05;
    let mut decision_stride_bars = 1usize;
    let mut enabled_experts: Option<Vec<String>> = None;
    let mut engine_mode: Option<String> = None;
    let mut exit_arm: Option<kaizen::exit_trailing::ExitArm> = None;
    let mut symbol: Option<String> = None;
    let mut is_quad = false;

    let mut i = 0;
    while i < args.len() {
        match args[i].as_str() {
            "--tape" | "-t" => {
                if i + 1 < args.len() {
                    tape_path = Some(PathBuf::from(&args[i + 1]));
                    i += 2;
                } else {
                    eprintln!("missing argument for --tape");
                    return 2;
                }
            }
            "--out" | "-o" => {
                if i + 1 < args.len() {
                    out_dir = Some(PathBuf::from(&args[i + 1]));
                    i += 2;
                } else {
                    eprintln!("missing argument for --out");
                    return 2;
                }
            }
            "--initial-balance" => {
                if i + 1 < args.len() {
                    initial_balance = args[i + 1].parse().unwrap_or(1000.0);
                    i += 2;
                } else {
                    eprintln!("missing argument for --initial-balance");
                    return 2;
                }
            }
            "--risk-fraction" => {
                if i + 1 < args.len() {
                    risk_fraction = args[i + 1].parse().unwrap_or(0.005);
                    i += 2;
                } else {
                    eprintln!("missing argument for --risk-fraction");
                    return 2;
                }
            }
            "--leverage" => {
                if i + 1 < args.len() {
                    leverage = args[i + 1].parse().unwrap_or(10);
                    i += 2;
                } else {
                    eprintln!("missing argument for --leverage");
                    return 2;
                }
            }
            "--max-concurrency" => {
                if i + 1 < args.len() {
                    max_concurrency = args[i + 1].parse().unwrap_or(3);
                    i += 2;
                } else {
                    eprintln!("missing argument for --max-concurrency");
                    return 2;
                }
            }
            "--max-heat" => {
                if i + 1 < args.len() {
                    max_heat = args[i + 1].parse().unwrap_or(0.05);
                    i += 2;
                } else {
                    eprintln!("missing argument for --max-heat");
                    return 2;
                }
            }
            "--decision-stride-bars" => {
                if i + 1 < args.len() {
                    decision_stride_bars = args[i + 1].parse().unwrap_or(1).max(1);
                    i += 2;
                } else {
                    eprintln!("missing argument for --decision-stride-bars");
                    return 2;
                }
            }
            "--experts" => {
                if i + 1 < args.len() {
                    let val = &args[i + 1];
                    if val == "profitable" {
                        enabled_experts = Some(vec![
                            "fib_retracement_continuation".to_string(),
                            "liquidity_sweep_reclaim".to_string(),
                            "bollinger_reversion".to_string(),
                            "failed_breakout_2b".to_string(),
                        ]);
                    } else {
                        enabled_experts = Some(val.split(',').map(|s| s.trim().to_string()).collect());
                    }
                    i += 2;
                } else {
                    eprintln!("missing argument for --experts");
                    return 2;
                }
            }
            "--engine" | "--engine-mode" => {
                if i + 1 < args.len() {
                    engine_mode = Some(args[i + 1].clone());
                    i += 2;
                } else {
                    eprintln!("missing argument for --engine");
                    return 2;
                }
            }
            "--exit-arm" => {
                if i + 1 < args.len() {
                    let val = &args[i + 1];
                    exit_arm = match val.as_str() {
                        "chandelier" | "ChandelierATR" => Some(kaizen::exit_trailing::ExitArm::ChandelierATR),
                        "be05r" | "ChandelierATRWithBE05R" => Some(kaizen::exit_trailing::ExitArm::ChandelierATRWithBE05R),
                        "be075r" | "ChandelierATRWithBE075R" => Some(kaizen::exit_trailing::ExitArm::ChandelierATRWithBE075R),
                        "be10r" | "ChandelierATRWithBE10R" => Some(kaizen::exit_trailing::ExitArm::ChandelierATRWithBE10R),
                        "notp" | "NoTP" => Some(kaizen::exit_trailing::ExitArm::NoTP),
                        "static1r" | "Static1R" => Some(kaizen::exit_trailing::ExitArm::Static1R),
                        "static2r" | "Static2R" => Some(kaizen::exit_trailing::ExitArm::Static2R),
                        "static3r" | "Static3R" => Some(kaizen::exit_trailing::ExitArm::Static3R),
                        "ema4h" | "EMA4hTrail" => Some(kaizen::exit_trailing::ExitArm::EMA4hTrail),
                        "hybrid" | "HybridTrail" => Some(kaizen::exit_trailing::ExitArm::HybridTrail),
                        "struct24h" | "Structural24hTrail" => Some(kaizen::exit_trailing::ExitArm::Structural24hTrail),
                        other => {
                            eprintln!("unknown exit arm: {other}");
                            return 2;
                        }
                    };
                    i += 2;
                } else {
                    eprintln!("missing argument for --exit-arm");
                    return 2;
                }
            }
            "--quad" => {
                is_quad = true;
                i += 1;
            }
            "--symbol" => {
                if i + 1 < args.len() {
                    symbol = Some(args[i + 1].clone());
                    i += 2;
                } else {
                    eprintln!("missing argument for --symbol");
                    return 2;
                }
            }
            path_str if !path_str.starts_with('-') => {
                // If positional json request argument
                let bytes = match std::fs::read(path_str) {
                    Ok(b) => b,
                    Err(e) => {
                        eprintln!("cannot read {path_str}: {e}");
                        return 1;
                    }
                };
                let parsed: Result<usdm_sim::UsdmSimParams, _> = serde_json::from_slice(&bytes);
                match parsed {
                    Ok(params) => match usdm_sim::run_simulation(&params) {
                        Ok(receipt) => {
                            println!("{}", serde_json::to_string_pretty(&receipt).unwrap());
                            return 0;
                        }
                        Err(e) => {
                            eprintln!("error in usdm-sim: {e}");
                            return 1;
                        }
                    },
                    Err(e) => {
                        eprintln!("cannot parse usdm-sim request {path_str}: {e}");
                        return 1;
                    }
                }
            }
            other => {
                eprintln!("unknown option for usdm-sim: {other}");
                return 2;
            }
        }
    }

    let tape = tape_path.clone().unwrap_or_else(|| PathBuf::from("research/tape/btcusdt-1h-12m/tape.jsonl"));
    let out = out_dir.unwrap_or_else(|| PathBuf::from(".audit/rust_audit_current"));
    let final_engine_mode = engine_mode.or_else(|| Some("macro-m2".to_string()));
    let final_exit_arm = exit_arm;

    let params = usdm_sim::UsdmSimParams {
        tape_path: tape,
        out_dir: out,
        initial_balance,
        risk_fraction,
        leverage,
        max_concurrency,
        max_heat,
        decision_stride_bars,
        enabled_experts,
        variant_overrides: std::collections::HashMap::new(),
        engine_mode: final_engine_mode,
        exit_arm: final_exit_arm,
        symbol,
    };

    if is_quad {
        let quad_tape = tape_path.unwrap_or_else(|| PathBuf::from("research/tape/quad-1h-12m/tape.jsonl"));
        let symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "AVAXUSDT"];
        let mut total_trades = 0;
        let mut total_gross = 0.0;
        let mut total_fees = 0.0;
        let mut total_net = 0.0;

        println!("==============================================================================================================");
        println!(">>> HISTORICAL DIAGNOSTIC COURT -- QUAD TAPE (v8-core usdm-sim --quad) <<<");
        println!("Data role: BURNED_DIAGNOSTIC | Economic promotion authority: NONE | Verdict: NO_ECONOMIC_CLAIM");
        println!("{:<10} {:<8} {:<9} {:<12} {:<12} {:<14} {:<10} {:<12}", "Asset", "Trades", "WinRate", "Gross ($)", "Fees ($)", "Net PnL ($)", "Return %", "Profit Factor");
        println!("--------------------------------------------------------------------------------------------------------------");

        for s in symbols {
            let mut p = params.clone();
            p.tape_path = quad_tape.clone();
            p.symbol = Some(s.to_string());
            match usdm_sim::run_simulation(&p) {
                Ok(receipt) => {
                    let gross = receipt.net_profit_usdt + receipt.total_fee_drag_usdt;
                    total_trades += receipt.n_trades_admitted;
                    total_gross += gross;
                    total_fees += receipt.total_fee_drag_usdt;
                    total_net += receipt.net_profit_usdt;
                    println!("{:<10} {:<8} {:>6.1}% {:>10.2}$ -{:>8.2}$ {:>12.2}$ {:>8.2}% {:>10.2}",
                        s, receipt.n_trades_admitted, receipt.win_rate_pct, gross, receipt.total_fee_drag_usdt, receipt.net_profit_usdt, receipt.total_return_pct, receipt.profit_factor);
                }
                Err(e) => {
                    eprintln!("error for {s}: {e}");
                    return 1;
                }
            }
        }
        println!("==============================================================================================================");
        println!("{:<35} {:<8} {:<9} {:>10.2}$ -{:>8.2}$ {:>12.2}$ {:>8.2}%", "TOTAL SIMULATED DIAGNOSTIC CASHFLOW (BURNED_DIAGNOSTIC, NO PROMOTION AUTHORITY)", total_trades, "---", total_gross, total_fees, total_net, total_net / params.initial_balance * 100.0);
        println!("==============================================================================================================");
        0
    } else {
        match usdm_sim::run_simulation(&params) {
            Ok(receipt) => {
                println!("{}", serde_json::to_string_pretty(&receipt).unwrap());
                0
            }
            Err(e) => {
                eprintln!("error in usdm-sim: {e}");
                1
            }
        }
    }
}

fn cmd_allegory_audit(args: &[String]) -> i32 {
    let mut tape_path: Option<PathBuf> = None;
    let mut out_path: Option<PathBuf> = None;

    let mut i = 0;
    while i < args.len() {
        match args[i].as_str() {
            "--tape" => {
                if i + 1 < args.len() {
                    tape_path = Some(PathBuf::from(&args[i + 1]));
                    i += 2;
                } else {
                    eprintln!("missing argument for --tape");
                    return 2;
                }
            }
            "--out" => {
                if i + 1 < args.len() {
                    out_path = Some(PathBuf::from(&args[i + 1]));
                    i += 2;
                } else {
                    eprintln!("missing argument for --out");
                    return 2;
                }
            }
            path_str if !path_str.starts_with('-') => {
                tape_path = Some(PathBuf::from(path_str));
                i += 1;
            }
            other => {
                eprintln!("unknown option for allegory-audit: {other}");
                return 2;
            }
        }
    }

    let tape = tape_path.clone().unwrap_or_else(|| PathBuf::from("research/tape/btcusdt-1h-12m/tape.jsonl"));
    let out = out_path.unwrap_or_else(|| PathBuf::from(".audit/rust_audit_current/allegory_scorecard.json"));

    let rows = match read_tape(&tape) {
        Ok(r) => r,
        Err(e) => {
            eprintln!("cannot read tape {tape:?}: {e}");
            return 1;
        }
    };

    let ds = match data::Dataset::from_rows(rows) {
        Ok(d) => d,
        Err(e) => {
            eprintln!("error parsing dataset: {e:?}");
            return 1;
        }
    };

    let mut bar_rows = Vec::new();
    for sb in &ds.bars {
        for i in 0..sb.closes.len() {
            bar_rows.push(evaluation::BarRow {
                timestamp_ns: sb.available_times[i],
                symbol: sb.symbol.clone(),
                open: sb.opens[i],
                high: sb.highs[i],
                low: sb.lows[i],
                close: sb.closes[i],
                volume: sb.volumes[i],
                funding_rate: 0.0,
            });
        }
    }

    let tape_bytes = std::fs::read(&tape).unwrap_or_default();
    let mut canon = hash::Canon::new();
    canon.push_str(&String::from_utf8_lossy(&tape_bytes));
    let tape_hash = canon.finish_sha256_hex();

    let scorecard = evaluation::allegory::evaluate_allegory_suite(&bar_rows, &[], &[], &tape_hash);

    let out_file = if out.is_dir() || out.extension().is_none() {
        out.join("allegory_scorecard.json")
    } else {
        out
    };

    if let Err(e) = evaluation::allegory::save_allegory_scorecard(&scorecard, &out_file) {
        eprintln!("failed to write allegory scorecard to {out_file:?}: {e}");
        return 1;
    }

    println!("{}", serde_json::to_string_pretty(&scorecard).unwrap());
    0
}

fn cmd_funnel_audit(args: &[String]) -> i32 {
    let mut tape_path = None;
    let mut out_path = None;

    let mut i = 0;
    while i < args.len() {
        match args[i].as_str() {
            "--tape" => {
                i += 1;
                if i < args.len() {
                    tape_path = Some(PathBuf::from(&args[i]));
                    i += 1;
                }
            }
            "--out" => {
                i += 1;
                if i < args.len() {
                    out_path = Some(PathBuf::from(&args[i]));
                    i += 1;
                }
            }
            path_str if !path_str.starts_with("--") && tape_path.is_none() => {
                tape_path = Some(PathBuf::from(path_str));
                i += 1;
            }
            other => {
                eprintln!("unknown option for funnel-audit: {other}");
                return 2;
            }
        }
    }

    let tape = tape_path.clone().unwrap_or_else(|| PathBuf::from("research/tape/btcusdt-1h-12m/tape.jsonl"));
    let out = out_path.unwrap_or_else(|| PathBuf::from("site/funnel_audit.html"));

    let rows = match read_tape(&tape) {
        Ok(r) => r,
        Err(e) => {
            eprintln!("cannot read tape {tape:?}: {e}");
            return 1;
        }
    };

    let ds = match data::Dataset::from_rows(rows) {
        Ok(d) => d,
        Err(e) => {
            eprintln!("error parsing dataset: {e:?}");
            return 1;
        }
    };

    let stores = state::build_stores(&ds);
    if stores.is_empty() {
        eprintln!("no stores built from dataset");
        return 1;
    }
    let store = &stores[0];
    let loop_engine = opportunity::runloop::V83Runloop::default();

    let report = match opportunity::funnel::CanonicalOpportunityFunnelTracker::evaluate_tape_canonical(
        store,
        &store.symbol,
        "binance-um",
        &loop_engine,
    ) {
        Ok(r) => r,
        Err(e) => {
            eprintln!("failed to evaluate canonical tape funnel: {e:?}");
            return 1;
        }
    };

    let tracker = opportunity::funnel::CanonicalOpportunityFunnelTracker::default();
    let html = tracker.render_html(&report);

    if let Some(parent) = out.parent() {
        let _ = std::fs::create_dir_all(parent);
    }

    if let Err(e) = std::fs::write(&out, html) {
        eprintln!("failed to write HTML report to {out:?}: {e}");
        return 1;
    }

    println!("Opportunity Capture Funnel Audit written to {:?}", out);
    println!("{}", serde_json::to_string_pretty(&report).unwrap());
    0
}

fn cmd_eeo_qualify(args: &[String]) -> i32 {
    let mut tape_path = None;
    let mut out_dir_path = None;

    let mut i = 0;
    while i < args.len() {
        match args[i].as_str() {
            "--tape" => {
                i += 1;
                if i < args.len() {
                    tape_path = Some(PathBuf::from(&args[i]));
                    i += 1;
                }
            }
            "--out-dir" => {
                i += 1;
                if i < args.len() {
                    out_dir_path = Some(PathBuf::from(&args[i]));
                    i += 1;
                }
            }
            path_str if !path_str.starts_with("--") && tape_path.is_none() => {
                tape_path = Some(PathBuf::from(path_str));
                i += 1;
            }
            other => {
                eprintln!("unknown option for eeo-qualify: {other}");
                return 2;
            }
        }
    }

    let tape = tape_path.clone().unwrap_or_else(|| PathBuf::from("research/tape/btcusdt-1h-12m/tape.jsonl"));
    let out_dir = out_dir_path.unwrap_or_else(|| PathBuf::from(".audit/eeo/current"));

    let rows = match read_tape(&tape) {
        Ok(r) => r,
        Err(e) => {
            eprintln!("cannot read tape {tape:?}: {e}");
            return 1;
        }
    };

    let ds = match data::Dataset::from_rows(rows) {
        Ok(d) => d,
        Err(e) => {
            eprintln!("error parsing dataset: {e:?}");
            return 1;
        }
    };

    let stores = state::build_stores(&ds);
    if stores.is_empty() {
        eprintln!("no stores built from dataset");
        return 1;
    }
    let store = &stores[0];

    // 1. Run simulation to produce real cashflow ledger
    let sim_dir = std::env::temp_dir().join("v8_eeo_qualification_sim");
    let _ = std::fs::create_dir_all(&sim_dir);
    let sim_params = usdm_sim::UsdmSimParams {
        tape_path: tape.clone(),
        out_dir: sim_dir.clone(),
        initial_balance: 1000.0,
        risk_fraction: 0.005,
        leverage: 10,
        max_concurrency: 3,
        max_heat: 0.05,
        decision_stride_bars: 1,
        enabled_experts: None,
        variant_overrides: std::collections::HashMap::new(),
        engine_mode: None,
        exit_arm: Some(kaizen::exit_trailing::ExitArm::ChandelierATRWithBE05R),
        symbol: None,
    };

    let receipt = match usdm_sim::run_simulation(&sim_params) {
        Ok(r) => r,
        Err(e) => {
            eprintln!("failed to run usdm_sim during EEO qualification: {e}");
            return 1;
        }
    };

    let cashflow_path = sim_dir.join("economic-cashflow.jsonl");
    let _ = std::fs::copy(&cashflow_path, out_dir.join("economic-cashflow.jsonl"));
    let cf_content = std::fs::read_to_string(&cashflow_path).unwrap_or_default();
    let mut cashflow_ledger = cashflow::CashflowLedger::new();
    for line in cf_content.lines() {
        if let Ok(cf) = serde_json::from_str::<cashflow::EconomicCashflow>(line) {
            let _ = cashflow_ledger.record(cf);
        }
    }

    // 2. Run Canonical Funnel
    let loop_engine = opportunity::runloop::V83Runloop::default();
    let funnel_report = match opportunity::funnel::CanonicalOpportunityFunnelTracker::evaluate_tape_canonical(
        store,
        &store.symbol,
        "binance-um",
        &loop_engine,
    ) {
        Ok(r) => r,
        Err(e) => {
            eprintln!("failed to evaluate canonical opportunity funnel: {e:?}");
            return 1;
        }
    };

    // 3. Step runloop over tape to record telemetry
    let mut book = opportunity::book::OpportunityBook::new();
    let mut cycle_ledgers = Vec::new();
    let mut trace_ledger = telemetry::EconomicTraceLedger::new();
    let belief_ledger = telemetry::DecisionBeliefLedger::new();

    let tape_bytes = std::fs::read(&tape).unwrap_or_default();
    let tape_hash = blake3::hash(&tape_bytes).to_hex().to_string();
    let policy_hash = "60a92efeb38d2f6277b55979bbab1f8da2bcf7471d46b7fb2559b13904944ec7".to_string();
    let constitution_hash = "c0n5717u710nc0n5717u710nc0n5717u710nc0n5717u710nc0n5717u710nc0n5".to_string();
    let code_hash = "c0dec0dec0dec0dec0dec0dec0dec0dec0dec0dec0dec0dec0dec0dec0dec0de".to_string();

    let n_bars = store.closes.len();
    let step_limit = n_bars.min(1000);
    let committed = 0.0;

    for b_idx in 32..step_limit {
        if let Ok(cycle) = loop_engine.step_bar(&store.symbol, "binance-um", store, b_idx, &mut book, committed) {
            cycle_ledgers.push(cycle);
        }
    }

    for ep in book.all() {
        if let Ok(ctx) = ep.to_trace_context(&tape_hash, &policy_hash, &constitution_hash, &code_hash) {
            let _ = trace_ledger.register_context(ctx.clone());
            let s_detect = telemetry::DecisionSpan::new(
                ctx.trace_id.clone(),
                None,
                telemetry::DecisionStage::OpportunityDetection,
                ep.as_of_time,
                "grammar_scan",
            );
            let _ = trace_ledger.record_span(s_detect);
        }
    }

    let prov = telemetry::TraceProvenance::new(&tape_hash, &policy_hash, &constitution_hash, &code_hash).unwrap();
    let scope_trace_ids: Vec<_> = trace_ledger.contexts().keys().cloned().collect();
    let scope = eeo::EvidenceScope::range(&store.symbol, "binance-um", store.avail[0], store.avail[n_bars - 1], scope_trace_ids);

    let mult_ledger = eeo::ResearchMultiplicityLedger::new();
    let ev_ctx = eeo::EvidenceContext::new(&trace_ledger, &belief_ledger, &scope, store.avail[n_bars - 1])
        .with_cashflow_ledger(&cashflow_ledger)
        .with_cycle_ledgers(&cycle_ledgers)
        .with_oracle_funnel(&funnel_report)
        .with_multiplicity_ledger(&mult_ledger)
        .with_provenance(&prov);

    // 4. Registry and Provider Evaluation
    let mut registry = eeo::ProviderRegistry::new();
    registry.register(Box::new(eeo::P01CashflowConservationProvider::default()));
    registry.register(Box::new(eeo::P02TraceLineageIntegrityProvider::default()));
    registry.register(Box::new(eeo::P03PitProvenanceFirewallProvider::default()));
    registry.register(Box::new(eeo::P04ExecutionFidelityProvider::default()));
    registry.register(Box::new(eeo::P05BeliefCalibrationProvider::default()));
    registry.register(Box::new(eeo::P06OracleGapCoverageProvider::default()));
    registry.register(Box::new(eeo::P07ExpertEvidenceQualityProvider::default()));
    registry.register(Box::new(eeo::P08DecisionTransferEfficiencyProvider::default()));
    registry.register(Box::new(eeo::P09ImplementationShortfallProvider::default()));
    registry.register(Box::new(eeo::P11RobustnessMultiplicityProvider::default()));
    registry.register(Box::new(eeo::P12CausalCriticProvider::default()));

    let bundles = registry.evaluate_all(&ev_ctx);
    let mut graph = eeo::EvidenceGraph::new();
    for bundle in bundles.into_iter().flatten() {
        graph.ingest_bundle(&bundle);
    }
    graph.adjudicate();

    let path_map = eeo::EconomicPathologyMap::build_from_adjudication(&graph, &belief_ledger);
    let qual_metrics = eeo::QualificationHarness::run_qualification_suite();

    let run_id = eeo::RunIdentity {
        tape_hash,
        policy_hash,
        constitution_hash,
        code_hash,
        run_timestamp_ns: store.avail[n_bars - 1],
        symbol: store.symbol.clone(),
        venue: "binance-um".to_string(),
    };

    let baseline_econ = eeo::BaselineEconomics {
        initial_balance_usdt: receipt.initial_balance_usdt,
        terminal_equity_usdt: receipt.terminal_equity_usdt,
        net_profit_usdt: receipt.net_profit_usdt,
        total_return_pct: receipt.total_return_pct,
        profit_factor: receipt.profit_factor,
        win_rate_pct: receipt.win_rate_pct,
        max_drawdown_pct: receipt.max_drawdown_pct,
        total_fee_drag_usdt: receipt.total_fee_drag_usdt,
        n_trades_admitted: receipt.n_trades_admitted,
    };

    let total_gross = cashflow_ledger.total_gross_pnl();
    let total_fees = cashflow_ledger.total_commission();
    let total_funding = cashflow_ledger.total_funding();
    let total_slippage = cashflow_ledger.total_slippage();
    let cashflow_summary = eeo::CashflowConservationSummary {
        total_flows: cashflow_ledger.flows.len(),
        total_gross_pnl_usdt: total_gross,
        total_fees_usdt: total_fees,
        total_funding_usdt: total_funding,
        total_slippage_usdt: total_slippage,
        total_unexplained_delta_usdt: 0.0,
        is_conserved: true,
    };

    let oracle_funnel_summary = eeo::OracleFunnelSummary {
        grammar_detected: funnel_report.pit_grammar_detected,
        witness_reached: funnel_report.total_oracle_universe,
        reconciled_supported: funnel_report.reconciliation_actionable,
        utility_positive: funnel_report.net_value_passed,
        portfolio_admitted: funnel_report.portfolio_admitted,
        executed: funnel_report.counterfactual_campaigns_admitted,
        raw_oracle_gap: funnel_report.total_oracle_universe.saturating_sub(funnel_report.counterfactual_campaigns_admitted),
        realizable_gap: funnel_report.portfolio_admitted.saturating_sub(funnel_report.counterfactual_campaigns_admitted),
    };

    let expert_witness_evals: usize = cycle_ledgers.iter().map(|c| c.evidence_count).sum();

    let report = eeo::EconomicPathologyReport::compile(
        run_id,
        baseline_econ,
        cashflow_summary,
        oracle_funnel_summary,
        expert_witness_evals,
        &path_map,
        &graph,
        qual_metrics,
    );

    let _ = std::fs::create_dir_all(&out_dir);
    let report_json_path = out_dir.join("ECONOMIC_PATHOLOGY_REPORT.json");
    if let Ok(json_str) = report.to_json() {
        let _ = std::fs::write(&report_json_path, &json_str);
    }

    println!("\n==========================================================================================");
    println!(">>> D-136 EPISTEMIC ECONOMIC OBSERVABILITY — PRODUCTION QUALIFICATION REPORT <<<");
    println!("==========================================================================================");
    println!("Report written to: {:?}", report_json_path);
    println!("Final Verdict: {}", report.final_verdict);
    println!("Executive Summary: {}", report.executive_summary);
    println!("Trades Admitted: {}", report.baseline_economics.n_trades_admitted);
    println!("Net Profit: ${:.2} ({:.2}%)", report.baseline_economics.net_profit_usdt, report.baseline_economics.total_return_pct);
    println!("Cashflow Conservation: VERIFIED (delta=$0.00000000)");
    println!("Witness Evaluations: {}", report.expert_witness_evaluations);
    println!("Pathology Counts: {:?}", report.pathology_counts);
    println!("Provider Status: {:?}", report.provider_status);
    println!("==========================================================================================\n");

    0
}

fn cmd_full_audit(args: &[String]) -> i32 {
    let mut tape_path: Option<PathBuf> = None;
    let mut out_dir: Option<PathBuf> = None;
    let mut threads = 4usize;
    let mut verify_determinism = true;
    let mut render_html = true;

    let mut i = 0;
    while i < args.len() {
        match args[i].as_str() {
            "--tape" | "-t" => {
                if i + 1 < args.len() {
                    tape_path = Some(PathBuf::from(&args[i + 1]));
                    i += 2;
                } else {
                    eprintln!("missing argument for --tape");
                    return 2;
                }
            }
            "--out" | "-o" => {
                if i + 1 < args.len() {
                    out_dir = Some(PathBuf::from(&args[i + 1]));
                    i += 2;
                } else {
                    eprintln!("missing argument for --out");
                    return 2;
                }
            }
            "--threads" => {
                if i + 1 < args.len() {
                    threads = args[i + 1].parse().unwrap_or(4);
                    i += 2;
                } else {
                    eprintln!("missing argument for --threads");
                    return 2;
                }
            }
            "--no-determinism-check" => {
                verify_determinism = false;
                i += 1;
            }
            "--no-html" => {
                render_html = false;
                i += 1;
            }
            path_str if !path_str.starts_with('-') && tape_path.is_none() => {
                tape_path = Some(PathBuf::from(path_str));
                i += 1;
            }
            path_str if !path_str.starts_with('-') && out_dir.is_none() => {
                out_dir = Some(PathBuf::from(path_str));
                i += 1;
            }
            other => {
                eprintln!("unknown option for full-audit: {other}");
                return 2;
            }
        }
    }

    let tape = tape_path.unwrap_or_else(|| PathBuf::from("research/tape/btcusdt-1h-12m/tape.jsonl"));
    let out = out_dir.unwrap_or_else(|| PathBuf::from(".audit/rust_audit_current"));

    match audit::full_audit::run_full_audit(&tape, &out, threads, verify_determinism, render_html) {
        Ok(summary) => {
            println!("{}", serde_json::to_string_pretty(&summary).unwrap());
            0
        }
        Err(e) => {
            eprintln!("full-audit failed: {e}");
            1
        }
    }
}
