//! Data-backed performance benchmark for the Rust compute path.
//!
//! This is intentionally a `cargo bench` binary, not a test harness. It reads
//! a declared physical tape, runs the real Dataset ingestion path, and reports
//! timings derived from that input. It never creates a receipt or an economic
//! claim.

use std::hint::black_box;
use std::path::PathBuf;
use std::time::Instant;

use v8_core::data::Dataset;

struct Config {
    tape: PathBuf,
    iterations: usize,
}

fn main() {
    let config = match parse_args() {
        Ok(config) => config,
        Err(message) if message == "help" => {
            print_help();
            return;
        }
        Err(message) => {
            eprintln!("{message}");
            std::process::exit(2);
        }
    };

    let metadata = match std::fs::metadata(&config.tape) {
        Ok(metadata) if metadata.is_file() => metadata,
        Ok(_) => fail(&format!("DATA_BLOCKED_TAPE_NOT_A_FILE:{:?}", config.tape)),
        Err(error) => fail(&format!("DATA_BLOCKED_TAPE_UNREADABLE:{:?}:{error}", config.tape)),
    };

    println!("V8 data-backed performance benchmark");
    println!("input={}", config.tape.display());
    println!("input_bytes={}", metadata.len());
    println!("iterations={}", config.iterations);
    println!();

    for iteration in 1..=config.iterations {
        let started = Instant::now();
        let dataset = match Dataset::from_mmap_path(&config.tape) {
            Ok(dataset) => dataset,
            Err(error) => fail(&format!("DATA_BLOCKED_TAPE_INVALID:{error}")),
        };
        let elapsed = started.elapsed();
        let rows = black_box(dataset.n_rows);
        let data_hash = black_box(dataset.data_hash.as_str());
        let seconds = elapsed.as_secs_f64();
        let rows_per_second = rows as f64 / seconds;
        let mib_per_second = metadata.len() as f64 / seconds / (1024.0 * 1024.0);

        println!(
            "iteration={iteration} rows={rows} elapsed_ms={:.3} rows_per_second={rows_per_second:.2} mib_per_second={mib_per_second:.2} data_hash={data_hash}",
            seconds * 1_000.0
        );
    }
}

fn parse_args() -> Result<Config, String> {
    let mut tape = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    tape.push("../research/tape/quad-1h-12m/tape.jsonl");
    let mut iterations = 3;
    let args: Vec<String> = std::env::args().skip(1).collect();
    let mut index = 0;

    while index < args.len() {
        match args[index].as_str() {
            "--help" | "-h" => return Err("help".to_string()),
            "--tape" => {
                index += 1;
                let Some(value) = args.get(index) else {
                    return Err("--tape requires a path".to_string());
                };
                tape = PathBuf::from(value);
            }
            "--iterations" => {
                index += 1;
                let Some(value) = args.get(index) else {
                    return Err("--iterations requires a positive integer".to_string());
                };
                iterations = value
                    .parse::<usize>()
                    .map_err(|_| "--iterations requires a positive integer".to_string())?;
                if iterations == 0 {
                    return Err("--iterations requires a positive integer".to_string());
                }
            }
            other => return Err(format!("unknown argument: {other}")),
        }
        index += 1;
    }

    Ok(Config { tape, iterations })
}

fn print_help() {
    println!(
        "Usage: cargo bench --bench benchmark_runner -- [--tape PATH] [--iterations N]\n\n\
         Defaults to the repository's declared quad-1h-12m physical tape."
    );
}

fn fail(message: &str) -> ! {
    eprintln!("{message}");
    std::process::exit(1);
}
