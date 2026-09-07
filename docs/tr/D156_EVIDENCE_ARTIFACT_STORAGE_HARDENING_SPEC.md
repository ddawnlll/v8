# D-156 Kanıt, Eser, İstatistik, Benchmark ve Önbellek Sağlamlaştırma Spesifikasyonu

**Durum:** `PROVISIONAL_DECISION`

**Tarih:** 2026-09-06

**İssue kümesi:** #318, #319, #320, #321, #322, #323, #324

**Normatif ilişki:** Bu belge #318 ile #324 arasındaki issue'larda tanımlanan sağlamlaştırma çalışmasının eksiksiz ve yetkili spesifikasyonudur. D-118 f64 değişmezlik yönetişimini ve mevcut V8 kanıt, ekonomik iddia, kalıcılık ve benchmark kararlarını işletir. Bu kararların yerine geçmez, dondurulmuş ekonomik kanıtı yeniden açmaz ve öngörücü kârlılık iddiasına yetki vermez.

**Uygulama dalı:** `audit/research-validity-20260906`

**İlgili PR:** #331, `fix: harden ledger artifacts, statistics, cache, and benchmark inputs`

Bu belge kasıtlı olarak tam metindir. Karar kaydı, changelog, uygulama yerleşimi, PR açıklaması ve monograflar özet niteliğindedir ve bağımsız spesifikasyonlar haline gelmek yerine bu belgeye bağlantı vermelidir.

## 1. Amaç

Bu issue kümesi tek bir bütünlük sınırını ele alır: V8 eksik, bozuk, sentetik, proxy veya kayıtsız kanıtı makul görünen bir ekonomik esere dönüştürmemelidir.

Sınır aşağıdakileri kapsar:

1. sonlu ve açıkça eksik olarak temsil edilen kayan nokta değerleri;
2. aday, nakit akışı, kanıt ve checkpoint kalıcılığının yalnızca-ekleme kuralları;
3. fiziksel eser kimliği ve replay uyumluluğu;
4. senaryo iflası, Monte Carlo yeniden örneklemesi ve SaR eksiklik semantiği;
5. `.parquet` uzantısının arkasına gizlenmiş JSON yerine standart Parquet yayını;
6. tanısal proxy ile kayıtlı tahmin ediciyi ayıran istatistik çekirdeği;
7. ilan edilmiş fiziksel girdileri tüketen ve makbuz uydurmayı reddeden benchmark çalıştırması;
8. içerik-adresli doğrulama ve eski JSONL'den geçiş içeren dayanıklı üretim önbelleği;
9. engellenen veya kabul edilen her yol için eksiksiz denetim izi.

Yönetici ilke şöyledir:

> Yetki veya veri eksikliği açık bir durumdur. Sayısal yer tutucu, uydurma eser veya ima edilen ekonomik iddia değildir.

## 2. Issue izlenebilirliği

### 2.1 #318: D-118 f64 değişmezlik yönetişimi

D-118, kayan nokta kimliği ve değişmezlik politikasının kaynağı olmaya devam eder. D-156 bu politikayı eser ve değerlendirme sınırlarında uygular:

- nicel gözlem olarak dışa açılan değerler mevcut olduklarında sonlu olmalıdır;
- `NaN`, pozitif sonsuz, negatif sonsuz ve geçersiz giriş dizileri reddedilmeli veya açık bir engellenmiş duruma çevrilmelidir;
- eksiklik `Option<T>`, açık bir durum veya tipleştirilmiş hata ile temsil edilmelidir;
- proxy değer, tescilli bir tahmin ediciyi ifade eden alan adını veya sözleşmeyi dolduramaz;
- sonlu bir `f64` fiziksel eser sözleşmesinin parçasıysa serileştiriciler IEEE-754 değerini korumalıdır;
- hiçbir tüketici eksikliği sessizce sıfır, yanlış veya başarılı kapı olarak yorumlayamaz.

D-156 yeni bir kayan nokta toleransı getirmez ve mevcut toleransı sessizce değiştirmez. Tolerans değişikliği ayrı bir karar olarak kaydedilmelidir.

### 2.2 #319: defter, checkpoint ve V8.2 eser sağlamlaştırması

Aday kayıt defteri, nakit akışı defteri, kanıt eserleri, retention kayıtları ve simülasyon checkpoint'leri kendi sınırlarında yalnızca-ekleme veya içerik-adresli kalır. Checkpoint'ler sürüme ve tape hash'ine bağlıdır. V8.2 uyumlu kanıt başlıkları ilan edilmiş generator, sürüm, tier, hash kodlaması ve çalışma sabitlerini korur. Python uygulaması donmuş parity oracle olarak kalır ve bu çalışma tarafından yeniden etkinleştirilmez.

### 2.3 #320: senaryo Monte Carlo, iflas ve SaR fallback semantiği

Senaryo simülasyonu yalnızca sağlanmış fiziksel işlem popülasyonunu yeniden örnekleyebilir. Temel popülasyon üretemez, gözlemleri kaydıramaz veya raporu tamamlanmış göstermek için sabit sonuç kullanamaz. İşlem getirileri yoksa, boşsa, sonlu değilse veya tekrar sayısı geçersizse iflas tahminleri eksik kalır ve rapor `NO_ECONOMIC_CLAIM` olur. Fiziksel likidite/kayma girdisi yoksa SaR çözümlenmemiş kalır.

### 2.4 #321: fiziksel Parquet eseri üretimi

Sözleşmesi Parquet olan her çıktı standart ve okunabilir bir Parquet dosyası olmalıdır. Yazıcı atomik yayın yapar, kaynak sırasındaki satır indekslerini kaydeder, kanonik kaynak satırlarını `row_json` içinde korur, nullable typed skaler sütunlar yazar ve şema ile provenance metadata'sı kaydeder. Yalnızca `.parquet` uzantılı JSON baytları geçersizdir.

### 2.5 #322: istatistik çekirdeği ve proxy DSR/PBO/SPA düzeltmeleri

İstatistik katmanı şunları ayırmalıdır:

- kayıtlı yöntemi ve yetki makbuzu olan gerçek tahmin edici;
- yalnızca proxy olarak gösterilebilen tanısal proxy;
- yetersiz güçlü veya eksik veri sonucu;
- korunum ya da lineage hatası.

Proxy DSR gerçek DSR değildir. Kayıtlı PBO/DSR tahmin edicisi olmayan multiplicity defterinde bu alanlar `None` kalır ve sonuç `NO_ECONOMIC_CLAIM` olur. WRC, gerçek DSR veya Hansen SPA sertifikasyonu ima yoluyla üretilmez.

### 2.6 #323: veriye dayalı BenchmarkRunner

`BenchmarkRunner`, herhangi bir değerlendirici makbuz üretebilmeden önce ilan edilmiş `BenchmarkEvidenceManifest`'i ve her fiziksel eseri doğrulamalıdır. Gözlem, skor, tarih, kapı, istatistik değeri, popülasyon satırı veya yetki makbuzu sentezleyemez. Mevcut çalıştırıcı fiziksel girdi doğrulamasından sonra `BLOCKED_REGISTERED_BENCHMARK_EVALUATOR_REQUIRED` ile durur; çünkü kayıtlı veriye dayalı değerlendirici ve kanıt şeması henüz onaylanmamıştır.

Bu, sınırın fail-closed tamamlanmasıdır. Eski sabit metrikli benchmark uygulamasını geri getirme izni değildir.

### 2.7 #324: üretim önbelleği depolama adaptörü

Üretim önbelleği sürümlü kanonik anahtar, içerik-adresli digest, işlemsel yayın, okuma sonrası doğrulama, compact ve geçerli eski JSONL kayıtlarından kontrollü geçiş içeren dayanıklı `redb` backend'ini kullanır. Bozuk, eski, uyuşmayan veya desteklenmeyen sürüm kayıtları cache hit olarak kabul edilmez.

## 3. Yetki ve kapsam dışı konular

### 3.1 Yetki önceliği

Aşağıdaki sıra geçerlidir:

1. V8 Anayasası ve kayıtlı D-serisi kararları;
2. bu tam metin D-156 spesifikasyonu;
3. aşağıda listelenen mevcut Rust tip ve modül sözleşmeleri;
4. uygulama yerleşimi ve changelog;
5. testler, raporlar ve insan-okur özetler.

Uygulama daha yüksek bir yetkiyle çelişirse incelemede başarısızdır. Özet bu spesifikasyonu geçersiz kılamaz.

### 3.2 Kapsam dışı konular

D-156 şunları yapmaz:

- kârlılığı veya öngörücü edge'i sertifikalandırmaz;
- tanısal, sentetik, karşı-olgusal veya proxy sonucu `SUPPORTED_EDGE` yapmaz;
- yakılmış tanısal bandı veya dondurulmuş holdout'u yeniden açmaz;
- ayrı bir kayıtlı yetki makbuzu olmadan yeni ekonomik tahmin edici getirmez;
- `src/v8/`, kök `tests/` veya kullanımdan kaldırılmış Python runtime'ını yeniden etkinleştirmez;
- gizli cache protokolü, eser formatı veya benchmark popülasyonu eklemez;
- başarılı derlemeyi ekonomik geçerlilik kanıtı saymaz;
- sentetik fixture'ı üretim, değerlendirme, findings defteri veya rapor üretim yolunda kullanmaz.

## 4. Yeniden kullanılacak mevcut tip, trait ve sözleşmeler

Uygulama aşağıdaki sözleşmeleri yeniden kullanmalıdır. Daha sonraki bir karar açıkça izin vermedikçe paralel yeni tipler yasaktır.

| Konu | Kanonik sözleşme | Zorunlu kullanım |
| --- | --- | --- |
| Eser kimliği | `v8-core/src/evidence.rs::Artifact`, `RunConstants`, `ArtifactTier`, `RetentionStore` | Hash kodlamasını, tier anlamını, çalışma sabitlerini, retention çözümünü ve byte-stable read-back'i koru. |
| Aday kalıcılığı | `v8-core/src/candidate.rs::CandidateRegistry`, `TransitionRecord` | Yasal geçişleri ekle, sıra ve event hash'lerini koru, replay ayrışmasında fail closed ol. |
| Nakit akışı kalıcılığı | `v8-core/src/cashflow.rs::CashflowLedger`, `EconomicCashflow` | Korunum kontrollerini ve fiziksel defter provenance'ını koru. |
| Checkpoint kalıcılığı | `v8-core/src/checkpoint.rs::SimulationCheckpoint`, `CheckpointHeader` | Sürümlü, tape-bound, atomik yayınlanan checkpoint kullan. |
| Fiziksel Parquet | `v8-core/src/parquet_artifact.rs::write_json_rows`, `verify_parquet`, `ParquetArtifactReceipt` | Gerçek Parquet üret ve doğrula; gizli JSON üretme. |
| Senaryo çıktıları | `v8-core/src/usdm_sim/scenario_ruin.rs::ScenarioRuinReport`, `SlippageAtRiskReport` | Açık eksiklik ve `NO_ECONOMIC_CLAIM` durumunu koru. |
| İstatistik | `v8-core/src/evaluation/statistics.rs` | `BootstrapResult`, `NullModelResult`, `PermutationResult` ve `ProxyStatistic` tiplerini kullan; `Result` ve `Option` semantiğini koru. |
| Multiplicity | `v8-core/src/evaluation/multiple_testing.rs::ResearchMultiplicityLedger`, `MultipleTestingSummary` | Arama lineage'ını ve deneme korunumunu izle; kayıtlı tahmin edici olmadan estimator alanlarını doldurma. |
| Benchmark girdi bildirimi | `v8-core/src/benchmark/case.rs::BenchmarkCase`, `BenchmarkEvidenceManifest` | Dolu case kimliği ve fiziksel kanıt yolları iste. |
| Benchmark sınırı | `v8-core/src/benchmark/runner.rs::BenchmarkRunner` | Fiziksel kanıtı doğrula, sonra değerlendirici kaydedilene kadar fail closed ol. |
| Cache depolama | `v8-core/src/cache.rs::CacheStore`, `CacheEntry`, `canonical_key`, `key_digest` | Sürümlü içerik-adresli redb depolaması ve doğrulanmış okumalar kullan. |
| Ekonomik firewall | Anayasa Kuralı 12 ve mevcut claim/status alanları | Çözülmemiş, proxy, tanısal ve kayıtsız çıktıları `NO_ECONOMIC_CLAIM` tut. |

## 5. Normatif gereksinimler

Aşağıdaki gereksinimler bağlayıcıdır.

### R156-01: sonlu-mevcut değişmezi

Mevcut nicel skaler sonlu olmalıdır. İstatistik, senaryo, benchmark, cache veya eser sınırına giren sonlu olmayan skaler reddedilmeli veya açık engellenmiş duruma çevrilmelidir. Uygulama sonlu olmayan değeri geçerli gözlem gibi sessizce serileştiremez.

### R156-02: eksikliği koruma

Eksik işlem popülasyonları, eksik episode süreleri, eksik rejimler, eksik likidite girdileri, eksik kanıt manifestoları ve eksik tahmin edici makbuzları eksik kalmalıdır. `None`, engellenmiş durum ve yapısal hata geçerlidir. Sıfır, boş başarı makbuzu veya uydurma default geçerli ikame değildir.

### R156-03: üretimde sentetik girdi yok

Sentetik fixture yalnızca `#[cfg(test)]` altındaki Rust test modüllerinde kullanılabilir. Üretim ve değerlendirme yolları fiziksel veri tüketmeli veya fail closed olmalıdır. Gerçekleşmiş giriş işlemlerini senaryo tanısı için yeniden örneklemek yalnızca popülasyon fiziksel olarak sağlandığında ve sonuç `NO_ECONOMIC_CLAIM` kaldığında serbesttir.

### R156-04: sabit istatistik veya ekonomik iddia yok

P-değerleri, etki büyüklükleri, PBO değerleri, güven değerleri, beklenen iyileştirmeler, Sharpe tabanlı sertifikasyon ve kârlılık sonuçları gerçek girdiler üzerinde kayıtlı tahmin ediciyle hesaplanmalıdır. Sabit değerler ve tarihsel sabitler bir kapıyı veya makbuzu doldurmak için kullanılamaz.

### R156-05: V8.2 eser lineage'ı

V8.2 uyumlu ledger eseri generator/sürüm, hash kodlaması, tier ve çalışma sabitleri dahil fiziksel başlık ve kimlik sözleşmesini korumalıdır. Başlığı eksik veya tutarsız eser geçerli kanıt olarak çözülemez. Donmuş Python dosyaları yalnızca parity oracle'dır ve değiştirilmez.

### R156-06: aday ve nakit akışı yalnızca-ekleme kalıcılığı

Aday geçişleri ve fiziksel nakit akışları sıra, yasal state transition, event kimliği, hash kimliği ve korunumu korumalıdır. Replay uyuşmazlığı, tutarsız yinelenen yayın veya bozuk kayıt hard failure'dır. Sonraki projection önceki fiziksel kaydı yeniden yazamaz.

### R156-07: atomik checkpoint yayını

Checkpoint yazarı parent dizini oluşturmalı, hedef dizinde geçici dosyaya yazmalı, geçici dosyayı flush ve sync etmeli, atomik rename yapmalı ve mümkünse kapsayan dizini sync etmelidir. Checkpoint okuyucu desteklenmeyen sürümü veya tape hash uyuşmazlığını reddetmelidir.

### R156-08: standart Parquet

`write_json_rows` standart Parquet okuyucularının okuyabileceği dosya üretmelidir. Eser kaynak sırasındaki `row_index`, kanonik kaynak provenance'ı için `row_json`, skaler değerler için nullable typed sütunlar ve eser türü, sıra, f64 kodlaması, şema manifestosu ve provenance metadata'sını içermelidir. Boş veya null değerler uydurma sıfıra çevrilemez.

### R156-09: atomik Parquet yayını ve doğrulaması

Parquet dosyası geçici kardeş dosyaya yazılmalı ve atomik yayınlanmalıdır. Dönen makbuz yol, satır sayısı, sütun sayısı, byte uzunluğu ve doğrulama sonucunu içermelidir. `verify_parquet` okunamayan dosyayı reddetmeli ve benchmark tüketicisi kabul etmeden önce fiziksel satır sayısının okunabildiğini doğrulamalıdır.

### R156-10: senaryo iflası girdi sınırı

Senaryo iflas simülatörü yalnızca çağıranın sağladığı sonlu `trade_net_rs` popülasyonunu tüketebilir. Boş girdi, sıfır tekrar veya sonlu olmayan girdi `DATA_BLOCKED_MISSING_OR_INVALID_TRADE_INPUT` üretir. Baseline builder işlem bandı uyduramaz.

### R156-11: SaR epistemik sınırı

Fiziksel likidite girdileri yoksa SaR raporu baseline ve tail değerleri için `Option<f64>` korumalıdır. Eksik likidite girdisi `UNRESOLVED_MISSING_LIQUIDITY_INPUT`, authority `UNRESOLVED` ve claim `NO_ECONOMIC_CLAIM` üretir. Uygulama nominal sabitten kayma çıkaramaz.

### R156-12: gerçek tahmin edici ayrımı

Proxy DSR açık proxy durumu, method version ve `NO_ECONOMIC_CLAIM` taşımalıdır. Gerçek DSR giriş noktası, gerçek tahmin edici ve yetki makbuzu kaydedilene kadar reddetmelidir. Proxy gerçek tahmin edici alanı altında serileştirilemez veya terfi kapısı tarafından tüketilemez.

### R156-13: multiplicity korunumu

Multiplicity defteri `total = survived + pruned + falsified` deneme muhasebesi özdeşliğini korumalıdır. Tam family ve variant lineage'ını tutmalıdır. Arama lineage'ı yoksa durum `DATA_BLOCKED_NO_SEARCH_LINEAGE` olur. Lineage geçerli fakat gerçek estimator tüketmemişse durum `MULTIPLICITY_LEDGER_VALID_GENUINE_ESTIMATOR_REQUIRED` olur ve claim `NO_ECONOMIC_CLAIM` kalır.

### R156-14: benchmark fiziksel kanıt bildirimi

Benchmark case dolu case kimliği, case hash'i, evidence manifestosu ve evidence yollarına sahip olmalıdır. Bildirilen her yol fiziksel olarak mevcut ve okunabilir olmalıdır. Parquet yolu standart Parquet doğrulamasından geçmelidir. Diğer eser yolları dosya metadata doğrulamasından geçmelidir.

### R156-15: benchmark değerlendiricisinin fail-closed sınırı

Kanıt doğrulamasından sonra `BenchmarkRunner`, ayrı bir kayıtlı değerlendirici ilan edilmiş veriyi tüketip kendi makbuzunu üretip ilgili D-serisi yetkisini karşılayana kadar `BLOCKED_REGISTERED_BENCHMARK_EVALUATOR_REQUIRED` döndürmelidir. Runner tarihsel sentetik-dünya yardımcılarını çağıramaz ve default metrik üretemez.

### R156-16: dayanıklı cache kimliği

Cache anahtarı sürüm ön eki, candidate kimliği, action kimliği, simulator hash'i ve data hash'ini içermelidir. Digest yalnızca kanonik anahtardan türetilmelidir. Cache okuması yalnızca saklanan anahtar, saklanan digest, istenen anahtar ve yeniden hesaplanan digest birlikte uyuştuğunda geçerlidir.

### R156-17: işlemsel cache yayını

Dayanıklı cache eklemeleri tek redb write transaction içinde commit edilmelidir. Kısmi yazma geçerli cache hit olarak görünmemelidir. Compact depolamayı azaltabilir ancak kimliği veya çıktı baytlarını değiştiremez.

### R156-18: kontrollü eski format geçişi

Eski JSONL cache açılırken yalnızca geçerli, desteklenen sürümde ve digest'i tutarlı kayıtlar kardeş redb veritabanına geçirilebilir. Bozuk, stale veya uyuşmayan kayıtlar atlanır; kaynak JSONL audit kaynağı olarak kalır. Migration kaydı yeniden yorumlama izni değildir.

### R156-19: iddia yükseltme yok

Tüm D-156 senaryo, istatistik, benchmark, cache ve eser çıktıları mühendislik veya tanısal kanıttır. `SUPPORTED_EDGE`, öngörücü kârlılık veya üretim onayı üretemezler. Ekonomik terfi mevcut WRC, gerçek DSR, Hansen SPA, holdout, ledger ve yetki şartlarına bağlıdır.

### R156-20: fiziksel referans bütünlüğü

Rapor, makbuz, changelog veya spesifikasyon bir eser yoluna ancak yol sözleşme yolu, açıkça bildirilmiş girdi yolu veya fiziksel olarak üretilip doğrulanmış çıktıysa referans verebilir. Uydurma Parquet, ledger, makbuz veya tablo referansı sözleşme ihlalidir.

## 6. Eser sözleşmeleri

### 6.1 Kanıt eserleri

Kanıt eserleri `Artifact` ve `RunConstants` tarafından yönetilir. Eser başlığı veri, kod, konfigürasyon, simulator, risk gate, evaluator version, hash encoding ve tier'ı bağlar. Okuyucular satırları tüketmeden önce başlığı doğrular. Eser retained evidence olarak görülmeden önce retention store referans edilen tape hash'ini çözmelidir.

### 6.2 Aday ve nakit akışı defterleri

Aday registry yasal geçişleri ve event hash'lerini kalıcılaştırır. Nakit akışı defteri mevcut korunum kontrollerinden geçen fiziksel nakit akışlarını kalıcılaştırır. Bu defterler benchmark skor depoları değildir. Tanısal veya karşı-olgusal değer gerçekleşmiş nakit akışı alanına konamaz.

### 6.3 Checkpoint'ler

`SimulationCheckpoint` sürümlü header, bar index'i, tape hash'i ve serileştirilmiş payload içerir. Dosya yayın protokolü geçici yazma, sync, atomik rename ve dizin sync işlemleridir. Beklenmeyen sürüm veya tape hash ile yükleme checkpoint hatası döndürür. Checkpoint replay durumudur, ekonomik kanıt değildir.

### 6.4 Parquet

Parquet eseri iki katmana sahiptir:

1. birlikte çalışabilir skaler erişim için typed nullable sütunlar;
2. kanonik kaynak satırı provenance'ı ve iç içe değerler için `row_json`.

Şema metadata'sı eser türünü, kaynak satır sırasını, IEEE-754 f64 kodlamasını, serileştirilmiş şema manifestosunu ve isteğe bağlı provenance'ı kaydeder. Adaptör Parquet okunabilir diye onun yetkili olduğunu iddia etmez. Yetki, üreten sözleşme ve makbuzdan gelir.

## 7. İstatistik ve senaryo semantiği

### 7.1 Girdi doğrulaması

İstatistik fonksiyonları minimum popülasyon büyüklüğünü, sonlu değerleri ve yeniden örnekleme parametrelerini doğrular. Geçersiz girdiler `Result` hatası döndürür. Yetersiz güçlü veya kullanılamayan null modeller uydurma istatistik yerine açık çözümlenmemiş sonuç döndürür.

### 7.2 Null modeller

Null-model suite eksik episode süresi, eksik rejim bilgisi veya eksik benchmark verisini çözümlenmemiş olarak kaydedebilir. Eksiklik sonucun parçasıdır ve böyle gösterilmelidir. Null-model satırı sessizce atılamaz veya uygun bir p-değeri ile değiştirilemez.

### 7.3 DSR, PBO ve SPA

`compute_proxy_deflated_sharpe_ratio`, `PROXY_NOT_GENUINE_DSR` durumu, `D153_PROXY_DSR_V1` method version'ı ve `NO_ECONOMIC_CLAIM` claim'i olan matematiksel bir tanıdır. `compute_deflated_sharpe_ratio`, gerçek estimator kaydedilene kadar `BLOCKED_GENUINE_DSR_ESTIMATOR_AND_RECEIPT_REQUIRED` döndürür.

`MultipleTestingSummary`, PBO ve family DSR değerlerini `Option<f64>` olarak dışa açar. Bu alanlar ancak kayıtlı estimator eksiksiz lineage'ı tüketip kendi yetki makbuzunu ürettikten sonra doldurulur. Defterin kendisi deneme korunumunu kanıtlar, ekonomik anlamlılığı değil.

D-156 WRC veya Hansen SPA'yı sessizce uygulamaz veya sertifikalandırmaz. Bu estimator'lar Kural 12 altında ayrı yükümlülüklerdir.

### 7.4 Senaryo iflası ve SaR

Senaryo iflası sağlanan gerçekleşmiş kesirsel net-getiri popülasyonunu yeniden örnekler. Durumu ve claim'i bunun senaryo tanısı olduğunu açıkça gösterir. Popülasyon yoksa `build_baseline_scenario_ruin` açık eksiklik üretir. Fiziksel likidite girdileri olmadan SaR alanları `None` kalır. Bu eksiklik sıfır kayma varsayımı değildir.

## 8. Benchmark çalışma topolojisi

Amaçlanan topoloji şöyledir:

```text
BenchmarkCase
  -> BenchmarkEvidenceManifest
  -> fiziksel yol doğrulaması
  -> uygun olduğunda Parquet doğrulaması
  -> kayıtlı evaluator sınırı
  -> evaluator'a ait makbuz
  -> ledger / report projection
```

Mevcut uygulama fiziksel yol doğrulamasından sonra durur; çünkü kayıtlı evaluator sınırı mevcut değildir. Bu kasıtlıdır. Gelecekteki evaluator ayrı bir gözden geçirilmiş Rust uygulaması olarak eklenmeli, tam metin spesifikasyonu ve D-serisi kaydı bulunmalı, makbuz üretmeden önce kanıt girdilerini ve hata semantiğini açıklamalıdır.

Sabit metrik veya sentetik dünya üreten tarihsel uygulama kabul edilebilir fallback değildir.

## 9. Cache topolojisi

Cache yolu şöyledir:

```text
kanonik anahtar
  -> anahtar sürümü doğrulaması
  -> içerik digest'i
  -> redb işlemsel ekleme
  -> doğrulanmış read-back
  -> eser/rapor tüketicisi
```

Bellek içi adaptör birim düzeyi davranış için kalabilir. `CacheStore::open` ile açılan üretim yolları redb kullanır. Eski JSONL migration'ı kardeş redb dosyasına tek yönlüdür ve kaynak audit log'unu silmez.

## 10. Kanonik hata semantiği

Aşağıdaki dizeler kararlı entegrasyon sinyalleridir ve sessizce değiştirilemez:

| Sınır | Hata veya çözümlenmemiş durum |
| --- | --- |
| Benchmark case | `BLOCKED_INVALID_BENCHMARK_CASE` |
| Eksik benchmark manifestosu | `DATA_BLOCKED_NO_VERIFIED_BENCHMARK_EVIDENCE` |
| Boş benchmark manifestosu | `DATA_BLOCKED_EMPTY_BENCHMARK_EVIDENCE_MANIFEST` |
| Eksik benchmark dosyası | `DATA_BLOCKED_MISSING_BENCHMARK_ARTIFACT` |
| Geçersiz Parquet | `DATA_BLOCKED_INVALID_PARQUET_ARTIFACT` |
| Okunamayan benchmark dosyası | `DATA_BLOCKED_UNREADABLE_BENCHMARK_ARTIFACT` |
| Eksik evaluator | `BLOCKED_REGISTERED_BENCHMARK_EVALUATOR_REQUIRED` |
| İflas girdisi | `DATA_BLOCKED_MISSING_OR_INVALID_TRADE_INPUT` |
| Eksik likidite | `UNRESOLVED_MISSING_LIQUIDITY_INPUT` |
| Eksik search lineage | `DATA_BLOCKED_NO_SEARCH_LINEAGE` |
| Estimator'sız geçerli lineage | `MULTIPLICITY_LEDGER_VALID_GENUINE_ESTIMATOR_REQUIRED` |
| Gerçek DSR kullanılamıyor | `BLOCKED_GENUINE_DSR_ESTIMATOR_AND_RECEIPT_REQUIRED` |
| Proxy DSR | `PROXY_NOT_GENUINE_DSR` |
| Claim durumu | `NO_ECONOMIC_CLAIM` |

Hata wrapper'ı iki nokta üst üste sonrasında yol veya bağlam ekleyebilir. Anlamsal prefix makine tarafından bulunabilir kalmalıdır.

## 11. Doğrulama sözleşmesi

Uygulama ancak tüm uygulanabilir kontroller izole PR worktree'sinde çalıştırıldığında kabul edilebilir:

1. `cargo check --manifest-path v8-core/Cargo.toml`;
2. `cargo test --manifest-path v8-core/Cargo.toml`;
3. `cargo clippy --manifest-path v8-core/Cargo.toml`;
4. `.venv/bin/python tools/audit_python_boundary.py`;
5. `python3 tools/audit_synthetic_leakage.py`;
6. `python3 tools/audit_economic_claim.py`;
7. `git diff --check`;
8. standart Parquet read-back ve satır sayısı doğrulama testleri;
9. checkpoint sürüm ve tape-hash ret testleri;
10. cache key, digest, transaction, migration ve stale-entry ret testleri;
11. istatistik sonlu-girdi, eksiklik, proxy-status ve gerçek-estimator bloklama testleri;
12. benchmark evidence-manifest ve evaluator fail-closed testleri.

Sentetik fixture kullanan testler Rust `#[cfg(test)]` modüllerinde kalmalı ve üretim findings, makbuz veya rapor yazmamalıdır.

## 12. OPEN_PIN'ler

### OPEN_PIN-156-1: kayıtlı veriye dayalı benchmark evaluator'ı

#323 veriye dayalı `BenchmarkRunner` adını taşır; ancak repository henüz fiziksel kanıt satırlarını her benchmark alanına, kapıya, makbuza ve authority sınıfına bağlayan kayıtlı bir evaluator şeması içermemektedir. Bu nedenle mevcut runner girdileri doğrular ve fail closed olur. Bu pin'i çözmek için yeni tam metin evaluator spesifikasyonu, D-serisi kararı, uygulama yerleşimi kaydı ve kanıt tabanlı testler gerekir. Pin sabit metrik veya sentetik girdi geri getirilerek çözülemez.

### OPEN_PIN-156-2: gerçek multiple-testing estimator makbuzları

PBO, gerçek DSR, WRC ve Hansen SPA ayrı istatistik yükümlülükleri olmaya devam eder. Makbuz şemaları, estimator sürümleri, data-role kuralları ve yetki sınırları kayıt altına alınmadan hiçbir değer terfi kapısını çalıştıramaz.

### OPEN_PIN-156-3: SaR için fiziksel likidite girdi sözleşmesi

Mevcut SaR çıktısı fiziksel likidite/kayma gözlemleri olmadan kasıtlı olarak çözümlenmemiştir. Gelecek bir likidite sağlayıcısı alanlar sayısal hale gelmeden önce zaman hizalamasını, venue kimliğini, birimleri, eksikliği ve yetkiyi tanımlamalıdır.

### OPEN_PIN-156-4: D-118 tolerans değişiklikleri

D-156 mevcut f64 değişmezliklerini uygular fakat yeni tolerans seçmez. Tolerans, rounding veya bit-identity semantiği değişikliği ayrı bir karar ve tam metin spesifikasyonu gerektirir.

## 13. Değişiklik ve migration kuralları

- Rust değişiklikleri `v8-core/` altında olmalıdır.
- `src/v8/` ve kök `tests/` donmuştur ve değiştirilemez.
- Yeni eser formatları D-serisi kararı ve migration veya ret kuralı gerektirir.
- Yeni evaluator veya estimator kodu proxy uygulamasıyla tip karışıklığına izin veren aynı modül yolunu paylaşmamalıdır.
- Mevcut eski eserler yalnızca açık bir uyumluluk adaptörü ve doğrulama ile okunabilir.
- Dokümantasyon değişikliklerinden sonra iki monograf da yeniden oluşturulmalıdır.
- PR güncellenebilir; ancak hiçbir agent merge yapamaz veya doğrudan `main`'e push edemez.

## 14. Kabul bildirimi

D-156 aşağıdaki koşullarda provisional hardening kararı olarak kabul edilir:

1. Rust uygulaması Bölüm 5 gereksinimlerini karşılar;
2. fiziksel Parquet, checkpoint, evidence, ledger, senaryo, istatistik, benchmark ve cache testleri geçer;
3. zorunlu audit'ler Python boundary değişikliği veya sentetik sızıntı olmadan geçer;
4. İngilizce ve Türkçe karar kayıtları bu tam metin spesifikasyona bağlantı verir;
5. uygulama yerleşimi etkilenen tüm modülleri ve evaluator OPEN_PIN'ini listeler;
6. İngilizce ve Türkçe monograflar senkron dokümantasyondan yeniden oluşturulur;
7. PR #318 ile #324 arasındaki issue'ların implementation ve verification izini içerir;
8. hiçbir makbuz veya rapor, mevcut kayıtlı yetkinin ötesinde ekonomik destek iddia etmez.

Çözülmemiş benchmark evaluator'ı ve gerçek estimator yükümlülükleri kasıtlı, görünür ve fail closed durumdadır. Sessizce tamamlanmış olarak işaretlenmez.
