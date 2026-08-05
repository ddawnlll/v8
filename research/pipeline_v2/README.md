# research_pipeline_v2 — V8 book-to-strategy research data system

**Status:** PROVISIONAL_DECISION. This is a research *data-production* system,
not a trading system and not evidence of edge. It converts the trading-book
corpus into source-faithful, provenance-tracked strategy records that V8's
expert registry can consume later. All output is `DESIGN_INFERENCE` /
`LITERATURE_SUPPORTED`-grade input; nothing here is `PROJECT_EVIDENCE_SUPPORTED`.

`pipeline_version: research_pipeline_v2.0` · `schema_version: 2.0`

## Why v2 exists

The v1 extraction conflated three things in single records: what the source
states, our crypto/V8 adaptation, and V8 defaults. That made later code look
source-supported when it was invented detail. v2 makes that impossible by
construction: a raw source layer that cannot mention crypto/V8, a separate
translation layer with per-field provenance, and independent extractors +
adjudication.

## Invariants

1. Raw source layer contains only what the source states. BTC/perpetual/1h/
   ATR-stop/NEXT_BAR_CLOSE/frozen-reference/1R tokens are a *leak* and are
   rejected by `tools/validate.py`.
2. Every field carries provenance
   (`SOURCE_EXPLICIT | SOURCE_DERIVED | MARKET_TRANSLATION |
   V8_OPERATIONALIZATION | EXPERIMENTAL_ASSUMPTION | V8_DEFAULT | UNRESOLVED`).
   Silent inference is forbidden.
3. No extraction quota — a book yields 0 or many claims; index/TOC entries are
   `LEAD_ONLY`, never executable rules.
4. Independent extractors A and B + adjudication for executable/quantitative
   claims; `UNRESOLVED` is a valid terminal state.
5. Counterevidence is always searched; absence is recorded as
   `NOT_FOUND_IN_SOURCE`.
6. Source claims are never deleted or merged; synthesis links them.
7. Backtest research is strictly separated (research registry vs experiment
   registry); book workers never see backtest results.

## Pipeline stages (one output layer per stage, never edited by later stages)

```text
text parts -> 1 corpus integrity -> 2 book mapping -> 3 claim scouting
-> 4 faithful extraction A -> 5 independent extraction B -> 6 counterevidence
audit -> 7 adjudication -> 8 book-level synthesis -> 9 cross-book canonical
registry -> 10 crypto/V8 translation -> 11 ExpertSpec generation
-> 12 static/PIT validation -> 13 expert compilation -> 14 experiment registry
```

## Layout

```text
research/pipeline_v2/
  pipeline_version.json        frozen protocol + quality targets
  schemas/*.json               data contracts (lead, raw_claim, book_map,
                               source_strategy, crypto_translation, expert_spec,
                               adjudicated_claim, audit)
  tools/
    build_corpus_manifest.py   books/editions/parts + sha256 integrity
    validate.py                hard gates (provenance, no-leak, strategy,
                               falsifiability, PIT, transfer, independent)
  workflows/
    calibration_v2.js          calibration run (map->scout->A/B->audit->
                               adjudicate->synthesize->canonical->translate->
                               spec->validate)
  corpus/books_manifest.json   generated corpus manifest
  processed_books/<book_id>/   per-book artifacts (from runs)
  registry/                    cross-book canonical registry + translations +
                               expert specs
  legacy_v1/                   archived v1 outputs (LEGACY_UNVERIFIED, search
                               hints only)
```

## Calibration plan (Aşama A)

Five books spanning the difficulty spectrum are run through the full pipeline
before the corpus-wide batch:

| book_id | type | book |
|---|---|---|
| book_0002 | low-quality/marketing | 17 Proven Currency Trading Strategies (2013) |
| book_0005 | algorithmic | Algorithmic Trading: Winning Strategies (Chan, 2013) |
| book_0018 | candlestick/chart | The Candlestick Course (Nison, 2003, OCR) |
| book_0042 | academic/statistical | Evidence-Based Technical Analysis (Aronson, 2007) |
| book_0108 | risk management | Trade Your Way to Financial Freedom (Tharp, 2006) |

Calibration measures: A/B extractor agreement, provenance compliance, silent
inference rate, index-only rate, coverage, validation gate pass rate. The
corpus-wide run starts only if calibration passes the gates.

## Known limitations (honest)

- Page-level anchors are approximate: the extraction pipeline preserves parts
  and line numbers but not page boundaries for all books (pdftotext drops
  page breaks for some formats). Page-to-part mapping is a follow-up.
- OCR'd books carry OCR noise; quotes from them are tagged `is_ocr`.
- `legacy_v1` findings are search hints only — they are never auto-migrated.
