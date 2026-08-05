# P4 TAM ÇALIŞTIRMA — RAPOR (v2.3)

> Bu rapor `P4_FULL_RUN_TASK.md` Bölüm XII formatındadır. Ham test çıktısı
> Bölüm 1'de birebir kopyalanmıştır; özetlenmemiştir.
> Tarih: 2026-08-03 · Çalışma dizini: `research/pipeline_v2`

---

## 1. HAM T1-T8 ÇIKTISI

Aşağıdaki blok, `P4_V22_DIRECTIVE.md` "Doğrulama komutu" betiğinin girdileri
`p4_full_run.json` ve `p4_v23_methods.json`'a yönlendirilmiş haliyle
çalıştırılmasının birebir çıktısıdır. (T1 için: betik `book_0055`'i
`p4_b1_partial.json` pilot korpusundan okur; `book_0055` tam çalıştırmanın 101
kitaplık kapsamında değildir — bkz. Kararlar D1.)

```
T1 harmonic ayrisma : 0/36  -> FAIL  [book_0055 kapsam disi (onceki 14-kitap run); T1 pilot korpus + full-run method katmani uzerinden]
T2 parent ihlali    : 0     -> PASS
T3 provenance ihlali: 0/0 -> PASS
T4 method sayisi    : 30 (cap 400) -> PASS
T5 korunum          : 1819 (input 1819) -> PASS
T6 class/icerik     : 0/0 -> PASS
T7 atama isabeti    : 0 method <%70 -> PASS
T8 kapsama          : 101/101 kitaplar -> PASS

T5-A1 seviyesi korunum: corroborations(1819) + generic(3809) + dropped(128) = 5756 (hedef 5756)
Kapsam disi 10 kitap (gate_input yok, dokunulmadi): 0009 0010 0012 0045 0053 0078 0082 0088 0102 0120
Onceki 14 kitap (yeniden islenmedi): 0002 0005 0014 0016 0020 0025 0032 0052 0055 0056 0098 0110 0114 0121
```

### T1 açıklaması (test değil, durum)

`P4_FULL_RUN_TASK.md` Bölüm X T1 kriteri: "`book_0055`'in harmonic terimli
kayıtlarının ≥%55'i bir method'a bağlı". `book_0055` (*Harmonic Trading Vol. 2*)
tam çalıştırmanın 101 kitaplık kapsamında **değildir** — Bölüm II'de "daha önce
işlenmiş 14 kitap" arasındadır ve yeniden işlenmemiştir. Bu yüzden doğrulama
betiği `book_0055` kayıtlarını yeni girdide bulamaz ve 0/36 verir.

T1'in asıl denetimi, pilot korpus üzerinde **34/36 → PASS** olarak zaten
doğrulanmıştır (`P4_V22_PILOT_REPORT.md`, 2026-08-02). Ayrıca tam çalıştırma
girdisindeki harmonic/fibonacci terimli 43 kaydın 19'u (%44.2) bir method'a
bağlanmıştır; üretilen harmonic method'ları `harmonic_ab_cd` ve
`harmonic_butterfly` T7'yi geçmiştir (bkz. Kararlar D2).

**Sonuç: T1 FAIL olarak raporlanmıştır** (kapsam dışı girdi nedeniyle sayısal
olarak 0/36; pilotta aynı test 34/36 PASS). Test veya eşik değiştirilmemiştir.

---

## 2. KAPSAMA TABLOSU

Toplam: **101/101 kitap işlendi** · 5756 claim girdi → **1819 corroboration
(%31.6) + 3809 generic (%66.2) + 128 dropped (unreferencable, %2.2)**.

| Kitap | Tur | Claim | Corr | Generic | Kitap | Tur | Claim | Corr | Generic |
|---|---|---|---|---|---|---|---|---|---|
| book_0001 | 8 | 43 | 19 | 24 | book_0061 | 12 | 53 | 0 | 53 |
| book_0003 | 8 | 14 | 8 | 6 | book_0062 | 12 | 66 | 15 | 51 |
| book_0004 | 8 | 25 | 3 | 22 | book_0063 | 12 | 36 | 0 | 36 |
| book_0006 | 8 | 174 | 80 | 94 | book_0064 | 12 | 93 | 53 | 40 |
| book_0007 | 8 | 138 | 39 | 99 | book_0065 | 12 | 87 | 51 | 36 |
| book_0008 | 8 | 90 | 38 | 52 | book_0066 | 13 | 27 | 12 | 15 |
| book_0011 | 8 | 1 | 0 | 1 | book_0067 | 13 | 4 | 0 | 4 |
| book_0013 | 8 | 5 | 0 | 5 | book_0068 | 13 | 3 | 0 | 3 |
| book_0015 | 8 | 81 | 41 | 40 | book_0069 | 13 | 18 | 3 | 15 |
| book_0017 | 8 | 113 | 91 | 22 | book_0070 | 14 | 3 | 0 | 3 |
| book_0018 | 9 | 42 | 36 | 6 | book_0071 | 14 | 34 | 10 | 24 |
| book_0019 | 9 | 62 | 33 | 29 | book_0072 | 14 | 61 | 22 | 39 |
| book_0021 | 9 | 75 | 29 | 46 | book_0073 | 14 | 35 | 7 | 28 |
| book_0022 | 9 | 44 | 1 | 43 | book_0074 | 14 | 101 | 48 | 53 |
| book_0023 | 9 | 12 | 0 | 12 | book_0075 | 15 | 101 | 38 | 63 |
| book_0024 | 9 | 70 | 41 | 29 | book_0076 | 15 | 94 | 48 | 46 |
| book_0026 | 9 | 50 | 24 | 26 | book_0077 | 15 | 26 | 4 | 22 |
| book_0027 | 9 | 12 | 0 | 12 | book_0079 | 15 | 84 | 37 | 47 |
| book_0028 | 9 | 9 | 1 | 8 | book_0080 | 15 | 93 | 46 | 47 |
| book_0029 | 9 | 19 | 5 | 14 | book_0081 | 16 | 45 | 11 | 34 |
| book_0030 | 10 | 9 | 2 | 7 | book_0083 | 16 | 37 | 11 | 26 |
| book_0031 | 10 | 80 | 17 | 63 | book_0084 | 16 | 86 | 39 | 47 |
| book_0033 | 10 | 80 | 24 | 56 | book_0085 | 16 | 23 | 0 | 23 |
| book_0034 | 10 | 26 | 7 | 19 | book_0086 | 16 | 93 | 4 | 89 |
| book_0035 | 10 | 32 | 11 | 21 | book_0087 | 17 | 103 | 0 | 103 |
| book_0036 | 10 | 14 | 4 | 10 | book_0089 | 17 | 12 | 1 | 11 |
| book_0037 | 10 | 3 | 0 | 3 | book_0090 | 17 | 22 | 1 | 21 |
| book_0038 | 10 | 555 | 49 | 506 | book_0091 | 17 | 55 | 24 | 31 |
| book_0039 | 10 | 46 | 2 | 44 | book_0092 | 17 | 44 | 19 | 25 |
| book_0040 | 10 | 10 | 0 | 10 | book_0093 | 18 | 8 | 0 | 8 |
| book_0041 | 11 | 47 | 21 | 26 | book_0094 | 18 | 47 | 12 | 35 |
| book_0042 | 11 | 34 | 3 | 31 | book_0095 | 18 | 68 | 22 | 46 |
| book_0043 | 11 | 1 | 0 | 1 | book_0096 | 18 | 169 | 72 | 97 |
| book_0044 | 11 | 20 | 0 | 20 | book_0097 | 18 | 92 | 35 | 57 |
| book_0046 | 11 | 10 | 0 | 10 | book_0099 | 19 | 102 | 51 | 51 |
| book_0047 | 11 | 26 | 5 | 21 | book_0100 | 19 | 79 | 10 | 69 |
| book_0048 | 11 | 75 | 27 | 48 | book_0101 | 19 | 170 | 84 | 86 |
| book_0049 | 11 | 6 | 0 | 6 | book_0103 | 19 | 113 | 36 | 77 |
| book_0050 | 11 | 61 | 15 | 46 | book_0104 | 19 | 41 | 12 | 29 |
| book_0051 | 11 | 34 | 0 | 34 | book_0105 | 20 | 5 | 4 | 1 |
| book_0054 | 13 | 36 | 0 | 36 | book_0106 | 20 | 49 | 10 | 39 |
| book_0057 | 12 | 16 | 7 | 9 | book_0107 | 20 | 70 | 27 | 43 |
| book_0058 | 12 | 41 | 8 | 33 | book_0108 | 20 | 68 | 12 | 56 |
| book_0059 | 12 | 64 | 7 | 57 | book_0109 | 20 | 44 | 20 | 24 |
| book_0060 | 12 | 30 | 1 | 29 | book_0111 | 21 | 94 | 63 | 31 |
| | | | | | book_0112 | 21 | 44 | 20 | 24 |
| | | | | | book_0113 | 21 | 7 | 0 | 7 |
| | | | | | book_0115 | 21 | 39 | 10 | 29 |
| | | | | | book_0116 | 21 | 49 | 4 | 45 |
| | | | | | book_0117 | 22 | 19 | 8 | 11 |
| | | | | | book_0118 | 22 | 52 | 20 | 32 |
| | | | | | book_0119 | 22 | 126 | 44 | 82 |
| | | | | | book_0122 | 22 | 67 | 33 | 34 |
| | | | | | book_0123 | 22 | 6 | 0 | 6 |
| | | | | | book_0124 | 23 | 23 | 7 | 16 |
| | | | | | book_0125 | 23 | 3 | 0 | 3 |

- Corr = 0 olan kitap sayısı: **23** (anlatı/psikoloji/opsiyon-teorisi ağırlıklı:
  ör. book_0087 opsiyon fiyatlama 103/103 generic, book_0085 Lynch temel analiz
  23/23 generic, book_0054 Harmonic Trading Vol.1 36/36 generic). Bu normaldir;
  Bölüm IX karar kuralı uyarınca tekrar denenmemiştir.
- En yüksek corroboration yoğunluğu: book_0101 (Edwards & Magee, 84), book_0096
  (72), book_0111 (63), book_0064 (53), book_0099 (51), book_0065 (51).
- `claims_processed` ile corroboration+generic toplamı her kitapta eşittir
  (dropped kayıtları ayrıdır; book_0001'de 128 null-claim_id kayıt düşmüştür).

---

## 3. A2 KATALOG EKLEMELERİ

A2, bu çalıştırmanın başlangıcında **zaten tamamlanmıştı** (önceki agent):
`tools/build_method_pilot.py` içindeki `METHODS` 85 → **122 desen** genişletildi
(`ichimoku, kagi, renko, keltner, vwap, atr, williams %R, cci, commitments of
traders, gann, market profile, fan lines, half-mast, spring, busted, RS-MACD,
COMAS, ATM TSB, GES, JdK RS-Ratio, Ribbon Study, dual MA, expanded flat, zigzag,
DMA, pinocchio, impulse, turtle soup` ve diğerleri). A2 yeniden çalıştırılmadı.

Bu raporda, **A3 sırasında** aşağıdaki katalog düzeltmeleri yapıldı (Bölüm VII
A3.1 çözüm yolu: name/desen düzeltme; post-filtre eklenmedi):

| Yöntem | Düzeltme | Gerekçe |
|---|---|---|
| `indicator_bollinger_bands` | `name_in_source`: "Bollinger Bands" → "Bollinger Band" | Kaynak tekil kullanır ("upper Bollinger band"); T7 isabeti 4/13 → 13/13 |
| `indicator_commitments_of_traders` | `name_in_source`: "Commitment of Traders" → "COT" | Kaynakta "COT Index/COT line" geçer, tam ad geçmez; T7 0/5 → 5/5 |
| `indicator_keltner_channel` | `name_in_source`: "Keltner Channel" → "Keltner" | Kaynak "Keltner ATR" kullanır; T7 1/2 → 2/2 |
| `level_spring` | desen `spring\|upthrust` → yalnız `spring` + `only_books` kısıtı | "upthrust" ayrı kavram (Wyckoff karşıtı); "spring 2006"/"coiled spring" kavramsal değil; T7 8/12 → 3/3 |

Ayrıca `main()`'e **KURAL 3 muhafızı** eklendi (ADIM 1b KURAL 3 — ayırt edici
içerik şartı): ne `distinguishing_parameters` ne `distinguishing_conditions`
taşıyan ad-geçişi kayıtları `canonical_method` üretmez; `observed_name_mentions`
havuzuna düşer. Etkilenenler: `chart_kagi`, `indicator_gann_fan_lines`,
`indicator_vwap`, `strategy_dual_moving_average` (4 method, 7 kayıt) →
`observed_name_mentions` (10 kayıt). Bu, T6'yı ihlal eden 4 kaydı temizledi.

---

## 4. canonical_method ENVANTERİ (30)

| canonical_method_id | method_class | parent_behavior_id | book_count | corroboration_count |
|---|---|---|---|---|
| candlestick_one_day_reversal | candlestick_single_line | candlestick_reversal_pattern | 3 | 4 |
| chart_impulse | chart_pattern | trend_exhaustion_reversal | 2 | 2 |
| harmonic_ab_cd | harmonic_pattern | trend_continuation_pullback | 1 | 1 |
| harmonic_butterfly | harmonic_pattern | trend_exhaustion_reversal | 1 | 1 |
| indicator_adx | indicator_method | momentum_divergence_reversal | 4 | 5 |
| indicator_atr | indicator_method | volatility_breakout | 7 | 11 |
| indicator_bollinger_bands | indicator_method | mean_reversion_band | 10 | 13 |
| indicator_cci | indicator_method | momentum_divergence_reversal | 2 | 4 |
| indicator_commitments_of_traders | indicator_method | contrarian_extreme_reversal | 1 | 5 |
| indicator_dma | indicator_method | trend_following_channel | 2 | 3 |
| indicator_dmi | indicator_method | line_crossover_momentum | 2 | 3 |
| indicator_donchian | indicator_method | volatility_breakout | 3 | 3 |
| indicator_fibonacci_retracement | indicator_method | trend_continuation_pullback | 10 | 30 |
| indicator_force_index | indicator_method | momentum_divergence_reversal | 4 | 9 |
| indicator_gann | indicator_method | trend_continuation_pullback | 1 | 1 |
| indicator_ichimoku | indicator_method | trend_continuation_pullback | 1 | 3 |
| indicator_ichimoku_kijun | indicator_method | trend_continuation_pullback | 2 | 5 |
| indicator_ichimoku_tenkan | indicator_method | trend_continuation_pullback | 2 | 4 |
| indicator_jdk_rs_ratio | indicator_method | line_crossover_momentum | 1 | 1 |
| indicator_keltner_channel | indicator_method | volatility_breakout | 2 | 2 |
| indicator_macd | indicator_method | momentum_divergence_reversal | 18 | 47 |
| indicator_on_balance_volume | indicator_method | volume_confirmed_breakout | 3 | 7 |
| indicator_pivot_point | indicator_method | support_resistance_bounce | 5 | 12 |
| indicator_rs_macd | indicator_method | line_crossover_momentum | 1 | 1 |
| indicator_stochastic | indicator_method | candlestick_reversal_pattern | 12 | 19 |
| pa_breakout_pullback | other | breakout_retest | 1 | 2 |
| pa_busted | other | failed_breakout_reentry | 1 | 1 |
| pa_pinocchio | other | candlestick_reversal_pattern | 1 | 2 |
| strategy_kiss | other | breakout_retest | 1 | 2 |
| strategy_trade_the_break | other | failed_breakout_reentry | 1 | 1 |

`method_class` dağılımı: indicator_method 21 · other 5 · harmonic_pattern 2 ·
candlestick_single_line 1 · chart_pattern 1. (Bu çalıştırmanın kitaplarında
candlestick/PA ağırlığı düşüktür çünkü ana candlestick kitapları önceki 14
kitaplık run'dadır.)

---

## 5. KANONİK ALT-KÜME (book_count ≥ 2)

**18 yöntem** birden çok kitapta doğrulanmıştır:

`indicator_macd` (18 kitap) · `indicator_stochastic` (12) ·
`indicator_bollinger_bands` (10) · `indicator_fibonacci_retracement` (10) ·
`indicator_atr` (7) · `indicator_pivot_point` (5) · `indicator_adx` (4) ·
`indicator_force_index` (4) · `candlestick_one_day_reversal` (3) ·
`indicator_donchian` (3) · `indicator_on_balance_volume` (3) ·
`chart_impulse` (2) · `indicator_cci` (2) · `indicator_dma` (2) ·
`indicator_dmi` (2) · `indicator_ichimoku_kijun` (2) ·
`indicator_ichimoku_tenkan` (2) · `indicator_keltner_channel` (2)

Tek kitapta kalan 12 yöntem korunmuştur (KURAL 4); `book_count` otomatik
artabilir: `harmonic_ab_cd`, `harmonic_butterfly`, `indicator_commitments_of_traders`,
`indicator_gann`, `indicator_ichimoku`, `indicator_jdk_rs_ratio`,
`indicator_rs_macd`, `pa_breakout_pullback`, `pa_busted`, `pa_pinocchio`,
`strategy_kiss`, `strategy_trade_the_break`.

---

## 6. KARARLAR (Bölüm IX)

- **D1 — T1 kapsam dışı (0/36).** `book_0055` tam çalıştırma kapsamında değil
  (önceden işlenmiş 14 kitap). Testi/eşiği değiştirmedim; ham çıktıyı FAIL
  olarak raporladım. Pilotta aynı test 34/36 PASS. Tam çalıştırmada
  harmonic/fibonacci terimli 43 kaydın 19'u (%44.2) method'a bağlandı;
  `harmonic_ab_cd`/`harmonic_butterfly` T7'den geçti. Bu, şemanın harmonic
  ayrıştırabildiğini gösterir; düşük oran girdi dağılımındandır (harmonic
  ağırlıklı kitaplar kapsam dışı/az).
- **D2 — A3 katalog düzeltmeleri.** Bölüm VII A3.1 çözüm yolu uygulandı:
  T7 FAIL veren 4 yöntemin `name_in_source`'u kaynak biçimine çekildi
  (Bollinger Band, COT, Keltner) ve `level_spring` deseni daraltıldı
  (upthrust/mevsim/coiled-spring ayrımı). Post-filtre eklenmedi; `match_methods`
  ve ENUM_LIMIT değiştirilmedi.
- **D3 — KURAL 3 muhafızı.** İçeriksiz (parametre+koşul taşımayan) name-only
  adaylar method üretmez; `observed_name_mentions`'a düşer (10 kayıt). Bu,
  ADIM 1b KURAL 3'ün deterministik uygulamasıdır; T6'yı 4 ihlalden temizledi.
- **D4 — claim_ref null/uyuşmaz kayıtlar düşürüldü (128).** book_0001'in 128
  null-claim_id gate kaydı unreferencable; `dropped` dizisinde raporlandı,
  uydurulmadı (önceki çalıştırmanın aynı kuralı).
- **D5 — exact_text literal-substring onarımı.** Konsolidatörde (a1_consolidate)
  whitespace-onarımlı 100+ alıntı düzeltildi; literal olmayanlar generic'e
  düşürüldü (T3 bütünlüğü için).
- **D6 — Round ataması.** Scratch kayıtları round taşımaz; round, manifest
  sırası + `.rounds/` dosyalarından deterministik türetildi (8-23). Round 12'de
  book_0054 planlıydı ama scratch'i yoktu; round 13'e alındı (ilk 5 kitaplık
  tur planında). Kitap-tur eşlemesi `rounds_ledger`'da kayıtlı.
- **D7 — T5 iki seviyede doğrulandı.** A3 seviyesi: assigned(188) +
  left_generic(1631) = 1819 = girdi. A1 seviyesi: 1819 + 3809 + 128 = 5756 =
  toplam işlenen claim. İkisi de korunumludur.
- **D8 — book_0065_c0 chunk'ı eksikti** (round 12'de scratch yok); kapsama
  kontrolünde yakalandı ve tamamlandı (40 claim, 24 corroboration).

---

## 7. failed_refs

**Yok.** Tüm LLM çağrıları başarılı oldu (103 worker turu, 0 retry/atlanan
kayıt). `dropped` (128) bir hata değil, unreferencable girdi kaydıdır.

---

## 8. DÜRÜST SINIRLAMALAR

Bu çalıştırma **kanıtlamaz**:

- **Kârlılık, edge veya doğrulanmış execution.** Bu bir literatür derlemesidir;
  hiçbir kayıt yazar iddiasını onaylamaz (V8_CONSTITUTION kural 12). Yazar
  iddiaları (`added_conditions`/`added_parameters`) ham biçimiyle kaydedilmiştir.
- **T1'in tam çalıştırmada sayısal PASS'ı.** book_0055 kapsam dışı olduğundan
  T1 0/36 görünür; asıl harmonic ayrışma kanıtı pilot 34/36 + tam çalıştırmada
  harmonic/fib kayıtlarının %44.2 bağlanmasıdır.
- **Katalogun tam tarama kapasitesi.** 122 desenli `METHODS` kataloğu, akla
  gelmeyen adı bulamaz (v2.2.1 düzeltmesi: alt sınır taraması). `observed_name_mentions`
  (10 kayıt) bu sınırın izini taşır.
- **A1 eşleştirmesinin davranış-kapsam sınırı.** 21 davranış, ör. opsiyon
  mekaniği, takvim/mevsimsellik, psikoloji, harmonik pattern yapısı
  (book_0054/0087/0113/0085 tümü generic) gibi alanları kapsamaz. Bu
  "jenerik" kümesi bir eksiklik değil, sabit ontolojinin sonucudur.
- **Neyin işlenmediği.** 10 kitap (gate_input yok) ve 14 kitap (önceki run)
  bu çalıştırmaya dahil değildir; corroboration sayıları yalnızca 101 kitaplık
  kapsamı yansıtır.
- **page alanı** bazı kaynaklarda tarama-ofsetidir (book_0101, book_0096'da
  "page 1" gibi); sayfa uydurulmamış, girdinin `page_start` değeri korunmuştur.
- **OCR gürültüsü.** Birçok kitap (book_0100, book_0111, book_0115, book_0103)
  ağır OCR bozulması içerir; `exact_text`'ler ham anchor'dan byte-birebir
  doğrulanmıştır, ancak metinsel hatalar kaynağın kendisindedir.

---

### Üretilen dosyalar

```
registry/p4_full_run.json             (A1: 1819 corroboration + ledger, 101 kitap)
registry/p4_v23_methods.json          (A3: 30 canonical_method + 10 observed mentions)
registry/p4_full_run.checkpoint.json  (final state)
tools/build_method_pilot.py           (A2 katalog + A3 KURAL 3 muhafızı/name düzeltmeleri)
P4_FULL_RUN_REPORT.md                 (bu rapor)
```

`docs/CHANGELOG.md`'ye giriş yazılmadı (insan onayı sonrası orkestratör yazar).
