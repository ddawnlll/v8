# #436 — Portfolio equity graft ve closed-loop residual reconciliation makbuzu

Durum: **düzeltildi ve ölçüldü.** `NO_ECONOMIC_CLAIM`. Bu dosyadaki her sayı bu
oturumda çalıştırılan gerçek tape koşusundan gelir; hiçbiri beyandan alınmamıştır.

| Alan | Değer |
|---|---|
| Issue | #436 (https://github.com/ddawnlll/v8/issues/436) |
| Yetki | Owner directive 2026-09-11 — scout-imzalı v8-next defect fix |
| Boundary | #409 |
| Tape | `research/tape/btcusdt-1h-12m/tape.jsonl` · sha256 `4812c6dc9e8b206246ca088eed2fe5460495c65314dcbbafa09cc1ba0d0a0f3f` |
| Pencere | 500 bar · offset 0 · 2025-07-01T00:00Z → 2025-07-21T20:00Z · sermaye 10 000 USDT · taker fee 5 bps |
| Makbuz | `docs/evidence/v87/NX02/loop_reconciliation_436.json` · sha256 `54abd31c9d75ae32586fba8c8672cc4641a2bfd2b70f03d2b5f94a6559056b77` |
| Üretici | `docs/evidence/v87/NX02/regenerate_loop_reconciliation_receipt.py` · sha256 `c5baf831c27ae0c276c22900a2e688f46e692f30a886de83b927571b26af4e50` |
| Bound receipt (önce) | `docs/evidence/v87/NX02/bound_receipt_before.json` · sha256 `a489c278b50c9a0afa06b8c4e77c29338d3f80ce03d024a0a82add0aeba0ec95` |
| Bound receipt (sonra) | `docs/evidence/v87/NX02/bound_receipt_after.json` · sha256 `093040dd397d6d14a8b2f3f0583ff72b4200f8c722558c1c45418436fd28d281` |

## 1. Ölçülen kusur (öncesi, `b7804bdc`)

1. **Seviye graft edilmişti, ölçülmemişti.** `drift = (balance_total - equity[-1]) / (n-1)`
   ve `adj[-1] += drift`: `adj[-1] == balance_total` **her residual için by
   construction** doğruydu. Bu pencere ölçümü: ham mark yolu `10 013.9129`,
   yayınlanan eğri `10 008.4736` — yani **5.4393 USDT**, 499 bara **-0.010900
   USDT/bar** olarak eşit dağıtılıyordu. `metrics_for_curve` bu eğriyi aldığı için
   `net_return`, `sharpe_*`, `max_drawdown`, `tail_mean_5pct` ve P/P+E
   `incremental_net` hepsi bu düzleştirilmiş seviyeden okunuyordu.
2. **Tek guard değiştirilmişti.** Gerçek tape her zaman funding satırı taşıdığı
   için `loop_err`, funding farkıyla değiştiriliyordu; motor↔seri residual'ı
   (`base_loop`) hiç yayınlanmıyordu. Ölçüm: engine residual `-6.54e-13`,
   yayınlanan `closed_loop_error` ise funding farkı `9.55e-09`; artifact'ın
   `cost_reconciliation` alan kümesi (9 alan) residual adını **içermiyordu** —
   buna rağmen `cost_basis: VERIFIED_ENGINE_FUNDING` yayınlanıyordu.
3. **Residual'i "açıklayan" alan totolojiydi.** `strategy_series_from_engine`'de
   `closed_loop_residual_explained_by_open_positions` birebir
   `open_position_realized_pnl`'e eşitti (gerçek NX02 penceresinde ikisi de
   `-0.5494735`), yani kendi girdisiyle çelişemezdi.

Üçü de sentetik enjeksiyonla kırmızıya çevrildi (bkz. §3a): dengede +1 USDT
uyumsuzluk HEAD'de `VERIFIED_ENGINE_FUNDING` üretiyordu.

## 2. Değişen sözleşme

`v8-next/src/v8_next/evaluation/economic_benchmark.py` (yalnızca bu dosya):

* **Residual artık ölçülüyor ve yayınlanıyor.** Her iki yolda
  `closed_loop_residual_usdt` / `engine_series_residual_usdt` (işaretli),
  `engine_series_residual_measured`, `engine_series_tolerance_usdt`,
  `closed_loop_terms` (terimler tek tek).
* **`loop_err` konjunksiyon.** `closed_loop_error = max(engine_series_residual_abs,
  funding_residual_abs)`; her ikisi de `loop_err_components_usdt` altında ayrı
  ayrı yayınlanır ve `loop_err_is_conjunction: true` beyan edilir. Funding
  uyuşması tek başına doğrulama yerine geçmez.
* **Fail-closed cost-basis sözlüğü.** `MISMATCH` (ölçülen residual tolerans
  dışı) ve `UNKNOWN` (balance ölçülemedi) durumları eklendi; tolerans dışı
  residual **hiçbir koşulda** `VERIFIED_*` yayınlamaz. Toleranslar
  `STRATEGY_LOOP_ATOL = 0.01`, `PORTFOLIO_LOOP_ATOL = 0.02` (NX02 ölçümünden
  korunan sınırlar). Sözlük `COST_BASIS_STATES` ile beyan edildi.
* **Graft açıkça adlandırıldı.** Dönen obje artık `equity_mtm` (graft
  edilmemiş mark yolu), `reconciliation_adjustment_per_bar` ve
  `equity_construction` beyanını taşıyor; `raw_equity` eski alias olarak aynı
  listeye bakıyor. `EQUITY_CONSTRUCTION` metni her iki yolda da yayınlanır.
* **Totoloji kaldırıldı.** `closed_loop_residual_explained_by_open_positions`
  yok; yerine kendi ölçümü olan residual var, `open_position_realized_pnl` ise
  yalnızca atfedilen terim olarak duruyor.

## 3. Kabul koşulları

Ölçüm komutu: `uv run --project v8-next --extra dev pytest -q
v8-next/tests/test_equity_loop_residual_436.py`
Sonuç (fix): **8 passed**. HEAD'de (fix stash'lenmiş): **6 failed, 1 passed**
(7. test o an henüz yazılmamıştı).

**(a) Enjekte edilmiş balance uyumsuzluğu fail-closed + residual raporlu.**
`test_mechanics_injected_balance_discrepancy_fails_closed_and_reports_residual`:
sentetik motor sonucuna `balance_total = 10000.9` verilir (kapalı defter 9999.9),
yani açıklanamayan **+1.0 USDT**. HEAD çıktısı:

```
assert not ser["cost_basis"].startswith("VERIFIED_")
E   AssertionError: VERIFIED_ENGINE_FUNDING
```

Fix çıktısı: `cost_basis == "MISMATCH"`, `engine_series_residual_usdt ≈ +1.0`,
`engine_series_ok False`, `loop_ok False` — ve funding tarafı hâlâ
`funding_ok True` olduğu için fail eden bileşenin residual olduğu kanıtlı.
Kontrol testi aynı fixture'ın uyumsuzluk olmadan
`VERIFIED_ENGINE_FUNDING` verdiğini gösterir; ayrıca `balance_total`
okunamazsa `UNKNOWN` (HEAD'de yine `VERIFIED_ENGINE_FUNDING` idi).

**(b) Residual kendi girdisi değil.** `test_mechanics_unexplained_residual_is_not_the_open_position_term`:
`sum_realized_pnl = 0`, `open_position_realized_pnl = -0.5494735` (NX02'nin
yayınladığı değer), `balance_delta = 0` → residual `+0.5494735`.
HEAD'de alan mevcut ve birebir `-0.5494735`; fix'te alan yok, residual kendi
ölçümü ve `!= open_position_realized_pnl`.

**(c) Yeniden üretilen makbuz.** Makbuz, gerçek tape penceresinde AYNI üretici
komutunun iki kod revizyonunda iki kez koşulmasıyla üretilir ve iki ölçüm de
kaydedilir (beyan edilmez):

| Ölçüm (gerçek tape, 500 bar) | Önce | Sonra |
|---|---|---|
| Yayınlanan `cost_basis` | `VERIFIED_ENGINE_FUNDING` | `VERIFIED_ENGINE_FUNDING` |
| `cost_reconciliation` alan sayısı | 9 | 27 |
| Residual yayınlanıyor mu | **hayır** | **evet** (`engine_series_residual_usdt`) |
| Engine closed-loop residual (üreticinin bağımsız yeniden hesabı) | `-6.54e-13` | `-6.54e-13` |
| Funding residual | `+9.55e-09` | `+9.55e-09` |
| Yayınlanan `closed_loop_error` | `9.55e-09` (yalnız funding) | `9.55e-09` (**konjunksiyon**) |
| Graft beyanı | yok | `eq_construction` + `-0.010900/bar` |
| Ölçülen graft büyüklüğü | `-5.4393 USDT` | `-5.4393 USDT` |

Aynı pencerede her iki fazda da kanonik `v8_next.app.portfolio` bound receipt'i
yeniden üretildi (fold profili, `FOLD_436`, pencere durumu `COMPLETED`,
receipt chain `True`); makbuz bunlara digest'leriyle bağlanır ve makbuz testi
saklanan kopyaların sha256'sını diskte doğrular.

Fail-closed yayılımı makine ile doğrulandı:
`test_mechanics_unverifiable_cost_basis_fails_closed_the_published_verdict` —
`cost_basis_ok=False` (yani `MISMATCH`) `build_verdicts`'te
`execution = EXECUTION_UNPROVEN` üretir; doğrulanmış tabanda `SIM_ONLY` kalır.

## 4. Sınırlar / kapsam dışı

* **Bound `EconomicReceipt` şeması bu kartta değiştirilmedi.** `app/portfolio.py`
  başka bir kartın kilidinde (#442); receipt'in `cost_reconciliation` bloğunu
  taşıması o dosyayı gerektirir. Bound receipt'in taşıdığı fail-closed hücre
  `metrics.portfolio_P.cost_basis` ve ondan türeyen `verdicts.execution`'dır;
  makbuz ölçülen iki bound receipt'i yanına koyar
  (`before.bound_receipt` / `after.bound_receipt`).
* Karar: graft **kaldırılmadı**, issue'nun izin verdiği ikinci yol seçildi —
  obje graft'ı açıkça adlandırıyor (`equity_mtm` + beyan edilmiş per-bar
  adjustment). Graft'ı kaldırmak `metrics_for_curve` girdisini değiştirir ve
  yayınlanan tüm istatistikleri yeniden tanımlar; o karar bu kartın kapsamı ve
  dosya kilidi dışında.
* Bu kartta `src/v8/`, `tests/`, `v8-core/` ve `artifacts/` altına dokunulmadı.
  Mevcut `artifacts/nx05-profiles/portfolio-fold/economic_receipt_da748498.json`
  ve `docs/evidence/v87/NX02/reconcile_table.json` salt-okunur kanıt olarak
  bırakıldı; üzerine yazılmadı.

## 5. Yeniden üretim

```sh
# önce/sonra ölçümü (kodu ilgili revizyona alıp iki kez):
uv run --project v8-next --extra dev \
  python docs/evidence/v87/NX02/regenerate_loop_reconciliation_receipt.py \
  --phase after --tape /Users/hootie/src/v8/research/tape/btcusdt-1h-12m \
  --bars 500 --bound-receipt <run>/economic_receipt_*.json \
  --copy-bound-receipt-to docs/evidence/v87/NX02 --out /tmp/loop_after.json
uv run --project v8-next --extra dev \
  python docs/evidence/v87/NX02/regenerate_loop_reconciliation_receipt.py \
  --compose /tmp/loop_before.json /tmp/loop_after.json \
  --out docs/evidence/v87/NX02/loop_reconciliation_436.json
```

Bound receipt'lerin kendisi:

```sh
uv run --project v8-next --extra dev python -m v8_next.app.portfolio \
  --profile fold --start-utc 2025-07-01T00:00:00Z --end-utc 2025-07-21T20:00:00Z \
  --fold-id FOLD_436 --tape-path /Users/hootie/src/v8/research/tape/btcusdt-1h-12m \
  --output-dir <out> --primary cash
```

Tape yoksa üretici koşmaz (`FAIL: real tape absent`); sentetik fallback yoktur.

## 6. Baseline notu

`pytest -q v8-next/tests/test_economic_benchmark.py v8-next/tests/test_portfolio_benchmark.py
v8-next/tests/test_runner_accounting_nx02.py v8-next/tests/test_equity_loop_residual_436.py`
→ **60 passed, 2 skipped, 1 failed**. Fail eden test
`test_mechanics_estimator_unavailable_is_not_a_power_verdict`, **bu değişiklikten
önce de `b7804bdc`'de aynı şekilde fail ediyor** (bu ortamda `scipy`/`arch`
provision edilmediği için `verdicts` iki receipt arasında farklılaşmıyor);
#436 ile ilgisi yoktur. Değişen dosyada `ruff check` ve `mypy` yeni hata
üretmedi (mypy: 5 önceden var olan hata, NX01'de kayıtlı).
