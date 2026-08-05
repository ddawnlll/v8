# research_pipeline_v2.1 — analiz stratejisi (execution plan)

**Status:** PROVISIONAL_DECISION. Bu belge v2.0 protokolünü iptal etmez;
onun *çalıştırma sırasını ve doğrulama yoğunluğunu* kanıta göre yeniden
bütçeler. Şema, provenance kuralları ve no-leak invariantları aynen geçerli.

`pipeline_version: research_pipeline_v2.1` · `schema_version: 2.0` (değişmedi)

---

## 0. Ölçülen durum (2026-08-02)

| Büyüklük | Değer |
|---|---|
| Kitap (dedup, manifest) | 125 |
| Ham metin | 78.334.391 karakter ≈ 19.6M token |
| Sayfa | 36.260 |
| Part dosyası | 331 (kitap başına ort. 2.5, part başına ~80k token) |
| Deterministik scout lead | 12.457 (7.650 high / 4.807 medium) |
| Lead anchor metni | 12.205.652 karakter = korpusun **%15,6**'sı ≈ 3.05M token |
| Lead/kitap | min 1 · medyan 91 · maks 693 (`book_0038`) |
| Lexical near-dup (J>0.5) | 12.457 lead içinde **122 çift** (32'si kitaplar arası) |
| Sayfa sınırı (`\f`) korunmuş mu | **Evet** — 331 part dosyasında mevcut |
| Tamamlanmış aşama | 1 (corpus integrity) ve 3 (scout, deterministik) |
| Boş | `processed_books/`, `registry/`, `prompts/` |

### Bu sayılardan çıkan üç düzeltme

**D1 — Lexical dedup ölü yol.** 12.457 lead içinde 122 near-dup çift var.
Kitaplar aynı davranışı farklı sözcüklerle anlatıyor. Maliyet düşürme
sözcük düzeyinde yapılamaz; **kavram düzeyinde novelty-gate** ile yapılır.

**D2 — Sayfa anchor'ı bedava.** `pdftotext` form-feed'leri part dosyalarında
duruyor. `page_start/page_end: null` alanları lokal bir tarama ile doldurulur.
v2.0'ın `page_cited_claims: 1.0` kalite hedefi şu an **karşılanamaz** durumda;
bu düzeltme onu karşılanabilir yapar. Model maliyeti: sıfır.

**D3 — Part granülaritesi bozuk.** 80k token'lık part'larda "önceki part
kuyruğu + mevcut part + sonraki part başı" bağlamı imkânsız. Çalışma birimi
part değil, **bölüm/section (~4–8k token)** olmalı; lead'ler zaten satır
anchor'ı taşıyor, bu yeniden dilimleme lokal ve bedava.

---

## 1. Neden mevcut plan 8–10 saat değil

v2.0 spec'i her lead için A + B + counterevidence + adjudication istiyor:

```
12.457 lead × 4 aşama          = 49.828 agent çağrısı
çağrı başına ~45 s, eşzamanlılık 14 (min(16, cores-2))
49.828 × 45 / 14               ≈ 160.000 s ≈ 44,5 saat
girdi token'ı (≈8k/çağrı)      ≈ 400M token
```

Sorun süre değil, **doğrulama yoğunluğunun sonuçla orantısız dağıtılması**.
Sistematik derleme metodolojisinde çift-bağımsız değerlendirme *dahil etme*
adımında yapılır, her veri alanında değil. v2.1 aynı ilkeyi uygular.

---

## 2. Üç yeniden çerçeveleme

### R1 — Bu bir doyum (saturation) problemi, çıkarım problemi değil

Nitel kanıt sentezi literatürü stop-rule'u çözmüş: temaların ~%80'i ilk 6–7
kaynakta çıkar, doyum homojen örneklemde 9–17 kaynakta gerçekleşir; teori
düzeyi doyum heterojen örneklemde 20–30'a çıkar (Guest et al. 2020;
Hennink et al. 2017; Saunders et al. 2018).

Teknik analiz kitapları **homojen bir popülasyondur** — hepsi aynı 6 soydan
türer: Dow/Schabacker/Edwards-Magee · Wyckoff/hacim · Japon mumları ·
Elliott-Gann · kantitatif-akademik · piyasa mikroyapısı. 125 kitaptan çıkacak
**farklı davranış mekanizması sayısı 40–80 bandındadır**, 1.000 değil.

Doyum **mekanizma keşfi** için geçerlidir. Şunlar için geçerli DEĞİLDİR ve
ucuz olarak korpus geneli taranmaya devam edilmelidir:
- nicel/parametrik özgüllük (her kitap farklı sayı verir),
- caveat / failure condition / akademik çürütme (nadir ve yoğunlaşmış),
- execution & mikroyapı olguları (3–5 kitapta toplanmış).

**Uygulama:** mekanizma keşfi doyum eğrisi ölçülerek durdurulur
(base size 6 kitap, run length 3, eşik: yeni family < %5 → 3 ardışık tur kuru
ise dur). Diğer üç kategori ucuz süpürme ile tam korpusta taranır.

### R2 — Çıkarılan expert sayısı bir maliyet, bir başarı değil

Deflated Sharpe Ratio (Bailey & López de Prado 2014): null altında beklenen
maksimum Sharpe deneme sayısı N ile büyür. N=1.000 bağımsız denemede beklenen
maks Sharpe ≈ 1,3. Yani **1.000 expert üretip hepsini backtest etmek, herhangi
bir bulguyu iddia etme kabiliyetini yok eder.**

V8 bunu zaten biliyor: `V8_CONSTITUTION` rule 13 family düzeyinde çokluk
düzeltmesi istiyor ve `src/v8/experts/base.py` ontolojisi
`mechanism_family_id` / `behavior_family_id` / `variant_id` ayrımını kuruyor —
parametre/eşik/geometri değişimi **varyanttır, ayrı expert değildir ve çokluk
düzeltmesinde tek birim sayılır**.

**Uygulama:** araştırmanın çıktı birimi expert değil, **family**'dir. Hedef
40–70 canonical behavior family. Araştırma fazının birinci sınıf çıktılarından
biri **dürüst N sayacıdır**: kaç family önerildi, kaçı reddedildi, kaç varyant
denendi. Bu sayı `registry/trial_ledger.jsonl` olarak backtest fazına devredilir.

### R3 — Kitaplar tek hedefe değil, dört V8 alt sistemine akar

Kullanıcının "expertler, execution modelimiz, simülasyon, ne olursa" ifadesi
tek boru hattı değil, dört ayrı çıkarım hedefi demek:

| Track | Hedef V8 bileşeni | Tipik kaynak | Yoğunluk |
|---|---|---|---|
| **M** mekanizma | `experts/*.py` → ExpertSpec | setup/pattern kitapları | geniş, doygun |
| **X** execution/mikroyapı | `simulator.py` fill/cost/slippage | Harris *Trading & Exchanges*, Kissell, algo kitapları | dar, yoğun |
| **G** risk geometrisi & sizing | `risk.py`, `lifecycle.py` | Tharp, Vince, para yönetimi | dar, yoğun |
| **F** metodoloji/çürütme | `lab.py`, doğrulama kapıları | Aronson, Chan, akademik | dar, **en yüksek değer** |

Bir mum kitabını execution extractor'ından geçirmek saf israf. Routing kitap
düzeyinde, TOC + başlıktan, ucuza yapılır.

**Not — F track'in asimetrik değeri:** V8 bir yanlışlama programı olduğu için
125 kitaptaki en değerli içerik stratejiler değil, **onları öldüren
kısıtlardır**. Aronson tek başına çıkarılan mekanizmaların yarısını
diskalifiye edebilir. Bu yüzden counterevidence, v2.0'daki gibi claim başına
6. adım değil, **erken çalışan bağımsız korpus süpürmesidir**; sonraki her
claim bu indekse bakar. Hem daha ucuz hem daha dürüst.

---

## 3. Katmanlı doğrulama (tiered verification)

Doğrulama yoğunluğu **sonuca orantılı** dağıtılır:

| Tier | Ne | Kapsam | Çağrı/birim |
|---|---|---|---|
| **T0** | lokal işlem, model yok | tüm korpus | 0 |
| **T1** | recall denetimi (kalibrasyon) | tabakalı örneklem | ~30 toplam |
| **T2** | triage + routing, batch'li | 12.457 lead | 40 lead/çağrı |
| **T3** | tek güçlü geçiş (corroboration) | bilinen mekanizmanın yeni kaynak varyantı | 10 lead/çağrı |
| **T4** | A/B + audit + adjudication | **sadece**: yeni family · nicel parametre olacak claim · pre-register edilecek her şey | 4 çağrı/lead |

T4 girişi bir **novelty gate** ile korunur: lead mevcut canonical family
kaydına eşleniyor mu? Eşleşiyorsa → T3 (sayfa alıntılı corroboration kaydı,
kanıt ağırlığı artar, maliyet düşük). Eşleşmiyorsa → T4.

Maliyet korpus tükendikçe **düşer**; bu doyum eğrisinin operasyonel karşılığıdır.

---

## 4. Regex kalitesi: varsayma, ölç

Deterministik scout'un iki ayrı hatası var ve **maliyetleri simetrik değil**:

- **Precision kaybı ucuz.** `TRIGGER_RULE` deseni `when (?:the|a|price)`
  içeriyor; 9.185 isabetin büyük kısmı gürültü. Extractor bunu saniyeler
  içinde eler. Zarar: biraz token.
- **Recall kaybı görünmez ve kalıcı.** Bir kitap kurulumu fiil kalıbı
  kullanmadan, grafik anlatımıyla tarif ediyorsa lexicon onu hiç görmez.
  O mekanizma korpusta var ama sizin için yok.

**T1 recall denetimi (planın en yüksek getirili 25 dakikası):**
6 kitaptan (her track'ten, biri OCR, biri düşük kaliteli) tabakalı rastgele
12 section seçilir; bu section'lar LLM scout ile **tam** okunur; bulunan
lead'ler regex lead'leriyle karşılaştırılır.

Karar kuralı:
- recall ≥ 0.85 → deterministik scout ön-filtre olarak kabul, ek maliyet yok
- 0.60 ≤ recall < 0.85 → lexicon genişlet + T2 triage'ı **section düzeyinde**
  çalıştır (lead değil section görünür, kaçanlar yakalanır)
- recall < 0.60 → yalnız yüksek değerli kitaplarda (M-track top-30 + tüm X/G/F)
  LLM scout, gerisinde regex

Maliyet: ~30 çağrı. Karşılığı: korpus genelinde ölçülmüş bir recall sayısı
ve "regex yüzünden ne kaybettik" sorusunun kapanması.

---

## 5. Faz planı ve zaman bütçesi

Eşzamanlılık 14, ortalama çağrı 45 s varsayımıyla.

| Faz | İş | Çağrı | Süre |
|---|---|---|---|
| **P0** | lokal: sayfa haritası (`\f`), section re-chunk, kitap routing (M/X/G/F), doyum sayacı iskeleti, lead→section bağlama | 0 | ~30 dk (CPU) |
| **P1** | T1 recall denetimi + 5 kitaplık kalibrasyon (v2.0'daki seçim korunur) | ~30 | ~25 dk |
| **P2** | T2 triage/routing: 12.457 lead, 40'lık batch | ~312 | ~17 dk |
| **P3** | F-track: korpus geneli counterevidence/caveat süpürmesi (kitap başına 1) | ~125 | ~7 dk |
| **P4** | M-track: novelty-gated mekanizma çıkarımı (T3 ~155 + T4 ~1.000) | ~1.155 | ~62 dk |
| **P5** | X + G track'leri (dar, yoğun okuma) | ~120 | ~7 dk |
| **P6** | book synthesis → canonical registry → crypto translation → ExpertSpec → validate (≈60 family × 4) | ~240 | ~13 dk |
| | **toplam** | **~1.982** | **~2 sa 40 dk** |

44,5 saat → ~2,7 saat. Kazanç kısaltmadan değil, **doğrulamayı sonuca göre
bütçelemekten** geliyor.

### Kilitlenen kapsam kararı (2026-08-02)

- **Kapsam: tam korpus, 125 kitap.** Hiçbir kitap P4 dışında bırakılmaz.
- **Track'ler: F + M + X + G, dördü de aktif.**
- **Doyum bir durdurucu değil, bir indirgeyicidir.** Tam kapsama korunur;
  3 ardışık tur yeni family üretmezse kalan turlar T4 (A/B + audit +
  adjudication) yerine **T3-only** (corroboration) moduna düşürülür. Kapsama
  kaybı yok, maliyet sınırlı. Bu karar `saturation_ledger.jsonl`'e yazılır ve
  geri alınabilir: sonraki turda yeni family çıkarsa T4 yeniden açılır.

Yürütme adımlarının tamamı `EXECUTION_PLAN_v2.1.md` dosyasındadır.

---

## 6. Sert kalite kapıları (v2.0'dan devralınan + eklenen)

v2.0'ın kaynak/sadakat/executability/PIT/translation/expert kapıları aynen
geçerli. v2.1 üç kapı ekler:

```
[ ] SATURATION_LOGGED    her turda yeni family sayısı ve doyum oranı kayıtlı
[ ] TRIAL_COUNT_LEDGER   önerilen/reddedilen family + varyant sayısı sayılıyor
                         (DSR'nin N'i sonradan uydurulamaz)
[ ] SCOUT_RECALL_MEASURED  T1 denetimi çalıştı, recall sayısı kayıtlı;
                         ölçülmemiş recall ile korpus koşusu başlamaz
```

Ve v2.0'ın karşılanamaz durumdaki hedefi düzeltilir:
`page_cited_claims: 1.0` ancak P0 sayfa haritası tamamlandıktan sonra
denetlenebilir; öncesinde `page_anchor_status: UNMAPPED` yazılır, sıfır
uydurulmaz.

---

## 7. Ne yapılmayacak

- Legacy v1 bulguları `RawClaim`'e dönüştürülmeyecek — yalnız recall kontrol
  listesi (v2.0 kararı korunuyor).
- Expert sayısı maksimize edilmeyecek; family sayısı ve prior gücü optimize
  edilecek (R2).
- Backtest araştırması bu boru hattına karıştırılmayacak; family kümesi
  ve trial ledger **dondurulmadan** ölçüm başlamayacak.
- `src/v8/` içine bu fazda kod eklenmeyecek; çıktı ExpertSpec'tir, expert
  compilation ayrı ve QA-gated bir adımdır (v2.0 stage 13).

---

## 8. Dürüst kısıtlar

- Doyum eğrisi bir *tahmin* değil ölçümdür, ama ölçümü tanımlayan family
  ontolojisi bizim kurgumuzdur; ontoloji çok kaba olursa doyum yapay olarak
  erken görünür. Bu yüzden family granülaritesi `base.py`'deki
  mechanism/behavior/variant ayrımına bağlanmıştır, serbest bırakılmamıştır.
- 40–80 family beklentisi literatür yapısına dayanan bir öngörüdür,
  ölçülmüş değildir. P4'ün ilk turu bunu doğrular veya çürütür.
- Süre tahminleri 45 s/çağrı ve 14 eşzamanlılık varsayımına dayanır;
  gerçek değerler P1 sonunda ölçülüp bu tablo güncellenmelidir.
- Regex scout'un recall'ü **henüz bilinmiyor**. P1 öncesi hiçbir korpus
  koşusu başlatılmamalıdır.
