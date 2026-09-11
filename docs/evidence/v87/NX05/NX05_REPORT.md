# NX05 (#426) — D153 ve portfolio benchmark yollarını ortak pencere ve receipt kimliğine bağla

Durum: **R1–R6 teknik olarak teslim edildi.** `NO_ECONOMIC_CLAIM`. Hiçbir koşu ekonomik
yeterlilik kanıtı sayılmadı; smoke koşular açıkça smoke etiketlidir.

## 0. Ortak sözleşme (yeni: `evaluation/run_window.py`)

Üç kural kod olarak uygulanır, çağıranın disiplinine bırakılmaz:

1. **Bar sayısı ile sınırlı pencere = smoke.** `--bars` yalnızca `smoke` profilini
   tanımlar; `fold`/`benchmark` mutlaka açık UTC sınırlarıyla verilir. Smoke çalıştırma
   çıktısı "liveness/mechanics only, NOT economic evidence, NOT a release benchmark"
   diye bağırır ve manifestte `economic_evidence=false` yazar.
2. **`RunKey`**: tape sha256 + pencere + case/policy + strateji config + sermaye/ücret +
   baseline + execution profile + code/lock hash üzerinden içerik-adresli digest.
   İçinde duvar saati yoktur; aynı girdi her seferinde aynı anahtarı verir.
3. **Tamamlanmış pencere yeniden koşmaz.** Pencere manifesti atomik yazılır; `COMPLETED`
   anahtar yeniden çalıştırmayı reddeder (ikinci ledger append ve ikinci nakit akışı
   olmaz). `RUNNING` manifesti "tamamlanmamış" olarak raporlanır, başarı sayılmaz.

## 1. R → exact check → artifact matrisi

| R | Değişiklik | Exact check | Ölçülen sonuç |
|---|---|---|---|
| R1 | İki CLI'de de `--start-utc/--end-utc/--fold-id/--profile`; 385/500-bar kısayolları smoke olarak etiketlendi | `pytest -q v8-next/tests/test_run_window_nx05.py` | PASS — smoke etiketi "SMOKE WINDOW … NOT economic evidence" içerir; `--bars` ile `fold` reddedilir |
| R2 | Run key dört sink'e bağlandı: rapor/window manifesti, execution telemetry, ledger (receipt `input_binding`), ResearchStore (`runs` tablosu) | `test_cli_binds_one_run_key_to_report_telemetry_ledger_and_store` | PASS — tek smoke koşusunda dört sink aynı anahtarı taşır |
| R3 | `load_tape_candles` ve `load_multitape` lazy `scan_ndjson` + UTC pencere; boş pencere fail-closed; funding writer yokluğu zaten `FUNDING_CATALOG_SUPPORT` ile bildiriliyor | `test_real_utc_window_is_exact_bounded_and_deterministic` | 744 bar penceresi 0.49 s'de; pencere sınırsız serinin birebir dilimi; boş pencere `FileNotFoundError` |
| R4 | Atomik pencere manifesti + `RunKey` + tamamlanmış koşu reddi | `test_completed_window_refuses_reexecution` + gerçek CLI koşusu | İkinci koşu **exit 3**, ledger sha256 ve giriş sayısı **değişmedi** (1 → 1) |
| R5 | `tools/nx05_profiles.py`: aynı gerçek pencere + aynı tape iki yoldan; signature/equity/maliyet tablosu | `python v8-next/tools/nx05_profiles.py` | İki yol 744 bar; signature farklı → `funding_attribution=NOT_CLAIMED_SIGNATURES_DIFFER` |
| R6 | Smoke / fold / benchmark profilleri ayrı süreçlerde; exact komut, walltime, peak RSS, artifact read-back | aynı tool | smoke 1.371 s / 582 MB, fold(D153) 1.399 s / 584 MB, fold(portfolio) 20.226 s / 607 MB |

Artefaktlar (`docs/evidence/v87/NX05/`):
`profiles.json` sha256 `63a5e036eab9b7be2bd7b2e2de4888f23305b57a2f1ac3e145261df9f4a6c45d`
`reconcile_table.json` sha256 `a6587de0c31007b6c9e556ee8e2041357ab784903924c229e5d3a82d7129421f`
(+ `NX05_REPORT.md`).

## 2. İki yolun farkları (R5) — uydurulmadı, açıklandı

| Alan | D153 benchmark yolu | Portfolio yolu |
|---|---|---|
| Tape | `research/tape/multi-1h-4y` | **aynı** tape |
| Pencere | 2025-01-01 → 2025-02-01 (744 bar) | aynı pencere, 744 bar |
| Universe | tek enstrüman (BTCUSDT) | tape'in tüm bacakları |
| Run key | `sha256:23956d1a…` | `sha256:44b8ebf5…` |
| State | COMPLETED | COMPLETED (receipt verify OK, ledger chain OK) |
| Trade signature | `0dd590098c…` | `c6a22ad945…` |

Anahtarların farklı olması bir kusur değil, tasarımın kendisidir: farklı case/policy/
universe farklı run'dır. Signature'lar farklı olduğu için **funding/no-funding
attribution iddia edilmedi** (R5'in şartı). Evrensel fark (1 enstrüman vs tüm bacaklar)
tabloda açıkça yazılıdır; bu bir hata kanıtı sayılmaz.

## 3. Sınırlar / pending

- Koşular smoke ve fold **probe**'larıdır; ekonomik yeterlilik kanıtı **değildir**
  (`economic_evidence: NONE — NO_ECONOMIC_CLAIM`). Skor üretilmedi, hedef skor yok.
- "Başka run artifactı gate çözemez" kuralı `verify_artifact_run_key` ile uygulanır
  (foreign → `FOREIGN_RUN_ARTIFACT`, bitmemiş → `INCOMPLETE_RUN`, hash uyuşmazlığı →
  `ARTIFACT_HASH_MISMATCH`); gate resolver'ın bu kontrolü çağırması NX08 kapsamındadır.
- Uzun (4 yıllık) benchmark koşusu bu iş kapsamında çalıştırılmadı; yükleme yolu
  bounded-memory olarak doğrulandı, engine koşusu NX09 kapsamındadır.
