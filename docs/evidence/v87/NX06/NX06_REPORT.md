# NX06 (#427) — Swing baseline'ı mevcut grammar ve squeeze protection ile bağla

Durum: **R1–R6 teknik kabul.** Ölçüm **karar-düzlemi diagnostik**tir: gerçek bar, gerçek
taker ücreti; **engine fill'i değil**, venue settlement değil. `NO_ECONOMIC_CLAIM`.
Getiri **pozitif çıkmadı** ve bu bir başarısızlık değildir — bu iş için kabul ölçütü
"family çalışıyor, ayrımı ve sınırları kanıtlı" olmaktır.

## 0. Sözleşme (yeni: `v8-next/src/v8_next/economics/swing_baseline.py`)

- Aile **ön-kayıtlı**: `SWING_FAMILY_VERSION = v87-swing-family-v1`, üç politika —
  `cash` (maruziyet yok), `causal_trend` (mevcut `trend-continuation-v2` +
  `timeout-only-v1`), `plain_swing` (mevcut `range-breakout-48-v1` + mevcut
  `squeeze:baseline:v2`). Kimlik = grammar+protection+horizon+ortak sözleşme hash'i.
- **İki ayrı süre karıştırılmaz**: episode'un kendi TTL'i (`opportunity.expires_ns`) ve
  açık-trade expiry'si (`PROTECTION_TTL_BARS` ailesi). Ölçülen: squeeze 336 bar (=14 gün),
  timeout-only policy hiç expiry damgalamaz (TTL'i episode verir).
- **Nedensellik**: karar yalnızca karar anında mevcut barlardan üretilir; sonuç yalnızca
  karar barından **sonraki** barlardan hesaplanır; karar anındaki/öncesindeki bar geri
  oynatılırsa `ValueError`.
- **Belirsizlik pozisyona karşı çözülür**: aynı bar hem stop hem target'a değerse **stop**
  alınır; açılışı stop'un ötesinde olan bar **açılışta** dolar (stop fiyatında değil).
- Ortak maliyet/sermaye sözleşmesi her politikada birebir aynı; `funding` ve `slippage`
  **sıfır değil**, `MISSING_NOT_FED_TO_THIS_PATH` / `NOT_MODELLED_IN_REPLAY` olarak yazılır.

## 1. R → exact check → artifact matrisi

| R | Değişiklik | Exact check | Ölçülen sonuç |
|---|---|---|---|
| R1 | Mevcut grammar + `protection_at` + `CampaignProtection` doğrudan çağrılıyor; TTL/expiry ayrımı ayrı alanlar | `pytest -q v8-next/tests/test_swing_baseline_nx06.py` | 14 passed — squeeze expiry 336 bar; timeout-only `None`; `squeeze:baseline:v2` aile anahtarı (`split(":")`) ile TTL tablosuna çözülür |
| R2 | Ön-kayıtlı 3 politikalı aile, tek ortak risk/maliyet sözleşmesi | aynı dosya + `family_registry.json` | `family_registry.json` **ölçümden önce** yazıldı (`registered_before_measurement: true`, içinde sonuç yok) |
| R3 | Tutuş süreleri bar + saat/gün olarak ölçülüyor; 336 bar çevrimi doğrulandı | `test_squeeze_expiry_is_336_bars_in_hours_and_days`, `test_opportunity_ttl_bars_is_measured_against_the_bar_duration` | 336 bar = 336.0 h = 14.0 gün (1h bar); 4h bara ölçeklenince TTL de ölçeklenir |
| R4 | Karar-düzlemi olay sırası (bar-bar, hindsight yok, gap→açılış, çift-değme→stop) **+** engine olay sırası mevcut native testlerle | `test_stop_is_taken_when_one_bar_touches_both_barriers`, `test_gap_through_the_stop_fills_at_the_open_not_at_the_stop_price`, `test_replay_refuses_a_bar_at_or_before_the_decision_instant`; engine: `test_native_engine.py::test_native_bracket_closes_and_cancels_sibling` + `::test_expiry_closes_native_position_and_charges_exit_fee` | 14 passed + **5 passed** (bracket 4 parametre + expiry) — engine bracket'ta eş kardeş emir CANCELED |
| R5 | Turnover, gross/net, fee, maruziyet, tutuş dağılımı, açık risk raporlanıyor; kapasite iddiası yok | `comparative_receipt.json` | aşağıdaki tablo; `open_risk_return` cutoff'ta açık kalan kampanya için ayrı alan |
| R6 | Aynı gerçek pencerede karşılaştırmalı receipt + fiziksel artifact hash'leri | `python v8-next/tools/nx06_swing_baseline.py` | `family_registry.json` `d8aaf1e8…`, `comparative_receipt.json` `b51e4e53…`; receipt registry hash'ini taşır |

## 2. Ölçülen sonuç (gerçek tape, 2025-01-01→2025-02-01, 744 bar, BTCUSDT-PERP.BINANCE, +96 bar warmup)

| Politika | Kampanya | Çıkışlar | Maruziyet | Tutuş medyan | Gross | Fee | **Net** | Turnover |
|---|---|---|---|---|---|---|---|---|
| `cash` | 0 | — | 0.000 | — | 0.000000 | 0.000000 | **0.000000** | 0.00 |
| `causal_trend` | 29 | 28 EXPIRY, 1 açık | 0.806 | 24 bar | +0.047861 | 0.029000 | **+0.018861** | 0.58 |
| `plain_swing` | 31 | 30 STOP, 1 TARGET | 0.150 | 1 bar | −0.000357 | 0.031000 | **−0.031357** | 0.62 |

Okuma notları (tahmin değil, ölçüm):
- Sayılar **birim notional başına fraksiyonel getiri toplamı**dır; portföy getirisi değildir.
- `plain_swing`'de squeeze koruması çok sıkı çalışıyor: 31 kampanyanın 30'u stop, medyan
  tutuş 1 bar → maliyet gross'u yiyor (gross ≈ 0, net −0.031). **Bu bir sonuçtur**, eleme
  gerekçesi değildir; minimum işlem hedefi için emir zorlanmadı, çıkış gevşetilmedi.
- `causal_trend`'de 28/29 çıkış timeout (24 bar TTL): koruma expiry damgalamadığı için
  episode TTL'i tek sözleşme.
- `cash` sıfırları **inşa gereği**dir ve notu "the comparison floor, not a measurement"
  diyerek bunu açıkça yazar; ölçülmüş bir sıfır gibi sunulmaz.

## 3. Sınırlar / pending (uygulama sürdü, blokaj yok)

- Sonuçlar **engine fill'i değil**: karar-düzlemi replay. Engine dolum farkı (kısmi dolum,
  book etkisi) bu iş kapsamında iddia edilmedi; family'nin engine'e bağlanması NX09
  (uzun koşu) işinin kapsamıdır.
- Native engine'de **gap-through-stop** vakası parametrik olarak test edilmedi; mevcut
  parametre seti stop/target sırasını ve kardeş emir iptalini kapsıyor. Bu kalem
  pending evidence olarak kayıtlıdır (yanlış bir "kapsandı" iddiası yazılmadı).
- `funding` ve `slippage` bu yolda **modellenmiş değil** (sıfır sayılmadı). Mark price
  yokluğu kayıtlıdır (NX01 envanteri).
- Kapasite/ölçek iddiası yok: kalibrasyon ve mark price olmadan "ölçülmüş kapasite"
  denmez.
