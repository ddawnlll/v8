# V8.7 Swing Benchmark — v8-next authoritative scope

2026-09-11 owner correction. Eski SB01–SB10 Rust uygulama planı geri çekilmiştir. Bu belge NX00–NX11 paketinin tam normatif şartnamesidir. Uygulama henüz yapılmış değildir.

## 1. Yetki ve sınır
Kullanıcının 2026-09-11 açık talimatı: asıl codebase v8-next; yanlış issue’ları kapat ve v8-next kaynaklarını tarayarak yeniden aç. Bu V8.7 kapsamı için Python/Nautilus uygulama yetkisi geçerlidir; eski Rust-only/frozen ifadeler bu kapsamı veto etmez. v8-core yalnızca referanstır; src/v8 ve kök tests tarihsel oracle olarak korunur. Kapsam için yeniden reactivation izni istenmez.

## 2. Ölçüm sözleşmesi
Gerçek veri, causal chronology, maliyetli equity, immutable trial ailesi ve fiziksel artifact binding zorunludur. Skor artışı ve kârlılık garanti edilmez. NO_ECONOMIC_CLAIM geçerli kalır. Sentetik veriler yalnızca MECHANICS ONLY test sınırındadır. Public capture/local paper kullanılabilir; private emir, transfer, live activation, main push, merge ve tag kapsam dışıdır.

Kaynak tarama SHA: `0990615962431ca8434824b3be33ac076a69f3bf`. Bu SHA yerel kaynak snapshotıdır; yayınlanan docs dalı runtime teslimatı değildir. Başlangıçta implementer kendi kaynak revisionını ayrıca kaydeder.

## 3. Takvim ve kanıt
Önerilen dört yıl: 2022-07-01 dahil → 2026-07-01 hariç. İlk 24 ay development; 2024-07-01→2025-07-01 dört 3-ay diagnostic fold; 2025-07-01→2026-07-01 yalnızca korunmuşluğu kanıtlanırsa final. Önceki ölçümler son yılın burned olduğunu bildiriyor; bu durumda final açılmaz. NX01 gerçek inventory ve burn kaynaklarını doğrular. 6-gün/385/500-bar smoke yalnızca mekanik sağlık kontrolüdür.

## NX01
Önceki envanter planı 10 sembol/48 ay, 394545 satır ve 960 arşiv hash doğrulaması bildiriyor; bu görevin başlangıcında fiziksel artifact ve provenance doğrulanacak. multitape.load_multitape zamanların kesişimini alıyor; bu davranış eksik barları saklayabilir. Funding interval varsayımı 8h; portföy enstrüman mapping dört sembolle sınırlı.

Veri bütünlüğü zaman kesişiminden önce denetlenir. Bilinmeyen kullanım ≠ dokunulmamış veri; veri rolü performansa bakılarak değiştirilemez.

### NX01.R1
Önce mevcut bc1a5aed/92c64b04/73dcfbb8 envanter artifactlarını bul, hashlerini doğrula; eksik kısımları gerçek kaynakta ölç. Sembol/ürün/venue, UTC sınırlar, satır, duplicate, gap, kline/funding/mark kapsamını kaydet; sırf dil değişti diye tam indirme/yeniden envanter yapma.

### NX01.R2
Deney kayıtlarından policy-lineage burn tablosunu doğrula; BURNED_DIAGNOSTIC ve USAGE_UNKNOWN durumlarını protected sayma. Bunlar mevcut DataRole enum değerleri değildir: ResearchStore burn/lineage metadatasına açık mapping yap.

### NX01.R3
Python yükleyicide kesişim öncesi kapsam/duplicate kontrolü yap; sessiz satır düşürmeyi engelle. Mevcut dört sembol mappingini gerçek instrument metadata ile genişlet veya desteklenmeyeni açık reddet; sahte enstrüman üretme.

### NX01.R4
SOL dahil funding olay zamanları ve gerçek interval değişimlerini taşı; eksik mark/funding için absence kaydet. Sabit 8h varsayımından gerçek ölçüm iddiası çıkarma.

### NX01.R5
Data hash, source hash, role/burn, timeframe, tarih ve runtime/config identity bağlayan manifesti ResearchStore ve catalog tüketicilerine bağla; hash/role uyuşmazlığında fail closed.

### NX01.R6
48 ayın 24/12/12 takvimini gerçek UTC tarihlere bağla; son 12 ay burned ise final eligibility false üret. Downstream NX03/NX05 girdilerini read-back doğrula.

## NX02
evaluation/runner.py ilk position_id eşleşmesini yeniden kullanıyor, parse hatasını sıfıra çevirebiliyor ve açık/kapalı sonuçları farklı birimlerle birleştiriyor. economic_benchmark.pair_positions zaten instrument+position_id ve tüketilen kapanış cursorü kullanıyor; bunu yeniden icat etme.

E_t = cash_t + unrealized_t; fees/funding nakitte bir kez sayılır. Return=(E_t/E_(t-1))-1 ayrı boyutsuz seri. Net PnL equity farkına aynı dış nakit akışı düzeltmesiyle eşit olmalıdır.

### NX02.R1
İki raporlama yolunu ortak yaşam döngüsü/muhasebe sözleşmesine bağla; mevcut pair_positions fonksiyonunu konsolide et. Aynı id tekrar kullanımı, instrument ayrımı ve eşzamanlı olay sırasını native fills ile sabitle.

### NX02.R2
Partial close, scale-in/out, reversal ve orphan close davranışını mevcut engine semantiğinden çıkar; tam destek yoksa açık unsupported sonucu ver. Bir close birden fazla campaigni kapatamaz.

### NX02.R3
Tüm raporda equity/PnL birimini açık USDT ve return birimini ayrı tut; parse/NaN/missing fiyatı sıfıra dönüştürme. trade_count completed campaign sayısı; açık risk ayrıca raporlanır.

### NX02.R4
Native equity ile bağımsız fills+fee+funding+unrealized replayi aynı event zamanı/cutoffta uzlaştır; mutlak/bağıl tolerans ve rounding sözleşmesini ölçüm hassasiyetine göre pinle.

### NX02.R5
Açık pozisyonu bar sonu MTM ile taşı; yapay kapanış/gelecek fiyatı kullanma. Baseline kendi pozisyonlarını kendi verisiyle aynı cutoffta yeniden değerler.

### NX02.R6
Gerçek küçük tape üzerinde iki rapor yolunun reconcile tablosunu üret; mekanik tekrar-id, partial ve hatalı sayısal giriş testleri ekle, gerçek tape yoksa ekonomik kanıtı pending bırak.

## NX03
ForwardPlan/freeze_forward_plan/bind_forward_data gerçek saatle prospective ön-kayıt ve tek seferlik veri binding yapıyor, BTC instrument kısıtı var. Bunları geriye dönük koşular için gevşetmek geleceğe sızıntı yaratır.

Warmup ⊂ geçmiş; scored ve fitting outcome aralıkları nedensel olarak ayrık. Prospective freeze time < start time. Historical final erişimi NX09 koşullu eligibility sözleşmesine bağlıdır.

### NX03.R1
48 ay için ilk 24 ay development, sonraki 12 ay dört adet 3 aylık chronological diagnostic fold, son 12 ay yalnızca eligible ise tek final olarak manifest üret. Tarih/role NX01 kanıtına bağlı olsun.

### NX03.R2
Historical plan için mevcut identity/store yapılarını kullan; gerekiyorsa ayrı typed historical plan ekle ve şemasını belgeye kaydet. ForwardPlan gerçek saat, freeze-before-start ve immutable binding kontrollerini koru.

### NX03.R3
Her fold için train_end < scored_start ve warmup/scored sınırlarını explicit UTC tut; warmup barlarını performans/paydaya dahil etme. Minimum historyyi gerçek grammar/protection ihtiyaçlarından türet.

### NX03.R4
Pozisyonları fold sonunda equity ile taşı; traininge sızan label/outcome intervalini purge et. Embargo durationı gerçek maksimum holding/label overlap sözleşmesinden pinle, keyfi sabit kullanma.

### NX03.R5
Karşılaştırılan tüm politikalar aynı takvim, başlangıç sermayesi, risk ve maliyet modelini kullanır; independent fold reset ile continuous portfolio aggregate farkını manifestte açık tut, getirileri çift sayma.

### NX03.R6
Boundary/warmup/burn/overlap regression testleri ve plan read-back üret; protected historical final yoksa bunu açık raporla, tarih veya rolü değiştirerek final yaratma.

## NX04
Yerel V87_V8NEXT_IMPLEMENTATION_PLAN D11 incelemesi zincirin sağlam, verifierın hatalı olduğunu bildiriyor: v2 etiketli geçmişte 10/12 alan ve sonra 13 alan canon kullanılmış. Bu bulgu özgün ledger bytes ve üretici revisionıyla doğrulanmalı; BROKEN @0 otomatik veri kaybı sayılmamalı.

digest = hash(versioned canonical payload); prev_digest önceki gerçek digesttir. Verifier düzeltmesi eski performans/gate iddialarını yeniden sertifikalandırmaz.

### NX04.R1
Özgün ledgerı salt okunur hashle; canonical payload geçişlerini producer commit/schema/provenance ile eşleştir. Seq 0–11/12/13–18 bulgusunu doğrulanmış örneklerle kaydet, varsayım olarak kodlama.

### NX04.R2
Mevcut doğrulayıcıya yalnızca kanıtlanmış historical schema mappingini ekle; rastgele alan altkümesi deneyip hash tutunca kabul eden fallback yasak. Ambiguous schema açık failure verir.

### NX04.R3
Yeni yazımlar için açık yeni digest/schema versiyonu üret; original bytes/digest/prev_hash korunur. Eski kayıtlar yeniden hashlenmez ve geriye dönük PASS düzenlenmez.

### NX04.R4
Chain geçerliliğini artifact varlığı/hash bütünlüğünden ayrı doğrula; hash-chain valid fakat artifact missing durumunu aynı başarıya indirgeme.

### NX04.R5
Her desteklenen historical canon için mekanik golden fixture, tek alan tamper, predecessor tamper, unknown version ve missing artifact testleri ekle. Fixtures test sınırı dışına çıkamaz.

### NX04.R6
Mevcut gerçek ledgerın before/after verifier raporunu ve unchanged file hashini teslim et; G2 bağını yalnızca doğrulanan sonuca göre güncelle.

## NX05
app/benchmark.py kısa 500 bar yükleme kullanıyor; app/portfolio.py default 385 bar. D153 BenchmarkRunner ile economic portfolio yolu ayrı. Catalog/BacktestNode, native execution telemetry ve shared-account engine zaten var.

Aynı run key aynı veri/politika/engine/maliyet/pencereyi ifade eder. Replay/resume çift kayıt veya çift nakit akışı yaratamaz.

### NX05.R1
Her iki CLI yolunda manifest/UTC date range/fold seçimini destekle; 385/500 bar kısayollarını smoke olarak etiketle, release benchmark defaultu gibi sunma.

### NX05.R2
Ortak data/code/lock/config/window/baseline/execution identityyi rapor, telemetry, ledger ve ResearchStorea bağla. Başka run artifactı gate çözemez.

### NX05.R3
Python catalog ve BacktestNode mevcut parity yolunu kullan; uzun pencereyi bounded memory ile işle ve funding writer desteklenmiyorsa yokluğunu belirt, hayali catalog claim üretme.

### NX05.R4
Restart/resume için deterministik run key ve completed-window manifesti kullan; partial çıktıyı başarı sayma, tamamlanmış fold/ledger appendini tekrar yazma.

### NX05.R5
Aynı küçük gerçek pencereyi iki yoldan çalıştırıp trade signatures, equity ve maliyet reconciliation tablosuyla farkları açıkla; funding/no-funding attribution yalnızca signatures aynıysa geçerli.

### NX05.R6
Smoke, 3-ay fold ve uzun benchmark execution profillerini ayır; exact komut, walltime/peak memory ve artifact read-back kaydet. Smoke ekonomik yeterlilik kanıtı değildir.

## NX06
economics/grammar.py beş policy sunuyor; economics/protection.py CampaignProtection/protection_at squeeze için 336 bar expiry içeriyor. adapters/expert_strategy.py ayrı fixed bracket yoluna sahip. experts/squeeze_swing diye mevcut Python modülü yok.

Signal yalnızca karar anında mevcut veriyi kullanır; execution ondan sonra gelir. Aynı risk bütçesi olmadan PnL veya turnover baseline üstünlüğü sayılmaz.

### NX06.R1
Squeeze/trend/range grammar ve koruma çağrı yollarını gerçek benchmarka bağla; mevcut squeeze protectionı kullan. Opportunity TTL ile açık trade expiry arasındaki semantik farkı koru.

### NX06.R2
Önceden kayıtlı küçük baseline ailesi oluştur: cash, mevcut causal trend ve sade swing policy. Başlangıç sermayesi/exposure/risk/ücret/funding/slippage her karşılaştırmada aynı sözleşmeye tabi olsun.

### NX06.R3
Holding sürelerini bar ve saat/gün olarak ölç; 336 barın timeframe dönüşümünü doğrula. Minimum trade hedefini tutturmak için zorunlu emir veya exit gevşetmesi yapma.

### NX06.R4
Stop/target/expiry ve gap execution davranışını native engine olay sırasıyla test et; geleceğin high/low bilgisiyle aynı bar avantajlı fill seçme.

### NX06.R5
Turnover, gross/net, ücret/funding/slippage, exposure/drawdown, holding dağılımı ve açık risk raporla; mark veya calibration yoksa measured-capacity iddiası verme.

### NX06.R6
Policy/config hashlerini fold açılmadan kaydet; mekanik long/short/expiry testleri ve aynı gerçek pencerede karşılaştırmalı receipt üret. Getiri artışı başarı koşulu değildir.

## NX07
alignment/family/reality_check/deflated_sharpe/overfitting modülleri ve ResearchStore zaten var. gate_resolution G5 fallbackları ile economic_benchmark statistics yolunun gerçek trial ailesine bağlanması incelenmeli; sentetik positive/negative control fonksiyonları ekonomik kanıttan ayrılmalı.

Karşılaştırma d_t=loss_baseline,t-loss_candidate,t aynı aralıklarda yapılır. Test ailesi seçimden önce kayıtlıdır; gözlem sayısı bağımsız örneklem sayısı değildir.

### NX07.R1
Tüm denenmiş baseline/challenger/ablationları immutable family manifestine kaydet; yalnızca kazanan denemeleri sayma. Eksik geçmiş denemeleri bilinmiyor olarak bildir.

### NX07.R2
Aynı timestamp ve risk-normalized interval loss serilerinde paired baseline excess hesapla; n_trade yerine bağımlılık ve overlapı hesaba katan örneklem yeterliliği raporla.

### NX07.R3
Mevcut WRC/SPA/DSR/PBO yollarını gerçek family girdilerine bağla; hangisinin diagnostic/hangisinin authority koşulu olduğunu explicit receipt alanında belirt; hardcoded fallbackları kaldır.

### NX07.R4
Block length, resampling seed/count ve multiplicity planını sonuç görülmeden pinle; stationarity/overlap varsayımları geçersizse istatistik UNKNOWN/BLOCKED olsun. Sırf p geçsin diye estimator seçme.

### NX07.R5
Sentetik known-effect/shuffled kontrolleri mekanik testte izole et; ledger/family ekonomik receiptine karışmadığını test et. Yetersiz/missing seri için sıfır p veya perfect confidence üretme.

### NX07.R6
Gerçek fold ailesi için CI, baseline excess ve yöntem/provenance/yeterlilik tablosu üret; olumsuz/sonuçsuz bulgu da geçerli teknik teslimdir.

## NX08
runner abstention denominator28 ve coverage0.60; certificate varsayılan robustness50/economic60; scoring dört sabit domain ve proxy tavana sahip. GATE_DESCRIPTORS etiketleri ile operational resolver alanları tutarlı ele alınmalı; sadece skor formülü değiştirmek yeterli değil.

Skor kanıt değildir; UNKNOWN diagnostic sonucu PASS olamaz. GateVector.readiness ve PolicyCertificate aynı artifact identities ile çalışır; diagnostic calibration live authority vermez.

### NX08.R1
Sabit coverage/uzman paydasını gerçekten eligible domain/decision ölçümlerinden türet; inactive/abstain/missing ayrımını açık göster. Ölçülmeyen domaini başarılı veya ekonomik olarak etkisiz varsayma.

### NX08.R2
Certificate default robustness/economic değerlerini kaldır; raw measurements+versioned transform+denominator+weights+binding dökümü üret. Eksik ölçüm açık missing kalır.

### NX08.R3
G0–G9 etiket/alan/resolver/readiness eşlemesini tek canonical kaynaktan üret; mevcut operational semantiği testle sabitle, belgesiz gate anlamı değişikliği yapma.

### NX08.R4
G3–G7 gerçek aynı-run artifactlarından çözülür; G5 default tape/family, G6 unequal-window comparison ve G7 son100historicalbar pseudo-prospective başarı yollarını kaldır.

### NX08.R5
Eski/new scorer aynı sabit receiptte yan yana hesaplanır, farklı benchmark sürümleri ayrı tutulur; dönüşüm-only artış ile gerçek ölçüm değişimi ayrılır. Hedef skor veya PASS zorlanmaz.

### NX08.R6
Tamper, eksik veri, eksik calibration, aile uyumsuzluğu ve diagnostic-only için gate regressions yaz; cap/readiness üst sınırları formülden türetilsin. Runtime economic claim authority kontrolünü koru.

## NX09
Önceki burn incelemesi son12ayın zaten kullanıldığını ve protected final kalmadığını bildiriyor. Dört yıllık veri dört yıllık unseen test değildir. Daha geniş pencere daha yüksek skor/getiri garantisi değildir.

Final verisi policy seçimi için kullanılamaz. BURNED/USAGE_UNKNOWN dönemler yalnızca diagnostic; geçmiş burn zaman geçince temizlenmez.

### NX09.R1
NX01 burn sonucuna göre 24/12/12 tarihlerini, dört adet 3-ay fold ve sınırlı ablation listesini sonuçları açmadan freeze et; kaynak ve config hashlerini kaydet.

### NX09.R2
Her fold için kayıtlı aynı familyyi çalıştır; tüm başarısız/sonuçsuz denemeleri de kaydet. Fold sonuçlarından yeni policy seçilirse yeni lineage ve ayrı diagnostic deney olarak kaydet.

### NX09.R3
Fold/rejim/sembol kırılımında net excess CI, maliyet, drawdown, holding ve sample sufficiency raporla; tek pooled Sharpe ile heterojenliği gizleme.

### NX09.R4
Tüm son12ay eligible ve önceden korunduğu kanıtlanırsa frozen policy için tek final koşusuna bu issue kapsamı izin verir. Aksi halde finali açma ve NO_PROTECTED_FINAL açıklamasını metadata olarak yaz; bunu GateState enum değeri diye ekleme.

### NX09.R5
Protected final yoksa bu research işi diagnostic report+prospective evidence backloguyla tamamlanabilir; G7/live readiness veya ekonomik edge sertifikası tamamlanmış sayılmaz.

### NX09.R6
Tüm R ölçütlerini gerçek artifactlarla raporla; kazanç negatif/skor düşükse sonucu aynen teslim et. Minimum ekonomik bulgu veya tahmini hedef sayılara ulaşma kapanış koşulu değildir.

## NX10
ForwardPlan, public stream replay/recovery ve EconomicPaperAdapter mevcut. shadow_ingest.load_shadow_fills source=live ve birkaç kolon kontrolünden LIVE_VENUE_SETTLED etiketi üretebiliyor; yerel dosyanın bu etiketi gerçek venue settlement kanıtı değildir.

Prospective data arrival freeze sonrasındadır. Public simulated fill ≠ authenticated venue settlement. Henüz olgunlaşmamış outcome bilinmiyor olarak kalır.

### NX10.R1
Gelecekte başlayacak public-data/local-paper planını gerçek freeze clock ile kaydet; historical replay veya local imported csvyi prospective/live settlement olarak etiketleme.

### NX10.R2
Mevcut capture/replay/forward adapter yolunu bağla; arrival/event timestamp, policy/runtime/lock hashleri ve rolling artifact identityyi kaydet. Sırlar veya özel hesap gerekmez.

### NX10.R3
Restart/recoveryde sequence/gap/duplicate kontrolü ve exactly-once muhasebe etkisini test et; missing intervalde fail closed ve görünür recovery raporu üret.

### NX10.R4
shadow_ingest etiketi için provenance ve gerçek authenticated settlement ayrımını düzelt. Public paper teknik kanıtıdır; source=live veya kolon varlığı authority receiptinin yerini alamaz.

### NX10.R5
Holding/markout olgunluğu ve ön-kayıtlı örneklem koşulları dolmadan G7yi PASS yapma. Teknik altyapı kabulü için bounded capture+restart kanıtı yeterli; uzun ekonomik gözlem ayrı pending evidence olarak görünür.

### NX10.R6
Exact start/stop/resume komutları, gerçek kısa public capture manifesti ve maturity raporu teslim et. Hesap erişimi yoksa private/live kolu kapsam dışı kalır, public çalışma ilerler.

## NX11
Eski SB issue paketi yanlış Rust kapsamındaydı. Yeni paket v8-next Python/Nautilus üzerinde teknik doğruluk ve swing benchmark yapıyor; ekonomik sertifika ayrı kanıt koşullarına bağlı.

Teknik tamamlanma ≠ ekonomik sertifikasyon. Release raporu sadece fiziksel ve revision-bound kanıt içerir; bir R eksikse o R complete değildir.

### NX11.R1
NX01–NX10 her R için commit/check/artifact hash matrisi üret; kapanmış GitHub issueyi tek başına yeterli kanıt sayma. Erişilmeyen veriyi pending yaz.

### NX11.R2
Aktif spec/uygulama planı/issue index/Hermes promptu v8-next olarak tutarlı hale getir; eski Rust planını withdrawn tarihçesi olarak ayır ve yeni issue bağlantılarını koru.

### NX11.R3
Teknik V8.7 kabullerini ekonomik edge/prospective maturity/live izinlerinden ayır; veri tamamen burned olsa da doğru diagnostic benchmark teknik teslim olabilir.

### NX11.R4
Release sınırındaki gerçek kararları çakışmasız D kaydı ve layout/changelog EN/TR belgelerine işle; sıradan implementation için yeni izin merasimi ekleme.

### NX11.R5
Etkilenen Python integration checks ve belge referans kontrollerini çalıştır; release boundaryde mevcut EN/TR monograph komutlarını çalıştır ve sonuçlarını kaydet. Hataları gizleme.

### NX11.R6
Teknik acceptance raporu ve kalan evidence backlogunu yayıma hazır teslim et. Bu issue release/tag/push-main/merge ya da live activation yetkisi değildir.

## NX00
#410–#420 yanlış Rust implementation kapsamı nedeniyle withdrawn ediliyor. NX01–NX11 kaynak taramasına dayanan yerine-geçen pakettir; bu epic tek Hermes goal ile yürütme içindir.

Epic kapanışı alt teknik kabullerin doğrulanmasına bağlıdır. Score/PASS hedefi uğruna veri, aile, eşik veya gate anlamı değiştirilemez.

### NX00.R1
Başlangıç SHA ve dirty treeyi kaydet; gerçek v8-next call graphını alt issue kanıtlarına göre doğrula. Kullanıcı değişikliklerini silme; Rusta implementation yönlendirme.

### NX00.R2
NX01/NX02/NX04 bağımsız başlangıç; sonra NX03; NX05/NX06; NX07; NX08; NX09/NX10; NX11 sırasını uygula. Alt issue bağımlılıklarında gerekli artifactları doğrula, bağımsız işi gereksiz bekletme.

### NX00.R3
Her alt issueyi tek-goal promptuyla R1–R6 tamamla; yeni runtime ve testler v8-next Python içinde. Mevcut accounting/store/protection/forward/statistics arayüzlerini yeniden kullan.

### NX00.R4
Her R için commit+exact check+gerçek artifact bağını ve Completed/Remaining alanlarını güncelle; test fixtureı economic receipt olarak gösterme, code review-only bulguyu test-pass sayma.

### NX00.R5
Eksik gerçek veri/final/prospective maturity durumunu açık evidence backloguna yaz; uygulama ve diagnostic işleri sürdür. Gerçek authority çatışmasında yalnızca ilgili kolu durdur.

### NX00.R6
Tüm teknik kabuller tamamlanınca alt işleri ve epici kanıtla kapat; ekonomik iddia/live yetki verilmiş gibi davranma. Final raporda ölçülen skorlar ile eski tahminleri açıkça ayır.
