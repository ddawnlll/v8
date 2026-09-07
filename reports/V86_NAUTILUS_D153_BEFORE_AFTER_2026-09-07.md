# V8.6 Nautilus Lane — D-153 Before/After Audit Report (2026-09-07)

## Talep
`usd-sim'i nautilus trade ile degistir, gerekirse v8'i ona gore kalibre et,
sonrasinda bana oncesi ve sonrasi d-153 audit raporunu sun karsilastiralim.`

## Karar (fail-closed)
`usdm_sim` **silinmedi**. Gerekçe:
- D-116 ikincil referans motor şartı + D-160 W4 verdict: "Nautilus differential
  (W14) does not exist; deleting now would violate D-116."
- Doğru migrasyon: `ExecutionLane` soyutlaması + `NautilusLane` adaptörü,
  varsayılan `usdm`, opt-in `--engine-mode nautilus`. Tam replasman W14'e kadar blokeli.

## Değişiklik
- `v8-core/src/execution/mod.rs` (yeni, ~200 satır): `ExecutionLaneId::parse`,
  `resolve_lane` (unknown → Err), `UsdmLane`, `NautilusLane::venue_config`,
  `calibrate()` (Mapped/Unmapped/NotApplicable; sentetik sıfır yok).
- `v8-core/src/lib.rs`: `pub mod execution;`
- Yeni testler: `lane_resolution_fails_closed_on_unknown`,
  `nautilus_calibration_never_fabricates` (13 lib testi içinde yeşil).

## Kalibrasyon (NautilusLane, venue=BINANCE)
| Boyut | usdm | nautilus | Statü |
|---|---|---|---|
| account/leverage | 10 | 10 | Mapped |
| account/balance | 1000.0 | 1000.0 | Mapped |
| risk/risk_fraction | 0.005 | — | Unmapped (strateji tarafı, venue karşılığı yok) |
| execution/maker_fill_probability | — | — | Unmapped (W14) |
| execution/adverse_selection | — | — | Unmapped (W14) |
| funding/clock_sign | — | — | Unmapped (D-160 OPEN_PIN: liquidation cum-sign) |
- `unmapped_count = 4`; gap'lar `None` + not ile kayıtlı, uydurma değer yok (Rule 12).

## D-153 Before/After
Komut:
`cargo test --manifest-path v8-core/Cargo.toml --test d153_benchmark_fabric_sabotage
--test d153_minerva_and_dashboard_test --test d153_parity_adapters_policy_bound
--test d153_receipt_ledger_selfverify --test d152_gate_vector_authority_firewall`

| Suite | Öncesi | Sonrası |
|---|---|---|
| d153_benchmark_fabric_sabotage (BFS-001..024) | 24/24 | 24/24 |
| d153_minerva_and_dashboard | 3/3 | 3/3 |
| d153_parity_adapters_policy_bound | 50/50 | 50/50 |
| d153_receipt_ledger_selfverify | 40/40 | 40/40 |
| d152_gate_vector_authority_firewall | 15/15 | 15/15 |
| **TOPLAM** | **132/132** | **132/132** |
- `cargo clippy`: No issues found (önce/sonra aynı).
- Drift yok: D-160 pin tablosu korunuyor (132/132; drift = STOP).

## Sonuç
- Lane takası iskeleti + kalibrasyon raporu canlı; D-153'te regresyon yok.
- Tam `usdm_sim` silme + Nautilus matching-engine bağlama: W14 OPEN_PIN olarak açık
  (maker fill, adverse selection, funding-clock ölçümü + `nautilus-trader = 0.63`
  bağımlılık bağlama).
- Verdict: `NO_ECONOMIC_CLAIM` (D-153 PROVISIONAL; benchmark ≠ assurance).
