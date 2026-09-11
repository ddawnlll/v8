# NX09 (#430) — Kayıtlı dört fold swing araştırması ve koşullu final raporu

Durum: **R1–R6 teknik kabul.** Protected final **yok** (ölçülmüş `TAIL_BURNED`), bu yüzden
final **açılmadı** ve durum metadata olarak yazıldı (`NO_PROTECTED_FINAL` — GateState değeri
değil). Teslim diagnostic research + prospective backlog'dır. `NO_ECONOMIC_CLAIM`.

## 0. Sıra: önce freeze, sonra ölçüm

`docs/evidence/v87/NX09/fold_freeze.json` **hiçbir fold sonucu yokken** yazıldı:
plan (`NX09-REGISTERED-01`) NX01 takvimi üzerinden kuruldu, store'a **immutable** kaydedildi
ve read-back ile digest'i yeniden türetildi. Freeze içinde: fold pencereleri (tarihlerle),
aile kaydı (`family_registry`), **ablasyon listesi**, ortak sözleşme, resampling planı
(block 5 / 999 rep / seed 7) ve kaynak kimlikleri (tape sha256, `code_and_lock_hash`,
calendar digest). Ölçüm ayrı dosyada: `fold_results.json`.

## 1. R → exact check → artifact matrisi

| R | Ne yapıldı | Exact check | Sonuç |
|---|---|---|---|
| R1 | 24/12/12 planı + 4 fold + ablasyonlar sonuçtan önce freeze; kaynak/config hash'leri | `pytest -q v8-next/tests/test_fold_research_nx09.py` | 8 passed — freeze'de `net_return`/`paired_ci`/`excess_vs_baseline` **yok**; `frozen_before_any_fold_result=true` |
| R2 | Her foldda kayıtlı aynı aile; başarısız/sonuçsuz denemeler de kayıtlı; sonuçtan policy seçilmedi | `test_a_flat_or_negative_finding_is_delivered_as_is` | `selected_from_fold_results = NONE`; yapısal kontrol: hiçbir `selected/promoted/winner` bayrağı yok |
| R3 | Fold/sembol/rejim kırılımı: net, excess, blok-bootstrap CI, maliyet, drawdown, holding, sufficiency | `test_every_fold_reports_a_breakdown_not_one_pooled_number` | 4 fold × 2 sembol; her politikada `net_return/max_drawdown/fee_cost/exposure_bars`, baseline'a göre `excess_vs_baseline` + `paired_ci`; 4 rejim dilimi raporlu |
| R4 | Protected final yok → final açılmadı, durum **metadata** olarak yazıldı | `test_the_final_window_was_never_opened`, `test_no_protected_final_is_metadata_not_a_gate_state` | `final_eligible=false`, gerekçe: `NO_PROTECTED_FINAL: … measured tail tape_role=BURNED_DIAGNOSTIC`; `GateState` üyeleri arasında `NO_PROTECTED_FINAL` **yok** |
| R5 | Diagnostic teslim + prospective backlog | `fold_results.json` → `prospective_backlog` | G7/live readiness veya ekonomik edge **sertifikalanmadı**; prospektif olgunluk NX10'da açık |
| R6 | Tüm R gerçek artefaktlarla; sonuç negatifse aynen | `python v8-next/tools/nx09_fold_research.py` | Freeze `e2a31153…`, sonuçlar `e8cb82e9…` |

## 2. Ölçülen sonuç (gerçek bar, gerçek taker ücreti; karar-düzlemi replay)

Fold bazında `net_return` (birim-sermaye üzerinden; portföy getirisi değil):

| Fold | Sembol | cash | causal_trend | swing_baseline | ablation m1 | ablation m2 |
|---|---|---|---|---|---|---|
| FOLD_1 | BTCUSDT | 0.0 | **+0.002660** | −0.000635 | −0.001024 | −0.000639 |
| FOLD_1 | ETHUSDT | 0.0 | +0.000051 | −0.001250 | −0.000996 | −0.000543 |
| FOLD_2 | BTCUSDT | 0.0 | −0.002374 | −0.000921 | −0.001679 | −0.001616 |
| FOLD_2 | ETHUSDT | 0.0 | +0.000084 | −0.001909 | −0.001043 | −0.001262 |
| FOLD_3 | BTCUSDT | 0.0 | −0.002010 | −0.000506 | −0.000610 | −0.000145 |
| FOLD_3 | ETHUSDT | 0.0 | −0.002424 | −0.000808 | −0.000970 | −0.001538 |
| FOLD_4 | BTCUSDT | 0.0 | −0.000705 | **+0.000589** | −0.000972 | −0.000718 |
| FOLD_4 | ETHUSDT | 0.0 | +0.000623 | −0.003646 | −0.002300 | −0.002582 |

Okuma (tahmin değil, ölçüm): swing ailesi 8 fold-sembol hücresinin 7'sinde ZARAR ediyor (net < 0); trend baseline'a göre ise 4'ünde kötü, 4'ünde iyi — bu iki bulgu farklıdır ve böyle raporlanır. İki cümle birbirine karıştırılmamalı. (Sonraki satırlar: swing ailesi 8 fold-sembol hücresinin 7'sinde baseline
`causal_trend`'e göre negatif; tek pozitif hücre (FOLD_4 BTCUSDT +0.000589) tek başına bir
bulgu değildir. Hiçbir hücrede kazanç ilan edilmedi, hiçbir policy sonuçtan seçilmedi ve
ablasyonlar (m1/m2) baseline korumaya göre iyileşme göstermedi. Bu **olumsuz sonuç olduğu
gibi** teslim edilir; minimum ekonomik bulgu kapanış koşulu değildir.

## 3. Sınırlar / pending (açık backlog)

- **Protected final yok**: son 12 ay `TAIL_BURNED`; final **açılmadı**, metadata yazıldı.
  Bu bir gate durumu değil, veri olgusudur.
- Sonuçlar **karar-düzlemi replay**: engine fill'i/venue settlement değil; funding bu yolda
  **MISSING** (sıfır sayılmadı); slippage modellenmedi.
- Prospektif olgunluk (holding/markout) ve G7 readiness **NX10'da açık pending evidence**;
  bu teslim onları tamamlanmış saymaz.
- Ekonomik edge sertifikası yok: `NO_ECONOMIC_CLAIM`. Bu iş **teknik kabul**tür ve öyle kalır.

Reproduce: `uv run --project v8-next --extra dev --extra research python v8-next/tools/nx09_fold_research.py`
