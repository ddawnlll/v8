# V8 swing benchmark analizi ve kurtarma planı

Arşiv notu (2026-09-11): Bu metin önceki salt okunur incelemenin tam içeriğidir;
bulgular incelenen yerel çalışma ağacına aittir, güncel Rust uygulamasının
aynı hataları taşıdığı iddiası değildir. Aşağıdaki "değiştirilmedi" ifadeleri
o incelemeyi anlatır. Yerel dosya bağlantıları repo içinde taşınabilir hale
getirildi; gitignored kanıt dosyaları GitHub'da bulunmayabilir.
Devamı: [V8.7 şartname](../contracts/V87_SWING_BENCHMARK_SPEC.md),
[uygulama planı](../migration/V87_SWING_BENCHMARK_IMPLEMENTATION_PLAN.md),
[issue dizini](../migration/V87_ISSUE_INDEX.md).

Mevcut 11,1 capability ve 2,0 readiness değerleri, sistemin swing trading potansiyelini güvenilir biçimde ölçmüyor. Ölçüm formülü dar bir sayısal aralığa sıkışmış; PnL eşleştirmesinde somut hata riski var; veri süreleri, kanıt rolleri ve gate anlamları birbirine karışıyor. Bunları düzeltmek araştırma kapasitesini artırabilir. Kârlılık artışı ise ayrıca sınanacak bir hipotezdir.

İncelemenin kapsamı yerel çalışma ağacı, benchmark ledger’ı, ilişkili fiziksel raporlar ve birincil dış kaynaklardır. Yeniden backtest çalıştırılmadı. Yerel ağaçta önceden mevcut değişiklikler bulunduğu için kaynak kod bulguları ile geçmiş koşunun tam yürütme sürümü aynı kabul edilmedi. Uygulama, test, ledger ve repo belgeleri değiştirilmedi. Bu metin onaylanmış mimari veya ekonomik sertifika değil, araştırma önerisidir.

**1. Entry 18 ile 19 neden doğrudan karşılaştırılamıyor?**

[Benchmark ledger](../../artifacts/benchmarks/benchmark_ledger.jsonl) içindeki son iki kayıt sıfır tabanlı 17 ve 18 numaralı kayıtlar; kullanıcı dilindeki entry 18 ve 19 bunlarla eşleşiyor. Son kayıtta capability 11,1, coverage 0,60, G0 BLOCKED, G1 UNKNOWN, G2 PASS, G3–G7 UNKNOWN, G8–G9 MISSING. Önceki kayıtta capability 12,7; G3/G4/G6 BLOCKED ve G5/G7 PASS.

G3–G7’nin çalıştırılmadığı bir koşuda UNKNOWN olması performans bozulması değildir. G2 de yalnızca karşılaştırılan fill/pozisyon çıktılarının tekrar edilebilirliğini gösterir; veri doğruluğu, ekonomik avantaj veya tüm ledger’ın sağlamlığı anlamına gelmez. Aynı hatanın deterministik tekrarı mümkündür.

Son iki kaydın input_binding değerleri ve veri bitiş zamanları farklı. Aynı policy_id altında farklı veri/ayar koşmuş olabilir. Hash farkı bunu işaret eder fakat hash tek başına hangi girdinin değiştiğini açıklamaz. Tam komut, kaynak manifesti, kod ve ayar sürümü, gate çalışma modu aynı olmadan farkı sadece fix’e atfetmek mümkün değil.

Mevcut certificate formülüyle 12,7 capability, diğer çarpanlar aynıysa 2,286 readiness üretirdi; bildirilen eski 1,7’yi üretmez. Dolayısıyla 1,7 → 2,0 artışının nedenini eski certificate ve koşu sürümü olmadan kesinleştiremeyiz. Son rapordaki 2,0 ise mevcut formülle tam açıklanıyor.

**2. Skorun matematiksel tavanı var**

[scoring.py:148](../../v8-next/src/v8_next/evaluation/scoring.py:148) on alan tanımlamasına rağmen bu hesap yolunda sadece dört alan üretiyor:

| Alan | Mevcut hesap | Sorun |
|---|---|---|
| ExecutionFidelity | Simülasyon shortfall ölçümü varsa ona, yoksa PnL Sharpe vekiline dayanıyor; üst sınır 0,50 | 10 bps referansı kalibre edilmiş gerçek kapasite ölçümü değil; simülasyon kanıtı gerçek piyasa fill kanıtı değil |
| OperationalSimplicity | clip(1 − 0,3 × abstain_rate, 0,10, 0,60) | Abstain oranı 0–1 içindeyken sonuç hep 0,60; karmaşıklık veya seçicilik değişimini ayırt etmiyor |
| DefeaterResistance | En az bir trade varsa 0,15 | Adversarial test sonucundan türetilmiyor |
| MicrostructureInvariance | Bar sayısıyla artıyor; üst sınır 0,30 | Daha uzun seri mikro yapı değişmezliğini kendiliğinden kanıtlamaz |

Alt bantlar sabit katsayılarla oluşturuluyor. Bunlar veriyle hesaplanmış güven aralıkları değil; kod da diagnostic band olarak adlandırıyor. effective_sample_size doğrudan ham n’ye eşit atanıyor. Korelasyon ve pozisyon örtüşmesi ölçülmüyor. CapabilityScalability bu dört alanın içinde dahi yok; dolayısıyla “Cap” gerçek sermaye taşıma kapasitesi değildir.

Mevcut ağırlıklar 0,10 + 0,15 + 0,08 + 0,12 = 0,45. Mümkün en yüksek alt bantlar sırasıyla 0,40, 0,48, 0,105, 0,225. Coverage 0,60 sabitken:

`Cap_max = 100 × 0,60 × 0,45 / (0,10/0,40 + 0,15/0,48 + 0,08/0,105 + 0,12/0,225) = 14,5338`

[certificate.py:53](../../v8-next/src/v8_next/evaluation/certificate.py:53) Minerva yokken robustness 50, projection yokken economic 60 atıyor. [Runner:503](../../v8-next/src/v8_next/evaluation/runner.py:503) certificate’ı bunları sağlamadan oluşturuyor.

`Readiness = Cap × 0,60 × 0,50 × 0,60 = Cap × 0,18`

Böylece 11,1 → 1,998; mevcut yolun teorik readiness tavanı 2,616. Bu bir performans tahmini değil, kaynak formülün cebirsel sonucudur. Coverage capability içinde ve readiness içinde iki kez etki ediyor. Bunun amaçlı bir kanıt cezası olup olmadığı ayrı bir tasarım kararıdır; mevcut sayıdaki etkisi gerçektir.

Öneri: Önce ham ekonomik metrikler, veri kapsamı, mühendislik kontrolleri ve kanıt yeterliliği ayrı gösterilsin. Yeni skor hesaplanacaksa ölçülebilir alanlar ve kalibrasyon önceden tanımlansın; eski seriyle aynı ölçekmiş gibi birleştirilmesin. Eksik robustness/economic kanıtı 50/60 yerine açık eksiklik olarak kalsın. Düzeltme sonrası skorun düşmesi veya hesaplanamaması başarısızlık değildir.

**3. PnL yolu strateji optimizasyonundan önce düzeltilmeli**

[Entry 19 trade dosyası](../../artifacts/benchmarks/BC-D153-CANONICAL-01_18_trades.jsonl) üç satır içeriyor. Üçü de aynı trade_id ve −3256,624313 pnl değerini taşıyor; zamanları farklı, son satırın yönü de farklı.

[runner.py:229](../../v8-next/src/v8_next/evaluation/runner.py:229) her açılışı aynı position_id’ye sahip ilk kapanışla eşliyor. Kimlik pozisyon yaşam döngüleri arasında yeniden kullanılıyorsa ilk kapanışın PnL’si yeniden sayılıyor. Dosyadaki örüntü bu hata yoluyla uyumlu. Doğru toplam zarar tutarı fill geçmişi ve hesap bakiyesiyle yeniden kurulmadan söylenemez.

Aynı kod kapanmış pozisyon için para tutarı, açık pozisyon için boyutsuz fiyat getirisi ekliyor. Bu iki birim tek seride karışabilir. Parse hatası 0 PnL’ye dönüşebiliyor. Ayrıca sıfır varyanslı seride Sharpe vekili 0,5 atanıyor; bu negatif sabit bir seriye de uygulanabilir. Ölçülmüş shortfall kullanılan alan bu son vekili kullanmasa da temel PnL sorunu ortadan kalkmıyor.

Kabul ölçütü: yaşam döngüsü bazında tekil trade kimliği; gerçekleşmiş ve açık PnL’nin ayrı muhasebesi; tüm getirilerin ortak para/risk birimi; komisyon ve funding’in bir kez işlenmesi; fill → pozisyon → hesap özsermayesi uzlaşması. Gerçekleşen fill fiyatına zaten yansımış slippage ayrıca ikinci kez düşülmemeli. [Rust cashflow:90](../../v8-core/src/cashflow.rs:90) para korunumu kontrolü açısından yararlı örnektir; dosyanın bulunması entegrasyonun doğrulandığı anlamına gelmez.

**4. Altı gün meselesi: veri yokluğu ile yanlış pencereyi ayıralım**

Yerel `research/tape/btcusdt-1h-12m/tape.jsonl` üzerinde kline zaman damgaları sayıldı: 8.760 kayıt, 8.760 benzersiz açılış zamanı, 2025-07-01 00:00 UTC ile 2026-06-30 23:00 UTC arası. Kapsam ve saatlik benzersiz sayım bir yıllık seriyi destekliyor; içerik/checksum doğrulamasının yerine geçmiyor.

[app/benchmark.py](../../v8-next/src/v8_next/app/benchmark.py) varsayılan yüklemede `limit=500` kullanıyor. Varsayılan tape’in ilk 500 saati yaklaşık 20,83 gün. [economic_benchmark.py](../../v8-next/src/v8_next/evaluation/economic_benchmark.py) ise `OOS_FIT_BARS=350` tanımlıyor: 500 − 350 = 150 saat, yani **6,25 günlük OOS**. Altı gün ifadesinin bu ekonomik değerlendirme yolundan gelmesi mümkün. Entry 19’un tam girdisi ayrıca bağlanmadıkça ikisini aynı koşu diye sunmamak gerekir.

Son ledger kaydı 6 Temmuz 2025’te bitiyor; giriş manifesti ledger’da okunabilir biçimde yer almıyor. G0’ın hangi continuity hatası nedeniyle BLOCKED olduğu yalnızca gate vektöründen çıkmıyor. Tam koşu manifestini kalıcı saklamak bu belirsizliği çözmeli.

`canonical-quad-12m-*` dizinlerindeki loglar dört varlık × 8.760 bar ve 4.380 funding satırı yüklendiğini yazıyor, fakat incelediğim iki dizinde tamamlanmış sonuç yerine yalnızca run.log var. Başlatılan yıllık koşuyu tamamlanmış benchmark olarak saymıyorum.

En kritik ayrım: [D152 sözleşmesi:101](../../docs/contracts/D152_SCENARIO_CENTRIC_EVIDENCE_PROFILE_SPEC.md:101) bu 12 aylık quad’ı mevcut policy lineage için **BURNED_DIAGNOSTIC** ilan ediyor. Hata ayıklama ve karşılaştırma için değerli; aynı veriyi yeniden bölmek dokunulmamış OOS üretmez.

**5. Gate’ler neden score hedefi olarak optimize edilmemeli?**

[gate_resolution.py](../../v8-next/src/v8_next/evaluation/gate_resolution.py) birkaç önemli ayrım içeriyor:

| Gate | Kaynak bulgusu | Araştırma için sonuç |
|---|---|---|
| G0 | Runner sürekliliği ölçüyor; entry 19 BLOCKED | Veri temizliği kanıtı olmadan model sonucunu değerlendirme |
| G1 | Runner causal PIT denetimini UNRUN bırakıyor | Tamamlanan barın kullanılabilirliği ve karar anı ayrıca denetlenmeli |
| G3 | Varsayılan rejim parçaları en fazla 100 bar; ekstrem dönemler geçmişten seçiliyor; parçalar örtüşebilir | Dört etiket dört bağımsız rejim kanıtı değildir; swing işlemini bitirmeye yetmeyebilir |
| G5 | Kısa kendi serisi yerine varsayılan tape/başka koşu sonuçlarına geçebiliyor | PASS hedef koşunun kendi yeterli örneklemini kanıtlamayabilir |
| G5 | Champion’dan aritmetik olarak türetilmiş fee/size/slippage varyantları; varsayılan 4 trial | Gerçek araştırma aramasının çoklu test kapsamı yerine geçmez |
| G5 | WRC p-değeri hesaplanıyor fakat `passed` ifadesi DSR ve Bonferroni kullanıyor | Raporda WRC bulunması gate’in WRC’yi uyguladığı anlamına gelmez |
| G6 | Verinin 2/3 ve 1/3 parçalarında toplam kâr oranı karşılaştırılıyor | Eşit günlük kâr hızında kısa parça kabaca yarı toplam kâr üretir; 0,60 eşiği salt performans korunumu değildir |
| G7 | Geçmişin son 100 barı backtest ediliyor; drift/e-process fiyat değişiminden geliyor | Gerçek prospektif shadow veya strateji avantajı kanıtı sayılmamalı |

G5’te maliyet senaryosu kurmak kendi başına yanlış değildir; aynı seriyi kaydırarak elde edilen senaryoları denenmiş gerçek strateji ailesi ve bağımsız trial sayısı gibi kullanmak yanlıştır. Üretim/evaluation içinde uydurulmuş piyasa verisi veya metrik kullanılmamalı. Adversarial mekanik testler test ortamında kalmalı; ekonomik kanıt gerçek tarihsel/ileriye dönük gözlemlerden gelmeli.

DSR çalışması seçim yanlılığı, normal olmayan getiriler ve bağımsız deneme sayısının önemini açıklıyor.[1] PBO çalışması gerçek adayların ortak zaman eksenindeki performans matrisini ve seçim sürecinin OOS bozulmasını inceliyor.[2] İsimleri doğru testlerin hesaplanması, yanlış nüfus veya yanlış trial kayıtlarını düzeltmez.

**6. Swing hedefi için önerilen değerlendirme düzeni**

Başlangıç hipotezi BTC/ETH likit perpetual ürünlerinde yaklaşık 2–14 gün tutuş. Bu ufuk performansı kanıtlanmış optimum değil, talep edilen swing hedefini somutlaştıran öneridir. SOL/AVAX gibi ek varlıklar genelleme testi olabilir; aynı kripto rejimine maruz kaldıkları için bağımsız örnek sayısı varlık sayısıyla çarpılmaz.

| Katman | Önerilen rol | Başarı ölçütü |
|---|---|---|
| Kısa regression replay | Aynı gerçek veri üzerinde küçük ve hızlı teknik kontrol | Muhasebe, determinism, timestamp, order lifecycle doğru |
| Uzun diagnostic araştırma | Mevcut 12 ayı tümüyle kullanarak davranış ve maliyet ayrıştırma | İşlem ömrü, açık pozisyon, churn ve rejim hataları görünür |
| Daha geniş tarihsel araştırma | Erişilebilir ve doğrulanabilir 3–5 yıllık piyasa dönemleri | Boğa, ayı, yatay ve volatil dönemlerde sonuç dağılımı; veri rolü açık |
| Kronolojik doğrulama | Gerçekten görülmemiş dönemler; önceden sabitlenen adaylar | Ortak risk temelinde net OOS katkısı ve belirsizlik |
| Prospektif shadow | Dondurulmuş policy ile ileriye doğru gerçek veri gözlemi | Karar, veri mevcudiyeti, emir niyeti ve sonradan oluşan sonuç bağlanır |

Önerilen çoklu zaman yapısı: 1D rejim, 4H setup, 1H veya gerektiğinde daha ayrıntılı yürütme. 1H veri swing için yanlış değildir; yanlış olan kısa sinyal, kısa örneklem, sabit stop ve değerlendirme ufkunu düşünmeden birlikte kullanmaktır. Günlük gösterge kullanılacaksa ısınma süresi o göstergenin gerçek geçmiş ihtiyacına göre ayrılmalı; gelecekteki tamamlanmamış 4H/1D mum bilgisi kullanılmamalı.

Her değerlendirme diliminde puanlanmayan geçmiş ısınması, puanlanan karar aralığı ve kararların sonucunu gözlemek için yeterli devam verisi olmalı. Sonuç ufkunu tamamlayamayan işlem sıfır/zarar/başarıya zorlanmamalı; açık mark-to-market ve sansürlü sonuç olarak ayrı gösterilmeli. Train/test sınırını aşan sonuç aralıkları purge edilmeli; embargo uzunluğu sonuç ufku ve bağımlılık yapısıyla belirlenmeli. Rastgele satır bölme kullanılmamalı.

Altı gün, 14 gün sürebilen bir işlemin tamamını bile gözlemleyemez. Çok sayıda saatlik bar istatistiksel olarak aynı sayıda bağımsız fırsat anlamına gelmez. Tek bir evrensel “yeterli trade sayısı” vermek yerine ekonomik açıdan anlamlı minimum etki, belirsizlik, bağımlılık ve rejim kapsamı üzerinden güç planı kurulmalı.

Binance kamu arşivi günlük/aylık dosyalar ve checksum sağlar; arşiv dosyalarının sonradan düzeltilebildiğini de bildirir. Bu nedenle indirilen veri sürümü, hash ve edinim tarihi sabitlenmeli.[3] Bar verisi intrabar sıralamayı tam belirlemez; Nautilus dokümanı bunu açıkça simüle edilen yol olarak anlatır. Stop/target aynı mumda temas ettiğinde alt çözünürlüklü gerçek kayıtlarla duyarlılık kontrolü gerekir.[4]

**7. Gerçek strateji kapasitesini artırabilecek hipotezler**

İlk hedef 28 expert’in sayısını artırmak değil, ayrı hipotezlerin katkısını ölçebilmek. Varsayılan strateji `range-breakout-48-v1`, min_support_quorum=1 ve benchmark CLI’da max_contradiction_tolerance=28 kullanıyor. Bu yapı 28 bağımsız stratejiyi eşit biçimde değerlendirdiğimiz anlamına gelmiyor; fırsat üreticisi hangi olayların değerlendirileceğini baştan sınırlandırıyor.

| Öncelik | Müdahale hipotezi | Beklenen mekanizma | Hipotezi reddedecek bulgu |
|---|---|---|---|
| 1 | Tek, sade swing breakout/squeeze adayı ile baseline kur | Daha az karar, daha açık maliyet ve hata atfı | İşlem sıklığı düşerken net expectancy/risk sonucu düzelmiyor |
| 2 | Rejime göre trend continuation ve range reversion’ı ayır | Aynı piyasa olayında çelişen mekanizmaların kör karışımını azalt | Sabit basit aday OOS’ta yönlendirilmiş modeli geçiyor |
| 3 | Volatilite/yapıya bağlı stop, risk bazlı boyut ve açık tutuş sınırı | Değişen volatilitede daha tutarlı parasal risk | Stop genişliği arttıkça toplam zarar/drawdown aynı veya kötü; maliyet kazanımı yetersiz |
| 4 | Expert/aile bazında çıkarma deneyi | Tekrarlı oylar ve maliyet üreten bileşenler belirlenir | Hiçbir bileşenin koşullu OOS katkısı tekrarlanmıyor |
| 5 | Ortak portföy risk bütçesi ve korelasyon kontrolü | BTC/ETH/altcoin işlemlerinin tek büyük piyasa bahsine dönüşmesi azaltılır | Risk azalırken hedefe göre net fayda kayboluyor |
| 6 | Funding, spread ve gerçek işlem zamanı maliyet filtresi | Küçük brüt fırsatların maliyet altında ezilmesi azalır | Azalan trade sayısı kaçırılan fırsat maliyetini karşılamıyor |

Rust tarafında [squeeze_swing.rs](../../v8-core/src/experts/squeeze_swing.rs) somut başlangıç fikri sunuyor: 48–72 saatlik yapı, volatilite sıkışması, 2 ATR stop ve 336 saat/14 gün expiry. Parametreleri başarı kanıtı saymıyorum; sade karşılaştırma adayı olarak kullanmayı öneriyorum. [MetricObservation](../../v8-core/src/benchmark/observation.rs) ölçüm/otorite/veri rolü ayrımı ve [population.rs](../../v8-core/src/benchmark/population.rs) zaman bölme sözleşmeleri de incelenmeye değer. Var olan kodu topluca kopyalamak yerine her mekanizmanın gerçek yürütme yolunu doğrulamak gerekir.

Trend/momentum için akademik başlangıç dayanağı var; klasik çalışma farklı vadeli piyasalarda 1–12 aylık ufukları inceliyor.[5] Bu bulgu kriptoda 2–14 günlük swing kârını doğrulamaz. Daha kısa ufuk burada sınanacak hipotezdir.

**8. Benchmark seçimi ve funding adaleti**

[Mevcut ekonomik rapor](../../artifacts/benchmarks/economic_report_588d668b.md) 500 barlık dönemde portfolio_P için yaklaşık %0,73 ve equal_weight için %30,64 net getiri raporluyor. Bu ayrı bir koşudur. Aynı raporda strategy funding değeri mevcutken birçok benchmark funding’i MISSING. Netlik etiketi ve maliyet temeli bu açıdan ayrıca denetlenmeli; farkın tamamını funding veya benchmark hatası açıklıyor denemez.

Cash, buy-and-hold, eşit ağırlık, risk hedefli baseline ve sade trend birlikte kalmalı. Mutlak sermaye koruma hedefi ile tam piyasa beta’sını yenme hedefi baştan ayrılmalı. Aynı başlangıç sermayesi tek başına aynı risk demek değildir; volatilite, exposure, leverage, maliyetler ve piyasa taşıma süresi birlikte raporlanmalı. Yeni birincil benchmark gelecekteki koşular için önceden seçilmeli; eski negatif sonuç geriye dönük yeniden etiketlenmemeli.

Swing perpetual stratejisinde funding gerçek zaman çizelgesiyle hesaplanmalı. Binance belirli koşullarda funding aralığının sekiz/dört saatten bir saate değişebildiğini açıklıyor; sabit “her sekiz saatte bir” varsayımı tüm tarihi kapsamaz.[6]

**9. Uygulama sırası ve gerçekçi beklenti**

Aşağıdaki süreler ölçülmüş teslim tarihleri değil, iş paketlerinin büyüklüğüne ilişkin planlama tahminleridir. Mevcut diğer çalışmalar ve veri erişimi süreleri değiştirebilir.

| Aşama | Yaklaşık çalışma | Somut çıktı | Skor/sonuç beklentisi |
|---|---|---|---|
| P0: ölçüme güven | İlk 2–4 çalışma günü | Entry 19 manifesti, yaşam döngüsü PnL uzlaşması, G0 neden kaydı, sürümlü ledger denetimi, score varsayımlarının görünürlüğü | PnL ve skor her iki yönde değişebilir; güvenilirlik artışı beklenir |
| P1: swing değerlendirmesi | Sonraki 3–7 çalışma günü | Tam 12 aylık diagnostic, ısınma/sonuç ufku, ortak riskli benchmarklar, veri rolü kaydı | Örneklem ve hata teşhis kapasitesi artar; kârlılık artışı otomatik değildir |
| P2: sınırlı aday araştırması | Sonraki 1–2 hafta | Bir sade baseline ve az sayıda önceden kayıtlı challenger, gerçek trial matrisi, çıkarma deneyleri | Churn/maliyet ve risk tutarlılığı için olumlu beklenti; net alpha belirsiz |
| P3: dokunulmamış ve prospektif kanıt | Örneklem gereksinimine bağlı | Kronolojik değerlendirme, gerçek shadow kayıtları, yeterlilik değerlendirmesi | G3–G7 ancak ilgili ölçüm gerçekten sağlanırsa iyileşebilir; takvim PASS üretmez |

BROKEN @0 için mevcut ledger’ın ilk kaydı digest-v2; verifier yalnızca v3’ü özel ele alıp diğerlerine input_binding ekliyor. Bu, sürüm uyumluluğu hatası için güçlü bir aday; bu inceleme kök nedeni yeni bir verifier koşusuyla doğrulamadı. Doğru yol tarihsel hash kanonunu sürümüne göre doğrulamak ve bağlı dosyaları kontrol etmek. Eski kanıtları silmek, hash’leri yeniden üretip aynı geçmişmiş gibi sunmak veya “merge olunca kesin düzelir” demek uygun değil.

Bugün savunulabilir sayısal tahmin eski formülün tavanıdır: capability yaklaşık 14,53 ve readiness yaklaşık 2,62. Yeni ölçekte 40/60/80 vaat etmek için veri yok. Asıl beklenen ilerleme; hatalı PnL’nin ortadan kalkması, değerlendirilebilen bağımsız swing fırsatlarının artması, maliyet ve korelasyonun görünmesi ve işe yaramayan expert’lerin seçilmeden önce elenmesidir. Bunlar strateji araştırmasını daha verimli yapar; ekonomik üstünlük ayrı kanıt ister.

İlk önerilen iş paketi: **muhasebe + veri kimliği + sürümlü ledger**, ardından **swing ufuklu uzun diagnostic**, sonra **sade baseline’a karşı az sayıda kontrollü aday**. Mevcut skorun yükselmesini optimize etmek bu sıranın yerini almamalı.

**Kaynaklar**

[1] David H. Bailey ve Marcos López de Prado, *The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting and Non-Normality*, 31 Temmuz 2014. [Yazar nüshası](https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf).

[2] David H. Bailey, Jonathan M. Borwein, Marcos López de Prado ve Qiji Jim Zhu, *The Probability of Backtest Overfitting*. [Yazar nüshası](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf). CSCV/PBO, kronolojik yürütme simülasyonuyla aynı şey değildir; seçim sürecini teşhis etmek için tamamlayıcıdır.

[3] Binance, *Binance Public Data*, erişim 11 Eylül 2026. [Resmî depo](https://github.com/binance/binance-public-data).

[4] NautilusTrader, *Bar-Based Execution*, latest dokümantasyonu, erişim 11 Eylül 2026. [Resmî dokümantasyon](https://nautilustrader.io/docs/latest/concepts/backtesting/bar-execution/). Buradaki genel bar belirsizliği ilkeleri kullanılmaktadır; yerel paket sürümünün tüm ayrıntılarının bu dokümantasyonla aynı olduğu iddia edilmemektedir.

[5] Tobias J. Moskowitz, Yao Hua Ooi ve Lasse Heje Pedersen, *Time Series Momentum*, Journal of Financial Economics, 2012. [Makale](https://fairmodel.econ.yale.edu/ec439/mosk.pdf).

[6] Binance, *Introduction to Binance Futures Funding Rates*, erişim 11 Eylül 2026. [Resmî açıklama](https://www.binance.com/en/support/faq/detail/360033525031).

Yerel birincil kanıtlar ilgili paragraflarda mutlak dosya yollarıyla bağlıdır. Özellikle entry 19’un tam giriş manifesti, eski readiness certificate’ı ve doğru trade bazlı PnL yeniden uzlaşması bu incelemenin açık kalan noktalarıdır.
