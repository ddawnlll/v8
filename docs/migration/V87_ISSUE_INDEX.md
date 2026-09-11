# V8.7 GitHub iş paketleri

Durum: 2026-09-11 tarihinde gh CLI ile yayınlandı; uygulama başlamadı.

Kaynaklar: [analiz](../research/v8-swing-benchmark-analizi.md),
[şartname](../contracts/V87_SWING_BENCHMARK_SPEC.md),
[uygulama planı](V87_SWING_BENCHMARK_IMPLEMENTATION_PLAN.md).

Ana takip: [EPIC #420](https://github.com/ddawnlll/v8/issues/420).

| Paket | Issue | Konu | Önkoşul |
|---|---|---|---|
| SB01 | [#410](https://github.com/ddawnlll/v8/issues/410) | Dört yıllık veri, burn geçmişi ve aktif Rust yürütme envanteri | Yok |
| SB02 | [#411](https://github.com/ddawnlll/v8/issues/411) | Trade yaşam döngüsü ve tek birimli bağımsız nakit uzlaşması | [SB01](https://github.com/ddawnlll/v8/issues/410) |
| SB03 | [#412](https://github.com/ddawnlll/v8/issues/412) | 24/12/12 causal walk-forward, warmup ve açık swing pozisyonları | [SB01](https://github.com/ddawnlll/v8/issues/410) |
| SB04 | [#413](https://github.com/ddawnlll/v8/issues/413) | Gerçek verili Rust benchmark runner, sürümlü ledger ve güvenli resume | [SB02](https://github.com/ddawnlll/v8/issues/411), [SB03](https://github.com/ddawnlll/v8/issues/412) |
| SB05 | [#414](https://github.com/ddawnlll/v8/issues/414) | Sade swing baseline, karşılaştırılabilir risk ve gerçek maliyet raporu | [SB04](https://github.com/ddawnlll/v8/issues/413) |
| SB06 | [#415](https://github.com/ddawnlll/v8/issues/415) | Gerçek trial ailesi, bağımlılık duyarlı istatistik ve örneklem yeterliliği | [SB05](https://github.com/ddawnlll/v8/issues/414) |
| SB07 | [#416](https://github.com/ddawnlll/v8/issues/416) | Kanıta bağlı yeni scorer ve canonical gate eşlemesi | [SB06](https://github.com/ddawnlll/v8/issues/415) |
| SB08 | [#417](https://github.com/ddawnlll/v8/issues/417) | Dondurulmuş swing walk-forward, sınırlı ablation ve final değerlendirme | [SB07](https://github.com/ddawnlll/v8/issues/416) |
| SB09 | [#418](https://github.com/ddawnlll/v8/issues/418) | Gerçek prospektif shadow, restart ve sonuç olgunluğu kanıtı | [SB04](https://github.com/ddawnlll/v8/issues/413), [SB07](https://github.com/ddawnlll/v8/issues/416) |
| SB10 | [#419](https://github.com/ddawnlll/v8/issues/419) | Teknik V8.7 release dosyası, EN/TR kayıtları ve ekonomik sonuç ayrımı | [SB08](https://github.com/ddawnlll/v8/issues/417), [SB09](https://github.com/ddawnlll/v8/issues/418) |

## Tek goal prompt

```text
GitHub https://github.com/ddawnlll/v8/issues/420 içindeki V8.7 programını tamamla. Ana issue ve
SB01–SB10 gövdelerindeki goal prompt, R# kabul ölçütleri, bağımlılıklar ve
kanıt koşullarını uygula. Tamamlanmış işi revision-bound kanıtını doğrulayarak
geç; sonraki işi bağımlılıkları sağlanınca başlat. Tüm yeni uygulama ve testler
v8-core içinde Rust olsun. Ekonomik yeterliliği teknik sürüm kabulünden ayır;
eksik veri/otoriteyi PASS veya skorla doldurma. Her iş sonunda Completed/
Remaining R IDs, exact checks, artifact hash ve lifecycle kayıtlarını güncelle.
Özel/canlı emir, otomatik merge, main'e push veya release/tag yapma.
```

Tek paket için ilgili issue içindeki “Goal prompt” bölümü doğrudan kullanılabilir.
Tüm issue'lar şablona uygun `state:triage` ile açıldı; bu durum promptların
eksik olduğu anlamına gelmez. `state:ready` ilgili bağımlılık ve kanıt girişleri
doğrulandıktan sonra body ve label birlikte güncellenerek verilir.

## Kalıcı metin ve yayın bağlamı

Issue gövdelerinin tam açılış metni [docs/issues/v87](../issues/v87/) altında
SB00–SB10 olarak korunur. Bunlar açılış snapshot'ıdır; canlı issue lifecycle
ve evidence güncellemelerinin kaynağı GitHub'dır. Her issue altı R# içerir:
66 gereksinim (60 paket gereksinimi + 6 program kabul/takip gereksinimi).

Belgeler yalnızca doküman içeren `codex/v87-swing-benchmark-plans` dalında
yayınlandı. Main'e push veya merge yapılmadı. Issue'ların Base SHA'sı
`d5826c2198b18cb73b38d882d1b8119ecd8a49c0`;
bu yayınlanmış doküman bağlamıdır, implementation tamamlanma SHA'sı değildir.
Farklı yerel snapshot'taki araştırma bulguları Rust'ta ayrıca doğrulanır.

Mevcut #389, #394–#398, #406–#408 ve ilgili ekonomik işler uygun paketlerde
referanslandı; hiçbir eski issue otomatik kapatılmadı veya supersede edilmedi.
