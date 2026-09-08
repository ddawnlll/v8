//! M09 D-161 §2–4: full-audit parsing delegates to clap without executing an audit.
use clap::Parser;
use v8_core::cli::{Cli, Commands};

#[test]
fn h4_diagnostic_requires_explicit_paths_and_fails_on_absent_tape() {
    assert!(Cli::try_parse_from(["v8-core", "h4-decomposition"]).is_err());
    let missing = std::env::current_exe().unwrap().join("no-tape.jsonl");
    let result = std::process::Command::new(env!("CARGO_BIN_EXE_v8-core"))
        .arg("h4-decomposition")
        .arg("--tape")
        .arg(&missing)
        .arg("--out")
        .arg(missing.join("no-report.txt"))
        .output()
        .unwrap();
    assert_eq!(result.status.code(), Some(1));
    assert!(!result.stderr.is_empty());
}

#[test]
fn defaults_and_explicit_options() {
    let Commands::FullAudit {
        tape,
        out,
        threads,
        no_html,
        no_determinism_check,
        paths,
    } = Cli::try_parse_from(["v8-core", "full-audit"])
        .unwrap()
        .command
    else {
        panic!()
    };
    assert!(tape.is_none() && out.is_none() && paths.is_empty());
    assert_eq!(threads, 4);
    assert!(!no_html && !no_determinism_check);
    let Commands::FullAudit {
        tape,
        out,
        threads,
        no_html,
        no_determinism_check,
        paths,
    } = Cli::try_parse_from([
        "v8-core",
        "full-audit",
        "-t",
        "tape.jsonl",
        "-o",
        "out",
        "--threads",
        "7",
        "--no-html",
        "--no-determinism-check",
    ])
    .unwrap()
    .command
    else {
        panic!()
    };
    assert_eq!(tape.unwrap().to_str(), Some("tape.jsonl"));
    assert_eq!(out.unwrap().to_str(), Some("out"));
    assert_eq!(threads, 7);
    assert!(no_html && no_determinism_check && paths.is_empty());
}

#[test]
fn malformed_and_duplicate_options_are_rejected() {
    for tail in [
        vec!["--threads", "oops"],
        vec!["--threads", "-1"],
        vec!["--threads"],
        vec!["--unknown"],
        vec!["--threads", "2", "--threads", "3"],
        vec!["--tape", "a", "-t", "b"],
        vec!["a", "b", "c"],
    ] {
        let mut args = vec!["v8-core", "full-audit"];
        args.extend(tail);
        assert_eq!(Cli::try_parse_from(args).unwrap_err().exit_code(), 2);
    }
    assert_eq!(
        Cli::try_parse_from(["v8-core", "full-audit", "--help"])
            .unwrap_err()
            .exit_code(),
        0
    );
}

#[test]
fn excess_mixed_paths_fail_before_domain_execution() {
    let output = std::process::Command::new(env!("CARGO_BIN_EXE_v8-core"))
        .args(["full-audit", "--tape", "a", "--out", "b", "extra"])
        .output()
        .unwrap();
    assert_eq!(output.status.code(), Some(2));
    assert!(String::from_utf8_lossy(&output.stderr).contains("excess positional"));
}

#[test]
fn legacy_positional_and_mixed_envelopes_parse() {
    for tail in [
        vec!["tape", "out"],
        vec!["--tape", "tape", "out"],
        vec!["--out", "out", "tape"],
        vec!["tape", "--out", "out"],
    ] {
        let mut args = vec!["v8-core", "full-audit"];
        args.extend(tail);
        assert!(Cli::try_parse_from(args).is_ok());
    }
}
