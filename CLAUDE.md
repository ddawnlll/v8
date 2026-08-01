# CLAUDE.md — V8 agent guide

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
3. `docs/ROADMAP.md` — build plan, Phases 0-7 with evidence gates.
4. `docs/CHANGELOG.md` — dated architecture decisions.
5. `docs/AGENT_RUNBOOK.md` — execution contract when running an autonomous
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
.venv/bin/python -m pytest tests -q                       # tests
.venv/bin/python tools/build_monograph.py --lang en ...   # rebuild (above)
uv venv .venv && uv pip install --python .venv/bin/python -e ".[dev]"   # env
```

## Architecture rules (non-negotiable)

- **Evidence labels** — `LITERATURE_SUPPORTED` / `PROJECT_EVIDENCE_SUPPORTED`
  / `DESIGN_INFERENCE` / `PROVISIONAL_DECISION` / `LOCKED_INVARIANT` /
  `OPEN_QUESTION` / `REJECTED_OPTION`; never interchangeable.
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
- `src/v8/` — runtime package: `schema`, `store` (append-only JSONL),
  `marketstate` (PIT builder), `experts/` (base + one file per behavior
  family, D-033), `lifecycle` (state machine +
  `ExposureBook`), `simulator` (canonical L1), `lab` (hash-bound runner),
  `synth` (synthetic tape), `simtruth/` (vendored V7 lab — engineering only,
  authority NOT renewed).
- `tests/` — pytest suite (`tests/test_vertical_slice.py`).
- `tools/` — `build_monograph.py` + `heads/`, `data.py` (V7 archive→tape
  builder, Phase 1), `download_v8_reading_list.py`.
- `research/` — literature: `papers/`, `text/`, `manifest/`.
- `site/brief/` — `v8-0.2.html`, the styled research brief.

## Conventions

- Small files, stdlib-first, deterministic; numpy is allowed only in
  `simtruth/` and research tooling, not in the decision-path core.
- Dataclasses for records; append-only logs; `sha1_hex` for canonical hashes.
- No comments unless the WHY is non-obvious.
