//! V8-core CLI parsing module via `clap` (V8.6 M09, ANA-A7).
//!
//! Owns CLI grammar, flags, and option validation via `clap`.
//! Dispatches thin commands to existing subsystem runners, preserving
//! return codes and failure semantics.

use clap::{Args, Parser, Subcommand};
use std::path::PathBuf;

#[derive(Parser, Debug)]
#[command(
    name = "v8-core",
    about = "V8 compute plane CLI (V8.6 recalibrated)",
    version = "0.2.0",
    arg_required_else_help = true
)]
pub struct Cli {
    #[command(subcommand)]
    pub command: Commands,
}

#[derive(Subcommand, Debug)]
pub enum Commands {
    /// Generate the historical H4 conflict report from explicit real tape input
    H4Decomposition {
        #[arg(long)]
        tape: PathBuf,
        #[arg(long)]
        out: PathBuf,
    },
    /// Ingest a tape into a Dataset and write the dataset artifact (S0)
    Ingest(RequestArg),
    /// Compute FeatureStore/StateView values (stage S1)
    Features(RequestArg),
    /// Evaluate compiled still_valid IR bytes (stage S2)
    #[command(name = "predicate-check")]
    PredicateCheck {
        ir_path: PathBuf,
        input_path: PathBuf,
    },
    /// Run the ReplayKernel over a candidate batch (stage S2)
    Replay(RequestArg),
    /// Benchmark CPU/Auto/GPU replay selection on a request
    Bench(RequestArg),
    /// Run the optional Vulkan f64 compute probe
    #[command(name = "gpu-probe")]
    GpuProbe,
    /// Compare the GPU replay against the scalar CPU golden case
    #[command(name = "gpu-parity")]
    GpuParity,
    /// Stream the Outcome Cube to reduced tables (stage S3)
    Cube(RequestArg),
    /// Batch per-bar ExpertPlane draft check (stage S4)
    #[command(name = "evaluate-check")]
    EvaluateCheck(RequestArg),
    /// Print the 28-expert dispatch table with ported flags (S4)
    Registry,
    /// Full per-bar ExpertPlane -> candidates -> reduce loop (S4)
    Evaluate {
        #[arg(trailing_var_arg = true, allow_hyphen_values = true)]
        args: Vec<String>,
    },
    /// Run the frozen v8_slice_001 Phase-4 admission/evaluation boundary
    Experiment {
        #[arg(trailing_var_arg = true, allow_hyphen_values = true)]
        args: Vec<String>,
    },
    /// S6: reconciliation (CandidateSnapshot join + PIT lineage)
    Reconcile {
        #[arg(trailing_var_arg = true, allow_hyphen_values = true)]
        args: Vec<String>,
    },
    /// S6: regret phases 1-3 (opportunity/systematicity/recover)
    Analysis {
        #[arg(trailing_var_arg = true, allow_hyphen_values = true)]
        args: Vec<String>,
    },
    /// S5: content-addressed DAG cache identity check
    #[command(name = "cache-check")]
    CacheCheck {
        #[arg(trailing_var_arg = true, allow_hyphen_values = true)]
        args: Vec<String>,
    },
    /// S5/S7: LEDGER_FORMAT_SPEC §8 cheap tests
    #[command(name = "ledger-check")]
    LedgerCheck {
        #[arg(trailing_var_arg = true, allow_hyphen_values = true)]
        args: Vec<String>,
    },
    /// S7: verdict statistics on reduced tables
    Verdict {
        #[arg(trailing_var_arg = true, allow_hyphen_values = true)]
        args: Vec<String>,
    },
    /// S7: verdict report artifacts + audit
    Report {
        #[arg(trailing_var_arg = true, allow_hyphen_values = true)]
        args: Vec<String>,
    },
    /// O3: Opportunity Universe representational coverage receipt
    #[command(name = "oracle-coverage")]
    OracleCoverage {
        #[arg(trailing_var_arg = true, allow_hyphen_values = true)]
        args: Vec<String>,
    },
    /// V8.3 prospective shadow provenance and artifact gate
    Shadow(RequestArg),
    /// Bind a declared diagnostic bundle to one shadow manifest
    #[command(name = "artifact-index")]
    ArtifactIndex(RequestArg),
    /// Exit ablation experiment
    #[command(name = "exit-ablation")]
    ExitAblation {
        #[arg(trailing_var_arg = true, allow_hyphen_values = true)]
        args: Vec<String>,
    },
    /// Finite-capital Binance USD-M portfolio simulator
    #[command(name = "usdm-sim")]
    UsdmSim {
        #[arg(trailing_var_arg = true, allow_hyphen_values = true)]
        args: Vec<String>,
    },
    /// Multi-episode historical archetype audit (A01-A12, D-125)
    #[command(name = "allegory-audit")]
    AllegoryAudit {
        #[arg(trailing_var_arg = true, allow_hyphen_values = true)]
        args: Vec<String>,
    },
    /// V8.3 Opportunity Capture Funnel empirical audit (Phase II)
    #[command(name = "funnel-audit")]
    FunnelAudit {
        #[arg(trailing_var_arg = true, allow_hyphen_values = true)]
        args: Vec<String>,
    },
    /// D-136 Epistemic Economic Observability qualification runner
    #[command(name = "eeo-qualify")]
    EeoQualify {
        #[arg(trailing_var_arg = true, allow_hyphen_values = true)]
        args: Vec<String>,
    },
    /// Unified high-throughput in-process audit engine (Issues #306-#309)
    #[command(name = "full-audit")]
    FullAudit {
        #[arg(long, short = 't')]
        tape: Option<PathBuf>,
        #[arg(long, short = 'o')]
        out: Option<PathBuf>,
        #[arg(long, default_value_t = 4)]
        threads: usize,
        #[arg(long)]
        no_determinism_check: bool,
        #[arg(long)]
        no_html: bool,
        /// Legacy positional tape/output paths, filling options not supplied by flags.
        #[arg(num_args = 0..=2)]
        paths: Vec<PathBuf>,
    },
    /// D-153 V8.5 Benchmark Fabric evaluation runner and audit
    Benchmark {
        #[arg(trailing_var_arg = true, allow_hyphen_values = true)]
        args: Vec<String>,
    },
}

#[derive(Args, Debug)]
pub struct RequestArg {
    /// Path to request.json
    pub request_path: PathBuf,
}
