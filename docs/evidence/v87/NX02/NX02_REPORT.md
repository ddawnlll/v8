# NX02 (#423) — Runner muhasebesini kronolojik eşleştirme ve native equity ile uzlaştırma

Durum: **R1–R6 teknik olarak teslim edildi.** `NO_ECONOMIC_CLAIM`. Bu oturumda ölçülen
gerçek komut çıktılarına dayanır; hiçbir sayı beyandan alınmamıştır.

## 0. Kimlik

| Alan | Değer |
|---|---|
| Issue base SHA | `0990615962431ca8434824b3be33ac076a69f3bf` |
| NX02 öncesi HEAD | `b9521045` (NX01 R5 + NX00/NX01 raporları) |
| Runtime | Python 3.12.12 · nautilus-trader 2.0.0rc4 |
| `uv.lock` / `v8-next/uv.lock` | `316bd844…` / `f230c2bd…` (değişmedi) |

## 1. R → exact check → artifact matrisi

| R | Değişiklik | Exact check | Ölçülen sonuç |
|---|---|---|---|
| R1 | `v8-next/src/v8_next/evaluation/runner.py` artık `economic_benchmark.pair_positions` tabanlı `campaign_accounting` kullanır (ilk-id eşleşmesi kaldırıldı); `v8-next/src/v8_next/evaluation/economic_benchmark.py` ortak sözleşmeyi barındırır | `pytest -q v8-next/tests/test_runner_accounting_nx02.py` | PASS — tekrar kullanılan `position_id` altında eşleşme kronolojik: `(5.0, -3.0)`; eski davranış `(5.0, 5.0)` verirdi |
| R2 | `campaign_lifecycle_checks`: partial/scale-in/reversal/orphan durumları **adlandırılır**; bir close yalnızca bir campaign kapatır | aynı pytest (`test_scale_in_and_orphan_cases_are_named`) | PASS — `SCALE_IN_OR_PARTIAL_REDUCTION` / orphan close adıyla raporlanır, sessizce yutulmaz |
| R3 | `parse_money` + `ACCOUNTING_UNITS`: PnL USDT, return boyutsuz, iki seri asla karışmaz; parse hatası `0.0` olmaz; `trade_count` = tamamlanmış campaign | aynı pytest (`test_unparsable_pnl_is_absence_never_zero`, `test_units_are_declared_and_kept_apart`) | PASS — parse hatası `unparsable` olarak adlandırılır, 0.0 seride yok |
| R4 | `reconcile_native_account`: native `balance_total` ↔ `başlangıç + Σ realized_pnl + Σ funding adjustment` (ölçülen motor kimliği); rapor yolu ↔ native kapalı pozisyon PnL'i | `test_reconcile_matches_the_measured_native_identity`, `test_reconcile_fails_closed_on_count_and_parse_faults`, gerçek tape testi | PASS — gerçek koşuda `MATCHED`, delta `0.00000000` (tolerans `1e-8`) |
| R5 | Açık campaign kesim anındaki **bar sonu** fiyatıyla işaretlenir; yapay kapanış/gelecek fiyat yok | `test_open_campaign_is_marked_at_the_cutoff_bar_end` | PASS — kesim=2. bar → 110; kesim sonrası bar (130) değeri etkilemez |
| R6 | `v8-next/tools/nx02_reconcile.py` tek gerçek motorda iki rapor yolunu + native hesabı karşılaştırır | `python v8-next/tools/nx02_reconcile.py` | PASS — `runner_status=MATCHED` |

Artefakt: `docs/evidence/v87/NX02/reconcile_table.json`
sha256 `39d610243ad32baa13d30fa96b4bbdfdf7f9353afe0e2a0194b722dfd97b1845`

## 2. Ölçülen pencere ve sayılar (gerçek tape)

Pencere: `research/tape/btcusdt-1h-12m/tape.jsonl`, 500 bar, quorum=1, tolerance=28,
başlangıç sermayesi 10.000 USDT (açıkça pinlendi: `ENGINE_INITIAL_BALANCE`).

| Ölçüm | Değer |
|---|---|
| Native `balance_total` | `9999.45052650 USDT` |
| Bağımsız replay (`10000 + Σrealized + Σadjustments`) | `9999.45052650` |
| Delta | `0.00000000` (tolerans `0.00000001`) |
| Tamamlanmış campaign | 0 |
| Açık pozisyon | 1 (LONG 0.010 BTC, giriş 109 894.7) |
| Açık risk (kesim barı MTM) | `+68.30 USDT` |
| Orphan close | 0 |
| Unsupported lifecycle | yok (bu pencerede) |

## 3. Bu oturumda ölçülen iki gerçek kusur (düzeltildi)

1. **Rapor yolu hatalı birim karıştırıyordu.** `runner.py@09906159` kapalı pozisyonun
   *mutlak USDT* `realized_pnl`'ini ve açık pozisyonun *boyutsuz* MTM oranını aynı
   `pnl_series`'e koyuyordu; ayrıca ilk `position_id` eşleşmesini kullanıyor ve parse
   hatasını `0.0` yapıyordu. Artık tek sözleşme (`campaign_accounting`) kullanılıyor.
2. **Ekonomik yolun kapalı-döngü hatası yanlış atfediliyordu.** Açık pozisyonun
   `realized_pnl`'i (ödenmiş komisyon) hesaba katılmadığı için gerçek koşuda
   `closed_loop_error = 0.54947350` **açıklanamayan artık** gibi görünüyordu. Atıf
   eklendikten sonra aynı koşuda `closed_loop_error = 7.06e-13` (float yuvarlaması) ve
   `open_position_realized_pnl = -0.5494735` olarak açıkça raporlanıyor.
   Ölçüm: 0.54947350 → 7.056577544517495e-13.
3. **İki yol trade sayısında anlaşmıyordu.** Ekonomik yol `n_trades` alanı *open
   event* sayıyordu (1), runner yolu tamamlanmış campaign sayıyordu (0). Alan artık
   `n_completed_campaigns` / `n_open_positions` / `n_trades_definition` ile ayrıştırıldı;
   eski alan geriye dönük uyumluluk için korunuyor ve tanımı yazılı.

## 4. Pending / kapsam dışı

| Kalem | Durum |
|---|---|
| Funding maliyeti (bu yol) | `funding: null` — motor bu kapsamda funding event'i ile beslenmiyor; sıfır yazılmadı |
| Ekonomik kabul | Fixture üzerinden PASS yok; ölçüm tek gerçek pencerede yapıldı, getiri iddiası üretilmedi |
| Uzun pencere / fold | NX05/NX09 kapsamı |

## 5. Baseline

- Tam v8-next suite bu değişikliklerden sonra çalıştırıldı (bkz. issue yorumu; sonuç
  raporlanan koşuya aittir).
- `mypy v8-next/src`: yalnızca **5 önceden var olan** hata (NX01'de doğrulandı).
- `ruff check` touched dosyalarda temiz.
