# NX08 (#429) — Scorer/gate tutarlılığı: türetilmiş coverage, default'suz sertifika, kanonik gate haritası

Durum: **R1–R6 teknik kabul.** Skor hedefi yok, PASS zorlanmadı; ölçülemeyen her şey
`MISSING`/`None` olarak kaldı. `NO_ECONOMIC_CLAIM`.

## 0. Sözleşme değişiklikleri (kaldırılan sahte-güven yolları)

1. **Coverage artık türetilir.** `scoring.compute_capability_breakdown(..., coverage_factor=None)`
   → `derive_coverage(domain_measurement_statuses(...))`. Ölçülebilir domainler
   `MEASURED / ABSTAINED`, ölçülemeyenler `INACTIVE`, veri yoksa `MISSING`; payda
   gerçekten ölçülebilir domainler, ayrıca **tüm domainlere göre** ikinci bir oran da
   raporlanır (`all_domain_coverage_factor`) ki ulaşılmamış 6 domain gözden kaçmasın.
   Sabit `0.60` yalnızca emekli sabit olarak (`LEGACY_FIXED_COVERAGE_FACTOR`) karşılaştırma
   tarafında yaşar ve `coverage_source=CALLER_SUPPLIED` diye etiketlenir.
2. **Sertifikada default yok.** `rob_score=50.0` / `economic_score=60.0` kaldırıldı:
   Minerva yoksa robustness `None` + seal `SEAL_DENIED_NO_MINERVA_RUN`; projection yoksa
   economic `None`. Herhangi bir faktör eksikse **readiness `None`** (MISSING) ve
   `missing_measurements` adı geçer; tam olduğunda formül aynen çalışır ve
   `readiness_upper_bound` aynı formülden türetilir.
3. **Tek kanonik gate haritası.** `v8-next/src/v8_next/evaluation/gate_registry.py` G0–G9 için
   label/field/resolver/readiness rolünü tek kaynaktan üretir ve canlı nesnelere karşı
   doğrular (`validate_registry() == []`): 10 gate, `GateVector` alan sırası birebir,
   resolver sembolleri `gate_resolution` içinde gerçekten var.
4. **G3–G7 sahte-başarı yolları kaldırıldı.**
   - **G5**: `DEFAULT_TAPE_PATH` okuyan sessiz regime fallback yok; yetki + gerekçe +
     **aynı-run kaynağı** (`fallback_tape`/`candles`) zorunlu, kaynak metrikte adıyla yazılır.
   - **G6**: 2/3 vs 1/3 gibi **eşit olmayan** pencereler artık karşılaştırılmıyor; iki taraf
     da `min(is, oos)` bara kırpılıyor (`window_equality=EQUAL_BARS`), bitişik ve örtüşmesiz.
   - **G7**: run'ın kendi son 100 tarihsel barından PASS üretilemez. `shadow_stream`
     açıkça bildirilmeden **UNKNOWN** (`PSEUDO_PROSPECTIVE_HISTORICAL_WINDOW_NOT_ACCEPTED`);
     bildirilirse köken adı zorunlu ve provenance `CALLER_DECLARED_NOT_VERIFIED_BY_GATE`.
5. **R5 çift skor.** `dual_scoring(...)` eski (sabit coverage) ve yeni (türetilmiş)
   skoru aynı girdilerle yan yana hesaplar; delta `TRANSFORM_ONLY` olarak etiketlenir
   (ölçümler aynı nesne). Kayıt receipt'te **sidecar** olarak durur ve **digest'e girmez**,
   böylece mevcut ledger girişleri yeniden hashlenmez.

## 1. R → exact check → artifact matrisi

| R | Ne yapıldı | Exact check | Sonuç |
|---|---|---|---|
| R1 | Coverage gerçek eligible/measured domainlerden; inactive/abstain/missing açık | `pytest -q v8-next/tests/test_nx08_gates_scoring.py` | 11 passed — ölçülemeyen domain "başarı" veya "ekonomik sıfır" sayılmıyor; boş koşuda `coverage_factor=None`, `aggregate=None` |
| R2 | Sertifika default'ları kaldırıldı + raw ölçüm→transform→payda→ağırlık→binding dökümü | `test_certificate_has_no_fabricated_robustness_or_economic_defaults`, `test_certificate_readiness_is_derived_from_the_formula_when_measured` | Minerva/projection yokken readiness **None**; varsa formülle birebir ve `upper_bound >= index` |
| R3 | `gate_registry` tek kaynak + canlı nesne doğrulaması | `test_gate_registry_is_consistent_with_the_live_objects`, `test_gate_registry_pins_the_existing_semantics` | `validate_registry() == []`; 10 gate/alan sırası/rol tablosu testle sabitlendi |
| R4 | G5 default tape, G6 eşit-olmayan pencere, G7 pseudo-prospective kaldırıldı | `test_g5_regime_fallback_has_no_default_tape`, `test_g6_compares_equal_length_windows`, `test_g7_cannot_mint_a_prospective_state_from_the_historical_tail` + `test_gate_resolution.py::test_g7_refuses_the_runs_own_historical_tail` | G5 kaynaksız fallback → `ValueError`; G6 `is_bars == oos_bars`; G7 → UNKNOWN, run'ın kuyruğundan PASS imkânsız |
| R5 | Eski/yeni skor aynı receipt'te; sürümler ayrı; transform-only vs ölçüm değişimi | `test_dual_scoring_separates_transform_from_measurement`, `test_receipt_carries_the_scorer_versions_but_not_in_the_digest` | delta `TRANSFORM_ONLY`; sidecar digest'i değiştirmiyor (receipt doğrulaması OK) |
| R6 | Regresyonlar: eksik veri, eksik kalibrasyon, aile uyumsuzluğu, diagnostic-only, tamper, cap türetimi | aynı dosya + `test_gate_resolution.py` + `test_ledger_canon_nx04.py` | 11 + 11 passed; readiness üst sınırı formülden; runtime economic-claim yetkisi korunuyor (`NO_MEASURED_CAPABILITY_SCORE`) |

Artefaktlar (`docs/evidence/v87/NX08/`):
`gate_manifest.json` sha256 `07af779906cdbd6baf56727f774fe306ea0ef15d3aa3eb40ed77ad11e372b923`
`scoring_manifest.json` sha256 `4ef6a85a3d207cc08cd1ed4ae485466e8f62c1e7a3225dffc87dacb8c3818bee`
(+ `NX08_REPORT.md`). Her ikisi de canlı nesnelerden üretildi (elle yazılmadı).

## 2. Ölçülen örnekler (manifest içinden)

| Koşu | Ölçülen/payda | coverage | açıklama |
|---|---|---|---|
| traded (744 bar, 31 işlem) | 4/4 | 1.000 | tüm ölçülebilir domain ölçüldü; `all_domain_coverage_factor=0.400` (10 domainin 4'ü) |
| abstained (744 bar, 0 işlem) | 2/4 | 0.500 | ExecutionFidelity/DefeaterResistance `ABSTAINED` |
| no_data (0 bar) | 0/0 | `None` | ölçüm yok → aggregate `None` (0 değil) |

Sertifika (Minerva/projection yok): readiness `None`, `missing_measurements =
["minerva_robustness_score","economic_score"]`, seal `SEAL_DENIED_NO_MINERVA_RUN`;
receipt `verify() = True`.

## 3. Sınırlar / pending

- G7'nin prospective iddiası artık yalnızca **açıkça bildirilmiş** bir akışla kurulabilir;
  bildirilen akışın gerçekten prospective olduğunu gate doğrulayamaz — provenance alanı
  bunu `CALLER_DECLARED_NOT_VERIFIED_BY_GATE` olarak yazar. Gerçek prospektif kanıt NX10'un
  açık pending kalemidir.
- Gate readiness'i hâlâ eski operational semantiği korur (G0/G1 BLOCKING, G8/G9 CAPITAL);
  bu iş **belgesiz gate anlamı değiştirmedi**, mevcut anlamı tek kaynağa bağladı ve testle sabitledi.
- Ekonomik iddia yok; skor/PASS hedefi için hiçbir eşik, ağırlık veya transform değiştirilmedi.
