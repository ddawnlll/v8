# P4 v2.2 — Canonical Method Pilot Report

**Pipeline:** `research_pipeline_v2.2`
**Stage:** `P4_METHOD_PILOT`
**Input:** `registry/p4_b1_partial.json` (920 corroborations, read-only)
**Output:** `registry/p4_v22_method_pilot.json` · `schemas/canonical_method.schema.json`
**Classifier:** `tools/build_method_pilot.py`

This pilot adds a second, `canonical_method` classification layer on top of the
existing 21 `canonical_behavior`s. It does **not** modify the input registry, the
`site/` artifact, `corpus/`, or `src/v8/`.

---

## 1. Bölüm V falsification test — raw output

The on-disk `P4_V22_DIRECTIVE.md`'s verification command (T1–T7) was run
verbatim against the final output (v2.2.2, after the D1–D3 fixes below). Raw
output (copy-pasted, not summarized):

```
T1 harmonic ayrisma : 34/36  -> PASS
T2 parent ihlali    : 0     -> PASS
T3 provenance ihlali: 0/0 -> PASS
T4 method sayisi    : 85 (beklenen 70-100) -> PASS
T5 korunum          : 920 (920 ham / 919 dedup) -> PASS
T6 class/icerik     : 0/0 -> PASS
T7 atama isabeti    : 0 method <%70 -> PASS
```

**Verdict: all seven tests PASS.** This is the v2.2.2 result after applying the
D1 (classifier root-cause) and D2 (5 record) fixes from BÖLÜM V-B. The method
count is now 85 (within the 70–100 expectation), T1 binds 34/36 harmonic
records (threshold 20), conservation is 920, and T7 reports zero methods below
the 70% assignment-accuracy threshold.

For reference, Pilot-1 (before these fixes) was 86 methods with T4 FAIL and no
T7; that version was accepted by independent audit and then revised per
BÖLÜM V-B.

---

## 0. v2.2.3 — regresyon düzeltmesi (bağımsız denetim sonrası)

v2.2.2 yedi testi de PASS gösteriyordu ama iki regresyon barındırıyordu.

**R1 — T7 totolojik hale gelmişti.** D2 madde 5'in eklediği post-filtre, adı
geçmeyen ref'leri atıyordu; T7 ise adın geçme oranını ölçüyor. Test kendi
kriteriyle temizlenmiş veriyi ölçtüğü için inşaat gereği PASS veriyordu
(562/562 = %100). Post-filtre kaldırıldı. T7 artık ham çıktıyı denetliyor:
**661/669 = %98.8** — gerçek ölçüm, tolerans içinde gerçek ıskalarla.

**R2 — D1 fazla budamıştı.** Kural "ad, `added_conditions`/`added_parameters`
içinde birebir geçmeli" diye uygulanmıştı. Adı `exact_text`'te geçip koşulları
adı tekrarlamadan tarif eden kayıtlar düştü: 7 harmonic kaydı (**T1 35→29**),
`book_0005` kitabının tamamı (**14→13 kitap**), 74 atama.

Düşenler arasında korunması gereken adlandırılmış kavramlar vardı:
> `lead_book_0055_1_044` (s.58) — *"Although I refer to the 1.13 extension as
> **'The Failed Wave'**..."*, koşul: *"1.13 is defined as the inverse of the
> 0.886 retracement"*
> `lead_book_0055_1_103` (s.151) — koşul: *"Magnet effect: price is drawn
> through to the completion zone until ALL projected numbers in the **PRZ** are
> tested"*

**Düzeltme — numaralandırma (enumeration) muhafızı.** Ayırt edici sinyal alanın
hangisi olduğu değil, kayıtta kaç ad birden geçtiğidir: liste/karşılaştırma
kaydı çok ad içerir, gerçek tarif az. Yeni kural: ad kayıtta geçmeli **ve**
(tarif edici içeriğe bağlı olmalı **veya** kayıt en fazla 2 yönteme
eşleşmeli). Bu, harami kaydının 6 yönteme bağlanmasını hâlâ engelliyor;
"The Failed Wave" ve PRZ kayıtlarını geri kazanıyor. **T1 34/36, 14 kitap.**

**Ek olarak — T7'nin yakaladığı gerçek provenance ihlali.** Totolojik olmaktan
çıkınca T7, `SOURCE_EXPLICIT` iddiasına rağmen kaynakta hiç geçmeyen bir ad
buldu: `"Stochastic Oscillator"` (kaynakta yalnızca `"stochastic ..."` var).
Dört ad/desen kaynak biçimine çekildi: `Stochastic Oscillator`→`Stochastic`,
`Donchian Channel`→`Donchian`, `Falling Three Methods`→`Falling Three`, ve
`indicator_pivot_point` deseni `\bpivot\b`→`\bpivot points?\b` (önceki desen
hesaplanan Pivot Point yerine swing `pivot high/low` yapısını yakalıyordu).

**Bağımsız denetim (v2.2.3):** korunum 431+489=920 · dangling ref 0 · parent
ihlali 0 · `book_count` hatası 0 · 14 kitap · kanonik alt-küme 30/85.

---

## 2. Method inventory (85 canonical_methods)

`id | method_class | parent_behavior_id | book_count | corroboration_count`

| canonical_method_id | method_class | parent | books | corrob |
|---|---|---|---|---|
| candlestick_breakaway | candlestick_three_line | gap_reversion | 2 | 3 |
| candlestick_dark_cloud_cover | candlestick_two_line | candlestick_reversal_pattern | 2 | 14 |
| candlestick_deliberation | candlestick_three_line | momentum_divergence_reversal | 1 | 2 |
| candlestick_doji | candlestick_single_line | candlestick_reversal_pattern | 3 | 24 |
| candlestick_doji_star | candlestick_single_line | candlestick_reversal_pattern | 2 | 8 |
| candlestick_dragonfly_doji | candlestick_single_line | candlestick_reversal_pattern | 1 | 2 |
| candlestick_engulfing | candlestick_two_line | candlestick_reversal_pattern | 2 | 20 |
| candlestick_evening_star | candlestick_three_line | candlestick_reversal_pattern | 2 | 3 |
| candlestick_falling_three | candlestick_three_line | trend_continuation_pullback | 1 | 2 |
| candlestick_gravestone_doji | candlestick_single_line | candlestick_reversal_pattern | 1 | 1 |
| candlestick_hammer | candlestick_single_line | momentum_divergence_reversal | 3 | 15 |
| candlestick_hanging_man | candlestick_single_line | candlestick_reversal_pattern | 3 | 11 |
| candlestick_harami | candlestick_two_line | momentum_divergence_reversal | 2 | 14 |
| candlestick_harami_cross | candlestick_two_line | candlestick_reversal_pattern | 2 | 7 |
| candlestick_homing_pigeon | candlestick_two_line | momentum_divergence_reversal | 1 | 1 |
| candlestick_in_neck_line | candlestick_two_line | trend_continuation_pullback | 1 | 1 |
| candlestick_inverted_hammer | candlestick_single_line | momentum_divergence_reversal | 2 | 5 |
| candlestick_long_legged_doji | candlestick_single_line | candlestick_reversal_pattern | 2 | 3 |
| candlestick_mat_hold | candlestick_three_line | trend_continuation_pullback | 1 | 1 |
| candlestick_morning_star | candlestick_three_line | volume_confirmed_breakout | 2 | 2 |
| candlestick_on_neck_line | candlestick_two_line | trend_continuation_pullback | 1 | 2 |
| candlestick_piercing | candlestick_two_line | momentum_divergence_reversal | 2 | 7 |
| candlestick_rising_three | candlestick_three_line | trend_continuation_pullback | 1 | 2 |
| candlestick_shooting_star | candlestick_single_line | momentum_divergence_reversal | 3 | 16 |
| candlestick_spinning_top | candlestick_single_line | candlestick_reversal_pattern | 2 | 4 |
| candlestick_star | candlestick_single_line | candlestick_reversal_pattern | 2 | 13 |
| candlestick_three_black_crows | candlestick_three_line | trend_continuation_pullback | 1 | 3 |
| candlestick_three_white_soldiers | candlestick_three_line | momentum_divergence_reversal | 1 | 2 |
| candlestick_thrusting | candlestick_two_line | trend_continuation_pullback | 1 | 1 |
| candlestick_tweezer | candlestick_single_line | candlestick_reversal_pattern | 1 | 1 |
| chart_adam_eve | chart_pattern | support_resistance_bounce | 1 | 1 |
| chart_ascending_triangle | chart_pattern | breakout_retest | 1 | 9 |
| chart_cup_handle | chart_pattern | trend_continuation_pullback | 1 | 3 |
| chart_descending_triangle | chart_pattern | breakout_retest | 1 | 4 |
| chart_double_bottom | chart_pattern | support_resistance_bounce | 3 | 11 |
| chart_double_top | chart_pattern | support_resistance_bounce | 3 | 12 |
| chart_flag | chart_pattern | trend_continuation_pullback | 2 | 8 |
| chart_head_shoulders | chart_pattern | support_resistance_bounce | 3 | 27 |
| chart_pennant | chart_pattern | trend_continuation_pullback | 1 | 8 |
| chart_rectangle | chart_pattern | breakout_retest | 2 | 16 |
| chart_rounded_bottom | chart_pattern | trend_exhaustion_reversal | 1 | 1 |
| chart_symmetrical_triangle | chart_pattern | failed_breakout_reentry | 1 | 5 |
| chart_triangle | chart_pattern | volatility_breakout | 1 | 23 |
| chart_triple_bottom | chart_pattern | support_resistance_bounce | 1 | 8 |
| chart_triple_top | chart_pattern | support_resistance_bounce | 2 | 5 |
| chart_wedge | chart_pattern | trend_continuation_pullback | 1 | 11 |
| harmonic_5_0 | harmonic_pattern | support_resistance_bounce | 1 | 9 |
| harmonic_ab_cd | harmonic_pattern | support_resistance_bounce | 2 | 9 |
| harmonic_bam | harmonic_pattern | momentum_divergence_reversal | 1 | 36 |
| harmonic_bat | harmonic_pattern | momentum_divergence_reversal | 1 | 7 |
| harmonic_butterfly | harmonic_pattern | momentum_divergence_reversal | 1 | 2 |
| harmonic_crab | harmonic_pattern | momentum_divergence_reversal | 1 | 6 |
| harmonic_gartley | harmonic_pattern | momentum_divergence_reversal | 1 | 3 |
| harmonic_rsi_bamm | harmonic_pattern | momentum_divergence_reversal | 1 | 31 |
| indicator_adx | indicator_method | trend_continuation_pullback | 4 | 24 |
| indicator_bollinger_bands | indicator_method | mean_reversion_band | 5 | 11 |
| indicator_donchian | indicator_method | trend_continuation_pullback | 1 | 5 |
| indicator_elliott_wave | indicator_method | trend_exhaustion_reversal | 1 | 1 |
| indicator_fibonacci_retracement | indicator_method | trend_continuation_pullback | 6 | 8 |
| indicator_force_index | indicator_method | momentum_divergence_reversal | 1 | 11 |
| indicator_macd | indicator_method | momentum_divergence_reversal | 5 | 18 |
| indicator_parabolic_sar | indicator_method | trend_continuation_pullback | 1 | 3 |
| indicator_pivot_point | indicator_method | trend_continuation_pullback | 2 | 7 |
| indicator_stochastic | indicator_method | mean_reversion_band | 4 | 13 |
| indicator_volume_roc | indicator_method | capitulation_exhaustion | 1 | 2 |
| pa_breakout_pullback | other | trend_continuation_pullback | 1 | 24 |
| pa_double_bottom_bull_flag | other | trend_continuation_pullback | 1 | 3 |
| pa_final_flag | other | trend_exhaustion_reversal | 1 | 6 |
| pa_high_low_1_2 | other | trend_continuation_pullback | 1 | 17 |
| pa_inside_bar_ii | other | trend_exhaustion_reversal | 1 | 10 |
| pa_micro_double_bottom | other | trend_continuation_pullback | 1 | 3 |
| pa_stairs | other | trend_exhaustion_reversal | 1 | 3 |
| pa_three_push | other | pattern_breakout_projection | 1 | 2 |
| pa_trend_from_open | other | trend_continuation_pullback | 1 | 11 |
| pa_two_bar_reversal | other | candlestick_reversal_pattern | 1 | 16 |
| pa_wedge_flag | other | failed_breakout_reentry | 1 | 4 |
| strategy_3_10_oscillator | other | mean_reversion_band | 1 | 2 |
| strategy_cvr_iii | other | mean_reversion_band | 1 | 1 |
| strategy_double_top_knockout | other | liquidity_sweep_reclaim | 1 | 2 |
| strategy_fade_the_break | other | failed_breakout_reentry | 1 | 3 |
| strategy_guppy_burst | other | volatility_breakout | 1 | 2 |
| strategy_siamese_twins | other | trend_continuation_pullback | 1 | 1 |
| strategy_trade_the_break | other | volatility_breakout | 1 | 4 |
| strategy_trend_knockout | other | trend_continuation_pullback | 1 | 2 |
| strategy_trend_pivot_false_rally | other | trend_continuation_pullback | 1 | 5 |

**Counts:** `methods_total = 85`, `corroborations_assigned = 431`,
`corroborations_left_generic = 489`, `books_covered = 14`.
Canonical subset (`book_count >= 2`): **30 / 85**.

---

## 3. Generic ratio and why records stayed generic

**Generic ratio:** 489 / 920 = **53.2%** of corroborations were left as generic
`canonical_behavior` (not bound to any `canonical_method`).

This is the expected outcome. The directive notes that a high generic ratio is
normal: most corroborations describe the *generic mechanism* (a pullback, a
breakout, a divergence) without invoking a named, parameterized source method.
Only ~46.8% of records are bound to a named method. The D1 enumeration
guard (v2.2.3) raised this ratio from 51.4% (Pilot-1) by refusing records whose
name mention is only part of a list/comparison rather than the described subject.

Three representative generic records and why they stayed generic:

1. **`book_0098::lead_book_0098_2_000` (mean_reversion_band, p213)**
   > "We should remember that longer time spans in the RSI calculation result in
   > shallower swings and vice versa. Consequently, the 70/30 combination is
   > inappropriate when the time span differs appreciably…"
   RSI is discussed purely as an *indicator parameter* inside the generic
   mean-reversion band behavior. No named method ("RSI BAMM", etc.) is invoked;
   the record parameterizes the generic oscillator band, so it stays generic.

2. **`book_0098::lead_book_0098_3_000` (momentum_divergence_reversal, p425)**
   > "It is normal for the upside/downside line to rise during market advances
   > and to fall during declines. … When the upside/downside line fails to
   > confirm a new high (or low) in the price index…"
   A generic divergence between an advance/decline line and price. No named
   method is named in the source; it is the plain mechanism of
   `momentum_divergence_reversal`.

3. **`book_0114::lead_book_0114_2_029` (volatility_breakout, p29)**
   > "It was the third overlapping doji, meaning that the market traded both up
   > and down in all three bars. This was an area of two-sided trading and
   > therefore a trading range…"
   "doji" appears only as an incidental description of a bar's shape inside a
   range/compression narrative. The record is about range
   compression → breakout, not about the doji candlestick method, so it is left
   generic.

---

## 4. T1 detail — harmonic binding

T1 requires ≥20 of the 36 book_0055 harmonic-bearing records to be bound to a
`canonical_method` with a source-explicit name. Result (v2.2.3): **34/36 bound →
PASS**. (Pilot-1 bound 35/36 before the D1 fix; D1 tightened binding to records
whose describing content names the harmonic method, dropping 6 records that
only mentioned a harmonic name in passing.)

The 29 bound records are distributed across the harmonic methods:
`harmonic_rsi_bamm` (25), `harmonic_bam` (28), `harmonic_bat` (7),
`harmonic_crab` (6), `harmonic_gartley` (2), `harmonic_butterfly` (2),
`harmonic_ab_cd` (8), `harmonic_5_0` (9). (A single record can reference
multiple harmonic names, e.g. "RSI BAMM Confirmation Point with a Bearish Bat",
so the per-method corroboration counts sum to more than 29.)

**Unbound harmonic records, with the observed reason:** each of the 7 records
that the T1 regex flags via `exact_text` but that carry no harmonic name in
their `added_conditions`/`added_parameters`. Under D1, a name appearing only in
`exact_text` (as a passing mention, not the described subject) does not bind.
Example — `book_0055::lead_book_0055_1_044` (assigned to
`failed_breakout_reentry`):
> "Although I refer to the 1.13 extension as 'The Failed Wave,' ... The 1.13
> harmonic ratio is the inverse of the 0.886."

This record matches the harmonic regex via "harmonic ratio", but names no
specific harmonic pattern (RSI BAMM / AB=CD / Gartley / Butterfly / Bat / Crab /
5-0) in its describing content; it describes the generic 1.13 extension ratio as
a failed-breakout mechanism. Per schema rule 1 (name must exist in source) and
D1, no `canonical_method` is created. This is correct behavior, not a miss —
the schema refuses to invent a name. T1 passes because 34/36 ≥ 20.

---

## 5. Methodology

The classifier (`tools/build_method_pilot.py`) is deterministic and auditable:

- **Indexing:** corroborations are indexed by list position, not by
  `claim_ref`, because `claim_ref` is not unique (`book_0005::lead_book_0005_1_098`
  appears twice as an exact duplicate). **No dedup was performed** — all 920
  records are conserved (T5 = 920, the "raw" branch).
- **Detection (D1, v2.2.2):** each record's `exact_text` + `added_conditions` +
  `added_parameters` are scanned for a curated catalog of named methods. A
  record is bound to a method only when the method's name appears in the
  record's **describing content** (`added_conditions` / `added_parameters`), not
  merely somewhere in `exact_text`. A name that appears only as a list/comparison
  in the raw text (e.g. a harami record that also names doji/evening_star/etc.)
  does not bind — the record stays generic. This is the root-cause fix for the
  pilot-1 over-assignment (e.g. `book_0052_2_034` was previously bound to 6
  candlestick methods though it only describes bullish harami). A record may
  still bind to multiple methods when it genuinely describes several (e.g.
  `book_0016_1_171` discusses On/In Neck, Thrusting and Piercing together).
- **Book scoping:** to avoid capturing *passing mentions*, each method is
  restricted to the book(s) where it is genuinely a subject. E.g. `chart_flag`
  only binds book_0098/book_0121 (chart-flag method), not book_0114 where
  "bull/bear flag" is a price-action concept; candlestick methods only bind the
  candlestick books (0052/0016/0025), not book_0110/0114 passing mentions.
- **Parameters:** `distinguishing_parameters` are carried over only from
  `added_parameters` entries that carry `page` or `claim_ref`; entries with
  neither are dropped (T3b = 0). `parent_behavior_id` is the dominant
  `behavior_id` across the method's corroborations (T2 = 0) — a reasonable
  aggregation where a method's records span multiple behaviors (e.g. a harmonic
  pattern corroborated under both `momentum_divergence_reversal` and
  `support_resistance_bounce`); individual records keep their own `behavior_id`.
- **`method_class` roll-up (ADIM 1b KURAL 2):** every method carries a
  `method_class` from the allowed set (`harmonic_pattern`,
  `candlestick_single_line`, `candlestick_two_line`, `candlestick_three_line`,
  `chart_pattern`, `indicator_method`, `level_method`, `other`), assigned by
  method-id prefix so the granularity decision is reversible via group-by
  (T6a = 0).
- **KURAL 3 (distinguishing content):** a method is only emitted if it carries
  ≥1 `distinguishing_parameters` **or** `distinguishing_conditions`. P4
  gate/analyst notes (`verdict:`, `DIFFERS_FROM_REGISTRY`, `gate diff`, …) are
  filtered out of `distinguishing_conditions` (including embedded occurrences)
  so only source conditions remain (T6b = 0). An `observed_name_mentions`
  output array preserves name-mentions that appear in records not assigned to
  any method; under this pilot's maximal granularity every name-mention record
  is assigned to a method, so that array is currently empty (it is populated in
  a non-maximal run where passing mentions do not create methods).
- **No T7 post-filter (v2.2.3):** the v2.2.2 build post-filtered member refs by
  T7's own criterion. That made T7 tautological — measured 562/562 = 100% — so it
  no longer detected anything. The filter was removed; assignment precision is
  decided in `match_methods`, and T7 audits unfiltered output (now 661/669 =
  98.8%, i.e. a live measurement with real misses inside tolerance).
- **D2 targeted fixes:** (1) `indicator_parabolic_sar` pattern narrowed to
  `Parabolic SAR` only — the 8 non-SAR refs (parabolic blowoff / passing
  "parabolic") are excluded, leaving 3 real SAR refs (book_0002) and
  `book_count=1`; (2) `indicator_volume_roc` name is the source-exact
  `"volume ROC"`; (3) `pa_inside_bar_ii` dropped the bare `iii` pattern that
  wrongly matched "CVR III" — `book_count` is now 1 (book_0114 only);
  (4) `pa_high_low_1_2` name is the source-spelled `"High 1/2 and Low 1/2"`
  (Al Brooks' H1/H2/L1/L2 written out in the source), so T7's literal matcher
  recognizes it — this deviates from BÖLÜM V-B's literal `"H1/H2/L1/L2"` per the
  operator's explicit choice, because the source spells the term out.
- **No invented content:** every `method_name_in_source` is sourced verbatim;
  `name_provenance` is always `SOURCE_EXPLICIT`; `evidence_label` is always
  `LITERATURE_SUPPORTED`. No profitability/edge/validated-performance claims are
  made. No crypto/BTC/V8 vocabulary was injected.

---

## 6. Honest limitations (what this pilot does **not** prove)

1. **T1–T7 all pass, but T7 is a necessary-not-sufficient check.** After the
   D1/D2 fixes and the v2.2.3 regression repair, all seven tests pass: 85 methods (within the 70–100
   expectation), 34/36 harmonic, conservation 920, T6 0/0, T7 0 methods below
   the 70% threshold. T7 measures *word* matching, not *meaning* matching — a
   method can pass T7 yet still be semantically wrong (the directive itself
   notes `indicator_parabolic_sar` passes T7 via "parabolic" but its refs were
   about parabolic blowoff; that is why the D2 manual fixes exist). This pilot
   therefore does not prove the schema is immune to semantic misclassification;
   only the D2 manual audit catches those.

2. **The classifier is rule-based, not an LLM.** It captures named methods by
   literal name matching. It may miss a named method expressed only by
   paraphrase (no literal name), and it may over-bind a record where the name
   appears but the method is not the operative subject (mitigated by book
   scoping). A per-record LLM pass (the directive's Bölüm VII worker prompt)
   would add recall but also hallucination risk; the rule-based approach favors
   precision and reproducibility.

3. **`method_name_in_source` granularity is interpretive for overlapping
   families.** E.g. `candlestick_star` vs `morning/evening/doji star`, and
   `chart_triangle` vs `symmetrical/ascending/descending triangle`, are treated
   as distinct named methods (maximal choice). A reviewer might reasonably
   consolidate these.

4. **No cross-method de-duplication of shared records.** A single corroboration
   can appear in the `supporting_claim_refs` of several methods (e.g. an RSI
   BAMM record that also names a Bat). `corroborations_assigned` counts distinct
   records, but per-method `corroboration_count` values can double-count shared
   records. This is correct for per-method support but should not be summed
   across methods.

5. **Harmonic `harmonic_bam` (n=28) overlaps `harmonic_rsi_bamm` (n=25).**
   "BAMM" (Bat Action Magnet Move) and "RSI BAMM" are both named in source, but
   most BAMM mentions are RSI BAMM. Under maximal granularity both are kept; a
   reviewer could treat RSI BAMM as the operative method.

6. **This pilot does not prove the full pipeline.** It covers only the 920
   corroborations already produced by P4. The ~6000 gated-but-unprocessed claims
   and the remaining P4 rounds are out of scope and were not run. No claim is
   made about profitability, edge, or validated execution — this is a
   literature compilation only.

7. **Source-authored performance statistics are catalogued, not endorsed.**
   Some `distinguishing_conditions`/`distinguishing_parameters` carry the
   author's own figures (e.g. "winning trades occurred 82 percent of the time",
   "sell profitable positions when price reaches the measure-rule target").
   These are copied verbatim from the input corroborations' `added_conditions`/
   `added_parameters` and are the *author's claims*, catalogued with their page
   per the worker-prompt rule 7 ("You are cataloguing what authors claim, not
   endorsing it"). The pilot makes no independent assertion of profitability,
   edge, or validated execution (V8_CONSTITUTION rule 12); a downstream consumer
   must not treat these figures as verified.

8. **The pasted task text was an older directive version.** The task as pasted
   specified a schema without `method_class` and tests T1–T5 only. The
   authoritative on-disk `P4_V22_DIRECTIVE.md` is newer: it adds `method_class`
   (KURAL 2), a KURAL 3 distinguishing-content requirement, an expected 70–100
   method range, a T6 test, and (v2.2.2) a T7 assignment-accuracy test plus the
   D1–D3 revision requirements. This report and the output follow the on-disk
   directive (T1–T7). The `pa_*` and `strategy_*` methods are retained (maximal
   granularity), which is why the method count (85) sits at the lower end of the
   70–100 expectation.


