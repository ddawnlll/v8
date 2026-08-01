# V8 — Behavior-Driven Trading Intelligence

**Status: PRE-EXPERIMENTAL / EVIDENCE-BOUND.** V8 is a falsification program,
not a promise of edge. This repository does not claim that V8 is profitable,
that trader intuition is reliable, or that execution has been validated
(`V8_CONSTITUTION` rule 12: the current simulation authority is uncertified;
live status is unreachable until it is independently renewed).

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
src/v8/                # Python package — the runtime
  simtruth/            #   vendored canonical simulation truth (V7 lab, engineering-only)
tests/                 # pytest suite
tools/                 # scripts: build_monograph.py, data.py, heads/, downloader
```

`src/v8/` uses the standard src layout (`src/<package>/`): the repo is named
v8, so flattening would create `v8/v8/`; the src layout keeps `import v8`
unambiguous and prevents accidental imports of the repo root.

## Rebuilding the monographs

Reproducible: the same corpus + manifest + script produce byte-identical HTML.

```bash
.venv/bin/python tools/build_monograph.py --lang en --docs docs    --out site/index.html
.venv/bin/python tools/build_monograph.py --lang tr --docs docs/tr --out site/tr.html
```

## The vertical slice (`src/v8/`)

A tiny but real path that proves the contracts run end-to-end, as the project
audit requires before any component is added: synthetic tape -> MarketState
(availability-gated) -> self-gating experts -> append-only candidate log
(lifecycle state machine) -> deterministic acceptance -> canonical bar
simulator -> hash-bound lab report.

```bash
.venv/bin/python -m pytest tests -q    # determinism, future-rejection,
                                       # dedup, illegal transitions, exposure
```

The slice uses synthetic data, sends no orders, holds no credentials, and
never claims an economic verdict (an absent authority receipt keeps the
verdict `NO_ECONOMIC_CLAIM`). It is infrastructure evidence, not alpha.

## Roadmap position

See `docs/ROADMAP.md` (Phases 0-7, each with a definition of done and an
evidence gate). Phase 0 (foundation) is done; Phase 1 (data plane) and
Phase 2 (state engine + feature graph) are the current targets. Feed,
persistence, runtime, and ops specs exist so the baseline can start without
designing the live system, which remains gated by the charter.
