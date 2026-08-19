# v8-core Guidelines

This directory (`v8-core/`) contains the authoritative Rust codebase for the entire V8 system.
All implementation, feature additions, bug fixes, refactoring, and test suites must be written here in Rust.

See root `AGENTS.md` for mandatory global invariants:
- **Rust Only:** All active code lives in `v8-core/`. Python is frozen.
- **Zero-Tolerance Anti-Hallucination Directive:** Absolute ban on hardcoded statistics ($p$-values, effect sizes, PBO, $+0.12R$), synthesized excursion offsets (`mfe_r + 0.8`), and fake artifact references in production/evaluation pipelines.
- **Constitution Rule 12:** `NO_ECONOMIC_CLAIM` until certified multiple-testing receipts exist.
