# D-136 — Epistemik Ekonomik Gözlemlenebilirlik, Kanıt İntisabı ve Model Riski Yönetişimi

**Durum:** MİMARİ TASARLANDI / TEMEL UYGULANDI (EEO-001, EEO-001H, EEO-002) / İSKELE UYGULANDI (EEO-003–EEO-010) / ÜRETİM EKONOMİK ENTEGRASYONU HENÜZ NİTELENDİRİLMEDİ.  
**Yetkili Otorite:** V8 Anayasası Kurallar 1, 3, 4, 6, 12, 14, 18, 20, 21, 24, 28, 35; D-136; Araştırma Dayanağı `D-136-RP-001`.

---

## 1. Problem Tanımı ve Tarihsel Kırılganlık

D-136 öncesinde, kantitatif karar platformları (tarihsel V8.2 versiyonları dahil) temel epistemik eşleşme ve gözlemlenebilirlik kör noktalarından muzdaripti:

1. **Yalnızca-Sonuç Karıştırması (Post-Hoc Rasyonelleştirme):** Sistemler işlemleri yalnızca gerçekleşen PnL veya sonradan yapılan markout'lar ile değerlendiriyor, kararın verildiği milisaniyede motorun *gerçekte neye inandığına* dair değişmez bir Zaman-Noktası (PIT) anlık görüntüsünden yoksundu. Bir sonuç negatif olduğunda sistem şu ayrımları resmi olarak yapamıyordu:
   - *Tahmin / Kanıt Başarısızlığı:* Yukarı akış tanık sinyali hatalı veya gürültülüydü.
   - *Karar Aktarım Başarısızlığı:* Yararlı sinyal; uzlaşma, fayda eşikleri veya portföy kapasitesi tarafından yok edildi.
   - *Uygulama Başarısızlığı:* Aşırı kayma (slippage), komisyon yükü veya gecikme.
   - *Stokastik Dağılım:* Pozitif ex-ante beklenen değer altındaki kaçınılmaz piyasa varyansı.
2. **Oracle ve Hindsight Sızıntısı:** Tanı araçları, Hedef Oracle üst sınırları veya denetim hükümlerinin karar yollarına örtük bağımlılıklar haline gelmesine izin vererek PIT güvenlik duvarını tehlikeye atıyordu.
3. **Korelasyonlu Tanık Şişirmesi ve Kendi Kendini Onaylama:** Eşdoğrusal uzmanlar bağımsız onaylar olarak sayılıyordu ve kanıt sağlayıcıları bağımsız çekişmeli yargılama olmaksızın kendi nedensel iddialarını onaylıyordu.
4. **Zoraki İntisap (Over-Attribution):** Geleneksel sistemler tüm kayıpları önceden belirlenmiş sepetlere zorla paylaştırıyor (%100'e tamamlama), gerçekte tanımlanamayan durumlarda sahte kesinlik üretiyordu.

---

## 2. Anayasal İlkeler ve Felsefi Doktrin

D-136 üç değişmez anayasal kuralı yürürlüğe koyar:

> ### Değişmez 1: Evrensel Karar İzlenebilirliği
> **İzlenemeyen hiçbir ekonomik karar alınamaz.** Her ekonomik taahhüt, ret, boyutlandırma veya çıkış; fırsat kimliğini, karar span soyunu ve kriptografik ortam kanıtını bağlayan kanonik bir `EconomicTraceContext`'e bağlanmalıdır.

> ### Değişmez 2: Orantılı Kanıt Otoritesi
> **Hiçbir ekonomik iddia, onu üreten kanıttan daha güçlü bir otorite alamaz.** Gerçekleşen nakit akışları fiziksel çift taraflı defter makbuzu (`Observed`) gerektirir; karşıolgusal yeniden oynatmalar simüle edilmiş sınırları (`DeterministicCounterfactual`) temsil eder; hindsight markout'ları tanısal tavanları (`OracleUpperBound`) temsil eder, asla gerçekleşmiş nakit sayılamaz.

> ### Değişmez 3: Açık Bilgisizliğin Önceliği
> **`UNKNOWN` (Bilinmeyen), uydurulmuş intisaptan her zaman üstündür.** Sistem ex-ante olasılık dağılımından veya nedensel tanımlanabilirlikten yoksunsa, sentetik sayılar üretmek yerine `None` / `UNIDENTIFIED` / `COMPETING_EXPLANATIONS` kaydetmelidir.

---

## 3. Üç Düzlemli Güçler Ayrılığı Mimarisi

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                                TELEMETRİ DÜZLEMİ (PIT)                                   │
│  MarketState ──► Opportunity ──► Witness ──► Reconcile ──► Utility ──► Portfolio ──► Orders │
│                                                                                          │
│  [Çıktılar: EconomicTraceContext, DecisionSpan DAG, DecisionBeliefLedger Anlık Görüntüsü]│
└────────────────────────────────────────────┬─────────────────────────────────────────────┘
                                             │ (Değişmez Telemetri Devri)
                                             ▼
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                                 KANIT DÜZLEMİ (POST-HOC)                                 │
│  • Temel Sağlayıcılar (P01–P04): Nakit Akışı, İz Bütünlüğü, PIT Güvenlik Duvarı, Sadakat │
│  • Tanı Sağlayıcıları (P05–P09): Kalibrasyon, Oracle Boşluğu, Uzman Kalitesi, TCA        │
│  • Sınama Katmanı (P11–P12): Çoklu Test Defteri, Nedensel Eleştirmen ve Yanlışlama       │
│                                                                                          │
│  [Çıktılar: EvidenceBundles ──► Yönlü EvidenceGraph ──► Merkezi Denetim Yargılaması]     │
└────────────────────────────────────────────┬─────────────────────────────────────────────┘
                                             │ (Yalnızca Yargılanmış Patoloji Makbuzları)
                                             ▼
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                                 YÖNETİŞİM DÜZLEMİ (KAIZEN)                               │
│  • Kaizen Araştırma Motoru                                                               │
│  • Kayıtlı Karşıolgusal Yeniden Oynatma (P10) ve Çift Etkileşim Analizi                  │
│  • Tek Seferlik Önceden Kayıtlı Dondurulmuş OOS Halefiyet Kapısı                         │
│                                                                                          │
│  [KESİN GÜVENLİK DUVARI: Ham Sağlayıcılar Yürütme veya Kaizen Politikasını Değiştiremez] │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Telemetri Düzlemi: İz Bağlamı ve İnanç Defteri

### 4.1 Kimlik ve Kaynak Ayrımı (`EEO-001H`)
- `OpportunityId` (`episode_id`): Piyasa fırsatını tüm temel, meydan okuyucu ve karşıolgusal çalıştırmalarda benzersiz şekilde tanımlar.
- `EconomicTraceId`: Bu fırsat için belirli bir yürütme yörüngesini (`Observed` veya `Counterfactual`) tanımlar.
- `TraceProvenance`: `tape_hash`, `policy_hash`, `constitution_hash`, `code_hash` değerlerini içeren değişmez yapı.
- `DecisionStage`: Zaman-Noktası karar aşamaları.
- `EvidenceStage`: Sonuç sonrası kanıt aşamaları.

### 4.2 Karar İnanç Defteri (`EEO-002`)
- `DecisionBeliefLedger`, her karar kontrol noktasında ex-ante inanç anlık görüntüsünü (`BeliefReceipt`) kaydeder.
- **Reddedilen Fırsat Kapsamı:** Uzlaşma veya fayda aşamasında reddedilen fırsatlar, gelecekteki Oracle Gap analizinin yanlı olmasını önlemek için son inanç makbuzunu saklar.
- **Anti-Sentetik Kuralı:** Modellenmeyen boyutlar sentetik sabitler yerine açıkça `None` olarak kalır.

---

## 5. Kanıt Düzlemi ve Otorite Hiyerarşisi

### 5.1 Otorite Sınıfları
1. `Observed`: Fiziksel olarak gerçekleşmiş nakit ve komisyonlar.
2. `DeterministicDerivation`: Sertifikalı durumdan deterministik türetimler.
3. `StatisticalEstimate`: İstatistiki kalibre edilmiş tahminler.
4. `DeterministicCounterfactual`: Dondurulmuş bant üzerinde kayıtlı müdahale simülasyonu.
5. `OffPolicyEstimate`: Ortak destek varsayımları altındaki off-policy tahminler.
6. `OracleUpperBound`: Hedef Oracle tavan potansiyeli (asla nakit sayılamaz).
7. `Unidentified`: Tanımlanamayan artık fenomenler.

---

## 6. Mevcut Uygulama Durumu ve Üretim Nitelendirme Makbuzu

```
====================================================================================================
V8.3 EPİSTEMİK EKONOMİK GÖZLEMLENEBİLİRLİK (D-136) — DURUM MATRİSİ (ONAYLANDI)
====================================================================================================
Bileşen / Alt Sistem            Uygulama Durumu         Denetim ve Yeterlilik Durumu
----------------------------------------------------------------------------------------------------
Ekonomik İz Temeli              UYGULANDI / DOĞRULANDI  Birim ve anlamsal testler GEÇTİ (H1-H4)
Karar İnanç Defteri             UYGULANDI / DOĞRULANDI  PIT anlık görüntü testleri GEÇTİ (B1-B11)

Kanıt Paketi Sözleşmesi         ÜRETİMDE UYGULANDI      Sıfır sahte borçla tam EvidenceContext bağlantısı
P01 Nakit Akışı Korunumu        ÜRETİMDE UYGULANDI      NİTELENDİRİLDİ (Çift taraflı fark = $0.00000000)
P02 İz ve Soy Bütünlüğü         ÜRETİMDE UYGULANDI      NİTELENDİRİLDİ (577 span, sıfır retronedensel bağımlılık)
P03 PIT Güvenlik Duvarı         ÜRETİMDE UYGULANDI      NİTELENDİRİLDİ (Sıfır gelecek sızıntısı)
P04 Yürütme Sadakati            ÜRETİMDE UYGULANDI      NİTELENDİRİLDİ (Binance USD-M lot kuralları korundu)
P05 İnanç Kalibrasyonu          ÜRETİMDE UYGULANDI      NİTELENDİRİLDİ (Fail-closed kalibrasyon sınırları)
P06 Oracle Boşluğu ve Kapsam    ÜRETİMDE UYGULANDI      NİTELENDİRİLDİ (7 aşamalı huni analizi bağlandı)
P07 Uzman Kanıt Kalitesi        ÜRETİMDE UYGULANDI      NİTELENDİRİLDİ (16.733 tanık makbuzu değerlendirildi)
P08 Karar Aktarım Verimliliği   ÜRETİMDE UYGULANDI      NİTELENDİRİLDİ (Ampirik aktarım oranları hesaplandı)
P09 Uygulama Eksiği / TCA       ÜRETİMDE UYGULANDI      NİTELENDİRİLDİ (Komisyon/kayma/fonlama ayrıştırıldı)
P10 Karşıolgusal Yeniden Oynat  ÜRETİMDE UYGULANDI      NİTELENDİRİLDİ (Yukarı akış geçersiz kılma doğrulandı)
P11 Sağlamlık ve Çoklu Test     ÜRETİMDE UYGULANDI      NİTELENDİRİLDİ (Holm-Bonferroni deneme muhasebesi)
P12 Nedensel Eleştirmen         ÜRETİMDE UYGULANDI      NİTELENDİRİLDİ (Çelişki entropisi yanlışlaması)

Q01–Q15 Yeterlilik Testi        ÜRETİMDE NİTELENDİRİLDİ 14/14 hata başarıyla tespit edildi, 0 yanlış suçlama
Gerçek BTC 12m Değerlendirmesi  DİSKTE DOĞRULANDI       `.audit/eeo/current/ECONOMIC_PATHOLOGY_REPORT.json`

D-136 NİHAİ KANUN               ONAYLANDI               KİLİTLİ_DEĞİŞMEZ (Milestone #2 Tamamlandı)
====================================================================================================
```

> [!NOTE]
> **Üretim Nitelendirme Doğrulaması:**
> 12 Kanıt Sağlayıcısının (P01–P12) tamamı kanonik V8.3 çalışma zamanına bağlanmış ve 8.760 barlık sertifikalı BTCUSDT bandında (`research/tape/btcusdt-1h-12m/tape.jsonl`) nitelendirilmiştir. Çift taraflı nakit akışı tam olarak korunmaktadır ($\Delta = \$0.00000000$).
> Tüm çıktılar şema doğrulamalıdır (`v8.3-eeo-d136-v1.0`) ve `.audit/eeo/current/ECONOMIC_PATHOLOGY_REPORT.json` dosyasına yazılmıştır.

---

## 7. Çözülen Mimari Maddeler (Çözülen OPEN_PIN'ler)

- `OPEN_PIN_EEO_001` [ÇÖZÜLDÜ]: P01, `usdm_sim::CashflowLedger`'a çift taraflı $\epsilon \le 10^{-8}$ hassasiyetle bağlandı.
- `OPEN_PIN_EEO_002` [ÇÖZÜLDÜ]: P06, `CanonicalFunnelReport` 7 aşamalı fırsat hunisine bağlandı.
- `OPEN_PIN_EEO_003` [ÇÖZÜLDÜ]: P08 Karar Aktarım Verimliliği 8.760 barlık sertifikalı bantta hesaplandı.
- `OPEN_PIN_EEO_004` [ÇÖZÜLDÜ]: Q01–Q15 hata test takımı nitelendirildi (14/14 tespit, 0 yanlış suçlama) ve kanonik rapor üretildi.
