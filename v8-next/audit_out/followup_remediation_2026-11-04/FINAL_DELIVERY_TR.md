# V8-next Denetim Takibi İyileştirme Raporu — 2026-11-04

## 1. Kapsam, taban durumu ve sınırlar

Çalışma yalnızca `v8-next/` ağacında yapıldı. Taban commit
`1fa78e89612a7728e8d86a85c44797bd2b6e1e48` (`fix/v8-next-critical-execution-gate-integrity`)
dalıdır. Çalışma ağacındaki mevcut değişiklikler korundu; `reset`, `clean`, `stash` veya
`checkout` ile hiçbir şey geri alınmadı. V9 dizinine, korumalı OOS penceresine, canlı veya
kimlik doğrulamalı venue işlemlerine dokunulmadı; gönderim, birleştirme veya PR yapılmadı.
Strateji mimarisi ve taban davranışı korunmuştur; değişiklikler yalnızca muhasebe, güvenlik,
istatistik ve taşınabilirlik düzeltmeleridir. Hiçbir ekonomik iddia üretilmedi;
`NO_ECONOMIC_CLAIM` yürürlükte kaldı.

## 2. Sekiz takibin durumu

| # | Takip | Durum | Gerekçe |
|---|---|---|---|
| 1 | Braket kimliği ve reduce-only | `PASS` | Mevcut odaklı testlerle doğrulandı; kod değişikliği gerekmedi. |
| 2 | Sınır zamanı funding atfı | `PARTIAL` | Replay `max(sınır, teslim)` anında ücretlendiriyor, pencere sonrası bilinen kaydı uygulamıyor, yinelenen sınır kaydını ikinci kez saymıyor. Paper tarafı, sınırda ve teslimde açık olan pozisyon aynıysa atfı kabul ediyor, maruziyet arada değiştiyse sonuç yayınlamayı reddediyor. Tek uzlaşmanın iki maruziyet arasında bölünmesi hâlâ sınır anı snapshot'ı gerektiriyor. |
| 3 | Nedensel funding markı | `PASS` | Sınırda veya öncesinde kapanmış ve mevcudiyeti sınırı aşmayan son kapanış kullanılıyor; bir barı aşan bayatlık reddediliyor; eksik mark sayılıyor. |
| 4 | G5 seçim ailesi denetimi | `PASS` | `SelectionFamily` üyeleri, kayıt anını ve dayanağı içeriyor; kimliği bu içerikten türetiliyor. Aile yoksa kapı `BLOCKED` / `MISSING_PROVENANCE_BOUND_SELECTION_HISTORY` döndürüyor; aile varsa ve boyu sabitlenmiş çoklukla eşleşiyorsa DSR ve Bonferroni karar veriyor. |
| 5 | Sıfır olmayan sonlu bootstrap p-değeri | `PASS` | `PLUS_ONE_V1` varsayılan, `LEGACY_EXCEED_OVER_REPS_V1` eski kanıtlar için birebir korunuyor; çözünürlük ve sınırlama metni değerle birlikte yayınlanıyor. |
| 6 | DuckDB atomik geri dönüş | `PASS` | Kopyalama ortasında hata ve yedek yolun da başarısız olması durumunda hedef dosya bayt bayt korunuyor, geçici dosya siliniyor; tablo kümesi ve satır sayıları uzlaşıyor. |
| 7 | Taşınabilir tape yolları | `PASS` | Tek bir çözümleyici (`adapters/tape_paths.py`) hem kaynak hem testlerde kullanılıyor: açık argüman > `V8_DATA_ROOT` / `V8_TAPE_ROOT` / `V8_TAPE_PATH` > depo göreli varsayılan; eksik tape `FileNotFoundError` veriyor. Eski mutlak önek artık 0 kez geçiyor (önce 32 dosyada 47 kez). |
| 8 | Ortak fill yardımcısı | `PASS` | Mevcut testlerle doğrulandı. |

## 3. Spesifikasyon kararları

- **D1 — Sınır + teslim atfı.** Bir uzlaşma `max(venue sınırı, yerel teslim)` anında
  ücretlendirilir. Yalnızca sınırda ücretlendirmek, nakit etkisini gözlemlenebilir olduğu andan
  önceye tarihler; yalnızca teslimde ücretlendirmek ekonomik sınırı kaydırır. İki an da kayıtta
  tutulur, kaydırma `funding_receipt_shifted` olarak sayılır.
- **D2 — Yinelenen kayıt sessizce birleştirilmez.** Aynı enstrüman ve sınır için ikinci kayıt
  düşülür ve `funding_duplicate_boundary` olarak raporlanır; aksi hâlde tek maruziyet iki kez
  borçlandırılırdı.
- **D3 — Mark sınırlı tarihsel modeldir.** Temel
  `OHLC_CLOSE_ASOF_BOUNDED_HISTORICAL_MODEL_NOT_VENUE_MARK` olarak yayınlanır; venue markı
  olduğu iddia edilmez ve `settlements.py`'nin geriye tarihli hesap güncellemesi yasağı
  zayıflatılmaz.
- **D4 — Paper tarafı tahmin etmek yerine reddeder.** Sınırda veya teslimde açık pozisyon varsa
  ve uzlaşma gecikmişse simüle bakiye yayınlanmaz. Tam sınırda kapanan pozisyon da reddedilir;
  eşzamanlı kapanış/funding sırası snapshot'tan kanıtlanamaz.
- **D5 — G5 hikâye değil provenance ister.** Tek stratejinin dört stres dönüşümü seçim ailesi
  değildir. DSR, Bonferroni ve White reality check tanılama olarak hesaplanmaya devam eder;
  kapı `BLOCKED` döner. `multiplicity_trials` düzeltmeyi genişletmeye devam eder, tanılama
  varyantları onu asla genişletmez.
- **D6 — Monte Carlo raporlaması sürümlüdür.** `PLUS_ONE_V1` sonlu yeniden örneklemede p = 0
  raporlanmasını engeller; eski sürüm birebir yeniden üretilebilir kalır; kütüphane WRC yolu
  "ham sonlu bootstrap tanılaması, kesin test değil" olarak etiketlenir.
- **D7 — Eksik veri yüksek sesle başarısız olur.** Göreli geçersiz kılmalar kabuk dizinine değil
  depo köküne göre çözülür; eksik tape boş bir koşu üretmez.

## 4. Değiştirilen dosyalar

Kaynak: `adapters/portfolio_backtest.py` (funding planlama yardımcısı, nedensel mark, yeni
kapsama etiketleri), `adapters/catalog_tape.py` (`resolve_tape_path`, depo göreli varsayılanlar),
`app/paper.py` (gecikmiş funding reddi), `evaluation/gate_resolution.py` (G5 fail-closed,
WRC sürümü), `evaluation/reality_check.py` (sürümlü p-değeri), `evaluation/multitape.py`
(`FundingRow.received_ns`).
Testler: yeni `test_funding_boundary_attribution_20261104.py`,
`test_funding_causal_mark_20261104.py`, `test_delayed_funding_fail_closed_20261104.py`,
`test_g5_family_block_20261104.py`, `test_reality_reporting_20261104.py`,
`test_duckdb_atomic_20261104.py`, `test_tape_path_resolution_20261104.py`; güncellenen
`test_reality_check.py`, `test_gate_resolution.py`, `test_swing_costs.py`,
`test_data_integrity_regressions.py`. Dokümantasyon: `README.md`,
`AUDIT_FOLLOWUPS_2026-10-31.md`.

## 5. Önce/sonra kanıtı

`BEFORE_AFTER.json` aynı girdiler üzerinde iki ifadeyi çalıştırarak üretildi; elle yazılmadı.
Reality check 19 tekrarda 0 aşım için önce `0.0`, sonra `0.05`; 2/3 için önce `0.6667`, sonra
`0.75`. G5, geçen bir stres tanılamasına rağmen önce `PASS`, sonra `BLOCKED` döndürüyor ve
`stress_diagnostic_passed = true` alanı bloğun performans değil provenance kaynaklı olduğunu
gösteriyor. HEAD'in kendi testleri HEAD kaynağına karşı hâlâ geçiyor
(`HEAD_baseline_behaviour.log`, 4 passed), yani eski davranış gerçekten farklı.

## 6. DuckDB ve arch

DuckDB 2.0.0 ve arch 8.0.0 bu koşu için `v8-next/.venv` içine uv ile kuruldu; böylece isteğe
bağlı testler atlanmadı, gerçekten çalıştı. DuckDB tarafında kopyalama ortasında hata enjekte
edildi ve yedek yol da başarısız kılınarak hedefin korunduğu kanıtlandı; dışa aktarılan tablo
kümesi ve satır sayıları kaynakla karşılaştırıldı. arch testleri reality-check kitaplık yolu
için çalıştı ve sonucun "ham tanılama" olarak etiketlendiği doğrulandı.

## 7. Hızlı paket, lint ve tip denetimi

Hızlı paket: **1125 geçti, 9 atlandı, 506 seçilmedi**. Yavaş testler dâhil tam paket:
**1575 geçti, 64 atlandı, 1 düştü** (`test_mechanics_metrics_and_capacity`, HEAD'de de aynı).
Ruff temiz. Ortam: Python 3.12.12, pytest 9.1.1, NautilusTrader 2.0.0rc4,
duckdb 2.0.0, arch 8.0.0 (`versions.log`). mypy hem HEAD'de hem şimdi **19 hata** veriyor ve dosyalar aynı (`pywin32` stub eksikliği, `Decimal` dönüşümleri, bir
`float | None` işlemi); yani yeni tip hatası eklenmedi, ancak mypy kapısı geçmiyor ve bu
`PASS` sayılmadı.

### Performans etkisi

35.040 barlık bacak ve 4.379 funding kaydı üzerinde ölçüldü (`performance.log`). Funding
planlaması, bisect öncesi sürümde 7,12 s medyandı; bar bitiş zamanlarını ikili arama ile bulup
enstrüman başına önbelleğe aldıktan sonra **0,0043 s** (yaklaşık 1.650 kat). Kontrol mantığı
aynı; başka hiçbir davranış değişmedi ve hızlı paket süresi (~6-7 s) artmadı. Tek başına mark
yardımcısı kendi indeksini kurduğu için çağrı başına ~0,39 ms ödüyor; planlayıcı bu bedeli
ödüyor değil.

## 8. Riskler ve açık noktalar

1. **#2 maruziyet bölünmesi.** Tek uzlaşmayı iki maruziyet arasında zamanla orantılı bölmek
   için sınır anı snapshot'ı gerekir; capture bunu taşımıyor. Kod tahmin etmek yerine reddediyor,
   bu yüzden takip `PARTIAL` kalıyor.
2. **#4 varsayılan durum.** Bu depoda provenance bağlı bir aile kaydı yok; yetenek ve reddetme
   kuralları test edilmiş olsa da G5 pratikte hâlâ `BLOCKED` dönüyor.
3. **Tam paket.** `tests/test_economic_benchmark.py::test_mechanics_metrics_and_capacity`
   `data_resolution` metni yüzünden düşüyor. Aynı hata HEAD'de de birebir var
   (`HEAD_preexisting_failure.log`), yani önceden mevcut; yine de `FAIL` olarak kaydedildi.
4. **Gerçek tape ekonomik doğrulaması.** Bu koşuda `NOT_APPLICABLE`: korumalı pencere açılmadı,
   OOS verisi okunmadı.
5. **myyp kapısı** kırmızı; mevcut borç kapatılmadı.

## 9. Eserler ve bütünlük

Dizin `v8-next/audit_out/followup_remediation_2026-11-04/`:
`ACCEPTANCE.md`, `ACCEPTANCE_MATRIX.md`, `BEFORE_AFTER.json`, `MEASURED.json`, `REPORT.md`,
`SHA256SUMS`, `SPEC_DECISIONS.md`, `TEST_RESULTS.md`, bu dosya, ham `*.log` dosyaları ve
tabloları loglardan türeten `build_artifacts.py`. `SHA256SUMS` her dosyanın özetini taşır;
`MEASURED.json` her logun özetini, boyutunu ve çıkış kodunu kaydeder. Arşivlenmiş yollara
(`v8-core/`, `src/v8/`, kök `tests/`) hiçbir yazma yapılmadı.

## 10. Yargı: `PARTIAL`

Sekiz takibin yedisi tam ve kanıtlı biçimde kapandı (#1, #3, #4, #5, #6, #7, #8); #2 kısmi
kaldı. Kalan tek iş kod hacmi değil kanıt eksikliğidir: tek funding uzlaşmasını iki maruziyet
arasında bölmek için sınır anı maruziyet snapshot'ı yok. Tam paketteki tek düşüş HEAD'de de
birebir tekrarlandığı için önceden mevcuttur ve `PASS` sayılmadı. Bunlar tamamlanmadan
`COMPLETE` denemez; hiçbir doğrulanmamış senaryo `PASS` olarak işaretlenmedi ve hiçbir ekonomik
iddia üretilmedi.
