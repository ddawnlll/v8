# NX07 (#428) — Trial ailesini bağımlılık duyarlı istatistiklere bağla

Durum: **R1–R6 teknik kabul.** Gerçek tape üzerinde gerçek bir aile ölçüldü.
Sonuç **olumsuz**: DSR güveni 0.1183 (authority eşiği 0.95), Bonferroni düzeltilmiş p = 1.0.
Bu bir başarısızlık değil, bu işin geçerli teslimidir — **hiçbir estimator p geçsin diye
seçilmedi**. `NO_ECONOMIC_CLAIM`.

## 0. Sözleşme (yeni: `evaluation/statistics_plan.py`)

`StatisticsPlan` = family + block_size + reps + seed + multiplicity_trials +
effective_independent_trials + independence_basis + CSCV partitions/metric/max_splits +
WRC block divisor/reps/seed + **authority_conditions** + **diagnostics** + pinned_ns.

- **Kimlik** yalnızca istatistiksel içeriği kapsar (`pinned_ns` hariç): aynı içerik
  yeniden pinlenebilir, farklı içerik **pinlenemez** → sonucu gördükten sonra blok
  uzunluğu/seed/multiplicity değiştirmek imkânsız.
- **Authority vs diagnostic veri olarak yazılır**: G5'in gerçekten dallandığı koşullar
  (`dsr_conf>=0.95`, `bonferroni_p<=0.05`) authority; WRC p, PBO, sufficiency ve regime
  attribution diagnostic. Kesişim boş olmak zorunda (tek istatistik ikisi olamaz).
- `sample_sufficiency(n, block_size)` = **örtüşmeyen blok** sayısı; ham satır sayısı
  bağımsız örneklem diye sunulmaz.

## 1. R → exact check → artifact matrisi

| R | Değişiklik | Exact check | Ölçülen sonuç |
|---|---|---|---|
| R1 | `compare_family` çıktısına `history_completeness: UNKNOWN_UNDISCLOSED_TRIALS_POSSIBLE` + gerekçesi; `family_losses` kayıtlı aile tamlığını zaten zorluyor | `pytest -q v8-next/tests/test_family.py` | 12 passed — kayıtsız/eksik deneme aile karşılaştırmasına giremez; **bilinmeyen geçmiş "bilinmiyor" olarak bildirilir**, tamlık iddia edilmez |
| R2 | `sample_sufficiency`: bağımsız blok sayısı; G5'te `independent_samples < 2` → BLOCKED, `n<20` (yetkisiz) → UNKNOWN | `test_sufficiency_counts_blocks_not_rows`, `test_underpowered_own_track_is_unknown_not_substituted` | 100 gözlem/5 blok → 20 bağımsız (satır sayısı değil); yetkisiz kısa seri **p/confidence üretmiyor** |
| R3 | WRC/SPA/DSR/PBO gerçek aile girdilerine bağlandı; receipt'te `authority_conditions`/`diagnostics`; **sessiz regime fallback kaldırıldı** (yetki + gerekçe zorunlu) | `test_authorized_fallback_requires_a_stated_basis`, `test_g5_selection_control_dsr_and_wrc` | Gerekçesiz fallback → `ValueError`; `num_trials=4` gibi gevşek parametre artık yok (`TypeError`) |
| R4 | Plan sonuçtan **önce** pinlenir ve dosyaya yazılır; `require_pinned_before_results` guard'ı | `test_plan_identity_covers_the_statistical_content_only`, `test_plan_pinned_after_the_results_is_refused`, `test_pin_is_immutable_per_family` | Aynı aile için farklı plan → `ValueError`; sonuçtan sonra pin → `ValueError`; block/seed/multiplicity/partitions plan kaynaklı (hardcode yok) |
| R5 | Sentetik known-effect/shuffled kontroller yalnızca mekanik testte; ledger/aile receipt'ine sızmadığı test edildi | `test_synthetic_controls_stay_out_of_economic_receipts` | Kontroller `scope=SYNTHETIC_CONTROL`; üretilen receipt serileştirmesinde `SYNTHETIC_CONTROL`/`known_effect` **yok**; yetersiz/sabit seri → verdict ≠ COMPUTED **+ gerekçe** (sıfır p yok) |
| R6 | Gerçek fold ailesi: 5 değişken (cash baseline + trend + squeeze baseline/m1/m2), gerçek bar, gerçek taker ücreti; CI/excess/yöntem-provenance-yeterlilik tablosu | `python v8-next/tools/nx07_family_statistics.py` | Plan `bf0941c7…` (ölçümden önce), receipt `79acbaa9…`; DSR/WRC COMPUTED, PBO UNDERPOWERED (gerekçeli) |

## 2. Ölçülen sonuç (gerçek tape, 2025-01-01→2025-02-01, 744 bar, 31 interval)

| Yöntem | Sınıf | Verdict | Girdi/provenance |
|---|---|---|---|
| Deflated Sharpe | **AUTHORITY_CONDITION** | COMPUTED | multiplicity 4, effective independent trials 4.0, gerekçe: dört ön-kayıtlı yürütme varyantı, bağımsızlık kanıtlanmadı |
| White Reality Check | DIAGNOSTIC | COMPUTED | stationary bootstrap, block 5, reps 999, seed 7 |
| PBO (CSCV) | DIAGNOSTIC | **UNDERPOWERED** | 31 interval 4 partition'a bölünemiyor — gerekçe receipt'te |

Ölçülen sayılar: **DSR güveni 0.11834** · Bonferroni düzeltilmiş p = **1.0** (dört varyantın
hepsi reddedilmedi) · `sample_sufficiency = SUFFICIENT` (6 bağımsız blok) · baseline (cash)
fazlası: causal_trend +0.000177, swing_squeeze_m2 −0.000170, swing_squeeze_baseline
−0.000304, swing_squeeze_m1 −0.000633.

Okuma: bu aile selection-control authority koşulunu **geçmiyor** ve geçmiyor olduğu
gibi raporlanıyor; eşik, blok uzunluğu veya varyant seti sonucu gördükten sonra
değiştirilmedi (değiştirilemez — plan pinli).

## 3. Sınırlar / pending

- Sonuçlar karar-düzlemi replay eğrileri (NX06 ile aynı sözleşme): **engine fill'i değil**,
  venue settlement değil; funding **MISSING** (sıfır değil).
- PBO bu pencerede yapısal olarak UNDERPOWERED (interval sayısı); daha uzun pencere NX09'un
  işi — bu bir veri/aile kısıtı olarak kayıtlı, "hesaplandı" diye yazılmadı.
- `history_completeness` **UNKNOWN**: yerel registry bu aileyi kanıtlar, registry dışında
  koşulmuş olabilecek daha eski denemeleri kanıtlayamaz.
- Ekonomik iddia yok: NO_ECONOMIC_CLAIM; bu iş istatistiksel yöntem bağlamayı teslim eder.
