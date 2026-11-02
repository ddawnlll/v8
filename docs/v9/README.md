# V9 Architecture Monograph — v1.1 (Model Council Revision)

## Authority and scope

- **Canonical source:** `docs/v9/V9_ARCHITECTURE_MONOGRAPH.md` (same content as the standalone v1.1 Markdown).
- **Rendered artifact:** `site/v9.html` — automatically built, never edited by hand.
- **Historical V8:** `site/index.html` and its underlying `docs/` corpus are NOT changed by this bundle.
- **Active product:** `v8-next/` remains the only active execution implementation.
- **Scientific status:** revised *target architecture and candidate executable contracts*, not successful implementation, trading-edge proof, merge authority, or live deployment approval.
- **Independent critical input:** `MODEL_COUNCIL_SYNTHESIS.md` and cited three blind-review files; the raw reviews are not included in this repo distribution.

## Rebuild

From repository root (Python environment with `markdown-it-py` or `markdown` installed):

```bash
python tools/build_v9_monograph.py \
  --src docs/v9/V9_ARCHITECTURE_MONOGRAPH.md \
  --out site/v9.html \
  --figdir docs/v9/figures
```

The builder embeds all supplied SVG figures and records the source SHA-256 in the generated HTML. Keep the renderer version pinned to obtain byte-identical outputs.

## Implementation protocol

1. Read V8 active boundary; produce local HEAD/D4 implementation inventory with symbols, test paths, and actual defects before coding.
2. Confirm historical audit issues on the currently pinned native replay and independent golden/fault-injection checks.
3. Approve only the `DecisionPolicyV0` mechanical vertical slice first; do not implicitly activate learned routing, new entry logic, stop policy, portfolio rotation or the Pi loop.
4. Require an owner decision for each versioned policy change and separate mechanical, accounting, scientific, and deployment authority.
5. `Kaizen` is a supplementary offline research capability; no LLM calls in trading callbacks.

**Never** treat this monograph as an instruction to merge all the proposed features in one PR.
