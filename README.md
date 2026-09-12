# V8 — Behavior-Driven Trading Intelligence

**Status: PRE-EXPERIMENTAL / EVIDENCE-BOUND.** V8 is a falsification program,
not a promise of edge. This repository does not claim that V8 is profitable,
that trader intuition is reliable, or that execution has been validated
(`V8_CONSTITUTION` rule 12: the current simulation authority is uncertified;
live status is unreachable until it is independently renewed).

**Active development boundary (2026-09-11, D-162 / reconciles #409):** `v8-next/`
is the **sole active and authoritative implementation** — the Python runtime,
expert plane, evaluation/benchmark fabric, evidence and report systems are the
current workstream. The Rust tree has been quarantined to `legacy/v8-core/` as a
non-canonical frozen reference, retained only as a labeled parity oracle; its
receipts and economic baselines are historical evidence of a superseded
implementation, not current V8 behavior. `src/v8/` plus `tests/` remain the
hash-locked frozen Python oracle, and `legacy/v82/` remains a quarantined
forensic archive.

V8 models the market as a set of behavior families rather than one universal
model: cheap self-gating **Experts** recognize a defined behavior, emit
**Candidate** hypotheses (never orders), a deterministic acceptance rule
admits them, a canonical Level-1 **simulator** produces counterfactual
outcomes, and a preregistered **hypothesis lab** binds code, data, and
config hashes before any verdict.

## Repository layout

```
docs/                  # source corpus — the single source of truth (Markdown/YAML)
  charter/             #   V8_CONSTITUTION.md
  contracts/           #   MARKET_STATE, EXPERT_PROTOCOL, CANDIDATE_LIFECYCLE,
                       #   DATASET, FEED_INGESTION, PERSISTENCE_REPLAY,
                       #   RUNTIME_SCHEDULER, SIMULATION_TRUTH
  protocols/           #   HYPOTHESIS_LAB, OPERATIONS, LEARNING_PROTOCOL
  audits/              #   RESEARCH_AUDIT, PROJECT_EVIDENCE_AUDIT, EVIDENCE_MATRIX, CONTRADICTION_MAP
  decisions/           #   DECISION_REGISTER, OPEN_DECISIONS
  research/            #   SOURCE_MAP, READING_LIST, analysis_*.md
  registries/          #   CLAIMS_REGISTRY.yaml, EXPERIMENT_REGISTRY.yaml
  tr/                  # Turkish translation of the corpus
  CHANGELOG.md         #   dated architecture decisions
  ROADMAP.md           #   build plan, Phases 0-7 with evidence gates
site/                  # generated reading artifacts (never hand-edited)
  index.html           #   EN monograph (built from docs/)
  tr.html              #   TR monograph (built from docs/tr/)
  brief/               #   v8-0.2.html, the styled research brief
research/              # literature evidence
  papers/              #   PDFs (canonical `NN_arxivid_title.pdf` naming)
  text/                #   extracted text + arxiv metadata + source integrity
  manifest/            #   research_papers_manifest.json (shared EN/TR)
v8-next/              # AUTHORITATIVE Python product (runtime, experts, evaluation, evidence)
legacy/v8-core/       # quarantined Rust reference — non-canonical, read-only parity oracle
legacy/v82/           # quarantined V8.2 forensic archive
src/v8/               # frozen Python parity oracle / legacy tooling dependency
tests/                 # historical Python tests and parity harness
tools/                 # monograph compiler, audits, and explicit legacy tooling
```

`v8-next/` is the authoritative request, evaluation and verification path.
`legacy/v8-core/` is frozen and may be executed read-only only as a labeled
parity oracle. `src/v8/` is retained only as the hash-locked historical oracle;
see `docs/legacy/PYTHON_ORACLE_POLICY.md`.

Verification is local-only; GitHub Actions workflows are removed. Run
`uv run --project v8-next --extra dev ruff check v8-next/src v8-next/tests` and
`uv run --project v8-next --extra dev pytest -q v8-next/tests`.
See [the product boundary](v8-next/AGENTS.md) for real-data acceptance rules.

## Rebuilding the monographs

Reproducible: the same corpus + manifest + script produce byte-identical HTML.

```bash
.venv/bin/python tools/build_monograph.py --lang en --docs docs    --out site/index.html
.venv/bin/python tools/build_monograph.py --lang tr --docs docs/tr --out site/tr.html
```

## The vertical slice

A tiny but real path that proves the contracts run end-to-end, as the project
audit requires before any component is added: synthetic tape -> MarketState
(availability-gated) -> self-gating experts -> append-only candidate log
(lifecycle state machine) -> deterministic acceptance -> canonical bar
simulator -> hash-bound lab report.

```bash
uv run --project v8-next --extra dev pytest -q v8-next/tests   # authoritative product gates
```

The slice sends no orders, holds no credentials, and never claims an economic
verdict (an absent authority receipt keeps the verdict `NO_ECONOMIC_CLAIM`).
It is infrastructure evidence, not alpha.

## Roadmap position

See `docs/ROADMAP.md` (Phases 0-7, each with a definition of done and an
evidence gate). Phase 0 (foundation) is done; Phase 1 (data plane) and
Phase 2 (state engine + feature graph) are the current targets. Feed,
persistence, runtime, and ops specs exist so the baseline can start without
designing the live system, which remains gated by the charter.
