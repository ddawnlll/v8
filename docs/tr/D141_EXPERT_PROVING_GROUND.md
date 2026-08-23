# D-141 — Expert Kanıtlama Alanı ve Alfa Arıtıcısı

**Durum:** `PROVISIONAL_DECISION / ÖNCE_YANLIŞLAMA / EKONOMİK_İDDİA_YOK`
**Yetkili otorite:** V8 Anayasası Kurallar 12, 18–27, 44–50; D-129, D-130, D-136, D-139, D-141.
**Kaynağa bağlı tasarım girdisi:** 2026-08-23 tarihinde sağlanan `D140_Expert_Proving_Ground_Research.html`; SHA-256 `28dd925c85c73cc66ccdfc1c0a0c99ac91d0c5ba1e26394f77faa6d8ff4c91d1`. Kaynak mimari önerir; V8 otoritesini geçersiz kılmaz ve ekonomik iddia yetkisi vermez.

## 1. Karar ve sınır

D-141, bir `ExpertWitness` sürümünün nitelendirme altyapısını kurar. Tanığın ilan edilen anlambilimi uygulayıp uygulamadığını, zaman-noktasına ve feature sınırlarına uyup uymadığını, ilan edilmiş gürültü dönüşümlerinde hukuka uygun davranıp davranmadığını ve bilinen kusurlarla yanlışlanıp yanlışlanamadığını ayrı ayrı cevaplar. Kârlılık kanıtlamaz, `OpportunityEpisode` yaratmaz, sermaye seçmez veya Expert'i terfi ettirmez.

Sentetik, üretilmiş, metamorfik, mutasyon, sabotaj, EAST ve tarihsel alegori girdileri yalnız Rust `#[cfg(test)]` nitelendirme harness'lerinde izinlidir. Runtime girdisi, evaluation manifest'i veya rapor üretim artifact'i olamazlar. Test kanıtı yalnız `SEMANTIC_QUALIFICATION`'dır ve `NO_ECONOMIC_CLAIM` üretmelidir. Gerçek-bantta zoraki-çekimserlik atfı, ayrı yetkilendirilmiş dondurulmuş kronolojik OOS kapısı sağlanmadıkça tanısaldır.

## 2. Dört düzlem sözleşmesi

| Düzlem | İzin verilen çıktı | Yasak güç |
|---|---|---|
| Spesifikasyon | Sürüm bağlı Davranış Kartı ve manifest | Mühürlü başarısızlıktan sonra spesifikasyonu geriye dönük uyarlamak |
| Nitelendirme | Senaryo, kahin, mutasyon, EAST, istatistik, passport makbuzu | Ekonomik veya sermaye iddiası |
| Atıf | Değişmeyen fırsat evreninde kayıtlı zoraki-çekimserlik farkı | Expert'in fırsat kimliği yaratması |
| Terfi | Ayrı frozen-OOS uygunluk girdisi | Geliştirme nitelendirmesini ekonomik destek saymak |

## 3. Yük taşıyan değişmezler

1. **Fırsat egemenliği:** Expert yalnız mevcut `OpportunityEpisode`'u gözlemler; onu yaratamaz, silemez veya yeniden anahtarlayamaz (D-129).
2. **Zamansal non-interference:** karar zamanına kadar eşit önekler, o zamana kadar bayt-eş karar ve makbuz üretir (D-139).
3. **Kahin bağımsızlığı:** Senaryo kahini, Expert fonksiyonunu içe aktaramaz, ona devredemez veya onu satır satır kopyalayamaz.
4. **Kanıt determinizmi:** taban-dünya hash'i, manifest, hipotez, algoritma/sürüm, seed, Expert/kod/referans sürümleri ve otorite yapılandırmasının aynı demeti aynı kanıt nesnesini üretir.
5. **Gizlenmiş sert hata yoktur:** gelecek okuması, yön terslemesi ve gizli durum gibi kritik sınıflar tam mutant imhası gerektirir.
6. **Uydurma kanıt yoktur:** mevcut olmayan kalibrasyon, sonuç, karşıolgusal veya risk verisi `None`, `NotApplicable`, `Unresolved` ya da `NO_ECONOMIC_CLAIM` olarak kalır.
7. **Tek sayı sertifikası yoktur:** Passport, otomatik terfi skoru değil; değişmez sonuçları ve metrik vektörlerinin birleşimidir.
8. **Test-only sentetik sınır:** sentetik senaryo fixture'ları, beklenen tutumlar ve makbuzları yalnız Rust test harness'i tarafından derlenir; production komutları bunları üretemez veya kalıcılaştıramaz.

## 4. Kanonik nesneler

`BehaviorCard`, kimliği; ekonomik olmayan mekanizma hipotezini; habitatı; setup/tetikleyiciyi; çekimserlik anlamını; simetriyi; geçersiz kılma/zaman aşımını; ilan edilmiş feature'ları; gürültü/sınır boyutlarını ve yasak bağımlılıkları bildirir.

`ExpertQualificationManifest` kartı Expert sürümüne, senaryo ailelerine, kahin sürümüne, seed'lere, istatistik kapılarına ve en yüksek otoriteye bağlar. `Scenario` hashlenebilir sonlu bir PIT dünyasıdır. `ScenarioOracle` bağımsız beklenen duruşu ya da ilişkiyi üretir. `QualificationRun` yürütmeyi manifest ve kod hash'lerine bağlar. `EvidenceObject` yalnız ilan edilen otoriteyi taşır. `ExpertPassport`, sonuçları tipleştirilmiş `EpistemicVerdict` halinde birleştirir.

## 5. Nitelendirme zinciri ve issue grafiği

```text
D141-001 -> 002 -> 003 -> 004 -> 005
                   \-> 006 -> 007 -> 008 -> 009 -> 010
                                             -> 011 -> 012 -> 013
                                                        -> 014 -> 015 -> 016 -> 017
```

| Dalga | Issue'lar | Çıkış artifaktı |
|---|---|---|
| I — Kanıtlama Alanı | 001–007 | BehaviorCard, ScenarioManifest, QualificationRun, CounterexampleBank, MutationReport |
| II — Epistemik Mahkeme | 008–010 | EvidenceObject, confidence/e-process sonucu, RiskCertificate, ExpertPassport |
| III — Alfa Arıtıcısı | 011–017 | MarginalContribution, DisplacementCost, InteractionMatrix, PromotionVerdict |

İlk pilotlar `failed_breakout`, `fib_projection_reversal` ve `liquidity_sweep_reclaim`'dır. Yayılım, pilotlar ilgili kapıları geçmeden genişlemez. Yetkili geçiş paydası 28 üyeli generator-expert dispatch tablosudur; `predicate` post-entry tez değerlendiricisidir, tanık değildir.

## 6. Senaryo, yeterlilik ve EWQ

Foundry; kanonik pozitif/negatif/sınır/metamorfik/null/koşullu/adversaryal/tarihsel tanı dünyalarını üretir. Kapsam yalnız ilan edilmiş hücrelerde hesaplanır:

`Coverage(E) = ağırlıklı ziyaret edilmiş zorunlu hücreler / ağırlıklı ilan edilmiş zorunlu hücreler`.

Her ilişki ön koşul taşır. İlan edilmişse fiyat-ölçek, LONG/SHORT ayna, alakasız-feature güvenlik duvarı, prefix non-interference, klon değişmezliği ve yürütme sırası permütasyonu zorunludur. Geçersiz girdi veya eksik ilan edilmiş feature, mevcut çekimserlik/no-habitat anlamına kapalı-başarısız düşmelidir.

Kritik mutant sınıfları tam imha ister. EAST geçerli ve makul karşı-örneği deterministik olarak küçültür; geçersiz dünyayı anlamlı hata saymaz. EWQ-01…10; manifest/kimlik, PIT, kanonik-negatif, metamorfik, mutant, kapsam, mühürlü challenge, istatistik, gerçek-bant atfı ve frozen OOS kapılarını sırasıyla korur. EWQ-09–10 ekonomik otorite vermez ve D-141 frozen OOS'u açmaz.

## 7. İstatistik ve ekonomik güvenlik duvarı

Eşleştirilmiş senaryo karşılaştırması, confidence sequence, e-process/e-value, çoklu test, eşdeğerlik/non-inferiority ve risk sertifikası yalnız varsayımları, durdurma kuralı, algoritma sürümü ve kapsamı manifestte bağlıysa kullanılabilir. Varsayım yoksa sonuç düşürülür; sayı uydurulmaz. Bu kanıtlar ekonomik sonuç çıkarmaz.

Zoraki-çekimserlik atfı, fırsat kimliğini korurken kayıtlı baz çizgi–müdahale farkını hesaplar. Kendi katkısı, ücret sürtünmesi, displacement, benzersiz yakalama ve ikili etkileşim tanıları, ayrı gerçek-bant ve frozen-OOS otoritesi olmadan terfi-uygun değildir.

## 8. OPEN_PIN tetikleyicileri

- İstenen istatistik için sabitlenmiş tahminci, varsayım veya referans vektörü yoksa.
- Kahin, değerlendirilen uygulamadan bağımsız olamıyorsa.
- Yeni davranış ailesinin yetkili Davranış Kartı yoksa.
- Bir ilişkinin Expert feature/venue anlamında geçerliliği belirsizse.
- Gerçek-bant verisi, müdahale anlamı veya frozen-OOS yetkisi yoksa.
- D-129, D-136 veya D-139 ile çatışma saptanırsa.

Her durum `BLOCKED / OPEN_PIN`'dir; alternatif mimari, sentetik ekonomik metrik veya sessiz varsayılan yasaktır.
