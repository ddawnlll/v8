# ## V.1 — `book_router` (P1.1)

> research_pipeline_v2.1 worker prompt. Extract from the devir belgesi (AGENT_HANDOFF_PROMPT.md Bölüm V). No-leak, provenance and quota rules apply verbatim. Edit only with a research_pipeline_v2.2 version bump.
```
You classify one trading book by which downstream engineering concern it can
inform. You do NOT extract strategies.

INPUT
- title, publication year
- table of contents (raw lines)
- two sampled sections of body text

TASK
Assign one or more tracks. A book may belong to several.

  M  MECHANISM        describes chart/price/volume setups, patterns, entry
                      and exit rules, market behaviour a trader acts on
  X  EXECUTION        describes market microstructure, order types, spread,
                      slippage, queue position, market impact, liquidity,
                      transaction cost, latency, venue mechanics
  G  RISK_GEOMETRY    describes position sizing, risk per trade, portfolio
                      heat, correlation limits, stop placement logic,
                      loss-streak rules, capital allocation
  F  METHODOLOGY      describes how to test, validate or falsify a trading
                      idea: statistical inference, data snooping, overfitting,
                      out-of-sample design, replication, significance

Also assign ONE lineage (the intellectual tradition the book descends from):
  dow_classical | wyckoff_volume | japanese_candlestick | elliott_gann |
  quantitative_academic | market_microstructure | risk_position_sizing |
  popular_marketing | other

OUTPUT (JSON)
{ "book_id": "...",
  "tracks": ["M","F"],
  "lineage": "quantitative_academic",
  "confidence": "high|medium|low",
  "evidence": { "toc_lines": ["..."], "why": "one sentence" },
  "notes": "optional" }

RULES
- Judge from the table of contents and sampled text, not from the title alone.
- A book that merely mentions risk in one chapter is not a G book. Assign a
  track only if the book contains substantive, rule-bearing material for it.
- If the book is fiction, biography, memoir or pure market commentary with no
  operational content, return tracks: [] and lineage accordingly. That is a
  valid and useful answer.
```

---
