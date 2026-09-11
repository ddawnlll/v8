# NX01 (#422) — Dört yıllık tape kimliği, burn haritası ve Python veri bağlantısı

Durum: **R1–R6 teknik olarak teslim edildi** (ekonomik beyan yok — `NO_ECONOMIC_CLAIM`).
Bu rapor yalnızca bu oturumda ölçülmüş fiziksel dosyalara ve gerçek komut çıktılarına
dayanır. Hiçbir sayı beyandan alınmamıştır.

## 0. Kimlik (R1)

Mevcut envanter artefaktları bulundu ve hash'leri doğrulandı (SB01 paketi, `bc1a5aed` /
`92c64b04` / `73dcfbb8`, üçü de `09906159`'un atası):

| Artefakt | sha256 |
|---|---|
| `docs/migration/v87-sb01/SB01_REPORT.md` | `a234371c03ba4481ea41417dbb38b3857a434d12b79e421def94c1211bb0ab76` |
| `docs/migration/v87-sb01/role_plan.json` | `8135419c29b7e280de747e647ded2e1bd5c6ab562f1ea2ae47ec5e038d4fba1e` |
| `docs/migration/v87-sb01/tape_inventory.json` | `81d64322acba8d33fd9076ee1671492484fc8e1e2277db818b50f2ad311149a4` |

Rust envanter aracı (`v8-core/src/bin/tape_inventory.rs`) artık referanstır; bu iş
envanteri **Python tarafında yeniden ölçtü** ve iddiaları bağımsız olarak doğruladı
(960/960 üç yollu hash, SOL heterojen funding, mark price yokluğu — hepsi teyit edildi).

| Alan | Değer |
|---|---|
| Issue base SHA | `0990615962431ca8434824b3be33ac076a69f3bf` |
| Oturum başlangıcı HEAD | `09906159` (aynı) |
| Artefakt üretimi sırasında HEAD | `45d006b636536f4489e95593ffba6a918032eab5` |
| Implementation commit | `7a3d2859a2c42813bc5bfbd694946faec6c79819` |
| Çalışma ağacı | kirli (owner değişiklikleri korundu; R1 kapsamı dışında hiçbir dosya geri alınmadı) |
| `uv.lock` (kök) sha256 | `316bd8444beff3dcbcd8761f29152a7a3fdaeaba313453fb7a87c2c766603778` |
| `v8-next/uv.lock` sha256 | `f230c2bddabb4d0f8c8dc7f11e51a2f81a1945b01b36b98bfe3c5ac61c3b7a2c` |
| Runtime | Python 3.12.12, nautilus-trader 2.0.0rc4, polars 1.44.1, numpy 2.5.3, pydantic 2.13.5 |

**SHA sürüklenmesi (ölçülmüş):** oturum sırasında başka bir otonom ajan `main`'e
`9f8e19a0` (docs/D-163) ve `8c8b1b39`+`45d006b6` (#387) commit'lerini ekledi. Bu iş
kendi commit'ini `45d006b6` üzerine attı; sürüklenme gizlenmedi, artefaktta hem
oturum başlangıcı hem üretim anı SHA'sı kayıtlıdır.

## 1. R → commit → exact check → artifact matrisi

| R | Değişiklik | Artefakt | Exact check | Sonuç |
|---|---|---|---|---|
| R1 | `v8-next/src/v8_next/evaluation/tape_identity.py` (yeni): `inventory_tape`, `verify_archives`, `sha256_file` | `docs/evidence/v87/NX01/tape_inventory.json` sha256 `480ac1dcc84ca16cfecb480c27071923d29d55bde21571255e7ceb8eb181ea1b` | `uv run --project v8-next --extra dev --extra research python v8-next/tools/tape_inventory.py` | PASS — 394.545 satır, 10 sembol, 960/960 arşiv üç yollu eşleşti |
| R2 | `default_recorded_accesses`, `policy_lineage_burn_table`, `RecordedAccess.verify`, `ROLE_TO_DATA_ROLE` | `docs/evidence/v87/NX01/burn_map.json` sha256 `24f089b1e8a2537bf2e9310d612c67056c244129cb424056214a3b6948c63ab3` | `uv run --project v8-next --extra dev --extra research pytest -q v8-next/tests/test_tape_identity_nx01.py` | PASS — 16/16 test; her iddia dosya+satır+metinden yeniden doğrulandı |
| R3 | `multitape.load_multitape` duplicate + kesişim denetimi; `portfolio_backtest.base_currency`, `catalog_tape` | `v8-next/src/v8_next/evaluation/multitape.py` @ `7a3d2859` | `uv run --project v8-next --extra dev --extra research pytest -q v8-next/tests/test_tape_identity_nx01.py` | PASS — duplicate → hard error, sessiz satır düşüşü raporlanır |
| R4 | `FundingRow.interval_defaulted`, ölçülen interval histogramı, `absence_notes` | `tape_inventory.json` → `funding_interval_counts` | aynı pytest + `v8-next/tools/tape_inventory.py` | PASS — SOL 2h×99 / 4h×2 / 8h×4357; mark price YOK kayıtlı |
| R5 | `TapeManifest`, `verify_manifest_against_file`, `bind_manifest_to_store`, `catalog_tape.build_catalog(manifest=…)` + `role_contract` | `docs/evidence/v87/NX01/manifest.json` sha256 `7e7ced3341ac41697975d121abf33d4061fbf2cb5b01b0208c29c38f6005ae90` | `pytest -q …::test_manifest_binds_to_store_and_fails_closed …::test_catalog_consumer_binds_to_the_manifest_and_fails_closed` | PASS — read-back OK; tamper `TAPE_HASH_MISMATCH`; `require_protected_final` reddedilir |
| R6 | `_add_months`, `swing_calendar`, `readback_calendar` | `docs/evidence/v87/NX01/calendar.json` sha256 `3a2517df576eba7daa1e8c012b4b88bf3bad9decfb3f8ef4176a1d81c0fe2755` | `python v8-next/tools/tape_inventory.py` (write + re-read karşılaştırması) | PASS — read-back birebir; `final_eligible=False` |

Yardımcı dosya hash'leri: `v8-next/tools/tape_inventory.py`, `v8-next/tests/test_tape_identity_nx01.py`
ve kaynak dosyaların tamamı `7a3d2859` commit'inde kayıtlıdır.

## 2. Ölçülen envanter (R1) — yeniden üretilebilir

| Metrik | Ölçülen |
|---|---|
| Tape | `research/tape/multi-1h-4y/tape.jsonl` — 226.706.603 bayt |
| sha256 | `b27891e917c38b59aaede1c07fe8316cd0600332389bbefcb667253448a18fa0` |
| Satır | 394.545 (kline 350.640 + funding 43.905) |
| Pencere | 2022-07-01T00:00:00Z → 2026-06-30T23:59:59.999Z (48 ay) |
| Sembol | ADA, AVAX, BNB, BTC, DOGE, ETH, LINK, LTC, SOL, XRP (10, hepsi 1h) |
| Leg başına | 35.064 bar; coverage 1.0000; duplicate 0; internal gap 0; unparsable 0; unclosed 0 |
| Arşiv | 960 `.zip` + 960 `.CHECKSUM`; üç yollu eşleşme **960/960** |
| Registry sha256 | `32efa35ee739890189a49ea969d8a5f512869e9bb78178a5ff03bce5b090ace4` |
| Arşiv küme digest | `fe9c855081a7df4ec70fe4f0a1eb72c38973bd17105c03d73ee35b128ca34dc4` |
| Funding interval | `{8h: 43804, 4h: 2, 2h: 99}` (SOL heterojen: 8h 4357 / 4h 2 / 2h 99) |
| Mark price | **YOK** → `MARK_PRICE_ABSENT` olarak kayıtlı, sıfırla doldurulmadı |

## 3. Burn haritası (R2) — kayıtlı erişimden, ölçülerek

Doğrulanan erişim kayıtları (dosya + satır + metin birebir kontrol edilir; eksik/uyumsuz
kayıt **fail** eder, atlanmaz):

| Kaynak | Dayanak | Ölçülen pencere |
|---|---|---|
| `tests/parity/test_parity_s0.py:139` | `load_real_tape("multi-1h-4y", limit=25_000)` | 2022-07-01T00:00Z → 2022-10-01T13:59:59.999Z |
| `tests/parity/test_parity_s1.py:198` | `load_real_tape("multi-1h-4y", limit=20_000)` | 2022-07-01T00:00Z → 2022-09-13T00:59:59.999Z |
| `tests/parity/test_parity_s4_realtape.py:144` | `load_real_tape("multi-1h-4y", limit=_TAPE_LIMIT)` (`_TAPE_LIMIT=2000`) | 2022-07-01T00:00Z → 2022-07-08T08:59:59.999Z |

Tail tüketimi (fiziksel dosyalarla): `quad-1h-12m` (AVAX/BTC/ETH/SOL), `btcusdt-1h-12m`,
`sol-dev-solusdt-2025-07-2026-07` — üçü de 2025-07-01T00:00Z'de başlıyor, yani son 12 ayın
içinde. Bu, son 12 ayın **daha önce tüketildiğinin** ölçülmüş kanıtıdır.

Segmentler: `ACCESS_PARITY_S0_SLICE` (BURNED), `ACCESS_PARITY_S1_SLICE` (BURNED),
`ACCESS_PARITY_S4_REAL-TAPE_SLICE` (BURNED), `DEVELOPMENT_RESIDUE_UNKNOWN`
(USAGE_UNKNOWN, 2022-10-01T14:00Z → 2025-06-30T23:59:59.999Z), `TAIL_BURNED`
(BURNED, 2025-07-01T00:00Z → 2026-06-30T23:59:59.999Z).

**Rol eşlemesi (açık, tek yönlü):** `BURNED_DIAGNOSTIC` → `DEVELOPMENT`,
`USAGE_UNKNOWN` → `DEVELOPMENT`, `PROTECTED_OOS` → `HOLDOUT`. Ne `BURNED_DIAGNOSTIC`
ne `USAGE_UNKNOWN` bir `store.DataRole` değeridir ve hiçbiri protected final sayılmaz.

## 4. Takvim (R6) — gerçek UTC tarihlere bağlı

- DEVELOPMENT: 2022-07-01T00:00:00Z → 2024-06-30T23:59:59.999Z (24 ay)
- FOLD_1: 2024-07-01 → 2024-09-30 · FOLD_2: 2024-10-01 → 2024-12-31 ·
  FOLD_3: 2025-01-01 → 2025-03-31 · FOLD_4: 2025-04-01 → 2025-06-30
- FINAL: 2025-07-01T00:00:00Z → 2026-06-30T23:59:59.999Z → **`final_eligible = false`**
- Gerekçe (metadata, GateState enum değeri değil):
  `NO_PROTECTED_FINAL: the final window overlaps TAIL_BURNED (burned or usage-unknown); the final is not opened`

NX03/NX05 girdileri `calendar.json` olarak yazıldı ve **re-read** ile birebir doğrulandı.

## 5. Eksik / pending kanıt (R5 kolu)

| Kalem | Durum |
|---|---|
| Mark price (funding mark) | **ABSENT** — arşiv kümesi yalnızca `1h` + `fundingRate`; sıfır veya türetilmiş fiyat kullanılmadı |
| Protected final | **YOK** — NX09 yalnızca diagnostic teslim + prospective backlog ile ilerleyebilir |
| Prospective olgunluk (NX10) | Bu issue kapsamı dışı; NX10'da pending evidence olarak durur |

## 6. Baseline kusurları (ayrı rapor)

Bu issue açılırken testler çalıştırılmamıştı. Ölçülen başlangıç durumu:

- `uv run --project v8-next --extra dev --extra research mypy v8-next/src` →
  **5 hata / 3 dosya**, hepsi `09906159` temiz kaynağında da birebir aynı (satır
  numaraları benim eklemelerim kadar kaymış):
  `adapters/expert_strategy.py:579`, `adapters/portfolio_backtest.py:200,387`,
  `evaluation/trajectory.py:43`. **Bu iş yeni mypy hatası eklemedi.**
- Baseline test yüzeyi bu oturumda yeşil: `test_catalog_f6.py`,
  `test_research_store.py`, `test_evaluation_lineage.py` → **26 passed**.
- NX01 testleri → **15 passed** (mekanik + gerçek tape).

## 7. Sınırlar

- Envanter okuma-yalnızdır; tape dizinine hiçbir şey yazılmadı, ledger yeniden hashlenmedi.
- `DEVELOPMENT_RESIDUE_UNKNOWN` "görülmemiş" iddiası **kanıtlanmış korunmuşluk değildir**;
  yalnızca kayıtlı erişim bulunamadığı anlamına gelir.
- Bu iş bir ekonomik sonuç, skor veya gate PASS iddiası üretmez.
