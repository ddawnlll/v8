# legacy_v1 — archived v1 extraction outputs

**Status:** `LEGACY_UNVERIFIED` · pipeline_version `v1` · NOT source evidence.

These files are the output of the v1 book-analysis workflow (run before
`research_pipeline_v2.0`). They are archived here as **search hints only** —
possible leads, possible strategy names, possible page/chapter hints. They are
NOT migrated into the v2 database because v1 conflated source statements with
V8/crypto interpretations in single records:

- Source text and V8 defaults (e.g. `BTCUSDT 1h`, `N bars`, `NEXT_BAR_CLOSE`,
  `1R target`) were mixed inside the same `setup_summary` field.
- Some records were built from index entries alone.
- Strategy/feature/risk/methodology findings shared one flat pool.
- `strategy_id` taxonomy was unstable (613 distinct ids / 1080 findings).

## Contents

| Path | What it is |
|---|---|
| `analysis/reader_seed_99_full.json` | 99 reader results, 1080 findings (reader schema v1) |
| `analysis/reader_seed_by_theme/*.json` | same findings bucketed by theme for the v1 merge |
| `v1_workflow_full.js` | the v1 workflow script (embedding + seeding design) |

## Use in v2

Per v2 protocol, legacy records may be used by the v2 `claim_scout` as *recall
hints* (a strategy name / page hint to re-locate the exact source passage), but:

- a legacy record never becomes a `raw_claim` automatically;
- the exact supporting passage must be re-found in the source text;
- provenance must be re-established field by field.

## Counts (v1)

- books scanned: 155 files -> 125 unique titles -> 124 readable
- OCR: 8 scanned PDFs (~3000 pages) via tesseract
- readers completed: 99 of 266 planned units
- findings: 1080
