# V8.7 v8-next uygulama planı

Kullanıcının 2026-09-11 açık talimatı: asıl codebase v8-next; yanlış issue’ları kapat ve v8-next kaynaklarını tarayarak yeniden aç. Bu V8.7 kapsamı için Python/Nautilus uygulama yetkisi geçerlidir; eski Rust-only/frozen ifadeler bu kapsamı veto etmez. v8-core yalnızca referanstır; src/v8 ve kök tests tarihsel oracle olarak korunur. Kapsam için yeniden reactivation izni istenmez.

Normatif kaynak: [docs/contracts/V87_SWING_BENCHMARK_SPEC.md](../contracts/V87_SWING_BENCHMARK_SPEC.md). Tarama SHA `0990615962431ca8434824b3be33ac076a69f3bf`. Python 3.12, mevcut uv.lock ve NautilusTrader 2.0.0rc4 kullanılır.

## Yürütme sırası
NX01, NX02, NX04 → NX03 → NX05 ve NX06 → NX07 → NX08 → NX09 ve NX10 → NX11. NX00 üst goal takibidir. Bağımsız işler sırayla da ilerleyebilir; alt issue artefact bağımlılıkları esastır.

## Kaynak taraması ve yeniden kullanım
Bu paket sadece .rs uzantısını .py ile değiştirme değildir: Python pair_positions, ResearchStore, ForwardPlan, CampaignProtection, CatalogBuild ve istatistik modülleri korunur. Ledger verifier ayrı NX04 kapsamındadır. D153 ve economic portfolio yolları birlikte kapsanır.

## NX01
Önceki envanter planı 10 sembol/48 ay, 394545 satır ve 960 arşiv hash doğrulaması bildiriyor; bu görevin başlangıcında fiziksel artifact ve provenance doğrulanacak. multitape.load_multitape zamanların kesişimini alıyor; bu davranış eksik barları saklayabilir. Funding interval varsayımı 8h; portföy enstrüman mapping dört sembolle sınırlı.

Mevcut yüzey: `v8-next/src/v8_next/evaluation/multitape.py`, `v8-next/src/v8_next/evaluation/store.py`, `v8-next/src/v8_next/adapters/catalog_tape.py`, `v8-next/src/v8_next/adapters/funding_history.py`, `v8-next/src/v8_next/adapters/portfolio_backtest.py`

Reuse: MultiTape, load_multitape; ResearchStore, DatasetWindowRecord, BurnRecord, HoldoutRecord; catalog_inventory, build_catalog

Bağımlılıklar: NONE

Test başlangıç yüzeyi: `v8-next/tests/test_catalog_f6.py`, `v8-next/tests/test_research_store.py`, `v8-next/tests/test_evaluation_lineage.py`

## NX02
evaluation/runner.py ilk position_id eşleşmesini yeniden kullanıyor, parse hatasını sıfıra çevirebiliyor ve açık/kapalı sonuçları farklı birimlerle birleştiriyor. economic_benchmark.pair_positions zaten instrument+position_id ve tüketilen kapanış cursorü kullanıyor; bunu yeniden icat etme.

Mevcut yüzey: `v8-next/src/v8_next/evaluation/runner.py`, `v8-next/src/v8_next/evaluation/economic_benchmark.py`, `v8-next/src/v8_next/adapters/portfolio_equity.py`, `v8-next/src/v8_next/adapters/accounting_replay.py`, `v8-next/src/v8_next/adapters/settlements.py`

Reuse: pair_positions, strategy_series_from_engine, portfolio_series_from_engine; EquityMark, native_equity, aligned_native_equity; replay_frozen_campaigns

Bağımlılıklar: NONE

Test başlangıç yüzeyi: `v8-next/tests/test_portfolio_benchmark.py`, `v8-next/tests/test_report_accounting.py`, `v8-next/tests/test_equity.py`, `v8-next/tests/test_settlements.py`, `v8-next/tests/test_d153_runner_report.py`

## NX03
ForwardPlan/freeze_forward_plan/bind_forward_data gerçek saatle prospective ön-kayıt ve tek seferlik veri binding yapıyor, BTC instrument kısıtı var. Bunları geriye dönük koşular için gevşetmek geleceğe sızıntı yaratır.

Mevcut yüzey: `v8-next/src/v8_next/evaluation/forward_plan.py`, `v8-next/src/v8_next/evaluation/store.py`, `v8-next/src/v8_next/app/observe.py`, `v8-next/src/v8_next/evaluation/multitape.py`

Reuse: ForwardPlan, freeze_forward_plan, bind_forward_data; ResearchStore, TrialRecord, DatasetWindowRecord; PaperConfig

Bağımlılıklar: NX01

Test başlangıç yüzeyi: `v8-next/tests/test_forward_plan.py`, `v8-next/tests/test_policy_identity.py`, `v8-next/tests/test_research_store.py`

## NX04
Yerel V87_V8NEXT_IMPLEMENTATION_PLAN D11 incelemesi zincirin sağlam, verifierın hatalı olduğunu bildiriyor: v2 etiketli geçmişte 10/12 alan ve sonra 13 alan canon kullanılmış. Bu bulgu özgün ledger bytes ve üretici revisionıyla doğrulanmalı; BROKEN @0 otomatik veri kaybı sayılmamalı.

Mevcut yüzey: `v8-next/src/v8_next/evaluation/benchmark_receipt.py`, `v8-next/src/v8_next/evaluation/parity.py`

Reuse: BenchmarkLedger, LedgerEntry, BenchmarkReceipt; ArtifactBinding (evaluation/parity.py), GateState, GateVector

Bağımlılıklar: NONE

Test başlangıç yüzeyi: `v8-next/tests/test_execution_scoring_link.py`, `v8-next/tests/test_d153_runner_report.py`

## NX05
app/benchmark.py kısa 500 bar yükleme kullanıyor; app/portfolio.py default 385 bar. D153 BenchmarkRunner ile economic portfolio yolu ayrı. Catalog/BacktestNode, native execution telemetry ve shared-account engine zaten var.

Mevcut yüzey: `v8-next/src/v8_next/app/benchmark.py`, `v8-next/src/v8_next/app/portfolio.py`, `v8-next/src/v8_next/evaluation/runner.py`, `v8-next/src/v8_next/evaluation/economic_benchmark.py`, `v8-next/src/v8_next/adapters/catalog_tape.py`, `v8-next/src/v8_next/adapters/portfolio_backtest.py`, `v8-next/src/v8_next/adapters/execution_telemetry.py`

Reuse: BenchmarkCase, BenchmarkRunResult, build_input_binding; RunIdentity, EconomicReceipt; CatalogBuild, run_portfolio_backtest, trade_signature, persist_execution_telemetry

Bağımlılıklar: NX02, NX03, NX04

Test başlangıç yüzeyi: `v8-next/tests/test_d153_runner_report.py`, `v8-next/tests/test_portfolio_benchmark.py`, `v8-next/tests/test_catalog_f6.py`, `v8-next/tests/test_execution_integration.py`

## NX06
economics/grammar.py beş policy sunuyor; economics/protection.py CampaignProtection/protection_at squeeze için 336 bar expiry içeriyor. adapters/expert_strategy.py ayrı fixed bracket yoluna sahip. experts/squeeze_swing diye mevcut Python modülü yok.

Mevcut yüzey: `v8-next/src/v8_next/economics/grammar.py`, `v8-next/src/v8_next/economics/protection.py`, `v8-next/src/v8_next/economics/decisions.py`, `v8-next/src/v8_next/adapters/expert_strategy.py`, `v8-next/src/v8_next/adapters/portfolio_backtest.py`, `v8-next/src/v8_next/domain/config.py`

Reuse: CampaignProtection, protection_at, grammar_opportunity; ExpertStrategyConfig, ExpertEnsembleStrategy; SleeveSpec, PaperConfig

Bağımlılıklar: NX02, NX03

Test başlangıç yüzeyi: `v8-next/tests/test_squeeze_protection.py`, `v8-next/tests/test_campaign_protection.py`, `v8-next/tests/test_grammar.py`, `v8-next/tests/test_portfolio_benchmark.py`

## NX07
alignment/family/reality_check/deflated_sharpe/overfitting modülleri ve ResearchStore zaten var. gate_resolution G5 fallbackları ile economic_benchmark statistics yolunun gerçek trial ailesine bağlanması incelenmeli; sentetik positive/negative control fonksiyonları ekonomik kanıttan ayrılmalı.

Mevcut yüzey: `v8-next/src/v8_next/evaluation/alignment.py`, `v8-next/src/v8_next/evaluation/family.py`, `v8-next/src/v8_next/evaluation/reality_check.py`, `v8-next/src/v8_next/evaluation/deflated_sharpe.py`, `v8-next/src/v8_next/evaluation/overfitting.py`, `v8-next/src/v8_next/evaluation/economic_benchmark.py`, `v8-next/src/v8_next/evaluation/store.py`, `v8-next/src/v8_next/evaluation/gate_resolution.py`

Reuse: IntervalLoss, paired_differentials, family_losses, compare_family; DSRPlan, CSCVPlan, TrialRecord, ResearchStore; run_statistics

Bağımlılıklar: NX03, NX05, NX06

Test başlangıç yüzeyi: `v8-next/tests/test_loss_alignment.py`, `v8-next/tests/test_family.py`, `v8-next/tests/test_deflated_sharpe.py`, `v8-next/tests/test_reality_check.py`, `v8-next/tests/test_overfitting.py`, `v8-next/tests/test_gate_resolution.py`

## NX08
runner abstention denominator28 ve coverage0.60; certificate varsayılan robustness50/economic60; scoring dört sabit domain ve proxy tavana sahip. GATE_DESCRIPTORS etiketleri ile operational resolver alanları tutarlı ele alınmalı; sadece skor formülü değiştirmek yeterli değil.

Mevcut yüzey: `v8-next/src/v8_next/evaluation/scoring.py`, `v8-next/src/v8_next/evaluation/certificate.py`, `v8-next/src/v8_next/evaluation/gate_resolution.py`, `v8-next/src/v8_next/evaluation/benchmark_receipt.py`, `v8-next/src/v8_next/evaluation/runner.py`

Reuse: CapabilityDomain, BoundedScore, CapabilityScoreCalculator; GateState, GateDescriptor, GateVector.readiness, PolicyCertificate.generate; ArtifactBinding

Bağımlılıklar: NX04, NX05, NX07

Test başlangıç yüzeyi: `v8-next/tests/test_execution_scoring_link.py`, `v8-next/tests/test_gate_resolution.py`, `v8-next/tests/test_d153_runner_report.py`

## NX09
Önceki burn incelemesi son12ayın zaten kullanıldığını ve protected final kalmadığını bildiriyor. Dört yıllık veri dört yıllık unseen test değildir. Daha geniş pencere daha yüksek skor/getiri garantisi değildir.

Mevcut yüzey: `v8-next/src/v8_next/evaluation/store.py`, `v8-next/src/v8_next/evaluation/forward_plan.py`, `v8-next/src/v8_next/evaluation/economic_benchmark.py`, `v8-next/src/v8_next/app/portfolio.py`

Reuse: ResearchStore, TrialRecord, HoldoutRecord; RunIdentity, EconomicReceipt; frozen plan ve NX07 family manifesti

Bağımlılıklar: NX01, NX03, NX05, NX06, NX07, NX08

Test başlangıç yüzeyi: `v8-next/tests/test_forward_plan.py`, `v8-next/tests/test_portfolio_benchmark.py`, `v8-next/tests/test_research_store.py`

## NX10
ForwardPlan, public stream replay/recovery ve EconomicPaperAdapter mevcut. shadow_ingest.load_shadow_fills source=live ve birkaç kolon kontrolünden LIVE_VENUE_SETTLED etiketi üretebiliyor; yerel dosyanın bu etiketi gerçek venue settlement kanıtı değildir.

Mevcut yüzey: `v8-next/src/v8_next/evaluation/forward_plan.py`, `v8-next/src/v8_next/evaluation/stream_replay.py`, `v8-next/src/v8_next/economics/stream_observation.py`, `v8-next/src/v8_next/adapters/economic_paper.py`, `v8-next/src/v8_next/adapters/shadow_ingest.py`, `v8-next/src/v8_next/app/forward.py`, `v8-next/src/v8_next/app/stream_run.py`, `v8-next/src/v8_next/evaluation/gate_resolution.py`

Reuse: freeze_forward_plan, bind_forward_data, replay_stream, restore_stream; StreamObservations, EconomicPaperAdapter, load_shadow_fills

Bağımlılıklar: NX03, NX05, NX06, NX08

Test başlangıç yüzeyi: `v8-next/tests/test_forward_plan.py`, `v8-next/tests/test_stream_replay.py`, `v8-next/tests/test_paper_recovery.py`, `v8-next/tests/test_portfolio_benchmark.py`

## NX11
Eski SB issue paketi yanlış Rust kapsamındaydı. Yeni paket v8-next Python/Nautilus üzerinde teknik doğruluk ve swing benchmark yapıyor; ekonomik sertifika ayrı kanıt koşullarına bağlı.

Mevcut yüzey: `v8-next/src/v8_next/evaluation/benchmark_receipt.py`, `v8-next/src/v8_next/evaluation/certificate.py`

Reuse: BenchmarkReceipt, GateVector, PolicyCertificate; mevcut docs/contracts ve migration kayıtları

Bağımlılıklar: NX01, NX02, NX03, NX04, NX05, NX06, NX07, NX08, NX09, NX10

Test başlangıç yüzeyi: `v8-next/tests/test_d153_runner_report.py`, `v8-next/tests/test_execution_scoring_link.py`

## NX00
#410–#420 yanlış Rust implementation kapsamı nedeniyle withdrawn ediliyor. NX01–NX11 kaynak taramasına dayanan yerine-geçen pakettir; bu epic tek Hermes goal ile yürütme içindir.

Mevcut yüzey: `v8-next/src/v8_next/evaluation/runner.py`, `v8-next/src/v8_next/evaluation/economic_benchmark.py`, `v8-next/src/v8_next/evaluation/store.py`, `v8-next/src/v8_next/evaluation/benchmark_receipt.py`

Reuse: Alt issue reuse sözleşmeleri; BenchmarkRunner, EconomicReceipt, ResearchStore, BenchmarkLedger

Bağımlılıklar: NX01, NX02, NX03, NX04, NX05, NX06, NX07, NX08, NX09, NX10, NX11

Test başlangıç yüzeyi: `v8-next/tests/test_d153_runner_report.py`, `v8-next/tests/test_portfolio_benchmark.py`
