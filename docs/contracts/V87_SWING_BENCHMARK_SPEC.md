# V8.7 — Swing Benchmark ve Kanıt Yenilemesi

Durum: DRAFT / PROPOSED. Planlama tarihi: 2026-09-11.
Bu belge tam metin sürüm önerisidir; ratifikasyon, uygulanmış mimari,
tamamlanmış benchmark veya ekonomik sertifika değildir.

Uygulama sırası ve kabul matrisi:
[V8.7 uygulama planı](../migration/V87_SWING_BENCHMARK_IMPLEMENTATION_PLAN.md).
Yönetişim: [2026-09-07 reset](../GOVERNANCE_RESET_V86_2026-09-07.md).

## 1. Amaç ve sürüm sınırı

V8.7, kısa diagnostic koşudan swing hedefiyle uyumlu, veri rolü açık,
muhasebesi uzlaştırılmış ve tekrar üretilebilir bir benchmarka geçiştir.
V8.6 altyapısının üzerine gelir; yeni runtime yazımı veya dil geçişi değildir.
`v8-core/` tek aktif Rust uygulamasıdır. `v8-next/` salt okunur hata/deney
referansıdır; `src/v8/`, `tests/` ve `v8-next/` değişmez.

V8.7 ürün/program adıdır. Cargo paket sürümü halen ayrı bir sürüm eksenidir;
bu öneri paket sürümünü, release tag'ini veya çalışan varsayılanları değiştirmez.
Benchmark protokolü, scorer, veri manifesti, estimator ve policy sürümleri
ayrı kimlikler taşır. Önerilen protokol kimliği `swing-benchmark-v1`;
uygulamada kabul edilene kadar bu kimlikle kanıt üretilmiş sayılmaz.

Başarı iki ayrı eksende raporlanır:

1. **Benchmark teknik olarak yeterli:** doğru muhasebe, veri kimliği,
   nedensellik, tekrar üretim, gerçek sonuçların eksiksiz raporlanması.
2. **Strateji ekonomik olarak yeterli:** önceden seçilmiş benchmark ve risk
   hedeflerine karşı yeterli bağımsız kanıt. İlk eksenin başarısı ikincisini
   gerektirmez. Teknik sürüm negatif/underpowered strateji sonucuyla da biter.

Canlı emir, para aktarımı, yeni venue yetkisi, sertifika uydurma, skor eşiğine
ulaşmak için veri seçme veya tam engine yeniden yazımı kapsam dışıdır.

## 2. Başlangıç kanıtı ve belirsizlikler

Ön inceleme kaynakları:

- `artifacts/benchmarks/benchmark_ledger.jsonl`: son incelenen kayıt seq=18,
  capability=11.1, G0 BLOCKED, G1 UNKNOWN, G2 PASS, G3–G7 UNKNOWN.
- `v8-next/src/v8_next/evaluation/runner.py`: kapanış eşleştirmesi yalnızca
  position_id ile; para tutarı ve açık pozisyon oranı aynı seriye girebilir.
- `v8-next/src/v8_next/evaluation/scoring.py`: dört vekil alan ve sabit coverage.
- `v8-next/src/v8_next/evaluation/certificate.py`: eksik kanıtta 50/60 varsayılanı.
- `v8-next/src/v8_next/app/benchmark.py`: varsayılan 500 bar sınırı.
- `v8-next/src/v8_next/evaluation/economic_benchmark.py`: 350 bar fit sınırı;
  500 bar koşusunda 150 saat/6.25 gün OOS. Bu ayrı yol entry 19 ile özdeş değildir.
- [D152 veri rolü](D152_SCENARIO_CENTRIC_EVIDENCE_PROFILE_SPEC.md): mevcut
  lineage için 12 aylık quad BURNED_DIAGNOSTIC.
- `v8-core/src/benchmark/runner.rs`: resmi evaluator bulunmadığında receipt
  yolu kapalı; diagnostic yolun mevcudiyeti resmi evaluator yeterliliği değildir.

Bu Python bulguları Rust'ta aynı hatanın bulunduğunu kanıtlamaz. Her iş paketi
önce aktif Rust çağrı yolunda eşdeğer davranışı doğrular; zaten doğru çalışan
mekanizmayı yeniden yazmaz. Rust benchmark scoru ile Python 0–100 çıktısının
ölçekleri de otomatik olarak aynı kabul edilmez.

Dört yıllık veri varlığı kullanıcı beyanıdır. Bu öneri dört yılın tümünü,
sembol bazında sürekliliğini, funding/mark kapsamını veya geçmiş kullanımını
doğrulamış değildir. İlk teslimat gerçek dosya envanteri ve kullanım haritasıdır.

## 3. Dört yıllık veri sözleşmesi

Örnek plan 48 aydır; kesin takvim tarihleri envanterden sonra sabitlenir.

| Dönem | Rol | Kullanım |
|---|---|---|
| Ay 1–24 | DEVELOPMENT | Aday geliştirme, parametre ve mekanizma araştırması |
| Ay 25–36 | WALK_FORWARD_VALIDATION | Önceden tanımlı seçim sürecinin dört üç aylık testi |
| Ay 37–48 | PROTECTED_OOS, yalnızca gerçekten görülmemişse | Ay 36 sonunda dondurulan sistemin bir defalık nihai değerlendirmesi |
| Sonradan gelen veri | PROSPECTIVE_SHADOW | Dondurulmuş policy'nin ileriye dönük gözlemi |

Geçmişte incelenmiş, optimize edilmiş veya seçim kararını etkilemiş dönem
lineage bazında BURNED_DIAGNOSTIC kalır. Kullanımı bilinmeyen dönem
USAGE_UNKNOWN olur; korunmuş OOS gibi sunulamaz. Dört yılın tamamı kullanılmışsa
tamamı diagnostic/walk-forward araştırma malzemesidir; tarihsel bağımsız test
bulunmadığı açık yazılır. Daha eski görülmemiş veri rejim/genelleme testi olabilir,
ancak daha yeni veriyle seçilmiş strateji için ileriye dönük test diye sunulmaz.

Her partition kaydı: data_id/hash, kaynak, sembol/venue/ürün, başlangıç/bitiş,
bar frekansı, boşluk/tekrarlar, edinim zamanı, bilgi mevcudiyeti modeli,
funding/mark kapsamı, delist/listing kapsamı, role, policy_lineage ve erişim
geçmişi içerir. Bilinmeyen değer açıkça eksik kalır. Candle kapanışı tarihsel
gerçek alınma zamanı olarak uydurulamaz.

Ham dosyalar değişmez; temizlenmiş türevler yeni kimlikle oluşur. Gerçek
gözlem eksikliği doldurulmuş fiyatla ekonomik kanıta dönüştürülemez. Bir sembolün
dört yıllık geçmişi yoksa eksiklik raporlanır; ortak kapsama sessizce indirgeme
veya yalnızca hayatta kalan sembolleri seçme yapılmaz.

## 4. Zaman bölme, swing ve sonuç gözlemi

Başlangıç araştırma hipotezi 2–14 günlük tutuş; 1D rejim, 4H setup ve 1H
yürütmedir. Bu bir başarı sonucu veya her aday için zorunlu optimum değildir.
Zaman çözünürlüğü, adayın lookback ve sonuç ufku policy manifestinde tanımlanır.

Her fold üç bölüm taşır: geçmişten gelen puanlanmayan warmup, puanlanan
karar aralığı, sonuçları izlemek için devam aralığı. Warmup gerçek gösterge
ihtiyacına göre hesaplanır. 4H/1D sinyal yalnızca tamamlanmış ve karar anında
kullanılabilir mumları görür. UTC sınırları, kapanış konvansiyonu ve veri
sıralaması manifestte bulunur.

Walk-forward takvimi:

| Tur | Geçmiş | Test |
|---|---|---|
| WF1 | Ay 1–24 | Ay 25–27 |
| WF2 | Ay 1–27 | Ay 28–30 |
| WF3 | Ay 1–30 | Ay 31–33 |
| WF4 | Ay 1–33 | Ay 34–36 |
| FINAL | Ay 36 sonunda dondurma | Ay 37–48, role uygunluğu varsa |

Tablo takvim üst sınırını gösterir: yeniden seçim anında henüz sonucu
olgunlaşmamış işlemler train'e giremez. Train etiketinin sonuç aralığı testle
örtüşüyorsa purge edilir. Embargo bilgi bağımlılığı ve sonuç ufkuna göre
önceden belirlenir; mevcut sabit bir saat/bir gün değerleri körlemesine taşınmaz.

Fold sonucunu sonra değiştirip aynı fold'u yeniden OOS ilan etmek yasaktır.
Seçim algoritması, aday ailesi, tuning bütçesi ve refit takvimi WF1 öncesi
sabitlenir. Önceki testler sonraki turda geçmiş olabilir; her tur sadece o an
erişilebilir bilgilerle karar verir. Değişiklik yeni araştırma denemesi olarak
kaydedilir ve kullanılan test artık görülmemiş sayılmaz.

Ekonomik portföy eğrisi takvimde kesintisiz mark-to-market izlenir; fold
sınırında pozisyonlar sırf rapor için zorla kapatılmaz. Policy güncellemesinde
mevcut pozisyonu hangi sürümün yöneteceği önceden tanımlanır. Fold getiri
atfı takvim bazlıdır; trade kohortları giriş zamanına göre ayrı raporlanır.
Devam aralığı eski fold'un tamamlanmış trade analizine hizmet eder, sonraki
model seçimine erkenden bilgi vermez. Veri sonunda açık sonuçlar censored;
zorunlu sıfır veya hayali kapanış değil. MTM ve kapalı trade raporu ayrı kalır.

Üç aylık test veya bir yıllık final otomatik yeterlilik değildir. Ham n,
bağımlılık, efektif örneklem, rejim kapsamı ve belirsizlik raporlanır. Yetersiz
örnek UNDERPOWERED; trade zorlamak veya eşik gevşetmek yoktur.

## 5. Muhasebe ve yürütme

Trade kimliği pozisyon yaşam döngüsünü ve ilgili execution olaylarını ayırır.
Aynı venue position_id'nin yeniden kullanılması yeni round-trip'i eski
kapanışa bağlayamaz. Kısmi fill, kısmi kapanış, reversal ve açık pozisyon ayrı
işlenir. Parse/ölçüm hatası sıfır PnL üretmez.

Para defteri, ortak özsermaye getirisi ve trade risk birimi ayrı tür/alanlardır.
Gerçekleşen fill fiyatına gömülmüş slippage ikinci kez maliyet olarak düşülmez.
Komisyon, funding, transfer ve MTM etkileri açık ayrışır. Portfolio equity
değişimi, nakit hareketleri ve pozisyon PnL'si bağımsız uzlaşır; tolerans fiyat,
miktar ve para hassasiyetine dayanır, sonucu geçirecek şekilde seçilmez.

Bar-only simülasyon mikro yapı gözlemi değildir. Aynı mumdaki stop/target
belirsizliği raporlanır; gerektiğinde mevcut gerçek daha ince çözünürlükle
karşılaştırılır. Simülasyon maliyet/latency varsayımları measured değil assumed
etiketlidir. Funding gerçek olay çizelgesi ve kapsamıyla işlenir. Eksik funding
veya mark verisi ilgili maliyet/likidasyon sonucunu eksik bırakır.

## 6. Baseline, aday ve istatistik sözleşmesi

Önce tek sade swing baseline; sonra sınırlı aday ailesi. Squeeze breakout ve
trend pullback ayrı hipotez olabilir. Mevcut Rust squeeze_swing bir araştırma
başlangıcıdır; parametrelerinin başarısı varsayılmaz. Adayların birleşimi ve
expert çıkarma deneyleri gerçek trial olarak kaydedilir.

Cash, buy-and-hold, equal-weight, risk hedefli baseline ve simple trend
diagnostic karşılaştırmalarda tutulur. Birincil ekonomik benchmark ve risk
mandatı yeni deney öncesi sabitlenir. Ortak sermaye yanında exposure, volatility,
leverage, turnover ve maliyet kapsamı karşılaştırılır. Geçmiş negatif raporlar
yeni benchmark seçimiyle geriye dönük başarılı ilan edilmez.

Trial registry policy/config/data hashes, aile, seçim zamanı, kullanılan veri
ve sonuçları kaydeder. Kaydırılmış champion serileri gerçek aday arama geçmişi
yerine geçmez. Stratejiler ortak zaman ekseninde değerlendirilir; kripto
varlıkları ve örtüşen işlemler bağımsız gözlem diye sayılmaz. Bootstrap gerçek
gözlemler üzerinde estimator içinde çalışır; yeniden örneklemeler yeni piyasa
veya trade kanıtı olarak ledger'a yazılmaz. Yapay fixtures yalnızca Rust test
harness'inde mekanik testler içindir.

DSR/WRC/SPA/PBO gibi testler uygun veri, aile ve tanımla çalıştırılır; eksik
hesap PASS olamaz. Hangi testin hangi kararı kontrol ettiği sürümlü acceptance
matrisinde yer alır. G5 başka tape'e sessiz fallback yapamaz. Rejim etiketleri
geçmişten tanısal seçilmişse causal trading feature gibi kullanılamaz.

## 7. Skorlar ve gate geçişi

Öncelik ham metrikler ve ayrı yeterlilik eksenleridir. Research validity,
economic performance, statistical sufficiency, execution fidelity ve prospective
evidence tek sayıda birbirini telafi edemez. NO_ECONOMIC_CLAIM korunur.

Yeni skorun ağırlıkları, normalizasyonları ve uncertainty yöntemi geliştirme
verisinde gerekçelendirilip protected OOS açılmadan dondurulur. Ölçülmeyen
alan sabit puan almaz; eksik alanlar kalan alanların yeniden ağırlıklandırılmasıyla
gizlenmez. Metrik değerine erişilemiyorsa aggregate optional/UNAVAILABLE olur
ve kapsam ayrıca gösterilir. Coverage'ın aynı bileşik puanda iki kez uygulanıp
uygulanmayacağı açıkça tanımlanır; varsayılan olarak kanıt sayımı tekrarlanmaz.

Önceki görüşmede geçen capability 45–65/readiness 15–30 ve 50/20 kilometre
taşları **kalibre edilmemiş planlama hedefleridir; beklenen sonuç veya kabul
eşiği değildir**. Yeni scorer doğrulanana kadar bunlarla ilerleme ölçülmez.
Eski Python formülündeki 14.53/2.62 tavan analizi o belirli yola aittir;
yeni Rust protokolüne aktarılmaz.

Gate kimliği numara yanında semantic_id ve gate_schema_version içerir.
D152/D153 G7–G9 adlandırma uyuşmazlığı mevcut otorite sözleşmeleriyle eşlenir;
bu taslak sessizce yeni numara tayin etmez. Her gate için required inputs,
hesap, predicate, missing behavior ve evidence binding tanımlanır. Determinism,
ledger doğrulaması, veri continuity ve ekonomik yeterlilik ayrı kontrollerdir.
G7 diye tarihsel replay'e prospektif kanıt yetkisi verilmez.

## 8. Artifact ve geçmiş uyumluluğu

Her yeni run ayrı değişmez dizine yazılır. Zorunlu manifest: run/protocol/policy
kimliği, code revision + dirty diff digest, config hash, veri/partition kimlikleri,
estimator/scorer/gate sürümleri, seed, yürütme varsayımları, başlangıç/bitiş,
tamamlanma durumu ve fiziksel artifact hash'leri. Dosyalar yazılıp doğrulanmadan
manifest complete olamaz. Kesilmiş koşu PARTIAL; log varlığı tamamlanma değildir.

Planlanan çıktı kategorileri: manifest, data audit, folds, fills, lifecycle
trades, cashflow/equity, raw metrics, gate evidence, trial registry, report ve
varsa yetkili receipt. Bunlar gelecekte üretilecek kategorilerdir; bu belgede
herhangi bir yeni sonuç dosyasının varlığı iddia edilmez.

Eski ledger değişmez. Digest kanonu bilinen sürüme göre doğrulanır; bilinmeyen
sürüm desteklenmiyor olarak kalır. Tarihsel satır yeniden hash'lenip orijinal
kanıtmış gibi sunulmaz. Salt okunur doğrulama ve gerekirse açık bir migration
ilişkisi ayrı artifact'tir. Yeni ve eski score serisi ayrı grafik/etiket taşır.

## 9. Çalıştırma katmanları ve hesap bütçesi

SMOKE: sabit küçük gerçek veri, teknik regresyon; ekonomik ağırlığı yok.
RESEARCH: rolü izinli geliştirme aralıkları, sınırlı adaylar.
VALIDATION: dondurulmuş kronolojik süreç; fold takvimi değişmez.
FINAL: korunmuş test; tuning/cache keşfinden ayrılmış erişim.
SHADOW: ileriye dönük gerçek veri; erişim zamanı ve karar bağı bağlanır.

Ham/decode/özellik cache'i veri ve hesap sürümüyle; sonuç cache'i ayrıca policy,
fold ve execution varsayımlarıyla anahtarlanır. Protected sonuçlar geliştirme
cache'inden okunamaz. Resume checkpoint'i input/config identity uyuşmazlığında
reddedilir. Paralellik zaman bağımlı tek portföy yolunu değiştirmez; bağımsız
koşular üzerinde ve deterministik toplanan sonuçlarla yapılır.

## 10. Tamamlanma ve sürüm çıkışı

V8.7-dev: teknik iş paketleri tamam; tanısal raporlar, eksiklikler ve veri rolleri
açık. V8.7-rc: protokol/scorer dondurulmuş, reproducibility ve adversarial
mekanik denetimler tamam. V8.7 benchmark release: tüm teknik kabul kanıtları
ve sınırları kayıtlı. Ekonomik aday yeterliliği ayrı sonuçtur; negatif sonuç
sürümün teknik tamamlanmasını engellemez.

Tier D sınırında mevcut gereksinimlere göre D-series kaydı, EN/TR tam metin,
layout mapping, CHANGELOG, iki monograph ve yetkili receipt/certificate
işleri yapılır. Bu draft aşamasında karar numarası, skor sertifikası veya
release etiketi yaratılmaz. Uygulama planının yazılması uygulamanın başladığı
veya bittiği anlamına gelmez.
