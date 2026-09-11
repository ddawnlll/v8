# NX04 (#425) — Ledger legacy canonicalization: doğrula, geçmişi yeniden hashleme

Durum: **R1–R6 teknik olarak teslim edildi.** `NO_ECONOMIC_CLAIM`. Hiçbir ledger byte'ı
yeniden yazılmadı; özgün dosya hash'i doğrulama öncesi ve sonrası **aynıdır**.

## 0. Ölçülen çekirdek bulgu

`artifacts/benchmarks/benchmark_ledger.jsonl` — 20 giriş, sha256
`657b2183871675d7a75ae8f1df4fd98d3529733d8856155579a775d3bfb3dccc`.

| Doğrulayıcı | Sonuç |
|---|---|
| Eski (NX04 öncesi, `HEAD`) `verify_chain()` | **BAŞARISIZ** — `ENTRY_RECEIPT_INVALID at 0: DIGEST_TAMPERED` |
| Eski doğrulayıcının digest hatası sayısı | **12 giriş** (tamamı v2) |
| Yeni (sürüm-çözümlü) `verify_report()` | **OK** — chain/digest/artifact üçü de geçerli, 20/20 |

Yani zincir ve veri sağlamdı; hatalı olan **doğrulayıcının canonical payload
varsayımıydı**. Özgün dosya hash'i ölçüm öncesi/sonrası değişmedi.

## 1. Kanon geçişleri (ölçülmüş, varsayım değil)

Her giriş için özgün ledger byte'larından yeniden üretim denendi; sonuç:

| Digest sürümü | Seq aralığı | Kanon alan sayısı | Stored digest yeniden üretildi |
|---|---|---|---|
| `v8.5-digest-v2` | 0–11 (12 giriş) | 9 | ✔ 12/12 |
| `v8.5-digest-v3` | 12 (1 giriş) | 11 | ✔ 1/1 |
| `v8.5-digest-v4` | 13–19 (7 giriş) | 12 | ✔ 7/7 |

Ekonomik alan çifti (`economic_evidence_digest`, `economic_receipt_path`) v2'de yok,
v3'te var, v4'te koşulsuz yazılıyor; `input_binding` yalnızca v4+ kanonunda.
Bu tablo `RECEIPT_CANON_TABLE` olarak koda girdi; her satırın `provenance` alanı
hangi ölçüme dayandığını yazar.

## 2. R → exact check → artifact matrisi

| R | Değişiklik | Exact check | Ölçülen sonuç |
|---|---|---|---|
| R1 | `tools/nx04_verifier_report.py` özgün ledgerı salt-okunur tarar; sürüm/digest/producer eşlemesini ölçer | `uv run --project v8-next --extra dev --extra research python v8-next/tools/nx04_verifier_report.py --legacy-rev HEAD` | seq 0–11/12/13–19 eşlemesi; tüm girişler kendi kanonuyla yeniden üretildi |
| R2 | `ReceiptCanon` + `RECEIPT_CANON_TABLE` + `build_canon_payload`: kanon yalnızca **kanıtlanmış** şablondan çözülür; rastgele alan altkümesi denemesi yok; kanıtlanmamış şekil `CANON_SHAPE_UNPROVEN` ile açık hata | `pytest -q v8-next/tests/test_ledger_canon_nx04.py` | PASS — 14 test; v2 + dolu ekonomik alan → açık red |
| R3 | Yeni yazımlar `v8.5-digest-v5` (kayıtlı); eski bytes/digest/parent hash korunur; eski kayıt yeniden hashlenmez | aynı pytest (`test_new_writes_register_a_version_without_moving_old_digests`, `test_real_ledger_verifies_and_is_never_rewritten`) | PASS — düzen aynı, sürüm işareti kanon içinde olduğu için yeni yazım yeni digest alır; ledger sha256 değişmedi |
| R4 | `EntryVerification` / `LedgerVerificationReport`: zincir, digest ve artifact **ayrı** verdict; "zincir geçerli ama artifact yok" aynı başarıya indirgenmez | `test_chain_validity_is_reported_separately_from_artifact_availability` | PASS — `overall=ARTIFACTS_INCOMPLETE`, `chain_valid=True`, `artifacts_intact=False` |
| R5 | Gerçek ledger'dan **makineyle** çıkarılan golden fixture'lar (`v8-next/tests/fixtures/ledger_canon/`), tek-alan tamper, predecessor tamper, bilinmeyen sürüm, eksik artifact testleri | aynı pytest (14 test) | PASS — fixture digest'leri tarihsel üreticilere ait, bu ağaç tarafından üretilmedi |
| R6 | Before/after doğrulayıcı raporu + değişmemiş dosya hash'i | `python v8-next/tools/nx04_verifier_report.py` | PASS — before FAIL (12 hata) / after OK (20/20); hash `657b2183…` aynı |

Artefaktlar (`docs/evidence/v87/NX04/`):
`ledger_canon_probe.json` sha256 `60ad862c4bc209ce69dca2e17050baa7bcca5a7fb5ed171688f1b6033c3176f6`
`verifier_report.json` sha256 `1c18b919c02e27fa3fb820f10599380c85d0a062fc82b7e4c4a45a2874fe95a6`
Fixture'lar: `v8-next/tests/fixtures/ledger_canon/{v8.5-digest-v2,v8.5-digest-v3,v8.5-digest-v4}.json`
+ `MANIFEST.json` sha256 `e2a0270bcb33da948049085b2b3c796f9568fca27ac013a1d0a6b0e0d996950f`

## 3. Sınırlar

- Bu düzeltme eski performans/gate iddialarını **yeniden sertifikalandırmaz**: yalnızca
  digest'in doğru şablonla yeniden üretildiğini gösterir. Ledger'daki skor/gate
  değerleri hakkında hiçbir ekonomik iddia üretilmez.
- `BROKEN @0` otomatik veri kaybı sayılmadı; ölçüm, kaybın değil doğrulayıcı
  varsayımının hatası olduğunu gösterdi.
- v2/v3 için ölçülmemiş alan kombinasyonları (ör. v3 + boş ekonomik çift) açık hata
  verir; kanıtlanmamış şekil digest tahminiyle geçirilmez.
