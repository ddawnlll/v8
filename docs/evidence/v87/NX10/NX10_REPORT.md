# NX10 (#431) — Gerçek prospective public shadow ve restart kanıtı

Durum: **R1–R6 teknik kabul** (bounded capture + restart kanıtı). Uzun ekonomik gözlem
**PENDING**; G7 PASS **değil**. Public paper **teknik kanıttır**, settlement değildir.
`NO_ECONOMIC_CLAIM`.

## 0. Kaldırılan yanlış etiket (R4)

`shadow_ingest` artık kolon varlığını/source=live'ı otorite saymıyor:

| Girdi | Eski davranış | Yeni davranış |
|---|---|---|
| İyi biçimli fills dosyası | `LIVE_VENUE_SETTLED` → G8 **PASS** | `PUBLIC_PAPER_NOT_SETTLED`, `authority: NONE` → G8 **NOT_APPLICABLE** |
| `provenance=authenticated_venue_statement` + `account_id` | yoktu | `LIVE_VENUE_SETTLED`, `authority: VENUE_STATEMENT` → G8 ancak bu yolla PASS |
| reconciliation | `shadow_count == engine_count or shadow_count > 0` | **tam eşitlik**; uyuşmazlık `COUNT_MISMATCH` + delta |

## 1. R → exact check → artifact matrisi

| R | Ne yapıldı | Exact check | Sonuç |
|---|---|---|---|
| R1 | **Gelecek** pencereli forward plan, store'un kendi saat damgasıyla freeze; historical replay prospective etiketlenmedi | `pytest -q v8-next/tests/test_public_shadow_nx10.py` | 9 passed — `window_is_in_the_future=true`, `start_ns > freeze_clock_ns`, `historical_replay_labelled_prospective=false` |
| R2 | Gerçek public capture yolu bağlandı: arrival + event damgaları, policy/runtime/lock hash'leri, rolling artifact kimliği | `python v8-next/tools/nx10_public_shadow.py --seconds 12` | 2 poll → 2 batch; `1009` kabul; her batch `payload_sha256` + `chain_hash` ile zincirli; `code_and_lock_hash` bağlı |
| R3 | Restart/recovery: duplicate/gap/out-of-order + exactly-once; eksik aralıkta fail closed + görünür recovery raporu | `test_duplicate_identities_are_dropped_and_counted`, `test_a_gap_fails_closed_until_it_is_acknowledged`, `test_out_of_order_events_are_rejected_not_reordered`, `test_resume_rebuilds_the_state_from_disk` | Aynı poll tekrarı → `1000` duplicate düşürüldü (çift sayım yok); gap → merge reddedildi (`MISSING_INTERVAL_NOT_BRIDGED`), ack ile tek kez birleşti; bozuk batch zincir kontrolünde yakalandı |
| R4 | Provenance vs authenticated settlement ayrımı | `test_public_paper_never_reads_as_a_settlement`, `test_reconciliation_is_exactly_once_not_has_any_fills`, `test_gate_resolution.py::test_g8_live_realization_modes` | Public paper → `NOT_APPLICABLE`; PASS yalnız kimlikli authenticated provenance ile |
| R5 | Olgunluk koşulları dolmadan G7 PASS değil | `maturity.json` | `g7_state=UNKNOWN`, `prospective_maturity=PENDING`; teknik kabul için bounded capture + restart yeterli |
| R6 | Exact komutlar + gerçek kısa public capture manifesti + maturity raporu | aşağıdaki komut bloğu | `docs/evidence/v87/NX10/capture/manifest.json` `ea0fd71b…`, `maturity.json` `dcb3d93a…` |

## 2. Exact start / stop / resume komutları (R6)

```sh
# freeze (gelecek pencere) + bounded public capture + restart kanıtı + maturity raporu
uv run --project v8-next --extra dev --extra research python v8-next/tools/nx10_public_shadow.py --seconds 18

# sadece doğrulama / read-back (capture dizini üzerinde)
uv run --project v8-next --extra dev --extra research python -c \
  "from pathlib import Path; from v8_next.evaluation.prospective_capture import load_capture; \
   print(load_capture(Path('docs/evidence/v87/NX10/capture'))[2])"

# shadow ingest durumu (provenance ayrımıyla)
uv run --project v8-next python -m v8_next.adapters.shadow_ingest check

# gate bataryası (G8 dahil)
uv run --project v8-next --extra dev --extra research pytest -q \
  v8-next/tests/test_public_shadow_nx10.py v8-next/tests/test_gate_resolution.py
```

Capture bir bütçe ile sınırlıdır (`--seconds`); süreç sonunda kendini kapatır, arka planda
kalan servis yoktur.

## 3. Ölçülen (12 sn'lik koşu)

| Alan | Değer |
|---|---|
| Poll / batch | 2 / 2 |
| Kabul edilen trade | 1009 |
| Duplicate düşürülen | 1000 (aynı poll'ün tekrarı; çift sayım yok) |
| Restart | `chain_verified=true`, `events_replayed=1009` |
| Zincir | her batch `payload_sha256` + `chain_hash`; manifest `chain_hash` son batch'e bağlı |
| G7 | `UNKNOWN` (prospective stream bildirilmedi, olgunluk yok) |
| Settlement | `PUBLIC_PAPER_NOT_SETTLED`, `authority: NONE` |
| Maturity | `PENDING` — pencere henüz gözlenmedi; holding/markout ölçülmedi |

## 4. Sınırlar / pending (açık backlog)

- **Prospective olgunluk PENDING**: freeze edilen 24 saatlik pencere henüz gözlenmedi.
  Bu iş onu tamamlanmış saymaz; holding/markout koşulları ölçülmedi.
- Public capture **hesap erişimi gerektirmez**; kimlikli/private kol kapsam dışıdır ve
  kapsam dışı **kalır** (goal private emir/transfer yetkisi vermez).
- G7 readiness ve ekonomik edge **sertifikalanmadı**; `NO_ECONOMIC_CLAIM`.
- Kısa capture, pipeline'ın çalıştığının kanıtıdır; istatistiksel bir iddia değildir.
