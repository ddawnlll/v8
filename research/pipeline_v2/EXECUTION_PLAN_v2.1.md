# research_pipeline_v2.1 — YÜRÜTME SPESİFİKASYONU (agent devir belgesi)

**Bu belgeyi okuyan agent'a:** Gerekçe `RESEARCH_STRATEGY_v2.1.md`
dosyasındadır; onu bir kez oku, sonra bu belgeyi adım adım uygula.
Bu belge **yürütülecek olandır**. Burada tanımlanmamış bir karar
çıkarsa **uydurma** — `registry/open_questions.jsonl`'e yaz ve insana sor.

`pipeline_version: research_pipeline_v2.1` · `schema_version: 2.0` (değişmedi)
**Kilitli kapsam:** 125 kitap (tam korpus) · track F + M + X + G (dördü aktif)

---

## 0. Ön koşullar — bunlar ZATEN VAR, yeniden üretme

| Var olan | Yol | Durum |
|---|---|---|
| Korpus manifesti (125 kitap, sha256) | `corpus/books_manifest.json` | tamam |
| Part metinleri (331 dosya) | `books/_extracted/_parts/*.txt` | tamam |
| Deterministik scout lead'leri (12.457) | `corpus/leads/*.jsonl` | tamam |
| Lead pack'leri (487) | `corpus/leads_packs/` | tamam |
| Şemalar (8 adet) | `schemas/*.json` | tamam |
| Donmuş protokol + kalite hedefleri | `pipeline_version.json` | tamam |
| Legacy v1 arşivi | `legacy_v1/` | **sadece arama ipucu** |

**Boş ve senin dolduracağın:** `processed_books/`, `registry/`, `prompts/`.

**Yeniden ÜRETME:** manifest, part metinleri, lead'ler. Bunlar donmuştur;
sha256 değişirse tüm alt katman geçersizleşir.

---

## 1. Devralınan sert invariantlar (ihlali = run iptali)

Bunlar v2.0'dan gelir, tartışmaya kapalıdır:

1. **No-leak.** Ham kaynak katmanında (leads → adjudicated_claims →
   source_strategies) `BTC`, `crypto`, `perpetual`, `funding`, `1h`, `USDM`,
   `ATR stop`, `NEXT_BAR_CLOSE`, `frozen reference`, `1R`, `V8` geçemez —
   kaynak metnin kendisi bunu söylemiyorsa. `tools/validate.py` reddeder.
2. **Provenance zorunlu.** Her alan bir etiket taşır: `SOURCE_EXPLICIT |
   SOURCE_DERIVED | MARKET_TRANSLATION | V8_OPERATIONALIZATION |
   EXPERIMENTAL_ASSUMPTION | V8_DEFAULT | UNRESOLVED`. Sessiz çıkarım yasak.
3. **Kota yok.** Bir kitap 0 claim de verebilir 150 de. "Her kitaptan N bulgu"
   talebi üretme.
4. **Katman değişmezliği.** Sonraki aşama önceki katmanı **düzenlemez**,
   yalnız yeni katman yazar. Düzeltme gerekiyorsa yeni kayıt + `supersedes`.
5. **`UNRESOLVED` geçerli bir terminal durumdur.** Uydurulmuş kesinlikten
   daima üstündür. `NOT_SPECIFIED` doldurulmaz.
6. **Backtest ayrı.** Bu run hiçbir fiyat verisine, tape'e, backtest sonucuna
   bakmaz. Book worker'ları sonuç görmez.

### v2.1'in eklediği invariant

7. **Prompt lint.** Aşama 3–8 worker prompt şablonlarının **kendisi** de
   yasaklı token listesinden temiz olmalıdır. Bir extractor prompt'unda "BTC"
   geçiyorsa çıktı temiz olsa bile kirlenmiştir. `prompts/*.md` dosyaları da
   `validate.py --lint-prompts` ile denetlenir.

---

## 2. Rol sözleşmeleri (worker contracts)

Her worker için: **ne görür · ne görmez · ne üretir**. "Ne görmez" kısmı
ihlal edilirse veri geçersizdir.

| Worker | Görür | **GÖRMEZ** | Üretir |
|---|---|---|---|
| `book_router` | başlık, TOC, 2 örnek section | — | track etiketi + yoğunluk skoru |
| `claim_triage` | 40 lead anchor'ı (batch) | registry, diğer kitaplar | route + claim_type + drop kararı |
| `counterevidence_sweeper` | kitabın FAILURE/METHODOLOGY lead'leri + section'lar | claim'ler, mekanizma kaydı | caveat/failure/contradiction kayıtları |
| `novelty_gate` | lead + **dondurulmuş** registry snapshot | A/B çıktıları | MATCH \| VARIANT_OF \| NEW |
| `extractor_a` | lead + section + komşu bağlam | **B'nin çıktısı**, crypto/V8 sözlüğü | `raw_claim_a` |
| `extractor_b` | aynı lead + aynı section (**ayrı çağrı, ayrı bağlam**) | **A'nın çıktısı**, crypto/V8 sözlüğü | `raw_claim_b` |
| `skeptic_auditor` | claim + kitabın counterevidence indeksi | — | `audit` |
| `adjudicator` | A, B, tam pasaj, audit | — | `adjudicated_claim` (alan bazlı) |
| `book_synthesizer` | tek kitabın **tüm** adjudicated claim'leri | diğer kitaplar, crypto/V8 | `source_strategies` |
| `canonical_registry` | tüm kitapların source_strategies'i | crypto/V8 | ilişki + canonical kimlik |
| `crypto_translator` | source_strategy + canonical kayıt | — | `crypto_translation` (**crypto/V8'e izinli TEK worker**) |
| `expert_spec_builder` | translation | ham kitap metni | `expert_spec` |
| `expert_validator` | spec + tüm üst katman | — | pass/fail + blocking_reasons |

**Extractor bağımsızlığı nasıl sağlanır:** A ve B ayrı `agent()` çağrılarıdır.
B'nin prompt'u A'nın çıktısını **içermez** ve A'nın çalıştığından haberdar
değildir. Aynı model kullanılabilir; bağımsızlık bağlam izolasyonundan gelir,
model farkından değil.

---

## 3. Faz planı

Her fazın: **girdi · işlem · çıktı (tam yol) · kabul kapısı · durma davranışı**.

---

### P0 — Lokal düzeltmeler (model çağrısı: 0)

Bu faz tamamen deterministiktir. LLM kullanma.

**P0.1 — Sayfa haritası.**
Girdi: `books/_extracted/_parts/*.txt`
İşlem: form-feed (`\f`) sayarak part içi sayfa sınırlarını çıkar; kitabın
`page_count` değeriyle karşılaştır.
Çıktı: `corpus/pages/<part_id>.pagemap.json` — `[{page, char_start, char_end,
line_start, line_end}]`; ayrıca `books_manifest.json` içindeki part
kayıtlarının `page_start`/`page_end` alanları doldurulur (yeni dosya:
`corpus/books_manifest.v21.json`, orijinal **değiştirilmez**).
Kapı: `\f` sayısı ile `page_count` farkı **>%5** olan kitaplar
`page_anchor_status: UNMAPPED` işaretlenir — bu kitaplarda claim'ler sayfa
yerine `part_id + line_range` ile anchor'lanır, sayfa **uydurulmaz**.

**P0.2 — Section re-chunk.**
Girdi: part metinleri + pagemap.
İşlem: part'ları 4.000–8.000 token'lık section'lara böl; sınırları başlık
sezgisi (satır başı büyük harf, numaralı başlık, boş satır kümesi) ile hizala,
paragraf ortasından kesme.
Çıktı: `corpus/sections/<book_id>.sections.jsonl` —
`{section_id, book_id, part_id, order, char_start, char_end, page_start,
page_end, token_estimate, prev_section_id, next_section_id}`
Kapı: hiçbir section atlanmamış (char aralıkları part'ı tam kaplar), sıra
boşluksuz, `coverage == 1.0`.

**P0.3 — Lead → section bağlama.**
Her lead'in `local_start_line`/`local_end_line` değeri bir `section_id`'ye
eşlenir; sayfa numarası pagemap'ten türetilir.
Çıktı: `corpus/leads_v21/<book_id>.jsonl` (lead'e `section_id`, `page_start`,
`page_end`, `page_anchor_status` eklenmiş hali). Orijinal `corpus/leads/`
**değiştirilmez**.

**P0.4 — Kitap sıralaması (bilgi yoğunluğu).**
Deterministik skor: `density = (strong_type_lead_sayısı / kitap_token/1000)`.
`strong_type` = ENTRY/TRIGGER/STOP/EXIT/INVALIDATION/POSITION_SIZING/
RISK_RULE/EMPIRICAL_CLAIM/METHODOLOGY.
Çıktı: `registry/book_order.json` — azalan yoğunluk sırası + her kitabın
lead sayısı ve token'ı.

**P0.5 — Tur (round) bölümlemesi.**
125 kitap → **13 tur**: Tur 1 = 10 tohum kitap (aşağıdaki soy çeşitliliği
kuralıyla), Tur 2–13 = kalan 115 kitap, yoğunluk sırasında 10'arlı.
**Tohum kuralı:** Tur 1'de her soydan en az bir kitap bulunmalı —
Dow/Edwards-Magee · Wyckoff/hacim · Japon mumları · Elliott-Gann ·
kantitatif-akademik · mikroyapı/execution · risk-sizing · düşük kaliteli
pazarlama (kalibrasyon için bilinçli olarak). Soy ataması P0'da başlık
anahtar kelimesiyle önerilir, P1'de `book_router` doğrular.
Çıktı: `registry/rounds.json`.

**P0 kabul kapısı:** `tools/coverage.py` tüm kitaplarda `coverage == 1.0`
raporlar; sayfa eşlenmemiş kitap listesi açıkça yazılır.

---

### P1 — Kalibrasyon + recall denetimi (~155 çağrı, ~35 dk)

**P1.1 — `book_router`, 125 çağrı.**
Girdi/çıktı: bölüm 2'deki sözleşme.
Çıktı: `registry/book_routing.json` —
`{book_id, tracks: [M|X|G|F], lineage, confidence, evidence: {toc_lines}}`.
Bir kitap birden çok track'e ait olabilir.

**P1.2 — Scout recall denetimi, ~30 çağrı. PLANIN EN KRİTİK ADIMI.**
Örneklem: 6 kitap (M-track yoğun · M-track seyrek · X · G · F · OCR'lı bir
kitap) × tabakalı rastgele 2 section = 12 section. Her section'da ayrıca
kontrol için 1 "lead'siz" section (regex hiç isabet vermemiş) seçilir → +6.
İşlem: seçilen section'ları **tam** LLM scout ile oku (regex çıktısını
GÖRMEDEN). Sonra karşılaştır.
Çıktı: `registry/scout_recall_report.json` —
```
{ per_section: [{section_id, llm_leads, regex_leads, matched, missed,
                 missed_examples:[{text, claim_type, why_regex_missed}]}],
  recall_overall, recall_by_claim_type, precision_estimate,
  zero_lead_sections_false_negative_rate }
```
**Karar kuralı (uygula, tartışma):**
- `recall ≥ 0.85` → deterministik scout ön-filtre olarak kabul; P2 lead
  düzeyinde çalışır.
- `0.60 ≤ recall < 0.85` → lexicon'a eksik desenler eklenir **ve** P2 triage
  **section düzeyinde** çalışır (worker lead'i değil section'ı görür).
  Maliyet artışı ~2×; kabul edilir.
- `recall < 0.60` → deterministik scout ön-filtre olarak **reddedilir**;
  P2 tüm korpusta section düzeyinde LLM scout olur. Bu durumda süre tahmini
  yeniden hesaplanıp **insana bildirilir** (HITL-1).

**P1.3 — 5 kitaplık tam kalibrasyon.**
v2.0'ın seçtiği beş kitap korunur: `book_0002` (pazarlama), `book_0005`
(algoritmik), `book_0018` (mum/OCR), `book_0042` (akademik), `book_0108`
(risk). Bu beş kitap P2→P6 zincirinden **uçtan uca** geçirilir.
Ölçülen: A/B uyum oranı, provenance uyumu, sessiz çıkarım oranı,
index-only oranı, validation kapısı geçiş oranı, **çağrı başına gerçek süre**.
Çıktı: `registry/calibration_report.json`.

**★ HITL-1 — İNSAN ONAYI ZORUNLU.**
Şunlar sunulur: recall sayısı · kaçan claim örnekleri · A/B uyumsuzluk
örnekleri · 5 kitabın ExpertSpec çıktıları · **ölçülmüş süre/çağrı ile
güncellenmiş toplam tahmin**. İnsan onaylamadan P2 korpus koşusu başlamaz.

---

### P2 — Triage ve routing (~312 çağrı, ~17 dk)

Girdi: 12.457 lead (veya P1.2 kararına göre section'lar), 40'lık batch.
İşlem: her lead için karar:
```
route:      M | X | G | F | DROP
claim_type: STRATEGY_SETUP | TRIGGER_RULE | ENTRY_RULE | INVALIDATION_RULE |
            EXIT_RULE | POSITION_SIZING | REGIME_FILTER | LIFECYCLE_RULE |
            PORTFOLIO_RISK_RULE | FEATURE_CLAIM | EMPIRICAL_CLAIM |
            FAILURE_EXAMPLE | AUTHOR_CAVEAT | METHODOLOGY_RULE
drop_reason (DROP ise): INDEX_ONLY | TOC | MOTIVATIONAL | BIOGRAPHICAL |
            ADVERTISEMENT | REGEX_FALSE_POSITIVE | DUPLICATE_OF:<lead_id>
needs_wider_context: bool
```
Çıktı: `processed_books/<book_id>/triage.jsonl` ve
`processed_books/<book_id>/rejected_leads.jsonl`.
Kapı: hiçbir lead karar dışı kalmaz (`triaged + rejected == input`).
**DROP edilen lead silinmez**, gerekçesiyle saklanır.

---

### P3 — Counterevidence korpus süpürmesi (~125 çağrı, ~7 dk)

**Bu faz P4'ten ÖNCE çalışır.** Sırayı değiştirme — gerekçe stratejide.

Girdi: kitap başına F/FAILURE/METHODOLOGY etiketli lead'ler + ilgili
section'lar (`AUTHOR_CAVEAT`, `FAILURE_EXAMPLE`, `METHODOLOGY_RULE`).
İşlem: kitabın kendi içindeki uyarı, başarısızlık örneği, koşul kısıtı,
ve **kendi içinde çelişki** kayıtlarını çıkar; her biri sayfa alıntılı.
Çıktı: `processed_books/<book_id>/counterevidence.jsonl`
```
{ book_id, page, exact_text, kind: CAVEAT|FAILURE_EXAMPLE|CONTRADICTION|
  SCOPE_LIMIT|REFUTATION, normalized_meaning, topic_terms: [...],
  applies_to_hint: [mechanism terimleri] }
```
Ayrıca global indeks: `registry/counterevidence_index.json` — topic_terms →
kayıt listesi. P4'ten sonraki her `skeptic_auditor` **bu indekse bakar**,
kitabı yeniden taramaz.
Kapı: F-track kitaplarının **hepsi** işlenmiş olmalı. Bir kitap 0
counterevidence üretirse kayıt `counterevidence_status: NOT_FOUND_IN_SOURCE`
olur — bu "güçlü kitap" demek değildir, sadece bulunmadı demektir.

---

### P4 — Mekanizma çıkarımı, novelty-gated, turlu (~1.150 çağrı, ~62 dk)

**Turlu çalışır. Tur içinde registry DONDURULMUŞTUR.** Bu, 14 paralel
agent'ın aynı yeni family'yi ayrı ayrı ilan etmesini önler ve run'ı
deterministik yapar.

Her tur (10 kitap) için sıra:

**P4.a — Novelty gate (tur başına ~1 çağrı/lead-kümesi).**
Girdi: turun M-track lead'leri + `registry/canonical_behaviors.jsonl`'in
**tur başındaki snapshot'ı** (kompakt: ~60 kayıt, her biri market-nötr
mekanizma taslağı).
Mekanizma taslağı şeması (piyasa-nötr, crypto terimi yok):
```
{ canonical_behavior_id, canonical_family_id,
  precondition_class, boundary_event, follow_through_state,
  resolution_event, direction_relation }
```
Karar: `MATCH(behavior_id)` | `VARIANT_OF(behavior_id, difference)` | `NEW`
Çıktı: `processed_books/<book_id>/novelty.jsonl`

**P4.b — Yönlendirme.**
- `MATCH` / `VARIANT_OF` → **T3**: tek güçlü geçiş, 10 lead/çağrı.
  Üretir: sayfa alıntılı `corroboration` kaydı (mevcut behavior'a kanıt
  ağırlığı ekler, yeni family yaratmaz).
- `NEW` → **T4**: `extractor_a` + `extractor_b` + `skeptic_auditor` +
  `adjudicator` (4 çağrı).
- Ayrıca **koşuldan bağımsız T4**: nicel/parametrik claim (`EMPIRICAL_CLAIM`,
  sayı içeren `SOURCE_EXPLICIT` parametre) → MATCH olsa bile T4'e gider.
  Parametreler backtest'te kullanılacak; tek geçişle çıkarılamaz.

**P4.c — Tur sonu birleştirme (merge). Paralel DEĞİL, tek çağrı.**
Turda `NEW` ilan edilen adaylar **birbirleriyle** karşılaştırılır; aynı
mekanizmanın iki farklı kitaptan gelen ilanı tek canonical_behavior'a
indirgenir. Ancak **source variant'lar korunur** — Elder'ın ve Connors'ın
kayıtları ayrı kalır, sadece canonical kimlik ortaklaşır.
Çıktı: `registry/canonical_behaviors.jsonl` güncellenir (append + supersede,
üzerine yazma yok).

**P4.d — Doyum kaydı.**
Çıktı: `registry/saturation_ledger.jsonl`
```
{ round, books:[...], leads_gated, new_families, total_families,
  new_family_rate, consecutive_dry_rounds, t4_mode: ON|DOWNGRADED }
```
**İndirgeme kuralı:** `consecutive_dry_rounds >= 3` → sonraki turlar
`t4_mode: DOWNGRADED` (NEW ilanları hâlâ T4, ama MATCH/VARIANT için nicel
claim istisnası kapanır). Bir turda yeni family çıkarsa sayaç sıfırlanır ve
**T4 yeniden açılır**. Kapsama asla daralmaz — her kitap her turda okunur.

**★ HITL-2 — Tur 3 sonunda İNSAN ONAYI.**
Sunulur: doyum eğrisinin ilk üç noktası · o ana kadarki family ontolojisi ·
"bu ayrımlar gerçekten farklı mekanizma mı yoksa aynı şeyin varyantı mı"
sorusu. Ontoloji çok kaba ise doyum **yapay olarak erken** görünür; bunu
sadece insan yakalar.

---

### P5 — X ve G track'leri (~120 çağrı, ~7 dk)

Dar ve yoğun. Novelty gate **yok** — bu track'lerde tekrar zaten az.

**X (execution/mikroyapı) → `simulator.py` politikasını besler.**
Çıkarılacaklar: emir tipi semantiği, spread/slippage modeli, kuyruk pozisyonu,
adverse selection, market impact, fill varsayımı, gecikme, seans/likidite
yapısı. Kaynak örneği: Harris *Trading and Exchanges* (metni zaten
`research/text/61_external_...` altında), Kissell, algoritmik execution
bölümleri.
Çıktı: `registry/execution_facts.jsonl` — her kayıt sayfa alıntılı,
`transfer_risk` alanı zorunlu (24/7 perpetual piyasaya taşınabilir mi).

**G (risk geometrisi & sizing) → `risk.py` / `lifecycle.py`.**
Çıkarılacaklar: pozisyon boyutlandırma kuralları, risk/işlem, ısı (heat)
limitleri, korelasyon kısıtları, ardışık kayıp kuralları, stop yerleşimi
mantığı, R tanımları.
Çıktı: `registry/risk_geometry_rules.jsonl`

**Neden bu ayrı bir track:** P4'ün ürettiği ExpertSpec'lerin büyük kısmı
`missing_geometry: {stop: true, target: true}` taşıyacak — kaynak kitap
stop/target vermediği için (ve bu doğru davranış, uydurmuyoruz). G-track
bu boşluğu **merkezi olarak** kapatır. Her expert'in kendi stop'unu uydurması
yerine tek bir `RiskGeometryResolver` politikası kaynak-izlenebilir olur.

---

### P6 — Sentez → canonical → translation → ExpertSpec (~240 çağrı, ~13 dk)

**P6.a — `book_synthesizer`.** Kitap başına, **o kitabın tüm claim'leri
bittikten sonra** (part part değil). Çıktı:
`processed_books/<book_id>/source_strategies.jsonl`

**P6.b — `canonical_registry`.** Cross-book ilişkiler:
`EXACT_DUPLICATE | CORROBORATES | REFINES | SPECIALIZES | GENERALIZES |
CONTRADICTS | SIMILAR_MECHANISM | DIFFERENT_BEHAVIOR`.
Source variant'lar **silinmez**. Çıktı:
`registry/strategy_relationships.jsonl`, `registry/canonical_families.json`

**P6.c — `crypto_translator`.** Crypto/V8 sözlüğüne izinli **tek** worker.
Her alan provenance taşır; veri yoksa `DATA_BLOCKED`.
Çıktı: `registry/crypto_translations.jsonl`, `registry/data_blocked.jsonl`

**P6.d — `expert_spec_builder`.** Sadece Candidate üretir; position size,
leverage, portfolio admission, ranking **üretmez** (Constitution rule 6, 14 —
router/scorer/ranker gated ve ABSENT).
Çıktı: `registry/expert_specs.jsonl`

**P6.e — `expert_validator`.** v2.0'ın altı kapısı + v2.1'in üç kapısı.
Geçemeyen spec `SPEC_INCOMPLETE` / `NOT_EXECUTABLE` / `DATA_BLOCKED` olarak
kalır — **düzeltilmez, uydurulmaz**.

---

## 4. Kalite kapıları (validator'ın uygulayacağı tam liste)

v2.0'dan devralınan: **kaynak** (book_id, edition, sayfa/part anchor, exact
passage, source claims, unknowns, caveats) · **sadakat** (provenance eksiksiz,
ham katmanda crypto/V8 yok, index-only değil, grafik yorumu prose'dan ayrı) ·
**executability** (observable prerequisite/setup/trigger/direction/
invalidation) · **PIT** (gelecek bar yok, repaint yok, frozen reference,
rolling normalization geçmişe bakar, trigger zamanı açık) · **translation**
(24/7 farkı, funding/fee, veri listesi, mekanizma hedef piyasada mevcut) ·
**expert** (deterministik, side-effect yok, portfolio kararı yok, geri
izlenebilir, parametre provenance eksiksiz).

v2.1'in eklediği üç kapı:
```
[ ] SATURATION_LOGGED     her tur için yeni family sayısı + oran kayıtlı
[ ] TRIAL_COUNT_LEDGER    önerilen/reddedilen family + varyant sayısı sayılı
[ ] SCOUT_RECALL_MEASURED recall ölçüldü ve kayıtlı; ölçülmeden korpus koşusu yok
```

### `registry/trial_ledger.jsonl` — neden birinci sınıf çıktı

Deflated Sharpe'ın `N`'i **sonradan uydurulamaz**. Her family önerisi,
reddi ve varyantı sayılmalı:
```
{ event: FAMILY_PROPOSED | FAMILY_REJECTED | FAMILY_MERGED | VARIANT_ADDED,
  canonical_family_id, canonical_behavior_id, variant_id,
  source_strategy_ids, round, reason, timestamp }
```
`base.py` ontolojisi gereği **varyantlar çokluk düzeltmesinde tek birim
sayılır** — ledger bunu family düzeyinde toplayabilecek şekilde yazılmalıdır.

---

## 5. Durum makinesi

```
UNSEEN → MAPPED → SCOUTED → TRIAGED → [NOVELTY_GATED]
      → EXTRACTED_A → EXTRACTED_B → AUDITED → ADJUDICATED
      → BOOK_SYNTHESIZED → CANONICAL_LINKED → TRANSLATED
      → EXPERT_SPEC_READY → QA_PASSED
```
Alternatif duraklar (hepsi geçerli terminal):
`LEAD_ONLY · CORROBORATION_ONLY · SOURCE_INCOMPLETE · UNRESOLVED ·
DATA_BLOCKED · NOT_EXECUTABLE · REJECTED · DUPLICATE_SOURCE`

Her kayıt **neden durduğunu** taşır:
```yaml
status: SOURCE_INCOMPLETE
blocking_reasons: [no_observable_trigger, only_index_reference]
```

---

## 6. Çıktı yerleşimi (v2.0 layout'u korunur)

```
processed_books/<book_id>/
  manifest.json  book_map.json  coverage.json  triage.jsonl
  novelty.jsonl  raw_claims_a.jsonl  raw_claims_b.jsonl  audits.jsonl
  adjudicated_claims.jsonl  corroborations.jsonl  source_strategies.jsonl
  quantitative_claims.jsonl  counterevidence.jsonl  unresolved.jsonl
  rejected_leads.jsonl  book_audit_report.json

registry/
  book_routing.json  book_order.json  rounds.json
  scout_recall_report.json  calibration_report.json
  canonical_families.json  canonical_behaviors.jsonl
  strategy_relationships.jsonl  counterevidence_index.json
  execution_facts.jsonl  risk_geometry_rules.jsonl
  crypto_translations.jsonl  expert_specs.jsonl
  data_blocked.jsonl  saturation_ledger.jsonl  trial_ledger.jsonl
  research_decisions.jsonl  open_questions.jsonl  run_ledger.jsonl

corpus/
  pages/<part_id>.pagemap.json  sections/<book_id>.sections.jsonl
  leads_v21/<book_id>.jsonl  books_manifest.v21.json
```

Her kayıt şu başlığı taşır (istisnasız):
```yaml
pipeline_version: research_pipeline_v2.1
schema_version: 2.0
model_id: ...
prompt_version: ...
created_at: ...
round: ...
```
Prompt veya şema **batch ortasında değiştirilmez**. Değişiklik gerekiyorsa
`v2.2` olarak yeni batch'te uygulanır ve `research_decisions.jsonl`'e yazılır.

---

## 7. Eşzamanlılık ve batch parametreleri

| Parametre | Değer | Gerekçe |
|---|---|---|
| Eşzamanlılık | `min(16, cores-2)` | runtime sınırı |
| Triage batch | 40 lead/çağrı | anchor'lar ~1.100 karakter |
| Corroboration (T3) batch | 10 lead/çağrı | daha fazla bağlam gerekir |
| T4 | 1 lead = 4 çağrı | A, B, audit, adjudicate |
| Tur büyüklüğü | 10 kitap | merge adımının makul kalması için |
| Novelty registry snapshot | tur başında dondurulur | determinizm + yarış önleme |

Merge (P4.c) ve canonical registry (P6.b) **bariyer** adımlarıdır — tüm
tur/korpus sonuçlarını birlikte görmeleri gerekir. Diğer her şey pipeline'dır,
bariyer koyma.

---

## 8. İnsan onay noktaları (HITL)

| # | Ne zaman | Ne sunulur | Neden insan |
|---|---|---|---|
| **HITL-1** | P1 sonu | recall sayısı, kaçan claim örnekleri, A/B uyumsuzlukları, 5 kitabın spec'leri, **ölçülmüş süre** | Ölçülmemiş recall ile 125 kitap koşmak geri dönülmez israf |
| **HITL-2** | P4 tur 3 sonu | doyum eğrisi ilk 3 nokta + family ontolojisi | Kaba ontoloji doyumu yapay erken gösterir; bunu metrik yakalamaz |
| **HITL-3** | P6.b sonrası | dondurulacak family kümesi + trial ledger N'i | Bu sayı backtest fazının istatistiksel geçerliliğini belirler; dondurulduktan sonra değiştirilemez |

---

## 9. Kapsam DIŞI (bu run'da yapılmayacak)

- **Expert compilation (v2.0 stage 13).** `src/v8/` altına kod yazmak
  `D-032` gereği register kararı + CHANGELOG girdisi ister. Bu run
  **QA_PASSED ExpertSpec'te biter**. Derleme ayrı ve gated bir adımdır.
- **Backtest / experiment registry (stage 14).** Family kümesi ve trial
  ledger dondurulmadan hiçbir ölçüm başlamaz.
- **Legacy v1 migrasyonu.** 1.080 v1 bulgusu `LEGACY_UNVERIFIED` kalır;
  yalnızca P4 sonunda **recall kontrol listesi** olarak kullanılır:
  "v1'de X vardı, v2.1 bunu buldu mu?" Bulmadıysa `open_questions.jsonl`.
  Otomatik `RawClaim`'e çevirme **yasak**.
- **Gated bileşenler.** Router, shared scorer, ranker, RL execution, online
  learning — ExpertSpec bunlara referans veremez (Constitution 6, 14).
- **Ekonomik iddia.** Hiçbir çıktı kârlılık, doğrulanmış execution veya
  terfi etmiş sistem ima edemez (Constitution 12).

---

## 10. Bitti tanımı (definition of done)

```
[ ] 125 kitabın hepsi coverage == 1.0
[ ] 12.457 lead'in hepsi triaged veya rejected (gerekçeli)
[ ] scout_recall_report.json mevcut ve recall sayısı kayıtlı
[ ] her kitapta counterevidence.jsonl mevcut (boşsa NOT_FOUND_IN_SOURCE)
[ ] saturation_ledger 13 tur için eksiksiz
[ ] trial_ledger N'i hesaplanabilir durumda
[ ] canonical_behaviors dondurulmuş, HITL-3 onaylı
[ ] her expert_spec QA_PASSED veya gerekçeli terminal durumda
[ ] validate.py --lint-prompts temiz (prompt'larda leak yok)
[ ] docs/CHANGELOG.md ve decisions/DECISION_REGISTER.md güncel
```

---

## 11. Çalıştıran agent'a dürüst uyarılar

1. **Recall ölçülmeden korpus koşusu başlatma.** Tek geri dönülmez hata bu.
2. **`NOT_SPECIFIED`'ı doldurma.** Kaynak stop vermiyorsa vermiyor. Uydurulmuş
   kesinlik, bu boru hattının var olma sebebini yok eder.
3. **Novelty gate'i paralelde registry yazarken çalıştırma.** Tur snapshot'ı
   dondurulmalı, yoksa aynı family 5 kez ilan edilir ve doyum eğrisi bozulur.
4. **Grafik açıklamasını prose kuralıyla karıştırma.** Bir şekilde sonradan
   görülen yapı operasyonel kural değildir.
5. **İndeks/TOC girdisi asla executable claim olamaz** — sadece başka sayfaya
   yönlendiren `LEAD_ONLY`.
6. **Bir kitabın 0 claim vermesi başarısızlık değildir.** Kota yok.
7. **Süre tahminleri (45 s/çağrı, eşzamanlılık 14) ölçülmemiş varsayımdır.**
   P1.3'te gerçek değeri ölç, tabloyu güncelle, HITL-1'de bildir.
8. **40–80 family beklentisi öngörüdür, ölçüm değildir.** Tur 1–3 bunu
   doğrular ya da çürütür; çürütürse HITL-2'de söyle, planı savunma.
