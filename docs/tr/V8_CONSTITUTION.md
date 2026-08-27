# V8 Anayasası v0.3 — Kanıt Anayasası v2 (CC-BILL-V8.3-AUTHORITY-003 & CC-AMEND-V8.3-KAIZEN-004 ile Onaylandı)

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
28. **3 Boyutlu Otorite Tensörü:** Otorite tek boyutlu skaler bir merdiven değildir.
    Birbirine dik 3 eksende tanımlanır:
    $$\text{Otorite} = (\text{EvidenceAuthority}, \text{DecisionAuthority}, \text{RealizationStatus})$$
    burada:
    - $\text{EvidenceAuthority} \in \{\text{Counterfactual}, \text{ModelDerived}, \text{Observed}\}$
    - $\text{DecisionAuthority} \in \{\text{DiagnosticOnly}, \text{Reconciled}, \text{UtilityEligible}, \text{PortfolioAuthorized}, \text{ExecutionAuthorized}\}$
    - $\text{RealizationStatus} \in \{\text{Hypothetical}, \text{Simulated}, \text{Filled}, \text{CashflowSettled}\}$
    Yüksek bir karar yetkisi (ör. `PortfolioAuthorized`), bir iddiayı sırf bu nedenle epistemik olarak "gözlemlenmiş" veya "nakde dönüşmüş" kılmaz.
29. **Çıplak İddia Yasağı (No Naked Economic Claims):** İç hesaplamalarda `f64` serbesttir;
    ancak modül sınırını aşan, rapora giren veya kararı etkileyen hiçbir ekonomik değer çıplak
    taşınamaz:
    $$\text{ClaimValue}\langle T \rangle = \{ \text{value}: T, \text{authority}: \text{Authority}, \text{receipt\_id}: \text{ReceiptId} \}$$
    Her ekonomik iddia değişmez bir kriptografik makbuz taşımak zorundadır.
30. **6 Kanuni İddia Sınıfı ve ClaimRegistry:** Sistem, ajanlar ve raporlar yalnız 6 kanuni
    iddia sınıfına tabidir: `DIAGNOSTIC_SIGNAL`, `COUNTERFACTUAL_POTENTIAL`,
    `RECOVERABLE_REGRET`, `SIMULATED_CASHFLOW`, `REALIZED_CASHFLOW` ve `SUPPORTED_EDGE`.
    Her iddia merkezi `ClaimRegistry` siciline yazılır. `COUNTERFACTUAL_POTENTIAL` iddiasının
    `REALIZED_CASHFLOW`'a dönüşmesi hukuken ve mimari olarak imkânsızdır.
31. **Renderer Firewall ve Serbest Metin Yasağı:** Görselleştiriciler, dashboard renderlayıcıları
    ve rapor jeneratörleri serbest formatlama yapamaz. Tüm başlık ve niteleyiciler doğrudan
    sertifikalı `ClaimValue` tipinden türetilir. Yetkisiz `realized`, `profit`, `alpha`, `cashflow`
    kelimelerinin kullanımı derleme ve CI kapısında kesilir.
32. **Anayasal Muhalif Denetim & Audit-of-Audit:** Bağımsız denetçinin asli görevi onaylamak değil,
    iddiaları aktif biçimde yanlışlamaktır (`FALSIFY CLAIM`). Ekonomik yetkilendirme üç imza gerektirir:
    $$\text{Implementation Receipt} + \text{Independent Adversarial Audit Receipt} + \text{Verdict Receipt} \implies \text{Authorized Claim}$$
    Denetim mekanizmasının kendisi sürekli otomatik sabotaj testlerine (bozulmuş hash, sentetik sızıntı, klon şişirme, kayıp defter) tabi tutulur.
33. **Merkezi Egemen Kaizen:** `KaizenController`, tek egemen araştırma, deney ve hüküm otoritesidir.
    Alt sistemler, uzmanlar ve simülatörler yalnız gözlem telemetrisi yayar; normatif hükmü yalnız
    `KaizenVerdictEngine` verebilir.
34. **Yürütme Fiziği Cihazı Olarak USD-M:** USD-M motoru ve borsa simülatörleri bağımsız karar
    otoritesine sahip değildir; borsa mikro-yapı fiziğini (komisyon, fonlama, marjin, lot kuantizasyonu,
    kayma) sağlayan pasif birer laboratuvar cihazı (`ExecutionBackend`) statüsündedir.
35. **Anayasal Erişilebilirlik ve Donmuş Miras Yasağı:** Ekonomik iddiaya ulaşan tüm çağrı yolları
    Kaizen'den geçmek zorundadır (`SHADOW_AUTHORITY_PATH` P0 hatasıdır). Donmuş eski aday veya Python
    kodlarının üretimde import edilmesi derleme hatasıyla (`FORBIDDEN_LEGACY_IMPORT`) engellenir.
36. **Dört Düzlemli Kuvvetler Ayrılığı:** V8 yönetişimi kesin olarak birbirinden ayrılmış 4 kurumsal düzlemde yürütülür:
    $$\text{Anayasa} \implies \text{Merkez Komite / Yargı} \implies \text{Kaizen (Tek Yürütme Motoru)} \implies \text{İcracı / Ajanlar} \implies \text{Çift Girişli Defter}$$
    Merkez Komite politika ve teoriyi belirler; Yargı denetler ve yanlışlar; Kaizen orkestre eder; Ajanlar uygular; Defter gerçeği belgeler.
37. **Bağımsız İcra Teftiş Heyeti (Execution Oversight Corps):** Bağımsız Usul ve Teknik İcra Komiserleri, katı yetki sınırları altında icra süreçlerini denetler: `READ`, `TRACE`, `TEST`, `REPLAY`, `CHALLENGE`, `BLOCK` serbesttir; `WRITE PROD CODE`, `MERGE` ve `DECLARE SUCCESS` kesinlikle yasaktır.
38. **Kör Denetçi ve Epistemik Çeşitlilik Emri (A1 Düzeltmesi):** Ajan klonlarının sahte mutabakatını ($N_{\text{eff}} \approx 2$) önlemek için denetçiler, üretici ajanın akıl yürütme zincirinden (`CoT`) tamamen tecrit edilir (`Blind Protocol`). Homojen ajanların uzlaşısı delil niteliği taşımaz.
39. **Gerekçesiz Veto Yasağı ve Hızlı Temyiz (A2 Düzeltmesi):** Delilsiz veya soyut veto yasaktır (`No Naked Veto`). Her blokaj kararı, derlenebilir ve panic üreten somut bir Rust testine (`#[test]`) veya makbuz ihlaline dayanmak zorundadır. Haksız blokajlara karşı 1 turluk Hızlı Temyiz Heyeti kurulur.
40. **Kademeli Seferberlik ve Token Bütçesi Güvenlik Duvarı (A3 Düzeltmesi):** Denetim 3 kademede seferber edilir:
    - *Tier 0 (Rutin):* Primary Implementer + Otomatik CI testleri.
    - *Tier 1 (Materyal):* Primary Implementer + 1 İcra Komiseri + Otomatik Denetim.
    - *Tier 2 (Anayasal / İktisadi):* Tam Şûra (5 Komite Ajanı + Primary Implementer + 2 İcra Komiseri + Red-Team + Verdict Otoritesi).
    Her icra adımı değişmez bir Token Bütçesi ve Yönetişim Verimliliği makbuzu üretir.
41. **Kriptografik Anayasa Sürüm Kilidi & Kaizen Bağımsız Denetimi (A4 Düzeltmesi):** Her görev belgesi (`ExecutionMandate`), başladığı andaki `constitution_tree_hash` değerini kilitler. Kaizen kendi orkestrasyonunu kendisi denetleyemez; bağımsız anayasal yargı denetimine tabidir.
42. **Zorunlu 6 Bölümlük Red-Team Saldırı Tüzüğü:** Red-Team bir onay memuru değil; sistemi yıkmaya ve yanlışlamaya çalışan Popperian bir antikordur. Her teknik teftiş raporu şu 6 bölümü içermek zorundadır: (1) Savunulabilir En Güçlü Yön, (2) Çürütücü En Güçlü Teori / Ölümcül Açık, (3) En Yıkıcı 3 Çöküş Senaryosu, (4) En Gizli 3 Çürüme Riski, (5) Çalıştırılabilir Yanlışlama Testleri, (6) Muhalif Şerh ve Nihai Oy.
43. **Olağanüstü Mainline İcra Yetkisi ve Kapsam Güvenlik Duvarı (D-135):** Olağanüstü kriz durumlarında (P0 anayasal ihlal, PIT sızıntısı, nakit akışı/defter bozulması, pipeline felci, kritik tekrarlanabilirlik çöküşü), Kaizen `EMERGENCY_EXECUTION_STATE` ilan edebilir ve makine tarafından doğrulanan, süreli, tek kullanımlık bir `EmergencyMergeWarrant` düzenleyebilir.
    - *(a) Çıplak Push Yasağı:* Çıplak `git push origin main` kesinlikle yasaktır. Push işlemi; `incident_id`, `base_commit`, `constitution_hash`, `allowed_files` ve `rollback_commit` bağlayan geçerli bir kriptografik warrant gerektirir.
    - *(b) Main Push $\neq$ Başarı İlanı:* Acil mainline birleştirmesi yalnızca yangın söndürmedir; icracı ekonomik başarı veya `SUPPORTED_EDGE` ilan edemez.
    - *(c) Pre-Push Minimal Gate & Post-Push Full CI:* Push öncesi hızlı derleme, birim testler ve PIT/sentetik sızıntı doğrulaması zorunludur. Push sonrası Full CI ve Red-Team teftişi zorunludur.
    - *(d) İki Aşamalı Hotfix & Geçici Baş (Provisional Head) Karantinası:* Mainline hotfix'i onaylanana kadar `PROVISIONAL_HEAD` karantinasında kalır; post-push başarısızlığında derhal deterministik `AUTO_ROLLBACK` tetiklenir.
    - *(e) Sıfır Ekonomik Tuning:* Acil hotfix sırasında hiperparametre, eşik değeri, dağıtıcı veya kazanma oranı optimizasyonu kesinlikle yasaktır.
    - *(f) Asgari Semantik Delta & Tek Kullanımlık Tüketim:* Tek Olay, Tek İcracı, Tek Merge, Tüketilen Yetki (`warrant.consume()`). Geçici break-glass yazma yetkisi merge ile birlikte atomik olarak iptal edilir.
44. **Tam Metin Şartname ve Çıpa Değişmezi (`NO_UNANCHORED_SPEC_ACCEPTANCE` / D-149):**
    Her anayasa değişikliği, yasa tasarısı, mimari revizyon ve ratifikasyon adayı; `docs/` altında (`docs/contracts/`, `docs/charter/` vb.) eksiksiz ve sansürsüz TAM METİN (full-text) bir şartname olarak saklanmak ZORUNDADIR. Monograflarda, karar sicilinde veya PR açıklamalarında yer alan özetler, doğrudan `docs/` altındaki bu otoritatif tam metne link vermek ve çıpalanmak zorundadır. Tam metin şartnamesi `docs/` altına işlenmemiş hiçbir tasarı veya karar kabul edilemez ve ratifiye edilemez (`NO_UNANCHORED_SPEC_ACCEPTANCE`).
45. **Zamansal Müdahalesizlik ve Nedensel Kale (D-139):**
    Tüm piyasa gözlemleri, indikatörler, olaylar ve telemetri kesin zaman-noktası nedenselliğini sağlamalıdır ($X_{\le t} = X'_{\le t} \implies \text{Karar}_{\le t}(X) = \text{Karar}_{\le t}(X')$). `ChronosGate` veri diyotundan geleceğe sızıntı kritik bir anayasal ihlaldir.
46. **Yoğun Bar Serileri ve Ayrık Olay Tiplemesi (D-139):**
    Kısaltılmış indikatör vektörleri yerini $N$-bar hizalı `DenseBarSeries<T>` yapılarına bırakır. Fonlama ve açık pozisyon (OI) olayları ayrık seyrek olay akışlarında yer alır (`BarId != FundingEventId != DecisionTime`).
47. **Sıfır-İşaretçili Nedensel Çerçeve Yeteneği (D-139):**
    Karar mantığı yalnızca açık erişilebilirlik sınırlarına sahip değer-bazlı değişmez `CausalFrame` dilimlerini alır ($\text{Erişilebilirlik} \le \text{KararZamanı}$).
48. **Karşıt Sızıntı Mutantı %100 Yok Etme Oranı (D-139):**
    Çalışma zamanı sistemleri `leak-mutants/` paketine karşı (LEAK-001 - LEAK-012) doğrulanmış %100 yok etme oranını korumalıdır.
49. **İki Kademeli Yürütme Otoritesi (D-139):**
    `FAST_RESEARCH` yürütmesi yalnızca `DIAGNOSTIC_ONLY` yetkisi taşır; sadece geçerli `TemporalIntegrityCertificate` taşıyan `CERTIFIED_SIM` yetkili değerlendirmeye sunulabilir.
50. **PnL Renderer Güvenlik Duvarı (D-139):**
    Ekonomik render motorları, geçerli bir `TemporalIntegrityCertificate` taşımayan her türlü sertifikasız bandı veya simülasyonu reddeder.
51. **Politika Kimliği ve Delil Durumunun Zamansal Ayrımı ($\text{PolitikaKimliği} \neq \text{DelilDurumu}$ / D-150):**
    Bir politikanın kimliği yalnızca dondurulmuş kod hash'i ve konfigürasyon hash'i ile tanımlanır. Delil durumu zaman içinde yalnızca-ekleme, kriptografik olarak mühürlenmiş `EvaluationEpoch` snapshot'ları üzerinden evrilir. Geçmiş asla yeniden yazılamaz veya yerinde değiştirilemez.
52. **Geri Alınabilir Skaler-Olmayan Üretim Kanıt Sertifikası (D-150):**
    Sertifikalar mühendislik, anlamsal, araştırma, yapısal, ekonomik, fırsat, ileriye dönük ve gerçekleşmiş alanlardaki yasal iddiaları temsil eden çok boyutlu skaler-olmayan vektörlerdir. Tek bir sert yenilgi (defeater) baskındır ve sertifikayı iptal eder/düşürür; başarısızlığın kârlılıkla skaler olarak dengelenmesi veya ortalamaya yedirilmesi kesinlikle yasaktır.
53. **Geçişli Yenilgi Yayılımı ve Zorunlu Kaizen Devri (D-150):**
    Herhangi bir değerlendirme katmanında (sentetik ters-stres dahil) tespit edilen bir defeater, bağımlı iddiaları iptal etmek üzere geçişli olarak yayılır. Defeater'lar, iyileştirme amacıyla 8-alanlı kayıp atfı içeren değişmez `KaizenHandoffReceipt` aracılığıyla derhal Kaizen'e devredilir.
54. **Yetki Yükseltmeyen Salt-Okunur Otorite Projeksiyonu (D-150):**
    Güvence ve değerlendirme katmanları delilleri kesinlikle yetki yükseltmeyen salt-okunur `AuthorityProjection` üzerinden tüketir. Hiçbir değerlendirici veya güvence modülü doğrudan ekonomik iddia basamaz veya `ClaimRegistry`'yi değiştiremez.
55. **Sıralı İzleme Güvenlik Duvarı ve Zaman Açısından Geçerli Çıkarım (D-150):**
    Geleceğe dönük ve canlıya alınmış politikaların sürekli izlenmesi, çıkarımsal iddialar için zaman açısından geçerli e-süreçleri veya güven dizileri gerektirir. Tekrarlanan sabit-ufuklu p-değerleri veya anlamlılık testleri yalnızca teşhis amaçlıdır (`DIAGNOSTIC_ONLY`) ve yasal çıkarım yetkisi taşımaz.
56. **Soya Göreceli Holdout Yakımı ve Dünya Kapsam Çıpalaması (D-150):**
    Nitelendirme veya teşhis amaçlı kullanılan holdout verisi, o politika soyuna göre geri döndürülemez şekilde `BURNED_DIAGNOSTIC` durumuna geçer ve asla dokunulmamış OOS iddialarını karşılayamaz. Sağlamlık iddiaları, bir `WorldCoverageManifest`e açık kriptografik bağlama gerektirir.

## Minimum Tutarlı Mimari (Authority DAG)

```text
                      ANAYASA
                         │
        ┌────────────────┴────────────────┐
        │                                 │
  5 KALICI MERKEZ                       YARGI
  KOMİTE AJANI                            │
        │                       ┌─────────┴─────────┐
        │                       │                   │
        │                 İCRA TEFTİŞ           BAĞIMSIZ
        │                 KOMİSERLERİ           RED TEAM
        │
        ▼
  KARAR SİCİLİ
        ↓
      KAIZEN (Egemen Orkestrasyon)
        ↓
  EXECUTION MANDATE (Anayasa Hash Sabitli)
        ↓
 PRIMARY IMPLEMENTER (Kör Teftiş Denetimli)
        ↓
   İŞÇİ AJANLAR
        ↓
  BLAKE3 MAKBUZLARI + CLAIM REGISTRY
        ↓
 ÇİFT GİRİŞLİ NAKİT AKIŞI DEFTERİ (Korunum Değişmezi Doğrulanmış)
        ↓
 KAIZEN HÜKÜM MOTORU (Üç İmzalı Mühür: İcra + Denetim + Hüküm)
```

Bu diyagramın ötesindeki her şey, ilgili registry deneyinin geçmesini gerektirir.


