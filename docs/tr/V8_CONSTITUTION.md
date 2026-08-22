# V8 Anayasası v0.2 (CC-PROP-V8.3-GL-001 / CC-RES-V8.3-GL-001 ile Onaylandı)

1. V8 bir falsifikasyon programıdır, edge vaadi değildir.
2. Bir iddia `LITERATURE_SUPPORTED`, `PROJECT_EVIDENCE_SUPPORTED`,
   `DESIGN_INFERENCE`, `PROVISIONAL_DECISION`, `LOCKED_INVARIANT`,
   `OPEN_QUESTION` ya da `REJECTED_OPTION` olarak etiketlenir; etiketler asla
   birbirinin yerine kullanılmaz.
3. MarketState yalnızca karar anında gözlemlenebilir bilgileri içerebilir. Olay
   (event), bilgi (knowledge), kullanılabilirlik (availability) ve karar (decision) zamanı ayrı alanlardır.
4. **Ekonomik Nesne Ayrımı:** `MarketState`, `EconomicExposureStructure`,
   `OpportunityEpisode`, `ObserverEvidence`, `ReconciledOpportunityState`,
   `ExecutionCampaign`, `Order / Fill / Position` ve `Outcome` birbirinden ayrı,
   değiştirilemez kayıtlardır. Hiçbiri diğerinin vekili olarak kullanılamaz. Tüm
   terminal durumlar—sona erme (expiry), geçersizleştirme (invalidation), çekimserlik
   (abstention) ve reddetme (rejection) dahil—saklanır.
5. Eklenen her bileşen, önceden kayıtlı, maliyetlendirilmiş, donmuş
   out-of-sample bir karşılaştırmada kendisinden hemen daha basit olan
   deterministik taban çizgiyi yenmelidir.
6. **Minimum Tutarlı Mimari:**
   $$\text{PIT MarketState} \rightarrow \text{Fırsat Grameri} \rightarrow \text{Kanonik Fırsat Kitabı} \leftarrow \text{Expert Duruşları} \rightarrow \text{Kanıt Uzlaştırma} \rightarrow \text{Seçici Fayda} \rightarrow \text{Portföy Uygunluğu} \rightarrow \text{Yürütme Kampanyası} \rightarrow \text{Emirler/Dolumlar/Defter}$$
   Router, öğrenilmiş scorer, küresel ranker ve sertifikasız RL execution varsayılan olarak yoktur.
7. Kurallı (canonical) execution bir atıf (attribution) kontrolüdür; alpha ile
   execution'ın istatistiksel olarak bağımsız olduğunun kanıtı değildir.
8. Simülasyon seviyesi iddiaya uymalıdır. Desteklenmeyen dolum, kuyruk, gecikme
   ya da veri-kalitesi varsayımları kapalı-başarısız (fail closed) olur.
9. Çıktılar; kaynağı, evreni, kodu, konfigürasyonu, tohumu, simülatörü ve defter
   hash'lerini bağlar. Eksik bir otorite makbuzu ekonomik bir hükmü engeller.
10. Tarama (screening), replikasyon, terfi (promotion), shadow ve canlı izleme
    ayrı durumlardır. Sentetik testler sözleşmeleri kanıtlar, ekonomiyi değil.
11. Geliştirmede geniş keşfet; tüm arama ailesini raporla; çokluk kontrolleri ve
    dokunulmamış kronolojik değerlendirme kullan. Donmuş OOS üzerinde reddedilmiş
    bir hipotezi asla onarmaya çalışma.
12. V7'nin mevcut simülasyon otoritesi sertifikalı değildir. Bağımsız olarak
    yenilenene kadar V8 sözleşmeler ve doğrulama artefaktları oluşturabilir ama
    kârlılık, doğrulanmış execution ya da terfi ettirilmiş bir trading sistemi
    iddia edemez.
13. **Gözlemci Anayasası:** Bir Expert, sürümlenmiş bir epistemik gözlemcidir,
    ekonomik bir egemen değildir. Expert'ler gözlemleme, destekleme (support),
    çelişme (contradict), çekimser kalma (abstain) ve belirsizlik raporlama
    yetkisine sahiptir; ekonomik fırsat kimliği oluşturma, sermaye tahsis etme,
    pozisyon açma veya yürütmeyi zorlama yetkileri KESİNLİKLE YOKTUR. Her Expert
    `mechanism_family_id`, `behavior_family_id`, `expert_id`, `expert_version` ve
    varsa `variant_id` taşır.
14. **Karmaşıklık ve Çokluk Bütçesi:** (a) **Runtime:** Aktif gözlemci sayısı
    sınırsızdır; tek sınır hesaplama ve determinizmdir. Gözlemci sayısını artırmak
    fırsat sayısını, portföy ısısını, işlem sayısını veya sermaye hakkını mekanik
    olarak artıramaz. (b) **Kanıt:** Donmuş OOS'ta eşzamanlı iddia taşıyan davranış
    ailesi sayısı aile düzeyi çokluk düzeltmesine girer (Kural 11). Ortak scorer ve
    çapraz ranker'lar kesinlikle yoktur.
15. Öğrenme offline ve registry-kapılıdır. Sonuç verisi aktif bir Expert'in
    tanımını asla değiştirmez; yalnızca, terfiden önce donmuş bir OOS
    karşılaştırmasını ve registry incelemesini geçmek zorunda olan challenger
    sürümler üretebilir.
16. **Maruziyet Yapısına Dayalı Risk Kabulü:** Portföy kısıtları ham sembol stringleri
    veya Expert kimlikleri üzerinde değil, `ExposureStructure` tanımları üzerinde
    çalışır. Çakışan duruşlar karşı-olgusal takip ile çözülür veya reddedilir.
    Faktör kovaryans ısı tavanıyla birlikte portföy ölçeğini sınırlayan budur.
17. Araştırma materyalizasyonları tape'ten bir kez derlenir ve yeniden kullanılır;
    eğitim materyalize görünümleri okur ve yalnızca `OpportunityGrammar`,
    `ExposureMapping`, `ExpertHabitat`, feature, simülatör veya uzlaştırma tanımları
    değiştiğinde yeniden derler.
18. **Fırsat Egemenliği (Opportunity Sovereignty):** Ekonomik fırsat kimliği, onu
    gözlemleyen Expert'ten bağımsız olarak kurulur. Bir gözlem; üretici, sembol,
    strateji veya gözlemci çokluğu yoluyla tek başına ek ekonomik gerçeklik yaratamaz.
19. **Kimlik Anayasası:**
    $$\text{Sembol} \neq \text{Enstrüman} \neq \text{EkonomikMaruziyet} \neq \text{Fırsat} \neq \text{İşlem}$$
20. **Gözlemci Çokluğu Değişmezliği:** Bir gözlemcinin birebir veya kolineer
    kopyalarını ($E, E_{\text{klon1}}, \dots$) veya yinelenen veri akışlarını eklemek
    sıfır marjinal epistemik kanıt üretir; fırsat kimliğini, işlem sayısını ve portföy
    riskini kesinlikle değiştirmez ($N_{\text{eff}} = 1.0$).
21. **Habitat ve Asli Çekimserlik:** Bir Expert önceden kayıtlı bir habitat içinde
    çalışır. Kendi habitatı dışında veya yüksek epistemik belirsizlik altında
    varsayılan eylem `ABSTAIN` / `NO_TRADE`'dir. Sessizlik, cezalandırılmayan asli
    bir epistemik durumdur.
22. **Korele Tanıklar ve Kanıt Soykütüğü:** Her kanıt duruşu açık soykütüğü taşır
    (`observer_id`, `evidence_family_id`, `feature_lineage`, `data_lineage`,
    `habitat_version`, `dependency_group`). Ham oy sayımı yasaktır; kanıt
    birleştirme tanıklar arası bağımlılığı iskonto etmelidir.
23. **Yanlışlanabilir Fırsat Grameri:** `CanonicalOpportunity`, metafiziksel bir mutlak
    gerçeklik değil; operasyonel, sürümlenmiş, yanlışlanabilir bir ölçüm koordinat
    sistemidir. Sınır kimliği belirsiz olduğunda `UNKNOWN` geçerli bir durumdur.
    Zorla birleştirme veya bölme yasaktır.
24. **Fırsat $\neq$ İşlem (Maliyet Sonrası Net Ekonomik Değer):** Doğrulanmış bir piyasa
    fırsatı, ancak beklenen brüt marj tüm sürtünmeleri (spread, komisyon, fonlama,
    kayma markout'ları ve belirsizlik tamponu) aştığında yürütmeye kabul edilir:
    $$\mathbb{E}[\Delta \text{PnL}_{\text{net}}] = \text{BrütMarj} - \text{Sürtünme} - \text{BelirsizlikCezası} > 0$$
    Sürtünme altı kurulumlar kesinlikle `NO_TRADE`'e döner.
25. **Evren Genişleme Değişmezliği:** Sembol, borsa, enstrüman veya gözlemci eklemek
    arama ve kanıt uzayını genişletir; portföy kaldıracını, işlem sıklığını veya
    toplam riski mekanik olarak genişletmez.
26. **Hatalı Çöküş Koruması (False-Collapse Protection):** Farklı getiri yapısına sahip
    çok bacaklı geometriler, spot-vadeli (perp) temeli (basis), takvim spread'leri ve
    farklı borsa fiyat ayrışmaları `ExposureStructure` içinde bağımsız bacak
    kimliklerini korumalıdır; kaba tek-varlık yönlü bahislere indirgenemez.
27. **Anayasal Yanlışlanabilirlik:** V8.3 mimarisi zorunlu Değişmezlik Testleri
    (T1–T12) ve Ekonomik Kapılar (G0–G5) ile bağlıdır. Herhangi bir değişmezin
    başarısızlığı derhal bir mimari yenilgi sayılır; tolerans gevşetme veya test
    bükme kesinlikle yasaktır.

## Minimum Tutarlı Mimari

```text
sürümlenmiş zaman-noktası tape/durum
  -> Ekonomik Maruziyet / Fırsat Grameri
  -> Kanonik Fırsat Kitabı
     ├── Expert A -> Duruş (Support)
     ├── Expert B -> Duruş (Support)
     ├── Expert C -> Duruş (Abstain)
     └── Expert D -> Duruş (Contradict)
  -> Kanıt Uzlaştırma (Bağımlılık ve Kovaryans İskontolu)
  -> Uzlaştırılmış Fırsat Durumu
  -> Seçici Fayda Kararı (TRADE / NO_TRADE / DEFER)
  -> Portföy Uygunluğu & Faktör Kovaryans Bütçesi
  -> Yürütme Kampanyası (Çok Bacaklı & Basis Korumalı)
  -> Kanonik Emirler / Dolumlar / Pozisyonlar / Defter
  -> Önceden Kayıtlı Hipotez Laboratuvarı & Karşı-Olgusal Regret Küpü
```

Bu diyagramın ötesindeki her şey, ilgili registry deneyinin geçmesini gerektirir.

