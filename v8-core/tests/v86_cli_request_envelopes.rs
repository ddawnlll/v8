//! M09 / D-161 §3–4: clap owns request-command envelopes, not domain validation.
use clap::Parser;
use v8_core::cli::{Cli, Commands};

#[test]
fn request_commands_preserve_paths() {
    for command in ["shadow", "artifact-index"] {
        let cli = Cli::try_parse_from(["v8-core", command, "request with spaces.json"]).unwrap();
        let request = match cli.command {
            Commands::Shadow(request) | Commands::ArtifactIndex(request) => request,
            other => panic!("wrong dispatch: {other:?}"),
        };
        assert_eq!(
            request.request_path.to_str(),
            Some("request with spaces.json")
        );
    }
}

#[test]
fn request_commands_reject_invalid_envelopes_before_dispatch() {
    for command in ["shadow", "artifact-index"] {
        for tail in [
            vec![],
            vec!["a.json", "b.json"],
            vec!["--unknown"],
            vec!["a.json", "--unknown"],
            vec!["--request-path", "a.json"],
        ] {
            let mut args = vec!["v8-core", command];
            args.extend(tail);
            assert_eq!(Cli::try_parse_from(args).unwrap_err().exit_code(), 2);
        }
        assert_eq!(
            Cli::try_parse_from(["v8-core", command, "--help"])
                .unwrap_err()
                .exit_code(),
            0
        );
    }
}

#[test]
fn request_commands_preserve_domain_failure_exit_code() {
    let source_file = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("src/cli.rs");
    assert!(source_file.is_file());
    let missing_request = source_file.join("absent.json");
    for command in ["shadow", "artifact-index"] {
        let output = std::process::Command::new(env!("CARGO_BIN_EXE_v8-core"))
            .arg(command)
            .arg(&missing_request)
            .output()
            .unwrap();
        assert_eq!(output.status.code(), Some(1));
        assert!(String::from_utf8_lossy(&output.stderr).contains("error reading"));
    }
}
