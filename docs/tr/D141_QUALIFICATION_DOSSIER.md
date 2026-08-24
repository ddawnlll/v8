# D-141 Nitelendirme Dosyası

**Karar:** D-141 Expert Kanıtlama Alanı ve Alfa Arıtıcısı
**Kapsam:** yalnız deterministik anlamsal nitelendirme
**Ekonomik otorite:** `NO_ECONOMIC_CLAIM`

## Yalnız-test sınırı

Pilot nitelendirme yalnız Rust test build'lerinde çalışır. Production CLI çıktısı
veya kalıcı sentetik makbuz üretmez; kapsamlı doğrulama komutu şudur:

```text
cargo test --manifest-path v8-core/Cargo.toml qualification::tests
```

## Pilot sonuç sözleşmesi

| Expert | Resmî manifest | Anlamsal hüküm | Ekonomik hüküm |
|---|---|---|---|
| `failed_breakout:v1` | D-141 test manifesti | EWQ-01…06 geçerse yalnız `SEMANTICALLY_QUALIFIED` | `NO_ECONOMIC_CLAIM` |
| `fib_projection_reversal:v1` | D-141 test manifesti | EWQ-01…06 geçerse yalnız `SEMANTICALLY_QUALIFIED` | `NO_ECONOMIC_CLAIM` |
| `ichimoku_cloud:v2` | D-141 test manifesti | EWQ-01…06 geçerse yalnız `SEMANTICALLY_QUALIFIED` | `NO_ECONOMIC_CLAIM` |

Mevcut suite, 28 tanıklı registry içinde 3 pilot tanığı çalıştırır (3/28 = %10,71 manifest kapsamı). Diğer kayıtlı tanıklar kendi Davranış Kartı, senaryoları ve manifestlerini almadan geçmiş/başarısız sayılmaz. Registry manifest kapsamı, çalıştırılmış test geçiş oranından ayrı raporlanır.

## Kapı yorumu

- EWQ-01…06 anlamsal nitelendirme kapılarıdır. Başarısız kanonik, metamorfik veya kritik mutasyon kontrolü nitelendirmeyi yanlışlar.
- EWQ-07 (mühürlü challenge) ve EWQ-08 (istatistiksel no-regression) pilot çalıştırmada `UNRESOLVED` kalır.
- EWQ-09 (gerçek-bant atfı) sentetik anlamsal çalıştırmada `NOT_APPLICABLE`'dır.
- EWQ-10 (frozen ekonomik OOS) `BLOCKED`'dir; D-141 yetki yoksa yerine veri açmaz.

Hiçbir D-141 makbuzu canlı kârlılık, gerçekleşmiş nakit akışı veya terfi uygunluğu kanıtı değildir.
