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
    about = "V8 compute plane CLI - trading intelligence & backtesting engine (V8.6)",
    version = "0.2.0",
    arg_required_else_help = true
)]
pub struct Cli {
    #[command(subcommand)]
    pub command: Commands,
}

#[derive(Subcommand, Debug)]
pub enum Commands {
    // ─── Benchmark & Testing ───────────────────────────────────
    /// Run D-153 benchmark suite (default: full readiness report)
    #[command(name = "bench")]
    Bench {
        /// Quick mode: minimal parity check (skip full benchmark)
        #[arg(long)]
        quick: bool,
        /// Path to benchmark case JSON (run single case)
        case: Option<PathBuf>,
    },

    // ─── Compute Pipeline ───────────────────────────────────────
    /// Generate H4 conflict report from tape (S0)
    H4Decomposition {
        #[arg(long)]
        tape: PathBuf,
        #[arg(long)]
        out: PathBuf,
    },
    /// Ingest tape into Dataset (S0)
    Ingest(RequestArg),
    /// Compute FeatureStore/StateView values (S1)
    Features(RequestArg),
    /// Evaluate compiled still_valid IR bytes (S2)
    #[command(name = "predicate-check")]
    PredicateCheck {
        ir_path: PathBuf,
        input_path: PathBuf,
    },
    /// Run ReplayKernel over candidate batch (S2)
    Replay(RequestArg),
    /// Run Vulkan f64 compute probe
    #[command(name = "gpu-probe")]
    GpuProbe,
    /// Compare GPU replay vs scalar CPU golden case
    #[command(name = "gpu-parity")]
    GpuParity,
    /// Stream Outcome Cube to reduced tables (S3)
    Cube(RequestArg),

    // ─── Expert Evaluation ──────────────────────────────────────
    /// Batch per-bar ExpertPlane draft check (S4)
    #[command(name = "evaluate-check")]
    EvaluateCheck(RequestArg),
    /// Print 28-expert dispatch table
    Registry,
    /// Full ExpertPlane → candidates → reduce loop (S4)
    Evaluate {
        #[arg(trailing_var_arg = true, allow_hyphen_values = true)]
        args: Vec<String>,
    },

    // ─── Experiments & Analysis ─────────────────────────────────
    /// Run frozen v8_slice_001 Phase-4 admission boundary
    Experiment {
        #[arg(trailing_var_arg = true, allow_hyphen_values = true)]
        args: Vec<String>,
    },
    /// S6: reconciliation (CandidateSnapshot join + PIT lineage)
    Reconcile {
        #[arg(trailing_var_arg = true, allow_hyphen_values = true)]
        args: Vec<String>,
    },
    /// S6: regret phases 1-3
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
    /// S5/S7: LEDGER_FORMAT_SPEC cheap tests
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

    // ─── Audits & Verification ──────────────────────────────────
    /// Opportunity Universe coverage receipt
    #[command(name = "oracle-coverage")]
    OracleCoverage {
        #[arg(trailing_var_arg = true, allow_hyphen_values = true)]
        args: Vec<String>,
    },
    /// Shadow provenance and artifact gate
    Shadow(RequestArg),
    /// Bind diagnostic bundle to shadow manifest
    #[command(name = "artifact-index")]
    ArtifactIndex(RequestArg),
    /// Exit ablation experiment
    #[command(name = "exit-ablation")]
    ExitAblation {
        #[arg(trailing_var_arg = true, allow_hyphen_values = true)]
        args: Vec<String>,
    },
    /// Full high-throughput in-process audit engine
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
        #[arg(num_args = 0..=2)]
        paths: Vec<PathBuf>,
    },
    /// Benchmark Fabric evaluation runner
    Benchmark {
        #[arg(trailing_var_arg = true, allow_hyphen_values = true)]
        args: Vec<String>,
    },

    // ─── Simulations ────────────────────────────────────────────
    /// Finite-capital Binance USD-M portfolio simulator
    #[command(name = "usdm-sim")]
    UsdmSim {
        #[arg(trailing_var_arg = true, allow_hyphen_values = true)]
        args: Vec<String>,
    },
    /// Historical archetype audit (A01-A12, D-125)
    #[command(name = "allegory-audit")]
    AllegoryAudit {
        #[arg(trailing_var_arg = true, allow_hyphen_values = true)]
        args: Vec<String>,
    },
    /// Opportunity Capture Funnel empirical audit
    #[command(name = "funnel-audit")]
    FunnelAudit {
        #[arg(trailing_var_arg = true, allow_hyphen_values = true)]
        args: Vec<String>,
    },
    /// Epistemic Economic Observability qualification
    #[command(name = "eeo-qualify")]
    EeoQualify {
        #[arg(trailing_var_arg = true, allow_hyphen_values = true)]
        args: Vec<String>,
    },
}

#[derive(Args, Debug)]
pub struct RequestArg {
    /// Path to request.json
    pub request_path: PathBuf,
}
