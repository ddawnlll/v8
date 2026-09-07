# D-161 — V8.6 CLI delegation to clap

Status: PROVISIONAL_DECISION. Date: 2026-09-07. Issue: #351 (M09).
Authority: user-authorized V8.6 implementation, full-text monograph §12 CLI and Appendix C ANA-A7; WORK_ITEM_POLICY §§3–4. No economic authority is granted.

## 1. Preserved proposal and scope

The entire supplied proposal is preserved at [V8.6 full text](V8_6_PRODUCTION_RECALIBRATION_FULL_TEXT.html), SHA256 c766a472eb9095f87864c4dfeaf898877a06fd47eccdd44e8697c613a6eb01b1. It remains provisional; this bounded decision does not override existing financial, RNG, parity or Kaizen authorities.

M09 delegates generic command-line parsing to a verified release of clap. Domain execution remains in existing command handlers. New Rust module: `v8-core/src/cli.rs`, owning the command/argument schema and parse boundary. `main.rs` owns dispatch only. Dependencies and lockfile must name a verified available release; the monograph's candidate is 4.6.6 and must not be silently replaced if unavailable.

## 2. Valid-input compatibility

Inventory all 29 current top-level command names, positional arguments, named options and valid defaults against parent e7d80f22888ff1e94f1be882c878f6af801d5375. Preserve valid command meaning, units, input files, domain handlers and domain failure exit codes. Existing JSON request validation remains with its domain owner. Option parsing is not a second implementation of financial validation.

## 3. Explicit invalid-input change

Parsing malformed numeric options, unknown options/commands, duplicate single-value options, missing required values and excess positional values returns exit 2 with a diagnostic before any domain operation. Unlike permissive historical loops, malformed explicit input must not silently fall back to a default. Defaults apply only when an optional argument is absent. Help returns exit 0. This is an intentional CLI correctness change, not byte-for-byte diagnostic compatibility; no valid trading policy is modified.

Each discrepancy discovered in the inventory must be listed in the receipt. If a caller relies on permissive invalid input, update the invocation explicitly or leave that caller blocked; do not hide a compatibility fallback in the parser.

## 4. Ownership and removal

Use clap Command/Arg/ArgMatches or derive-equivalent schemas. Remove replaced manual flag scanning, numeric fallback parsing and positional-count checks in migrated main handlers. A top-level clap command accepting an unrestricted tail while leaving every old parser active does not satisfy M09. Delegated domain request-file commands retain their existing handlers, with their command-line envelope expressed in clap.

## 5. Verification

R1: command inventory names every active command/argument/default and its old handler.
R2: actual main dispatch consumes clap results; replaced generic parse loops are removed.
R3: Rust tests cover valid representative commands, defaults, unknown/missing/duplicate/malformed/excess input, help exit behavior and preserved domain dispatch. Run targeted tests/check during integration, then required full checks once at final validation.

Receipts are PENDING until commands are run. A passing parser unit test is not evidence of engine integration or V8.6 completion. No synthetic test input may enter production evidence.

## 6. Failure and reversal

Unavailable pin/API or unresolved domain contract: OPEN_PIN for the affected boundary. Rust-only/frozen Python rules remain unchanged. Reversal is the recorded parent commit and independent CLI change; no autonomous merge, force-push, or destruction of old branches. Required EN/TR decision and layout records accompany the implementation.
