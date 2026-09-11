# V8.7 → v8-next uygulama planı

Durum: TASLAK / PLAN. Bu belge uygulama değildir; hiçbir v8-next kod yolu
değiştirilmemiştir. Doğrulama durumu her bulguda ayrı işaretlidir:
`[DOĞRULANDI]` = bu planı yazan tarafından kaynak okunarak birinci elden
doğrulandı; `[İDDİA]` = yalnızca analiz dokümanından alındı, SB paketinde
yeniden doğrulanacak.

## 0. Önce sınır kararı (prerequisite, uygulanmadan hiçbir paket başlamaz)

V8.7 issue'larının hepsi şu kuralı taşıyor: *"Tüm yeni implementation/test
v8-core içinde Rust; v8-next yalnızca referans."* `AGENTS.md` §1 de aynı şeyi
söylüyor. Bu plan o kuralın **bu kapsam için** supersede edilmesini gerektirir.

Bunu meşru kılan şey, `v8-next/AGENTS.md`'nin kendi cümlesidir:

> "Do not add, edit, refactor, or extend its implementation or tests **unless the
> owner explicitly reactivates `v8-next/` in a later instruction**."

Yetki kaynağı: kullanıcının 2026-09-11 tarihli açık talimatı ("bunu v8-next'e
nasıl implement ederiz"). Yetki sırası (reset §1) bunu destekler: *current
explicit project objective* en üstte; teknik şartname ondan sonra gelir.

**#409 tam olarak bu kaydın eksikliğinden açıldı**: `v8-next/AGENTS.md` bir
zamanlar Python'u yeni ürün yolu ilan ediyordu, sonra "ruff clean" etiketli bir
commit'in içinde tersine çevrildi — karar kaydı olmadan. Şimdi ters yönde
yapılacak şey aynı hatayı tekrarlamamak: **kayıtla.**

Enact edilecek adımlar (sırayla, hepsi tek seferde):

1. `docs/decisions/DECISION_REGISTER.md`'ye tarama yapılıp **çakışmasız yeni D
   numarası** ile: "V8.7 swing benchmark iş paketleri v8-next Python üzerinde
   yürütülür; Rust-only kuralı bu kapsam için tarihseldir." (EN + `docs/tr/`).
2. `v8-next/AGENTS.md`'ye tek paragraf: reactivation kaydına atıf + kapsam
   (V8.7 SB01–SB10) + yürürlükte kalan kısıtlar (aşağıdaki §5 listesi aynen).
3. `AGENTS.md` §1'e tek satır çapraz atıf: Rust-first beyanı genel kapsam için
   durur; V8.7 swing benchmark kapsamı D-xxx ile v8-next'tedir.
4. #409'a kanıtla kapanış yorumu; #420'ye durum tablosu; #411–#419 gövdelerinde
   **Kural 1** ("v8-core Rust") metni yeni kapsa göre güncellenir; R1–R6
   ölçütleri ve kanıt şartları **değişmez** (onlar dile bağlı değil).
5. Kendi Rust çıktımın durumu: SB01 araç+artifact'ları committed kalır (ölçüm
   geçerli, §1). `v8-core/src/trade_lifecycle.rs` (SB02 taslağı) **park edilir,
   commit edilmez** — v8-next'e Python'da yazılacak; Rust dosyası silinmez, sahibinin
   kararına bırakılır.

## 1. SB01 zaten teslim edildi ve ölçümleri dilden bağımsız

Commit'ler `bc1a5aed`, `92c64b04`, `73dcfbb8`. Bunlar tape hakkındaki **olgu**
ölçümleridir; hangi dilde uygulama yapıldığından etkilenmez:

- `research/tape/multi-1h-4y`: 10 sembol × 48 ay, 2022-07-01→2026-06-30,
  394.545 satır, **960/960 arşiv üç yollu hash eşleşmesi**, kline 0 boşluk /
  0 duplicate, tam 1h grid.
- **Mark price yok** (yalnızca kline + fundingRate kanalı).
- **SOLUSDT funding heterojen**: `{8h: 4357, 4h: 2, 2h: 99}` — analiz §8'in
  "sabit 8 saat varsayımı tüm tarihi kapsamaz" uyarısı bu tape'te **ölçülmüş**.
- Burn haritası: parity fixture'ları ilk 25.000 satırı okumuş (→ ilk ~3 ay
  `BURNED_DIAGNOSTIC`); 2022-10-01..2025-06-30 `USAGE_UNKNOWN`; **2025-07-01..
  2026-06-30 `BURNED_DIAGNOSTIC`** (`quad-1h-12m` + `sol-dev` + `btcusdt-1h-12m`).
- **Sonuç: dört yıllık pencerede korunmuş final yok.** Ay 37–48 = bugünkü
  `quad-1h-12m` ile aynı ay-ay pencere → SB08 finali açılmaz.
- Rust çağrı yolu: dört yıllık tape hiçbir Rust yoluna bağlı değil; resmî
  evaluator kapalı (`BLOCKED_REGISTERED_BENCHMARK_EVALUATOR_REQUIRED`).

v8-next için eklenecek tek SB01 işi: v8-next koşularının **aynı veri kimliğine**
bağlanması (aşağıda SB04 manifesti). Envanteri üreten araç Rust kalabilir; o bir
ölçüm aracıdır, ürün yolu değildir.

## 2. v8-next'te birinci elden doğrulanmış kusurlar

Hepsi bu planın yazarı tarafından kaynak okunarak doğrulandı.

| # | Yer | Kusur | Durum |
|---|---|---|---|
| D1 | `evaluation/runner.py:229-231` | `next((c for c in closed_positions if c["position_id"] == pos["position_id"]))` — **ilk kapanışı** eşler; venue `position_id`'yi yeniden kullanırsa tek kapanış birden çok açılışa atfedilir | `[DOĞRULANDI]` |
| D2 | `evaluation/runner.py:236-237` | `except (ValueError, TypeError): pnl_series.append(0.0)` — **parse hatası sıfır gözlemi** olur | `[DOĞRULANDI]` |
| D3 | `evaluation/runner.py:242-243` | Aynı seriye USDT tutarı ile **boyutsuz** `(last_close-entry)/entry` karışır | `[DOĞRULANDI]` |
| D4 | `evaluation/runner.py:223` | `total_trades = len(opened_positions)` — tamamlanmış round-trip değil, **açılış** sayısı | `[DOĞRULANDI]` |
| D5 | `evaluation/runner.py:246` | Abstain paydasında **sabit 28** expert | `[DOĞRULANDI]` |
| D6 | `runner.py:249` + `scoring.py:91-92` + `certificate.py:70` | `coverage_factor = 0.60` sabit ve **hem cap hem readiness içinde** uygulanıyor | `[DOĞRULANDI]` |
| D7 | `evaluation/scoring.py:158-163` | 10 alan bildirilir, **4'ü** hesaplanır; `op_val = clip(1-0.3a, .10, .60)` her zaman **0.60**; `def_val` sabit 0.15; `micro_val` bar sayısıyla artar; bantlar sabit çarpan; `effective_sample_size = ham n` | `[DOĞRULANDI]` |
| D8 | `evaluation/certificate.py:56-65` + `runner.py:499` | Eksik Minerva→**50**, eksik projection→**60** readiness çarpımına *sayı* olarak giriyor; runner certificate'ı ikisi de yokken üretiyor | `[DOĞRULANDI]` |
| D9 | `app/benchmark.py:92` + `economic_benchmark.py:44` | `load_tape_candles(tape_file, limit=500)`; `OOS_FIT_BARS = 350  # chronological split of the 500-bar window; fixed, never relabeled` → 150 saat ≈ **6,25 gün** OOS; 14 güne kadar sürebilen swing işlemi bu pencerede kapanamaz | `[DOĞRULANDI]` |
| D10a | `gate_resolution.py:444-468` | G5 kendi serisi < 20 ise **başka tape'in** (`btcusdt-1h-12m`, `DEFAULT_TAPE_PATH`) rejimlerini koşup realized PnL'leri örnek olarak alıyor ve `/10000.0` ile ölçekliyor; `sample_source = "regime_fallback"` olarak işaretleniyor | `[DOĞRULANDI]` |
| D10b | `gate_resolution.py:500-534` | "Varyantlar" tek seriden aritmetik: `r-0.0001`, `0.95r`, `r-0.0002`; `effective_independent_trials = num_trials` (varsayılan **4**); `independence_basis` metni "preregistered" diyor ama kayıtlı gerçek deneme yok | `[DOĞRULANDI]` |
| D10c | `gate_resolution.py:546-575` | `passed = dsr_conf >= 0.95 and bonf_p <= 0.05`; **WRC hesaplanıp metriklere yazılıyor ama karara girmiyor**; üstelik WRC baseline'ı sıfır-kayıplı seri | `[DOĞRULANDI]` |
| D10d | `gate_resolution.py:609-664` | G6: IS ilk 2/3, OOS son 1/3, `retention = oos_profit / is_profit >= 0.60`. Eşit günlük kâr hızında OOS kârı IS'in ~yarısı olur → tutarlı bir strateji bu eşiği **yapısal olarak** geçemez | `[DOĞRULANDI]` |
| D10e | `gate_resolution.py:689-784` | G7 "prospective shadow": girdi `candles[-100:]` (tarihsel); e-process ve drift **yalnızca fiyattan** türetiliyor (`ret=(px-ref_mean)/ref_mean`, `update=1+0.1*tanh(ret*10)`); `decisions` sadece log'a yazılıyor, verdict'e girmiyor; `passed = 0.01 <= e_raw < 20.0 and drift < 0.15`. Yani prospektiflik kararı **fiyat dalgalanmasıyla** veriliyor, strateji davranışıyla değil | `[DOĞRULANDI]` |
| D11 | `benchmark_receipt.py:295-321` + ledger kayıtları | **Yayımlanmış ledger sağlam; "BROKEN / DIGEST_TAMPERED" bir doğrulayıcı hatasıdır.** Kanon 10→12→13 alana büyüdü ama **10→12 geçişinde sürüm damgası artırılmadı** (0–11 `v2` etiketli ama 10-alan kanonuyla yazılmış); `verify()` bugünkü 13-alan kanonunu uyguluyor ve `!= "v8.5-digest-v3"` koşulu yüzünden **v2'ye `input_binding`'i de ekliyor**. Ölçüm: seq 0–11 → 10-alan kanonu (`1c75c1a1`) ile **birebir**; seq 12 → 12-alan (`9bf0b1aa`) ile **birebir**; seq 13–18 → 13-alan (güncel) ile **birebir**. Zincir bağlantıları da sağlam (her `parent_entry_hash` = önceki `entry_hash`) | `[DOĞRULANDI]` |

**Cebirsel tavan (benim hesabım, doğrulandı):** kullanılan ağırlıklar
0.12+0.15+0.10+0.08 = 0.45; en iyi alt bantlar Exec 0.40, Ops 0.48, Def 0.105,
Micro 0.225 →
`Cap_max = 100 × 0.60 × 0.45 / (0.10/0.40 + 0.15/0.48 + 0.08/0.105 + 0.12/0.225) = 14.5338`
`Readiness_max = 14.5338 × 0.60 × 0.50 × 0.60 = 2.616`
`11.1 → 1.998` (bugünkü sayı). Bu bir performans tahmini değil, kaynak formülün
cebirsel sonucudur. Yani mevcut skor sistemi **yapısal olarak** 15'in üstüne
çıkamaz — bu, "skoru yükseltme" hedefinin baştan imkânsız olduğu anlamına gelir.

## 3. İş paketlerinin v8-next karşılıkları

Sıra korunur: SB01 → (SB02 ∥ SB03) → SB04 → SB05 → SB06 → SB07 → SB08 → SB09 → SB10.

### SB02 — muhasebe (en kritik; her şeyin önünde)
- **Yüzey:** yeni `v8_next/accounting/lifecycle.py`; düzeltme `evaluation/runner.py:225-247`.
- Yapılacak: açılış→kısmi kapanış→kapanış→reversal için **round-trip kimliği**
  (venue `position_id` kimlik *değildir*); gerçekleşen/MTM ayrı; tek para birimi;
  fee+funding bir kez; parse hatası hata (asla 0.0); `total_trades` tamamlanmış
  round-trip.
- Test: yeniden kullanılan id → iki ayrı yaşam döngüsü; eşit PnL'li farklı iki
  işlem kabul; partial/dedup/out-of-order; hesap özsermayesi uzlaşması.
- Kural: mevcut doğru mekanizmayı yeniden yazma; `pnl_series` tek birim olur.

### SB03 — zaman bölme
- **Yüzey:** `evaluation/alignment.py`, `forward_plan.py`, `outcomes.py`.
- 24/12/12 gerçek tarihlere bağlanır (SB01): geliştirme 2022-07..2024-06;
  kronolojik doğrulama 2024-07..2025-06; **final 2025-07..2026-06 INELIGIBLE**.
- Warmup puanlanmaz; label maturity; purge/embargo sonuç ufku ve funding
  heterojenliğine göre (SOLUSDT 2h/4h!); fold sınırında pozisyon taşınır;
  veri sonunda açık işlem censored (0/zarar/başarıya zorlanmaz).

### SB04 — runner, manifest, ledger, resume
- **Yüzey:** `evaluation/runner.py` (manifest), `benchmark_receipt.py`, `store.py`,
  ledger doğrulayıcı; `app/benchmark.py` profil bayrakları (SMOKE/RESEARCH/
  VALIDATION), varsayılan 500-bar'ın gizli varsayılan olmaktan çıkarılması.
- Run identity: protocol/policy, **code + dirty diff hash**, config, veri/rol/fold
  kimliği, estimator/scorer/gate sürümleri, seed, execution varsayımları.
- PARTIAL/COMPLETE ayrımı; hash + read-back sonrası atomik COMPLETE; kesilen koşu
  başarı sayılmaz.
- Ledger: **her sürüm kendi kanonunda** doğrulanır (D11); bilinmeyen sürüm fail
  closed; eski satır yeniden hash'lenip "orijinal" diye sunulmaz.

### SB05 — baseline, risk, maliyet
- **Yüzey:** `experts/squeeze_swing` (Python tarafı), `economic_benchmark.py`,
  `cash_return.py`, `equity.py`, `excess.py`, `reference.py`.
- Sade incumbent + risk hedefli simple trend (primary), cash/buy-hold/equal-weight
  ikincil; aynı risk politikası hash'i iki kolda; funding **olay zamanlı** ve
  kapsamı görünür; eksik mark/funding'de "fully cost-adjusted" iddiası yok;
  intrabar stop/target belirsizliği raporlanır.

### SB06 — trial ailesi ve istatistik
- **Yüzey:** `evaluation/family.py`, `multitest.py`, `multitape.py`,
  `deflated_sharpe.py`, `reality_check.py`, `overfitting.py`, `selection_estimates.py`.
- Gerçek denenmiş/terk edilmiş denemeler kaydedilir; **kaydırılmış champion
  varyantları trial sayılmaz**; ortak zaman ekseni; USDT/yüzde karışmaz; hangi
  testin hangi kararı kontrol ettiği yazılır; uygulanamayan yöntem gerekçeli
  UNRUN; sample adequacy ve efektif n; **başka tape'e fallback yok** (D10).

### SB07 — scorer ve gate
- **Yüzey:** `evaluation/scoring.py` (yeniden yazım), `certificate.py`,
  `gate_resolution.py`, `claims.py`.
- Ölçülmeyen alan **puan almaz** ve eksik alan diğer ağırlıkları yeniden
  ölçekleyerek gizlenmez; aggregate UNAVAILABLE olabilir. **Eksik robustness/
  economic → readiness UNAVAILABLE, 50/60 değil** (D8). Coverage tek kez (D6).
  Eski 0–100 serisi ile yeni seri ayrı kimlik/etiket taşır. Gate kimliği
  semantic_id + schema sürümü; Missing/Unknown/Blocked PASS'a çevrilemez; skor
  AuthorityFirewall'ı aşamaz.

### SB08 — dondurulmuş walk-forward
- Seçim/refit bütçesi, aday ailesi (≤3 policy) ve comparator WF1 öncesi donar;
  dört fold kronolojik; tüm aday sonuçları ve **negatif** sonuçlar kayıtlı;
  ablation yalnızca preregistered ailede; final **açılmaz** (SB01: BURNED) →
  teslimat `INELIGIBLE_EVIDENCE` + no-final gerekçesi.

### SB09 — prospektif shadow
- **Yüzey:** public capture + `shadow` yolu; checkpoint/dedup/late-data.
- Freeze wall-clock sonrası gerçek `receive/available/decision` zamanları;
  tarihsel replay prospektif sayılmaz (G7/D10); sınırlı gerçek public smoke;
  altyapı kabulü ile ekonomik yeterlilik ayrı; uzun birikim UNDERPOWERED kalır.

### SB10 — teknik sürüm
- R# izlenebilirlik matrisi, EN/TR karar+sözleşme, IMPLEMENTATION_LAYOUT,
  CHANGELOG, iki monograph (`tools/build_monograph.py` ile, tekrarlanabilir hash);
  ekonomik sonuç teknik tamamlanmadan **ayrı**; `NO_ECONOMIC_CLAIM` korunur.

## 4. Doğrulama komutları (v8-next, `v8-next/AGENTS.md` kaynaklı)

```sh
uv sync --project v8-next --locked --extra dev
uv run --project v8-next --extra dev ruff check v8-next/src v8-next/tests
uv run --project v8-next --extra dev mypy v8-next/src
uv run --project v8-next --extra dev pytest -q v8-next/tests/<ilgili_test>.py
```

Milestone/release sınırında ayrıca repo denetimleri:
`.venv/bin/python tools/audit_python_boundary.py`,
`python3 tools/audit_synthetic_leakage.py`, `python3 tools/audit_economic_claim.py`.

Dört yıllık ağır koşu her küçük değişiklikte çalıştırılmaz: önce smallest
discriminating check, sonra milestone koşusu.

## 5. Değişmeyen kısıtlar (reactivation bunları gevşetmez)

- Değerlendirme iddiası taşıyan testler **gerçek tape** ister; tape yoksa skip.
  Sentetik mum yalnızca `MECHANICS ONLY` mekanik testlerde, sıfır değerlendirme
  ağırlığıyla.
- Eksik kalibrasyon/funding/timestamp/istatistik **eksik kalır**; koşuyu başarılı
  göstermek için trade zorlanmaz.
- Tarihsel kapanış-zamanı "labeled diagnostic model"tir, ölçülmüş erişilebilirlik
  değildir. Simüle muhasebe gerçek venue nakit uzlaşması değildir.
- Private order client / transfer / hesap değişikliği / canlı aktivasyon yok;
  public capture ve yerel paper simülasyon serbest.
- `src/v8/` ve `tests/` (frozen oracle) değişmez. Kullanıcının kirli ağacındaki
  ilgisiz değişiklikler korunur.

## 6. Açık uçlar

- D11 çözüldü: düzeltme **doğrulayıcıda** yapılır, kayıtlarda değil. Eski satırlar
  yeniden hash'lenmeyecek, "yeniden mühürlenmeyecek" ve tamper diye
  etiketlenmeyecek; `verify()` gerçek kanon kümesine göre sürüm-farkında olacak ve
  bundan sonraki kanon değişimleri **yeni sürüm damgası** alacak. Bu SB04'ün işi.
- Entry 19'un tam giriş manifesti ve eski readiness certificate'ı bulunamadı;
  "1.7 → 2.0 artışı" nedeni bu iki artifact olmadan **kesinleştirilemez**
  (analiz §1). Uydurulmayacak.
- `v8-core/src/trade_lifecycle.rs` (SB02 Rust taslağı, 11/11 test yeşil) bu
  kapsamda **kullanılmayacak**; park edildi.
- Ekonomik sonuç, p-value, Sharpe, PBO veya canlı yetki bu plandan **doğmaz**.
