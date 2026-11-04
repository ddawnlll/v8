# V9 — Market-Aware Adaptive Trading Intelligence

## Single source of truth

**Canonical and only normative V9 architecture:** [V9_ARCHITECTURE_MONOGRAPH.md](V9_ARCHITECTURE_MONOGRAPH.md), `V9-ARCH-RFC-1.4`.

The older RFC 1.0–1.3.2 texts survive in **Git history/review provenance** only, not as a competing specification. Do **not** instruct agents to choose between RFC 1.0 and RFC 1.3.2 or reference a nonexistent `V9_ARCHITECTURE_MONOGRAPH_v1.md` in this repository. For issue/milestone planning, read the single current Markdown file.

- **Product definition:** a continuously evaluating, market-aware trader; **not** an audited V8 baseline, a single veto strategy or an automatic money-maker.
- **Target intelligence:** multi-horizon `MarketBelief`, all **28 existing experts** as context-conditioned evidence sources with abstention, canonical recurrent `OpportunityBook`, unified `WAIT/ENTER/HOLD/REDUCE/EXIT/ABSTAIN` trader decision, position thesis evaluation, portfolio/capital constraints.
- **Safety/realism:** one existing hard risk + Nautilus execution authority, durable identity/outbox, stop/partial-fill correctness, source/PIT bounds, qualified fees/funding/mark/equity, independent audit and OOS isolation.
- **First product-visible proof:** `V9-INT-001..006` full integrated **shadow** feedback loop using synthetic/PIT test events with zero native adaptive orders. No completed V9 without it.
- **V0:** a mechanical migration/parity comparator, **not** the V9 product. `M1` entry veto is **one optional initial scientific experiment**, not the target architecture.

## GitHub milestone plan — derived only from canonical RFC

1. **M0 Foundation & Safety:** pinned source map, used-path safety, audit and V0 parity.
2. **M1 Market & 28 Expert Intelligence:** event-driven belief/stance/abstention in shadow.
3. **M2 Continuous Trader Brain:** opportunity reevaluation + unified trader + active position + portfolio; `V9_INTEGRATED_SHADOW_VERIFIED`.
4. **M3 Adaptive Trade Management:** scoped entry, position and allocation challenger policies.
5. **M4 Integrated Validation:** joint-policy interactions, full same-capital costed replay, OOS protocol and prospective shadow.

**Separate authorities:** design ≠ shadow implementation ≠ mechanical PASS ≠ economic evidence ≠ owner policy promotion ≠ live deployment. `NO_EDGE` is a valid economic conclusion. A blocked accounting claim does not automatically prevent unrelated read-only shadow tests.

## Repository boundaries

- Only active trader codebase: `v8-next/`; no new execution engine, OMS, safety brain or duplicate OpportunityBook.
- [V9_IMPLEMENTATION_PLAN.md](V9_IMPLEMENTATION_PLAN.md) and [V8_TO_V9_DELTA.md](V8_TO_V9_DELTA.md) are derivative **implementation aids**, not competing normative architectures.
- [../V9_BACKLOG.md](../V9_BACKLOG.md) preserves historical requirements; stale commentary does not override the canonical product goal.
- `site/index.html` belongs to historical V8.
- **`site/v9.html` is currently STALE (legacy v1.1) and NOT canonical** until regenerated from this RFC.

## Rebuild optional HTML reader

```bash
python tools/build_v9_monograph.py \
  --src docs/v9/V9_ARCHITECTURE_MONOGRAPH.md \
  --out site/v9.html \
  --figdir docs/v9/figures
```

Generated HTML must carry the source hash/version and is never edited manually. The original Markdown remains authoritative.

**Status:** Documentation design revision only. PR #507 remains draft/unmerged. No native V9 tests, independent council approval, OOS edge claim or live authority is asserted by this document.
