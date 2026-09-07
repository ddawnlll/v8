//! Local verification entry point. Stops on the first failed check.
use std::{path::Path, process::Command};

fn run(root: &Path, program: &str, args: &[&str]) {
    println!("\n> {program} {}", args.join(" "));
    match Command::new(program).args(args).current_dir(root).status() {
        Ok(status) if status.success() => {}
        Ok(status) => std::process::exit(status.code().unwrap_or(1)),
        Err(error) => {
            eprintln!("cannot run {program}: {error}");
            std::process::exit(1);
        }
    }
}

fn main() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).parent().unwrap();
    let python = if root.join(".venv/bin/python").is_file() {
        ".venv/bin/python"
    } else {
        "python3"
    };
    for script in [
        "tools/audit_python_boundary.py",
        "tools/audit_synthetic_leakage.py",
        "tools/audit_economic_claim.py",
        "tools/forbidden_names.py",
    ] {
        run(root, python, &[script]);
    }
    let manifest = "v8-core/Cargo.toml";
    run(
        root,
        "cargo",
        &["check", "--locked", "--manifest-path", manifest],
    );
    run(
        root,
        "cargo",
        &["test", "--locked", "--manifest-path", manifest],
    );
    run(
        root,
        "cargo",
        &[
            "clippy",
            "--locked",
            "--manifest-path",
            manifest,
            "--all-targets",
            "--",
            "-D",
            "warnings",
        ],
    );
    println!("\nLocal verification passed. No economic or live-readiness claim.");
}
