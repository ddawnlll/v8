# D-141 Nitelendirme Dosyası

**Karar:** D-141 Expert Kanıtlama Alanı ve Alfa Arıtıcısı
**Kapsam:** yalnız deterministik anlamsal nitelendirme
**Ekonomik otorite:** `NO_ECONOMIC_CLAIM`

## Makbuz

Çalıştırılabilir makbuz `.audit/d141/current/PILOT_QUALIFICATION_REPORT.json` dosyasıdır ve şu komutla fiziksel olarak üretilir:

```text
cargo run --manifest-path v8-core/Cargo.toml -- qualify-experts --out .audit/d141/current/PILOT_QUALIFICATION_REPORT.json
```

Makbuz yalnız dosya fiziksel olarak mevcutsa ve manifest/run hash'leri çalıştırılan kodla eşleşiyorsa geçerlidir. Kâr, getiri veya terfi iddiası içermez.

## Pilot sonuç sözleşmesi

| Expert | Resmî manifest | Anlamsal hüküm | Ekonomik hüküm |
|---|---|---|---|
| `failed_breakout:v1` | makbuzdaki D-141 manifest hash'i | EWQ-01…06 geçerse yalnız `SEMANTICALLY_QUALIFIED` | `NO_ECONOMIC_CLAIM` |
| `fib_projection_reversal:v1` | makbuzdaki D-141 manifest hash'i | EWQ-01…06 geçerse yalnız `SEMANTICALLY_QUALIFIED` | `NO_ECONOMIC_CLAIM` |

Diğer kayıtlı tanıklar kendi Davranış Kartı ve manifestlerini almadan geçmiş/başarısız sayılmaz. Registry manifest kapsamı, çalıştırılmış test geçiş oranından ayrı raporlanır.

## Kapı yorumu

- EWQ-01…06 anlamsal nitelendirme kapılarıdır. Başarısız kanonik, metamorfik veya kritik mutasyon kontrolü nitelendirmeyi yanlışlar.
- EWQ-07 (mühürlü challenge) ve EWQ-08 (istatistiksel no-regression) pilot makbuzda `UNRESOLVED` kalır.
- EWQ-09 (gerçek-bant atfı) sentetik anlamsal çalıştırmada `NOT_APPLICABLE`'dır.
- EWQ-10 (frozen ekonomik OOS) `BLOCKED`'dir; D-141 yetki yoksa yerine veri açmaz.

Hiçbir D-141 makbuzu canlı kârlılık, gerçekleşmiş nakit akışı veya terfi uygunluğu kanıtı değildir.
