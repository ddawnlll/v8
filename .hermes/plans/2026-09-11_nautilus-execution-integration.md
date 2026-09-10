# Plan: NautilusTrader execution katmanının v8-next'e tam entegrasyonu

**Tarih:** 2026-09-11
**Amaç:** v8-next'te gerçek execution modellemesi kurmak; NautilusTrader'ın
fill/latency/fee/margin/likidite yeteneklerini kullanmak ve üretilen execution
kanıtını benchmark gate'lerine + domain skorlarına bağlamak.

## Mevcut durum (kanıtlı)

- `nautilus-trader==2.0.0rc4` kurulu ve kullanılıyor (`BacktestEngine`).
- `portfolio_backtest.py:158` `add_venue(...)` çağrısı **fill_model / fee_model /
  latency_model geçmiyor** → Nautilus varsayılanı: bar fiyatından, tam boyut,
  sıfır slippage, sıfır latency.
- `expert_strategy.py:390` `fill_model=None, latency_model=None` parametreleri
  var ama hiç bağlanmamış.
- `app/paper.py:209` `UtilityInputs(fees=None, spread=None, slippage=None,
  funding_cost=None, calibration_receipt=None)` → `utility_admission()` her
  zaman `REJECTED_MISSING_CALIBRATION`.
- Sonuç: `ExecutionFidelity` domaini gerçek execution yerine pnl Sharpe
  proxy'sinden türetiliyor; `g8=UNRUN_NO_VENUE_ACCOUNT`.

## Kullanılacak Nautilus API'si (kurulu sürümden doğrulandı)

Import yolu: `nautilus_trader.execution`

**Fill modelleri** (hepsi `(prob_fill_on_limit: float, prob_slippage: float,
random_seed: int | None)`):
`DefaultFillModel`, `OneTickSlippageFillModel`, `TwoTierFillModel`,
`ThreeTierFillModel`, `SizeAwareFillModel`, `VolumeSensitiveFillModel`,
`LimitOrderPartialFillModel`, `ProbabilisticFillModel`, `BestPriceFillModel`,
`MarketHoursFillModel`

**Latency:** `StaticLatencyModel(base_latency_nanos, insert_latency_nanos,
update_latency_nanos, cancel_latency_nanos)`

**Fee:** `MakerTakerFeeModel()` (instrument maker/taker kullanır),
`FixedFeeModel(commission, charge_commission_once=None)`

**`add_venue` parametreleri (tam):** `margin_model, fill_model, fee_model,
latency_model, modules, book_type, routing, reject_stop_orders,
support_gtd_orders, support_contingent_orders, use_position_ids,
use_random_ids, use_reduce_only, use_message_queue, use_market_order_acks,
bar_execution, bar_adaptive_high_low_ordering, trade_execution,
liquidity_consumption, queue_position, allow_cash_borrowing, frozen_account,
oto_trigger_mode, price_protection_points, liquidation_enabled,
liquidation_trigger_ratio, liquidation_cancel_open_orders`

Şu an kullanılmayanlar: `liquidity_consumption=False`, `queue_position=False`,
`bar_adaptive_high_low_ordering=False`, `use_market_order_acks=False`,
`price_protection_points=None` + üç model de `None`.

**Telemetri:** `BacktestEngine.generate_order_fills_report()`.

## Determinizm kuralı (pazarlık dışı)

- Her fill modeli `random_seed`'e pinlenir; profil digest'i receipt'e girer.
- Aynı tape + aynı profil → **bit-bit aynı** fill signature ve decision signature.
- Bu, G2 (`DETERMINISM_RERUN_NOT_PERFORMED`) için de gerçek kanıt üretir.

## Uygulama adımları

1. **`adapters/execution_models.py`** — `ExecutionProfile` (frozen) + `PROFILES`
   registry (`baseline`, `realistic`, `volume_aware`) + model builder'lar +
   `venue_kwargs(profile)` + `profile_digest(profile)`.
2. **`adapters/portfolio_backtest.py`** — `execution_profile` parametresi,
   `add_venue(**venue_kwargs)`, fill telemetrisi, `fill_signature`,
   slippage/shortfall/latency/komisyon hesabı, sonuca `execution` bloğu.
3. **`economics/decisions.py` + `app/paper.py`** — `UtilityInputs` friction
   alanları **ölçülen** execution'dan doldurulur; ölçüm yoksa `None` kalır
   (fail-closed korunur).
4. **Benchmark bağlantısı** — runner `gate_metrics["execution"]` yazar;
   `ExecutionFidelity` domaini ölçülen shortfall'dan beslenir.
5. **Deterministik testler** — profil digest kararlılığı, aynı seed → aynı fill,
   gerçek tape'te iki koşu → aynı signature; sentetik yalnızca MECHANICS ONLY.
6. **Doğrulama** — gerçek quad tape ile D-153 battery + gate/skor çıktısı.

## Kabul kriterleri

- `add_venue` artık `fill_model`/`fee_model`/`latency_model` alıyor (None değil).
- Sonuçta `execution` bloğu: profil adı, digest, fill sayısı, ortalama slippage
  (bps), implementation shortfall, latency (ns), toplam komisyon.
- Deterministik test: aynı girdi → aynı `fill_signature` (iki bağımsız koşu).
- `UtilityInputs` ölçüm varsa dolu, yoksa `None` (asla uydurma).
- Gerçek tape koşusunda gate/skor çıktısı execution kanıtı içeriyor.
- Tüm testler geçiyor; sentetik veri yalnızca MECHANICS ONLY işaretli.

## Sınırlar (dürüst)

- G8'in *venue account* şartı simülasyonla kapanmaz; o gerçek hesap verisi ister.
  Nautilus sandbox/live adapter'ları yol sağlar ama bu planın kapsamı dışında.
- Katsayı uydurulmaz: kalibre edilmemiş bir slippage/latency değeri "ölçülmüş"
  diye sunulmaz; profil adı ve parametreleri açıkça raporlanır.
