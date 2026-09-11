# NX03 (#424) — Historical walk-forward planını ForwardPlan güvenliğinden ayır

Durum: **R1–R6 teknik olarak teslim edildi.** `NO_ECONOMIC_CLAIM`.

## 0. Ayrım (neden yeni tip)

`ForwardPlan` / `freeze_forward_plan` / `bind_forward_data` ileriye dönük araçlardır:
gerçek duvar saatini okur, pencere başlamadan donmayı zorlar, tek bir veri
binding'ini kabul eder. Bunları geriye dönük koşular için gevşetmek, bir planın
kendi penceresi **gözlendikten sonra** kaydedilmesine izin verirdi — geleceğe sızıntı.

Bu iş tarihsel planı **ayrı tipli ve ayrı store şemasıyla** ekledi
(`v87-historical-plan-v1`, `historical_plans` tablosu). Forward tablolarına hiç
dokunulmadı: read-back kanıtında `forward_plans = 0`, `forward_bindings = 0`.
Forward kontrolleri (gerçek saat, freeze-before-start, immutable binding) aynen durur
ve mevcut testleri yeşildir.

## 1. Ölçülen pencere ve gereksinimler (gerçek tape)

| Alan | Değer |
|---|---|
| dataset_id | `sha256:a20414c6a1366fbca763d8835a04f368676816d511238cc7ed86647df77c5b86` |
| calendar_digest | `sha256:0ecf3d035107cf985f7e58df5d8e9678133928bba718c33f6f7fc05464062138` |
| Pencere | DEVELOPMENT 2022-07-01→2024-06-30 · FOLD_1..4 (3 aylık, 2024-07-01→2025-06-30) · FINAL **kapalı** |
| `warmup_bars` | **49** = max(policy gerekli bar; 49 range-breakout / 25 trend / 21 mean-reversion, 24 önceki UTC seans) |
| `purge_bars` | **336** = max(policy outcome horizon 336/24/12, protection TTL 336 squeeze) |
| `aggregation` | `INDEPENDENT_FOLD_RESET` (manifest alanı; `CONTINUOUS_PORTFOLIO` ayrı ve digest'i farklı) |
| `train_window` | `EXPANDING_FROM_DATASET_START` (açıkça yazılı: her fold kendinden önceki tüm geçmişle eğitilir) |
| final | `final_eligible=false` — `NO_PROTECTED_FINAL: … TAIL_BURNED …; measured tail tape_role=BURNED_DIAGNOSTIC` |
| plan_digest | `sha256:9cd69f989a21bb107c8e65e1bcd9f102a54680be817af2c88d3e29eadba60921` |

Warmup/purge, çalışma zamanının **kendi sabitlerinden** türetilir
(`POLICY_REQUIRED_BARS`, `POLICY_HORIZON_BARS`, `PROTECTION_TTL_BARS`,
`experts.levels.previous_session_bars`'ın 24 barlık şartı). Keyfi sabit yok; grammar ve
protection modülleri bu sabitleri dışa verecek şekilde minimal refaktör edildi
(davranış aynı: `test_grammar.py`, `test_squeeze_protection.py`,
`test_campaign_protection.py` yeşil).

## 2. R → exact check → artifact matrisi

| R | Değişiklik | Exact check | Ölçülen sonuç |
|---|---|---|---|
| R1 | `evaluation/historical_plan.py`: NX01 takviminden 24/12/12 plan; tarih/rol NX01 kanıtına bağlı (`dataset_id`, `calendar_digest`, `tape_role`) | `pytest -q v8-next/tests/test_historical_plan_nx03.py` | 13 passed — fold pencereleri 2024-07-01…2025-06-30, final kapalı |
| R2 | Ayrı tipli tarihsel plan + dokümante şema; `historical_plans` tablosu; ForwardPlan kontrolleri korunur | aynı pytest (`test_historical_path_never_touches_the_forward_tables`, `test_freezing_is_immutable_and_readback_rederives_the_digest`) | PASS — forward tablolar boş; ikinci farklı kayıt reddedilir |
| R3 | `train_end < scored_start`; warmup penceresi geçmişte ve scored dışında; explicit UTC sınırlar; minimum history gerçek grammar/protection ihtiyacından | aynı pytest (`test_every_fold_separates_training_warmup_and_scoring`) | PASS — nanosecond sınırlar; purge boşluğu tam `purge_bars × bar_ns` |
| R4 | Purge/embargo gerçek outcome horizon + protection TTL'den pinlendi (336 bar); eğitim etiketi scored pencereye sızamaz | `test_verify_rejects_a_train_window_reaching_into_scoring`, `test_history_requirements_come_from_the_real_contracts` | PASS — sızan pencere `TRAIN_OVERLAPS_SCORED` ile reddedilir |
| R5 | Tüm politikalar aynı takvim; `aggregation` ve `train_window` manifestte açık; aynı fold getirisi iki kez sayılmaz | `test_aggregation_and_train_window_are_explicit` | PASS — farklı aggregation farklı digest |
| R6 | Boundary/warmup/burn/overlap regresyonları + plan read-back | `python v8-next/tools/nx03_plan.py` | PASS — read-back birebir, digest aynı, forward satırları 0 |

Artefaktlar (`docs/evidence/v87/NX03/`):
`historical_plan.json` sha256 `994f4950bb6db74beb2e692424257d73288fb8cb31165a73f1410978316c8372`
`plan_readback.json` sha256 `0b74e12e9604d5a355691706b6aa5791d539610ec9d85021235b41e1ced363a3`
`plan_store.sqlite` (read-back kanıtı).

## 3. Pending / sınırlar

- **Protected historical final yok** (son 12 ay `TAIL_BURNED`) → final penceresi
  açılmadı; tarih veya rol değiştirilerek final yaratılmadı. NX09 diagnostic yolu.
- Fold **koşumu** (fold sonunda pozisyonu equity ile taşıma, gerçek execution)
  NX09 kapsamındadır; bu iş planı ve sözleşmeyi üretir, koşuyu değil.
- Bu iş bir skor veya ekonomik sonuç iddiası üretmez.
