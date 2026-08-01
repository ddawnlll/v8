# V8 Araştırma Sentezi: Doğrulama, Mikro Yapı, Simülasyon, Execution ve Portföy Seçimi

## Kapsam, kaynak hijyeni ve kanıt sınırı

Bu bölüm, okuma listesinin **30–60** maddelerini inceler. Liste 31 numaralı girdi
içerir ancak yalnızca **28 benzersiz çalışma** barındırır: 40/41. maddeler aynı
PBO makalesinin sürümleridir, 59. madde 33'ü, 60. madde 34'ü tekrarlar. 28
benzersiz tam metnin tamamı alındı ve okundu. "Erişilebilir" bu yüzden, birincil
bir tam-metin PDF'inin yerel olarak mevcut olduğu anlamına gelir; her makalenin
hakem denetiminden geçtiği, her veri kümesinin herkese açık olduğu ya da her
ampirik sonucun bağımsız olarak yeniden üretilebilir olduğu anlamına **gelmez**.

Üç bibliyografik düzeltme önemlidir:

1. **34 ve 60** maddeleri arXiv:2507.07107'ye bağlanır; gerçek başlığı
   *Machine Learning Enhanced Multi-Factor Quantitative Trading: A
   Cross-Sectional Portfolio Optimization Approach with Bias Correction*'tür—
   "Quantitative Asset Pricing" değil.
2. **37** maddesi arXiv:2512.12924'tür, *Interpretable Hypothesis-Driven
   Trading: A Rigorous Walk-Forward Validation Framework*. Sağlanan metin 34
   maddesinin yanında `2512.12924`'ü yeniden kullansa da, 34'ten farklı bir
   çalışmadır.
3. **44** maddesi aslında *PredictionMarketBench*'tir; tüm trading stratejileri
   için genel amaçlı bir benchmark değildir. Alanı, ikili tahmin-piyasası
   sözleşmeleridir.

Aşağıda kullanılan kanıt etiketleri:

- **Mekanizma kanıtı**, bir makalenin savunulabilir bir nedensel ya da yapısal
  açıklama sağladığı anlamına gelir.
- **Ölçüm kanıtı**, bildirilmiş bir veri kümesi ve saat altında bir gözlemlenebilir
  ya da teşhisi doğruladığı anlamına gelir.
- **Protokol kanıtı**, bir araştırma kontrolünü desteklediği anlamına gelir;
  bir trading edge'i değil.
- **Örnekleyici kanıt**, bir testi motive eden ama onu çözemeyen küçük, sentetik,
  özel ya da zayıf tanımlanmış bir deney anlamına gelir.

### Kanıt-derinliği denetimi

| Liste maddeleri | Tam-metin erişimi | İnceleme derinliği | Niteleme |
|---|---|---|---|
| 30–39 | Birincil PDF, 10/10 | Özet, yöntem, ampirik tasarım/sonuçlar, sonuç/sınırlamalar | Birkaçı yakın tarihli ön baskıdır; 34 özel gerçek veri kullanır; 38 kavramsal bir denemedir. |
| 40–41 | Birincil yazar PDF'si artı SSRN kaydı | CSCV tasarımı, örnekler ve yazarın belirttiği yanlış kullanım/sınırlamalar dahil tam makale | Bir benzersiz makale iki kez temsil edilmiştir. |
| 42 | Birincil yazar PDF'si artı SSRN/DOI kayıtları | DSR inşası, deneme-bağımlılığı tartışması ve sonuç dahil tam makale | Yayımlanmış makale; yine de sızıntı/execution onarımından çok teşhistir. |
| 43–44 | Birincil PDF, 2/2 | Özet, yöntem/veri, ampirik sonuçlar, sonuç/sınırlamalar | 44'ün yalnızca dört benchmark episode'u vardır. |
| 45–58 | Birincil PDF, 14/14 | Özet, veri/koşullandırma değişkeni, ana ampirik/kuramsal sonuç, sonuç/sınırlamalar | 50 ve 51 tezdir; 58 bir incelemedir; gözlemsel etki otomatik olarak nedensel değildir. |
| 59–60 | 33 ve 34 ile aynı birincil PDF'ler | Çapraz-kova etkileri incelendi | Kopya girdilerdir, bağımsız doğrulama değil. |

Bu sentezde hiçbir atanmış çalışma "yalnızca-özet" değildir. Bununla birlikte
kanıt gücü tasarıma, veri erişimine, inceleme durumuna ve tanımlamaya göre
değişir; tam-metin erişimi bir kalite notu değildir.

Bu bölümdeki hiçbir sonuç V8'in kârlı ya da dağıtılabilir olduğunu kurmaz. Bir
getiri tahmini, eşzamanlı bir açıklayıcı ilişki, bir simülatör benchmark sonucu
ve gerçekleştirilebilir bir net portföy etkisi farklı nesnelerdir. V8 bunları
ayrı tutmalıdır.

## Literatür V8'de neyi değiştirir

En güçlü sonuçlar mimari ve epistemiktir:

1. **Araştırma aramasının kendisi modelin parçasıdır.** Deneme sayısı, aile
   üyeliği, varyantlar arası bağımlılık, parametre değişiklikleri ve atılan
   candidate'lar yalnızca-eklenen araştırma artefaktları olmalıdır. Dosya çekmecesi
   (file drawer) eksik olduğunda PBO ve DSR anlamsızlaşır.
2. **Donmuş bir holdout gerekli ama yeterli değildir.** Ona tekrar tekrar
   danışmak ya da yeniden kullanmak onu eğitim verisine dönüştürür. PBO/DSR
   seçimi teşhis eder; ikisi de sızıntıyı, kötü dolumları, eksik maliyetleri,
   rejim kırılmalarını ya da nedensel-olmayan bir feature'ı onarmaz.
3. **Simülasyon sadakati iddiaya-görelidir.** Bar replay'ı yavaş, agresif emir
   hipotezlerini yanlışlayabilir ama kuyruk, maker-dolumu ya da saniye-altı OFI
   iddialarını destekleyemez. Emir-akışı makaleleri başlıca, katı sadakat
   sınırları için bir argümandır; Level-3 simülasyon hakkı değil.
4. **Emir akışı kalıcıdır ama etki duruma-bağlıdır.** Uzun bellek, derinlik,
   spread, tick boyutu, haber, günün saati, bir olayın fiyat-değiştiren durumu
   ve diğer varlıkların akışı önemlidir. Statik bir global OFI katsayısı kabul
   edilebilir bir execution modeli değildir.
5. **Eşzamanlı uyum öngörülebilirlik değildir.** Çok yüksek OFI-fiyat-değişimi
   \(R^2\)'si aynı saatteki bir fiyat-oluşumu özdeşliğini tanımlayabilir.
   Değerin trade etmek için yeterince erken mevcut olduğunu kanıtlamaz.
6. **Etki tek bir evrensel skaler fonksiyon değildir.** Doğrusal kısa-ufuk OFI
   yasaları, geçici/geçmişe-bağımlı propagatörler, sigmoidal toplu etki, kare-kök
   metaorder etkisi ve çapraz etki; farklı koşullandırma değişkenleri ve
   toplama ölçekleri altında hepsi doğru olabilir.
7. **Execution ve alpha operasyonel olarak ayrılabilir, istatistiksel olarak
   bağımsız değildir.** İşlem-yapılabilirlik maskeleri, maliyet/kayma stresi,
   derinlik ve etki koşullandırması hem feature dağılımını hem de candidate
   sıralamasını değiştirebilir.
8. **Sıralama görev-yetkisi- ve çekişme-bağımlıdır.** Yalnızca birden çok kabul
   edilebilir candidate gerçek bir sermaye/risk/likidite bütçesi için rekabet
   ettiğinde haklıdır. Eşleştirilmiş belirsizlik ya da maliyet stresi olmadan
   küçük Sharpe farkları bir sıralama temeli değildir.

---

## I. Backtest aşırı-uyumu, çoklu test ve doğrulama protokolleri

### 30. Backtest seçimi için kovaryans cezaları

Koshiyama ve Firoozye; in-sample korelasyon/Sharpe tahminleri için serbestlik-
derecesi düzeltmeleri türetir ve 1.361 hisse senedi, para birimi ve sabit-getirili
seri üzerinde saf gecikme seçimini, AIC'yi, örtük-Sharpe düzeltmesini ve
ayarlanmış bir \(R^2\) ölçütünü karşılaştırır. Deney, genişleyen in-sample
tahmini, 21 günlük OOS partilerini, ilk 1.008 günlük pencereyi, 18 aday gecikme
uzunluğunu ve hem OLS hem de toplam en küçük kareleri (TLS) kullanır. Önerilen
kovaryans cezaları, saf seçime göre gerçekleşen OOS Sharpe'ını ve beklenen ile
gerçekleşen Sharpe arasındaki uyumu iyileştirir; TLS genellikle daha küçük gecikme
uzaylarına cezalandırır ve bu tasarımda OLS'yi geçer
([arXiv:1905.05023](https://arxiv.org/abs/1905.05023)).

**Desteklenen.** Karmaşıklık-farkında amaçlar, doğrusal bir gecikme modeli seçerken
iyimserliği azaltabilir ve performans tahmini, yalnızca kazanan in-sample
istatistiği değil, etkili serbestlik derecelerini yansıtmalıdır.

**Sınırlar.** Yöntem, sinyal ve getiri için yönetilebilir bir ortak davranış
varsayar ve tek bir doğrusal otoregresif strateji ailesinde test edilmiştir.
Makale örtüşen genişleyen değerlendirmeler kullanır ve çapraz-varlık eşleştirilmiş
testler bildirir; varlık ve zaman bağımlılığı saf kesinliği iyimser yapar. Bu aile
içinde daha yüksek bir OOS Sharpe'ı, sömürülebilir bir V8 Expert'inin kanıtı
değildir. Düzeltme; gecikme ızgarasının dışındaki açıklanmamış aramayı, nedensel
veri kusurlarını ya da execution hatasını hesaba katmaz.

**V8 çıkarımı.** Her Expert/scorer/ranker varyantı için hem nominal hem de etkili
karmaşıklığı sakla. Kovaryans cezasını yalnızca daha basit sabit baselinelara
karşı iç bir karşılaştırıcı olarak kullan. Kronolojik donmuş OOS'un, aile-çapında
deneme muhasebesinin ya da simülasyon sertifikasyonunun yerini alamaz.

### 31. Aşırı-uyum karşıtı filtre olarak GAN-üretilmiş yollar

Sun ve Lyuu; geometrik Brownian hareketi ve AR(2) tarafından üretilen yollarda
tekrarlayan GAN'lar eğitir ve sonra üretilen yollardaki backtestlerin, al-ve-tut
ile hareketli-ortalama stratejilerini Monte Carlo gerçeğine benzer şekilde
sınıflandırıp sınıflandırmadığını sorar. GAN bazı marjinal yol özelliklerini
yeniden üretir; karışıklık matrisleri, sentetik-yol değerlendirmesinin kontrollü
oyuncak modellerde kasıtlı olarak pozitif olanları null kombinasyonlardan ayırt
edebildiğini gösterir ([arXiv:2209.04895](https://arxiv.org/abs/2209.04895)).

**Desteklenen.** Üretici bir model, yalnızca çekişmeli kayıp ya da görsel
benzerlikle değil, göreve-koşullu—strateji sıralamalarının ya da reddetme
kararlarının aktarılıp aktarılmadığıyla—değerlendirilebilir.

**Sınırlar.** Makale, bir İngilizce çevirinin güncelliğini yitirmiş iddialar
içerdiğini açıkça not eder. Veri-üreten yasalar bilinir, düşük-boyutlu ve
durağandır; örneklem-boyutu bulgusu GAN ezberlemesini yansıtabilir. GBM/AR(2);
volatilite kümelenmesini, sıçramaları, etkiyi, stratejik tepkiyi, çapraz-varlık
bağımlılığını, kuyruklamayı ve rejim değişimini atlar. Bir üreticiyi tek bir
tarihsel gerçekleşme üzerinde eğitmek, görülmemiş rejimler hakkında bağımsız bilgi
yaratamaz. Sentetik bir backtest, kaynak simülatörünün yanlılıklarını sadakatle
yeniden üretebilir.

**V8 çıkarımı.** Sentetik yollar stres araçlarıdır, asla piyasa edge'i kanıtı
değildir. Herhangi bir V8 üreticisi, görev-tabanlı posterior tahmin kontrolleriyle
karşılaşmalıdır: kuyruk/bağımlılık istatistikleri, candidate sıklığı, durum
işgali, maliyet/etki tepkisi ve ayrılmış gerçek bloklar üzerinde sıra korunumu.
Bir üreticinin başarısızlığı kullanımını engeller; başarısı yalnızca stres testine
izin verir.

### 32. Bir backtest PnL'sini iskonto etmek

Rej, Seager ve Bouchaud; başlangıçta geçerli bir stratejiyi gerekli bir Sharpe
eşiğini geçene kadar değiştiren bir araştırmacıyı modeller. "Cımbızlar" (tweaks)
seçili PnL bölümlerinde yönü çevirir ve varsayıma göre gerçek OOS performansını
düşürür. Gerçek Sharpe'ın, eşiğin, backtest uzunluğunun ve araştırmacı
özgürlüğünün bir fonksiyonu olarak bir aşırı-uyum faktörü—beklenen seçilmiş
in-sample Sharpe'ın beklenen OOS Sharpe'ına bölümü—türetirler. CTA-benzeri
örnekleyici ayarlarda (gerçek Sharpe 0.3–0.5, eşik yaklaşık 0.7, cımbız oranı
yaklaşık 0.05) faktör yaklaşık ikidir ([arXiv:1902.01802](https://arxiv.org/abs/1902.01802)).

**Desteklenen.** Araştırmacı davranışı ve kabul eşikleri, her değişikliğin makul
bir anlatısı olsa bile seçim baskısı yaratır; düşük-Sharpe etkileri özellikle
savunmasızdır.

**Sınırlar.** İşaret-çevirme modeli, Gauss segment Sharpe yaklaşımı, sabit cımbız
oranı ve her değişikliğin gerçeği bozduğu varsayımı stilize edilmiştir. "Backtest
PnL'sini ikiye böl" evrensel bir tahmin edici değildir. Daha uzun geçmiş yalnızca
davranışsal ve durağanlık varsayımları altında yardımcı olur.

**V8 çıkarımı.** Mutasyon soyağacını ve her Expert revizyonunun yapılma nedenini
kaydet. Başarısız bir kapıdan sonraki her kurtarma değişikliğini yeni bir aile
üyesi olarak ele al ve son dokunulmamış değerlendirmeyi sıfırla. Makaleyi sayısal
bir kırpma değil, şüphecilik için niteliksel bir öncül olarak kullan.

### 33. DRL kripto para trading'i ve CSCV/PBO

FinRL çalışması; beş dakikalık kripto para verisi üzerinde PPO, TD3 ve SAC için
hiperparametre seçimine kombinatoryal olarak simetrik çapraz-doğrulamayı gömer.
2.700 kombinasyonluk bir uzaydan çizilen 50 hiperparametre kümesi dener, modelleri
%10 eşikli PBO ile etiketler ve 2022 kripto çekişi sırasındaki tek bir kısa test
dönemini değerlendirir. Bildirilen PBO: PPO için %8,0, TD3 için %9,6 ve SAC için
%21,3'tür; tüm portföy getirileri negatiftir ve seçilen PPO karşılaştırıcılardan
daha az kaybeder ([arXiv:2209.05559](https://arxiv.org/abs/2209.05559)).

**Desteklenen.** DRL sonuçları hiperparametrelere son derece duyarlıdır; açık bir
arama-ailesi teşhisi görünüşte güçlü bir ajanı reddedebilir. "En az aşırı-uyumlu"
olanın yine de para kaybetmesi, seçim istikrarı ile ekonomik değer arasındaki
önemli bir ayrımdır.

**Sınırlar.** Test yalnızca 58 günü kapsar, eşik bu çerçeveye rağmen geleneksel
bir Neyman–Pearson testi değildir, CVIX tasfiye kuralı başka bir tasarım
serbestlik derecesidir ve execution maker/kuyruk iddiaları için yeterince
belirtilmemiştir. Yazarlar limit emirlerin, trade kapanışının, daha geniş bir
evrenin ve daha zengin feature'ların gelecek çalışma olduğunu kabul eder.

**V8 çıkarımı.** Bu, V8'in öğrenilmiş execution/RL'yi başlangıç mimarisinden hariç
tutma kararını destekler. Yeniden ele alınırsa, politikaları tohumlar ve sabit
arama bütçeleri arasında karşılaştır, PBO'yu bir teşhis olarak kullan,
eşleştirilmiş bilgi/aksiyon kısıtlarında deterministik bir risk politikası
değerlendir ve sertifikalı bir olay defteri gerektir.

### 34. Maske-önce çapraz-kesit trading ve portföy optimizasyonu

Sağlanan başlık yanlıştır. Du'nun makalesi; 213 faktörlü, yalnızca-long bir Çin
A-hisse senedi hattını, zaman-noktası işlem-yapılabilirlik maskesiyle, asimetrik
MSE ile, GBM blok-bootstrap artırımıyla ve Ledoit–Wolf/Markowitz tahsisiyle
inceler. Ana mühendislik iddiası "yukarı-akış kontaminasyonu"dur: fiyat-limit
gözlemlerinin sonradan kaldırılması başarısız olur çünkü yuvarlanan operatörler
zaten çalıştırılamaz kapanışları yutmuştur. Bildirilen gerçek panelde, tam maskenin
kaldırılması görünür IC'yi yükseltir ama gerçekleştirilebilir IC ve Sharpe'ı
düşürür; makale 5–8 bps doğrusal ciro maliyetleri ve %3 ağırlık sınırı kullanır
([arXiv:2507.07107](https://arxiv.org/abs/2507.07107)).

**Desteklenen.** İşlem-yapılabilirlik; feature hesaplamasına, eğitim etiketlerine,
portföy inşasına ve simülasyona yayılması gereken birinci sınıf, monoton bir veri
sözleşmesidir—nihai bir satır filtresi değil. Görünür tahmin uyumu, ekonomik
geçerlilik düştükçe yükselebilir.

**Sınırlar.** Gerçek veri kümesi özeldir, nihai OOS penceresi yalnızca
2022–2024'tür, bildirilen geliştirme araması yaklaşık 50 etkili konfigürasyon
kullanır ve maliyet modeli boyut için doğrusal ve iyimsedir. GBM artırımı
kuyrukları küçümser; canlı ya da kuyruk-düzeyi kanıt yoktur. Bildirilen DSR, her
konfigürasyonun paylaştığı bir yanlılığı düzeltemez.

**V8 çıkarımı.** Neden kodları ve monoton maskelerle `tradable_for_feature`,
`tradable_for_decision` ve `tradable_for_execution` alanları ekle. Ranker
girdileri ve karşı-olgusal etiketler ulaşılamaz fiyatları hariç tutmalıdır. Bir
"maske ablasyonu"nu geçerlilik testi olarak çalıştır: maskenin kaldırılması
görünür metrikleri iyileştiriyorsa, hat bunu kutlamak yerine bir çalıştırılabilir-
bilgi çelişkisi olarak işaretlemelidir.

### 35. GT-Score

GT-Score; ortalama getiriyi, z-benzeri bir benchmark kapısını, \(R^2\)-tarzı
tutarlılığı ve aşağı-yön sapmasını birleştirir. 50 ABD büyük-ölçek hisse senedi,
15 rastgele tohum, 9.000 Monte Carlo optimizasyon denemesi ve 5.340 walk-forward
denemesi üzerinde RSI, MACD ve Bollinger stratejileriyle test edilmiştir. Eğitim
performansının Sharpe/Sortino/basit-kâr amaçlarından daha fazlasını korur ama ham
test getirisi biraz daha düşüktür ve eşleştirilmiş etki büyüklükleri çok küçüktür.
Makale, walk-forward avantajlarının birkaç dönemde tersine döndüğünü ya da
kaybolduğunu ve ana tabloların işlem maliyetlerini atladığını açıkça bildirir
([arXiv:2602.00080](https://arxiv.org/abs/2602.00080)).

**Desteklenen.** Bir optimizasyon hedefi, zirve getiriyi açıkça istikrar için
feda edebilir ve dönem-dönem kanıt, tek bir havuzlanmış orandan daha
bilgilendiricidir.

**Sınırlar.** "%98 aşırı-uyum azalması", seçilen eğitim-doğrulama genelleme
oranındaki göreli bir artıştır; ölçülmüş %98'lik bir yanlış-keşif azalması
değildir. z kapısı trade getirilerini yaklaşık IID/Gauss olarak ele alır, gömülü
bir çoklu-test düzeltmesi yoktur, günlük barlar execution'ı doğrulayamaz ve 0–10
bps duyarlılığı spread/etki/likiditeyi atlar.

**V8 çıkarımı.** GT-Score'u V8'in evrensel scorer'ı olarak benimseme. Onu maliyet-
yalnızca, deterministik kanıt skoru, lojistik ve sığ ağaç baselinelarının yanında
kayıtlı bir baseline olarak yeniden üret. Tümünü eşleşen kapsamda ve gün/oturum-
bloğu belirsizliğiyle yargıla; görünür istikrarı artımlı fayda olmadan pozisyon
baskılamasından geliyorsa herhangi bir hedefi reddet.

### 36. AlgoXpert IS–WFA–OOS protokolü

AlgoXpert kronolojik bir dağıtım iş akışı önerir: istikrarlı bir IS platosu, üç
temizlenmiş yuvarlanan WFA katı, çoğunluk-geçişi artı felaket drawdown vetosu ve
sonra kilitli bir yıllık OOS. USDJPY M5 örneği MT5 "Every Tick", 2022–2025 Exness
verisi, beş günlük temizleme ve önceden bildirilmiş Sharpe/Calmar/drawdown
kapılarını kullanır. Üç WFA katından ikisi geçer ve kilitli 2025 OOS bildirilen
performans kapılarını aşar ([arXiv:2603.09219](https://arxiv.org/abs/2603.09219)).

**Desteklenen.** Aşama kapıları, parametre kilitleri, plato seçimi, açık
başarısızlık semantiği, kat sınırlarında normalleştirilmiş durum ve WFA
başarısızlığından sonra açılmayan bir OOS yararlı yönetişim örüntüleridir.

**Sınırlar.** İddia edilen execution-farkında çerçeve execution-doğrulanmış
değildir: gecikme ya da olumsuz kayma stresi çalıştırılmamıştır, bir trade-
yoğunluğu ölçütü doğrudan bildirilmemiştir, yalnızca bir çift/broker kullanılır
ve kat 1'deki çarpıcı bir eğitim/test tersine dönüşü bir denetim bayrağı olarak
bırakılır. Dört doğrulama-sonrası varyant daha fazla seçim getirir ve küçük
farklar test edilmemiştir.

**V8 çıkarımı.** Karar izini benimse; sayısal eşiklerini değil. Eksik bir kapı
alanı `UNKNOWN`'dur, asla örtük `PASS` değil. Herhangi bir dağıtım hükmünden önce
execution'ı strese sok. Başarısız kat bilinen bir hedef rejimi temsil ettiğinde
ya da paylaşılan bir operasyonel değişmez başarısız olduğunda V8, çoğunluk-
geçişinden daha katı olmalıdır.

### 37. Yorumlanabilir hipotez-güdümlü walk-forward doğrulama

Bu ayrı makale, beş el-yapımı günlük-OHLCV hipotezi için 2015–2024 arasında 34 üç
aylık OOS testi çalıştırır. %0,55 yıllık getiri, Sharpe 0,33, maksimum drawdown
−%2,76 ve istatistiksel anlamlılık yok bildirir: t-testi \(p=0,34\), bootstrap
aralığı sıfırı geçer, permütasyon \(p=0,98\) ve gözlenen etki için yalnızca
yaklaşık %12 güç. Performans düşük-volatilite yıllarında negatif, yüksek-
volatilite yıllarında pozitiftir ([arXiv:2512.12924](https://arxiv.org/abs/2512.12924)).

**Desteklenen.** Yararlı bir laboratuvar, iyi enstrümante edilmiş bir
null/yetersiz-güç sonucu döndürebilir. Rejim ayrıştırması, bir toplu istatistiğin
işaret değişimlerini gizlediğini açığa çıkarabilir.

**Sınırlar.** "Mikro yapı sinyali" etiketi günlük OHLCV için fazla güçlüdür. Sabit
5 bps kayma boyutu, spread'i ya da günün saatini modellemez; 34 üç aylık gözlem
zayıftır ve rejim sınırları sonradan (post-hoc) belirlenmiştir. Makale, kanıt
olmadan LLM/RLHF uzantıları hakkında spekülasyon yapar.

**V8 çıkarımı.** İkili bir kazanç zorlamak yerine `NO_OPPORTUNITY`,
`HINDSIGHT_ONLY`, `WEAKLY_SELECTABLE` ve `FORMALIZATION_CANDIDATE`'ı koru.
Anlamsız-olmayan ama operasyonel olarak temiz bir deney, değerli bir falsifikasyon
sonucu olarak kalırken terfiyi engellemelidir.

### 38. Piyasaları tahmin etmek zordur

Noguer'in denemesi; arbitrajsızlık, bilgisel verimlilik, öngörülebilirlik ve net
sömürülebilirliği ayırt eder. Nedensel piyasa yapısının çok sınırlı ölçeklenebilir
net alpha ile bir arada var olabileceğini savunmak için \(P\)–\(Q\) kamasını,
Doob ayrıştırmasını, filtrasyon-göreli tahmini, kapasiteyi, etkiyi, dönüşlülüğü ve
rejim belirsizliğini kullanır. Açık ampirik dizisi: tahmin → risk ayarı →
maliyetler/etki → kapasite → OOS hayatta kalma → canlı dönüşlü çürümedir
([arXiv:2606.08209](https://arxiv.org/abs/2606.08209)).

**Desteklenen.** Bu disiplinli bir taksonomi ve bir falsifikasyon gündemidir; yeni
ampirik kanıt değil. Volatilite/emir-akışı öngörülebilirliği, sessizce pozitif bir
koşullu-ortalama trade iddiasına dönüştürülemez.

**Sınırlar.** Alıntılanan sonuçların çoğu klasiktir ve birleştirme kavramsaldır.
Stilize lognormal modellerdeki entropi özdeşlikleri V8'in ulaşılabilir bilgisini
tahmin etmez. "Piyasalar nedenseldir" eyleme-geçirilebilir bir feature
spesifikasyonu değildir.

**V8 çıkarımı.** Her iddia kendi filtrasyonunu, aksiyon saatini, maliyet/kapasite
alanını ve hayatta kalma ufkunu adlandırmalıdır. Tahminî bir ilişkiden çıkarılan
nedensel bir hikâye yerine `mechanism_unknown` tercih edilir.

### 39. Doğrusal stratejiler için analitik IS/OOS Sharpe oranları

Jacquier, Muhle-Karbe ve Zhu; doğrusal tahmin sinyalleriyle sürülen Markowitz
portföyleri için beklenen IS ve OOS Sharpe oranlarını türetir. Karmaşıklık hem
sinyallerle hem de varlıklarla büyür; daha uzun örneklemler ve daha yüksek gerçek
sinyal gücü replikasyon oranını iyileştirir. 12 varlık ve 37 sinyalli bir emtia-
vadeli-işlem simülasyonu, on yıllık bir backtestten sonra yalnızca yaklaşık %30
beklenen replikasyon oranı verir. Analitik yaklaşımlar AR(1) sinyalleri ve kalın-
kuyruklu yenilikler altında yakın kalır. 39 sinyalli, 1926–2024 hisse-senedi-primi
veri kümesi, öngörülen karmaşıklık/örneklem-uzunluğu örüntülerini yeniden üretir
([arXiv:2501.03938](https://arxiv.org/abs/2501.03938)).

**Desteklenen.** V8'e az sayıda Expert/feature ve uzun savunulabilir geçmişle
başlamak için nicel bir neden vardır; kesitsel boyut örneklem kapasitesini
tüketir.

**Sınırlar.** Ana formüller doğrusal/Gauss-IID ortamlar içindir. Ampirik egzersiz,
örtük sinyal gücünü kısmen gerçekleşen OOS Sharpe'ına kalibre eder; bu yüzden
bağımsız tahminden çok ilişkileri doğrular. Makale, tek-model tahmin hatasını
birleştiren çoklu testi açıkça bir kenara bırakır.

**V8 çıkarımı.** Feature, varlık, Expert ya da ranker etkileşimi eklemeden önce
bir karmaşıklık/örneklem yeterlilik raporu gerektir. Ortak şoklar ve ilişkili
akış etkili örneklem boyutunu çökerttiğinde "daha fazla varlık" bedava
replikasyon değildir.

### 40. Backtest Aşırı-uyum Olasılığı (PBO/CSCV)—dergi/yazar-PDF kaydı

40 ve 41. maddeler aynı çalışmanın dergi/çalışma-kağıdı sürümleridir; iki bağımsız
kaynak değil. Bailey ve arkadaşları bir strateji-zaman performans matrisi inşa
eder, simetrik IS/OOS bölümlerini sayar, IS kazananını seçer ve OOS sıra logitini
ölçer. PBO, seçilen IS kazananının OOS medyanının altına düştüğü kesirdir. Mevsimsel
strateji örneklerinde, rastgele bir yürüyüş üzerinde optimizasyon IS Sharpe'ı 1,27
ama PBO yaklaşık %55 üretir ([yazar PDF](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf); [SSRN 2326253](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253)).

**Desteklenen.** PBO, kazanana tek-denemeli bir p-değeri atamak yerine bir *seçim
sürecini* doğrudan denetler. Seçilen performans istatistiğine göre model-serbesttir.

**Yazarların belirttiği sınırlar.** Simetrik bölme, güçlü otokorelasyonlu
stratejiler için uygunsuz olabilir; tüm denemeler açıklanmalıdır; yönlendirilmiş
aramanın ara yinelemeleri dikkatli tanım gerektirir; PBO kötü maliyetleri, look-
ahead'i ya da yanlış simülasyonu tespit etmez; örneklem dışı kırılmalar görünmez;
yüksek PBO her üyenin yeteneksiz olduğu anlamına gelmez; PBO'ya optimize etmek
yanlış kullanımdır.

**V8 çıkarımı.** PBO'yu yalnızca, tam aile matrisini sakladıktan sonra, önceden
kayıtlı, tutarlı bir aile üzerinde hesapla. Onu asla Expert/scorer/ranker
ayarlarını ayarlamak için kullanma. Yalnızca bir skaler değil, OOS bozulmasının ve
sıralarının dağılımını raporla.

### 41. Backtest Aşırı-uyum Olasılığı—yinelenen SSRN çalışma-kağıdı kaydı

41. madde SSRN 2326253'tür, 40. maddenin çalışma-kağıdı kaydıdır ve bağımsız bir
replikasyon sağlamaz. Yöntemi, kanıtı, sınırlamaları ve V8 çıkarımları bu yüzden
40. madde altında analiz edilenlerle aynıdır. Kaynak (provenance) için her iki
kaynak bağlantısını da koru, ama bir benzersiz çalışma ve bir kanıtsal katkı say
([SSRN 2326253](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253)).

### 42. Deflate Edilmiş Sharpe Oranı

Bailey ve López de Prado; olasılıksal bir Sharpe istatistiğini (örneklem uzunluğu,
çarpıklık, basıklık) etkili sayıda bağımsız deneme arasındaki beklenen maksimum
Sharpe ile birleştirir. DSR, gözlenen Sharpe'ın sıfırdan çok, seçim-kaynaklı
benchmark'ı aşıp aşmadığını sorar ([yazar PDF](https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf); [SSRN 2460551](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551); [DOI](https://doi.org/10.3905/jpm.2014.40.5.094)).

**Desteklenen.** Kazanan Sharpe, normal-olmayan getiri momentleri, iz uzunluğu,
denenen Sharpe değerleri arasındaki dağılım ve denemelerin sayısı/bağımlılığı
birlikte kanıtsal gücü belirler.

**Sınırlar.** Stratejiler ilişkiliyken ve deneme sayısı örneklem uzunluğunu
aştığında etkili bağımsız deneme sayısını tahmin etmek zordur. Ortalama korelasyon
yalnızca doğrusal bağımlılığı yakalar. DSR bildirilen aileye dayanır; sızıntıyı,
ortak simülatör iyimserliğini, Sharpe tahmin edicisinden atlanan zaman
bağımlılığını, maliyet yanlış belirlemesini ya da rejim değişimini düzeltmez.

**V8 çıkarımı.** DSR, blok-bootstrap belirsizliğinin ve son donmuş OOS'un yanında
açıklama-destekli bir teşhistir—kendi başına bir terfi kapısı değil. Etkili-deneme
varsayımının incelenebilir olması için deneme kovaryansını/soyağacını sakla.

### 43. Yüksek-verimli varlık fiyatlaması

Chen ve Dim; 136.000 long-short muhasebe-oranı, geçmiş-getiri ve ticker
stratejisine ampirik Bayes uygular. Yuvarlanan, gerçek-zamanlı en-üst-%1 EB
portföyü, 1983–2020 arasında bildirilen %5,7 yıllık getiri kazanır; bu,
yayınlanmış anomalilerden oluşan bir portföye yakındır; öngörülebilirlik muhasebe
sinyallerinde, küçük hisse senetlerinde ve 2004-öncesinde yoğunlaşır. EB tahminleri
2004-öncesinde doğrudur ama görünür yapısal kırılmadan sonra fazla iyimserdir.
Birkaç sıkı finans çoklu-test prosedürü, sonraki birçok OOS performansçısını
kaçırır ([arXiv:2311.10685](https://arxiv.org/abs/2311.10685)).

**Desteklenen.** Tam kesitsel dağılım modellenir ve gerçek-zaman kullanılabilirliği
uygulanırsa, geniş ölçekli arama tutarlı biçimde analiz edilebilir. Aşırı
muhafazakâr kontrol büyük yanlış-negatif maliyetleri yaratabilir.

**Sınırlar.** Sonuçlar; tam bir kapasite/etki/borçlanma-maliyeti defteri yerine
brüt long-short getirileridir. Binlerce muhasebe oranı oldukça bağımlıdır, öncel
yapısal bir kırılmanın gerisinde kalabilir ve performans 2004'ten önce
yoğunlaşır. Sonuç, sınırsız V8 aramasını lisanslamaz.

**V8 çıkarımı.** Aile-düzeyi ampirik Bayes, V8 gerçekten binlerce karşılaştırılabilir
candidate'a sahip olduğunda olası bir gelecek araştırma raporudur. Başlangıçtaki
2–3 Expert tasarımı için erkendir. Kullanılırsa, posterior beklenen fayda kapasite/
maliyeti ve zamanla-değişen öncelleri içermeli ve donmuş holdout öncel uyumunun
dışında tutulmalıdır.

### 44. PredictionMarketBench

PredictionMarketBench; emir defterlerini, trade'leri, yaşam döngüsünü ve
mutabakatı; maker/taker ücretleri, görüntülenen-hacmin-arkasında-kuyruk semantiği,
araç-çağrısı bütçeleri ve replay edilebilir günlüklerle deterministik olay-güdümlü
episode'lara paketler. İlk sürümde yalnızca dört Ocak 2026 Kalshi episode'u
vardır. Basit bir Bollinger ajanı genel olarak kazanırken aktif bir LLM ajanı
kaybeder; ama kâr tek bir Bitcoin episode'unda yoğunlaşır
([arXiv:2602.00133](https://arxiv.org/abs/2602.00133)).

**Desteklenen.** Taşınabilir episode manifestleri, birleştirilmiş saatler,
deterministik replay, açık API/aksiyon bütçeleri, maker/taker ayrımı, mutabakat
semantiği ve tam yörüngeler güçlü benchmark tasarım örüntüleridir.

**Sınırlar.** Dört episode strateji-performans çıkarımını destekleyemez. Gecikme,
kesin mekan önceliği, karşı-olgusal piyasa tepkisi ve stratejik etkileşim
yoktur; benchmark'ın tekrar tekrar kullanımı aşırı-uyumu davet eder. Tarihsel
yalnızca-trade maker dolumları yine de kuyruk varsayımlarına bağlıdır.

**V8 çıkarımı.** Koşum yapısını yalnızca, sıralı L2/trade verisi mevcut olduğunda
Level-3 araştırması için aynala: episode manifesti, olay/alma/karar/gönderim
saatleri, emir durum makinesi, ücretler, mutabakat ve deterministik makbuzlar.
Level 1'de pasif/kısmi/kuyruk iddialarında kapalı-başarısız ol.

---

## II. Piyasa mikro yapısı, emir akışı, likidite ve etki

### 45. Kaba anlık görüntüler altında genelleştirilmiş OFI

Su ve arkadaşları; üç saniyelik Çin emir-defteri anlık görüntülerinin birden çok
tick hareketini atlayabileceğini ve klasik OFI'nin olay-olay en-iyi-kotasyon
inşasını ihlal edebileceğini not eder. Genelleştirilmiş OFI'leri, geçilen fiyat
seviyeleri boyunca miktarları toplar; bir log dönüşümü derinliği dengeler. On CSI
500 bileşeninde, 30 saniye, bir dakika ve beş dakikadaki eşzamanlı doğrusal
uyumlar, klasik OFI'dan çok daha yüksek OOS \(R^2\) bildirir
([arXiv:2112.02947](https://arxiv.org/abs/2112.02947)).

**Kanıt ve sınır.** Bu, bir OFI tanımının feed tanecikliliğiyle eşleşmesi
gerektiğine dair ölçüm kanıtıdır. Son derece yüksek uyum eşzamanlı fiyat değişimiyle
ilgilidir ve yalnızca on seçili hisse senedidir; kotasyon değişikliklerinde
kodlanmış aynı fiyat hareketini kısmen yeniden inşa edebilir. Log-GOFI'nin hareketten
önce bilindiğinin ya da spread/gecikme sonrası kârlı kaldığının kanıtı değildir.

**V8 çıkarımı.** Her emir-akışı feature'ı feed çözünürlüğünü ve atlanan
seviyelerin gözlemlenebilir olup olmadığını bildirir. Yalnızca borsa zaman damgasını
değil, `availability_time`'ı kullan. Aynı-pencereli bir OFI/getiri regresyonu, bir
Expert edge testine değil, simülatör kalibrasyonuna/atfına aittir.

### 46. Akış, etki, hacim ve volatilitenin birleşik Hawkes kuramı

Muhle-Karbe ve arkadaşları; kalıcı "çekirdek" emirleri Hawkes süreçleriyle
reaktif akıştan ayırır. Ölçekleme sınırında tek bir çekirdek-kalıcılık parametresi
\(H_0\), işaretli-akış kalıcılığını, pürüzlü işaretsiz hacmi, pürüzlü volatiliteyi
ve güç-yasası etkisini birbirine bağlar. Yaklaşık 0,75–0,8'lik tahminler,
kare-kök etkiyi ve pürüzlü günler-arası volatiliteyi ima eder
([arXiv:2601.23172](https://arxiv.org/abs/2601.23172)).

**Kanıt ve sınır.** Makale, stilize olgular arasında tutarlı bir yapısal köprü
sunar ve \(H_0\) için gerçek işaretli-akış verisi kullanır. Birçok adım
asimptotik/yaklaşıktır; "çekirdek" ile tepki akışı gizlidir ve volatilite eşlemesi
günler-arası ölçeklerle ilgilidir. Trade edilebilir gerçek-zamanlı bir çekirdek-
akış durumu tanımlamaz.

**V8 çıkarımı.** Simülasyon kalibrasyonu; işaret otokorelasyonunu, işaretsiz-hacim
pürüzlülüğünü, fiyat difüzyonunu ve etkiyi birlikte test etmelidir—tek bir eğriyi
eşleştirmek yetersizdir. Kalıcılığı sabit evrensel bir katsayı değil, bir stres
boyutu olarak kullan.

### 47. Kare-kök etki ve emir dengesizliği için yapay piyasa

Barucca ve arkadaşları; gerçek veriye uydurulmuş mekanistik bir metaorder/
propagatör ortamını simüle eder. Yapay piyasa çapraz-korelasyonları, kare-kök-
benzeri etkiyi ve emir-akışı-dengesizliği davranışını yeniden üretir ve genel
akış algoritmalarının trader kimlikleri olmadan bile yararlı metaorder vekilleri
yeniden inşa edebildiğini gösterir ([arXiv:2509.05065](https://arxiv.org/abs/2509.05065)).

**Kanıt ve sınır.** Çalışma değerli bir *model eleştirisi* egzersizidir: yaklaşık
analitik sonuçlar, daha eksiksiz mekanizmanın simülasyonunda hayatta kalır. Ama
stilize olguları uydurulmuş parametrelerle yeniden üretmek benzersizliği kurmaz;
metaorder varış/boyutu ve etki mekanizmaları dayatılmıştır, ajanlar tam bir
stratejik LOB sağlamaz ve sentetik başarı trading ekonomisini sertifikalandıramaz.

**V8 çıkarımı.** Bir yapay piyasa, metamorfik simülatör testleri için
kullanılabilir—örneğin çekirdek kalıcılığını artırmak etki/volatiliteyi tutarlı
biçimde değiştirmelidir. Kalibrasyon için kullanılan gerçek tape'in ötesinde,
izin verilen ekonomik iddiaları asla genişletemez.

### 48. Emir-defteri olaylarının fiyat etkisi

Cont, Kukanov ve Stoikov; en-iyi-alış/satış fiyat ve boyut değişimlerinden olay-
düzeyi OFI tanımlar; limit emirleri, iptalleri ve piyasa emirlerini toplar. 50 ABD
hisse senedinde, kısa-aralık orta-fiyat değişimleri OFI'de yaklaşık doğrusaldır;
eğim derinlikle ters ilişkilidir. OFI, fiyat değişimlerini trade hacminden daha
iyi açıklar ve katsayılar zaman ölçeği ve likiditeyle sistematik olarak değişir
([arXiv:1011.6402](https://arxiv.org/abs/1011.6402); [DOI](https://doi.org/10.1093/jjfinec/nbt003)).

**Kanıt ve sınır.** Bu, net en-iyi-kotasyon akışı ve derinliği yerel fiyat-oluşumu
değişkenleri olarak destekleyen güçlü ölçüm kanıtıdır. İlişki esas olarak
eşzamanlıdır; konsolide TAQ tam kuyruk kimliğini, gizli likiditeyi ya da nedensel
dışsal emir şoklarını açığa çıkarmaz. Kısa aralıklarda doğrusal uyum, doğrusal-
olmayan metaorder etkisiyle çelişmez.

**V8 çıkarımı.** L2 sadakatinde, derinliğe, spreade, tick rejimine ve aralığa
koşullu bir etki yüzeyi kalibre et. Bar sadakatinde OFI'yi geri doldurma ya da
iddia etme. Bir OFI Expert için, feature'ı tahmin aralığından önce dondur ve
yalnızca-derinlikli bir modelle benchmark yap.

### 49. Propagatörler: geçici versus geçmişe-bağımlı etki

Taranto ve arkadaşları; geçmiş trade işaretlerinin sönümlenen çekirdeklerden
geçtiği geçici-etki modelini, beklenen emir işaretine göre sürprizin kalıcı etkiye
sahip olduğu geçmişe-bağımlı modelle karşılaştırır. Olayları fiyat-değiştiren ve
fiyat-değiştirmeyen trade'lere bölmek, özellikle büyük-tick hisse senetlerinde
tepkiyi ve imza-plot uyumlarını büyük ölçüde iyileştirir; HDIM kuramsal olarak
daha temizdir ama ampirik olarak yalnızca marjinal olarak daha iyidir
([arXiv:1602.02735](https://arxiv.org/abs/1602.02735)).

**Kanıt ve sınır.** Uzun-bellek akışı ve neredeyse-difüzif fiyatlar likidite/etki
uyarlaması gerektirir. Olay taksonomisi, modaya uygun bir model etiketinden daha
önemlidir. Modeller doğrusal kalır, çoğunlukla piyasa emirlerini kullanır ve
doğrusal-olmayan metaorder etkisini ile atlanan limit/iptal olaylarını kabul eder.

**V8 çıkarımı.** Simülatör doğrulaması, fiyat-değiştiren ve fiyat-değiştirmeyen
olayları ayırt etmeli ve saat/geri-bildirim hataları için negatif-gecikme
teşhislerini test etmelidir. Yüksek-frekanslı çalışma için sabit bir trade-başına
kayma parametresi yapısal olarak yetersizdir.

### 50. Gerig'in gizli-emir kuramı

Gerig'in tezi; piyasayı, otokorelasyonlu emir akışını geçmişe-bağımlı, asimetrik
likidite aracılığıyla yaklaşık ilişkisiz getirilere çeviren bir sistem olarak
modeller. LSE broker kodlarını gürültülü trader vekilleri olarak kullanarak alt
emirleri gizli emirlere gruplar, ağır-kuyruklu bir boyut dağılımı bulur ve basit
bir otoregresif işaret modelinden çok bir gizli-emir bilgi modeline yakın etki/
getiri örüntüleri bildirir ([arXiv:0804.3818](https://arxiv.org/abs/0804.3818)).

**Kanıt ve sınır.** Emir bölmeyi, asimetrik likiditeyi, içbükey/logaritmik toplam
etkiyi, getiri kuyruklarını ve kümelenmiş volatiliteyi bağlayan erken bir mekanizma
sağlar. Broker kodu trader kimliği değildir; 100-trade gruplama kuralı buluşsaldır;
çalışma küçük bir LSE ortamında 2007 tarihli bir fizik tezidir ve birçok işlevsel-
form tartışması daha sonra gelişmiştir.

**V8 çıkarımı.** Candidate "baskısı", kalıcı ebeveyn niyetini yalnızca gizli bir
hipotez olarak genel reaktif akıştan ayırmalıdır. Katılımcı kimlikleri olmadan
vekili olarak adlandır, gruplama belirsizliğini ölç ve yeniden inşa edilen
metaorder'ları asla gerçek-etiket doğruları olarak ele alma.

### 51. Koşullu etki tezi

51. maddenin arkasındaki tez, 2015 LOBSTER verisinden dört NASDAQ hisse senedi
için piyasa emirlerini yeniden inşa eder, gecikme-1 tepkisini ölçer ve OFI'ye
koşullu toplu etki için doğrusal ile karar-ağacı regresyonlarını karşılaştırır.
Pozitif anlık tepki, spread ile ilişki, doğrusal-altı toplu OFI tepkisi ve TSLA
çalışmasında karar ağacı için daha düşük test MSE'si bulur
([arXiv:2004.08290](https://arxiv.org/abs/2004.08290)).

**Kanıt ve sınır.** Erişilebilir bir tezdir, geniş piyasa kanıtı değil. Piyasa
emirlerinin mevcut likiditeyi aşmadığını varsayar, analizin bir kısmında limit-
emir/iptal etkisini ihmal eder, ebeveyn-emir kimliğinden yoksundur, dört seçili
hisse senedi ve bir dönem kullanır ve gerçekçi bir execution defteriyle
karşılaştırmaz.

**V8 çıkarımı.** Ağaç doğrusal-olmayanlığı, yalnızca doğrusal bir derinlik/OFI
modeli ve zaman-bloğu OOS'tan sonra bir kalibrasyon baseline'ı olabilir. V8,
daha düşük tek-adım MSE'yi artımlı net fayda olarak yorumlamamalıdır.

### 52. Emir akışı ve etki için çevrimiçi Bayes değişim noktaları

Tsaknaki, Lillo ve Mazzarisi; Bayes çevrimiçi değişim-noktası tespitini Markov ve
skor-güdümlü rejim-içi bağımlılığa genişletir. Birer aylık MSFT ve TSLA emir akışı
bir ve üç dakika yakınında toplanarak, zamanla-değişen-korelasyon modelleri ARMA
ve IID-BOCPD üzerinde tek-adım OOS MSE'sini iyileştirir. Tespit edilen rejimler,
zaman/hacimle içbükey fiyat evrimi gösterir ve çevrimiçi etki tahminlerini
iyileştirir ([arXiv:2307.02375](https://arxiv.org/abs/2307.02375)).

**Kanıt ve sınır.** Çalışma, sabit bir rejim etiketi yerine çevrimiçi rejim
belirsizliğini destekler. Ama iki hisse senedi/iki ay, keyfi toplama, sabit hazard
seçimleri ve aynı emir akışından çıkarılan rejimler genellemeyi sınırlar. Tespit
edilen bir rejimin gerçek bir metaorder olduğu kanıtlanmamıştır.

**V8 çıkarımı.** Bir rejim feature'ı test edilirse, MarketState tam posterior/
çalışma-uzunluğu belirsizliğini, model sürümünü ve kullanılabilirlik saatini
saklar. Yuvarlanan AR/skor-güdümlü baselinelarla karşılaştır; terfi, yalnızca OFI
MSE'si değil, eşleştirilmiş maliyet-sonrası iyileştirme gerektirir.

### 53. Makro haberler etrafında gün-içi getiri–akış dinamikleri

Takahashi, 1.490 gün (2008–2013) için bir saniyelik S&P 500 E-mini BBO verisinde
heteroskedastisite ile tanımlanmış yapısal bir VAR tahmin eder; 15 dakikalık
aralıkla ayrı ayrı. Hem OFI'nin fiyat etkisi hem de getirilere ters akış tepkisi
bir saniye ölçeğinde anlamlıdır; şoklar büyük ölçüde bir saniye içinde dağılır.
Planlı duyurular fiyat etkisini ve getiri volatilitesini artırırken akış etkisini
ve akış volatilitesini azaltır; bu likidite çekilmesiyle tutarlıdır
([arXiv:2508.06788](https://arxiv.org/abs/2508.06788)).

**Kanıt ve sınır.** Fiyat/akış eşzamanlılığını doğrudan ele alır ve olay takvimi
ile gün-içi duruma koşullamak için güçlü bir neden sağlar. Tanımlama
heteroskedastisite/sıra varsayımlarına bağlıdır; veri 2013'te biten tek bir
vadeli işlem piyasasıdır; zaman damgaları yalnızca bir saniyedir; bildirilen
ilişkiler net bir strateji değildir.

**V8 çıkarımı.** Planlı-haber durumu zaman-noktası ve takvim-sürümlü olmalıdır.
Maliyet/etki stresi yayınların yakınında sıçramalıdır. Eşzamanlı fiyat ve akış
kullanan bir feature, alma/karar gecikmesinin ötesinde geciktirilmelidir.

### 54. Hisse senetlerinde OFI'nin çapraz etkisi

Cont, Cucuringu ve Zhang; LOBSTER kullanarak 2017–2019 arası en-üst-100 S&P 500
adını inceler. Entegre çok-seviyeli kendi-varlık OFI'si eşzamanlı getirileri o
kadar iyi açıklar ki çapraz-varlık OFI'si çok az ekler; gelecekteki bir dakikalık
getiriler için seyrek çapraz-varlık OFI'si OOS \(R^2\)'sini ve kendi-varlık
modellerine göre brüt bir tahmin portföyünü iyileştirir, ama avantaj ufukla hızla
kaybolur. Ağ yapısı düşük-sıralı/sektöreldir ([arXiv:2112.13213](https://arxiv.org/abs/2112.13213); [DOI](https://doi.org/10.1080/14697688.2023.2236159)).

**Kanıt ve sınır.** Ekonomik karşılaştırma işlem maliyetlerini açıkça görmezden
gelir; yıllıklandırılmış PnL tablosu dağıtılabilirlik kanıtı değildir. Eşzamanlı
dakika toplaması öncül/gecikme ve Epps etkileri yaratabilir; evrenler ve LASSO
seçimleri serbestlik derecelerini tüketir; ortak faktörler nedensel çapraz etki
gibi görünebilir.

**V8 çıkarımı.** Çapraz-varlık durumu koşullu bir deneydir. Eşzamanlı
kullanılabilirlik, seyrek/global-faktör baselineları, ciro/spread/etki/borçlanma
maliyetleri, sektör-kümesi belirsizliği ve net kazancın eyleme-geçirilebilir
gecikmede hayatta kaldığının kanıtı gerektir. Başlangıç Expert ontolojisinden çok
gelecekteki portföy çekişmesiyle ilgilidir.

### 55. CSI 300 vadeli işlemlerinde stokastik OFI tepkisi

Bu makale OFI'yi, muhtemelen ağır-kuyruklu sıçramalarla sürülen Ornstein–
Uhlenbeck-benzeri ortalama-dönen bir tepkiye sahip bir şok olarak modeller ve onu
fiyat dinamiklerine bağlar. Bir yıllık 500 ms CSI 300 vadeli işlem anlık görüntüsü
tarihsel pencereler ve gelecek ufukları üzerinde taranır; yazarlar istikrarlı OFI
işaret etkileri, zamanla-değişen güç ve farklı "verimlilik" rejimleri bildirir
([arXiv:2505.17388](https://arxiv.org/abs/2505.17388)).

**Kanıt ve sınır.** Zamansal-tepki sorusu yararlıdır: feature pencereleri ve
tahmin ufukları birbirinin yerine geçemez. Ama kapsamlı ufuk/pencere keşfi, LASSO
CV ve bildirilen "kâr noktaları" tam çokluk ve maliyet muhasebesi gerektirir.
Makale piyasa derinliğini ve ayrıntılı volatilite işlemesini atlar; ağır-kuyruk/OU
modeli benzersiz tanımlanmamıştır.

**V8 çıkarımı.** OOS'tan önce ufuk yüzeyini kaydet ve tüm yüzeyi tek bir aile
olarak kontrol et. En iyi hücre yerine zaman-bloğu replikasyonu altında işaret ve
etki istikrarını tercih et. Net çalıştırılabilir kanıt olmadan hiçbir "verimsiz
rejim" etiketi terfi ettirilemez.

### 56. Evrensel ölçekleme ve doğrusal-olmayan toplu etki

Patzelt ve Bouchaud; trade'leri NASDAQ, İskandinav hisse senetleri ve EUREX
vadeli işlemleri arasında toplar. Ölçek ayarından sonra hacim-etki eğrileri
sigmoidaldir ve kabaca on trade'den gün-içi ufuklara kadar istikrarlıdır. Aşırı
aynı-işaretli dengesizlik, bol/yeniden-doldurulan karşı likidite fiyatı
sabitlediği için *daha küçük* fiyat hareketiyle ilişkilidir; bir trade'in orta-
fiyatı değiştirme olasılığı aşırı işaret yanlılığında sıfıra yaklaşır
([arXiv:1706.04163](https://arxiv.org/abs/1706.04163); [yazar PDF](https://www.cfm.com/wp-content/uploads/2022/12/301-2017-Universal-scaling-and-nonlinearity-of-aggregate-price-impact-in-financial-markets.pdf)).

**Kanıt ve sınır.** Bu, "daha tek taraflı genel akış ⇒ orantılı olarak daha büyük
gelecek getirisi" saf kuralıyla güçlü biçimde çelişir. Sonuçlar, ebeveyn
kimlikleri olmayan gözlemsel toplamlardır; mekan parçalanması, gizli likidite ve
koşullandırma eğrileri etkiler. Toplu işaret etkisi, izole nedensel metaorder
etkisinden farklıdır.

**V8 çıkarımı.** Dengesizlik ile karşı derinlik/yeniden-doldurma arasında bir
etkileşim ekle; bir doygunluk/sabitleme rejimini strese sok. Monoton bir OFI
Expert, etkisi likiditeye koşullu olarak kayboluyor ya da tersine dönüyorsa
reddedilmelidir.

### 57. Ortak fiyat/emir-akışı dinamikleri için MTD modelleri

Taranto ve arkadaşları; al/sat × fiyat-değiştiren/fiyat-değiştirmeyen olaylarını
genelleştirilmiş bir Karışım Geçiş Dağılımıyla modeller. Parametre sayısı gecikme
sırasıyla üstel değil doğrusal büyür. Altı ABD hisse senedinde, zayıf kısıtlı MTDg
modelleri, on günlük yuvarlanan tahminden sonra bir-gün-ileri olay log-kaybını
koşulsuz olasılıklara ve tutumlu varyantlara göre iyileştirir
([arXiv:1604.07556](https://arxiv.org/abs/1604.07556)).

**Kanıt ve sınır.** Ayrık bir olay modeli, tick verisine Gauss VAR'dan daha
uygundur ve uzun belleği tutumlu biçimde temsil edebilir. Artık farklılıklar
kalır; fiyat-değiştiren olaylar nadirdir; eksik defter derinliği muhtemelen
önemlidir; çekirdekler emir bölmeyi tepkiler/sürü davranışıyla karıştırır ve
nedensel dürtü tepkileri değildir.

**V8 çıkarımı.** MTDg'yi yalnızca sonraki-olay/dolum görevleri için bir L2/L3
olasılıksal baseline olarak kullan. Ekonomiden önce gün bazında kalibrasyonu ve
log-kaybını değerlendir. Bar-düzeyi V8'e aktarma ya da çekirdeğini "piyasa
tepkisi" olarak etiketleme.

### 58. Emir akışı ve fiyat oluşumu incelemesi

Lillo; LOB mekanizmalarını, ekonometrik/nokta-süreci/ajan modellerini, uzun-bellek
emir akışını, çapraz etkiyi, kare-kök metaorder etkisini ve ortak etkiyi inceler.
Merkezi bir ayrım şudur: piyasa etkisi bilgiyi, trader'ların tahminini düzeltmeyi
ya da mekanik arz/talebi yansıtabilir; gözlemsel korelasyon tek başına aralarında
seçim yapamaz. Eşzamanlı metaorder'lar ve ilişkili işaretler execution
maliyetlerini kaydırabilir/kalabalıklaştırabilir ([arXiv:2105.00521](https://arxiv.org/abs/2105.00521)).

**Kanıt ve sınır.** Yüksek kaliteli bir sentezdir, bağımsız bir ampirik
replikasyon değildir. Gizli dinamik likiditeyi ve nedensel tanımlamanın
zorluğunu vurgular.

**V8 çıkarımı.** Candidate kayıtları `predictive_association`, `mechanical_impact`
ve `causal_mechanism_tested`'ı ayırt etmelidir. Portföy execution stresi, bağımsız
tek-emir maliyetlerini toplamak yerine ortak etkiyi ve ilişkili kalabalıklığı
içermelidir.

### 59. Madde 33'ün kopyası, execution çapraz-kovası

59. madde tam olarak arXiv:2209.05559'un tekrarıdır. Execution ilgisi negatiftir:
limit-emir ayarı ve trade kapanışı açıkça gelecek çalışmadır; bu yüzden öğrenilmiş
V8 execution için kanıt sağlamaz. Bibliyografik olarak bir kez say ve ikinci bir
kaynak değil, `VALIDATION` artı `EXECUTION_CAUTION` olarak etiketle.

### 60. Madde 34'ün kopyası, portföy çapraz-kovası

60. madde yine arXiv:2507.07107'ye bağlanır. Portföy davranışıyla ilgilidir çünkü
bildirilen sistem eşit-ağırlıklı en-üst-100'ü, örneklem-kovaryans MVO'yu ve
Ledoit–Wolf MVO'yu karşılaştırır ve ağırlıkları %3'te sınırlar. Ama başlık
faydası tahmini, maskeyi, kaybı, artırımı ve tahsis değişikliklerini karıştırır;
gerçek veri özeldir ve etki basitleştirilmiştir. Bir kez say ve `VALIDATION`,
`TRADABILITY` ve `PORTFOLIO_CONSTRUCTION` olarak etiketle.

---

## III. Uzlaştırılmış çelişkiler

| Görünür çelişki | Uzlaştırma | V8 kuralı |
|---|---|---|
| Kısa-ufuk fiyat değişimi OFI'de doğrusaldır (48), ama toplu/metaorder etkisi kare-kök, sigmoidal ya da doygunlukludur (46, 47, 49, 56, 58). | Koşullandırma nesneleri farklıdır: kısa kutularda net en-iyi-kotasyon olay akışı, işaretli trade toplamları ve tanımlanmış/gizli ebeveyn emirleri birbirinin yerine geçemez. Likidite ölçek ve geçmişle uyarlanır. | Her etki iddiası olay türünü, koşullandırma değişkenini, toplama saatini, boyut normalizasyonunu ve ufku bildirir. |
| Kalıcı emir akışı getirileri öngörülebilir yapmalı, ama fiyatlar difüzife yakındır (46, 49, 50, 57). | Geçici/geçmişe-bağımlı etki ve asimetrik likidite öngörülebilir akışı dengeler; tepki akışı gözlenen yasayı değiştirir. | Simülatör testleri işaret belleğini ve getiri imza plotlarını birlikte eşleştirmelidir. |
| Daha tek taraflı akış fiyatı daha çok hareket ettirmeli, ama aşırı işaret dengesizliği fiyatı sabitleyebilir (56). | Aşırı kalıcılık çoğu zaman görünür/gizli karşı likidite ve yeniden-doldurma ile birlikte oluşur. | Derinlik/yeniden-doldurma etkileşimi ekle; koşulsuz monotonluğu reddet. |
| Çapraz-varlık OFI eşzamanlı olarak az ekler ama kısa-ufuk tahminlere yardımcı olur (54). | Kendi çok-seviyeli OFI eşzamanlı ortak akışı emer; gecikmiş dikkat/eşzamanlı-olmayış kısa öncül/gecikme yapısı bırakabilir. | Eşzamanlı atfı, sıkı geciktirilmiş tahminden ve gecikme testlerinden ayır. |
| PBO/DSR geniş aramayı cezalandırırken, yüksek-verimli EB geniş aramanın işe yarayabileceğini bulur (40–43). | Arama genişliği hata değildir; koşulsuz seçim ve yanlı tahminlerdir. Muhafazakâr prosedürler de yanlış pozitifleri yanlış negatiflerle takas eder. | Yanlış kabul ile yanlış reddin kaybını kaydet; tüm denemeleri açıkla; dokunulmamış bir son değerlendirme tut. |
| Walk-forward/CSCV yardımcı olur, ama simetrik ya da tekrarlanan bölmeler başarısız olabilir (33, 36, 40). | Bağımlılık, durum devri, etiket örtüşmesi, rejim sınırları ve yeniden kullanım geçerliliği belirler. | Bağımlılık birimini, temizleme mantığını, durum sıfırlamasını ve danışma sayısını bildir. |
| Üretici bir model aşırı-uyumu azaltabilir (31), ama sentetik veri model hatasını büyütebilir. | Sentetik yollar koşullu varyasyon ekler, yeni gerçek değil; yararlılık göreve- ve kalibrasyona-bağlıdır. | Sentetik kanıt strese sokabilir ya da yanlışlayabilir ama edge'i asla sertifikalandıramaz. |
| Bir işlem-yapılabilirlik maskesi görünür IC'yi düşürür ama gerçekleştirilebilir performansı iyileştirir (34). | Görünür istatistiksel sinyal ulaşılamaz durumlarda yatabilir. | Ekonomik gözlemlenebilirlik tahmin uyumuna hükmeder. |
| Bir ranker Sharpe'ı en üstleyebilirken başka bir candidate drawdown'ı en aza indirir (36) ve kovaryans optimizasyonu eşit ağırlığı yenebilir (34). | Sıralama görev-yetkisine ve tahmin edilen kovaryans/maliyete koşulludur; küçük örneklem istikrarsızlığı sırayı tersine çevirebilir. | Portföy faydasını önceden bildir ve deterministik 1/N/risk-bütçesi baselinelarıyla karşılaştır. |

---

## IV. Makalelerden türetilen V8 simülasyon doğruluğu gereksinimleri

### A. Sadakatten-iddiaya matrisi

| İddia | Minimum savunulabilir girdi | Gerekli simülatör semantiği | Yasak kısayol |
|---|---|---|---|
| Agresif giriş sonrası günlük/bar yön Expert'i | Kurumsal aksiyonlar ve kullanılabilirlik saatleriyle PIT OHLCV | Sonraki uygun bar dolumu, her iki bacakta ücretler/kayma, aynı-bar belirsizlik politikası, boşluklar/zaman aşımları | Karar barının kapanışında dolum; intrabar kuyruk varsayımları |
| İşlem-yapılabilirlik/limit-hareket Expert'i | Karar zamanında bilinen borsa limit/durdurma/askıya alma alanları | Maskenin yuvarlanan feature'lara ve hedefe yayılması; ulaşılamaz emir reddi | Feature'lar hesaplandıktan sonra sonradan silme |
| Tick OFI tahmini | Alma süreleriyle sıralı trade'ler/kotasyonlar ya da L2 | Tahmin aralığından önce feature donması; olay sıralaması; spread/derinlik-farkında agresif dolumlar | Aynı-pencere OFI'yi tahmin olarak kullanma; bar yeniden inşası |
| Pasif maker ya da dolum-olasılığı iddiası | Sıralı L2, trade baskıları, mekan kuralları, kalibre edilmiş kuyruk pozisyonu | Katıl/iptal/kısmi-dolum/öncelik durum makinesi, gecikme, maker/taker ücretleri | Kuyruk olmadan trade-through dolum; günlüklenmemiş gizli-likidite varsayımı |
| Metaorder/kare-kök etki | Katılımcı/ebeveyn etiketleri ya da açıkça belirsiz yeniden inşa | Alt/ebeveyn soyağacı, karşı-olgusal sınırlama, boyut/ADV/volatilite normalizasyonu | Genel işaret dizilerini gerçek ebeveyn emirleri olarak ele alma |
| Çapraz etki/kalabalıklık | Eşzamanlı çok-varlıklı L2/trade'ler ve kullanılabilirlik | Ortak saatler, portföy ortak etkisi, ilişkili maliyet stresi | Varlık-başına bağımsız kayma toplama |

### B. Gerekli doğrulama testleri

1. **Nedensellik/saat testleri:** gelecek olayları boz ve güncel MarketState/candidate/emir hash'lerinin değişmediğini kanıtla; borsa, alma, karar, gönderim, uygunluk, dolum ve mutabakat zamanlarını ayırt et.
2. **Maske monotonluğu:** aşağı-akış geçerliliği daha katı olabilir ama maskelenmiş bir hücreyi asla sessizce yeniden etkinleştiremez; ulaşılamaz gözlemler içeren yuvarlanan pencereler önceden kayıtlı bir politikayı izler.
3. **Olay taksonomisi:** L2+'da, ekonomik kullanımdan önce fiyat-değiştiren/fiyat-değiştirmeyen tepkiyi, işaret belleğini, derinlik-koşullu OFI eğimini ve imza plotlarını yeniden üret.
4. **Etki stresi:** doğrusal, içbükey, kare-kök, sigmoidal/doygunluk, haber-genişletilmiş ve ortak-etki senaryoları; terfi, sonucun desteklenmeyen bir modele bağlı olmamasını gerektirir.
5. **Kuyruk testleri:** çalıştırılabilir karşı akış olmadan dolum yok; derinliğin arkasına katılmak önceliği iyileştiremez; kısmi dolumlar boyut/nakdi korur; iptal gecikmesine saygı gösterilir.
6. **Araştırma-ailesi makbuzları:** aynı veri/kod/config/tohum/defter hash'leri sonuçları yeniden üretir; gizli/silinmiş deneme tespiti bir geçerlilik başarısızlığıdır.
7. **Diferansiyel testler:** skaler referans versus hızlandırılmış simülatör, tam-tape versus pencere replay ve iki bağımsız muhasebe uygulaması.

---

## V. Hipotez Laboratuvarı, scorer, ranker ve execution çıkarımları

### Hipotez Laboratuvarı

Her laboratuvar kaydı şu alanları eklemelidir:

- `research_family_id`, `parent_variant_id`, `trial_index`, `mutation_reason`, `searched_after_failure`;
- `filtration` ve tüm kullanılabilirlik saatleri;
- `feature_window`, `forecast_horizon`, `holding_horizon`, `purge`, `embargo`, `state_reset`;
- `dependence_unit`, `cluster_unit` ve bootstrap/permütasyon şeması;
- `tradability_mask_version` ve hariç tutma nedenleri;
- `simulator_fidelity`, `unsupported_semantics`, `impact_model_family`;
- `gross_utility`, spread, ücret, kayma, etki, borçlanma/fonlama, kapasite ve net fayda;
- tam-aile kapsamı varsayımlarıyla `PBO`, `DSR` ya da EB teşhisleri;
- `consultations_of_frozen_holdout` ve ilk yetkili hükümden sonra otomatik bir geçersizleştirme kuralı.

Terfi yine de sabit bir dedektörün trade-yok, yön-karıştırılmış, maliyet-stresli ve
eşit-bilgili global baselinelara karşı test edilmesini gerektirir. OFI/durum tahmin
metrikleri ikincildir; birincil karşılaştırma, bildirilen bir risk/kapasite
bütçesinde eşleştirilmiş net faydadır.

### Scorer

Bir scorer yalnızca ham Sharpe ya da "genelleme oranı" üzerinde optimize
edilmemelidir. Eşleşen candidate kapsamında şunları karşılaştır:

1. deterministik kanıt skoru;
2. yalnızca-maliyet filtresi;
3. kalibre edilmiş lojistik model;
4. sığ ağaç;
5. önerilen herhangi bir GT-benzeri ya da kovaryans-cezalı hedef.

Kalibrasyonu zaman/rejim/işlem-yapılabilirlik koşullu, skor ondalık dilimine göre
beklenen faydayı, seçici-risk/kapsam eğrilerini, ciroyu ve etkiyi raporla. Gün/
oturum-bloğu eşleştirilmiş belirsizlik ve dokunulmamış bir son dilim zorunludur.
Eşleşen-kapsam faydasını iyileştirmeden daha az trade seçen bir skor başarısız
olur.

### Ranker ve portföy katmanı

Sıralama, defter tekrarlayan **bağlayıcı bir kaynak sınırını aşan eşzamanlı
kabul edilebilir candidate'lar** göstermedikçe kabul edilemez. Bu ön koşul
sağlandığında:

- yetkiyi önceden bildir: büyüme, drawdown kontrolü, beklenen açık,
  likidite/kapasite ya da ağırlıklı bir fayda;
- tümünü-kabul-et-risk-sınırıyla, deterministik 1/N ile, deterministik risk
  bütçesiyle ve öğrenilmiş/önerilen ranker ile karşılaştır;
- getirilerde, tutma aralıklarında, sektör/faktör maruziyetinde, likiditede ve
  ortak etkide örtüşmeyi modelle;
- kovaryans büzülmesi kullan ve tahmin penceresi ile eşit-ağırlık baseline'ına
  duyarlılığı göster;
- bağımsız candidate Sharpe'ını değil, marjinal portföy katkısını değerlendir;
- sıra istikrarını ve ikili sıranın belirsizliğini raporla; eşitlikler/belirsizlik,
  sahte bir kesinlik yerine deterministik risk kontrollerine çözülmelidir.

### Execution

Mikro yapı literatürü, şimdilik öğrenilmiş execution değil, bir execution
*araştırma gündemi* destekler. Kurallı deterministik execution'ı karşılaştırıcı
olarak tut. Sadakat yalnızca, belirli bir sonuç desteklenen stres altında
değiştiğinde yükseltilir. Öğrenilmiş bir executor şunlara kadar engellenir:

1. en az bir Expert, kurallı execution altında replike maliyet-sonrası değer
   gösterir;
2. simülatör, seviyeye-özgü doğruluk testlerini geçer;
3. eşleştirilmiş bilgide sabit TWAP/agresif/pasif buluşsal yöntemler güçlü
   baseline'lardır;
4. aksiyon/durum/emir muhasebesi deterministik ve denetlenmiş;
5. politika değerlendirmesi tohumları, rejimleri, etki yüzeylerini, gecikmeyi ve
   kapasiteyi kapsar;
6. alpha ve executor etkileşimi, bir faktöriyel deneyle ölçülür.

---

## VI. Önerilen önceden kayıtlı deneyler

### EXP-VAL-01 — Tam-aile aşırı-uyum denetimi

**Soru:** Denenen tüm Expert geometrileri arasında ne kadar seçim bozulması var?

**Tasarım:** Nihai OOS'tan önce, candidate-gün fayda matrisini dondur. Mekanizmaya
göre tutarlı aileler tanımla. Açıklanan etkin-deneme tahminiyle CSCV/PBO, DSR ve
blok-bootstrap kazanan-bozulması hesapla. Mekanizmabaşına-tek-varyant politikasıyla
karşılaştır.

**Geçer:** Aday gösterilen varyant, dokunulmamış dilimde pozitif eşleştirilmiş
net fayda korur ve teşhisler önceden kayıtlı endişe eşiklerinin altındadır.
**Başarısız:** Eksik bir deneme, son-dilim yeniden kullanımı ya da başarısız
varyantları hariç tutmaya bağlı bir sonuç, aileyi geçersiz kılar.

### EXP-VAL-02 — Karmaşıklık/örneklem-boyutu sınırı

**Soru:** Eklenen Expert/feature/varlıklar, etkin örneklem boyutunu tükettikten
sonra OOS değerini iyileştiriyor mu?

**Tasarım:** 1, 2, 3 Expert'li ve sabit feature gruplu iç-içe modeller; eşit bilgi
ve arama bütçesi; blok-OOS replikasyon oranını nominal/etkin boyuta karşı çiz.
Kovaryans-cezalı doğrusal baseline'ları dahil et.

**Geçer:** Eklenen karmaşıklık, yalnızca IS Sharpe değil, replike eşleştirilmiş
iyileştirme üretir. **Başarısız:** replikasyon düşer ya da güven aralıkları fayda
kazancı olmadan genişler.

### EXP-VAL-03 — İşlenebilirlik-maskesi ablasyonu

**Soru:** Herhangi bir görünür sinyal, çalıştırılamaz gözlemlere mi bağlı?

**Tasarım:** Maske-yok, sonradan satır maskesi ve maske-önce yayılımı karşılaştır.
Limit/durdurma/askıya alma olaylarından sonra tam geri-bakış için faktör
değerlerini denetle. Birincil metrikler: gerçekleştirilebilir IC, reddetme
nedenleri, net fayda ve ulaşılamaz-emir oranı.

**Geçer:** Maske-önce nedensel olarak temizdir ve sonuçlar hayatta kalır.
**Başarısız:** kabul edilen herhangi bir emir, ulaşılamaz bir gözleme atıfta
bulunur; geçersiz maskelerle görünür metrik iyileşmesi kontaminasyon olarak
günlüklenir.

### EXP-OFI-01 — Sıkı geciktirilmiş OFI versus eşzamanlı atıf

**Soru:** OFI gelecek getirileri tahmin mi ediyor, yoksa yalnızca aynı fiyat
hareketini mi açıklıyor?

**Tasarım:** Sıralı L2 ile klasik, log/genelleştirilmiş ve çok-seviyeli OFI'yi
\([t-w,t]\) üzerinde hesapla; kararlar alma gecikmesinden sonra oluşur; \((t+\ell,
t+\ell+h]\) tahmin et. Ufuklar boyunca yalnızca-derinlik, kendi-OFI, çapraz-OFI ve
karıştırılmış-zaman baseline'larını karşılaştır. Maliyetler sonraki çalıştırılabilir
kotasyonu ve etki stresini kullanır.

**Geçer:** Uygulanabilir gecikmede tekrarlanan pozitif eşleştirilmiş net fayda ve
aile düzeltmesinden sonra zaman/varlıklar arasında istikrarlı işaret.
**Başarısız:** değer yalnızca \(\ell=0\)'da, yalnızca maliyetlerden önce ya da
yalnızca aranan hücrelerde var.

### EXP-OFI-02 — Likidite sabitleme ve monotonluk yanlışlaması

**Soru:** Tek taraflı akışın koşullu monoton bir etkisi var mı?

**Tasarım:** OFI/işaret dengesizliği × karşı derinlik/yeniden-doldurma ×
spread/tick rejimi ile tabakala. Geliştirme bloklarında monoton doğrusal ve esnek
etkileşim modellerini uydur. Bir doygunluk/sabitleme alternatifini dondur.

**Geçer:** Koşullu bir form replike olur ve maliyet-farkında tahmini iyileştirir.
**Başarısız:** aşırı dengesizlik sabitlendiğinde ya da işaret tersine döndüğünde
koşulsuz monoton bir Expert reddedilir.

### EXP-OFI-03 — Haber ve gün-içi durum

**Soru:** OFI katsayıları, planlı yayınlar çevresinde ve gün boyunca istikrarlı mı?

**Tasarım:** Zaman-noktası olay takvimi; ayrı ön-, yayın- ve son-pencereler;
derinlik, spread, fiyat/akış etkisi, gecikme ve tahmin faydasını tahmin et.
Duyuru tarihine göre kümele. Ampirik duyuru nicelikleriyle spread/etki stresi uygula.

**Geçer:** Duruma-koşullu bir kural replike olur; aksi halde haber pencereleri
`NO_TRADE` olur ya da daha büyük maliyet rezervleri kullanır. **Başarısız:**
dedektör yayından önce duyuru değerlerini kullanır ya da havuzlanmış sonuçlar
negatif bir rejimi gizler.

### EXP-OFI-04 — Rejim posterioru versus statik model

**Soru:** Çevrimiçi değişim-noktası durumu, yuvarlanan otoregresyonun ötesinde
kararları iyileştiriyor mu?

**Tasarım:** BOCPD-IID, Markov BOCPD, skor-güdümlü BOCPD, yuvarlanan AR ve
rejim-yok baseline'ları. Yalnızca karar saatinde kullanılabilir posterior/çalışma-
uzunluğu değerleri. Önce OFI log-kaybını, sonra eşleştirilmiş aşağı-akış faydasını
değerlendir.

**Geçer:** Kalibrasyon ve maliyet-sonrası fayda, dokunulmamış varlıklarda/aylarda
iyileşir. **Başarısız:** aşağı-akış kazancı olmadan daha iyi OFI MSE'si ya da
istikrarsız tehlike duyarlılığı, feature'ı engeller.

### EXP-SIM-01 — Etki-modeli duyarlılık merdiveni

**Soru:** Bir V8 sonucu doğrusal kaymaya bağlı mı?

**Tasarım:** Aynı değiştirilemez emirleri sabit bps, spread/derinlik-doğrusal,
karekök katılım, sigmoidal doygunluk, haber stresi ve ilişkili ortak etki altında
yeniden oynat. Modeller yalnızca desteklenen veriyle kalibre edilir; desteklenmeyen
dallar tahmin değil, olumsuz senaryolardır.

**Geçer:** Candidate/ranker hükmü, önceden kayıtlı makul sınırlar içinde
değişmez. **Başarısız:** işaret/rank değişimi, parametre ortalaması değil, bir
sadakat engeli anlamına gelir.

### EXP-SIM-02 — Sentetik-piyasa metamorfik testleri

**Soru:** Simülatör, bilinen yapısal değişikliklere tutarlı biçimde yanıt veriyor mu?

**Tasarım:** Kontrollü Hawkes/propagatör/MTD ortamları üret. Çekirdek-akış
kalıcılığını artır, derinliği azalt, spread'i genişlet, tepkisel akış ekle ve
fiyat-sabitleyen likidite tanıt. İşaret belleğini, volatilite pürüzlülüğünü, fiyat
difüzyonunu, etki şeklini ve muhasebeyi test et.

**Geçer:** Yönsel değişmezler korunur ve kod, bilinen mekanizmayı tolerans içinde
yeniden üretir. **Sınır:** geçmek yalnızca uygulama davranışını doğrular, asla
piyasa edge'ini değil.

### EXP-RANK-01 — Çekişme ve marjinal portföy faydası

**Soru:** Bir ranker gerekli mi ve gerekliyse deterministik tahsisi yeniyor mu?

**Tasarım:** Önce rankersız çekişme sıklığını tahmin et. Bağlayıcıysa, kabul
edilen candidate'ları 1/N, risk paritesi/bütçesi, sınırlı açgözlü net fayda,
büzülmüş MVO ve önerilen ranker ile yeniden oynat. Maliyetler ilişkili ortak etkiyi
içerir; eşleştirilmiş gün-düzeyi farkları kullan.

**Geçer:** Maliyet/kovaryans stresi altında tekrarlayan çekişme artı istikrarlı
artımlı portföy faydası. **Başarısız:** nadir çekişme, yalnızca bağımsız-metrik
kazancı ya da belirsizlik içinde rank tersine dönmesi ranker'ı reddeder.

### EXP-EXEC-01 — Sadakat yükseltme kararı

**Soru:** Mevcut Expert sonucu için Level 1 yetersiz mi?

**Tasarım:** Level-1 muhafazakâr piyasa-tarzı replay'i, tam olarak aynı karar
akışında mevcut Level-2 agresif tick replay ile karşılaştır. Dolum zamanını,
spread'i, kaymayı, zaman aşımını ve rank değişikliklerini analiz et. Level 3
sertifikalanmadıkça pasif dolumları test etme.

**Geçer:** Hüküm istikrarlıysa, daha ucuz seviyeyi koru. **Yükselt:**
desteklenebilir daha zengin veriyle maddi işaret/rank duyarlılığı. **Engelle:**
duyarlılık, veride olmayan kuyruk/pasif semantiğine bağlı.

---

## VII. Nihai araştırma konumu

Makaleler, daha karmaşık bir mimariyi haklı çıkarmak yerine V8'in asgari
baseline'ını güçlendirir. Savunulabilir başlangıç noktası şudur:

`zaman-noktası MarketState → deterministik self-gating Expert'ler → tam Candidate
yaşam döngüsü → deterministik risk/kabul → kurallı Level-1 defter`.

Literatür daha keskin kabul koşulları ekler:

- **Router:** yalnızca self-gating maliyeti bağlayıcıysa ve değerli-candidate
  geri çağırımı ölçülebiliyorsa.
- **Scorer:** yalnızca eşleşen-kapsam eşleştirilmiş OOS kazancı, kalibrasyon ve
  tam-aile düzeltmesinden sonra.
- **Ranker:** yalnızca gösterilmiş portföy çekişmesi ve kovaryans/ortak-etki
  stresi altında marjinal net faydadan sonra.
- **Öğrenilmiş execution/RL:** yalnızca sertifikalı Expert değeri ve gerekli
  sadakatte simülatör otoritesinden sonra.
- **OFI/mikro yapı Expert'i:** yalnızca sıralı veri, açık kullanılabilirlik
  gecikmesi, derinlik/spread/haber koşullandırması ve eşzamanlı atıfın tahminden
  katı ayrımıyla.

Belirleyici ders "PBO kullan", "karekök etki kullan" ya da "OFI kullan" değildir.
Her iddiayı, onu gerçekten destekleyebilecek veriye, saate, koşullandırma
değişkenine, arama ailesine, simülatör seviyesine ve portföy kararına bağlamaktır.
Bundan daha geniş olan her şey bir V8 olgusu değil, bir deney önerisidir.