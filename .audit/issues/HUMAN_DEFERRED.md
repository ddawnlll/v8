# HUMAN_DEFERRED — decisions requiring human/maintainer authority

Companion to `TRIAGE.md` (§A/§B rows marked HUMAN or residual-DEFER).
Each row: decision needed, competent authority, blocker, next input.
Nothing here is skipped work — all are explicitly non-autonomous under
Constitution Rules 12/14, WORK_ITEM_POLICY, or repo-settings ownership.
No verdict here grants economic authority; everything stays `NO_ECONOMIC_CLAIM`.

## Audit-issue residuals (§A)

- #61 strategy direction (widen R unit / 4h-daily horizons): needs Kaizen-gov + frozen-OOS design; authority: maintainers + D-141 registry. Blocker: none (measurement recorded). Next: preregistered measurement proposal, not a code change.
- #63 per-expert structural `stop_price` mandate: new-variant rule (Constitution: condition-set change = challenger + frozen-OOS + registry). Authority: expert registry (D-141). Next: per-expert challenger proposals.
- #64 structural `target_r` + `w_min` feasibility gate mandate: same variant rule as #63. Authority: D-141 registry. Next: challenger + gate spec.
- #65 literature-condition mapping tables (25 experts): research task; `requires`-field semantics (data-absence vs design-choice). Authority: research lead. Next: handbook-grounded audit (100-book verification noted in #73 scope limits).
- #69 default `round_trip_cost_r` / threshold re-derivation from venue schema: economic-feasibility claim. Authority: maintainers + authority receipt. Next: exchange-schema receipt.
- #70 `bollinger_reversion` Setup-3 RR=0.5 justification or revision: Authority: D-141 registry (`PROVISIONAL_DECISION` record). Next: required-hit-rate write-up or geometry revision challenger.

## docs/issues HUMAN rows (§B)

- AUD003 D-116 parity unmapped (commission/funding/terminal-balance): OPEN_PIN carried by D-159. Authority: D-116 owners + maintainers.
- AUD004B genuine DSR estimator receipt: OPEN_PIN (D-156). Proxy ≠ genuine. Authority: statistics owners.
- AUD005B recoverability challenger promotion: frozen-OOS gate verdict. Authority: D-141 registry.
- AUD008 maker-fill probability: assuming maker fills is prohibited without authority (fill model is `FILL_AT_BAR_CLOSE`). Authority: execution owners + venue receipts.
- AUD009B SaR physical liquidity inputs: absent → fail-closed stands (D-156). Authority: data owners.
- AUD010 taxonomy alignment: gov decision. Authority: committee.
- GOV001 branch protection: repo-settings, maintainer-only. Agent must never attempt. Authority: repo admin.
- KZ005 adaptive sweep authority + e-BH gate: stopping-rule authority. Authority: Kaizen-gov.
- KZ011 05-Feb acceptance proof: single-event overfit risk; acceptance = human verdict. Authority: D-141 registry + maintainers.
- KZ013 pyramiding / KZ014 portfolio heat / KZ015 gov guardrails / KZ016 OI sponsorship: sizing & policy decisions. Authority: maintainers + registry.
- V83_G5 succession authority: G5 stays `NO_ECONOMIC_CLAIM` (D-152). Authority: committee.
- V85 ratification: D-147 non-binding by design. Authority: Central Committee & Yüksek Divan.
- VALIDITY001 deltas: the four D-159 carried OPEN_PINs (G7–G9 naming, evaluator registration, pre-v2 rows, D-116 parity). Authority: respective owners.
- V83 frozen-OOS / shadow promotion verdicts: harness is autonomous, promotion verdicts are not. Authority: registry.

## Explicitly non-goals for autonomous lane

- Merging any PR, pushing to `main`, changing repo settings (AGENTS.md §7).
- Touching `src/v8/` or `tests/` (frozen oracle, boundary audit).
- Emitting `SUPPORTED_EDGE`, profit claims, or threshold/parameter "optimizations" from diagnostics.
- Hand-editing `site/*.html` (builder only).
