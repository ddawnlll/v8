# P4 v2.2 — CANONICAL METHOD KATMANI · AGENT DEVİR DİREKTİFİ

> Bu dosyanın tamamı, işi yapacak agent'a verilecek prompt'tur. Soğuk başlangıç
> içindir: bu dosyayı okumak, işi yapmak için yeterli olmalıdır.
>
> **Dil kuralı** (`AGENT_HANDOFF_PROMPT.md` konvansiyonu): orkestrasyon
> talimatları Türkçe, **worker/LLM prompt'ları İngilizce ve İngilizce kalır**
> — korpus İngilizce, çeviri sessiz anlam kaybı üretir.
>
> Çelişki olursa: `docs/charter/V8_CONSTITUTION.md` > bu dosya > diğerleri.

---

## BÖLÜM I — GÖREV

P4 (kanonik davranış keşif katmanı) çalıştı ama **kanonik kimliği yok etti.**
Görevin, P4'e ikinci bir sınıflandırma katmanı eklemek ve bunu ucuz bir pilotla
sınamaktır.

**Sen ne DEĞİLSİN:**
- Strateji tasarımcısı değilsin. Kaynağın söylemediğini yazmazsın.
- Backtester değilsin. Bu görevde hiçbir fiyat verisine bakmazsın.
- Korpus okuyucu değilsin. **Ham kitap metnine (`corpus/`) dokunmayacaksın.**
  Bu görevin tüm girdisi zaten işlenmiş JSON'dur.

**Başarı ölçütün ne DEĞİL:** üretilen `canonical_method` sayısı. Fazla üretmek
zarar verir — jenerik davranışı yeniden adlandırmak keşif değildir.

**Başarı ölçütün:** Bölüm V'teki yanlışlama testinin sonucu. Test başarısız
olursa **başarısız olduğunu raporlamak da geçerli bir teslimattır.**

---

## BÖLÜM II — NE BOZUK (kanıtla)

### Bulgu 1 — Adlandırılmış kanonik yöntemler registry'de yok

`registry/p4_b1_partial.json` içindeki 21 davranışın hiçbirinde şu terimler
geçmiyor (tam metin araması yapıldı, 26/26 sonuç: YOK):

```
fibonacci · retracement · ichimoku · pivot · harmonic · gartley · elliott
wave · commitment/COT · market profile · vwap · head and shoulders
triangle · flag · pennant · wedge · cup · macd · bollinger · atr · adx
seasonal · carry · order flow · absorption
```

### Bulgu 2 — Ama veride varlar

Bu bir tarama (recall) sorunu DEĞİLDİR. Alt katmanlarda mevcutlar:

| Terim | `corpus/leads/` | `processed_books/*/claims.jsonl` | P4 registry |
|---|---|---|---|
| fibonacci | 47 kitap | **42 kitap** | 0 |
| elliott | 37 | **28** | 0 |
| head and shoulders | 28 | **21** | 0 |
| pivot point | 22 | **20** | 0 |
| harmonic | 12 | **11** | 0 |
| ichimoku | 9 | **5** | 0 |
| commitments of traders | 5 | **5** | 0 |

### Bulgu 3 — Kayıp noktası: P4'ün eşleştirme kapısı

Kesin kanıt. `book_0055` = *Harmonic Trading, Volume Two*. P4'e girdi, okundu,
60 corroboration üretti — ve hepsi jenerik kovalara gitti:

```
38  momentum_divergence_reversal
10  support_resistance_bounce
 5  volume_confirmed_breakout
 3  trend_following_channel
 2  trend_continuation_pullback
 1  failed_breakout_reentry
 1  mean_reversion_band
```

Bu 60 kaydın **36'sının `exact_text` alanında** `harmonic|gartley|butterfly|
crab|bat|AB=CD|fibonacci|retracement` terimlerinden biri geçiyor. Örnek:

> `momentum_divergence_reversal` ←
> *"RSI must retrace to 50% mid-point line before completing **RSI BAMM**
> Confirmation Point..."*

RSI BAMM, Harmonic Trading'in imzalı mekanizmasıdır. P4 "bu bir momentum
divergence" deyip mevcut jenerik davranışı doğruladı. Teknik olarak yanlış
değil — ama kanonik kimlik yok edildi.

**Kök neden:** P4 ontolojisi tek katmanlı. Her davranış
`precondition_class → boundary_event → follow_through_state → resolution_event`
şablonuna indirgeniyor. Adlandırılmış yöntemler bu şablona indirgendiğinde
ayırt edici hiçbir şey kalmıyor, çünkü ayırt edici olan şablon değil
**parametrizasyondur** (hangi Fib oranı, hangi RSI eşiği, hangi sayım kuralı).

### Bulgu 4 — Ayırt edici veri ZATEN yakalanmış

Bu, görevi kolaylaştıran en önemli bulgu. 920 corroboration kaydında:

```
added_conditions dolu : 910/920
added_parameters dolu : 556/920   (sayfa numaralı)
```

Örnek `added_parameters` içeriği:
```json
[{"name": "RSI time span (default)", "value": "14-day with 70/30 overbought/oversold thresholds", "page": 213},
 {"name": "RSI time span (short)",   "value": "9-day with 80/20 thresholds", "page": 213},
 {"name": "RSI time span (long)",    "value": "65-day with 65/35 thresholds", "page": 213}]
```

Yani kanonik yöntemi ayırt edecek parametre verisi elde. **Yeni LLM ile korpus
okuması gerekmiyor.**

### Bulgu 5 — Kullanılmayan şema slotu

`registry` girdilerinde `variant_claim_refs` alanı zaten var ama neredeyse boş
(12 tohum davranışta 0, keşfedilen 9'da 0-8 arası). Yeni katman bu slotu
değil, **ayrı bir kayıt tipini** kullanmalı (Bölüm III).

---

## BÖLÜM III — YAPILACAK İŞ

### ADIM 1 — Şema: `canonical_method` katmanı

İki katmanlı ontoloji kur. **Mevcut 21 `canonical_behavior` çöpe gitmiyor** —
üst katman olarak aynen kalıyor.

- `canonical_behavior` (VAR, değişmiyor): mekanizma-agnostik jenerik davranış.
  Örn. `momentum_divergence_reversal`.
- `canonical_method` (YENİ): o mekanizmanın kaynakta **adlandırılmış,
  parametreli** varyantı. Örn. `harmonic_rsi_bamm`.

Yeni kayıt sözleşmesi — bu şemayı
`schemas/canonical_method.schema.json` olarak yaz:

```json
{
  "canonical_method_id": "harmonic_rsi_bamm",
  "parent_behavior_id": "momentum_divergence_reversal",
  "method_class": "harmonic_pattern",
  "method_name_in_source": "RSI BAMM",
  "name_provenance": "SOURCE_EXPLICIT",
  "distinguishing_parameters": [
    {"name": "RSI retracement level", "value": "50 mid-point", "page": 118,
     "claim_ref": "book_0055::lead_book_0055_2_014"}
  ],
  "distinguishing_conditions": ["Trigger Bar must be established first"],
  "supporting_claim_refs": ["book_0055::lead_book_0055_2_014"],
  "book_ids": ["book_0055"],
  "book_count": 1,
  "corroboration_count": 12,
  "evidence_label": "LITERATURE_SUPPORTED"
}
```

**Zorunlu kurallar:**

1. `method_name_in_source` **kaynakta geçen isim olmalıdır.** Kaynakta isim
   yoksa `canonical_method` üretme. Bu, sessiz çıkarımı engelleyen tek kapıdır.
2. `name_provenance` sadece `SOURCE_EXPLICIT` olabilir. Başka bir değer
   gerekiyorsa o kayıt geçersizdir, üretme.
3. Her `distinguishing_parameters` girdisi `page` **veya** `claim_ref`
   taşımalıdır. İkisi de yoksa alanı boş bırak, uydurma.
4. `parent_behavior_id`, mevcut 21 davranıştan biri olmalıdır. Yeni jenerik
   davranış **önerme** — bu görev keşif görevi değildir.
5. Bir `canonical_method`, en az **1 corroboration** ile desteklenmelidir.
   Desteksiz kayıt üretme.
6. `evidence_label` alanı `docs/charter/V8_CONSTITUTION.md`'deki etiket
   kümesinden gelmelidir. Bu görevde daima `LITERATURE_SUPPORTED`.

### ADIM 1b — GRANÜLERLİK KURALI (bağlayıcı)

> Bu bölüm, "hangi incelikte `canonical_method` üretilmeli?" sorusuna verilen
> bağlayıcı cevaptır. Ölçüme dayanır, tercihe değil.

**Ölçüm.** 920 corroboration'ın `exact_text + added_conditions +
added_parameters` alanları tarandı. Girdide **~39 farklı adlandırılmış yöntem**
geçiyor:

```
flag 53 · RSI BAMM 40 · doji 37 · head&shoulders 30 · triangle 27 · adx 24
engulfing 21 · hammer 20 · macd 18 · shooting star 17 · stochastic 14
hanging man 14 · harami 14 · dark cloud 14 · piercing 14 · wedge 13
bollinger 11 · parabolic 11 · bat 10 · crab 10 · AB=CD 10 · pennant 9
fibonacci 8 · pivot 8 · marubozu 7 · evening star 7 · three-line 7
gartley 6 · morning star 4 · butterfly 3
gap 108 · double top/bottom 51 · triple top/bottom 15 · opening range 8
donchian 5 · cup and handle 2 · rounding 1 · gann 1 · elliott 1
```

> ⚠️ **DÜZELTME (v2.2.1).** Yukarıdaki ~39 sayısı bir **ALT SINIRDIR**, sayım
> değildir. Yöntem: önceden tahmin edilen isimlerin regex'le aranması. Akla
> gelmeyen ismi bulamaz. Nitekim bulamadı — `book_0114`'ün price-action
> setup'ları (`two-bar reversal` 16 kayıt, `breakout pullback` 25, `high 1/2`
> 12, `micro channel` 12, `failed final flag` 6, `spike and channel` 5,
> `second entry` 5) ve `book_0002`/`book_0032`'nin adlandırılmış stratejileri
> (`fade the break` 3, `guppy burst` 2, `bow tie` 6, `trend knockout` 2) bu
> listede yok ama veride var ve `added_parameters` taşıyorlar.
>
> **T4'ün 60 cap'i bu eksik taramaya göre kalibre edilmişti; geçersizdir.**
> Yeni kalibrasyon T4'te.

Cap kaygısının paydası yine de düzeltilmelidir: bu pilotun girdisi kitaplar
değil, 920 corroboration'dır.

**KURAL 1 — Kaynağın adlandırdığı en ince seviyede üret.**
`gartley`, `butterfly`, `crab`, `bat` ayrı `canonical_method`'lardır — tek bir
`harmonic` kovası DEĞİL. Sebep: bunlar farklı Fib oran kümeleridir, yani
farklı *parametrizasyonlardır*, ve `canonical_method`'ın varlık sebebi tam
olarak budur. Aynı şekilde `hammer` ve `hanging_man` ayrıdır (aynı geometri,
farklı ön-koşul) — farkları `distinguishing_conditions`'a yazılır.

Bireysel candlestick adlarını jenerik `candlestick_reversal_pattern` altında
eritmek **düzeltmeye çalıştığımız hatanın bir seviye aşağıda tekrarıdır.**
Harmonic'i `momentum_divergence_reversal`'a gömmekle doji'yi
`candlestick_reversal_pattern`'a gömmek aynı kimlik imhasıdır.

**KURAL 2 — `method_class` alanı zorunlu (geri-toplama için).**
Her `canonical_method` kaydına şu alanı ekle:

```json
"method_class": "harmonic_pattern"
```

İzinli değerler: `harmonic_pattern` · `candlestick_single_line` ·
`candlestick_two_line` · `candlestick_three_line` · `chart_pattern` ·
`indicator_method` · `level_method` · `other`

Sebep: yukarı toplamak kayıpsızdır, aşağı ayrıştırmak imkânsızdır. Bu alan
sayesinde granülerlik kararı **geri alınabilir** kalır; ileride "candlestick'leri
3 aileye topla" denirse tek bir group-by yeter, yeniden işleme gerekmez.

**KURAL 3 — Adlandırılmış olmak YETMEZ; ayırt edici içerik şart.**
Bir `canonical_method` üretmek için isim geçmesi tek başına yeterli değildir.
Kayıt ayrıca **en az bir** `distinguishing_parameters` **veya**
`distinguishing_conditions` girdisi taşımalıdır (kaynaktan, sayfa/claim_ref'li).

Geçerken anılan isim (örn. bir listede "doji, hammer, harami" sayılması, kural
verilmeden) `canonical_method` ÜRETMEZ. Bunun yerine, ilgili jenerik davranışın
altında şu alana kaydedilir:

```json
"observed_name_mentions": [{"name": "doji", "claim_ref": "...", "page": 88}]
```

Bu kural, en ince granülerliğin "her kelimeyi yöntem yapma"ya dönüşmesini
engelleyen tek kapıdır.

**KURAL 4 — Kanonik alt-küme YAKALAMA anında değil, RAPOR anında seçilir.**

Veride temiz bir ayrım var: kanonik yöntemler çok kitapta, yazar-icadı setup
adları tek kitapta geçiyor.

```
çok kitap : gap 11 · fibonacci 6 · double top 6 · macd 5 · stochastic 5
            bollinger 5 · parabolic 5 · head&shoulders 5 · doji 4 · hammer 4
tek kitap : two-bar reversal · high 1/2 · breakout pullback · fade the break
            guppy burst · bow tie · trend knockout · RSI BAMM
```

Bu ayrım için **yeni alan ekleme** — `book_count` zaten şemada var. Kural:

- **Hiçbir yöntemi kapsam dışı bırakma.** Tek kitapta geçse de üret.
- Kanonik alt-küme = `book_count >= 2` filtresi, **rapor anında** uygulanır.
- Tek-kitaplık kayıtlar korunur; kalan ~6000 claim işlendiğinde ikinci kitapta
  görünürlerse `book_count` kendiliğinden artar ve kanonik kümeye terfi eder.

Sebep: yukarı toplamak/filtrelemek kayıpsızdır, atılan kaydı geri getirmek
imkânsızdır. Yakalama anında "bu yazar-icadı" diye atmak, düzeltmeye
çalıştığımız kimlik imhasının üçüncü tekrarı olur.

**BEKLENTİ:** ~70-100 `canonical_method` (tümü), bunun ~25-35'i
`book_count >= 2` ile kanonik. Kural 3 her kayıt için yine zorunludur.

**BU PİLOTTA ÇIKMAYACAK OLANLAR (başarısızlık sayma):**
`ichimoku`, `kagi`, `renko`, `commitments of traders`, `vwap`, `atr`,
`williams %R`, `cci`, `keltner` — bu terimler 920 corroboration'da **sıfır**
kez geçiyor, çünkü ilgili kitaplar (book_0107 Ichimoku, Beyond Candlesticks,
COT Bible) P4'ün işlediği 14 kitaba hiç girmedi. Bunlar kalan ~6000 claim
adımında gelecek. Yokluklarını şema hatası olarak raporlama.

### ADIM 2 — Pilot: 920 corroboration üzerinde koştur

**Girdi (tek dosya, salt-okunur):**
`registry/p4_b1_partial.json` → `corroborations` dizisi (920 kayıt)

Her kaydın şekli:
```
{claim_ref, behavior_id, page, exact_text, added_conditions, added_parameters, round}
```

> ⚠️ **`claim_ref` BENZERSİZ DEĞİLDİR.** 920 kayıtta 919 benzersiz ref var.
> `book_0005::lead_book_0005_1_098` iki kez geçiyor — tam kopya (aynı
> `behavior_id`, `round`, `page`, `exact_text`), yani çift yazım hatası.
> **Kayıtları `claim_ref` ile indeksleme** — sessizce bir kayıt kaybedersin.
> Liste konumunu (index) kullan. Tekilleştirmeyi seçersen T5'te belirt.

**İşlem:** Her corroboration için, `exact_text` + `added_conditions` +
`added_parameters` üçlüsüne bakarak şunu sor: *bu kayıt, kaynakta adı geçen
bir yöntemi mi tarif ediyor, yoksa jenerik mekanizmayı mı?*

- Adlandırılmış ise → uygun `canonical_method` kaydına bağla (yoksa oluştur).
- Jenerik ise → **dokunma.** Mevcut `canonical_behavior` bağı doğrudur.

Jenerik kalması beklenen oranın yüksek olması normaldir. Her şeyi
adlandırılmış yapmaya çalışma.

**Çıktı:** `registry/p4_v22_method_pilot.json`

```json
{
  "pipeline_version": "research_pipeline_v2.2",
  "schema_version": "2.2",
  "stage": "P4_METHOD_PILOT",
  "input_corroborations": 920,
  "methods": [ /* canonical_method kayıtları */ ],
  "unassigned_count": 0,
  "counts": {
    "methods_total": 0,
    "corroborations_assigned": 0,
    "corroborations_left_generic": 0,
    "books_covered": 0
  }
}
```

---

## BÖLÜM IV — YASAKLAR

- `registry/p4_b1_partial.json` dosyasını **DEĞİŞTİRME.** Salt-okunur girdidir.
- `site/` altına **dokunma.** Üretilen artefakttır, bu görevin kapsamı dışı.
- `corpus/` altındaki ham metinleri **okuma.** Bu görevin girdisi işlenmiş
  JSON'dur; korpusa dönmek maliyeti gereksiz yere patlatır.
- `src/v8/` altına **dokunma.** Bu bir araştırma-hattı görevidir, runtime değil.
- Yeni `canonical_behavior` **önerme.** 21 jenerik davranış sabittir.
- Kaynakta olmayan hiçbir yöntem adı, parametre veya koşul **uydurma.**
  Bilinmiyorsa alan boş kalır veya kayıt üretilmez.
- Ham katmana **kripto/BTC/V8 terminolojisi sokma** (`pipeline_version.json`
  invariants). Kitaplar kripto öncesidir; kaynak katmanı kaynak kalır.
- **Kârlılık, edge, doğrulanmış execution iddiası yazma**
  (`V8_CONSTITUTION` kural 12). Bu bir literatür derlemesidir.
- `tools/build_final_html.py` dosyasına bu adımda **dokunma.** HTML en son
  düzeltilecek, registry doğru olduktan sonra.

---

## BÖLÜM V — YANLIŞLAMA TESTİ (kabul kriteri)

Bu testler geçmezse şema yanlıştır. **Testi geçmek için çıktıyı zorlama —
başarısızlık raporu geçerli teslimattır.**

### T1 — Harmonic ayrışması (BİRİNCİL TEST)

`book_0055` (*Harmonic Trading, Volume Two*), 60 corroboration'ının 36'sında
harmonic/fibonacci terimi taşıyor. Bu 36 kaydın **en az 20'si** bir veya daha
fazla `canonical_method` kaydına bağlanmalıdır ve o kayıtların
`method_name_in_source` alanı kaynaktaki gerçek adı taşımalıdır
(örn. `RSI BAMM`, `AB=CD`, `Gartley`, `Butterfly`, `Crab`, `Bat`).

Bu test başarısız olursa: **şema Harmonic'i Harmonic olarak ayıramıyor
demektir. DUR ve raporla.** Adım 2'nin tamamını (6000 claim) çalıştırma.

### T2 — Parent bütünlüğü

Her `canonical_method.parent_behavior_id`, `p4_b1_partial.json`'daki 21
`canonical_behavior_id`'den biri olmalı. İhlal sayısı = 0.

### T3 — Provenance bütünlüğü

- `name_provenance != "SOURCE_EXPLICIT"` olan kayıt sayısı = 0
- `page` ve `claim_ref` alanlarının ikisi de boş olan
  `distinguishing_parameters` girdisi sayısı = 0

### T4 — Şişme kontrolü

`methods_total <= 60`. Girdide ölçülen farklı ad sayısı ~39'dur (Adım 1b);
beklenen aralık 25-45. 60'ı aşmak, Kural 3'ün (ayırt edici içerik şartı)
uygulanmadığına dair güçlü sinyaldir — durup gerekçelendir.

### T7 — Atama isabeti (v2.2.2, YENİ)

Her `canonical_method` için, `supporting_claim_refs`'in **en az %70'inde**
`method_name_in_source` geçmelidir. Eşleşme kısaltma-duyarlıdır: tam ad,
parantez içi kısaltma (`Average Directional Index (ADX)` → `ADX`), veya
parantezsiz çekirdek ad.

Eşik kalibrasyonu (pilot-1 ölçümü): genel isabet %96.7; %70 eşiği tam olarak
temizlenmesi gereken 5 kaydı düşürüyor, temiz 81 kaydı geçiriyor.

> ⚠️ **T7 gerekli ama YETERLİ DEĞİL.** Kelime eşleşmesi anlam eşleşmesi
> değildir. `indicator_parabolic_sar` T7'yi geçer ("parabolic" kelimesi var)
> ama kayıtların çoğu *parabolic blowoff*'tan (dikey fiyat hareketi)
> bahsediyor, Wilder'ın *Parabolic SAR* göstergesinden değil. Bu tür hatalar
> yalnızca Bölüm V-B'deki elle denetimle yakalanır.

### T6 — Granülerlik kuralları

- `method_class` alanı boş veya izinli küme dışında olan kayıt sayısı = 0
- Ne `distinguishing_parameters` ne `distinguishing_conditions` taşıyan
  `canonical_method` sayısı = 0 (Kural 3 ihlali)

### T5 — Korunum

`corroborations_assigned + corroborations_left_generic` toplamı **920** (ham)
veya **919** (çift kayıt tekilleştirildiyse) olmalıdır. Başka bir sayı kayıp
kayıt demektir. Hangisini seçtiğini rapora yaz.

### Doğrulama komutu

Çıktıyı yazdıktan sonra bunu çalıştır ve sonucunu rapora ekle:

```bash
cd /Users/hootie/src/v8/research/pipeline_v2 && python3 - <<'PY'
import json, re
base = json.load(open('registry/p4_b1_partial.json'))
out  = json.load(open('registry/p4_v22_method_pilot.json'))
beh  = {b['canonical_behavior_id'] for b in base['registry']}
corr = base['corroborations']
meth = out['methods']

RX = re.compile(r'harmonic|gartley|butterfly|crab|bat\b|AB=CD|fibonacci|retracement', re.I)
h55 = {c['claim_ref'] for c in corr
       if c['claim_ref'].startswith('book_0055') and RX.search(c['exact_text'])}
assigned = {r for m in meth for r in m.get('supporting_claim_refs', [])}

t1 = len(h55 & assigned)
t2 = sum(1 for m in meth if m.get('parent_behavior_id') not in beh)
t3a = sum(1 for m in meth if m.get('name_provenance') != 'SOURCE_EXPLICIT')
t3b = sum(1 for m in meth for p in m.get('distinguishing_parameters', [])
          if not p.get('page') and not p.get('claim_ref'))
t5 = out['counts']['corroborations_assigned'] + out['counts']['corroborations_left_generic']

print(f"T1 harmonic ayrisma : {t1}/36  -> {'PASS' if t1 >= 20 else 'FAIL'}")
print(f"T2 parent ihlali    : {t2}     -> {'PASS' if t2 == 0 else 'FAIL'}")
print(f"T3 provenance ihlali: {t3a}/{t3b} -> {'PASS' if t3a == 0 and t3b == 0 else 'FAIL'}")
CLASSES = {'harmonic_pattern','candlestick_single_line','candlestick_two_line',
           'candlestick_three_line','chart_pattern','indicator_method',
           'level_method','other'}
t6a = sum(1 for m in meth if m.get('method_class') not in CLASSES)
t6b = sum(1 for m in meth if not m.get('distinguishing_parameters')
          and not m.get('distinguishing_conditions'))

print(f"T4 method sayisi    : {len(meth)} (beklenen 70-100) -> {'PASS' if len(meth) <= 120 else 'FAIL'}")
print(f"T5 korunum          : {t5} (920 ham / 919 dedup) -> {'PASS' if t5 in (919, 920) else 'FAIL'}")
print(f"T6 class/icerik     : {t6a}/{t6b} -> {'PASS' if t6a == 0 and t6b == 0 else 'FAIL'}")

# T7 — atama isabeti (kisaltma-duyarli)
cmap = {}
for c in corr: cmap.setdefault(c['claim_ref'], []).append(c)
def matches(nm, b):
    nm = (nm or '').lower().strip()
    if not nm: return False
    if nm in b: return True
    for ab in re.findall(r'\(([^)]+)\)', nm):
        if ab.strip() in b: return True
    core = re.sub(r'\([^)]*\)', '', nm).strip()
    if core and core in b: return True
    toks = [t for t in re.split(r'[^a-z0-9=/]+', core) if len(t) > 3]
    return bool(toks) and all(t in b for t in toks)
t7 = []
for m in meth:
    refs = m.get('supporting_claim_refs', []); h = 0
    for r in refs:
        b = ''.join((c['exact_text'] + ' ' + json.dumps(c.get('added_conditions'))
                     + ' ' + json.dumps(c.get('added_parameters'))).lower()
                    for c in cmap.get(r, []))
        if matches(m.get('method_name_in_source'), b): h += 1
    if refs and h / len(refs) < 0.70:
        t7.append((m['canonical_method_id'], h, len(refs)))
print(f"T7 atama isabeti    : {len(t7)} method <%70 -> {'PASS' if not t7 else 'FAIL'}")
for cid, h, n in t7: print(f"     {cid}: {h}/{n}")
PY
```

---

## BÖLÜM V-B — PİLOT-1 DENETİM BULGULARI (v2.2.2, ZORUNLU)

Pilot-1 (86 method) bağımsız denetimden geçti. **T1-T6 PASS, kabul edildi.**
Aşağıdakiler kalan ~6000 claim'e geçmeden önce düzeltilmelidir — bu hatalar
tam çalıştırmada ~7 kat büyür.

### Denetimde DOĞRULANAN (değiştirme)

```
T1 harmonic ayrisma : 35/36   PASS   ← sema Harmonic'i ayirabiliyor
korunum             : 447+473 = 920  PASS
book_count/book_ids : 0 hata          PASS
var olmayan ref     : 0               PASS
genel atama isabeti : 730/755 = %96.7
kanonik alt-kume    : 32/86 (book_count>=2)
```

### D1 — Sınıflandırıcı: isim eşleşmesi ≠ yöntem tarifi (KÖK NEDEN)

`tools/build_method_pilot.py` şu an ismi **kaydın herhangi bir yerinde**
görünce atama yapıyor; kaydın o yöntemi *anlattığını* doğrulamıyor.

Kanıt: `book_0052::lead_book_0052_2_034` altı yönteme birden atanmış
(`doji`, `evening_star`, `harami`, `harami_cross`, `morning_star`, `star`)
ama metin **yalnızca bullish harami** tarif ediyor. Diğer beş isim kayıtta
geçiyor ama tarif edilen yöntem değil.

**Düzeltme:** Bir kaydı yönteme atamak için ismin geçmesi yetmez; kaydın
`added_parameters` / `added_conditions` içeriğinin **o isme bağlı** olması
gerekir. İsmin yalnızca liste/karşılaştırma bağlamında geçtiği kayıtlar
atanmaz — jenerik kalır.

Not: çoklu atama kendiliğinden hata DEĞİLDİR.
`book_0016::lead_book_0016_1_171` gerçekten On Neck / In Neck / Thrusting /
Piercing'in dördünü birden tartışıyor; o atama meşrudur.

### D2 — Kayıt düzeltmeleri (5 adet)

| # | Kayıt | Bulgu | Yapılacak |
|---|---|---|---|
| 1 | `indicator_parabolic_sar` | 11 ref'in yalnızca **3'ü** SAR/stop-and-reverse'ten bahsediyor; **2'si** *parabolic blowoff* (farklı kavram). `book_count=5` bu kirlilikle şişmiş. | SAR olmayan ref'leri çıkar, `book_count`'u yeniden hesapla. 3 ref altına düşerse kaydı sil. |
| 2 | `indicator_volume_roc` | Kaynak **"volume ROC"** diyor, kayıt "Volume Rate of Change" diye açmış → `SOURCE_EXPLICIT` iddiası birebir değil. | `method_name_in_source` = `"volume ROC"`. |
| 3 | `pa_inside_bar_ii` | `book_count=2` ama ikinci kitap `book_0032`'nin CVR III/VIX kaydı — inside bar'la alakasız. Bu hata kaydı **yanlışlıkla kanonik alt-kümeye terfi ettiriyor**. | `book_0032` ref'ini çıkar, `book_count`→1. |
| 4 | `pa_high_low_1_2` | Kayıt **geçerli** (19 ref'in 18'inde H1/H2/L1/L2 geçiyor). Yalnızca ad kaynak biçiminde değil. | `method_name_in_source` = `"H1/H2/L1/L2"`. |
| 5 | `candlestick_falling_three` (1/2) · `indicator_donchian` (3/5) · `indicator_pivot_point` (9/15) · `indicator_stochastic` (8/13) | T7 eşiğinin altında — ilgisiz ref'ler karışmış. | İsmi geçmeyen ref'leri çıkar; kayıt eşiği geçemezse sil. |

### D3 — Yeniden üretim

Düzeltmeler `tools/build_method_pilot.py` içine yazılır, betik yeniden
koşturulur, `registry/p4_v22_method_pilot.json` yeniden üretilir. **Çıktı
JSON'unu elle düzenleme** — betik deterministik ve yeniden üretilebilir
kalmalıdır.

Sonra Bölüm V'teki **yedi testin tamamı** (T1-T7) yeniden koşturulur ve ham
çıktı `P4_V22_PILOT_REPORT.md`'ye işlenir.

### D4 — Bundan sonra

D1-D3 tamamlanıp T1-T7 PASS olunca **kalan ~6000 claim'e geçiş onaylıdır**
(Bölüm VIII). O adımda `p4_gate_input` hazır olan 115 kitabın işlenmemiş
~101'i devreye girer; `ichimoku`, `kagi`, `renko`, `commitments of traders`
gibi şu an sıfır olan kanonik aileler orada beklenir.

---

## BÖLÜM VI — TESLİMAT

1. `schemas/canonical_method.schema.json` — yeni şema
2. `registry/p4_v22_method_pilot.json` — pilot çıktısı
3. `P4_V22_PILOT_REPORT.md` — şunları içerecek:
   - Bölüm V doğrulama komutunun **ham çıktısı** (kopyala-yapıştır, özet değil)
   - Üretilen `canonical_method` listesi: id, parent, kitap sayısı, corroboration sayısı
   - Jenerik kalan corroboration oranı ve **neden** jenerik kaldıklarına dair 3 örnek
   - T1 başarısızsa: hangi 36 kaydın bağlanamadığı ve gözlemlenen sebep
   - **Dürüst sınırlamalar bölümü** (bu pilot neyi kanıtlamaz)

`docs/CHANGELOG.md`'ye giriş **yazma** — bunu insan onayı sonrası orkestratör
yapacak. Sadece yukarıdaki üç dosyayı üret.

---

## BÖLÜM VII — WORKER PROMPT (İNGİLİZCE — DEĞİŞTİRME)

Her corroboration batch'i için LLM'e verilecek prompt budur. İngilizce kalır.

```
You are classifying claims extracted from trading literature. Each record
below was already matched to a GENERIC behavior. Your job is to decide whether
the record additionally describes a NAMED method from the source text.

A NAMED METHOD is a technique the author refers to by a proper name:
"RSI BAMM", "Gartley", "AB=CD", "Ichimoku", "Elliott Wave", "pivot point",
"head and shoulders", "Commitments of Traders", "Bollinger Bands", etc.

Rules — violating any of these invalidates your output:
1. The name MUST appear in the record's exact_text, added_conditions, or
   added_parameters. If you cannot point to it, output "generic".
2. Do NOT invent a name. Do NOT normalize a description into a name.
   "prices bounce off a level" is GENERIC, not "support_resistance_method".
3. Do NOT propose new generic behaviors. The parent must be the behavior_id
   already assigned to the record.
4. Every parameter you extract MUST carry the page number or claim_ref shown
   in the record. If neither is present, omit the parameter.
5. A record may be generic. Most records ARE generic. Output "generic" freely.
6. Do not add crypto, Bitcoin, or perpetual-futures terminology. The sources
   predate crypto. Preserve the source's own market and instrument context.
7. Do not assert profitability, edge, or validated performance. You are
   cataloguing what authors claim, not endorsing it.

Output strict JSON, one object per input record:
{"claim_ref": "...", "verdict": "named" | "generic",
 "method_name_in_source": "<exact string from source, or null>",
 "canonical_method_id": "<snake_case slug, or null>",
 "distinguishing_parameters": [{"name": "...", "value": "...", "page": N}],
 "distinguishing_conditions": ["..."],
 "evidence_quote": "<the substring proving the name appears, or null>"}

If verdict is "named", evidence_quote is MANDATORY and must be a literal
substring of the record you were given.
```

---

## BÖLÜM VIII — BAĞLAM SAYILARI (referans)

Bu görevin kapsamı dışı ama karar verirken bilmen gerekenler:

```
125   korpustaki kitap
9643  triage edilmiş toplam claim
7211  p4_gate_input olarak hazırlanmış M-track claim (115 kitap, 7.7 MB)
1214  P4'ün gerçekten işlediği claim (tur1: 883 + tur2: 331)
 920  corroboration kaydı  ← BU GÖREVİN TEK GİRDİSİ
  21  canonical_behavior (12 tohum + 9 keşif)
  14  corroboration üreten kitap
  69  P4 turlarına giren kitap
```

P4 turlar 3-7 `claims_gated=0` ile çalıştı — yani boş döndü. Mevcut HTML bunu
"kesinti" diye açıklıyor; bu yanlıştır, girdi zamanlanmamıştır. Bu pilot
geçerse sıradaki iş, kalan ~6000 hazır claim'i işlemektir. **O işi bu görevde
yapma.**
