# P5 — G / X / F TRACK ÇIKARIMI — AGENT TASK PROMPT (v2.4)

> **Bu dosyanın tamamı görevdir.** Soğuk başlangıç içindir.
>
> **SORU SORMA.** Belirsizlik için Bölüm VI karar tablosu. Orada karşılığı
> olmayan durumda: en muhafazakâr seçenek (üretme / düşür / boş bırak),
> kararı rapora yaz, devam et.
>
> **Dil:** orkestrasyon Türkçe, **worker prompt'ları İngilizce kalır**.
>
> Çelişki sırası: `docs/charter/V8_CONSTITUTION.md` > bu dosya > diğerleri.

Kök: `/Users/hootie/src/v8` · Çalışma dizini: `research/pipeline_v2`

---

## BÖLÜM I — NEDEN BU GÖREV

P4 tamamlandı ve korpusun yalnızca **M (mekanizma)** track'ini işledi. Geriye
kalan üç track hiçbir işleme aşamasına girmemiştir:

```
M mekanizma  : 7211 claim   ✔ P4 işledi (92 kitap, 2739 corroboration, 105 yöntem)
G risk       : 1062 claim   ✗ hiç işlenmedi
F metodoloji :  880 claim   ✗ hiç işlenmedi
X execution  :  490 claim   ✗ hiç işlenmedi
                ───────────
                2432 claim  = korpusun %25'i
```

Bu üç track, V8'in para yoluna doğrudan besleme yapar:

| Track | Neyi besler | V8 karşılığı |
|---|---|---|
| **X** execution | Maliyet modeli gerçekçiliği — Faz 4 kapısının ölçütü "after-cost" | `binance_usdm_costs_v1`, `src/v8/simulator.py` |
| **G** risk | Pozisyon geometrisi, hayatta kalma | `src/v8/risk.py`, `lifecycle.py` ExposureBook |
| **F** metodoloji | Yanlışlama disiplini, data-snooping savunması | `src/v8/lab.py`, deney tasarımı |

**Tasarım zaten var, kod yok.** Prompt'lar yazılmış ama hiçbir workflow onları
çağırmıyor — doğrulandı:

```
prompts/risk_geometry_extractor.v21.md      7.0K   "(P5, G track)"
prompts/execution_facts_extractor.v21.md    1.7K   "(P5, X track)"
```

`grep -o "ROLE('[a-z_]*')" workflows/*.js` çıktısında bu ikisi **yoktur**.

---

## BÖLÜM II — KAPSAM VE SIRA

**Sıra zorunlu: X → G → F.** Gerekçe: X en küçük (490), en yüksek getirili
(maliyet modeli kapının ölçütü) ve en hızlı doğrulanabilir. X biterse desen
kanıtlanmış olur, G ve F aynı deseni ölçekler.

Her track için işlenecek claim listesini şu komutla üret (tahmin etme):

```bash
cd /Users/hootie/src/v8/research/pipeline_v2 && python3 - <<'PY'
import json, glob, collections
out = collections.defaultdict(list)
for f in glob.glob('processed_books/*/claims.jsonl'):
    for l in open(f):
        if not l.strip(): continue
        d = json.loads(l)
        if d.get('route') in ('G', 'X', 'F'):
            out[d['route']].append({'claim_id': d.get('claim_id'),
                                    'book_id': f.split('/')[-2],
                                    'anchor_text': d.get('anchor_text'),
                                    'page_start': d.get('page_start'),
                                    'claim_type': d.get('claim_type')})
for k in ('X', 'G', 'F'):
    json.dump(out[k], open(f'registry/p5_{k.lower()}_input.json', 'w'))
    print(f'{k}: {len(out[k])} claim -> registry/p5_{k.lower()}_input.json')
PY
```

`claim_id` null olan kayıtları **düşür** (korpusta %2.6 böyle kayıt var),
sayısını rapora yaz. Uydurma.

---

## BÖLÜM III — ÇIKTI SÖZLEŞMELERİ

Her track kendi şemasını üretir. Şemaları
`schemas/p5_<track>.schema.json` olarak yaz.

### X — execution facts (`registry/p5_x_execution.json`)

```json
{"claim_ref": "book_0041::lead_book_0041_2_014",
 "fact_class": "slippage | spread | commission | funding | order_type |
                fill_behavior | latency | market_impact | venue_rule",
 "statement": "<kaynaktan birebir alıntı>",
 "quantitative": {"value": "30-100 pips", "context": "after fundamental announcement"},
 "instrument_scope": "forex | equities | futures | options | unspecified",
 "era_hint": "2008",
 "transfer_risk": "HIGH | MEDIUM | LOW",
 "page": 213,
 "provenance": "SOURCE_EXPLICIT",
 "evidence_label": "LITERATURE_SUPPORTED"}
```

`transfer_risk`: kaynağın piyasası kripto perp'ten ne kadar uzaksa o kadar
yüksek. 2008 forex spread'i BTCUSDT perp'e doğrudan taşınamaz — **HIGH**.
Bu alan zorunludur ve `HIGH` olması kaydı geçersiz kılmaz, işaretler.

### G — risk geometry (`registry/p5_g_risk.json`)

```json
{"claim_ref": "...",
 "rule_class": "position_size | stop_placement | max_loss | drawdown_limit |
                exposure_cap | scaling | correlation_limit | capital_preservation",
 "statement": "<birebir alıntı>",
 "parameters": [{"name": "risk per trade", "value": "2% of equity", "page": 88}],
 "conditions": ["applies only to trend-following systems"],
 "conflicts_with": ["<başka claim_ref, çelişki varsa>"],
 "page": 88, "provenance": "SOURCE_EXPLICIT",
 "evidence_label": "LITERATURE_SUPPORTED"}
```

`conflicts_with` önemlidir: kitaplar risk kuralları konusunda **çelişir**
(%1 vs %2 vs %5). Çelişkiyi çözme, **kaydet**. Karşıt görüşü silmek
`V8_CONSTITUTION`'a aykırıdır.

### F — methodology (`registry/p5_f_methodology.json`)

```json
{"claim_ref": "...",
 "principle_class": "data_snooping | out_of_sample | sample_size | overfitting |
                     survivorship_bias | look_ahead | multiplicity | replication |
                     statistical_significance | backtest_pitfall",
 "statement": "<birebir alıntı>",
 "actionable_test": "<bu ilkenin V8 lab'inde nasıl test edileceği, veya null>",
 "page": 44, "provenance": "SOURCE_EXPLICIT",
 "evidence_label": "LITERATURE_SUPPORTED"}
```

`actionable_test` alanını **yalnızca kaynak somut bir prosedür veriyorsa**
doldur. Kendi test fikrini yazma → `null`.

---

## BÖLÜM IV — BAĞLAYICI KURALLAR

1. `statement` kaynaktan **birebir alıntı**. Parafraz, özet, çeviri yok.
2. `provenance` yalnızca `SOURCE_EXPLICIT`. Başka değer gerekiyorsa kayıt
   geçersizdir, üretme.
3. Her `parameters` / `quantitative` girdisi `page` taşımalı. Sayfa yoksa
   `page: null` — **uydurma**.
4. Kaynağın söylemediğini yazma. Boş alan bırakmak, doldurmaktan iyidir.
5. Kaynak piyasası korunur. **Kripto/BTC/perp terminolojisi ham katmana
   sokulmaz** (`pipeline_version.json` invariants). Aktarım riski
   `transfer_risk` ile işaretlenir, metin değiştirilerek değil.
6. **Kârlılık / edge / doğrulanmış execution iddiası yazma**
   (kural 12). Bu bir literatür derlemesidir.
7. Çelişkili kayıtları **koru**. Sentezleme, seçme, uzlaştırma yok.
8. Gated bileşenleri (router, scorer, ranker, RL execution, online learning)
   implemente etme (kural 6, 14).
9. Çıktı JSON'u **elle düzenlenmez** — betikten üretilir.

---

## BÖLÜM V — ÇALIŞTIRMA VE ÇÖKME KORUMASI

- Track başına tur boyu: **5 kitap**.
- Her turdan sonra **HEM** veri dosyasını **HEM** checkpoint'i diske yaz.
  (Önceki P4 çalıştırması yalnızca ara dosya yazıp checkpoint'i güncellemedi;
  3 saat boyunca ilerleme görünmez kaldı.)
- Checkpoint: `registry/p5_<track>.checkpoint.json` — işlenmiş kitaplar, tur,
  sayımlar.
- Yarıda kesilirse checkpoint'ten devam et, baştan başlama.
- **Doygunluk nedeniyle erken durma.** Bir tur 0 kayıt üretirse normaldir.

### Dokunulmayacak dosyalar

```
registry/p4_*.json          P4 çıktıları — salt-okunur
findings_v23.html           üretilen rapor
site/  ·  src/v8/  ·  corpus/  ·  docs/CHANGELOG.md
```

---

## BÖLÜM VI — KARAR TABLOSU (soru sormak yerine)

| Durum | Karar |
|---|---|
| Claim hiçbir `*_class` değerine uymuyor | Kayıt üretme. Sayacı artır, devam et. |
| Claim iki sınıfa birden uyuyor | İkisini de yaz (ayrı kayıt). Bölmek kayıptan iyidir. |
| Sayı var ama birimi belirsiz | `value` alanına kaynağın yazdığı gibi yaz. Yorumlama. |
| Kaynak çelişkili iki kural veriyor | İkisini de kaydet, `conflicts_with` ile bağla. |
| Kaynak kripto öncesi (hepsi öyle) | Normal. `transfer_risk` ile işaretle, metni değiştirme. |
| `claim_id` null | Düşür, say, rapora yaz. |
| LLM çağrısı hata verdi | 2 kez dene, sonra atla + `failed_refs`'e ekle. |
| Token bütçesi bitiyor | Checkpoint yaz, durumu rapora yaz, **dur**. Sessizce kısaltma. |
| Test FAIL | Testi/eşiği değiştirme. Nedeni bul veya FAIL olarak raporla. |
| Tabloda olmayan belirsizlik | En muhafazakâr seçenek + rapora yaz + devam. **Soru sorma.** |

---

## BÖLÜM VII — KABUL TESTLERİ

| Test | Kriter |
|---|---|
| **P1** kapsama | İşlenen claim = girdi claim − null'lar. Eksikse hangi kitap/neden. |
| **P2** provenance | `provenance != SOURCE_EXPLICIT` = 0 |
| **P3** alıntı bütünlüğü | `statement`, kaynağın `anchor_text`'inin **literal alt-dizisi** olmayan kayıt = 0 |
| **P4** sayfa dürüstlüğü | `page` dolu ama kaynak `page_start` null olan kayıt = 0 |
| **P5** sınıf geçerliliği | Şema dışı `*_class` değeri = 0 |
| **P6** kripto sızıntısı | `statement` içinde `bitcoin·btc·crypto·perp·funding rate` geçen kayıt = 0 (kaynak gerçekten öyle diyorsa istisna, rapora yaz) |
| **P7** çelişki korunumu | G track'te `conflicts_with` dolu ≥1 kayıt olmalı (kitaplar risk konusunda çelişir; sıfırsa çelişkiler siliniyor demektir) |

Doğrulama betiğini `tools/verify_p5.py` olarak yaz, **ham çıktısını** rapora
kopyala.

---

## BÖLÜM VIII — TESLİMAT

1. `schemas/p5_x.schema.json`, `p5_g.schema.json`, `p5_f.schema.json`
2. `registry/p5_x_execution.json`, `p5_g_risk.json`, `p5_f_methodology.json`
3. `tools/build_p5.py` (deterministik, yeniden üretilebilir)
4. `tools/verify_p5.py`
5. `P5_GXF_REPORT.md` — ham P1-P7 çıktısı · track başına sınıf dağılımı ·
   `transfer_risk` dağılımı (X) · çelişki tablosu (G) · kararlar ·
   `failed_refs` · **dürüst sınırlamalar**
6. `tools/build_v23_html.py` içine P5 bölümlerini ekle, `findings_v23.html`'i
   yeniden üret. (Üretici zaten var ve çalışıyor — yeni bölüm ekle, mevcut
   bölümleri bozma.)

`docs/CHANGELOG.md`'ye yazma — insan onayı sonrası.

---

## BÖLÜM IX — WORKER PROMPT (İNGİLİZCE — DEĞİŞTİRME)

`prompts/execution_facts_extractor.v21.md` ve
`prompts/risk_geometry_extractor.v21.md` ile birlikte kullanılır.

```
You extract structured facts from trading-literature claims. You are given
records with: claim_id, book_id, anchor_text, page_start, claim_type.

Extract ONLY what the source states. You are cataloguing an author's claims,
not evaluating or improving them.

Rules — violating any of these invalidates your output:
1. "statement" MUST be a literal substring of anchor_text. Never paraphrase,
   summarize, translate, or clean up.
2. Every numeric parameter MUST carry the page from page_start. If page_start
   is null, set page to null. NEVER invent a page.
3. If the record does not fit any class in the schema, output
   {"verdict":"skip"}. Skipping is correct and common. Do not force a fit.
4. Preserve the source's own market, instrument, and era. These books predate
   crypto and mostly discuss equities/forex/futures. Do NOT translate rules
   into Bitcoin, perpetual futures, or funding-rate terms. Mark distance from
   crypto perps in transfer_risk instead.
5. Do not resolve contradictions. If the source contradicts another rule, that
   is data — record it. Never merge, average, or pick a winner.
6. Do not assert profitability, edge, or validated performance.
7. Leave a field empty rather than guessing. An empty field is honest; a
   plausible invention is not.

Output strict JSON, one object per input record, matching the schema you were
given for this track. When verdict is "skip", output only
{"claim_ref": "<claim_id>", "verdict": "skip"}.
```

---

## BÖLÜM X — BAŞLANGIÇ SIRASI

```
[ ] 1. Bölüm II komutunu çalıştır → p5_x/g/f_input.json
[ ] 2. X track: şema → build → 5'erli turlar → checkpoint her turda
[ ] 3. X için P1-P7 koştur, ham çıktıyı sakla
[ ] 4. X sonucu sağlamsa G track'i aynı desenle çalıştır
[ ] 5. F track'i çalıştır
[ ] 6. tools/verify_p5.py ile üçünü birden doğrula
[ ] 7. build_v23_html.py'ye P5 bölümlerini ekle, HTML'i yeniden üret
[ ] 8. P5_GXF_REPORT.md yaz
```

Adımlar arasında duraklamak için soru sorma.
