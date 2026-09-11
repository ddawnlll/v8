# NX00 (#433) — v8-next swing benchmark paketi: nihai teknik kabul raporu

**Bu bir teknik kabul raporudur; ekonomik sertifika değildir.** `NO_ECONOMIC_CLAIM`.
Release/tag/push-main/merge/live aktivasyon yetkisi **vermez**; private emir, transfer veya
hesap değişikliği yapılmadı, hiçbir credential kullanılmadı.

## 1. Epic R1–R6 → kanıt

| R | Ölçüt | Durum | Kanıt |
|---|---|---|---|
| R1 | Başlangıç SHA + dirty tree kaydı; gerçek v8-next call graph doğrulaması; kullanıcı değişikliklerine dokunulmadı | **Tamam** | `docs/evidence/v87/NX00/baseline_identity.json` `ded4940d…` — base SHA `09906159`, `uv.lock` `316bd844…`, Python 3.12.12 / nautilus-trader 2.0.0rc4; hiçbir reset/stash uygulanmadı |
| R2 | Bağımlılık sırası: NX01/NX02/NX04 → NX03 → NX05/NX06 → NX07 → NX08 → NX09/NX10 → NX11, artefaktlarla doğrulanmış | **Tamam** | Her issue'nun "Dependencies" girdisi kapanan alt işin artefakt hash'i ile karşılandı; matris: `docs/evidence/v87/NX11/acceptance_matrix.json` |
| R3 | Her alt issue R1–R6; yeni runtime/testler v8-next Python içinde; mevcut arayüzler yeniden kullanıldı | **Tamam** | 11/11 alt issue kapandı; yeni modüller yalnızca mevcut owner arayüzü yetmediğinde açıldı (`run_window`, `swing_baseline`, `statistics_plan`, `gate_registry`, `prospective_capture`, `tape_identity`, `historical_plan`) |
| R4 | Her R için commit + exact check + gerçek artefakt bağı; fixture economic receipt sayılmadı | **Tamam** | Alt issue gövdelerinde R→commit→check→artifact matrisi; kabul matrisi testleri **şimdi** yeniden çalıştırdı (10/10 PASS) |
| R5 | Eksik veri/final/prospective durumu açık backlog; bağımsız işler sürdü | **Tamam** | `V87_TECHNICAL_ACCEPTANCE.md` §4 + matris `pending_backlog` (5 kalem) |
| R6 | Teknik kabuller tamamlanınca alt işler ve epic kanıtla kapanır; tahminler ölçüm diye sunulmaz | **Tamam** | Aşağıdaki §2/§3 ayrımı; 11 alt issue kapalı; bu rapor epic kapanış kanıtıdır |

## 2. Ölçülen sonuçlar (tahmin değil)

| Ölçüm | Değer | Kaynak |
|---|---|---|
| Tape kimliği | 226.706.603 B · sha256 `b27891e9…` · 394.545 satır · 960/960 arşiv 3-yollu eşleşme | NX01 |
| Burn tablosu | son 12 ay `TAIL_BURNED`; parity dilimleri 2022-07-01→2022-10-01T13:59Z | NX01 |
| Mark price | **YOK** (yokluk kayıtlı; funding mark ölçülemedi) | NX01 |
| Native ↔ bağımsız replay | delta `0.00000000` (tol `1e-8`); kapalı-döngü hata `0.54947350 → 7.06e-13` | NX02 |
| Legacy ledger | sürüm-çözümlü kanon ile **20/20 OK**; dosya baytları değişmedi (`657b2183…`) | NX04 |
| Swing ailesi (2025-01) | `causal_trend` net **+0.018861**; `plain_swing` net **−0.031357** (30 STOP / 1 TARGET / 31 kampanya) | NX06 |
| Aile istatistiği | DSR güveni **0.11834**; Bonferroni düzeltilmiş p **1.0**; sufficiency SUFFICIENT (6 bağımsız blok); PBO UNDERPOWERED (gerekçeli) | NX07 |
| Kayıtlı dört fold | swing ailesi 8 fold-sembol hücresinin **7'sinde** baseline'a göre negatif; ablasyonlar (m1/m2) iyileştirmedi; final açılmadı (`NO_PROTECTED_FINAL`) | NX09 |
| Bounded public capture | 1009 trade kabul, **1000 duplicate** düşürüldü, restart `chain_verified=true`, G7 `UNKNOWN` | NX10 |
| Test durumu | tam v8-next suite **978 passed**; ruff temiz; mypy **5 önceden var olan** hata | NX11 |

Bu sonuçlar **olumsuz/kararsız** ve olduğu gibi yazıldı. Minimum ekonomik bulguya ulaşmak
veya hedef skora yaklaşmak kapanış koşulu **değildir**.

## 3. Eski tahminler / varsayılan sayılar ile ayrım

| Kalem | Eski durum | Şimdi |
|---|---|---|
| Coverage | sabit **0.60** (payda uydurma) | **türetilmiş**: ölçülen/ölçülebilir domain + tüm domainlere göre ikinci oran; ölçüm yoksa `None` |
| Sertifika robustness | sabit **50.0** | Minerva koşusu yoksa `None` → readiness **MISSING** |
| Sertifika economic | sabit **60.0** | projection yoksa `None` / MISSING |
| Execution fidelity | `sharpe_proxy×0.25+0.10` vekili | ölçülmüş shortfall varsa o; yoksa vekil **kaynağı adıyla** raporlanır |
| Legacy ledger | 12 girişte sahte `DIGEST_TAMPERED` | 20/20 OK (baytlar yeniden hashlenmedi) |
| Rust SB paketi (#410–#420) | yanlış kapsam | **geri çekildi** (issue index'te tarihçe); bu raporda hiçbir Rust tahmini ölçüm olarak anılmadı |

Hiçbir eski tahmin "gerçekleşmiş sonuç" gibi sunulmadı; ölçülen sayılar yalnızca §2'deki
gerçek koşulardan gelir.

## 4. Eksik ekonomik kanıt ve kalan riskler (açık)

| Kalem | Durum | Neden |
|---|---|---|
| Protected final penceresi | `NOT_AVAILABLE` | son 12 ay `TAIL_BURNED` (ölçülmüş) → final açılmadı |
| Prospektif olgunluk | `PENDING` | freeze edilen 24 saatlik public pencere henüz gözlenmedi; holding/markout ölçülmedi |
| Engine fill parity (swing ailesi) | `PENDING` | sonuçlar karar-düzlemi replay; engine fill modeli bağlanmadı |
| Funding / markout | `MISSING` (sıfır **değil**) | arşivde mark price yok |
| Ekonomik edge | `NO_ECONOMIC_CLAIM` | DSR 0.11834 / p = 1.0; authority eşiği geçilmedi |
| Belge-yolu denetimi | **56** gerekçesiz atıf (30 distinct) | D-162 karantina taşıması; V8.7 belgelerinde **0**; denetim gevşetilmedi |
| Monograph derleyicisi | erişilemeyen girdi | `research/manifest/research_papers_manifest.json` checkout'ta yok |
| mypy | 5 hata | önceden var olan, listelenmiş |

**Risk özeti:** teknik iskelet (muhasebe, ledger, pencere/run-key, aile, istatistik, gate,
capture) doğrulanmış durumda; buna karşılık **hiçbir ekonomik iddia** yapılamaz — protected
final yok, prospektif olgunluk yok ve ölçülen aile istatistiği authority eşiğinin çok altında.
Swing ailesinin mevcut ayarlarıyla (sıkı squeeze koruması) maliyet gross'u yiyor; bu aile
böyle teslim edilir, "gelecek vaat eden" diye sunulmaz.

## 5. Yetki sınırı

Bu kabul: release/tag/push-main/merge/live aktivasyon yetkisi **değildir** (D-163: merge
yetkisi yayın yetkisi değildir). EN/TR site yayını ve tag işlemleri sahipte kalır. Karar
kaydı: **D-164** (EN/TR register). Kabul matrisi: `docs/evidence/v87/NX11/acceptance_matrix.json` sha256 `927e8726ed01a978169f3d9c1ed515d94a6b1ffcb1944c831c70e82bf96cf872`.

**Düzeltme (2026-09-11):** NX09 commit kimliği bu raporda ve matriste `42136221`
olarak geçiyordu; gerçek commit `42136231`. Matris düzeltmeden sonra yeniden
üretildi; önceki `a3c04935…` hash'i geçersizdir. Artefakt içerikleri değişmedi.
