# D-141 Nitelendirme Dosyası

**Karar:** D-141 Expert Kanıtlama Alanı ve Alfa Arıtıcısı
**Kapsam:** yalnız deterministik anlamsal nitelendirme
**Ekonomik otorite:** `NO_ECONOMIC_CLAIM`

## Test-only kanıt sınırı

D-141 anlamsal senaryoları Rust `#[cfg(test)]` fixture'larıdır. Production CLI'da `qualify-experts` komutu ve D-141 sentetik makbuz yazıcısı yoktur: bu, üretilmiş dünyaların runtime evaluation veya rapor artifact'lerine girmesini engeller. Yetkili doğrulama, incelenen kod revizyonuna bağlı scoped Rust test çıktısıdır; kâr, getiri veya terfi iddiası içermez.

## Pilot sonuç sözleşmesi

| Expert | Resmî manifest | Anlamsal hüküm | Ekonomik hüküm |
|---|---|---|---|
| `failed_breakout:v1` | test kanıtındaki D-141 manifest hash'i | EWQ-01…06 geçerse yalnız `SEMANTICALLY_QUALIFIED` | `NO_ECONOMIC_CLAIM` |
| `fib_projection_reversal:v1` | test kanıtındaki D-141 manifest hash'i | EWQ-01…06 geçerse yalnız `SEMANTICALLY_QUALIFIED` | `NO_ECONOMIC_CLAIM` |
| `liquidity_sweep_reclaim:v1` | test kanıtındaki D-141 manifest hash'i | EWQ-01…06 geçerse yalnız `SEMANTICALLY_QUALIFIED` | `NO_ECONOMIC_CLAIM` |
| `trend_pullback:v1` | test kanıtındaki D-141 manifest hash'i | EWQ-01…06 geçerse yalnız `SEMANTICALLY_QUALIFIED` | `NO_ECONOMIC_CLAIM` |
| `trend_pullback_depth:v1` | test kanıtındaki D-141 manifest hash'i | EWQ-01…06 geçerse yalnız `SEMANTICALLY_QUALIFIED` | `NO_ECONOMIC_CLAIM` |
| `donchian_breakout:v1` | test kanıtındaki D-141 manifest hash'i | EWQ-01…06 geçerse yalnız `SEMANTICALLY_QUALIFIED` | `NO_ECONOMIC_CLAIM` |
| `volume_confirmed_breakout:v1` | test kanıtındaki D-141 manifest hash'i | EWQ-01…06 geçerse yalnız `SEMANTICALLY_QUALIFIED` | `NO_ECONOMIC_CLAIM` |
| `range_breakout_1to1:v1` | test kanıtındaki D-141 manifest hash'i | EWQ-01…06 geçerse yalnız `SEMANTICALLY_QUALIFIED` | `NO_ECONOMIC_CLAIM` |
| `floor_trader_pivot:v1` | test kanıtındaki D-141 manifest hash'i | EWQ-01…06 geçerse yalnız `SEMANTICALLY_QUALIFIED` | `NO_ECONOMIC_CLAIM` |
| `fib_retracement_continuation:v1` | test kanıtındaki D-141 manifest hash'i | EWQ-01…06 geçerse yalnız `SEMANTICALLY_QUALIFIED` | `NO_ECONOMIC_CLAIM` |
| `obv_adl_regime:v1` | test kanıtındaki D-141 manifest hash'i | EWQ-01…06 geçerse yalnız `SEMANTICALLY_QUALIFIED` | `NO_ECONOMIC_CLAIM` |
| `funding_crowding_reversal:v1` | test kanıtındaki D-141 manifest hash'i | EWQ-01…06 geçerse yalnız `SEMANTICALLY_QUALIFIED` | `NO_ECONOMIC_CLAIM` |
| `open_interest_divergence:v1` | test kanıtındaki D-141 manifest hash'i | EWQ-01…06 geçerse yalnız `SEMANTICALLY_QUALIFIED` | `NO_ECONOMIC_CLAIM` |

Diğer kayıtlı generator-expert'ler kendi Davranış Kartı ve manifestlerini almadan geçmiş/başarısız sayılmaz. Payda 29 değil 28'dir: `predicate` Expert tanığı değil post-entry tez değerlendiricisidir. Registry manifest kapsamı, çalıştırılmış test geçiş oranından ayrı raporlanır.

## Kapı yorumu

- EWQ-01…06 anlamsal nitelendirme kapılarıdır. Başarısız kanonik, metamorfik veya kritik mutasyon kontrolü nitelendirmeyi yanlışlar.
- EWQ-07 (mühürlü challenge) ve EWQ-08 (istatistiksel no-regression) pilot makbuzda `UNRESOLVED` kalır.
- EWQ-09 (gerçek-bant atfı) sentetik anlamsal çalıştırmada `NOT_APPLICABLE`'dır.
- EWQ-10 (frozen ekonomik OOS) `BLOCKED`'dir; D-141 yetki yoksa yerine veri açmaz.

Hiçbir D-141 makbuzu canlı kârlılık, gerçekleşmiş nakit akışı veya terfi uygunluğu kanıtı değildir.
