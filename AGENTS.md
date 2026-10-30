# AGENTS.md — Agent Guidelines & Execution Invariants

## 1. Repository Boundaries & Authority
- **`v8-next/` (PRIMARY & ACTIVE):** The sole active codebase. All development, audits, scripts, tests, and artifacts happen here.
- **`v8-core/` (ARCHIVED RUST — READ-ONLY):** Never modify, create files, or run `cargo` builds/tests here. Read only when explicitly asked to reference historical Rust logic.
- **`src/v8/` & `tests/` (ARCHIVED LEGACY PYTHON — DO NOT TOUCH):** Strictly off-limits. Never read, write, or import from `src/v8/` or root `tests/`.

## 2. Token & Context Discipline (Flash Model Optimization)
- **Terse Output Only:** Do not narrate plans, repeat instructions, or write long prose explanations between tool calls. Execute commands directly and state results in ≤3 lines.
- **Bounded Reads Only:** Never dump whole large files into context. Use `rg`, `head`, `jq`, `sqlite3`, or line-bounded reads.
- **Artifact Size Cap:** Keep individual JSONL files below ~5 MB. Never export all 28 stances unless explicitly required; store dense per-bar data in Parquet/SQLite or export only the target expert + aggregates.

## 3. Zero-Tolerance Anti-Hallucination & Data Integrity
- **No Hardcoded or Synthetic Metrics:** Never hardcode p-values, effect sizes, PBO scores, or offset trade excursions (e.g., `mfe_r + 0.8`). All metrics must come from real computations.
- **Fail Closed:** If data or markouts are missing, emit `None`, `BLOCKED`, `NOT_IDENTIFIABLE`, or `NOT_APPLICABLE`. Never invent placeholders or write `PASS_WITH_LIMITATION`.
- **No Fictitious Artifacts:** Every file path, hash, or table referenced in a report must physically exist on disk and match the manifest.
- **No Uncertified Economic Claims:** Unless multiple-testing adjustments (WRC, DSR, Hansen SPA) and authority receipts pass, verdicts must remain `NO_ECONOMIC_CLAIM`.

## 4. Workflow & Git Governance (Trunk-Based)
- **Default Loop (Tier A/B):** `edit in v8-next/ → run focused tests/lint → commit to main → continue`. No PR ceremony or D-xxx/monograph overhead for routine dev.
- **Audit / Investigation Mode:** When assigned an audit or evidence run in `v8-next/`, keep strategy, engine, sizing, and execution behavior strictly unchanged unless instructed otherwise. Additive audit scripts and read-only inspection are allowed.
- **Tier D (Release / Economic Claim Boundary Only):** Require `DECISION_REGISTER.md` (`D-xxx`), `IMPLEMENTATION_LAYOUT.md`, `CHANGELOG.md`, and monograph rebuilds (`tools/build_monograph.py`) only at explicit release boundaries.

## 5. Fast Execution Protocol — Audits, Investigations & Evidence Runs

### 5.1 Preflight Before Tool Use (5 Minutes Max)
1. Read the acceptance contract and write a short `ACCEPTANCE.md` containing:
   - required final language and exact section headings;
   - allowed gate enum: `PASS | FAIL | BLOCKED | NOT_APPLICABLE`;
   - required counts: orphan, unmatched, reconciliation, hashes;
   - exact artifact filenames.
2. Locate the dataset and existing artifacts first. If the tape is absent, declare the build step before any analysis.
3. Identify one baseline command, one verification command, and one `run_dir`. Do not discover the test environment late.
4. Fix the run ID and frozen window before reading outcomes.

### 5.2 One Run, One Source of Truth
- Freeze dataset SHA-256 and window once; do not silently change them.
- Run the baseline once. Re-run only for determinism or a declared counterfactual.
- Prefer one integrated audit script with `run`, `funnel`, `orders`, `metrics` subcommands over four scripts written and regenerated sequentially.
- Derive all reports and tables from one `run_dir`; never hand-copy numbers.
- Do not export all 28 stances unless required. Store large per-bar data in Parquet/SQLite or export only the selected expert and aggregates.
- Keep individual JSONL artifacts below ~5 MB (a 21 MB `ensemble_decisions.jsonl` is context-hostile).

### 5.3 Final-Language Artifact First
- Immediately after metrics are computed, create the mandatory final delivery artifact in the required language (e.g. `FINAL_DELIVERY_TR.md`) with all required headings.
- Populate it programmatically from JSON/CSV artifacts; never write a long prose report first and the mandatory delivery last.
- **Flash Token Rule:** Write the full report to disk ONLY. Do NOT echo or paste the contents of `FINAL_DELIVERY_TR.md` or `ACCEPTANCE.md` into the chat response.

### 5.4 Completion Self-Audit (Mandatory Before Declaring Done)
Verify in parallel (and record in the delivery artifact, NOT as a long chat essay):
- required headings present (language and exact section names);
- all gate statuses are strictly `PASS | FAIL | BLOCKED | NOT_APPLICABLE` (never `PASS_WITH_LIMITATION`; use `BLOCKED` or `NOT_IDENTIFIABLE` if evidence is missing);
- every orphan/unmatched count is explicit and zero, or explained;
- artifact hashes match the manifest;
- funnel, order, fill, position, and economic totals reconcile;
- `git diff --name-only` excludes archived paths (`src/v8/`, `tests/`, `v8-core/`);
- focused tests and lint ran with exit codes recorded.

### 5.5 Context & Timebox Rules
- Never dump a whole large file into context. Use `rg`, `head`, `jq`, `sqlite3`, or bounded reads.
- Run independent checks in parallel where possible (tests, lint, hashes).
- Target a complete end-to-end audit within ~20 minutes. If tight, shrink to baseline + funnel + economics first, then expand.
- Spend at most 2 cycles on any non-essential counterfactual; mark it `NOT_IDENTIFIABLE` or `NOT_APPLICABLE` and move on.

### 5.6 Audit-Mode Code Freeze (`v8-next/`)
- When assigned an **audit, investigation, or evidence run** in `v8-next/`, only read-only inspection and additive audit tools/scripts are allowed. Strategy, engine, sizing, and execution behavior must remain strictly unchanged during the audit.