# P4 TAM ÇALIŞTIRMA — AGENT TASK PROMPT (v2.3)

> **Bu dosyanın tamamı görevdir.** Soğuk başlangıç içindir: bunu okumak işi
> yapmak için yeterlidir.
>
> **SORU SORMA.** Bu görevde hiçbir aşamada kullanıcıya soru sormayacaksın.
> Her belirsizlik için Bölüm IX'da bir karar kuralı vardır. Bölüm IX'da
> karşılığı olmayan bir belirsizlikle karşılaşırsan: en muhafazakâr seçeneği
> al (veri üretme, kayıt düşürme, jenerik bırak), kararı
> `P4_FULL_RUN_REPORT.md`'nin "Kararlar" bölümüne yaz, devam et.
>
> **Dil kuralı** (proje konvansiyonu): orkestrasyon Türkçe, **worker/LLM
> prompt'ları İngilizce ve İngilizce kalır** — korpus İngilizce, çeviri sessiz
> anlam kaybı üretir.
>
> Çelişki sırası: `docs/charter/V8_CONSTITUTION.md` > bu dosya >
> `P4_V22_DIRECTIVE.md` > diğerleri.

Kök dizin: `/Users/hootie/src/v8`
Çalışma dizini: `/Users/hootie/src/v8/research/pipeline_v2`

---

## BÖLÜM I — GÖREV VE KİMLİK

125 ticaret kitabından çıkarılmış claim korpusunun P4 katmanını **tamamlamak**.
P4 daha önce kısmen çalıştı (14 kitap) ve durdu. Senin işin kalan 101 kitabı
işlemek ve iki katmanlı kanonik kaydı üretmek.

**Sen ne DEĞİLSİN:**
- Strateji tasarımcısı değilsin. Kaynağın söylemediğini yazmazsın.
- Backtester değilsin. Bu görevde hiçbir fiyat verisine bakmazsın.
- Keşifçi değilsin. Yeni `canonical_behavior` **önermezsin** — 21 tanesi sabit.
- Soru soran bir asistan değilsin. Karar kuralların Bölüm IX'da.

**Başarı ölçütün ne DEĞİL:** üretilen method/claim sayısı. Şişirme bu programa
zarar verir.

**Başarı ölçütün:** kapsama tamlığı (101/101 kitap işlendi), provenance
bütünlüğü (uydurma = 0), ve Bölüm X'daki sekiz testin sonucu. **Testler
başarısız olursa bunu raporlamak da geçerli teslimattır** — sahte PASS üretme.

---

## BÖLÜM II — KESİN KAPSAM (ölçülmüş, tahmin değil)

```
125  korpustaki kitap
115  gate_input hazır kitap            (7211 M-track claim)
 10  gate_input YOK — kapsam dışı      (aşağıda liste)
 14  P4'ün daha önce işlediği kitap    (1455 claim → 920 corroboration + 120 new_claim)

İŞLENECEK: 101 kitap / 5756 claim
  ├─ 46 kitap / 1165 claim  — P4 turlarına hiç zamanlanmamış
  └─ 55 kitap / 4591 claim  — zamanlanmış ama hiç çıktı üretmemiş
                               (turlar 3-7 `claims_gated=0` ile boş döndü)
```

**gate_input'u OLMAYAN 10 kitap — DOKUNMA, kapsam dışı:**
`book_0009 · book_0010 · book_0012 · book_0045 · book_0053 · book_0078 ·
book_0082 · book_0088 · book_0102 · book_0120`

Bunlar M-track claim üretmemiş kitaplardır (anlatı/biyografi ağırlıklı).
Bunlar için `p4_gate_input/` dizini yoktur. **Üretmeye çalışma.**

**Daha önce işlenmiş 14 kitap — YENİDEN İŞLEME:**
`book_0002 · book_0005 · book_0014 · book_0016 · book_0020 · book_0025 ·
book_0032 · book_0052 · book_0055 · book_0056 · book_0098 · book_0110 ·
book_0114 · book_0121`

İşlenecek 101 kitabın kesin listesini şu komutla üret (tahmin etme):

```bash
cd /Users/hootie/src/v8/research/pipeline_v2 && python3 - <<'PY'
import json, glob
d = json.load(open('registry/p4_b1_partial.json'))
sched = set()
for r in d['saturation_ledger']: sched.update(r['books'])
have = {p.split('/')[-2] for p in glob.glob('processed_books/*/p4_gate_input')}
prod = {x['claim_ref'].split('::')[0] for x in d['corroborations']}
prod |= {x['book_id'] for x in d['new_claims'] if x.get('book_id')}
todo = sorted((have - sched) | (sched - prod))
claims = sum(sum(1 for l in open(f) if l.strip())
             for b in todo for f in glob.glob(f'processed_books/{b}/p4_gate_input/*'))
print(f'ISLENECEK: {len(todo)} kitap / {claims} claim')
print('\n'.join(todo))
PY
```

---

## BÖLÜM III — MİMARİ: İKİ KATMAN, ÜÇ AŞAMA

### İki katmanlı ontoloji (LOCKED — değiştirme)

- **`canonical_behavior`** — mekanizma-agnostik jenerik davranış. **21 tanesi
  sabittir**, `registry/p4_b1_partial.json` → `registry` dizisinde. Yeni
  önerme, mevcut olanı yeniden adlandırma.
- **`canonical_method`** — o mekanizmanın kaynakta **adlandırılmış,
  parametreli** varyantı (RSI BAMM, Gartley, Doji, Donchian...). Şema:
  `schemas/canonical_method.schema.json`.

Tarihsel gerekçe: P4 tek katmanlı çalıştığında kanonik kimliği yok etti —
*Harmonic Trading*'in RSI BAMM'ını `momentum_divergence_reversal`'a gömdü.
İki katman bunu önlemek içindir. Aynı hatayı tekrarlama.

### Üç aşama

| Aşama | Ne yapar | Yöntem | Girdi |
|---|---|---|---|
| **A1** | claim → behavior eşleştirme + `added_conditions`/`added_parameters` çıkarımı | **LLM** | `p4_gate_input/*.jsonl` |
| **A2** | METHODS kataloğunu genişlet | **deterministik madencilik** + LLM onayı | ham `anchor_text` |
| **A3** | corroboration → `canonical_method` sınıflandırma | **%100 deterministik, 0 token** | A1 çıktısı |

**Sıra zorunlu: A2 → A1 → A3.** A2 ham metinden çalışır, A1'e bağımlı değildir;
önce yapılırsa A3 tek geçişte biter.

---

## BÖLÜM IV — VERİ ŞEKİLLERİ (ezberleme, buradan oku)

### Girdi: `processed_books/<book_id>/p4_gate_input/gate*.jsonl`

```json
{"claim_id": "book_0107::lead_book_0107_2_001",
 "route": "M",
 "claim_type": "LIFECYCLE_RULE",
 "anchor_text": "<~840 karakter ham regex penceresi>",
 "section_id": "...", "page_start": 12, "page_end": 12,
 "carries_quantity": true}
```

`behavior_id` YOK · `added_conditions` YOK · `added_parameters` YOK.
A1'in işi bunları üretmektir.

### A1 çıktısı: corroboration (mevcut formatla birebir aynı olmalı)

```json
{"claim_ref": "book_0107::lead_book_0107_2_001",
 "behavior_id": "<21 kanonik davranıştan biri>",
 "page": 12,
 "exact_text": "<kaynaktan birebir alıntı>",
 "added_conditions": ["..."],
 "added_parameters": [{"name": "...", "value": "...", "page": 12}],
 "round": 8}
```

### A3 çıktısı: canonical_method

Şema `schemas/canonical_method.schema.json`. Zorunlu alanlar:
`canonical_method_id · parent_behavior_id · method_class ·
method_name_in_source · name_provenance · distinguishing_parameters ·
distinguishing_conditions · supporting_claim_refs · book_ids · book_count ·
corroboration_count · evidence_label`

`method_class` izinli değerler: `harmonic_pattern · candlestick_single_line ·
candlestick_two_line · candlestick_three_line · chart_pattern ·
indicator_method · level_method · other`

---

## BÖLÜM V — AŞAMA A2: KATALOG GENİŞLETME (önce bunu yap)

`tools/build_method_pilot.py` içindeki `METHODS` kataloğu **elle
kürasyonludur** ve yalnızca 14 kitaptan çıkarılmış 85 desen içerir. Regex
bilmediği adı bulamaz. Şu anda katalogda **olmayan** ama korpusta bulunan
kanonik aileler: `ichimoku · kagi · renko · commitments of traders · vwap ·
atr · williams %R · cci · keltner · elliott wave · gann · market profile`.

### A2.1 — Ad adaylarını deterministik çıkar (0 token)

101 kitabın `anchor_text`'i üzerinde çalıştır. Doğrulanmış yaklaşım
(örneklemde Gartley, Butterfly, Double Top/Bottom, Three Drives, Fibonacci
Retracement, Pinocchio buldu):

```python
PATS = [
  r'\b(?:the\s+)?([A-Z][A-Za-z\-]+(?:\s+[A-Z][A-Za-z\-]+){0,3})\s+'
  r'(?:pattern|method|indicator|oscillator|strategy|setup|system|line|cloud|channel|band|wave)\b',
  r'\bknown as (?:the\s+)?([A-Z][A-Za-z\- ]{2,30})',
  r'\bcalled (?:the\s+)?([A-Z][A-Za-z\- ]{2,30})',
  r'\breferred to as (?:the\s+)?([A-Z][A-Za-z\- ]{2,30})',
]
```

Gürültü filtresi: `the · this · that · figure · chapter · using · another ·
example · following · above · below` ile başlayanları ve uzunluğu <3 veya >40
olanları at. Frekansa göre sırala.

### A2.2 — Aday listesini LLM ile onaylat

**Yalnızca aday listesi** LLM'e gider (kısa), 5756 kayıt DEĞİL. Her aday için
tek soru: *bu, kaynakta adlandırılmış bir ticaret yöntemi mi, yoksa sıradan
bir tamlama mı?* Onaylananlar `METHODS`'a eklenir.

### A2.3 — Katalog eklerken uyulacak kurallar

1. `name_in_source` **kaynakta geçen biçim** olmalı. Açılım/kısaltma yazma.
   Emsal: `"Stochastic Oscillator"` kaynakta hiç geçmiyordu, `"Stochastic"`
   olarak düzeltildi.
2. Desen, adı **birebir** hedeflemeli. Emsal hatalar — tekrarlama:
   - `\bpivot\b` → swing `pivot high/low` yapısını yakalıyordu; hesaplanan
     Pivot Point için `\bpivot points?\b` olmalı.
   - `parabolic` → *parabolic blowoff* (dikey fiyat hareketi) ile *Parabolic
     SAR* (Wilder göstergesi) tamamen farklı; desen SAR'ı hedeflemeli.
3. Yeni desen eklerken `only_books` kısıtını, ad genel bir kelimeyse kullan
   (örn. candlestick adları yalnızca candlestick kitaplarında aransın).
4. Katalog eklerini `tools/build_method_pilot.py` içine yaz. **Ayrı bir
   katalog dosyası oluşturma.**

---

## BÖLÜM VI — AŞAMA A1: P4 ÇEKİRDEĞİ (token maliyeti burada)

### A1.1 — Mevcut altyapıyı kullan, yeniden yazma

- Workflow: `workflows/p4_rounds.js` (şemalar, tur mantığı, ledger'lar hazır)
- Rol prompt'ları: `prompts/novelty_gate.v21.md`, `prompts/corroborator.v21.md`
- Bunlar çalışır durumdadır. **Yeni bir pipeline yazma.**

### A1.2 — Turlama

- Tur başına **10 kitap**. 101 kitap → 11 tur.
- Her turdan sonra ara çıktıyı diske yaz (Bölüm VIII checkpoint).
- **DOYUM NEDENİYLE ERKEN DURMA.** Önceki çalıştırmanın en büyük hatası buydu:
  turlar 3-7 `claims_gated=0` ile boş döndü ve bu "doygunluk" sanıldı.
  **101 kitabın hepsi işlenecek.** Bir tur 0 yeni aile üretirse bu normaldir —
  zaten yeni aile aramıyorsun (21 davranış sabit).
- Her turda `claims_gated` sayısını logla. Bir tur `claims_gated=0` verirse bu
  bir **hatadır**, doygunluk değil: girdi zamanlanmamış demektir. Durdur,
  nedenini bul, düzelt, devam et.

### A1.3 — A1 için bağlayıcı kurallar

1. `behavior_id`, 21 kanonik davranıştan biri olmalı. Eşleşme yoksa kaydı
   **jenerik bırak** (corroboration üretme) — zorlama.
2. `exact_text` kaynaktan **birebir alıntı** olmalı. Özetleme, parafraz etme.
3. `added_parameters` girdileri `page` **veya** `claim_ref` taşımalı. İkisi de
   yoksa parametreyi **yazma**.
4. Sayfa bilinmiyorsa `page: null` bırak. **Sayfa uydurma.** UNMAPPED
   kitaplarda sayfa yerine `section_id` + satır kullanılır.
5. `round` alanına tur numarasını yaz (mevcut veri 1-7 kullandı; sen 8'den
   başla).

---

## BÖLÜM VII — AŞAMA A3: METHOD SINIFLANDIRMA (deterministik, 0 token)

`tools/build_method_pilot.py`'yi A1 çıktısı üzerinde çalıştır.

### A3.1 — Betikteki iki mekanizmaya DOKUNMA

Bunlar bağımsız denetimden geçti, regresyon düzeltmesidir:

1. **Numaralandırma (enumeration) muhafızı** (`match_methods`): ad kayıtta
   geçmeli **ve** (tarif edici içeriğe bağlı olmalı **veya** kayıt en fazla
   `ENUM_LIMIT=2` yönteme eşleşmeli). Bu, bir harami kaydının 6 candlestick
   yöntemine birden bağlanmasını engellerken *"The Failed Wave"* / PRZ gibi
   adı yalnızca `exact_text`'te geçen kavramları korur.
2. **T7 post-filtresi YOKTUR ve eklenmeyecektir.** Önceki sürümde eklenen
   post-filtre, T7'yi kendi kriteriyle besleyip totolojik hale getirmişti
   (562/562 = %100, ölçüm değeri sıfır). Atama isabeti `match_methods` içinde
   kararlaştırılır; T7 **filtrelenmemiş** çıktıyı denetler.

**T7 FAIL alırsan çözüm post-filtre eklemek DEĞİLDİR.** Çözüm, ilgili
yöntemin `name_in_source` değerini kaynak biçimine çekmek veya desenini
daraltmaktır (Bölüm V, A2.3 madde 1-2).

### A3.2 — `ENUM_LIMIT` kalibrasyonu

`ENUM_LIMIT=2` 920 kayıtlık pilotta ampirik olarak belirlendi. 5756 kayıtta
yeniden kalibrasyon gerekebilir. Kural: T7 PASS ve T1 ≥ eşik kaldığı sürece
**değiştirme**. Değiştirmek zorunda kalırsan eski/yeni değeri ve gerekçeyi
rapora yaz.

---

## BÖLÜM VIII — ÇIKTI DOSYALARI VE CHECKPOINT

### Yazılacak dosyalar (yalnızca bunlar)

```
registry/p4_full_run.json            A1 çıktısı (corroborations + new_claims + ledger)
registry/p4_v23_methods.json         A3 çıktısı (canonical_method kayıtları)
registry/p4_full_run.checkpoint.json her turdan sonra üzerine yazılır
tools/build_method_pilot.py          A2 katalog ekleri (mevcut dosya güncellenir)
P4_FULL_RUN_REPORT.md                rapor
```

### Checkpoint zorunlu

Her turdan sonra `registry/p4_full_run.checkpoint.json` yaz: işlenmiş kitap
listesi, tur numarası, o ana kadarki sayımlar. Çalışma yarıda kesilirse
checkpoint'ten devam et, baştan başlama.

### Kesinlikle DEĞİŞTİRİLMEYECEK dosyalar

```
registry/p4_b1_partial.json      salt-okunur girdi (1.8 MB)
registry/p4_v22_method_pilot.json  pilot çıktısı, referans
site/                            üretilen artefakt
src/v8/                          runtime paketi
corpus/                          ham metinler — OKUMA bile
tools/build_final_html.py        HTML en son, ayrı görevde
docs/CHANGELOG.md                insan onayı sonrası orkestratör yazar
```

---

## BÖLÜM IX — KARAR TABLOSU (soru sormak yerine buraya bak)

| Durum | Karar |
|---|---|
| Claim hiçbir davranışa uymuyor | Jenerik bırak, corroboration üretme. Zorlama. |
| Claim 2+ davranışa uyuyor | En spesifik olanı seç. Eşitlik varsa alfabetik ilk. Rapora yaz. |
| Kaynakta adlandırılmamış yeni bir mekanizma | `canonical_behavior` **önerme**. Jenerik bırak. |
| Katalogta olmayan bir yöntem adı gördün | A1 sırasında **inline method üretme**. A2'ye not düş, A2 turunda ekle. |
| `exact_text` alıntısı 1100 karakteri aşıyor | Cümle sınırında kes, `...` ekleme, kesme noktasını rapora yazma gereği yok. |
| Sayfa numarası yok | `page: null`. Uydurma. |
| Bir tur `claims_gated=0` verdi | **Hata.** Doygunluk sayma. Dur, girdiyi kontrol et, düzelt, devam et. |
| LLM çağrısı hata verdi | 2 kez yeniden dene. Hâlâ başarısızsa o kaydı atla, `failed_refs` listesine ekle, devam et. |
| Aynı `claim_ref` iki kez geçiyor | Liste konumuyla (index) indeksle. `claim_ref` benzersiz DEĞİLDİR (mevcut veride 1 tam kopya var). |
| Token bütçesi bitmek üzere | Checkpoint yaz, işlenen/işlenmeyen kitapları rapora yaz, **dur**. Sessizce kısaltma. |
| Test FAIL veriyor | Testi veya eşiği değiştirme. Nedeni bul, veriyi/deseni düzelt. Düzeltilemiyorsa FAIL olarak raporla. |
| Bir kitabın tüm claim'leri jenerik kaldı | Normal. Rapora yaz, tekrar deneme. |
| Bölüm IX'da olmayan bir belirsizlik | En muhafazakâr seçenek (üretme/düşür/jenerik bırak) + rapora yaz + devam et. **Soru sorma.** |

---

## BÖLÜM X — KABUL TESTLERİ

`P4_V22_DIRECTIVE.md` → "Doğrulama komutu" bloğundaki T1-T7 betiğini, girdi
dosyalarını yeni çıktılara (`p4_full_run.json`, `p4_v23_methods.json`)
yönlendirerek çalıştır. Ek olarak T8.

| Test | Kriter |
|---|---|
| **T1** harmonic ayrışma | `book_0055`'in harmonic terimli kayıtlarının ≥%55'i bir method'a bağlı |
| **T2** parent bütünlüğü | 21 dışı `parent_behavior_id` = 0 |
| **T3** provenance | `name_provenance != SOURCE_EXPLICIT` = 0 **ve** `page`/`claim_ref` taşımayan parametre = 0 |
| **T4** şişme | method sayısı ≤ 400 (5756 claim ölçeğinde; pilotta 85/920 idi) |
| **T5** korunum | `assigned + generic` = işlenen toplam claim sayısı |
| **T6** granülerlik | geçersiz `method_class` = 0 **ve** ne parametre ne koşul taşıyan method = 0 |
| **T7** atama isabeti | `<%70` isabetli method = 0 (**post-filtresiz** ölçüm) |
| **T8** kapsama | işlenen kitap = 101. Eksikse hangi kitap ve neden. |

**Ham test çıktısını rapora kopyala-yapıştır.** Özetleme.

---

## BÖLÜM XI — YASAKLAR

- **Soru sorma.** Bölüm IX bağlayıcıdır.
- Yeni `canonical_behavior` önerme. 21 tanesi sabittir.
- Kaynakta olmayan yöntem adı, parametre veya koşul **uydurma**.
- Sayfa numarası **uydurma**.
- T7 post-filtresi **ekleme** (Bölüm VII.A3.1).
- Testi veya eşiği geçmek için **değiştirme**.
- Ham katmana **kripto/BTC/V8 terminolojisi sokma**. Kitaplar kripto
  öncesidir; kaynak katmanı kaynak kalır (`pipeline_version.json` invariants).
- **Kârlılık, edge, doğrulanmış execution iddiası yazma**
  (`V8_CONSTITUTION` kural 12). Bu bir literatür derlemesidir.
- Gated bileşenleri (router, shared scorer, ranker, RL execution, online
  learning) **implemente etme** (kural 6, 14).
- Çıktı JSON'unu **elle düzenleme**. Her şey betikten üretilir; determinizm
  ve yeniden üretilebilirlik korunur.
- `corpus/` altındaki ham kitap metinlerini **okuma** — girdi
  `p4_gate_input`'tur. (İstisna: A2.1 ad madenciliği `anchor_text` üzerinde
  çalışır, o da `p4_gate_input` içindedir.)

---

## BÖLÜM XII — TESLİMAT

`P4_FULL_RUN_REPORT.md` şunları içerecek:

1. **Ham T1-T8 çıktısı** (kopyala-yapıştır, özet değil)
2. Kapsama tablosu: işlenen kitap/claim, jenerik kalan oran, kitap başına dağılım
3. A2 katalog eklemeleri: eklenen ad, kaynak biçimi, desen, kaç kayıt bağladı
4. `canonical_method` envanteri: id, `method_class`, parent, `book_count`,
   `corroboration_count`
5. Kanonik alt-küme (`book_count >= 2`) sayısı ve listesi
6. **Kararlar** bölümü: Bölüm IX'a göre verdiğin her karar
7. `failed_refs` listesi (varsa) ve nedenleri
8. **Dürüst sınırlamalar** bölümü: bu çalıştırma neyi kanıtlamaz

`docs/CHANGELOG.md`'ye giriş **yazma** — insan onayı sonrası orkestratör yapar.

---

## BÖLÜM XIII — WORKER PROMPT (İNGİLİZCE — DEĞİŞTİRME)

A1 (behavior matching + extraction) için worker prompt'u.
`prompts/corroborator.v21.md` ile birlikte kullanılır.

```
You are extracting structured records from trading-literature claims.

For each input record you receive: claim_id, route, claim_type, anchor_text,
section_id, page_start, page_end.

Decide whether the claim corroborates one of the 21 canonical behaviors you
were given. Then extract the distinguishing content.

Rules — violating any of these invalidates your output:
1. behavior_id MUST be one of the 21 canonical behaviors supplied. If none
   fits, output {"verdict": "generic"} and nothing else. Do not force a match.
   Most claims ARE generic. Output "generic" freely.
2. Do NOT propose new behaviors. The 21 are fixed.
3. exact_text MUST be a literal substring of anchor_text. Do not paraphrase,
   summarize, translate, or clean it up.
4. Every added_parameters entry MUST carry the page number from the input. If
   page_start is null, set page to null. NEVER invent a page number.
5. added_conditions must state conditions the SOURCE gives. Do not add your
   own trading judgment, and do not restate the generic mechanism.
6. If the claim names a specific method (Gartley, Ichimoku, Doji, Donchian,
   RSI BAMM, ...), keep that name verbatim inside exact_text or
   added_conditions. Do NOT normalize, expand, or abbreviate it. Downstream
   deterministic tooling depends on the literal source spelling.
7. Do not add crypto, Bitcoin, or perpetual-futures terminology. These sources
   predate crypto. Preserve the source's own market and instrument context.
8. Do not assert profitability, edge, or validated performance. You are
   cataloguing what an author claims, not endorsing it.

Output strict JSON, one object per input record:
{"claim_ref": "<claim_id verbatim>",
 "verdict": "corroboration" | "generic",
 "behavior_id": "<one of the 21, or null>",
 "page": <int or null>,
 "exact_text": "<literal substring of anchor_text, or null>",
 "added_conditions": ["..."],
 "added_parameters": [{"name": "...", "value": "...", "page": <int or null>}]}

When verdict is "generic", every other field except claim_ref must be null or
an empty array.
```

---

## BÖLÜM XIV — BAŞLANGIÇ SIRASI (kontrol listesi)

```
[ ]  1. Bölüm II'deki komutu çalıştır, 101 kitaplık listeyi üret
[ ]  2. A2.1 — ad adaylarını deterministik çıkar (0 token)
[ ]  3. A2.2 — aday listesini LLM ile onaylat
[ ]  4. A2.3 — onaylananları build_method_pilot.py METHODS'a ekle
[ ]  5. A1 — 11 tur × 10 kitap, her turdan sonra checkpoint
[ ]  6. registry/p4_full_run.json yaz
[ ]  7. A3 — build_method_pilot.py'yi A1 çıktısında çalıştır
[ ]  8. registry/p4_v23_methods.json yaz
[ ]  9. T1-T8'i çalıştır, ham çıktıyı sakla
[ ] 10. P4_FULL_RUN_REPORT.md yaz (Bölüm XII)
```

Her adım bittiğinde bir sonrakine geç. Duraklamak için soru sorma.
