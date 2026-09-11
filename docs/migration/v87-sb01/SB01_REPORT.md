# SB01 (#410) — Dört yıllık veri, burn geçmişi ve aktif Rust yürütme envanteri

Durum: **TESLİM EDİLDİ (R1–R5), R6 KISMİ**. Bu rapor yalnızca ölçülmüş gerçek
dosyalara ve okunmuş kaynak kod çağrı yoluna dayanır; hiçbir sayı beyandan
türetilmemiştir.

| Alan | Değer |
|---|---|
| Issue | #410 (SB01) |
| Base SHA (yayınlanmış docs) | `d5826c2198b18cb73b38d882d1b8119ecd8a49c0` |
| Bu işin commit'i | `bc1a5aed` (araç + ilk manifest); rol bağlama sonrası ikinci commit |
| Change class | CONTRACT_IMPLEMENTATION |

## 1. Envanter (R1) — ölçülmüş

Araç: `v8-core/src/bin/tape_inventory.rs` (yeni tarama tooling'i: **yalnızca Rust**,
salt okunur; tape dizinine hiçbir şey yazmaz, arşivleri yeniden yazmaz).

| Metrik | Değer |
|---|---|
| Tape | `research/tape/multi-1h-4y/tape.jsonl` — 226.706.603 bayt, 394.545 satır |
| tape sha256 | `sha256:b27891e917c38b59aaede1c07fe8316cd0600332389bbefcb667253448a18fa0` |
| Pencere | 2022-07-01T00:00:00Z → 2026-06-30T23:59:59.999Z (48 ay) |
| Arşivler | 960 `.zip` (17.166.942 bayt) + 960 `.CHECKSUM` + 960 `source.json` kaydı |
| Üç yollu hash | **960/960 eşleşti** (fiziksel dosya = sidecar = registry) |
| Registry sha256 | `sha256:32efa35ee739890189a49ea969d8a5f512869e9bb78178a5ff03bce5b090ace4` |
| Arşiv küme özeti | `sha256:15c2362edd61924991771f3c64e0f9784332ee495a228161b2b0846c95120a27` |
| Semboller | 10: ADA, AVAX, BNB, BTC, DOGE, ETH, LINK, LTC, SOL, XRP (hepsi USDT-M perp, binance-um) |

Sembol bazında kapsam (ölçülmüş):

| Sembol | kline satır | benzersiz | duplicate | eksik slot | coverage | grid | funding satır |
|---|---|---|---|---|---|---|---|
| ADAUSDT | 35.064 | 35.064 | 0 | 0 | 1.0000 | 1h tam | 4.383 |
| AVAXUSDT | 35.064 | 35.064 | 0 | 0 | 1.0000 | 1h tam | 4.383 |
| BNBUSDT | 35.064 | 35.064 | 0 | 0 | 1.0000 | 1h tam | 4.383 |
| BTCUSDT | 35.064 | 35.064 | 0 | 0 | 1.0000 | 1h tam | 4.383 |
| DOGEUSDT | 35.064 | 35.064 | 0 | 0 | 1.0000 | 1h tam | 4.383 |
| ETHUSDT | 35.064 | 35.064 | 0 | 0 | 1.0000 | 1h tam | 4.383 |
| LINKUSDT | 35.064 | 35.064 | 0 | 0 | 1.0000 | 1h tam | 4.383 |
| LTCUSDT | 35.064 | 35.064 | 0 | 0 | 1.0000 | 1h tam | 4.383 |
| SOLUSDT | 35.064 | 35.064 | 0 | 0 | 1.0000 | 1h tam | **4.458** |
| XRPUSDT | 35.064 | 35.064 | 0 | 0 | 1.0000 | 1h tam | 4.383 |

* Kline: 350.640 satır, her sembolde tam 1h grid'i, boşluk yok, duplicate yok,
  `closed: true` olmayan satır yok, eksik payload alanı yok, 394.545 satırın
  tamamında `payload_hash` benzersiz.
* **SOLUSDT funding heterojen**: interval dağılımı ölçüldü →
  `{8h: 4357, 4h: 2, 2h: 99}`. Diğer semboller saf 8h. Bu 99 olay modal 8h
  grid'ine yuvarlanırsa sessizce kaybolur; envanterde ayrı alan olarak duruyor.
* **Mark price YOK.** Arşiv kümesi yalnızca `1h` + `fundingRate` kanallarından
  oluşuyor; `markPriceKlines` hiçbir katmanda yok. Bu bir eksiklik olarak
  kayıtlıdır, sıfır veya türetilmiş fiyatla doldurulmamıştır.

## 2. Burn haritası (R2) — kayıtlı erişimden

Kaynak: depodaki erişim kayıtları (`tests/parity/*.py`, `v8-core/src`, `docs/`,
`artifacts/`, `.audit/`) ve D152 rol tablosu. **Hiçbir dönem otomatik
PROTECTED yapılmadı.**

| Segment | Tarih | Rol | Kanıt |
|---|---|---|---|
| PARITY_SLICE_BURNED | 2022-07-01 .. 2022-10-01 13:59 | `BURNED_DIAGNOSTIC` | `test_parity_s0.py:139` limit=25.000, `s1.py:198` limit=20.000, `s4_realtape.py:61` `_TAPE_LIMIT=2000`. En derin satır-indeksli erişim = ilk 25.000 satır (sembol başına 2.500) |
| DEVELOPMENT_RESIDUE_UNSEEN | 2022-10-01 14:00 .. 2025-06-30 | `USAGE_UNKNOWN` | Bu aralık için hiçbir erişim kaydı bulunamadı. Korunmuş OOS **değildir** |
| FINAL_12M_BURNED | 2025-07-01 .. 2026-06-30 | `BURNED_DIAGNOSTIC` | `quad-1h-12m` (AVAX/BTC/ETH/SOL, 2025-07..2026-06) aktif Rust yolunda: `bench_runner.rs:66`, `main.rs:1710`; `sol-dev-*` aynı pencere; `btcusdt-1h-12m` 2025-07..2026-07 varsayılan tape (`main.rs:116,1653,1687,1827`); D152:21 burned quad → `BURNED_DIAGNOSTIC`, promotion `NONE` |
| PROSPECTIVE_CANDIDATE | 2026-07-01 .. | `PROSPECTIVE_SHADOW_CANDIDATE` | `btcusdt-1h-12m` 2026-07-31'e kadar uzanıyor. **Aday**; SB09 freeze + gerçek alınma zamanı olmadan prospektif kanıt değil |

## 3. 24/12/12 takvim bağlaması (R3) — kritik sonuç

| Dönem | Gerçek tarih | Planlanan rol | Fiilî rol |
|---|---|---|---|
| Ay 1–24 | 2022-07-01 .. 2024-06-30 | DEVELOPMENT | DEVELOPMENT (ilk ~3 ay ayrıca BURNED) |
| Ay 25–36 | 2024-07-01 .. 2025-06-30 | WALK_FORWARD_VALIDATION | USAGE_UNKNOWN veri üzerinde walk-forward |
| Ay 37–48 | 2025-07-01 .. 2026-06-30 | PROTECTED_OOS | **INELIGIBLE_EVIDENCE** — bu dönem `quad-1h-12m` / `sol-dev` / `btcusdt-1h-12m` lineage'ları tarafından tüketilmiş, yani yanmış |

Sekiz walk-forward takvimi: WF1 (test 2024-07..09), WF2 (2024-10..12),
WF3 (2025-01..03), WF4 (2025-04..06) — dördü de Ay 25–36 içinde, yani
`USAGE_UNKNOWN` bölgede.

> **Açık kayıt:** Dört yıllık pencerede bağımsız tarihsel test **yoktur**.
> "Korumuş gibi görünen" son 12 ay tam olarak zaten kullanılmış olan sondur.
> Kalan tek bağımsız kanıt ekseni prospektiftir (SB09) ve bu takvimle
> 2026-07-01'den sonra başlar. Bu, SB08'in finalini **açılmaz** kılar; teknik
> tamamlanma negatif/INELIGIBLE sonuçla da geçerlidir (şartname §10).

## 4. Aktif Rust çağrı yolu ve resmî evaluator açığı (R4)

Gerçek sembollerle ölçülen yol:

```text
v8-core/src/cli.rs   Commands::Bench { quick, case }
        ↓
v8-core/src/main.rs  fn cmd_bench_quick(...)
        ↓
v8-core/src/main.rs:2498  BenchmarkRunner::default().run_benchmark(&BenchmarkCase)
        ↓
v8-core/src/benchmark/runner.rs:56  run_benchmark()
        ├─ case_id / case_hash boş ise → "BLOCKED_INVALID_BENCHMARK_CASE"
        ├─ verify_evidence_artifacts(case)
        └─ Err("BLOCKED_REGISTERED_BENCHMARK_EVALUATOR_REQUIRED")
```

* **Resmî yol kapalıdır**: D-156 kayıtlı evaluator PIN'i açık olduğu için
  `run_benchmark` receipt üretmez, fail-closed davranır.
* `run_benchmark_diagnostic` (runner.rs:73) aynı fiziksel kanıtı doğrular ama
  `receipt_minted: false` ve `DIAGNOSTIC_AUTHORITY` ile döner; skor, gate
  verdict'i veya ekonomik iddia üretmez. Diagnostic'in varlığı resmî evaluator
  yeterliliği **değildir**.
* **Muhasebe zinciri benchmark modülüne bağlı değil**: `benchmark/` içinde
  `cashflow` / `execution_boundary` / `portfolio` toplam **3 satırda** geçiyor
  (2'si `gate_authority.rs`, 1'i `report.rs`) — hiçbir fill/fill→lifecycle→
  cashflow→equity zinciri benchmark koşusuna bağlanmıyor. SB02/SB04'ün
  var olma sebebi tam olarak bu boşluktur.
* Gerçek bölücü semboller: `WalkForwardPartitioner::new(4, true, 0.70,
  3_600_000_000_000 /*1h*/, 86_400_000_000_000 /*1d*/)`,
  `CpcvPartitioner::new(6, 2, 1h, 1d)` — SB03'ün bağlanacağı tipler.
* **Dört yıllık tape hiçbir Rust yoluna bağlı değil.** Aktif varsayılanlar
  `btcusdt-1h-12m` ve `quad-1h-12m` (`main.rs:116,1653,1687,1710,1827`,
  `exit_ablation.rs:58`, `bench_runner.rs:66`, `kaizen/iteration.rs:571-584`).

Python bulguları (`position_id` yeniden kullanımı, 500-bar varsayılanı, 50/60
sabit puanı) bu raporda Rust'ta doğrulanmış bulgu olarak **işaretlenmemiştir**;
her biri ilgili SB paketinde Rust yolunda yeniden ölçülecektir.

## 5. Hash-bound manifest ve read-back (R5)

| Artifact | sha256 |
|---|---|
| `docs/migration/v87-sb01/tape_inventory.json` | `becfe6f6a81ca51d56a2a0994f0de82656a02183614f877446e68f68fd73af61` |
| `docs/migration/v87-sb01/role_plan.json` | `45dfed5cbaaadfe75c5f93d4db0614d914f67c16ed0e7bd6a2e79529d931b857` |
| `v8-core/src/bin/tape_inventory.rs` | `3a8443333b8e486584f86bab8a388553d9e759b0285fae73260d09ffd0e89be1` |
| Manifest identity | `sha256:7f65494c4563b20207422456e4f6a6453b65f5294ede55f898470a1cfd9589d5` |

Manifest kimliği duvar saati damgasını **dışlar**: aynı baytlar + aynı şema
yeniden tarandığında aynı kimlik üretilir. `role_plan.json` hash'i manifestte
taşınır; roller bir **girdidir**, araç tarafından çıkarılmaz. Veri konumu/hash
taşınırsa eksik kaynak açık kalır (`archives.sidecar_only` / `missing_source_entry`).

## 6. Downstream girdiler (R6)

* **SB02** → bu tape'te execution/fill/account kaydı **yok**; tape yalnızca piyasa
  verisi taşıyor. SB02 gerçek izinli fill/account kaydı olmadan PENDING kalır.
  Girdi olarak: `funding_grid_regularity = HETEROGENEOUS`, `mark_price = ABSENT`.
* **SB03** → hazır: partition manifesti (3 segment), dört fold takvimi, doğrulanmış
  kesintisiz 1h karar saati grid'i (0 boşluk/0 duplicate), ve SOLUSDT nedeniyle
  embargo'nun tek tip 8h funding varsayamayacağı uyarısı.
* SB05'in sembol evreni BTC/ETH için kapsam doğrulanmıştır (ikisi de 48 ay tam).

## 7. Doğrulama komutları ve gerçek sonuçlar

```text
cargo test  --manifest-path v8-core/Cargo.toml --bin tape_inventory
  → 8 passed; 0 failed        (grid adımı 1000× hatasına karşı kalıcı test dahil)

cargo run --manifest-path v8-core/Cargo.toml --bin tape_inventory -- \
  scan --tape-dir research/tape/multi-1h-4y \
       --out docs/migration/v87-sb01/tape_inventory.json \
       --roles docs/migration/v87-sb01/role_plan.json
  → 960 zips / 960 sidecars / 960 registry entries; 3-way matched 960
  → 350640 kline + 43905 funding (10 instruments); mark price present = false; roles BOUND

cargo run --manifest-path v8-core/Cargo.toml --bin tape_inventory -- \
  verify --manifest docs/migration/v87-sb01/tape_inventory.json
  → verify PASS — 28 identity fields reproduced for 10 instruments   (exit 0)
```

## 8. Bu pakette üretilmeyenler (açıkça)

* Resmî benchmark receipt/certificate **yok** (D-156 PIN açık, `run_benchmark` fail-closed).
* Ekonomik sonuç, getiri, p-value, Sharpe, PBO **yok** — `NO_ECONOMIC_CLAIM` yürürlükte.
* Mark price / open interest içeren bir maliyet ya da likidasyon sonucu **yok**;
  bu veriler hiçbir fiyatla doldurulmadı.
* SB02 için gerçek fill/account kaydı bulunamadı; uydurulmadı, PENDING bırakıldı.
