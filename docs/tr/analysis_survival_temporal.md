# Survival, Çok-Durumlu (Multi-State) Candidate Yaşam Döngüleri ve Zamansal Nokta Süreçleri (Temporal Point Processes)

## Kapsam, kaynak bütünlüğü ve iddia sınırı

Bu bölüm, listenin 16–29. maddelerini inceler. Liste on dört numaralı
girdi içerir ancak yalnızca **on üç farklı çalışma** barındırır: madde 28, madde
24'ün HTML görünümüdür, ayrı bir makale değildir. On iki farklı çalışma, tam PDF
olarak yerel olarak ya da arXiv'den erişilebilir durumdaydı. Madde 27'ye yalnızca
resmî OpenReview/NeurIPS sayfası ve arama-dizini metinleri üzerinden
erişilebildi çünkü PDF uç noktası bir anti-bot doğrulaması döndürdü; bu nedenle
madde 27'nin kanıtı açıkça poster özeti ve dizinlenmiş makale alıntılarıyla
sınırlıdır. Madde 20, verilen listede bir "ölçüm hatası" makalesi olarak yanlış
etiketlenmişti. Gerçek başlığı *Flexible multi-state models for
interval-censored data: specification, estimation, and an application to ageing
research*'tür.

İncelenen literatür, istatistiksel ayrımları ve veri-sözleşmesi
gereksinimlerini destekler. V8'in tahminî edge'e sahip olduğunu, execution'ı
iyileştirdiğini, kayıpları önlediğini ya da para kazandırdığını **kanıtlamaz**.
Tıp, kredi, DeFi borç verme ve bir vadeli işlemler emir defterinden gelen
sonuçlar; yöntemlerin kendi ortamlarındaki kanıtlarıdır, V8 ekonomisine dair
kanıt değildir. Aşağıdaki her önerilen aktarım, ampirik bir trading sonucu
olarak değil, test edilecek bir tasarım çıkarımı olarak etiketlenmiştir.

### Kaynak muhasebesi

| Madde | Farklı kaynak ve erişim | Kanıt durumu |
|---|---|---|
| 16 | Spadea & Seneviratne, *From Risk to Rescue* ([arXiv:2604.14583](https://arxiv.org/abs/2604.14583)); tam PDF | Ön baskı; Aave v3'te simülasyon çalışması, V8 kanıtı değil |
| 17 | Konstantinov, Efremenko & Utkin, *Survival Analysis as Imprecise Classification with Trainable Kernels* ([arXiv:2506.10140](https://arxiv.org/abs/2506.10140)); tam PDF | Ön baskı; tek-olaylı sağdan-sansürlenmiş yöntemler |
| 18 | Green et al., *FinSurvival* ([arXiv:2507.14160](https://arxiv.org/abs/2507.14160)); tam PDF | Ön baskı; açık DeFi benchmark'ı, açık sınırlamalarla |
| 19 | Groha, Schmon & Gusev, *A General Framework for Survival Analysis and Multi-State Modelling* ([arXiv:2006.04893](https://arxiv.org/abs/2006.04893)); tam PDF | Ön baskı; sinirsel-ODE çok-durumlu yöntem |
| 20 | Machado & van den Hout, *Flexible multi-state models for interval-censored data* ([arXiv:1703.08090](https://arxiv.org/abs/1703.08090)); tam PDF | Metodoloji ön baskısı; liste başlığı düzeltildi |
| 21 | Dempsey, *Exchangeable, Markov multi-state survival process* ([arXiv:1810.10598](https://arxiv.org/abs/1810.10598)); tam PDF | Kuramsal/metodolojik ön baskı |
| 22 | Zhong et al., *KANFormer for Predicting Fill Probabilities via Survival Analysis in Limit Order Books* ([arXiv:2512.05734](https://arxiv.org/abs/2512.05734)); tam PDF | Ön baskı; tek-enstrümanlı, ayrıcalıklı-feature'lı execution çalışması |
| 23 | Asanjarani, Liquet & Nazarathy, *Estimation of Semi-Markov Multi-state Models* ([arXiv:2005.14462](https://arxiv.org/abs/2005.14462)); tam PDF | Tekrarlanabilir vignette'lı metodolojik karşılaştırma |
| 24 | Rahman & Purushotham, *Pseudo value-based Deep Neural Networks for Multi-state Survival Analysis* ([arXiv:2207.05291](https://arxiv.org/abs/2207.05291)); tam PDF | KDD DSHealth atölye bildirisi |
| 25 | Lee & Lee, *A Behavioral Scorecard Model Using Survival Analysis* ([arXiv:2503.05023](https://arxiv.org/abs/2503.05023)); tam PDF | Uygulamalı ön baskı; aylık kesikli kredi ortamı |
| 26 | Weibull et al., *A multi-state model incorporating estimation of excess hazards and multiple time scales* ([arXiv:2012.13926](https://arxiv.org/abs/2012.13926)); tam PDF | Metodolojik/uygulama ön baskısı |
| 27 | Groha, Gusev & Schmon, *SurviVAEl: Variational Autoencoders for Clustering Time Series* ([OpenReview](https://openreview.net/forum?id=pREEF8_kWNT), [NeurIPS atölye sayfası](https://neurips.cc/virtual/2022/60051)); yalnızca resmî özet ve dizinlenmiş alıntılar | 2022 atölye posteri; doğrulanmış tam-PDF sonuç denetimi yok |
| 28 | Madde 24 ile aynı çalışma, ar5iv üzerinden sunulmuş | Kopya; bağımsız kanıt yok |
| 29 | Zhou et al., *Advances in Temporal Point Processes: Bayesian, Neural, and LLM Approaches* ([arXiv:2501.14291](https://arxiv.org/abs/2501.14291)); tam PDF, TMLR 06/2026'da yayımlanmış | Anket (survey), yeni bir ampirik model doğrulaması değil |

Aşağıda kullanılan kurallı metodolojik çapraz-kontroller şunlardır:
çok-durumlu modelleri geçiş yoğunlukları üzerinden tanımlayan ve gözlem
örüntülerini tartışan Andersen ve Keiding'in olay-geçmişi incelemesi
([DOI](https://doi.org/10.1191/0962280202SM276ra)); Kaplan–Meier ve kümülatif
insidansı Aalen–Johansen'in özel durumları hâline getiren, bakımı yapılan
`survival` paketi rakip-risk/çok-durumlu öğreticisi
([CRAN öğreticisi](https://stat.ethz.ch/CRAN/web/packages/survivalVignettes/vignettes/tutorial.html));
Leung, Elashoff ve Afifi'nin sansürleme varsayımları incelemesi
([DOI](https://doi.org/10.1146/annurev.publhealth.18.1.83)); ve Brown ve
arkadaşlarının nokta süreçleri için zaman-yeniden-ölçekleme teşhisi
([makale](https://sites.stat.columbia.edu/liam/teaching/neurostat-fall13/papers/brown-et-al/time-rescaling.pdf)).

## V8'in koruması gereken biçimsel ayrımlar

### Bir yaşam döngüsü olgusu otomatik olarak istatistiksel bir son nokta değildir

`CandidateEpisode`, durum değişiklikleri yalnızca-eklenen (append-only) bir
geçiş günlüğüyle kaydedilen bir yazılım nesnesi olsun. Güncel yazılım durumu, o
günlüğün deterministik bir izdüşümü olabilir. Bu, episode'u bir Markov süreci,
bir yarı-Markov (semi-Markov) süreci, bir rakip-risk (competing risk) kaydı ya
da bir zamansal nokta süreci (temporal point process) hâline getirmez. Bunlar,
belirtilmiş bir rastgele niceliğe ve gözlem şemasına dayatılan alternatif
istatistiksel modellerdir.

Tek bir terminal olay için, gizli olay zamanını (T), sansürleme zamanını
(C), gözlenen zamanı (Y=\min(T,C)) ve olay göstergesini
(\Delta=1\{T\leq C\}) tanımlayın. Hayatta kalma fonksiyonu ve tehlike (hazard)
şunlardır:

\[
S(t\mid x)=P(T>t\mid x), \qquad
\lambda(t\mid x)=\lim_{h\downarrow0}\frac{P(t\leq T<t+h\mid T\geq t,x)}{h}.
\]

Bir kaydı "expired" (sona erdi), "not executed" (execute edilmedi) ya da
"rejected" (reddedildi) olarak adlandırmak; onun bir olay mı, rakip bir neden mi
yoksa sansürleme mi olduğunu belirlemez. Bu seçim, tahmin hedefine (estimand)
bağlıdır. Soru `PENDING`'den ilk trigger'a kadarki süre ise, trigger'dan önceki
expiry rakip bir son nokta olabilir. Soru, gözlenen emir politikası altında emir
gönderiminden ilk fill'e kadarki süre ise, trader tarafından talep edilen bir
iptal rakip bir olay olabilir; bunu bilgi-vermeyen sansürleme (non-informative
censoring) olarak ele almak, güçlü ve çoğu zaman inandırıcı olmayan bir
varsayımdır çünkü iptal kararları, fill'i yöneten aynı emir-defteri geçmişine
bağlıdır. Madde 22, iptali ya da piyasa-kapanışı expiry'sini açıkça sansürleme
olarak ele alır ve kovaryantlar verildiğinde fill ile sansürlemenin koşullu
bağımsızlığını varsayar; bu bir model varsayımıdır, emir verisinin genel bir
özelliği değildir ([arXiv:2512.05734](https://arxiv.org/abs/2512.05734)).

### Rakip riskler olay nedenleri gerektirir, ikili etiketlerden oluşan bir torba değil

İlk terminal zamanı (T) ve neden (J\in\{1,\ldots,K\}) için, nedene-özgü
tehlike şöyledir:

\[
\lambda_k(t\mid H_{t-})=
\lim_{h\downarrow0}\frac{P(t\leq T<t+h,J=k\mid T\geq t,H_{t-})}{h},
\]

kümülatif insidans ise:

\[
F_k(t)=P(T\leq t,J=k)=\int_0^t S(u-)\lambda_k(u)\,du.
\]

Nedene-özgü tehlike ve kümülatif insidans farklı sorulara yanıt verir. Bir
nedene-özgü tehlikedeki artış, episode'ları risk kümesinden çıkararak başka bir
nedenin gözlenen kümülatif insidansını azaltabilir. Bu nedenle ayrı
tek-karşı-hepsi (one-vs-rest) hayatta kalma uyumları, otomatik olarak tutarlı
bir ortak rakip-risk modeli değildir. CRAN öğreticisi, Aalen–Johansen
tahmincisinin genel durum-işgal tahmincisi olduğunu ve bir rakip-risk grafiği
için kümülatif insidansa indirgendiğini gösterir
([öğretici](https://stat.ethz.ch/CRAN/web/packages/survivalVignettes/vignettes/tutorial.html)).

V8 bu nedenle, kaynak durumu ve tahmin hedefi başına hangi son noktaların rakip
olduğunu belirtmelidir. `REJECTED`, `EXPIRED`, `INVALIDATED` ve `ACCEPTED`,
yalnızca her biri zaman damgası çözünürlüğünde karşılıklı olarak ayrık ise ve
eşitlik (tie) politikası önceden bildirilmişse, `PENDING`'den ilk çıkışlar
olarak rakip olabilir. `ARCHIVED` bir saklama eylemidir, doğal bir olay nedeni
değildir. `CLOSED`, execution'ın akış yönündedir ve trigger-öncesi bir
reddedilmeyle aynı risk kümesinde değildir. Tüm terminal adlarını tek bir düz
"candidate sonucu" içinde karıştırmak, kaynak durumunu ve risk-kümesi tanımını
yok eder.

### Çok-durumlu nicelikler farklıdır

Durum süreci (X(t)\in\mathcal S) ve izin verilen edge (j\to k) için üç nesne
birbirine karıştırılmamalıdır:

1. geçiş yoğunluğu (\lambda_{jk}(t\mid H_{t-})), (j) durumunu işgal etme
   koşuluna bağlı anlık bir oran;
2. geçiş olasılığı
   (P_{jk}(s,t\mid H_s)=P(X(t)=k\mid X(s)=j,H_s));
3. durum-işgal olasılığı (\pi_k(t)=P(X(t)=k)) ya da (s) anındaki geçmişe
   koşullu landmark/dinamik sürümü.

Madde 24, geçiş olasılığını, durum-işgal olasılığını ve dinamik durum-işgal
olasılığını açıkça ayrı hedefler olarak tahmin eder
([arXiv:2207.05291](https://arxiv.org/abs/2207.05291)). Madde 19,
sürekli-zamanlı bir modelde geçiş yoğunluklarını ve işgal olasılıklarını
birbirine bağlamak için Kolmogorov ileri denklemlerini çözer
([arXiv:2006.04893](https://arxiv.org/abs/2006.04893)). "Geçiş olasılığı" adı
verilen bir skor; kaynak durumu, varış noktası, koşullandırma geçmişi, tahmin
kaynağı, ufuk ve tahminciyi belirtmedikçe eksiktir.

### Markov, yarı-Markov, geçmişe-bağımlı ve deterministik farklıdır

Markov varsayımı, güncel duruma (ve bildirilmiş herhangi bir güncel
kovaryanta/zamana) koşullu olarak, daha erken yörünge geçmişinin gelecek
hakkında ek bilgi sağlamadığını söyler. Zaman-homojen bir sürekli-zamanlı Markov
zinciri, üstel, hafızasız bekleme süreleri ima eder. Yarı-Markov bir süreç,
ziyaret edilen durumların Markov gömülü zincirini korur ancak üstel olmayan
bekleme sürelerine izin verir ve geçiş riskini, güncel duruma girişten bu yana
geçen süreye bağımlı kılar. Genel bir geçmişe-bağımlı süreç, tam yola bağlı
olabilir. Deterministik bir yazılım geçiş doğrulayıcısı, tek başına bunların
hiçbiri değildir.

Madde 23, V8'in koruması gereken bir ayrım daha yapar. "Yaklaşım I", gömülü bir
geçiş olasılığı (p_{ij}) ve sonraki duruma (j) koşullu bir bekleme (sojourn)
dağılımı kullanır. "Yaklaşım II", yalnızca bekleme süresinden (u) sonra hâlâ (i)
durumunu işgal etme koşuluna bağlı geçiş yoğunluğunu (\tilde\alpha_{ij}(u))
kullanır. Varış noktasına koşullu bekleme tehlikesi ile nedene-özgü geçiş
yoğunluğu sayısal olarak aynı değildir; makale aralarındaki dönüşümü türetir
([arXiv:2005.14462](https://arxiv.org/abs/2005.14462)). Bu nedenle yalnızca
`transition_hazard` adlandırılmış bir alan, eksik belirlenmiştir.

### Olay zamanı, gözlem zamanı ve bilgi zamanı farklı saatlerdir

Veri sözleşmesi en azından şunlara ihtiyaç duyar:

| Saat | Anlamı | Neden tek bir değere indirgenemez |
|---|---|---|
| `event_time` | Kaynak olayın kaynağa göre gerçekleştiği zaman | Fiziksel sıralamayı tanımlar ancak o anda gözlenebilir olmayabilir |
| `available_time` | Yükün, bildirilen feed altında sisteme kullanılabilir olduğu en erken zaman | Nokta-içi (point-in-time) feature kabul edilebilirliğini yönetir |
| `ingested_time` | Bu kurulumun yükü aldığı/kalıcı hâle getirdiği zaman | Operasyonel gecikmeyi ve replay farklılıklarını ölçer |
| `knowledge_time` | Sistemin olgu üzerinde meşru biçimde harekete geçebildiği ledger zamanı | Düzeltmeleri ve nedensel karar görünümlerini sıralar |
| `decision_time` | Bir Expert/risk/execution aktörünün karar verdiği zaman | Tahmin kaynağını ve feature kesimini tanımlar |
| `birth_time` ve `episode_age` | Candidate kaynağı ve kaynaktan bu yana geçen süre | Saat-ileri (clock-forward) hayatta kalma ölçeği |
| `state_entry_time` ve `state_age` | Güncel yaşam döngüsü durumuna giriş ve bekleme süresi | Saat-sıfırlama (clock-reset) yarı-Markov ölçeği |
| `calendar_time` | Mutlak zaman/rejim/mevsim | Zamanda-homojen-olmayan etkilere izin verir |
| `observation_start` | Geçerli risk-kümesi gözleminin başlangıcı | Gecikmiş giriş/soldan-truncation için gereklidir |
| `label_horizon_end` | Önceden bildirilmiş sonuç penceresinin sonu | Sağdan sansürlemeyi ve olgunluğu tanımlar |
| `label_available_time` | Etiketi hesaplamak için gereken tüm verilerin kullanılabilir olduğu zaman | Olgun sonuçların geriye sızmasını önler |

Madde 26, ulaşılan yaş, takvim zamanı ve tanıdan bu yana geçen sürenin farklı
geçiş modellerine girebileceğinin ve tek bir genel zaman damgasıyla
değiştirilemeyeceğinin somut bir gösterimidir
([arXiv:2012.13926](https://arxiv.org/abs/2012.13926)). Madde 23, mutlak takvim
zamanını sıfırlanmış bekleme süresinden ayırır ve kendi karşılaştırmasının zaman
homojenliği varsaydığını belirtir. Madde 29, sonraki-olay yoğunluğu için son
olaydaki geçmişi (H_{t_n}) ile koşullu yoğunluk için keyfi (t) zamanından hemen
önceki geçmişi (H_{t-}) dikkatle ayırır
([arXiv:2501.14291](https://arxiv.org/abs/2501.14291)). Yukarıdaki kesin
yazılım saat adları bir V8 tasarım çıkarımıdır; ancak anlamlarının tek bir
değere indirgenmeme gerekliliği, bu farklı istatistiksel nesnelerden ve
nokta-içi karar geçerliliğinden doğrudan çıkar.

## Makale-makale kanıt, sınırlamalar ve güvenli V8 aktarımı

### 16. *From Risk to Rescue: An Agentic Survival Analysis Framework for Liquidation Prevention*

**Ne yapar.** Makale, borç-alma-ile-tasfiye gibi olay çiftleri için ayrı XGBoost
Cox modelleri ve türetilmiş sabit-ufuklu bir "dönüş periyodu" etrafında bir Aave
v3 müdahale çerçevesi kurar. Elle belirlenmiş bir zamansal eğilim skoru ekler ve
simüle edilmiş geri-ödeme/mevduat müdahalelerini arar. Değerlendirme, zincir-üstü
Aave/Polygon kaynaklı kayıtları ve bir protokol simülatörünü kullanır
([arXiv:2604.14583](https://arxiv.org/abs/2604.14583)).

**Raporlanan kanıt.** Kaynak, 21,8 milyondan fazla ham kayıt, 90 tasarlanmış
feature, 8.400-kontrollü bir ön-filtre örneği ve 4.882-profillik nihai yüksek
risk kohortu bildirir. Tasfiye-ile-biten örnekler, çift başına bilinçli olarak
en kısa 300 zaman-başına-olay vakasını seçer. Simülatörü; genişleyen bir efektif
tasfiye eşiği, 1,5x güvenlik faktörüyle çıkarılan harici cüzdan bakiyeleri,
dust filtreleri ve altı tespit prosedürü kullanır. Simülatör sağlık-faktörü
korelasyonu, tasfiye öngörüsü, sıfır simüle kötüleşme oranı ve seçilen kohortta
%86,83'lük simüle tasfiye azalması raporlar.

**Sınırlamalar.** Bunlar, kurulmuş bir simülatör altındaki eşleştirilmiş replay
sonuçlarıdır; gözlenen karşı-olgusal sonuçlar değildir. Dinamik tasfiye sınırı,
cüzdan çıkarımı, hariç tutmalar, gaz varsayımları ve müdahale uygulanabilirlik
kuralları, sonucu üreten mekanizmanın parçasıdır. Yaklaşan tasfiyeleri seçmek,
bir nüfus tahmini değil, bir stres-testi popülasyonudur. "Doğruluk %69,11",
hayatta kalma kalibrasyonu kurmak için yeterince tanımlı değildir. Makale birkaç
olay türünü "eşzamanlı" tahmin ettiğini söylese de, alttaki FinSurvival görevleri
index–sonuç çiftleridir; bunun tutarlı bir ortak rakip-risk olabilirliği
olduğu gösterilmemiştir. Sonuç, V8 ekonomisini, Candidate durumlarını ya da bir
execution politikasını doğrulayamaz.

**Güvenli aktarım.** Gözlenen sonuçları simüle edilmiş karşı-olgusal
sonuçlardan ayrı tutun; her karşı-olgusalla birlikte simülatör/config/sürümünü
saklayın; kohort filtrelerini önceden bildirin; müdahale karşılaştırmalarından
önce simülatör durum-yeniden-yapılandırmasını doğrulayın; simüle edilmiş
kurtarmayı asla gözlenen nedensel kurtarma olarak tanımlamayın. Makale,
hayatta-kalma-koşullu izlemeyi güdüler ancak bir V8 modeli seçmez.

### 17. *Survival Analysis as Imprecise Classification with Trainable Kernels*

**Ne yapar.** Makale zamanı aralıklara ayrıklaştırır ve sağdan-sansürlenmiş bir
örneği, gelecek aralıklar üzerindeki olası olasılık dağılımları kümesiyle temsil
eder. Eğitilebilir Nadaraya–Watson/dikkat kernel'leri bu belirsiz etiketleri
birleştirir. Üç eğitim varyantı (iSurvM, iSurvQ, iSurvJ), C-index ve entegre
Brier skoru kullanılarak Beran tahmincisiyle karşılaştırılır
([arXiv:2506.10140](https://arxiv.org/abs/2506.10140)).

**Raporlanan kanıt.** Yazarlar, çoğu gerçek veri kümesinde ve sentetik
ortamlarda Beran'a göre iyileşmeler bildirir; iSurvJ varyantları, özellikle
boyut ve sansürleme arttıkça en güçlüsüdür. Ayrıca örneklerde Beran tahminlerini
içeren aralık-değerli hayatta kalma bantları gösterirler.

**Sınırlamalar.** Karşılaştırma temel olarak tek bir kernel tahmincisinedir;
tam hayatta-kalma-modeli manzarasına değil. Hiperparametre optimizasyonu
sonuçları önemli ölçüde etkiler; sinirsel sürüm ölçeklenmeyebilir. Çalışma küçük
ve orta boyutlu verileri kapsar. En önemlisi, makale rakip riskleri ve
zamana-göre-değişen kovaryantları açıkça gelecek çalışmaya bırakır. Aralık-değerli
temsili, bir modelleme kurulumu altında epistemik belirsizliği ifade eder; otomatik
olarak kalibre edilmiş bir tahmin aralığı ya da bir V8 reddetme (reject) seçeneği
değildir.

**Güvenli aktarım.** Sansürlenmiş episode'ları düşürmek yerine elde tutmayı ve
bir olay-zamanı dağılımını ikili bir terminal etiketinden ayırmayı destekler.
`EXPIRED` ya da `INVALIDATED`'ı belirsiz olasılıklar olarak ele almayı
gerekçelendirmez; ayrıca yeni bir rakip-risk uzantısı ve kalibrasyon çalışması
olmadan çok-nedenli Candidate etiketlerini desteklemez.

### 18. *FinSurvival: A Suite of Large Scale Survival Modeling Tasks from Finance*

**Ne yapar.** FinSurvival, kamuya açık Aave Ethereum işlemlerini 16
index-olay/sonuç-olayı hayatta kalma görevine dönüştürür (borç alma, mevduat,
geri ödeme, çekim, tasfiye); zamansal ve kullanıcı/piyasa geçmişi feature'larıyla.
Ayrıca, kısıtlı ortalama hayatta kalma süresi (RMST) üzerinde eşikleme yaparak
ikili görevler oluşturur
([arXiv:2507.14160](https://arxiv.org/abs/2507.14160)).

**Raporlanan kanıt.** Makale 7.698.497 görev kaydı, 114.861 kullanıcı, 60 varlık,
128 feature ve ortalama %81,26 sansürleme bildirir. Feature'lar, index işlemine
"kadar" geçmiş özetleri olarak tanımlanır. Bölme zamansaldır (kesim tarihi 1
Temmuz 2022) ve uç tamponları içerir. Klasik XGBoost/AFT baseline'ları, hayatta
kalma görevlerinde test edilen derin hayatta kalma modellerini geride bırakır;
lojistik regresyon ve elastik net, RMST-eşikli sınıflandırma görevlerinde başı
çeker. Performans olay çiftine göre önemli ölçüde değişir.

**Sınırlamalar.** Makale, raporlanan analizin rakip riskleri **modellemediğini**
açıkça belirtir; boru hattı bunu yapacak şekilde genişletilebilse bile. İkili
görevler, index olaylarını farklı sonuç tanımları arasında kopyalar ve tek bir
ortak yaşam döngüsü oluşturmaz. Sınıflandırma, RMST eşiğinden önce sansürlenen
kayıtları düşürür ve hedef popülasyonu değiştirir. Tek bir zaman kesimi artı
tamponlar, tek başına örtüşen kullanıcı/olay geçmişlerinin, hesap kümelenmesinin
ya da kullanılabilirlik-zamanı feature soyağacının temizlendiğini göstermez.
Elle kurulmuş feature'lar ve protokol/kullanıcı davranışı alana-özgüdür.
Makalenin kamuya açık blok zincirleri hakkındaki geniş adillik/gizlilik
ifadeleri V8 için gerekli değildir ve miras alınmamalıdır.

**Güvenli aktarım.** FinSurvival; index olayını, sonuç nedenini, süreyi,
sansürleme göstergesini, kullanıcı/enstrüman gruplamasını ve zamansal bölme meta
verilerini açık tutmak için güçlü bir kanıttır. Ayrıca yararlı bir olumsuz sonuç
sağlar: ölçek, derin bir modeli en iyi yapmaz ve hayatta kalma ile eşikli
sınıflandırma, model ailelerini farklı şekilde sıralayabilir. Bir V8 Candidate
grafiğini doğrulayamaz ya da ayrı ikili olay-çifti modellerinin çok-durumlu bir
model olarak adlandırılmasına izin vermez.

### 19. *A General Framework for Survival Analysis and Multi-State Modelling*

**Ne yapar.** SurvNODE, nedene-özgü geçiş yoğunluklarını sinirsel adi
diferansiyel denklemlerle modeller ve geçiş/durum olasılıkları için Kolmogorov
ileri denklemlerini çözer. Düz bir Markov temsilini gevşetmek için gizli bir
bellek durumu sunulur; bir varyasyonel uzantı, bireysel belirsizliği ve
kümelenmeyi modeller
([arXiv:2006.04893](https://arxiv.org/abs/2006.04893)).

**Raporlanan kanıt.** Makale; standart tek-olaylı, rakip-riskli ve simüle
çok-durumlu görevlerde, orantılı-olmayan ve doğrusal-olmayan ortamlar dahil,
rekabetçi sonuçlar bildirir. Ayrımcılığı ve kalibrasyon-yönelimli nicelikleri
değerlendirir ve yörünge kümeleri gösterir.

**Sınırlamalar.** Makalenin "varsayımdan-bağımsız" ifadesi harfiyen
okunmamalıdır. Seçilmiş bir durum grafiğini, olabilirlik/gözlem sürecini,
sansürleme koşullarını, türevlenebilir parametreleştirmeyi, optimizasyon
prosedürünü ve genelleşmeye yetecek kadar kararlı bir veri-üretim ilişkisini
varsayar. Öğrenilmiş bir gizli bellek durumu, sonlu gözlenen-durum Markov
varsayımını gevşetir; nedensel geçmişi tanımlanabilir kılmaz. Sinirsel esneklik,
yorumlanabilirlik ve örnek verimliliğini uyum karşılığında takas edebilir.
Tıbbi/sentetik benchmark'lar bu mimariyi V8 için seçmez.

**Güvenli aktarım.** V8 için ana katkı kavramsaldır: birden fazla geçici/absorbe
edici durum önemli olduğunda, kopuk terminal etiketlerini uydurmak yerine tutarlı
geçiş ya da işgal niceliklerini tahmin edin. Aalen–Johansen/Cox ya da basit
yarı-Markov baseline'larıyla başlayın; SurvNODE yalnızca daha sonraki bir
karmaşıklık ablasyonuna aittir.

### 20. *Flexible multi-state models for interval-censored data*

**Ne yapar.** Machado ve van den Hout; yaşam durumları arasındaki geçişler
yalnızca ziyaretlerde gözlenirken ölüm zamanlarının kesin olabileceği durumlarda
sürekli-zamanlı, birinci-dereceden Markov çok-durumlu modeller uydurur.
Geçişe-özgü Weibull, Gompertz ya da P-spline tehlike fonksiyonları cezalandırılmış
olabilirlikle tahmin edilir; geçiş olasılıklarındaki belirsizlik simülasyonla
yayılır ([arXiv:1703.08090](https://arxiv.org/abs/1703.08090)).

**Raporlanan kanıt.** Uygulama, aralıklı olarak gözlenen bilişsel durumları ve
bilinen ölüm zamanları olan bir İngiliz yaşlanma kohortunu kullanır. Yöntem,
ziyaret zamanlarını kesin geçiş zamanları gibi varsaymak yerine olabilirlik
katkılarını gözlem zamanları arasındaki geçiş olasılıklarından kurar. Esnek
spline tehlike fonksiyonları zaman-bağımlılık modellemesini iyileştirir.

**Sınırlamalar.** Koşullu birinci-dereceden Markov varsayımı açıktır. Gözlem
takvimi ve kovaryant uzlaşımı olabilirliğin parçasıdır. Spline pürüzlülüğü AIC
ile seçilir; gözlenen zaman aralıklarının ötesine tahmin, hâlâ tehlike şekline
bağlıdır. Liste notuna rağmen kaynağın ölçüm hatasıyla hiçbir ilgisi yoktur.

**Güvenli aktarım.** V8 yalnızca bar-kapanışı kanıtı görüyorsa — bir
predicate'in bir bar içinde değiştiğine dair — geçişi kesin bir olay olarak
sessizce kapanışa/açılışa atamamalıdır. Bir geçiş aralığını ya da belirtilmiş bir
simülatör uzlaşımını koruyun. Bu makale aralık-sansürlü geçiş işlemeyi destekler;
Candidate episode'ları için Markov varsayımını kanıtlamaz.

### 21. *Exchangeable, Markov multi-state survival process*

**Ne yapar.** Dempsey; Markov olan, birim yeniden-etiketlemeye değişmez olan ve
alt-örnekleme altında tutarlı olan nüfus-değerli süreçleri karakterize eder.
Aralıklı gözlenen ve sansürlenmiş çok-durumlu yollar için yaklaşık bir MCMC şeması
geliştirir ve bunu kardiyak allograft vaskülopatisine uygular
([arXiv:1810.10598](https://arxiv.org/abs/1810.10598)).

**Raporlanan kanıt.** Kuram, değişebilirliğin (exchangeability) ve
örnek-boyutu tutarlılığının bir nüfus süreçleri sınıfını nasıl kısıtladığını
açıklığa kavuşturur. Uygulama, yıllık muayeneleri olan 622 hastayı içerir ve
randevular arasında gizli hastalık ilerlemesi için hayatta kalma tahminlerini
ayarlamak üzere birleştirilebilir bir Markov modeli kullanır.

**Sınırlamalar.** Değişebilirlik, IID'nin eş anlamlısı değildir ve koşullandırma
olmadan V8'e uygulanabilirliği kuşkuludur: Candidate episode'ları enstrümana,
experte, rejime ve eşzamanlılığa göre farklılık gösterir. Bu kuramdaki
"alt-örnekleme altında tutarlılık", bir müdahale-yokluğu (lack-of-interference)
koşulu ima eder; piyasa candidate'ları paylaşılan olaylar, kapasite ya da
kopya-ayıklama yoluyla etkileşebilir. Yöntem ayrıca zaman-homojen Markov
dinamikleri ve gözlenen geçmiş verildiğinde bilgi-vermeyen gözlem zamanları
varsayar. Bu varsayımlar özseldir, varsayılan değildir.

**Güvenli aktarım.** Yararlı ders; nüfus değişmezliklerini ve gözlem-süreci
varsayımlarını açıkça belirtmek ve bağımlılığı test etmektir. V8, ilişkili
episode'ları gruplamalı ya da kümelemelidir ve bu makaleyi keyfi candidate
yeniden-etiketleme ya da bağımsızlık iddia etmek için kullanmamalıdır.

### 22. *KANFormer for Predicting Fill Probabilities via Survival Analysis in Limit Order Books*

**Ne yapar.** KANFormer, limit emrin ilk kısmi ya da tam fill'ine kadar geçen
süreyi tahmin eder. Fill'den önceki iptal ya da piyasa kapanışı sağdan
sansürleme olarak kodlanır. Model; LOB anlık görüntülerini, eylem-türü
geçmişlerini, katılımcı-düzeyi davranışı ve kuyruk pozisyonunu birleştirir ve
kovaryant-bağımlı bir Weibull hayatta kalma eğrisi tahmin eder
([arXiv:2512.05734](https://arxiv.org/abs/2512.05734)).

**Raporlanan kanıt.** Veriler, 2016–2017'de 300 gün boyunca yakın-ay CAC 40
endeks vadeli işlemlerini kapsar ve kronolojik olarak eğitim/doğrulama/test
bölünür. 30 veri kümesi gerçekleştirmesi boyunca makale KANFormer RCLL 0,53,
IBS 0,027, entegre AUC 0,76 ve C-index 0,72 bildirir. AUC/Brier entegrasyon
penceresi, medyan olay-zamanı yüzdelik dilimine kadar yalnızca 20 ufku kapsar ve
üst sınırı 0,627 saniyedir. Ablasyon, kuyruk pozisyonu kaldırıldığında en büyük
ayrımcılık kaybını bildirir.

**Sınırlamalar.** Çıktı için Weibull formu varsayılır. 30 çalıştırma ilk
modelden sıcak-başlatılır; bu nedenle tam eğitim rastgeleliğinden çok veri kümesi
bileşimini izole ederler. Makale tek bir enstrümanı, mekanı, dönemi ve saniye-altı
ufku kapsar. Herhangi bir kısmi fill'i olay olarak tanımlar; bu nedenle tam fill
süresine, fill kesrine, ters-seçime (adverse selection), iptal politikasına ya da
execute edilebilir PnL'ye yanıt vermez. Yazarlar, tam katılımcı davranışı
feature'larının tek bir piyasa katılımcısı tarafından gözlemlenebilir olmadığını
açıkça belirtir. En kritik nokta, iptalin fill riskiyle ilişkili olması
muhtemeldir; onu bağımsız sansürleme olarak kodlamak, bir koşullu-bağımsızlık
argümanı ve duyarlılık testleri gerektirir.

**Güvenli aktarım.** `first_fill`, `partial_fill_update`, `full_fill`,
`cancel_request`, `cancel_ack` ve `expiry` olaylarını ayırın. Kuyruk bilgisini
yalnızca gerçekten mevcut ve kalibre edilmiş olduğunda saklayın. Bir fill-hayatta
kalma deneyi, yalnızca-gözlenebilir ve ayrıcalıklı-feature varyantlarını
karşılaştırmalıdır. Bu çalışma; pasif/kuyruk fill iddialarının sıralı L2 artı
ayrı olarak doğrulanmış bir emir/fill otoritesi gerektirdiği V8 kuralını
zayıflatmaktan çok güçlendirir.

### 23. *Estimation of Semi-Markov Multi-state Models*

**Ne yapar.** Makale iki yarı-Markov parametreleştirmesini karşılaştırır: gömülü
geçiş olasılıkları artı varış-noktası-koşullu bekleme dağılımları ve durum
girişinden bu yana geçen süreyle dizinlenen geçişe-özgü yoğunluklar. İki gerçek-veri
örneğiyle kesin ilişkiyi, olabilirlik sonuçlarını, yorumları ve yazılım takaslarını
türetir ([arXiv:2005.14462](https://arxiv.org/abs/2005.14462)).

**Raporlanan kanıt.** Geçiş-yoğunluğu parametreleştirmesi, geçişlerin ayrı
parametreleri olduğunda olabilirliği daha küçük iki-durumlu bileşenlere
bölebilir ve standart hayatta kalma araçlarını etkinleştirir. Bekleme-zamanı
parametreleştirmesi, ilgi nesnesi varış noktasına koşullu bekleme süresi
olduğunda daha doğal olabilir. Makale tekrarlanabilir R kodu/vignette sağlar.

**Sınırlamalar.** Ampirik örnekler, evrensel tahmin üstünlüğü kurmaktan çok
yorumu örnekler. Ana ele alış parametrik ve zaman-homojendir; makale takvim-zamanı
homojensizliğini açıkça gelecek çalışmaya bırakır. Olabilirlikleri bölmek,
bildirilen parametreleştirme altında geçerlidir; bağımlılığı ya da rakip riskleri
görmezden gelme izni değildir.

**Güvenli aktarım.** Candidate modellemesi `state_entry_time` ve `state_age`
taşımalıdır. Her tehlike alanı, varış noktasına koşullu olup olmadığını
bildirmelidir. En ucuz test sinirsel bir model değildir: aynı katlamalar ve tahmin
hedefi üzerinde bir saat-ileri baseline'ı, bir saat-sıfırlama yarı-Markov
baseline'ı ve bir geçmiş-feature baseline'ını karşılaştırın.

### 24 ve 28. *Pseudo value-based Deep Neural Networks for Multi-state Survival Analysis*

**Ne yapar.** Madde 24; durum işgali, dinamik işgal ve geçiş olasılıkları için
jackknife pseudo-değerleri üzerinde eğitilen `msPseudo` adlı bir ileri-beslemeli
sinirsel regresör önerir. Test edilmiş bir Markov varsayımı altında sıradan
Aalen–Johansen'i, bu varsayım reddedildiğinde ise landmark Aalen–Johansen'i seçer.
Madde 28, tam olarak aynı makalenin HTML hâlidir
([arXiv:2207.05291](https://arxiv.org/abs/2207.05291)).

**Raporlanan kanıt.** Deneyler; 5.000 örnekli dört simüle Markov/Markov-olmayan
veri üreteci, METABRIC (1.975 hasta) ve EBMT'yi (2.279 hasta) içerir. Beş
tekrarlı beş-katlı çapraz-doğrulama, entegre AUC ve Brier skorunu değerlendirir.
Makale, seçilen çok-durumlu baseline'lardan daha iyi ortalama performans ve
tetiklenmiş/kademeli %75 sansürleme testlerinde sağlamlık bildirir.

**Sınırlamalar.** Bu kısa bir atölye bildirisidir. Pseudo-değerleri, seçilen
tahmincinin varsayımlarını ve hatalarını miras alır; Markov özelliğini test edip
ardından bir tahminci seçmek, belirsizliği otomatik olarak temsil edilmeyen
veriye-bağımlı bir seçim katmanı ekler. Gerçek veri için "gerçek değer", gözlenen
bireysel bir olasılık değil, bir pseudo-sonuçtur. Baseline kovaryantları ve
önceden seçilmiş ufuklar kuruluma hükmeder. Tıbbi/simüle sonuçlar V8'i
doğrulamaz ve kopya madde kanıt eklemez.

**Güvenli aktarım.** İşgal, dinamik işgal ve geçiş hedeflerini açıkça
adlandırmayı, Markov yeterliliğini test etmeyi ve basit Aalen–Johansen/landmark
baseline'larını tutmayı destekler. Durum grafiği, risk kümeleri, gözlem kesimleri
ve sansürleme mekanizması kararlı olana dek sinirsel bir scorer'ı gerekçelendirmez.

### 25. *A Behavioral Scorecard Model Using Survival Analysis*

**Ne yapar.** Bu uygulamalı makale, aylık Freddie Mac kredi geçmişlerini landmark
panellerine genişletir, lojistik regresyonla aylık temerrüt tehlikesini tahmin
eder ve kümülatif temerrüt olasılığını bir skor kartına eşler
([arXiv:2503.05023](https://arxiv.org/abs/2503.05023)).

**Raporlanan kanıt.** 2018–2021'de başlatılan krediler, Haziran 2021'e kadarki
bir in-sample kohort ile daha sonraki bir holdout arasında bölünür. Aylık
panelleri tamamen patlatmak yaklaşık 504,6 milyon satır yaratırdı; çalışma bu
yüzden yaklaşık 30,6 milyon satırlık ağırlıklı bir örneklem kullanır. Statik,
zamana-göre-değişen, süre, makroekonomik ve mevsimsel terimleri modeller; ofset
ayarından sonra in-sample AUC 0,82 ve zaman-dışı (out-of-time) AUC 0,70 bildirir.

**Sınırlamalar.** Bin boyutları ve örnekleme ağırlıkları keyfi olarak tanımlanır
ve gelecek çalışmaya bırakılır. Tek bir krediden gelen tekrarlanan landmark
satırları bağımlıdır; makale GEE'yi inceler ama çalışan-korelasyon
karşılaştırmasından sonra sıradan lojistik regresyonu korur. Aylık kesikli-zaman
eşitlikleri, nadir-olay ayrımı, seçilen spline terimleri, skor ofsetleri ve bir
Youden-endeksi kesimi uygulama kararlarıdır. AUC, olasılık kalibrasyonu ya da
müdahale faydası kurmaz. Makalenin skor-kartı ölçeklemesi ve nezaket-çağrısı
eşiğinin doğrudan bir V8 anlamı yoktur.

**Güvenli aktarım.** Landmark satırları bir tahmin-kökeni tanımlayıcısı,
özne/episode grubu, örneklem ağırlığı ve ufuk taşımalıdır. Eğitim/test bölmeleri,
örtüşen landmark'ların ve etiket aralıklarının sızmasını engellemelidir.
Kesikli-zaman tehlike, veri çözünürlüğü gerektirdiğinde ucuz bir baseline'dır;
evrensel bir model değildir.

### 26. *A multi-state model incorporating estimation of excess hazards and multiple time scales*

**Ne yapar.** Makale, göreli sağkalım ile çok-durumlu modellemeyi birleştirerek
beklenen nüfus oranlarını aşırı (excess) oranlardan ayırır; geçiş modellerinin
ulaşılan yaş, takvim zamanı ve tanıdan bu yana geçen süreyi kullanmasına izin
verir ([arXiv:2012.13926](https://arxiv.org/abs/2012.13926)).

**Raporlanan kanıt.** Bir Hodgkin lenfoma uygulaması; morbidite ve mortalite
durum olasılıklarını, kovaryantlar arasındaki farkları ve aşırı ile beklenen
oranlara atfedilen oranları tahmin eder. Esnek parametrik tehlikeler ve
parametrik bootstrap belirsizliği Stata'da uygulanmıştır.

**Sınırlamalar.** Beklenen/aşırı ayrımı, harici nüfus tabloları ve
tabakalaşmadan sonra referans nüfusla değişebilirlik gerektirir. Nedensel bir
tedavi yorumu daha fazla varsayım gerektirir. Örnek yalnızca ara hastalığın ilk
görülümünü kullanır ve tekrarlayan olayları gelecek çalışma olarak not eder.
Birden çok bileşen modelin her biri uyum için kontrol edilmelidir ve gizli-zaman
simülasyonunun bilinen bir yorum tartışması vardır.

**Güvenli aktarım.** V8, beklenen/aşırı tehlike semantiğini içe aktarmamalıdır.
Aktarılabilir nokta yalnızca çoklu-zaman-ölçeği sözleşmesi ve her geçişi hangi
ölçeğin sürdüğünü belirleme gerekliliğidir. Tekrarlayan Candidate episode'ları,
önceki bir episode'u sessizce üzerine yazmak yerine açık yeni episode/ebeveyn ya
da tekrarlayan-olay semantiği gerektirir.

### 27. *SurviVAEl: Variational Autoencoders for Clustering Time Series*

**Ne yapar.** Resmî özet, tahmin belirsizliğini ölçmek ve hasta yörüngelerini
kümelemek için tasarlanan VAE-tabanlı bir çok-durumlu sağkalım çerçevesini
tanımlar; dizinlenmiş alıntılar, gizli kümelerin parametrik-olmayan
Aalen–Johansen işgal tahminleriyle özetlendiğini gösterir
([OpenReview](https://openreview.net/forum?id=pREEF8_kWNT)).

**Raporlanan kanıt.** Erişilebilir resmî kayıt, yöntemin amacını ve atölye-posteri
durumunu kurar. Genel sayfada doğrulanmış sonuç tabloları açığa çıkmaz. Kontrol
edildiği anda sıfır genel OpenReview yanıtı vardı.

**Sınırlamalar.** Tam PDF doğrulama duvarı üzerinden bağımsız olarak
alınamadığından, bu incelemeden V8'e hiçbir sayısal sonuç, bölme, ablasyon ya da
sınırlama iddiası aktarılmamalıdır. Bir VAE gizli kümesi, bir Candidate yaşam
döngüsü durumu değildir ve nedensel ya da operasyonel bir mekanizmaya karşılık
gelmek zorunda değildir. Üretici bir gizli temsildeki belirsizlik, otomatik
olarak kalibre edilmiş olay-zamanı belirsizliği değildir.

**Güvenli aktarım.** Düşük öncelikli bir araştırma fikri dışında yok:
denetlenebilir bir durum grafiği ve basit tahmin ediciler var olduktan sonra,
yörünge kümelemesi tanımlayıcı sıkıştırma için test edilebilir. Durum grafiğini
tanımlayamaz ya da geçiş/olay kanıtının yerine geçemez.

### 29. *Advances in Temporal Point Processes: Bayesian, Neural, and LLM Approaches*

**Ne yapar.** Bu 2026 TMLR anketi; işaretsiz ve işaretli TPP'leri, koşullu
yoğunluk/yoğunluk parametreleştirmelerini, olabilirlik ve Bayes çıkarımını,
Hawkes/parametrik-olmayan/sinirsel/difüzyon/LLM ailelerini, benchmark'ları,
değerlendirmeyi, uygulamaları ve açık problemleri tanımlar
([arXiv:2501.14291](https://arxiv.org/abs/2501.14291)).

**Çekirdek biçimsel kanıt.** ([0,T]) penceresindeki sıralı olaylar için
(\mathcal T=((t_1,k_1),\ldots,(t_N,k_N))), işaretli bir koşullu yoğunluk
(\lambda^*(t,k\mid H_{t-})), sıkı geçmiş verildiğinde türe göre beklenen olay
sayılarını karakterize eder. Log-olabilirlik şudur:

\[
\sum_{n=1}^{N}\log\lambda^*(t_n,k_n)
-\int_0^T\sum_{k=1}^{K}\lambda^*(u,k)\,du.
\]

İkinci terim önemlidir: olay-olmayan maruziyet/gözlem penceresi olmadan yalnızca
olay satırlarında öğrenmek geçerli bir yoğunluk olabilirliği değildir. Bir
çok-değişkenli Hawkes süreci, yoğunluğu taban artı geçmiş-tetikli çekirdeklere
ayrıştırır, ama sıfırları model içindeki Granger nedensel-olmayışı tanımlar;
müdahale nedenselliğini değil.

**Anket kanıtı.** İnceleme; sonraki-olay zamanı/işareti tahminini, uzun-ufuk dizi
tahminini, getirme/akıl yürütme görevlerini ve nedensel-yapı keşfini ayırt eder.
Yalnızca olabilirlik yerine görev-hizalı metrikler önerir ve tutarsız
ön-işleme/bölme/metrikleri önemli bir alan sorunu olarak belgeler. Ayrıca
yorumlanabilirliği, uzun-dizi ölçeklemeyi, sürekli-zaman entegrasyonunu,
örnekleme verimliliğini ve çok-modlu hizalamayı çözülmemiş olarak tanımlar.

**Sınırlamalar.** Bu bir anket olduğu için, model-ailesi üstünlüğü hakkındaki
ifadeler tek bir kontrollü benchmark yerine heterojen çalışmaları özetler.
Esnek sinirsel yoğunluk nedensel bir açıklama değildir. Hawkes uyarımı, paylaşılan
gizli bir sürücüyü yansıtabilir. Olaylar üzerinde LLM-tabanlı getirme ya da akıl
yürütme, tutarlı bir stokastik olay-zamanı/işareti modeli tanımlamadıkça bir TPP
değildir. Anket, Candidate geçişlerinin bir TPP gerektirdiğini göstermez.

**Güvenli aktarım.** İşaretli bir TPP'yi yalnızca önceden bildirilmiş bir
eşzamanlı-olmayan tekrarlayan olay görevi için kullan; örneğin geçerli bir
geçmişten sonraki kabul edilebilir yaşam-döngüsü geçiş zamanını ve türünü
tahmin etmek. Ampirik/yenilenme/Poisson ya da basit Hawkes baseline'larıyla
başla. Tam gözlem pencerelerini, işaretleri, sıkı sıralamayı, eşzamanlı-olay
politikasını ve maruziyeti koru. Zaman-yeniden-ölçekleme ya da simülasyon-tabanlı
uyum-iyiliği teşhisleri uygula; Brown ve arkadaşları, doğru belirlenmiş koşullu
yoğunluğun olay zamanlarını birim-oranlı Poisson sürecine dönüştürdüğünü gösterir
([makale](https://sites.stat.columbia.edu/liam/teaching/neurostat-fall13/papers/brown-et-al/time-rescaling.pdf)).

## Candidate yaşam-döngüsü sözleşmesi: ne değişmeli ve ne değişmemeli

### Deterministik kontrol grafiğini koru, yanına istatistiksel görünümler ekle

Yaşam-döngüsü hizmeti, yasal geçişleri doğrulamaya ve yalnızca-eklenen olayları
replay etmeye devam etmelidir. İstatistiksel somutlaştırmalar türetilmiş
görünümler olmalı, değiştirme otoritesi değil. Tek bir günlük birçok tahmin
hedefini destekleyebilir:

| Görünüm | Köken/risk kümesi | Son nokta | Sansürleme/rakip nedenler | Birim |
|---|---|---|---|---|
| Kurulum tamamlanması | `DETECTED` | ilk `PENDING` | rakip olarak reddet; veri-sonu sansürlü | episode |
| Tetikleyici süreci | `PENDING` | ilk `TRIGGERED` | expiry/invalidation/reject ayrı rakip çıkışlar | episode veya landmark |
| Kabul süreci | `TRIGGERED` | `ACCEPTED` | reddetme/invalidation ayrı çıkışlar | episode |
| Gönderim gecikmesi | `ACCEPTED` | `ORDER_SUBMITTED` | geri çekme/reddetme/iptal-planı belirtilen çıkışlar | emir planı |
| İlk-dolum süreci | canlı gönderilmiş emir | ilk pozitif dolum | cancel-ack/expiry rakip olaylar veya bilgi-vermeyen sansür duyarlılığı | emir |
| Tamamlama süreci | ilk dolum veya gönderim | istenen miktarın tamamı doldu | iptal/yeniden-fiyatlama/kısmi kalan açıkça modellenir | emir revizyonu |
| Pozisyon kapanışı | ilk dolum/pozisyon açılışı | flat pozisyon | zorla/manuel/risk çıkışları işaret veya neden | pozisyon |
| Tekrarlayan expert olayları | gözlem penceresi | sonraki olay zamanı ve işareti | pencere sonu; feed kesintisi ayrı | enstrüman–expert akışı |

Tek bir `label_status` tüm bu görevleri kodlayamaz. `MATURE`, `RIGHT_CENSORED`
ve `UNAVAILABLE` etiket gözlemlenebilirliğini; `EXPIRED`, `INVALIDATED` ve
`REJECTED` yaşam-döngüsü nedenlerini; `NOT_EXECUTED` ise nedeni kullanılabilir
kalması gereken toplu bir olguyu tanımlar. Bunları ayrı eksenler olarak koru.

### Gerekli geçiş yükü

Her geçiş kaydı en az şunları taşımalıdır:

- değiştirilemez `candidate_id`, `transition_id`, `transition_sequence`, köken
  ve varış durumları;
- `event_type`, `cause_code`, `actor_type`, `actor_version` ve kanıt ref'leri;
- `event_time`, kesin zaman bilinmediğinde isteğe bağlı aralık sınırları,
  `available_time`, `ingested_time` ve `knowledge_time`;
- aktör kararları için `decision_time`, `state_entry_time`, `state_age`,
  `birth_time` ve `episode_age`;
- kaynak/saat hassasiyeti ve eşzamanlı-olay öncelik politikası;
- gözlem-penceresi ve feed-sağlığı durumu; böylece eksik bir geçiş sessizce
  sağkalım olarak yorumlanmaz;
- orijinal olayı yeniden yazmadan düzeltme/üstünlük bağlantısı.

Emir geçişleri için emir revizyonu, istenen/kümülatif/kalan miktar,
ilk/kısmi/tam-dolum ayrımları, mekan olay ID'si, borsa ve alma saatleri, iptal
isteği/onay saatleri ve açık kuyruk-verisi kaynağı ekle. Madde 22, kuyruk
bağlamının bir dolum modeline hükmedebileceğini gösterirken aynı anda
ayrıcalıklı kuyruk/katılımcı feature'larının mevcut varsayılmaması gerektiğini
gösterir ([arXiv:2512.05734](https://arxiv.org/abs/2512.05734)).

### Eşitlikler ve eşzamanlı olaylar

Bar çözünürlüğünde tetikleyici, hedef, stop, invalidation ve expiry aynı zaman
damgasında görünebilir. Bir rakip-risk veri satırı tek bir ilk neden gerektirir;
kanıt günlüğü tüm kaynak olgularını saklayabilir. Bu yüzden:

1. her kaynak olayını hassasiyetiyle sakla;
2. önceden bildirilmiş, sürümlenmiş bir önceliği yalnızca türetilmiş tahmin
   hedefinde uygula;
3. kaynak çözünürlüğü sırayı belirleyemediğinde sonucu `interval_ambiguous`
   olarak işaretle;
4. makul alternatif öncelik kuralları altında sonuçları yeniden çalıştır;
5. nedeni asla daha sonraki yoldan ya da istenen sonuçtan seçme.

Madde 20 ilgili uyarıyı sağlar: aralık-gözlemlenen geçişler, uydurulmuş kesin
zamanlar değil, bir geçiş-olasılığı olabilirliği ya da bildirilmiş bir yaklaşım
gerektirir ([arXiv:1703.08090](https://arxiv.org/abs/1703.08090)).

### Yeniden aktivasyon ve tekrar

Yeniden-aktivasyon-yok durum-makinesi kuralı, denetim kimliği için savunulabilir
ama bir sağkalım teoremi değildir. Yenilenen bir kurulum, `parent_candidate_id`/
küme ID'siyle bağlanan yeni bir episode yaratmalıdır. İstatistiksel analiz daha
sonra tekrarlayan ve bağımlı episode'ları tanımalıdır. Madde 21'in değişebilirlik/
müdahale-yokluğu koşulları genel olarak varsayılmamalı ve madde 26 ilk-olay
analizinin tekrarı göz ardı ettiğini açıkça not eder. Özne/enstrüman/olay-kümesi
gruplarını, episode eşzamanlılığını ve küme-farkında belirsizliği/bölmeleri
raporla.

## Veri kümesi ve olay-zamanı sözleşmesi

### Kurallı tablolar ve pazarlık konusu olmayan soyağacı

Kanıt deposu, tek bir geniş modelleme tablosu yerine farklı değiştirilemez
varlıklar açığa çıkarmalıdır:

1. yük hash'li ve tüm kaynak/kullanılabilirlik saatleriyle ham kaynak olayı;
2. maksimum girdi kullanılabilirliği ve derleme sürümüyle feature/MarketState
   değeri;
3. Candidate episode doğum kaydı;
4. Candidate geçiş olayı;
5. emir revizyonu/olayı ve dolum olayı;
6. gözlem-penceresi/feed-sağlığı kaydı;
7. köken, durum grafiği, son-nokta nedenleri, sansürleme kuralı, ufuk, varsa
   simülatör ve etiket kullanılabilirliğini belirten sonuç görünümü manifesti;
8. bölme, gruplar, ağırlıklar ve kod/veri hash'leriyle araştırma somutlaştırma
   manifesti.

Sonuç görünümü, bir olgunun o tahmin hedefi için olay, rakip neden ya da
sansürleme olup olmadığına karar verir; ham yaşam-döngüsü olayı değil. Bir
episode, "ufukta kapanışa kadar geçen süre" için sağdan sansürlü olabilirken
"pending'den ilk çıkış" için gözlemlenmiş bir rakip nedene sahip olabilir.

### Model-hazır birimler ayrı kalmalıdır

**Doğumdaki-episode satırları** doğum kanıtına koşullu soruları yanıtlar.
**Landmark satırları** bildirilmiş bir gözlem kesiminde dinamik soruları yanıtlar
ve episode başına çok sayıda bağımlı satır üretebilir. **Geçiş satırları** bir
köken durumuna ve durum-girişi/geçmiş kesimine koşullanır. **Emir satırları**
Candidate kalitesini değil, emir sonuçlarını modeller. **Olay-akışı pencereleri**
TPP'leri destekler ve sıfır-olay maruziyet aralıklarını içermelidir. Bu birimleri
açık ağırlıklar ve gruplar olmadan tek bir örnekte karıştırmak, hedef ve
bağımlılık belirsizliği yaratır.

Madde 25, landmark patlamasının (n(n+1)/2) satır yarattığını ve
örnekleme/ağırlıklar ile özne-içi bağımlılık kontrollerini zorunlu kıldığını
gösterir ([arXiv:2503.05023](https://arxiv.org/abs/2503.05023)). Madde 29, bir
TPP olabilirliğinin hem olay katkılarını hem de tam pencere üzerinde entegre
yoğunluğu gerektirdiğini gösterir ([arXiv:2501.14291](https://arxiv.org/abs/2501.14291)).

### Sansürleme ve gözlem politikası

Her sonuç görünümü şunları bildirmelidir:

- olay tanımı ve ilk/kısmi/tam olayın sayılıp sayılmadığı;
- zaman kökeni, giriş zamanı, ufuk ve zaman ölçeği;
- tüm rakip nedenler ve eşitlik politikası;
- sağdan-, aralık- ya da soldan-sansürleme temsili;
- sansürlemenin kovaryantlar verildiğinde bağımsız varsayıldığı koşullar;
- feed kesintisi/veri kümesi sonu/kullanıcı eylemi/emir iptali ayrımları;
- kovaryantların baseline, harici zamana-göre-değişen ya da iç post-köken
  değişkenler olup olmadığı;
- bilgi-vermeyen sansürleme için duyarlılık analizi.

Leung ve arkadaşları, sansürleme mekanizmalarının çoğu zaman bilinmediğini ve
yaygın yöntemlerin göz ardı edilebilirlik varsayımları gerektirdiğini vurgular
([inceleme](https://doi.org/10.1146/annurev.publhealth.18.1.83)). Bu yüzden
"sansürlü" nötr bir çöplük olamaz. Veri kaybı sıradan sağkalım değildir. İptal,
otomatik olarak bağımsız sansürleme değildir. Expiry, soruya bağlı olarak
deterministik bir idari ufuk ya da önemli bir rakip sonuç olabilir.

### Bölme sözleşmesi

Önce zamana göre böl, sonra feature/geçmiş ya da etiket aralığı kat sınırını
geçen herhangi bir satırı temizle ya da ambargoya al. Bildirildiği gibi tüm
tekrarlanan landmark'ları ve bağlantılı/tekrarlayan episode'ları grupla; örtüşme
ve eşzamanlılığı raporla. Ön-işlemeyi, pseudo-değerleri, sansürleme ağırlıklarını,
baselineları, eşikleri ve kalibrasyonu yalnızca eğitimde-kullanılabilir
etiketler üzerinde fit et. Bir etiket, yalnızca `label_available_time` anında
eğitime katılır; asla sırf olay zamanı geçmişte diye değil.

FinSurvival'ın zamansal bölmesi ve tamponları yararlı bir başlangıç örneğidir,
ama ikili görevleri ve yüksek sansürlemesi tüm bu korumaları göstermez
([arXiv:2507.14160](https://arxiv.org/abs/2507.14160)). TPP anketi de tutarsız
ön-işleme ve bölmeleri, yayınlanan karşılaştırmaların birikememesinin önemli bir
nedeni olarak tanımlar ([arXiv:2501.14291](https://arxiv.org/abs/2501.14291)).

## Görünür kalması gereken çelişkiler ve gerilimler

1. **İkili sağkalım versus ortak rakip riskler.** FinSurvival, 16 bağımsız
   index–sonuç görevi bildirir ve rakip riskleri açıkça atlar; *Risk to Rescue*
   çok-olaylı risk karşılaştırmalarını tanımlar. V8, bağımsız kalibre edilmiş
   olay-çifti dönüş periyotlarını karşılaştırmanın tutarlı olay olasılıkları
   verdiğini çıkarım etmemelidir.

2. **Sansürleme versus olay nedeni.** KANFormer, koşullu bağımsızlık altında
   iptali ve piyasa kapanışını sansürleme olarak ele alır. İçsel bir iptal
   politikası için iptal, dolumla-ilgili geçmiş tarafından sürülür ve bilgi-verici
   ya da rakip bir olay olabilir. Her iki kodlama da duyarlılık testine tabi
   tutulmalıdır.

3. **Birinci-derece Markov kolaylığı versus süre bağımlılığı.** Madde 20,
   aralık gözlemleri için birinci-derece Markov olabilirliği kullanır; madde 23,
   üstel-olmayan beklemelerin neden yarı-Markov yapısı gerektirdiğini açıklar.
   İkisi de sessizce varsayılmamalıdır. Karşılaştırma için `state_age` mevcut
   olmalıdır.

4. **"Varsayımdan-bağımsız" sinirsel esneklik versus gözlem varsayımları.**
   Maddeler 17 ve 19 parametrik işlevsel formları gevşetir ama yine de
   sansürleme, durum, zaman, mimari ve örnekleme varsayımlarına bağlıdır. Esnek
   yaklaşımcılar tanımlama gereksinimlerini kaldırmaz.

5. **Sıradan Aalen–Johansen verimliliği versus landmark sağlamlığı.** Madde 24,
   AJ ya da landmark AJ seçmek için veriye-bağımlı bir Markov testi kullanır.
   Tahminci seçim belirsizliği ve düşük-güçlü testler pseudo-hedefleri
   etkileyebilir; yalnızca seçilen sonucu değil, ikisini de karşılaştır.

6. **Değişebilirlik versus piyasa bağımlılığı.** Madde 21'in yeniden-etiketleme
   ve alt-örnekleme tutarlılık varsayımları matematiksel olarak yararlıdır ama
   candidate'lar bir piyasa şokunu, enstrümanı, Expert'i, sermaye kısıtını ya da
   tekilleştirme kuralını paylaştığında başarısız olabilir.

7. **Tahminî dolum kanıtı versus çalıştırılabilir kullanılabilirlik.** Madde
   22'nin en yararlı girdileri, makalenin tek bir aktörün gözlemleyemeyeceğini
   söylediği kuyruk pozisyonu ve katılımcı-düzeyi davranışı içerir. Bildirilen
   saniye-altı kalibrasyonu, V8 pasif-dolum iddialarına yetki vermez.

8. **Gizli kümeler versus operasyonel durumlar.** Madde 27'nin VAE kümeleri
   tanımlayıcı yörünge grupları olabilir; yasal Candidate durumlarını ya da
   geçiş otoritesini tanımlayamazlar.

9. **TPP Granger yapısı versus nedensel mekanizma.** Çok-değişkenli bir Hawkes
   modelinde sıfır tetikleyici çekirdeğin model altında bir Granger yorumu
   vardır. Sıfır-olmayan bir çekirdek, göz ardı edilmiş ortak nedenlerden ya da
   durağan-olmayıştan doğabilir; bir müdahale etkisi değildir.

10. **Sıralama versus kalibrasyon versus fayda.** C-index/AUC ayrımcılığı ölçer;
    Brier/log-olabilirlik sansürleme varsayımları altında dağılımsal doğruluğu
    ele alır; ikisi tek başına yararlı bir karar politikası kurmaz. İkisini de
    raporla ve göreve-özgü operasyonel hata ekle; ekonomik iddialara
    çevirmeden.

## Karmaşık modellemeden önce sıralanan ucuz yanlışlama deneyleri

### Sözleşme ve veri yanlışlayıcıları

1. **Saat tersine çevirme denetimi.** Her feature ve geçiş için, semantik olarak
   gerekli olduğu yerde `event_time <= available_time <= knowledge_time <=
   decision_time` olduğunu iddia et; gecikmiş düzeltmeler gibi açık istisnaları
   zorlamak yerine kaydet. Rastgele feed gecikmeleri enjekte ettikten sonra bir
   örneklemi yeniden inşa et ve yeni kullanılabilirlikten önce hiçbir karar
   görünümünün değişmediğini doğrula.

2. **Replay determinizmi.** Alım sırasını karıştır, bildirilen `(knowledge_time,
   transition_sequence)` kuralıyla replay et ve özdeş yaşam-döngüsü
   projeksiyonlarını/hash'lerini iddia et. Sonra bir düzeltme enjekte et ve
   mutasyon yerine yalnızca-eklenen üstünlüğü gerektir.

3. **Aralık-zamanı yanlışlayıcısı.** Kesin geçiş zamanlarını barlara kabalaştır
   ve (a) uydurulmuş bar-kapanış zamanlarını, (b) aralık-sansürlü olabilirliği ve
   (c) iyimser/kötümser eşitlik önceliğini karşılaştır. Sonuç maddi olarak
   hareket ederse, kesin-zaman iddiaları desteklenmez.

4. **Eksik-feed yanlışlayıcısı.** Sürekli bir ham-veri penceresini sil. Sonuçlar
   "hayatta kaldı", `EXPIRED` ya da olumsuz değil, politikaya göre
   `UNAVAILABLE`/aralık-sansürlü olmalıdır.

5. **Nüfus-birimi denetimi.** Doğumda bir episode'u, tüm landmark satırlarını,
   tüm geçişleri ve tüm emirleri ayrı ayrı say. Tekrarlanan satırların
   episode/enstrüman/olay-kümesi gruplarını ve ağırlıklarını koruduğunu doğrula.

### Sağkalım ve rakip-risk yanlışlayıcıları

6. **İkili-versus-rakip-risk sağlık kontrolü.** Aynı `PENDING` kohortunda,
   alternatif çıkışları sansürleyen ayrı Kaplan–Meier eğrilerini bir
   Aalen–Johansen kümülatif-insidans tahminiyle karşılaştır. Büyük farklar,
   bağımsız ikili görevlerin yaşam döngüsüne yaklaştığı iddiasını yanlışlar.
   Bakımı yapılan sağkalım öğreticisi baseline tahminciyi sağlar
   ([CRAN](https://stat.ethz.ch/CRAN/web/packages/survivalVignettes/vignettes/tutorial.html)).

7. **Olay/sansür yeniden-kodlama duyarlılığı.** Emir dolumları için en az üç
   sürüm çalıştır: iptal-sansürleme, iptal-rakip-neden ve gözlemlenebilir
   geçmişten ters-olasılık-sansürleme ağırlıklandırması. Dolum eğrileri ya da
   kalibrasyon maddi olarak hareket ederse, bağımsız sansürleme sağlam değildir.

8. **Saat-ileri versus saat-sıfırlama.** Aynı basit geçiş modelini episode yaşı,
   durum yaşı ve ikisiyle birlikte fit et. Durum-yaşı terimleri tutulan Brier/log
   skorunu maddi olarak iyileştirirse ya da kalan süre yapısını kaldırırsa,
   yalnızca-durumlu Markov modeli yanlışlanır. Madde 23'ün parametre ayrımını
   kullan ([arXiv:2005.14462](https://arxiv.org/abs/2005.14462)).

9. **Markov yeterlilik kontrolü.** Köken-durum/landmark katmanları içinde, basit
   bir modele önceki durum, önceki bekleme süresi, geçiş sayısı ya da kompakt
   geçmiş feature'ları ekle. Tutulan iyileştirme ya da sistematik kalıntı
   farkları, gözlenen-durum Markov yeterliliği iddiasını reddeder. Tek bir
   düşük-güçlü ön teste güvenmek yerine sıradan AJ ile landmark AJ'yi karşılaştır.

10. **Orantılı-tehlike kontrolü.** Zamana-göre-değişen etkileri çiz/test et ve
    Cox'u kesikli-zamanlı ya da spline-tehlike baseline ile karşılaştır. Etki
    işaretleri ya da kalibrasyon ufka göre değişiyorsa, tek bir tehlike oranıyla
    özetleme.

11. **Ufuk duyarlılığı.** Birkaç savunulabilir ufku önceden bildir, her birinde
    risk-kümesi sayılarını ve kalibrasyonu raporla ve sonuç-sonrası ufuk
    seçimini engelle. Yalnızca seçilmiş bir ufukta "kazanan" bir model, genel bir
    yaşam-döngüsü iddiasında başarısız olur.

12. **Tam-yaşam-döngüsü versus yalnızca-executed ablasyonu.** Model ailesini,
    feature'ları, bölmeyi ve olgun karşı-olgusal etiket politikasını sabitle.
    Eğitimi tüm uygun candidate'lar (uygun nedenler/sansürlemeyle) üzerinde,
    yalnızca-executed satırlara karşı karşılaştır. Kalibrasyonu ve atfı aynı
    sabit prospektif kohortta değerlendir. Bu, tam yaşam döngüsünün istatistiksel
    değer katıp katmadığını doğrudan test eder; yanıtı varsaymaz.

13. **Tekrarlayan/bağımlılık yanlışlayıcısı.** Saf belirsizliği, enstrüman/olay
    kümesi/ebeveyn episode ile küme bootstrap ya da gruplu katlarla karşılaştır.
    Maddi bir genişleme ya da sıra tersine dönmesi IID raporlamayı yanlışlar.

### Dolum ve TPP yanlışlayıcıları

14. **Yalnızca-gözlemlenebilir dolum ablasyonu.** Yalnızca gerçekten kullanılabilir
    emir/defter alanlarını kullanarak basit bir Cox/Weibull/kesikli-tehlike
    baseline'ını yeniden üret; sonra kuyruk ve katılımcı-geneli feature'ları ayrı
    ekle. Kazançlar yalnızca ayrıcalıklı alanlarla varsa, dağıtılabilir dolum
    iddiası başarısız olur. İlk kısmi ve tam dolumu farklı son noktalar olarak
    tut.

15. **TPP gereklilik testi.** Ampirik işaret frekansları artı bir yenilenme ya da
    homojen-olmayan Poisson baseline'ını, tam olarak aynı pencerelerde basit bir
    Hawkes/TPP ile karşılaştır. Tutulan olabilirlik *ve* görev-hizalı zaman/işaret
    kalibrasyonunda iyileşme gerektir. Statik ya da yenilenme baseline'ı
    eşleştiriyorsa, ekstra TPP karmaşıklığını reddet.

16. **Olay-yok maruziyet testi.** Kasıtlı olarak yanlış bir yalnızca-olay-satırı
    sınıflandırıcısı ve entegre maruziyetli uygun bir yoğunluk olabilirliği
    eğit. İlki sayı/pencere kalibrasyonunda başarısız olmalıdır. Bu, sonraki-satır
    sınıflandırmasını nokta-süreci modeli olarak adlandırmanın yaygın hatasını
    yakalar.

17. **Zaman-yeniden-ölçekleme teşhisi.** Tutulan olay zamanlarını uydurulmuş
    kümülatif koşullu yoğunluk üzerinden dönüştür. Üstel varışlar-arası süreleri
    ve tekdüze dönüştürülmüş CDF değerlerini test et; otokorelasyonu incele.
    Başarısızlık, sonraki-olay MAE'si iyi olsa bile iddia edilen koşullu
    yoğunluğu yanlışlar ([Brown et al.](https://sites.stat.columbia.edu/liam/teaching/neurostat-fall13/papers/brown-et-al/time-rescaling.pdf)).

18. **Eşzamanlı-işaret duyarlılığı.** Kaynak zaman damgası çözünürlüğünde,
    deterministik işaret önceliğini, bileşik işaretleri ve küçük jitter'ı yalnızca
    teşhis olarak karşılaştır. Maddi istikrarsızlık, seçilen sürekli-zaman TPP
    temsilinin veri tarafından tanımlanmadığı anlamına gelir.

19. **Geçmiş kırpma ablasyonu.** Son-olay, sınırlı-pencere ve daha-uzun-geçmiş
    girdilerini karşılaştır. Görünür uyarım, takvim/rejim kovaryantları
    eklendikten sonra kayboluyorsa, orijinal Hawkes çekirdeğini mekanizma olarak
    yorumlama.

20. **Karşı-olgusal/gözlenen ayrım testi.** Ham geçmişi sabit tutarken simülatör
    config/hash'ini değiştir. Yalnızca karşı-olgusal sonuç kayıtları değişebilir;
    gözlenen dolumlar ve geçişler bayt-bayt aynı kalmalıdır. Bu, madde 16'daki
    müdahale-simülatörü örüntüsünün gözlenen gerçeği üzerine yazmasını önler.

## V8 için karar çıkarımları

Savunulabilir yakın-vadeli karar muhafazakârdır:

- `Candidate != order != fill != outcome`'u bir denetim değişmezi olarak koru;
- execute edilmemiş terminal nedenler dahil her yasal yaşam-döngüsü geçişini
  sakla;
- tek bir evrensel kalite etiketi yerine ayrı, sürümlenmiş sonuç görünümleri
  tanımla;
- her sağkalım hedefi için açık köken durumu, son nokta, neden, saat, ufuk,
  gözlem penceresi ve sansürleme kuralı gerektir;
- yarı-Markov ya da çok-durumlu modelleri test etmeden önce
  `state_entry_time/state_age` ve aralık-zaman desteği ekle;
- sinirsel çok-durumlu ya da TPP modellerinden önce Aalen–Johansen, basit
  nedene-özgü/kesikli tehlikeler ve yenilenme/Poisson baselinelarını kullan;
- iptalleri, expiry'leri, feed kesintilerini ve idari arşivlemeyi farklı olgular
  olarak ele al;
- karşı-olgusal simülatör sonuçlarını ayrı bir sonuç otoritesinde tut;
- TPP çalışmasına yalnızca tam maruziyet pencereleri ve uyum-iyiliği
  teşhisleriyle bildirilmiş bir tekrarlayan eşzamanlı-olmayan olay görevi için
  izin ver;
- her ekonomik sonucu **OPEN** olarak sakla. 16–29. makalelerin hiçbiri V8
  getirilerini, maliyetlerini, dolumlarını, kapasitesini ya da sağlamlığını
  sertifikalandırmaz.

Literatürün en güçlü katkısı, sinirsel bir sağkalım modeli ekleme tavsiyesi
değildir. Bir spesifikasyon disiplinidir: herhangi bir şeyi fit etmeden önce
risk kümesine, durum grafiğine, zaman kökenine, olay nedenine, sansürleme
mekanizmasına, gözlem sürecine ve saat semantiğine karar ver. Bunlar belirsizse,
daha büyük model kapasitesi belirsizliği denetlenmesi daha zor hale getirir.
