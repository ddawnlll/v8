# CLAUDE.md — V8 agent guide

## 🚨 CRITICAL RULE: RUST ONLY (`v8-core/`) — PYTHON IS DEPRECATED & FROZEN
- **The authoritative runtime codebase is `v8-core/` (Rust).**
- **ALL new features, bug fixes, evaluations, refactors, and test suites MUST be in Rust inside `v8-core/`.**
- **NEVER modify or add Python code under `src/v8/` or `tests/`.** `src/v8/` is a frozen historical parity oracle locked by `docs/legacy/PYTHON_ORACLE_LOCK.json`.
- Changes to `src/v8/` fail boundary integrity audits (`tools/audit_python_boundary.py`).

Optimized for agentic coding: read this first, then the monograph.

## What this is

V8 is a **behavior-driven trading intelligence research program** (crypto
perpetual futures). Status: **PRE-EXPERIMENTAL / EVIDENCE-BOUND**. It is a
falsification program, not a promise of edge. Never write text claiming
profitability, validated execution, or a promoted trading system
(`V8_CONSTITUTION` rule 12).

## Read order (most important first)

1. `site/index.html` — the canonical monograph (single file, everything,
   with a table of contents). **It is GENERATED — never hand-edit `site/*`.**
2. `docs/charter/V8_CONSTITUTION.md` — the rules (1-17).
3. `docs/WORK_ITEM_POLICY.md` — canonical work-item, PR & merge governance (v1.2).
4. `docs/ROADMAP.md` — build plan, Phases 0-7 with evidence gates.
5. `docs/CHANGELOG.md` — dated architecture decisions.
6. `docs/AGENT_RUNBOOK.md` — execution contract when running an autonomous
   build session (steps, gates, commit protocol, pinned decisions).


## Source of truth and regeneration

- `docs/` is the editable corpus (Markdown/YAML).
- `site/index.html` (EN) and `site/tr.html` (TR) are built artifacts.
- After editing `docs/`, rebuild **both** and record the change:

```bash
.venv/bin/python tools/build_monograph.py --lang en --docs docs    --out site/index.html
.venv/bin/python tools/build_monograph.py --lang tr --docs docs/tr --out site/tr.html
```

- Every change lands in `docs/CHANGELOG.md`; decisions in
  `docs/decisions/DECISION_REGISTER.md`; open questions in
  `docs/decisions/OPEN_DECISIONS.md`.

## Commands

```bash
.venv/bin/python tools/audit_python_boundary.py            # Python/Rust boundary
.venv/bin/python tools/forbidden_names.py                  # gated identifiers
cargo test --manifest-path v8-core/Cargo.toml               # Rust runtime tests
.venv/bin/python tools/build_monograph.py --lang en ...   # rebuild (above)
uv venv .venv && uv pip install --python .venv/bin/python -e ".[dev]"   # tooling env
```

## Architecture rules (non-negotiable)

- **Evidence labels** — `LITERATURE_SUPPORTED` / `PROJECT_EVIDENCE_SUPPORTED`
  / `DESIGN_INFERENCE` / `PROVISIONAL_DECISION` / `LOCKED_INVARIANT` /
  `OPEN_QUESTION` / `REJECTED_OPTION`; never interchangeable.
- **ZERO SHADOW ARCHITECTURE (Mandatory Registration):**
  1. Every new module, structural pattern, error taxonomy, or cryptographic upgrade MUST register a `D-xxx` decision in `docs/decisions/DECISION_REGISTER.md` (and `docs/tr/DECISION_REGISTER.md`).
  2. Every module MUST be mapped in `docs/contracts/IMPLEMENTATION_LAYOUT.md`.
  3. Every architecture change MUST be logged in `docs/CHANGELOG.md`.
  4. Monograph must be rebuilt immediately (`tools/build_monograph.py`).
  5. Unregistered shadow code paths are strictly prohibited.

- **Gated components are ABSENT by default**: router, shared scorer, ranker,
  RL execution, online learning (rules 6, 14). Do not implement them.
- **Learning is offline and registry-gated**; outcome data never mutates an
  active Expert (rule 15, `LEARNING_PROTOCOL`).
- **Versions evolve by challenger + frozen-OOS + registry decision**, never
  in place.
- **One active exposure per (instrument, direction)** (rule 16).
- **Determinism**: no wall clock (`NOW()`) inside replay; the three clocks
  (event / available / ingested) are never collapsed.
- The economic verdict stays `NO_ECONOMIC_CLAIM` without an authority receipt.

## Code layout

- Normative contracts: `docs/contracts/ARCHITECTURE_SPEC.md` (pipeline +
  technology baseline, D-031) and `docs/contracts/IMPLEMENTATION_LAYOUT.md`
  (file family: every file's responsibility/interface, layering rules, tracked
  code/spec divergences). Do not add or rename a `src/v8/` module without a
  register decision + CHANGELOG entry (D-032).
- `v8-core/` — authoritative Rust runtime, compute plane, scheduler, backends,
  analysis, verdict, report and audit surfaces.
- `src/v8/` — frozen Python parity oracle and explicit legacy-tool dependency;
  not a runtime path. See `docs/legacy/PYTHON_ORACLE_POLICY.md`.
- `tests/` — historical Python tests/parity harness; not the CI runtime gate.
- `tools/` — documentation compiler, boundary audits, and explicitly invoked
  legacy data/diagnostic tooling.
- `research/` — literature: `papers/`, `text/`, `manifest/`.
- `site/brief/` — `v8-0.2.html`, the styled research brief.

## Conventions

- Small files, stdlib-first, deterministic; numpy is allowed only in
  `simtruth/` and research tooling, not in the decision-path core.
- Dataclasses for records; append-only logs; `sha1_hex` for canonical hashes.
- No comments unless the WHY is non-obvious.

## Computation budget (D-099)

Compute is evidence work, not a ritual. Before any command expected to take
more than five seconds, or any command that repeats an already-green check,
state the decision it could change and the new semantic risk it covers. Run it
only when its expected marginal decision value exceeds its full cost (runtime,
user latency, context/tool overhead, and redundancy).

- Mandatory semantic-boundary gates override that economic test: changed
  correctness semantics, determinism/parity boundaries, safety/authority
  boundaries, or a required handoff gate still run.
- Prefer the smallest discriminating check. Do not rerun a green suite after
  documentation-only or formatting-only edits; run the full handoff suite at
  most once per handoff.
- Keep an added verification pass to 60 seconds. If more evidence is needed,
  stop and report the evidence, the remaining uncertainty, and the exact next
  check rather than continuing speculative computation.
- A small complementary gate bundle is allowed when no individual check can
  establish the relevant boundary; name the bundle's shared decision first.

The canonical, reader-facing version is
`docs/COMPUTATION_BUDGET_POLICY.md`; `rules.md` is the short root-level copy.

## Work-Item & PR Governance (v1.2)

- **Collaborative workflow:** Defined in `docs/WORK_ITEM_POLICY.md` and `CONTRIBUTING.md`.
- **Precedence Hierarchy:** Constitution & Decisions > `WORK_ITEM_POLICY.md` > `CONTRIBUTING.md` > Scoped Agent Instructions. If active authorities conflict, STOP and open/escalate an `OPEN_PIN`.
- **Traceability Rule:** Every work item must satisfy the Universal Context-Completeness Contract (R# traceability, reused contracts, invariants, canonical failure semantics, dependency map, OPEN_PIN triggers). Every PR requires a complete `R#` traceability matrix.

