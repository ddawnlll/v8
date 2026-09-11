# v8-core Guidelines

This directory (`v8-core/`) contains the authoritative Rust codebase for the entire V8 system.
All implementation, feature additions, bug fixes, refactoring, and test suites must be written here in Rust.

See root `AGENTS.md` for mandatory global invariants:
- **Rust Only:** All active code lives in `v8-core/`. Python is frozen.
- **Zero-Tolerance Anti-Hallucination Directive:** Absolute ban on hardcoded statistics ($p$-values, effect sizes, PBO, $+0.12R$), synthesized excursion offsets (`mfe_r + 0.8`), and fake artifact references in production/evaluation pipelines.
- **Constitution Rule 12:** `NO_ECONOMIC_CLAIM` until certified multiple-testing receipts exist.
- **Zero-Shadow Architecture:** All modules and architectural choices MUST be registered in `DECISION_REGISTER.md` (D-series), `IMPLEMENTATION_LAYOUT.md`, and compiled into monographs.

## CLI Usage

### Single Command: `make`

```bash
# Default: Run the data-backed performance benchmark
make

# Other options
make bench-quick      # One measured ingestion pass
make bench-full       # Ten measured ingestion passes
make bench-case CASE=<case.json>  # CLI single case
make clippy
make test
```

**Benchmark output includes:**
- Physical input path and byte size
- Parsed row count and data hash
- Per-iteration elapsed time and throughput

Use `make test` for D-153 correctness and adversarial verification tests.
