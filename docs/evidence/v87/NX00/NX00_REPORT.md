# NX00 (#433) — Ana goal: v8-next swing benchmark paketi

Durum: **R1 tamam; R2 kısmi (NX01 tamam, NX02–NX11 açık); R3–R6 sürüyor.**
`NO_ECONOMIC_CLAIM` yürürlükte. Bu dosya epic seviyesinde kimlik, sıra, matris ve
kanıt backlog'unu tutar; alt işlerin matrisleri `docs/evidence/v87/NX<nn>/` altındadır.

## R1 — Başlangıç kimliği (tamam)

`baseline_identity.json` sha256 `ded4940d928d86f9a19602087c1e395b1007608f5fc98872e1d1bdd41ebb8cfd`

| Alan | Değer |
|---|---|
| Issue base SHA | `0990615962431ca8434824b3be33ac076a69f3bf` |
| Oturum başlangıcı HEAD | `0990615962431ca8434824b3be33ac076a69f3bf` (main) |
| Kayıt anında HEAD | `7a3d2859a2c42813bc5bfbd694946faec6c79819` |
| Çalışma ağacı | kirli, 40 giriş (owner değişiklikleri **korundu**, hiçbiri geri alınmadı) |
| Stash | 1 giriş (başka bir ajanın kendi çalışması; bu iş dokunmadı) |
| `uv.lock` sha256 | `316bd8444beff3dcbcd8761f29152a7a3fdaeaba313453fb7a87c2c766603778` |
| `v8-next/uv.lock` sha256 | `f230c2bddabb4d0f8c8dc7f11e51a2f81a1945b01b36b98bfe3c5ac61c3b7a2c` |
| Runtime | Python 3.12.12 · nautilus-trader 2.0.0rc4 · polars 1.44.1 · numpy 2.5.3 · pydantic 2.13.5 |

### Eşzamanlı ajan sürüklenmesi (ölçülmüş, gizlenmedi)

Bu oturum sürerken başka bir otonom ajan `main`'i ilerletti: `9f8e19a0` (docs/D-163,
"otonom merge yetkisi"), `8c8b1b39` + `45d006b6` (#387 OOS Sharpe). Bu iş yalnızca
kendi dosyalarını (`git add <explicit path>`) commit'ledi; başka hiçbir dosya
eklenmedi, silinmedi veya geri alınmadı. NX01 artefaktı hem başlangıç hem üretim anı
SHA'sını taşır.

### Gerçek v8-next call graphı (R1'in ikinci yarısı)

Ölçülen gerçek yüzey (iddia değil, dosya okuması):

| Katman | Gerçek dosyalar | Testler |
|---|---|---|
| Veri/girdi | `v8-next/src/v8_next/evaluation/multitape.py`, `v8-next/src/v8_next/evaluation/tape_identity.py` (yeni), `v8-next/src/v8_next/adapters/catalog_tape.py`, `v8-next/src/v8_next/adapters/funding_history.py` | `test_tape_identity_nx01.py`, `test_catalog_f6.py` |
| Muhasebe | `v8-next/src/v8_next/evaluation/runner.py`, `v8-next/src/v8_next/evaluation/economic_benchmark.py`, `v8-next/src/v8_next/adapters/portfolio_equity.py`, `v8-next/src/v8_next/adapters/accounting_replay.py` | `test_d153_runner_report.py`, `test_portfolio_benchmark.py`, `test_report_accounting.py` |
| Ledger/receipt | `v8-next/src/v8_next/evaluation/benchmark_receipt.py`, `v8-next/src/v8_next/evaluation/parity.py` | `test_execution_scoring_link.py` |
| Forward/prospective | `v8-next/src/v8_next/evaluation/forward_plan.py`, `v8-next/src/v8_next/evaluation/stream_replay.py`, `v8-next/src/v8_next/adapters/economic_paper.py`, `v8-next/src/v8_next/adapters/shadow_ingest.py` | `test_forward_plan.py`, `test_stream_replay.py`, `test_paper_recovery.py` |
| İstatistik | `v8-next/src/v8_next/evaluation/alignment.py`, `v8-next/src/v8_next/evaluation/family.py`, `v8-next/src/v8_next/evaluation/reality_check.py`, `v8-next/src/v8_next/evaluation/deflated_sharpe.py`, `v8-next/src/v8_next/evaluation/overfitting.py` | `test_loss_alignment.py`, `test_family.py`, `test_reality_check.py`, `test_deflated_sharpe.py`, `test_overfitting.py` |
| Skor/gate | `v8-next/src/v8_next/evaluation/scoring.py`, `v8-next/src/v8_next/evaluation/certificate.py`, `v8-next/src/v8_next/evaluation/gate_resolution.py` | `test_execution_scoring_link.py`, `test_gate_resolution.py` |
| Politika | `v8-next/src/v8_next/economics/grammar.py`, `v8-next/src/v8_next/economics/protection.py`, `v8-next/src/v8_next/adapters/expert_strategy.py` | `test_grammar.py`, `test_squeeze_protection.py`, `test_campaign_protection.py` |

Python/Nautilus icra düzlemi mevcuttur (`nautilus-trader==2.0.0rc4`,
`v8-next/src/v8_next/adapters/execution_models.py`, `v8-next/src/v8_next/app/paper.py`, `v8-next/src/v8_next/app/sandbox.py`, `v8-next/src/v8_next/app/trial.py`); bu iş onu yeniden
kurmaz, mevcut arayüzleri yeniden kullanır.

## R2 — Bağımlılık sırası ve artefakt doğrulaması (sürüyor)

Sıra: NX01, NX02, NX04 → NX03 → NX05, NX06 → NX07 → NX08 → NX09, NX10 → NX11.

| İş | Durum | Doğrulanan artefakt |
|---|---|---|
| NX01 (#422) | **Tamam (R1–R6)** | `docs/evidence/v87/NX01/` + commit `7a3d2859` |
| NX02 (#423) | Açık | — |
| NX04 (#425) | Açık | — |
| NX03 (#424) | Açık (NX01 girdisi hazır: `calendar.json`) | NX01 `calendar.json` read-back doğrulandı |
| NX05 (#426) | Açık (NX02/NX03/NX04 bekler) | — |
| NX06 (#427) | Açık (NX02/NX03 bekler) | — |
| NX07 (#428) | Açık | — |
| NX08 (#429) | Açık | — |
| NX09 (#430) | Açık | NX01 burn tablosu: protected final **YOK** → diagnostic teslim yolu |
| NX10 (#431) | Açık | — |
| NX11 (#432) | Açık | NX01 matrisi hazır |

Bir issue'nun "kapalı" olması kanıt sayılmaz; yukarıdaki satırlar commit + artefakt
hash'i ile bağlanır.

## R3 — Alt işlerin tek-goal yürütümü

Her alt iş kendi R1–R6'sını kendi evidence dizininde matrisler. NX01 bu kalıbın ilk
uygulamasıdır (`docs/evidence/v87/NX01/NX01_REPORT.md`).

## R4 — Matris disiplini

- Test fixture'ı economic receipt olarak sunulmaz; her PASS satırı gerçek dosya +
  exact komut + ölçülmüş sonuca bağlıdır.
- Yalnızca code review bulgusu test-pass sayılmaz.
- Baseline kusurları ayrı raporlanır (NX01 raporu §6; mypy: 5 önceden var olan hata).

## R5 — Açık kanıt backlog'u

| Kalem | Durum | Etki |
|---|---|---|
| Mark price (funding mark) | **ABSENT** — 4 yıllık arşiv kümesinde yok | Funding mark ölçümü yapılamaz; sıfır/türetilmiş değer kullanılmaz |
| Protected final (son 12 ay) | **YOK** — `TAIL_BURNED` ölçüldü | NX09 final açamaz; diagnostic + prospective backlog |
| Prospective olgunluk | Bekliyor | NX10'da pending evidence; G7/live readiness iddia edilemez |
| Ekonomik edge | Kanıt yok | `NO_ECONOMIC_CLAIM` |

## R6 — Ekonomik iddia ve yetki

Bu epic bir ekonomik sertifika değildir. Teknik kabul ile ekonomik sertifika ayrıdır;
NX01 ölçümleri hiçbir skor, PASS veya getiri iddiası üretmez. Live emir/transfer/merge/
tag yetkisi kullanılmamıştır (main'e yalnızca yerel commit atılmıştır).
