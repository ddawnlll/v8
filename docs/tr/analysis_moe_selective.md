# Mixture-of-Experts, Routing ve Selective Prediction: V8 için Kanıt İncelemesi

## Kapsam, kaynak denetimi ve kanıt standardı

Bu not, kullanıcının sağladığı okuma listesindeki 1–15. maddeleri kapsar: mixture-of-experts (MoE), routing ve koşullu hesaplama üzerine sekiz listede yer alan girdi ve selective prediction, reject option ve kalibrasyon üzerine yedi girdi. 6. madde ayrı bir makale değildir: 2. maddenin, arXiv:2507.11181'in HTML görünümüdür. Atanan set bu nedenle **15 liste girdisi ama 14 benzersiz makale** içerir. 14 benzersiz PDF'nin tamamı erişilebilirdi ve indirildi; atanan hiçbir kaynak erişilemez değildir. Kesin arXiv metadata'sı ayrıca 2026-07-31 tarihinde arXiv API'sinden alındı.

İnceleme üç kanıt sınıfını ayırt eder:

- **Doğrudan ampirik kanıt:** makalenin kendisinin raporladığı, değerlendirilmiş bir model, veri kümesi, karşılaştırma veya ablasyon.
- **Doğrudan kuramsal kanıt:** açık varsayımlar altında bir teorem. İdealleştirilmiş bir sınıflandırma dağılımı hakkındaki bir teorem, piyasalar için ampirik kanıt olarak ele alınmaz.
- **İkincil sentez:** diğer makaleleri aktaran bir survey veya eğitici yazının anlatımı. Bu, taksonomi ve hata modu keşfi için yararlıdır, ancak bağımsız ve başarılı bir deney eklemez.

Aşağıdaki V8 sonuçları bilinçli olarak dardır. Bu makalelerin hiçbiri V8'i test etmez, bir Router'ın trading edge yarattığını kanıtlamaz, Expert'lerin ekonomik mekanizmayla uzmanlaştığını kanıtlamaz ya da bir `NO_TRADE` kuralının maliyet sonrası portföy faydasını iyileştirdiğini ortaya koymaz. Dil/görüntü sınıflandırmasından trading'e aktarımlar, V8'e özgü deneyler gerektiren tasarım çıkarımları (design inferences) olarak işaretlenir.

## V8 için yönetici bulguları

1. **Literatür, koşullu hesaplamayı bir V8 Router'ı olarak değil, bir tasarım ailesi olarak destekler.** MoE, bir modül alt kümesini etkinleştirirken parametre kapasitesini genişletebilir; ancak fayda, heterojen yapıya, routing kalitesine, eğitim dinamiklerine ve sistem kısıtlarına bağlıdır. V8'in planladığı iki veya üç ucuz deterministik Expert için, bu Expert'ler çalıştırılmadan önce öğrenilmiş bir Router'ı haklı çıkaracak gösterilmiş bir hesaplama darboğazı yoktur.

2. **Routing, anlamsal uzmanlaşma ile eşanlamlı değildir.** Bu setteki en güçlü karşı örnek Mixtral'dir: expert ataması ArXiv, GitHub, PubMed, felsefe ve Wikipedia genelinde çok az konu düzeyi farklılaşması gösterdi; daha çok sözdizimsel ve ardışık konum yerelliği gösterdi. Daha sonraki dört modelli analiz de MoE LLM'lerinin heterojen expert'ler öğrendiğini söylemenin erken olduğu sonucuna varır. V8 uzmanlaşmayı router entropisi, dengeli yükler, expert ID'leri veya çekici görsel kümelerle değil, karşı olgusal (counterfactual) ekonomik davranışla ölçmelidir.

3. **Uzmanlaşma için kuramsal gerekçe koşulludur, evrensel değildir.** Chen ve arkadaşları, veri belirli bir küme yapısı içerdiğinde, doğrusal olmayan CNN Expert'leri kümeye özgü sinyalleri öğrenebildiğinde ve belirtilen bir optimizasyon prosedürü kullanıldığında uzmanlaşmayı kanıtlar ve gösterir. Sıradan CIFAR-10'da MoE tek modelleri geçemedi; güçlü küme yapısına sahip kurgulanmış bir döndürme görevinde geçti. Bu, V8'in Expert ayrıştırmasını eşit bilgili küresel bir baseline'a karşı test etme yönündeki mevcut gereksinimini doğrudan destekler.

4. **Yük dengesi bir sistem hedefidir, yararlı uzmanlığın kanıtı değildir.** Dengeleme, çöküşü ve donanım darboğazlarını önleyebilir, ancak doğal görev/uzman hizalamasına da karşı çalışabilir. Küçük bir V8 Expert setiyle, bağlayıcı bir kapasite kısıtı önce gösterilmedikçe tekdüze seçimi zorlamak haksız olur.

5. **`NO_TRADE`, açık bir hedefe sahip seçici (selective) bir karar olarak biçimselleştirilmelidir.** Maliyet temelli red, tavan risk altında azami kapsama ve taban kapsama altında minimum risk, idealleştirilmiş kuramda Bayes-optimal bir sıralamayı paylaşır, ancak farklı işletme seçimlerini kodlar. V8, "eşiğin üzerindeki güven"i kendiliğinden meşrulaştırıcı görmek yerine, yanlış bir trade'in ekonomik kaybını, çekimserliğin fırsat maliyetini ya da hedef kapsama/risk kısıtını önceden beyan etmelidir.

6. **Sabit kapsamalı bir kapı için sıralama kalitesi olasılık kalibrasyonundan daha önemlidir, ancak garantiler için kalibrasyon yine de önemlidir.** Franc ve arkadaşları, uygun bir belirsizlik skorunun yalnızca koşullu risk sıralamasını koruması gerektiğini, optimal bir seçici (selector) kurmak için bunun yeterli olduğunu gösterir. Feng ve arkadaşları, sınıflandırıcının kendi maksimum softmax skorunun görüntü görevlerinde ayrı seçim başlıklarından daha iyi performans gösterdiğini bulur. Yine de Franc ve arkadaşları, öğrenilmiş kayıp sıralama skorlarının, özellikle SVM'ler için, doğal marjlardan veya maksimum sınıf olasılığından daha iyi olabileceğini gösterir. V8 bu nedenle "doğal skor" ile "öğrenilmiş Scorer" arasında doktrinel bir seçim değil, eşleştirilmiş bir karşılaştırma gerektirir.

7. **Conformal garantiler piyasa kayması altında otomatik olarak elde edilemez.** Conformal makalesi, değişebilirlik (exchangeability) varsayımı altında singleton hata garantileri türetir ve çevrimiçi ile çevrimdışı indüktif ortamları dikkatle ayırt eder. Seri bağımlılık, uyarlanabilir yeniden eğitim, durağan olmama, varlık seçimi ve işlem maliyeti etiketleri bu varsayımları ihlal edebilir veya karmaşıklaştırabilir. Herhangi bir V8 conformal katmanı, kesin değişebilirlik ya da ağırlıklı/blok-conformal argümanını belirtmelidir; aksi halde dağılımdan bağımsız bir garanti değil, bir teşhistir.

8. **İki zaman serisi makalesi farklı sorulara yanıt verir.** Inácio ve arkadaşları, tahmin zorluğunun ex-ante bir sıralamasını öğrenir ve bunu dağıtım anı reddi için kullanır. Fu ve arkadaşları, aşırı uyumu azaltmak için model eğitimi sırasında belirsiz/aykırı zaman adımlarını maskeler; bu canlı bir çekimserlik mekanizması değildir. Fu ve arkadaşları, maskelemenin aşırı olay tahminini tehlikeye atabileceği konusunda açıkça uyarır; bu, finansal sistemler için maddi bir risktir.

9. **Mevcut V8 baseline kararları savunulabilir durumdadır ve bu incelemeyle güçlenmiştir.** Küçük deterministik öz-gating Expert setini çalıştırın, her değerlendirmeyi ve Candidate'ı kaydedin ve Router ile öğrenilmiş Scorer'ı erteleyin. Yalnızca neredeyse mükemmel değerli-Candidate geri çağırma oranını korurken bağlayıcı bir operasyonel kazanç üretiyorsa bir Router kabul edin. Bir Scorer veya `NO_TRADE` kapısını yalnızca eşleşen kapsamada ve yalnızca tekrarlanan kronolojik OOS maliyet sonrası fayda, kalibrasyon ve istikrar kanıtı üzerinde kabul edin.

## Makale makale analiz

### 1. Mu ve Lin — kapsamlı MoE survey (arXiv:2503.07137)

**Kaynak ve kanıt türü.** Siyuan Mu ve Sen Lin, *A Comprehensive Survey of Mixture-of-Experts: Algorithms, Theory, and Applications* (ilk yayın 2025; incelenen sürüm v4, tarih 2026). [arXiv özeti](https://arxiv.org/abs/2503.07137). Bu geniş kapsamlı bir survey'dir, yeni bir routing deneyi değildir.

**Makalenin katkısı.** Makale MoE'yi gating fonksiyonları, Expert ağları, routing, eğitim stratejisi ve sistem tasarımı etrafında düzenler, ardından sürekli, meta, çok görevli, pekiştirmeli ve federasyonlu öğrenme uygulamalarını inceler. Mimari kapasiteyi seyrek aktivasyondan yararlı biçimde ayırır ve yinelenen sorunları kataloglar: kararsız eğitim, expert yükü dengesizliği, olası çöküş, iletişim ve bellek yükü, sezgisel Expert-sayısı seçimleri ve modern derin MoE routing için zayıf kuram.

**V8 ile ilgili kanıt.** Survey, `Router`, `Expert`, eğitim ve sistem zamanlamasını ayrı tasarım sorunları olarak ele alma görüşünü destekler. Ayrıca birkaç Expert'e aşırı güvenin izlenmesini ve dinamik kapasitenin olası bir deney olarak ele alınmasını destekler. En önemlisi, gelecek çalışma bölümü Expert sayısını, uzmanlaşma derecesini veya routing politikasını çözülmüş seçimler olarak resmetmez. Uyarlanabilir yük dengeleme, dinamik kapasite, ilkeli Expert-sayısı seçimi ve daha güçlü yorumlanabilirlik/kuram çağrısı yapar.

**Sınırlamalar ve aktarım dışı durumlar.** Makale ağırlıklı olarak ikincil bir katalogdur ve bir okuyucunun yayın seçimi yanlılığını tahmin etmesine olanak verecek sistematik bir inceleme arama protokolü tanımlamaz. Örneklerine, Expert-paralel iletişim ve parametre etkinleştirmenin birincil kısıtlar olduğu büyük sinir modelleri hâkimdir. V8'in ilk Expert'leri birbirinin yerine geçebilen FFN blokları değil, küçük çalıştırılabilir hipotezlerdir; survey, öğrenilmiş bir V8 Router'ını veya belirli bir top-k kuralını haklı çıkaramaz. MoE'nin verimlilik/performansı artırdığına dair geniş ifadeleri, alıntılanan çalışmaların koşullarını ve baseline'larını devralır.

**V8 kullanımı.** Taksonomi ve risk kontrol listesi olarak kullanın. V8'in MoE uygulaması gerektirdiğine dair bağımsız kanıt olarak saymayın. Expert başına yük, örtüşme, routing istikrarı, yönlendirilememe (failure-to-route) ve hesaplama/gecikme kaydını destekler, ancak V8 ölçülebilir bir kısıt var olana kadar dengeleme kaybı veya dinamik kapasite eklememelidir.

### 2. Zhang ve arkadaşları — LLM'lerde MoE incelemesi (arXiv:2507.11181)

**Kaynak ve kanıt türü.** Danyang Zhang, Junhao Song, Ziqian Bi, Xinyuan Song, Yingfang Yuan, Tianyang Wang, Joe Yeong ve Junfeng Hao, *Mixture of Experts in Large Language Models* (2025). [arXiv özeti](https://arxiv.org/abs/2507.11181). Survey/inceleme.

**Makalenin katkısı.** Seyrek gating, hiyerarşik MoE, expert routing, çok modlu/çok görevli kullanım, dağıtım, kalibrasyon ve toplamayı inceler. Model kapasitesinin etkin çıkarım parametrelerinden ayrıştırılabileceğini vurgular, ancak expert çeşitliliği, güvenilir kalibrasyon, istikrarlı routing ve çıkarım toplamasını çözülmemiş pratik gereksinimler olarak da tanımlar. İnceleme; düzensiz bellek erişimi, cihazlar arası iletişim, toplu işleme kararsızlığı, donanımın yetersiz kullanımı ve ham etkin parametre sayılarının yakalamadığı yeniden üretilebilirlik maliyetlerini tartışır.

**V8 ile ilgili kanıt.** V8 için yararlı ders mimari ayrışmadır: bir gating mekanizması hesaplamadan tasarruf edebilir, ancak kötü atamalar yoluyla model kalitesini hâlâ düşürebilir ve seyrek etkinleştirme kendi operasyonel durumunu yaratır. Bu nedenle bir Router, hem dışlama kalitesi hem de operasyonel fayda üzerinden değerlendirilmelidir. Makalenin kalibrasyon ve toplama vurgusu, router skorlarını ayrı bir kalibrasyon testi olmadan Candidate-kalitesi olasılıkları olarak yorumlamaya karşı da argüman oluşturur.

**Sınırlamalar ve aktarım dışı durumlar.** Bu makale LLM çalışmalarını sentezler ve V8 benzeri hiçbir ekonomik değerlendirme sunmaz. Parametre sayısı ve token routing, raporlanan LLM faydalarını koruyacak biçimde maliyet sonrası trade seçimine benzetilemez. Eğitim verileri, routing ayrıntıları veya model tarifleri kamuya açık olmadığından, iddia edilen endüstriyel örneklerin bazılarını denetlemek zordur. İnceleme, bu sistemlerin bağımsız bir tekrarı değildir.

**V8 kullanımı.** Router skorunu, Expert çıktısını, Candidate kanıtını ve Scorer çıktısını ayrı kaydedilen alanlar olarak tutun. Öğrenilmiş bir kapı sessizce ekonomik kalite skoruna dönüşmemelidir.

### 3. Chen ve arkadaşları — MoE uzmanlaşmasının kuramı (arXiv:2208.02813)

**Kaynak ve kanıt türü.** Zixiang Chen, Yihe Deng, Yue Wu, Quanquan Gu ve Yuanzhi Li, *Towards Understanding Mixture of Experts in Deep Learning* (2022). [arXiv özeti](https://arxiv.org/abs/2208.02813). Doğrudan kuram artı sentetik, görüntü ve dil deneyleri.

**Yöntem ve doğrudan kanıt.** Makale, küme-merkezli yamalar, kümeye özgü etiket-sinyali yamaları, öznitelik-gürültüsü yamaları ve Gaussian gürültü içeren bir ikili sınıflandırma dağılımı kurar. Bu dağılım altında:

- Teorem 4.1 negatif bir sonuç verir: öznitelik sinyali ve öznitelik gürültüsü aynı güç dağılımına sahipken, etkinleştirme fonksiyonu veya genişliği ne olursa olsun tek bir iki katmanlı CNN, %87,5 test doğruluğunu aşamaz.
- Teorem 4.2, ayrıntılı örneklem büyüklüğü, başlatma, genişlik, öğrenme oranı ve optimizasyon koşulları altında, seyrek gating'li doğrusal olmayan bir MoE'nin %100 doğruluğa yaklaşabileceğini gösterir. Kanıt, Expert'lerin başlatmaya göre uzmanlaştığı bir keşif aşamasını, ardından küme-merkezli özniteliklerin gözlemleri ilgili Expert grubuna yönlendirdiği bir router-öğrenme aşamasını anlatır.
- Başlıca sentetik ortamlarda, doğrusal olmayan MoE, sevkiyat entropisi sıfıra yakınken %99,46 ± 0,55 ve %98,09 ± 1,27 doğruluk elde etti; doğrusal MoE, çok daha yüksek sevkiyat entropisiyle %92,99 ± 2,11 ve %88,48 ± 1,96 elde etti. Tek doğrusal olmayan modeller %79,48 ve %72,29 elde etti.
- Standart CIFAR-10'da MoE ve tek model doğruluğu esasen eşitti veya MoE hafifçe daha kötüydü: örneğin ResNet18 %95,51 ± 0,31'e karşılık MoE %95,32 ± 0,68. Görevin daha güçlü bir gizli küme yapısına sahip olduğu kurgulanmış CIFAR-10-Rotate'te MoE, ResNet18'i %88,23 ± 0,96'dan %92,60 ± 2,01'e yükseltti ve daha küçük omurga ağlarını da benzer şekilde iyileştirdi.
- Çok dilli bir duygu analizi deneyi doğruluğu yalnızca mütevazı biçimde, %74,13'ten %76,22'ye iyileştirirken, router örnekleri büyük ölçüde dile göre ayırdı.

**Yorum.** Bu makale, MoE avantajının sömürülebilir heterojenliğe ve uygun Expert doğrusalsızlığına bağlı olduğuna dair setteki en açık kanıtı sağlar. Ayrıca temsil kapasitesinin tek başına yetersiz olduğunu gösterir: doğrusal Expert'lerin bir karışımı sentetik hedefi temsil edebilirdi, ancak eğitim sırasında amaçlanan kümeleri aynı etkinlikle geri kazanamadı.

**Sınırlamalar.** Teorem, oldukça yapılandırılmış ortogonal bir yama modeline, iki katmanlı CNN Expert'lerine, normalize edilmiş gradyan inişine, belirli routing gürültüsüne/erken durmaya ve asimptotik parametre koşullarına uygulanır. MoE'nin gerçek ekonomik rejimleri keşfettiğine dair genel bir teorem değildir. Gerçek veri deneyleri, çağdaş LLM'lere kıyasla küçüktür ve döndürme görevi, kümeleme içerecek biçimde bilinçli olarak tasarlanmıştır. Sıfıra yakın sevkiyat entropisi yoğunlaşmış atamayı gösterir, ekonomik doğruluğu değil. Hiçbir işlem maliyeti, zamansal bağımlılık, dağılım kayması veya seçici trading kararı çalışılmamıştır.

**V8 kullanımı.** "Expert'ler küresel modeli yener" ifadesini ampirik bir hipotez olarak ele alın. Bir Router öğrenmeden önce, önerilen davranış habitat'larının karar zamanı değişkenleriyle ayrıştırılabilir olup olmadığını ve her Expert'in artımsal koşullu faydaya sahip olup olmadığını test edin. Bir Expert-değişimi (Expert-swap) testi ekleyin: Router tarafından atanan alt kümede, atanan Expert'i diğer her Expert'le ve küresel baseline ile karşılaştırın. Bu karşı olgusal avantaj olmadan düşük entropili bir routing dağılımı uzmanlaşmayı ortaya koyamaz.

### 4. Lo ve arkadaşları — dört MoE LLM'inin sonradan analizi (arXiv:2406.18219)

**Kaynak ve kanıt türü.** Ka Man Lo, Zeyu Huang, Zihan Qiu, Zili Wang ve Jie Fu, *A Closer Look into Mixture-of-Experts in Large Language Models* (ilk yayın 2024; v3 2025). [arXiv özeti](https://arxiv.org/abs/2406.18219). Doğrudan gözlemsel analiz artı sınırlı bir mimari deneyi.

**Yöntem ve doğrudan kanıt.** Yazarlar Mixtral 8x7B, Mixtral 8x22B, DeepSeekMoE ve Grok-1'i parametre kosinüs benzerliği, çıktı benzerliği/normları, gate embedding'leri ve katman konumu kullanarak analiz eder. Şunları raporlarlar:

- gate embedding'leri ile Expert etkinleştirme matrisleri arasındaki korelasyonlar; bu, bireysel FFN nöronlarını daha ince taneli Expert'ler olarak görmeyi motive eder;
- Mixtral ve DeepSeekMoE'de gate seçimlerinin genellikle daha büyük çıktı normlarına sahip Expert'leri kayırdığı;
- Expert parametre/çıktı benzerliğinin genellikle daha derin katmanlarda azaldığı, ardından son katmanda arttığı;
- Mixtral Expert'lerinin, sıfırdan eğitilen DeepSeek/Grok Expert'lerinden birbirine daha çok benzediği; bu, Mixtral'in upcycling benzeri bir başlatma kullanmış olabileceğine dair belirtilmiş bir varsayıma — gösterilmiş bir olguya değil — yol açar;
- yaklaşık 120B token üzerinde eğitilen altı adet 24 katmanlı, 3,6B parametreli model; bir MoE katmanını yoğun bir katmanla değiştirmek, değiştirme daha sonraki bir katmanda gerçekleştiğinde genellikle daha çok zarar verdi; son katman değişimi ise ortalama sonuçları hafifçe iyileştirdi. Bu, katmana bağlı tahsis hipotezlerini yalnızca o test edilen ölçekte ve tarifte destekler.

**Yorum.** Makale, saf bir modülerlik anlatısını zayıflatır. Parametre çeşitliliği, davranışsal çeşitlilik, routing seçimleri ve insan tarafından yorumlanabilir uzmanlaşma farklı niceliklerdir. Mevcut MoE sistemlerinin gerçekten heterojen Expert'ler öğrenip öğrenmediği sonucuna varmanın erken olduğunu söyleyerek kapanır.

**Sınırlamalar.** Yazarlar, routing stratejilerinin ve mimari varyantlarının eksik kapsamını, esas olarak kosinüs benzerliğine dayanmayı ve ince ayar sonrası sınırlı analizi listeler. Gözlemler korelasyoneldir. Daha büyük çıktı normu gate seçimiyle ilişkili olabilir, ancak trade faydası için doğru hedef olmayabilir. Katman deneyi tüm olası değişiklikleri yalıtmaz ve V8'in katmansız Expert mimarisinden çok uzaktır.

**V8 kullanımı.** Uzmanlaşmayı parametre uzaklığından veya seçim sıklığından tanımlamayın. Sonuç koşullu, karşı olgusal uzmanlaşma ölçüleri kullanın. V8 bir gün Expert temsillerini birlikte öğrenirse, sıfırdan ile paylaşılan/upcycled başlatmayı karşılaştırın ve paylaşılan başlatmanın yedekli Expert'ler üretip üretmediğini kaydedin.

### 5. Cai ve arkadaşları — LLM MoE survey (arXiv:2407.06204)

**Kaynak ve kanıt türü.** Weilin Cai, Juyong Jiang, Fan Wang, Jing Tang, Sunghun Kim ve Jiayi Huang, *A Survey on Mixture of Experts in Large Language Models* (ilk yayın 2024; v3 2025). [arXiv özeti](https://arxiv.org/abs/2407.06204). Survey ve taksonomi.

**Makalenin katkısı.** Bu survey; yoğun, token-seçimli, Expert-seçimli, eğitilemez ve yumuşak/birleştiren gate'leri; Expert mimarisini/sayısını/boyutunu/sıklığını; paylaşılan Expert'leri; yoğundan-seyrek ve seyrekten-yoğun eğitimi; ve sistem düzeyindeki hesaplama, iletişim ve depolamayı ayırt eder. Birkaç önemli gerilimi belgeler:

- token-seçimli routing genellikle yardımcı dengeleme kayıpları gerektirir, ancak dengelemenin önemi eşit token sayılarını garanti etmez;
- kapasite sınırları token'ları düşürebilir ve konum yanlılığı getirebilir ("sona doğru düşme" dahil);
- routing erken uzmanlaşabilir ve büyük ölçüde bağlamdan çok token kimliğine göre olabilir;
- dengeleme kaybı, çok görevli ortamlarda göreve özgü tahsisle çatışabilir;
- top-k, Expert-seçimli, yumuşak routing ve sabit/eğitilemez routing farklı kalite–istikrar–sistem ödünleşimleri yapar.

**Sınırlamalar.** Heterojen benchmark'lar ve hızla değişen sistemlerle geniş bir ikincil survey'dir. Raporlanan hiperparametreler, aynı katsayıların veya gate ailelerinin LLM eğitimi dışında da çalıştığına dair kanıt değildir. "Sektörde baskın" bir benimseme ifadesidir, bir optimallik sonucu değildir. Hiçbir ekonomik veya zamansal karar problemi değerlendirilmemiştir.

**V8 kullanımı.** Routing test edilirse, token/candidate seçimini Expert-kapasite zamanlamasından ayırın. Bir kapasite sınırına ulaşıldığında Candidate'ları sessizce düşürmeyin; bunları açık `REJECTED`/`SUPPRESSED` olayları ve gerekçe olarak kaydedin. Öğrenmenin üstün olduğunu varsaymak yerine sabit habitat routing'i öğrenilmiş routing ile karşılaştırın.

### 6. Zhang ve arkadaşları için yinelenen HTML girdisi (arXiv:2507.11181v1)

**Kaynak durumu.** *Mixture of Experts in Large Language Models (HTML version)*, 2. maddenin HTML temsilidir, başka bir makale değildir. [arXiv HTML](https://arxiv.org/html/2507.11181v1). 2. maddeyle aynı başlığa, yazarlara ve temel çalışmaya sahiptir; v1 ile incelenen PDF'in v2'si editoryal olarak farklılık gösterebilir.

**Kanıt işlemi.** Bir kez sayın. HTML sayfası erişilebilirliği ve bölüm düzeyinde bağlantıları iyileştirebilir, ancak bağımsız bir deney, kuram veya tekrar katmaz. Herhangi bir kaynakça veya "okunan makale sayısı" ifadesi 15 atanmış girdi, 14 benzersiz makale olarak raporlanmalıdır.

### 7. Jiang ve arkadaşları — Mixtral 8x7B teknik raporu (arXiv:2401.04088)

**Kaynak ve kanıt türü.** Albert Q. Jiang ve arkadaşları, *Mixtral of Experts* (2024). [arXiv özeti](https://arxiv.org/abs/2401.04088). Benchmark ve routing analizli doğrudan model raporu.

**Yöntem ve doğrudan kanıt.** Mixtral, her transformer FFN alt bloğunu sekiz SwiGLU Expert ile değiştirir ve her token için en iyi iki logit üzerinde softmax uygulayan doğrusal bir router kullanır. Her token, yaklaşık 47B seyrek parametreli bir modelden 13B aktif parametreye erişir. Yazarların değerlendirme hattında Mixtral, daha az aktif parametre kullanırken çoğu raporlanan benchmark'ta Llama 2 70B'yi yakaladı ya da aştı: MMLU %70,6'a karşılık %69,9, MBPP %60,7'a karşılık %49,8, MATH %28,4'e karşılık %13,8 ve GSM8K %74,4'e karşılık %69,6. Rapor, aktif parametre sayısının bellek maliyetini, donanım kullanımını, routing yükünü ve artan bellek yüklerini ihmal ettiğini açıkça not eder; seyrek MoE özellikle toplu iş yüklerine uygundur.

Routing analizi, V8 için manşet benchmark'lardan daha önemlidir. ArXiv, GitHub, PubMed Abstracts, PhilPapers, StackExchange, Gutenberg ve Wikipedia genelinde Expert-seçim oranları geniş ölçüde benzerdi. Yazarlar orta/son katmanlarda daha çok sözdizimsel davranış ve yüksek ardışık-token yerellik gözlemledi. İlk-seçim routing için, aynı-Expert tekrarı 15. katmanda %12,5 rastgele referansa karşılık yaklaşık %24–28 idi; iki seçimden biri dikkate alındığında tekrar, yaklaşık %46 rastgele referansa karşılık kabaca %62–67 idi. Gösterilen örneklerde seçimin alandan çok sözdizimiyle hizalandığı sonucuna varırlar.

**Sınırlamalar.** Bu, model üreticisinden gelen bir teknik rapordur; eğitim verisi, toplam parametre, duvar-saati bütçesi ve bellek üzerinde eşleştirilmiş kontrollü bir MoE-versus-yoğun deney değildir. Eğitim verisi/hesaplama ayrıntıları eksiktir. Pek çok benchmark karşılaştırması model ailesi ve ön-eğitim açısından farklılık gösterir. Routing analizi küçük olarak tanımlanır, seçili katmanları ve veri kümelerini inceler ve routing örüntülerini benchmark kazançlarına nedensel olarak bağlamaz. LLM token-routing verimliliği, Candidate-routing değeri anlamına gelmez.

**V8 kullanımı.** Mevcut tüm-ucuz-Expert baseline'ını koru. Öğrenilmiş routing tanıtılırsa, anlamsal/ekonomik hizalamayı doğrudan test et: atanan Expert kimliği, ortak durum kontrol edildikten sonra mekanizma/habitat ve artımlı net faydayı öngörmelidir. Ayrıca patlama/yerellik etkilerini ölç; çünkü ilişkili ardışık atamalar, ortalama yükler dengeli görünse bile bir rotayı aşırı yükleyebilir ya da riski yoğunlaştırabilir.

### 8. Scardapane ve arkadaşları — koşullu hesaplama eğitici yazısı (arXiv:2403.07965)

**Kaynak ve kanıt türü.** Simone Scardapane, Alessandro Baiocchi, Alessio Devoto, Valerio Marsocci, Pasquale Minervini ve Jary Pomponi, *Conditional computation in neural networks: principles and research trends* (2024). [arXiv özeti](https://arxiv.org/abs/2403.07965). Eğitici yazı/survey.

**Makalenin katkısı.** Makale, dinamik girdi seyrekliği (token seçimi), genişlik seyrekliği (MoE) ve derinlik seyrekliği (erken çıkışlar) için ortak bir biçimcilik sağlar. Gumbel-softmax yaklaşımları dahil sert/ayrık routing'i, yumuşak routing/birleştirmeden ayırır. Sentezi, sabit doğruluk–hesaplama ödünleşimlerini, routing çöküşünü, yük dengesizliğini, küresel yerine yerel optimize edilmiş routing'i ve olgun uzmanlaşma/genelleme metriklerinin eksikliğini vurgular.

Uzmanlaşma bölümü alışılmadık biçimde ihtiyatlıdır: sert routing uzmanlaşmayı kolaylaştırabilir, ama öğrenilmiş routing bazen sabit routing'in gerisinde kalmıştır; pek çok karar bağlamı yok sayabilir ve eğitimde erken sabitlenebilir. Makale ayrıca routing grafiklerinin teşhis için yararlı olduğunu ama ilkeli benchmark'lardan yoksun olduğunu ve çok sayıda modülle yönetilemez hale gelebileceğini not eder.

**Sınırlamalar.** Hangi koşullu-hesaplama ailesinin en iyi olduğunu kuran yeni kontrollü bir MoE deneyi yoktur. Örnekler farklı hedeflere sahip görüntü, dil ve ağlara yayılır. FLOP azalmaları gecikme ya da ekonomik faydayı garanti etmez. Eğitici yazı, küresel routing'i, elastik çıkarım bütçelerini ve uzmanlaşma ölçümünü açıkça açık bırakır.

**V8 kullanımı.** Bu, deterministik bir ön-router'ı öğrenilmiş bir router ile karşılaştırmayı ve `NO_TRADE`/erken-çıkış davranışını gözlemlenebilir tutmayı destekler. V8 için "erken çıkış", eksik bir kayıt değil, açık neden kodlu bir Expert değerlendirmesi anlamına gelmelidir. Sabit kapsam ve sabit hesaplama bütçeleri, kalitenin yanında raporlanmalıdır.

### 9. Feng ve arkadaşları — sınıflandırıcı-türevli seçici skorlar (arXiv:2206.09034)

**Kaynak ve kanıt türü.** Leo Feng, Mohamed Osama Ahmed, Hossein Hajimirsadeghi ve Amir Abdi, *Towards Better Selective Classification* (arXiv 2022; ICLR 2023). [arXiv özeti](https://arxiv.org/abs/2206.09034). Doğrudan görüntü-sınıflandırma deneyleri.

**Yöntem ve doğrudan kanıt.** Makale, SelectiveNet'in seçim başlığını, Deep Gamblers'ın çekimserlik logitini ve Self-Adaptive Training'in çekimserlik logitini basit bir sınıflandırıcı-türevli skorla karşılaştırır: maksimum sınıf softmax olasılığı ("Softmax Response," SR). Uzman mimarilerin alttaki sınıflandırıcıyı iyileştirdiğini ama ayrı seçim mekanizmalarının ek bir genelleme başarısızlık noktası eklediğini savunur. Prosedürleri dışsal seçim çıktısını atar, durumları SR ile sıralar ve hedef kapsam için doğrulama verisinde bir eşik seçer. Eğitim sırasında ayrıca entropi-minimizasyon düzenlileştirmesi eklerler.

ImageNet100'de, orijinal mekanizmayı SR ile değiştirmek çoğu kapsamda seçici hatayı azalttı. Örnekler arasında SelectiveNet %80 kapsamda %6,00'den %4,47'ye; Self-Adaptive Training %5,20'den %4,46'ya; %60 kapsamda SAT %1,72'den %1,37'ye düştü. Çok düşük kapsamda SelectiveNet'in kendisi dramatik biçimde başarısız olurken SAT kullanılabilir kaldı. 25–175 sınıflı ImageNet alt kümelerinde, SAT artı entropi minimizasyonu ve SR, %30, %50 ve %70 kapsamda raporlanan hatayı iyileştirdi; makale seçili karşılaştırmalarda %80–85'e varan göreli kazançlar raporlar. Deneyler CIFAR-10, ImageNet/ImageNet100 alt kümeleri, StanfordCars ve Food101'i içerir.

**Sınırlamalar.** Bu, çoğunlukla IID görüntü benchmark'ları altında sınıflandırmadır; eşik kalibrasyonu doğrulama ve testin aynı dağılımdan geldiğini varsayar. Yazarlar OOD test verisinin hedef kapsamı geçersiz kılabileceğini ve seçici sınıflandırmanın sınıf/grup eşitsizliklerini büyütebileceğini açıkça kabul eder. SR olasılıksal olarak kalibre edilmiş olmak zorunda değildir; sabit kapsam için temelde yararlı bir sıralama gerekir. Entropi minimizasyonu kayma altında aşırı güven yaratabilir. Raporlanan göreli iyileştirmeler, baseline hatası küçükken büyük görünebilir. Görevlerin hiçbiri işlem maliyetleri, asimetrik fırsat maliyetleri, seri bağımlılık ya da portföy kısıtları içermez.

**V8 kullanımı.** Expert'in yerel kanıtını/skorunu, Scorer deneyleri için ekstra-model içermeyen güçlü bir baseline olarak dahil et. Eşikleri yalnızca her kronolojik eğitim katının içinde kalibre et. Elde edilen ve hedeflenen kapsam ile riski varlık, yön, likidite, volatilite ve zaman rejimi bazında raporla; böylece toplu iyileştirmeler seçici dışlamayı gizleyemez.

### 10. Franc, Prusa ve Voracek — optimal reddetme stratejileri (arXiv:2101.12523)

**Kaynak ve kanıt türü.** Vojtech Franc, Daniel Prusa ve Vaclav Voracek, *Optimal strategies for reject option classifiers* (arXiv 2021; sonra JMLR 2023). [arXiv özeti](https://arxiv.org/abs/2101.12523). Doğrudan kuram artı benchmark deneyleri.

**Kuram.** Makale üç hedefi biçimselleştirir:

- **maliyet-bazlı:** beklenen tahmin kaybını artı sabit bir reddetme maliyetini en aza indir;
- **sınırlı-iyileştirme:** seçici-risk tavanına bağlı olarak kapsamı en üstle;
- **sınırlı-kapsam:** kapsam tabanına bağlı olarak seçici riski en aza indir.

Bilinen veri-üreten dağılım için üçü de aynı optimal strateji sınıfını verir: bir Bayes sınıflandırıcısı artı rastgeleleştirilmiş bir Bayes seçim fonksiyonu. Koşullu-risk eşiğinin altını kabul et, üstünü reddet ve tam eşitliklerde rastgeleleştir. "Uygun bir belirsizlik skoru" kesin riski tahmin etmek zorunda değildir; sıralamasını koruması yeterlidir. Makale tüm risk–kapsam eğrisini sınırlı-kapsam çözümlerine bağlar ve AuRC'yi tekdüze seçilen bir hedef kapsam altında ortalama seçici risk olarak yorumlar.

Yazarlar kayıp regresyonunu ve SELE'yi, AuRC için yumuşak bir ikili sıralama vekilini önerir. Uygun-risk sıralaması için Fisher tutarlılığını kanıtlar. SELE kaybı, verilen kurulum altında ampirik AuRC'nin iki katı içindedir ve optimizasyonda açık sıralamadan kaçınır.

**Doğrudan ampirik kanıt.** 11 sınıflandırma veri kümesinde SELE, lojistik regresyonda ortalama AuRC sırası 1.36'ya karşılık maksimum sınıf olasılığı için 2.73 ve SVM'de 1.09'a karşılık marj için 2.82 idi. Lojistik regresyon için MCP'yi ve regresyonu anlamlı biçimde yendi ve makalenin Nemenyi karşılaştırmaları altında SVM marjını/regresyonunu yendi; ancak COVTYPE ya da PENDIGIT gibi bireysel veri kümeleri öğrenilmiş skorların tekdüze en iyi olmadığını gösterir. Kalibre edilmiş olasılıksal bir sınıflandırıcı üzerindeki öğrenilmiş kazançlar, ayrımcı bir SVM marjı üzerindeki kazançlardan daha mütevazıydı. 11 sıralı-regresyon veri kümesinde her iki öğrenilmiş skor da yerel marj baseline'ını yendi; yapılandırılmış-çıktı yüz-noktası görevi de iyileşti.

**Sınırlamalar.** Bayes eşdeğerliği, ilgili dağılımın/koşullu riskin ve kaybın iyi tanımlı olduğunu varsayar. Fisher tutarlılığı asimptotiktir ve sonlu-örneklem, kaymış ya da bağımlı-piyasa performansını garanti etmez. AuRC, kapsam düzeylerini tekdüze ağırlıklandırır; bu V8 ekonomisini yansıtmayabilir. Benchmark bölmeleri finansal walk-forward testleri değildir. Skaler bir belirsizlik sıralaması, değişen sermaye kısıtlarını, eşzamanlı Candidate'lar arasındaki etkileşimleri ya da execution maliyetlerini, hedef kaybın parçası olmadıkça tek başına ele alamaz.

**V8 kullanımı.** V8 Scorer hedefini, genel sınıflandırma hatası yerine **koşullu ekonomik kaybın** tahmini ya da sıralaması olarak tanımla. Yerel kanıtı, kayıp regresyonunu, ikili sıralama kaybını, lojistik ve sığ ağacı aynı Candidate evreninde ve kapsamda karşılaştır. Birincil olarak önceden bildirilen kapsamda ekonomik faydayı kullan; AuRC ya da bir fayda–kapsam eğrisi teşhistir.

### 11. Inácio ve arkadaşları — meta-öğrenme ile seçici zaman serisi tahmini (arXiv:2606.23448)

**Kaynak ve kanıt türü.** Ricardo Inácio, Vitor Cerqueira, Marília Barandas ve Carlos Soares, *Selective Time Series Forecasting via Metalearning* (2026). [arXiv özeti](https://arxiv.org/abs/2606.23448). Doğrudan yuvarlanan-köken ve transfer deneyleri.

**Yöntem.** Yöntem, tahmin verilmeden önce bir tahmin kökeninin zor olup olmayacağını öngörür. Bir CatBoost meta-modeli, son gecikme penceresinin TSFEL tanımlayıcılarını—trend, mevsimsellik, zamansal, spektral ve karmaşıklık feature'ları—tarihsel tahmin hatasının seri-içi ampirik yüzdelik dilimine eşler. Yüzdelik normalizasyon, ölçeği kaldırmayı ve seriler-arası transferi desteklemeyi amaçlar. Tahmin hataları yuvarlanan-köken değerlendirmesiyle elde edilir. Çıkarımda, tahmin edilen hata yüzdelik dilimi bir eşiğin üzerinde olan kökenler reddedilir. Tasarım tahminciden ayrıdır ve sıfır-atış ya da daha önceki hedef-alanı kökenleri üzerinde uyarlanarak çalışabilir.

**Doğrudan kanıt.** Çalışma M1, M3 ve Tourism aylık/üç aylık serilerini; NHITS ve KAN tahmincilerini; 6 aylık ya da 4 üç aylık ufukları; ve kaynak→hedef çiftleri M3→M1 ve M1→Tourism'i kullanır. Gruplu çapraz-doğrulama, bir serinin kökenlerini bir arada tutar. Alan-içi Spearman korelasyonları tahmin edilen ve gerçekleşen hata sırası arasında 0.71–0.90 idi. Sıfır-atış transfer korelasyonu ve AUCO'yu bozarken, hedef kökenlerin %30'unda uyarlama raporlanan tüm durumlarda korelasyonu ve AUCO'yu iyileştirdi. Örneğin, KAN ile M3-aylık→M1-aylık Spearman'ı 0.628 sıfır-atıştan 0.820 uyarlanmışa ve AUCO'yu 0.043'ten 0.013'e iyileştirdi; NHITS ile 0.571'den 0.812'ye ve 0.045'ten 0.013'e.

Temel düzeyde, uyarlanmış reddetme, raporlanan reddetme oranlarında sMAPE'yi monotonik olarak azalttı ve genellikle bir oracle'a en küçük boşluğa sahipti. Tourism aylık KAN için, tut-hepsi sMAPE 0.288, %40 reddetmeden sonra 0.215'e düştü; kalıntı-ölçek 0.228'e ulaşırken tahmin-aralığı genişliği 0.325'e kötüleşti. NHITS ve üç aylık veri için de benzer örüntüler raporlandı. Seri düzeyinde bir bootstrap, yöntemi bir NHITS/M1-üç aylık kalıntı-ölçek karşılaştırması dışında tüm baseline'lardan oracle'a daha yakın buldu (p=0.191).

**Sınırlamalar.** Yazarlar yöntemin temsili meta-eğitim verisine bağlı olduğunu, kısa alanlar için daha az güvenilir hale geldiğini, kalibre edilmiş belirsizlik yerine göreli risk öngördüğünü ve biçimsel garanti sağlamadığını açıkça belirtir. Veri kümeleri yüksek frekanslı piyasalar değil, düşük frekanslı benchmark serileridir. Hedef uyarlama etiketli daha erken kökenleri kullanır ve nedensel olarak uygulanmalıdır. Tahmin hatası trade faydası değildir; bir dönem tahmin etmesi zor olabilir ama yine de sağlam bir yön ya da volatilite trade'i sunabilir ve bunun tersi de geçerlidir. Baseline kümesi sınırlıdır.

**V8 kullanımı.** Yakın bir V8 benzeri, yalnızca kabul edilebilir durumdan inşa edilen ve yuvarlanan sonuçlar üzerinde eğitilen bir ex-ante "candidate zorluğu" meta-modelidir. Onu yalnızca deterministik Expert'ler var olduktan sonra, yerel kanıta ve kalıntı/durum-kalitesi buluşsal yöntemlerine karşı test et. Hedefleri varlık ya da bildirilen eş değer grubu içinde ihtiyatla normalize et: yüzdelik normalizasyon transferi iyileştirir ama mutlak ekonomik büyüklüğü atar.

### 12. Fu ve arkadaşları — derin tahmin için seçici öğrenme (arXiv:2510.25207)

**Kaynak ve kanıt türü.** Yisong Fu, Zezhi Shao, Chengqing Yu, Yujie Li, Zhulin An, Qi Wang, Yongjun Xu ve Fei Wang, *Selective Learning for Deep Time Series Forecasting* (NeurIPS 2025). [arXiv özeti](https://arxiv.org/abs/2510.25207). Doğrudan eğitim-yöntemi deneyleri artı sınırlı bir varyans-tahmini sonucu.

**Yöntem.** Bu makale dağıtımda tahminleri **reddetmez**. Genelleştirilemez sayılan zaman noktalarını maskeleyerek eğitim kaybını değiştirir. Bir belirsizlik maskesi, örtüşen kayan-pencere tahminlerinden kalıntı entropisini tahmin eder. Bir anomali maskesi, hafif bir modelin tahmin edilen kalıntı alt sınırını kullanır ve mevcut kalıntısı o sınıra yakın olan noktaları maskeler. Model MSE'yi yalnızca korunan zaman adımlarında hesaplar. Bir teorem, Lipschitz, sınırlı-kalıntı, sınırlı-gradyan, öğrenme-oranı ve güncelleme-boşluğu varsayımları altında tarihsel kalıntı-varyansı tahmini ile mevcut model altındaki varyans arasındaki farkı sınırlar.

**Doğrudan kanıt.** Sekiz veri kümesinde (dört ETT varyantı, Electricity, Exchange, Weather, ILI), dört ufukta ve altı omurgada yazarlar, üç çalıştırmanın ortalaması alınarak 192 omurga/veri kümesi/ufuk durumunun tamamında iyileştirme raporlar. Ortalama MSE azalmaları arasında Informer için %37,4, Crossformer için %15,6, TimesNet için %8,4, iTransformer için %6,5 ve TimeMixer için %4,3 vardır. ETTh1, ETTm2, Electricity ve Weather üzerindeki ablasyonlar, çift maskenin tek maskenin ya da eşit-oranlı rastgele maskelemenin ikisini de yendiğini gösterir. Sıfır-atış ETT transferi de iyileşti.

**Kritik sınırlamalar.** Makalenin ekinde belirsizlik maskelemesinin temiz bir sentetik veri kümesine zarar verebileceği görülür: MSE yalnızca %5 belirsizlik maskelemesinde 0.0295'ten 0.0475'e yükseldi ve daha büyük oranlarda çok daha fazla. Yazarlar çift maskenin nadir aşırı olayları kaldırabileceği ve aşırı-olay tahminini tehlikeye atabileceği konusunda uyarır. Maske oranları önemli ayarlanmış hiperparametrelerdir; Exchange'de %90 anomali maskesinin en iyi performans gösterdiği bildirilir; bu, kuyruk-özgü doğrulama olmadan trading'e kopyalamak için özellikle tehlikeli olur. Yöntem şu anda alan-içidir ve büyük temel-model ön-eğitimiyle doğrudan uyumlu değildir. Teorem, güçlü varsayımlar altında bir tahminci sapmasını sınırlar; maskelenmiş gözlemlerin ekonomik olarak önemsiz olduğunu kanıtlamaz.

**V8 kullanımı.** Bunu `NO_TRADE` için kanıt olarak alıntılama. Yalnızca ayrı bir Expert-eğitimi sağlamlık deneyini motive eder. Herhangi bir V8 maskeleme çalışması, bir kuyruk-olayı holdout'unu korumalı ve kriz/büyük-hareket geri çağırımını, düşüş faydasını ve kalibrasyonu test etmelidir. Yöntem tarafından maskelenen eğitim noktaları denetim defterinde kalmalıdır; Candidate evreninden kaybolamazlar.

### 13. Hallberg Szabadváry ve arkadaşları — conformal reddetme garantileri (arXiv:2506.21802)

**Kaynak ve kanıt türü.** Johan Hallberg Szabadváry, Tuwe Löfström, Ulf Johansson, Cecilia Sönströd, Ernst Ahlberg ve Lars Carlsson, *Classification with Reject Option: Distribution-free Error Guarantees via Conformal Prediction* (2025). [arXiv özeti](https://arxiv.org/abs/2506.21802). Doğrudan olasılık türetimi artı sayısal gösterimler.

**Yöntem ve teorem.** İkili sınıflandırmada bir conformal tahminci boş küme, singleton ya da her iki etiketi çıkarabilir. Önerilen reddedici yalnızca singleton kümeleri kabul eder. Boş kümeler yenilik reddi, iki-etiketli kümeler belirsizlik reddi olarak yorumlanır. Değişebilirlik altındaki çevrimiçi yumuşatılmış bir conformal tahminci için, `E` boş küme olayı, `S` singleton ve conformal anlamlılık ε ise, Önerme 2 singleton hata olasılığını verir:

`σ = (ε − P(E)) / P(S)`.

Özdeşlik, boş tahminlerin her zaman conformal hatalar olduğu ve çift tahminlerin asla olmadığı gerçeğinden gelir. Ampirik olarak, `(nε − e)/s` singleton hata oranını tahmin eder. Makale, bu formülün çevrimdışı endüktif conformal tahminde önceki kullanımını düzeltir: çevrimdışı geçerlilik eğitim-koşullu/PAC-benzeridir, kalibrasyon boyutuna ve bir güven parametresi δ'ya bağlıdır ve ayarlama olmadan tam bağımsız çevrimiçi hata sürecini miras almaz.

**Doğrudan kanıt.** Sayısal gösterimler QSAR biyobozunum üzerinde tam conformal tahmini, Spambase üzerinde çevrimdışı endüktif conformal tahmini ve ikiliye dönüştürülmüş bir California Housing görevinde toplu endüktif conformal tahminini kapsar. Tüm reddetme oranlarının ulaşılabilir olmadığını ve aynı reddetme oranının farklı hata oranlarıyla farklı ε değerlerinden doğabileceğini gösterirler. Bir tam-conformal örnekte, gözlemlerin en fazla yaklaşık %40'ı singleton tahminler verdi; bu yüzden minimum reddetme oranı yaklaşık %60 idi. Yazarlar ayrıca kabul edilen singleton sayıları küçükken tahmin edicinin gürültülü hale geldiğini not eder.

**Sınırlamalar.** Garanti, ilgili değişebilirlik kurulumunu, doğru çevrimiçi/çevrimdışı formülü ve yeterince çok singleton tahmini gerektirir. Etiket-kümesi kapsamı/hatasıyla ilgilidir, maliyet-sonrası faydayla değil. Makale yalnızca doğrudan ikili sınıflandırmayı ele alır; çok-sınıf için one-vs-all önerir. Tam conformal tahmin hesaplama açısından pratik olmayabilir. Piyasa dizileri durağan-değildir ve bağımlıdır; V8 seçimi/yeniden eğitimi uyarlanabilir olabilir. Teorem, keyfi varlık filtrelemesi, test döneminde eşik ayarı ya da veri revizyonlarından sonra kapsam vermez.

**V8 kullanımı.** Conformal tahmin olası bir güvenlik katmanıdır, varsayılan garanti değildir. Test edilirse, kurallı simülatör altında `counterfactual_net_utility > 0` gibi maliyet-duyarlı bir ikili hedef tanımla, kronolojik katlar içinde fit/ kalibre et ve yalnızca pozitif bir singleton kabul et. Boş ve belirsiz reddi ayrı raporla. Değişebilirlik ya da uygun bir zaman-serisi conformal yöntemi gerekçelendirilmedikçe, sonuçları "ampirik conformal teşhis" olarak etiketle; "dağılımdan-bağımsız garantili" değil.

### 14. Zhang, Wang ve Qiao — çok-kategorili reddet ve iyileştir (arXiv:1701.02265)

**Kaynak ve kanıt türü.** Chong Zhang, Wenbo Wang ve Xingye Qiao, *On Reject and Refine Options in Multicategory Classification* (2017). [arXiv özeti](https://arxiv.org/abs/1701.02265). Doğrudan kuram, simülasyonlar ve gerçek-veri çalışmaları.

**Yöntem ve kanıt.** Makale, bükülmüş kayıplı açı-tabanlı marj sınıflandırıcıları geliştirir. Tüm sınıf marjları sıfıra yakın olduğunda bir reddetme sonucu kullanılır. Yeni bir iyileştirme (refine) sonucu, olası sınıfların bir alt kümesini döndürür ve olası olmayanları eler. Önerme 2, 0-d-1 kaybı altında çok-sınıflı Chow/Bayes kuralını belirtir: en olası sınıfı yalnızca olasılığı `1-d`'yi aştığında tahmin et, aksi halde reddet. Yazarlar marj-türevli reddetme bölgelerinin genellikle çok-sınıflı Bayes bölgesine eşit olmadığını gösterir, ancak `a1` ve `a2` eğim parametreleri aracılığıyla sıkı iç/dış sınırlar kurar.

Kuramsal sonuçlar; artan boyut ve sınıf sayısıyla aşırı-risk yakınsamasını ve düşük-gürültü varsayımı altında daha hızlı oranları kapsar. Simülasyonlar ve gerçek-veri deneyleri normal, yalnızca-reddetme ve reddet-artı-iyileştir sınıflandırıcılarını karşılaştırır. İyileştirmenin raporlanan değeri, bilinçli olarak belirsiz alt kümelerde doğru sınıfın yüksek küme kapsamıdır. Örneğin, dört sınıflı bir simülasyonda normal sınıflandırıcının iyileştirme alt kümesindeki hatası %45,89 iken reddet-ve-iyileştir yönteminin yanlış-iyileştirme oranı %1,581 idi; ancak küme-değerli bir tahmin kesin bir etiketten daha kolaydır ve çıktılar eşit bilgi içeriyormuş gibi karşılaştırılmamalıdır.

**Sınırlamalar.** Sonuçlar marj kaybına, açı kodlamasına, reddetme maliyeti ve eşiklerin ayarlanmasına ve çoğunlukla IID sınıflandırmaya bağlıdır. İyileştirme kümesi aksiyon alanını ve kaybı değiştirir; düşük yanlış-iyileştirme oranı doğrudan top-1 hatasıyla karşılaştırılamaz. Bayes-bölge yaklaşımı çok-sınıflı durumda kesin değildir. Hiçbir zamansal, ekonomik ya da portföy süreci test edilmez.

**V8 kullanımı.** İyileştirme kavramı, belirsiz bir kurulumu, tek bir tetikleyici karşılanana kadar emir gönderimini yasaklarken açık olası yönler/mekanizmalarla `DETECTED` ya da `PENDING` olarak tutmak için bir tasarım benzetmesidir. Küme-değerli bir trade'in yürütülmesini haklı çıkarmaz. `NOT_APPLICABLE`, belirsiz kanıt ve güçlü olumsuz kanıt ayrımını tek bir `NO_TRADE` koduna sıkıştırmak yerine koru.

### 15. Ramaswamy, Tewari ve Agarwal — tutarlı çok-sınıflı reddetme (arXiv:1505.04137)

**Kaynak ve kanıt türü.** Harish G. Ramaswamy, Ambuj Tewari ve Shivani Agarwal, *Consistent Algorithms for Multiclass Classification with a Reject Option* (2015). [arXiv özeti](https://arxiv.org/abs/1505.04137). Doğrudan kuram ve küçük benchmark deneyleri.

**Kuram.** Yanlış-sınıflandırma maliyeti 1 ve çekimserlik maliyeti α olan çekimserlik kaybı altında Bayes kuralı, o posterior en az `1-α` olduğunda maksimum-posterior sınıfı öngörür ve aksi halde çekimser kalır. Makale, Crammer-Singer ve one-versus-all hinge vekillerinin, sıradan argmax yerine reddetme-farkında tahmin kurallarıyla eşleştirildiğinde α=1/2 için tutarlı hale geldiğini gösterir. `n` yerine `ceil(log2 n)` boyutta çalışan ikili-kodlu-tahmin (BEP) dışbükey vekilini tanıtır ve aşırı-risk dönüşüm sınırları türetir. Genellemeler α'yı `[0, 1/2]` içinde kapsar.

**Doğrudan ampirik kanıt.** Sentetik ve UCI çok-sınıflı deneyler, Crammer-Singer, one-versus-all ve BEP'i sabit reddetme oranlarında (%0, %20, %40) karşılaştırır. BEP, gösterilen deneylerde one-versus-all ile karşılaştırılabilir ve Crammer-Singer'dan daha iyi olarak raporlanır; logaritmik olarak çok sayıda fonksiyon öğrendiği için eğitim daha kısadır. Ampirik bölüm bir kavram kanıtıdır; kapsamlı modern bir benchmark değildir.

**Sınırlamalar.** Ana vekil sonuçları α≤1/2 ile sınırlıdır; makale α>1/2'yi açıkça gelecek çalışma olarak bırakır. Maliyet oranı anlamlı ve istikrarlı olmalıdır. Tutarlılık asimptotiktir ve IID sınıflandırmadaki sabit reddetme oranları piyasa sürüklenmesini ya da faydayı çözmez. İkili kodlama keyfi bir sınıf kodu dayatabilir; V8 Expert mekanizmaları yalnızca sınıf etiketleri değildir.

**V8 kullanımı.** Bir reddetme kararı, eğitilen/değerlendirilen kaybın ve tahmin kuralının parçası olmalıdır; keyfi bir skora güven eşiği eklemek, amaçlanan ekonomik hedefle tutarlı olmayabilir. V8, trade, yanlış-yönlü trade ve `NO_TRADE` maliyetlerini açıkça ifade etmeli ve önceden bildirilen ekonomik olarak makul bir aralık üzerinde duyarlılığı test etmelidir.

## Makaleler-arası sentez — V8 bileşenleri için

### Router

**Desteklenen.** Seyrek kapılar, büyük sinir sistemlerinde aktif hesaplamayı azaltabilir ve kapasiteyi artırabilir. Router çöküşü, eşit olmayan yük, kapasite taşması, erken/donmuş atama, token-kimliği yönlendirmesi ve sistem yükü tekrarlayan sorunlardır. Sabit routing, bazı ortamlarda öğrenilmiş routing ile rekabet edebilir ya da onu geçebilir. Routing, veri ve Expert'ler uygun yapıya sahip olduğunda anlamlı kümeler keşfedebilir.

**Desteklenmeyen.** Hiçbir makale bir Router'ın iki ya da üç ucuz deterministik trading Expert'inden oluşan bir topluluğu iyileştirdiğini kurmaz. Hiçbir makale, tahmin kaybıyla eğitilmiş bir kapının nadir, yüksek-faydalı Candidate'ları koruduğunu göstermez. Hiçbir makale dengeli Expert yüklerini yararlı uzmanlaşmayla eşitlemez.

**V8 kararı.** D-004'ü koru: başlangıç baseline'ında Router yok. Bir "ön-router" daha sonra ayrıca sürümlenmiş bir dışlama politikası olarak test edilebilir. Deneyde skor, eşik, neden, model sürümü ve karşı-olgusal Expert değerlendirmesiyle açık bir `ExpertSkipped` kaydı üretmelidir; böylece yanlış dışlamalar ölçülebilir.

### Expert'ler

**Desteklenen.** MoE en makul olduğunda istikrarlı, sömürülebilir heterojenlik vardır; Chen ve arkadaşlarının CIFAR karşıtlığı, onsuz az fayda ve net küme yapısıyla kurgulanmış bir görevde daha çok fayda gösterir. Doğrusal-olmayan ya da ifade gücü yüksek Expert'ler ve eğitim dinamikleri önemlidir. Sonradan (post-hoc) parametre/routing görselleştirmeleri, işlevsel uzmanlaşma kurmak için yetersizdir.

**V8 kararı.** Bir Expert, kendi habitat/setup/trigger/invalidation/expiry'sine sahip sürümlenmiş, çalıştırılabilir bir hipotez olarak kalır. Deterministik self-gating Expert'ler ve eşit-bilgili global karşılaştırıcı ile başla. Yalnızca farklı çıktılar değil, atamaya-özgü karşı-olgusal avantaj gerektir.

### Candidate Scorer

**Desteklenen.** Seçici kararlar için durumlar koşullu riske göre sıralanmalıdır. Sınıflandırıcı-yerel bir skor güçlü bir baseline olabilir; öğrenilmiş bir kayıp-sıralama skoru, yerel skorlar riski kötü sıraladığında değer katabilir. Dışsal seçim başlıkları tahminciden ayrı olarak başarısız olabilir. Eşik kalibrasyonu yöntemin parçasıdır, raporlama sonradan düşüncesi değil.

**V8 kararı.** D-007'yi koru: başlangıçta öğrenilmiş Scorer yok. Deterministik kanıt skoru baseline'dır. Test edildiğinde Candidate evrenini sabit tut ve scorer'ları tam eşleşen kapsamda karşılaştır. Hedef, yalnızca yön doğruluğu değil, kurallı maliyet-sonrası faydayı ve ilgili olduğunda drawdown/kuyruk kaybını içermelidir.

### `NO_TRADE`

**Desteklenen.** Çekimserlik, maliyeti ya da kapsam/risk kısıtı olan açık bir aksiyondur. Kapsam ve seçici risk, tek bir doğruluk sayısı değil bir eğri oluşturur. Reddetme nedene göre ayrılabilir (belirsizlik versus yenilik). Eşikler dağılım kayması altında başarısız olabilir ve düşük kapsam sistematik dışlamayı gizleyebilir.

**V8 kararı.** `NO_TRADE` eksik veri, düşen bir satır ya da hiç çağrılmamış bir Expert değildir. En az şunları temsil et: `NOT_APPLICABLE`, `INSUFFICIENT_EVIDENCE`, `AMBIGUOUS_DIRECTION`, `STATE_INVALID/DEGRADED`, `RISK_REJECTED`, `CAPACITY_REJECTED` ve `SCORER_REJECTED`. Her biri günlüklenen bir değerlendirme ya da yaşam-döngüsü geçişidir. Çalışma noktasını önceden kayıtlı bir ekonomik hedeften seç ve gerçekleşen kapsamı ölç.

## V8'in koruması gereken çelişkiler ve gerilimler

| Gerilim | Bir tarafta kanıt | Diğer tarafta kanıt | V8 çözümü |
|---|---|---|---|
| MoE uzmanlaşma yaratır | Chen ve arkadaşları kurgulanmış bir dağılım altında küme uzmanlaşmasını kanıtlar/gözlemler; çok dilli routing kısmen dille hizalanır. | Mixtral çok az alan düzeyi routing bulur; Lo ve arkadaşları heterojen uzmanlığın kanıtlanmamış kaldığını söyler. | Uzmanlaşma bir hipotezdir. Expert-değişimi ve koşullu-fayda testleri gerektir. |
| Öğrenilmiş routing tercih edilir | MoE başarısı genellikle eğitilebilir kapılar kullanır. | Koşullu-hesaplama survey'i öğrenilmiş routing'in sabit routing'e göre yetersiz kalabileceğini bildirir; routing bağlamı yok sayabilir/erken donabilir. | Aynı olaylarda tüm-Expert'leri, sabit habitat'ı ve öğrenilmiş router'ı karşılaştır. |
| Dengeli yük arzu edilir | Çöküşü ve cihaz darboğazlarını önler. | Dengeleme görev hizalamasına karşı çalışabilir; tekdüze trafik uzmanlaşma değildir. | Dengeyi bir kısıt/teşhis olarak ele al; asla birincil kalite metriği değil. |
| Yerel güven yeterlidir | Feng ve arkadaşları SR'nin görüntü benchmark'larında ayrı başlıkları yendiğini gösterir. | Franc ve arkadaşları öğrenilmiş SELE/kayıp skorlarının, özellikle SVM'lerde, MCP/marjları yenebileceğini gösterir. | Yerel kanıt zorunlu baseline'dır; öğrenilmiş skoru yalnızca eşleştirilmiş OOS kazancıyla kabul et. |
| Güven, reddetme kalitesini garanti eder | Conformal singleton tahminlerinin değişebilirlik altında türetilmiş bir hata oranı vardır. | Çevrimdışı formüller düzeltme gerektirir; ulaşılabilir kapsam sınırlı olabilir; piyasa kayması saf varsayımları ihlal eder. | Varsayımları belirt; aksi halde yalnızca ampirik kapsam raporla. |
| Seçici öğrenme sağlamlığı iyileştirir | Fu ve arkadaşları belirsiz/anormal zaman adımlarını maskeleyerek ortalama tahmin hatasını iyileştirir. | Aynı makale belirsizlik maskelemesinin temiz veriye zarar verdiğini gösterir ve kayıp aşırı-olay kapasitesi konusunda uyarır. | Kuyruk-koruma ve kriz geri çağırımı veto metrikleridir. Eğitim maskesini `NO_TRADE` ile eşitleme. |
| Aktarılabilir öngörülebilirlik vardır | Inácio ve arkadaşları yararlı sıfır-atış sıralaması ve güçlü uyarlanmış sonuçlar elde eder. | Sıfır-atış performansı bozulur; yöntemin olasılıksal garantisi yoktur ve temsili meta-veriye dayanır. | Yuvarlanan alan-uyarlanmış rakip kullan; sürüklenme/feature-desteği testleri ihlal edildiğinde kapalı-başarısız ol. |
| Tek skaler çalışma hedefi yeterlidir | Bayes kuramı maliyeti, risk tavanını ve kapsam tabanını aynı koşullu-risk sıralamasıyla birleştirir. | Pratik eşikler ve ekonomik ödünleşimler farklıdır; portföy çekişmesi noktasal değildir. | Scorer Candidate'ları sıralar; portföy kabulü ayrı bir risk/kapasite aksiyonu olarak kalır. |

## Somut deney programı

### Deney R1 — Herhangi bir Router haklı mı?

**Soru.** Ucuz bir kapı, ekonomik olarak değerli Candidate'ları kaybetmeden Expert değerlendirmelerini atlayabilir mi?

**Kollar.** (A) tüm deterministik Expert'leri çalıştır; (B) sabit deterministik habitat ön-router; (C) lojistik kapı; (D) sığ ağaç kapısı. Daha basit bir öğrenilmiş kapı geçene kadar derin bir Router ekleme.

**Birim ve bölme.** Karar saati × araç, gruplu kronolojik katlar, Candidate sonuç ufukları üzerinde temizleme/ambargo ve dokunulmamış bir nihai dönemle. Eşikleri ve dönüşümleri her eğitim katının içinde fit et. Belirsizlik tahminlerinde varlık/oturum bağımlılığını koru.

**Birincil veto metriği.** Testten önce, kurallı karşı-olgusal net faydası önceden kayıtlı ekonomik eşiği aşan bir Candidate olarak tanımlanan `valuable_candidate` geri çağırımı. OOS sonuçlarını görmeden önce belirtilen neredeyse-mükemmel geri çağırım düzeyini gerektir; tek taraflı bir alt güven sınırı raporla. Tek bir yüksek-şiddetli kaçırılmış kuyruk Candidate'ı niteliksel incelemeyi tetikleyebilir.

**İkincil metrikler.** Önlenen Expert değerlendirmeleri, duvar-saati p50/p95/p99 gecikmesi, CPU/bellek, değerli-Candidate kesinliği, Expert/varlık/rejim bazında yanlış dışlamalar, Candidate örtüşmesi, aşağı akış sabit politikasının maliyet-sonrası faydası, yük patlama(lılığ)ı ve routing istikrarı. "Dengeli routing" ve "daha az değerlendirme", geri çağırım kapısının başarısızlığını telafi edemez.

**Kabul.** Yalnızca C ya da D, bağlayıcı bir operasyonel kısıtta B ve A'yı yenerse, değerli-Candidate geri çağırımını karşılarken ve eşleştirilmiş OOS net faydasını azaltmazken. Aksi halde A'yı koru.

### Deney E1 — Expert'ler ekonomik olarak uzmanlaşıyor mu?

**Soru.** Önerilen Expert ayrıştırması, aynı karar-zamanı bilgisine sahip tek bir global kural/modelin ötesinde değer katıyor mu?

**Kollar.** Her uygun olayda her Expert; o olayda tüm diğer Expert'ler karşı-olgusal olarak; eşit-bilgili global baseline; karıştırılmış habitat etiketleri; uygulanabilirse havuzlanmış çok-görevli model.

**Metrikler.** Koşullu maliyet-sonrası fayda, önceden bildirilen Candidate etiketleri için Brier/log kaybı, kalibrasyon, değerli-Candidate geri çağırımı ve olay sayısı. Bir uzmanlaşma matrisi `U[i,j]` tanımla: Expert `i`'nin habitat `j`'ye atanan olaylardaki faydası. Yararlı uzmanlaşma, yalnızca farklı sinyal sıklığı değil, köşegen-dışı Expert'lere ve global baseline'a karşı istikrarlı bir köşegen avantajı gerektirir. Blok-bootstrap aralıkları ve çokluk-ayarlı aile testleri raporla.

**Kabul.** Bir Expert'i yalnızca mekanizmasına-özgü köşegen avantajı replike olursa koru. Expert'ler yedekliyse birleştir/basitleştir. Hiçbir Expert global'i yenmezse, o test edilen aile için H3'ü reddet.

### Deney S1 — Scorer sabit kapsamda seçimi iyileştiriyor mu?

**Soru.** Donmuş bir Candidate evreni verildiğinde, öğrenilmiş bir skor ekonomik seçimi iyileştiriyor mu?

**Kollar.** Rastgele sıralama; deterministik kanıt skoru; yalnızca-maliyet skoru; yerel model olasılığı/tepkisi; lojistik koşullu-kayıp modeli; sığ ağaç; SELE'den ilham alan ikili kayıp-sıralama modeli.

**Protokol.** Önceden seçilen %10/25/50/75/100 gibi sabit kapsamlarda ve ekonomik olarak seçilen bir çalışma kapsamında değerlendir. Her skor özdeş Candidate'ları ve kabul edilebilir feature'ları görür. Eşik kalibrasyonu yalnızca yuvarlanan eğitim/kalibrasyon pencerelerinde gerçekleşir.

**Birincil sonuç.** Çalışma kapsamında kurallı maliyet-sonrası faydada eşleştirilmiş fark. Fayda–kapsam ve risk–kapsam eğrilerini raporla, ama donmuş OOS üzerinde en iyi kapsamı seçme. İkincil sonuçlar: koşullu kaybın kalibrasyonu, belirsizlikle beklenen kalibrasyon hatası, kuyruk kaybı, ciro/maliyet, elde edilen kapsam ve varlık/rejim bazında istikrar.

**Kabul.** Eşleşen kapsamda deterministik kanıt üzerinde tekrarlanan kronolojik OOS kazancı, istikrarlı kalibrasyon ve kabul edilemez alt-grup/kuyruk bozulması olmadan. "Daha az trade" tek başına başarısızlıktır.

### Deney N1 — `NO_TRADE` hedefini seç

**Soru.** Hangi açık çekimserlik formülasyonu V8'in ekonomisiyle eşleşiyor?

**Kollar.** Önceden kayıtlı çekimserlik maliyetli maliyet-bazlı kural; net-kayıp tavanına bağlı olarak kapsamı en üstleyen sınırlı-risk kuralı; minimum aktivite oranının üzerinde net kaybı en aza indiren sınırlı-kapsam kuralı. Mümkün olduğunda aynı skor sıralamasını kullan; böylece test çalışma-noktası politikasını izole eder.

**Metrikler.** Kapsam, seçici net kayıp/fayda, reddedilen kârlı Candidate'ların fırsat maliyeti, reddedilen kötü Candidate'lardan önlenen kayıp, ciro, kuyruk drawdown katkısı ve neden-kodu dağılımı. OOS'tan önce sabitlenen ekonomik olarak savunulabilir bir ızgara üzerinde maliyet duyarlılığını raporla.

**Kabul.** Seçilen kural, önceden bildirilen maliyet aralığında ve kronolojik replikasyonlarda kabul edilebilir kalmalıdır. Çalışma noktası istikrarsızsa, deterministik kapalı-başarısız kuralları koru ve öğrenilmiş bir `NO_TRADE` eşiğini terfi ettirme.

### Deney N2 — Öngörülebilirlik meta-kapısı rakibi

**Soru.** Ex-ante durum yapısı, Candidate sonuç riskini varlıklar/rejimler arasında sıralayabilir mi?

**Tasarım.** Inácio ve arkadaşlarını uyarla: yuvarlanan-köken sonuçları; yalnızca PIT feature'ları; varlık-içi ya da eş-değer-grup-içi yüzdelik hedef artı mutlak-fayda hedefi; gruplu katlar; yalnızca daha erken hedef gözlemlerini kullanan nedensel uyarlamayla ardından sıfır-atış varlık/rejim değerlendirmesi.

**Baselinelar.** Durum-kalitesi kuralı, son kalıntı ölçeği, meşru üretildiyse tahmin-aralığı genişliği, deterministik kanıt, rastgele ve oracle (yalnızca teşhis).

**Vetolar.** Meta-feature'larda gerçekleşmiş ufuk verisi kullanımı yok; sessiz hedef-alanı ince ayarı yok; sıra korelasyonundan kalibre edilmiş belirsizlik iddiası yok. Sıfır-atış/uyarlanmış performans deterministik kanıtın altına düşerse ya da kazançlar yalnızca yüksek-volatiliteli kârlı olayları bastırmaktan geliyorsa reddet.

### Deney N3 — Conformal teşhis

**Soru.** Bir conformal küme-değerli sınıflandırıcı, yararlı, ampirik olarak istikrarlı pozitif singleton kararları üretebilir mi?

**Tasarım.** Etiketleri kurallı simülatör altında tanımla; ayrı kalibrasyon penceresi; pozitif singleton → uygun, negatif singleton → açık negatif, boş → yenilik/geçersiz-durum `NO_TRADE`, çift → belirsizlik `NO_TRADE`. Çevrimiçi, çevrimdışı ve toplu-güncelleme formüllerini doğru izle.

**Metrikler.** Ampirik singleton hatası, kabul kapsamı, boş/çift oranları, aralık/küme boyutu, kalibrasyon boyutu ve zamansal blok bazında hata. Eşleşen kapsamda düz skor eşiğiyle karşılaştır.

**İddia disiplini.** "Dağılımdan-bağımsız"ı yalnızca kesin değişebilirlik/geçerlilik teoremi uygulanan diziye uygulanıyorsa kullan. Aksi halde conformalize ampirik seçim olarak tanımla.

### Deney T1 — Kuyruk silinmesi olmadan seçici eğitim

**Soru.** Eğitim-zamanı zaman-adımı maskelemesi, nadir-olay duyarlılığını yok etmeden bir Expert'i iyileştiriyor mu?

**Kollar.** Maske yok; rastgele maske; belirsizlik maskesi; anomali maskesi; çift maske. Oranlar yalnızca eğitim katlarında sabitlenir/ayarlanır.

**Metrikler.** Ortalama tahmin kaybı, Candidate faydası, kalibrasyon, aşırı-hareket geri çağırımı, en-kötü-ondalık kaybı, kriz-penceresi performansı ve maskelenen gözlemlerin sayısı/sonucu. Aşırı-olay geri çağırımı ve düşüş faydası veto metrikleridir.

**Kabul.** Ortalama MSE ya da doğruluk iyileştirmesi yetersizdir. Yalnızca kuyruk/kriz metrikleri önceden kayıtlı eşitliksizlik (non-inferiority) sınırları içinde kalırsa ve ekonomik OOS faydası iyileşirse terfi ettir.

## İncelemenin ima ettiği gerekli kayıt eklemeleri

Her Expert değerlendirmesi ya da atlaması için, değerlendirme çalıştırmalarında `expert_id/version`, `market_state_id`, uygunluk, yerel kanıt skoru, varsa Router skoru/sürümü, çağrıldı/atlandı, atlama nedeni, hesaplama süresi ve karşı-olgusal çıktıyı sakla. Her Scorer/`NO_TRADE` kararı için skor, kalibrasyon-penceresi tanımlayıcısı, eşik, hedef ve elde edilen kapsam, karar nedeni ve reddin belirsizlik, yenilik/veri kalitesi, risk ya da kapasite olup olmadığını sakla. Reddi yokluktan asla çıkarsama.

Expert-başına yük ve patlamalılık, atama istikrarı, Expert-çıktı örtüşmesi, değerli-Candidate yanlış negatifleri, grup-başına kapsam ve skor/sonuç sıralamasındaki sürüklenme için izleme ekle. Bunlar teşhislerdir; bileşen kabulü eşleştirilmiş OOS ekonomik sonuçlarına bağlı kalır.

## Referanslar

1. Siyuan Mu ve Sen Lin (2025). *A Comprehensive Survey of Mixture-of-Experts: Algorithms, Theory, and Applications*. [arXiv:2503.07137](https://arxiv.org/abs/2503.07137).
2. Danyang Zhang, Junhao Song, Ziqian Bi, Xinyuan Song, Yingfang Yuan, Tianyang Wang, Joe Yeong ve Junfeng Hao (2025). *Mixture of Experts in Large Language Models*. [arXiv:2507.11181](https://arxiv.org/abs/2507.11181).
3. Zixiang Chen, Yihe Deng, Yue Wu, Quanquan Gu ve Yuanzhi Li (2022). *Towards Understanding Mixture of Experts in Deep Learning*. [arXiv:2208.02813](https://arxiv.org/abs/2208.02813).
4. Ka Man Lo, Zeyu Huang, Zihan Qiu, Zili Wang ve Jie Fu (2024). *A Closer Look into Mixture-of-Experts in Large Language Models*. [arXiv:2406.18219](https://arxiv.org/abs/2406.18219).
5. Weilin Cai, Juyong Jiang, Fan Wang, Jing Tang, Sunghun Kim ve Jiayi Huang (2024). *A Survey on Mixture of Experts in Large Language Models*. [arXiv:2407.06204](https://arxiv.org/abs/2407.06204).
6. Referans 2'nin çift görünümü. [arXiv HTML:2507.11181v1](https://arxiv.org/html/2507.11181v1).
7. Albert Q. Jiang ve arkadaşları (2024). *Mixtral of Experts*. [arXiv:2401.04088](https://arxiv.org/abs/2401.04088).
8. Simone Scardapane, Alessandro Baiocchi, Alessio Devoto, Valerio Marsocci, Pasquale Minervini ve Jary Pomponi (2024). *Conditional computation in neural networks: principles and research trends*. [arXiv:2403.07965](https://arxiv.org/abs/2403.07965).
9. Leo Feng, Mohamed Osama Ahmed, Hossein Hajimirsadeghi ve Amir Abdi (2022/2023). *Towards Better Selective Classification*. [arXiv:2206.09034](https://arxiv.org/abs/2206.09034).
10. Vojtech Franc, Daniel Prusa ve Vaclav Voracek (2021; JMLR 2023). *Optimal strategies for reject option classifiers*. [arXiv:2101.12523](https://arxiv.org/abs/2101.12523).
11. Ricardo Inácio, Vitor Cerqueira, Marília Barandas ve Carlos Soares (2026). *Selective Time Series Forecasting via Metalearning*. [arXiv:2606.23448](https://arxiv.org/abs/2606.23448).
12. Yisong Fu, Zezhi Shao, Chengqing Yu, Yujie Li, Zhulin An, Qi Wang, Yongjun Xu ve Fei Wang (2025). *Selective Learning for Deep Time Series Forecasting*. [arXiv:2510.25207](https://arxiv.org/abs/2510.25207).
13. Johan Hallberg Szabadváry, Tuwe Löfström, Ulf Johansson, Cecilia Sönströd, Ernst Ahlberg ve Lars Carlsson (2025). *Classification with Reject Option: Distribution-free Error Guarantees via Conformal Prediction*. [arXiv:2506.21802](https://arxiv.org/abs/2506.21802).
14. Chong Zhang, Wenbo Wang ve Xingye Qiao (2017). *On Reject and Refine Options in Multicategory Classification*. [arXiv:1701.02265](https://arxiv.org/abs/1701.02265).
15. Harish G. Ramaswamy, Ambuj Tewari ve Shivani Agarwal (2015). *Consistent Algorithms for Multiclass Classification with a Reject Option*. [arXiv:1505.04137](https://arxiv.org/abs/1505.04137).

## Nihai karar çıkarımları

- **Router:** baseline'da yok olarak kalır. Literatür routing başarısızlık modlarını somutlaştırır ama V8 kabul kuralı O-004'ü karşılamaz.
- **Expert'ler:** küçük bir deterministik self-gating kümesi ve eşit-bilgili global karşılaştırıcı ile ilerle. Ekonomik uzmanlaşmayı Deney E1'e kadar kanıtlanmamış olarak ele al.
- **Scorer:** başlangıçta yok olarak kalır. Yerel deterministik kanıt zorunlu baseline'dır; öğrenilmiş koşullu-kayıp sıralaması, S1 altında daha sonraki bir rakiptir.
- **`NO_TRADE`:** onu açık, maliyetli, kalibre edilmiş, neden-kodlu ve denetlenmiş yap. Bir karardır, eksik bir olay değildir. OOS'tan önce maliyet/risk/kapsam çalışma kurallarını seç ve gerçek kapsam ile reddedilen fırsat maliyetini ölç.
- **Conformal ya da meta-öğrenme eklemeleri:** yalnızca deneyler. Ne dağılımdan-bağımsız sınıflandırma teoremi ne de düşük-frekanslı tahmin transfer sonuçları, bağımlı, durağan-olmayan trading verisi için bir üretim garantisi olarak içe aktarılamaz.
