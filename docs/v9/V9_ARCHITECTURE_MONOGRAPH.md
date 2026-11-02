# V9 — Market-Aware Adaptive Trading Intelligence

## Bilimsel mimari monografı · Model Council sonrası kapsamlı revizyon · V8-next evrim sözleşmesi

**Sürüm:** `V9-ARCH-RFC-1.1-REVISED`  
**Revizyon tarihi:** 2 Kasım 2026  
**Dil:** Türkçe; kod, araştırma başlıkları ve teknik sözleşmeler İngilizce kimliklerini korur.  
**Uygulama sınırı:** `ddawnlll/v8` → `v8-next/` (Python 3.12, NautilusTrader 2.0.0rc4; bu sürüm depoda pinlenmiştir).  
**Belge türü:** bilimsel mimari monografı + hakem revizyonu + normatif aday sözleşmeler; kod, ekonomik sertifika veya otomatik uygulama izni değildir.  
**Normatif durum:** **REVISED ARCHITECTURE TARGET / OWNER APPROVAL PENDING / UNVALIDATED POLICIES**. V8 Anayasası'nı veya geçmiş immutable kanıtları tek başına değiştirmez.  
**Kısa hüküm:** *V9, V8'in zaten mevcut olan MarketState–Opportunity–Expert–Execution anlayışını sürekli, bağlama duyarlı, açıklanabilir trader kararına dönüştürür; Pi Agent ile denetimli Kaizen, bu canlı karar çekirdeğinin yerine değil, onun dışında eklenir.*

> **Bilimsel dürüstlük bildirimi.** Bu çalışma, üç bağımsız kör Model Council değerlendirmesi ve revizyon sentezi ile kullanıcının ilettiği özgün V8 monografı, iki 2026 Deep Research raporu, araştırma handoff ZIP'i, D4 native raporu ve önceki bağımsız ham audit raporunu, erişilebilen GitHub kodunu ve doğrulanmış birincil akademik kaynakları sentezler. Bu belgede yeni bir backtest, sealed OOS sınaması, bağımsız çalıştırılmış V9 prototipi veya canlı işlem sonucu **üretilmemiştir**. Mevcut deneyler yalnız tanımlı BTCUSDT 1H geliştirme bandı ve test koşullarını temsil eder. Kanıt-iddia kapsamı kaynaklara sıkıca bağlı tutulur.

---

# Özet / Abstract

**Araştırma problemi.** Finansal piyasa koşulları durağan değildir; fırsat gözlemi, işlem seçimi, giriş fiyatı, sermaye işgali, pozisyonun sonraki yönetimi ve emir gerçekleşmesi birbirleriyle etkileşir. Bir sistemin çok sayıda uzman modülü veya ayrıntılı audit üretmesi, gözlemlediği değişikliklere doğru ekonomik tepki verdiğini göstermez. V8-next'in native keşif deneyleri, mevcut konsensüsün seçimde etkisiz kaldığı bir örneği; gecikmeli doğrulamanın ekonomik zararını; dinamik stop yönetiminin belirsiz fakat araştırmaya değer sonuçlarını; gerçek kalıcı fırsat durumunun tek başına ekonomik avantaj sağlamadığını ortaya koymuştur. Temel soru, **V8'in hangi yeteneklerinin daha tutarlı bir karar döngüsüne dönüşmesi gerektiği** ve bunun nasıl yanlışlanacağıdır.

**Yöntem.** Tarihsel mimari belgeleri kodla eşleştirildi; A/B/C/D4 yerel deneylerinin iddia sınırları ayrıştırıldı; piyasa rejimleri, çevrimiçi değişim tespiti, seçici tahmin, maliyetli yürütme, çoklu test ve otonom araştırma literatürü tarandı; tasarım sözleşmeleri, durum makineleri, güvenlik sınırları, test matrisi ve geçiş planı oluşturuldu. Kaynaklar *birincil akademik yayın / repoda gözlenmiş / yerel rapor / tasarım çıkarımı / açık soru* olarak etiketlendi.

**Öneri.** Tek ürün çekirdeği korunur: PIT market observations → world/market belief → canonical opportunities ← expert evidence → trader decision policy → price-aware entry/position/portfolio policies → hard risk guard → native NautilusTrader → audit + economic attribution → yeni gözlemle yeniden değerlendirme. İkinci, **çevrimdışı** katman Pi Agent ile hipotez üretir, mevcut research/evaluation/Oracle altyapısında test eder, GitHub Issue/PR üzerinden onaya sunar. Hiçbir LLM canlı trading risk kapısını atlayamaz.

**Sonuç statüsü.** Bu, *ekonomik edge'in kanıtı* değil, **test edilebilir hedef mimari ve daraltılmış uygulanabilir davranış sözleşmesidir**. Kabul, yalnız kontrol edilen davranışların ve ilgili ekonomik sonuçların yeni, geçerli deneylerle doğrulanmasına bağlıdır.

**Anahtar terimler:** market belief, non-stationarity, point-in-time, behavioral experts, opportunity sovereignty, selective decisions, native execution, endogenous occupancy, post-entry management, economic attribution, falsification, autonomous Kaizen, audit lineage.

---

# Hakem sonrası editoryal karar ve revizyon kapsamı

Üç modelin birbirinden bağımsız, **yalnızca monografı** okuyarak yaptığı kör inceleme aynı üst hükmü verdi: `PROMISING BUT REQUIRES REVISION` [C1–C3]. Bu raporlar kodun doğrulandığını veya eleştirilerin istatistiksel bağımsızlığını göstermez. Bulgular içinde belgenin kendi üzerinde gösterilebilen kusurlar ile bugünkü `v8-next/` kodunda gerçekten sürüp sürmediği bilinmeyen tarihsel audit sorunları ayrılmıştır. Kararların ayrıntılı izi [C4] sentezinde korunur.

**Bu v1.1 sürümünün kabul ettiği on temel düzeltme:** (1) sembolik ekonomik `argmax` üretim algoritması olmaktan çıkarıldı; (2) tek kanonik karar/niyet/venue olayı/neden sözlüğü ve izin matrisi tanımlandı; (3) baseline-equivalent `DecisionPolicyV0` algoritması yazıldı; (4) opportunity, intent, order ve position durumları ortogonal ayrıldı; (5) partial fill, cancel/replace, unknown venue ve restart için güvenlik kuralları kondu; (6) `MarketBelief` ölçülebilir, test edilmemiş bir view olarak sınırlandı; (7) yalnızca tarihsel artefakta ilişkin audit kusurları canlı implementasyon kusuru gibi gösterilmedi; (8) funding, fill ve mark otoritesi matrisi eklendi; (9) ilk deneyde aynı takvim equity, deneme ailesi ve karar değiştiren tek müdahale şart koşuldu; (10) Pi Kaizen çekirdeğin yanında, yetkisiz bir eklenti olarak korundu.

**Hakemlerden kısmen ayrıldığımız nokta:** İlk implementasyonda çalıştırılmayacak diye `Market Intelligence`, `Dynamic Position` ve `Portfolio` sorumluluklarını V9'un nihai vizyonundan çıkarmıyoruz. `TARGET_DESIGNED`, `INSTRUMENTED`, `MECHANICALLY_VALIDATED`, `ECONOMICALLY_EVALUATED`, `PROMOTABLE` durumlarını birbirine karıştırmadan ilerliyoruz. Başarısız deney mimari hipotezi reddedebilir; bir sınıfın varlığı ekonomik faydayı kanıtlamaz.

## Belge onayının beş ayrı düzeyi

| Düzey | Ne gerektirir? | Ne **sağlamaz**? |
|---|---|---|
| `ARCHITECTURE_ACCEPTED` | Owner tarafından karara bağlanmış hedef sorumluluklar | Çalışan kod |
| `MECHANICS_VERIFIED` | Pinned commit, deterministik fixture, native olay sınırı | Market edge |
| `EVIDENCE_QUALIFIED` | Geçerli veri, execution ve muhasebe kapsamı | OOS üstünlüğü |
| `ECONOMICALLY_SUPPORTED` | Tanımlı aile/ölçütle yeterli bağımsız karşılaştırma | Üretim yetkisi |
| `PRODUCTION_AUTHORIZED` | Ayrı güvenlik, operatör ve venue kabulü | Gelecek kâr garantisi |

Bu beş boyut tek `PASS` veya sayısal score içine sıkıştırılamaz. V1.1, ilk iki düzeye ulaşmak için gerekli davranış sözleşmelerini sunar; hiçbir düzeye ulaşıldığını **iddia etmez**.

---

# I. Araştırma soruları, kapsam ve kanıt hiyerarşisi

## 1.1 Birincil araştırma sorusu

> Gözlemleyip anlık emir açan bir sistem, piyasadaki değişimleri izleyen, kendi aktif görüşünü yeniden değerlendiren, fırsat ve pozisyonlarını devam eden bir ekonomik karar problemi olarak ele alan **adaptif trader** sistemine nasıl evrilir; bu gelişmenin gerçek değer kattığı nasıl ölçülür?

Bu sorunun yedi alt parçası vardır: (Q1) piyasayı doğru zaman sınırlarıyla nasıl temsil ederiz; (Q2) davranış temelli expert'ların marjinal değeri nedir; (Q3) fırsatın kimliği ve takibi emirden nasıl ayrılır; (Q4) karar bekleme/giriş/tutma/düzenleme/çıkışı nasıl ele alır; (Q5) portföy işgali karşı-olgusal seçimi nasıl etkiler; (Q6) sonuç nasıl güvenilir ölçülür; (Q7) Pi Agent bu sistemi yetkisiz kontrol etmeden nasıl geliştirir?

## 1.2 Kapsam dışı iddialar

Bu makale V9'un kârlı olduğunu; 28 expert'ın tahmin gücünün kanıtlandığını; rejim sınıflandırmasının getiriyi artırdığını; sürekli LLM kararının yararlı olduğunu; veri rejimlerinin sabit olduğunu; BTC sonuçlarının altcoin perpetual evrenine taşınabildiğini; funding, gerçek L1/L2 fill veya likidasyonların doğrulandığını **iddia etmez**. Ayrıca bir V9 canlı işletim sertifikası veya bağımsız hakemli yayın değildir.

## 1.3 Kanıt etiketleri

| Etiket | İçerik | İzin verilen yorum |
|---|---|---|
| `PRIMARY_LITERATURE` | DOI/arXiv üzerinden doğrulanmış dış çalışma | Yalnız çalışmanın popülasyonu, yöntemi ve varsayımları |
| `REPO_OBSERVED` | GitHub'da okunan gerçek kaynak/konfigürasyon | Kodun mevcut olması; bütün sistemin çalıştığını kanıtlamaz |
| `PROJECT_REPORTED` | Ham artifact, yerel run veya kullanıcı raporu | Raporlanan döneme ve profile özgü sonuç |
| `PROJECT_AUDITED_LIMITED` | Bağımsız ZIP üzerinde yeniden hesaplanan kontrol | Yalnız mevcut artifact ve bağlam kapsamı |
| `DESIGN_INFERENCE` | Bu monograftaki mühendislik önerisi | Ekonomik üstünlük iddiası yok |
| `OPEN / BLOCKED` | Yanıtlanmamış, ölçülemeyen veya geçersiz alan | Uygun koşul olmadan kullanılamaz |

## 1.4 Araştırma kaynakları

Yerel `index(3).html` V8 tarihsel tam monografı; Deep Research I (Kasım 2026, 92 KB metin) ve Deep Research II (Kasım 2026, 69 KB Markdown), `V8_NEXT_V9_RESEARCH_COMPLETE_HANDOFF.zip` (616 üyeli paket, orijinal run ve kanıtlar), `D4_ANSWER_TR.md`, `audit-20261030T223550Z-6ffc87e.zip` ve `v8_next_independent_raw_audit_review.md` bu araştırmanın birincil **proje** kaynaklarıdır. Belgelerdeki sayılar kaynaklarının zaman ve statülerine bağlıdır. GitHub varsayılan dalı, yerel olarak henüz push edilmemiş D4 araştırma modüllerini göstermeyebilir.

---

# II. V8'in özgün düşüncesi ve mimari hastalığı

## 2.1 Özgün tez: Expert bir trader değildir

V8 araştırma monografındaki temel ifade şu anlamı taşır: **MarketState, OpportunityEpisode, ExpertEvidence, ExecutionCampaign ve Order/Fill aynı ekonomik nesne değildir.** Market doğrudan gözlemlenebilir, PIT-zamanlı fırsat olayı yaratır; expert bu olayı gözlemler, destekleyebilir, çürütebilir veya çekimser kalabilir. Fırsatın kimliği expert sayısıyla çoğalmaz. Emre giriş, ayrı risk/utility kararıdır. Orijinal `V8_CONSTITUTION` bu ayrımları, duplicate observer invariance'ı, ilk-sınıf abstention'ı, immutable evidence ve locked OOS kontrolünü açıkça tanımlar [P1].

Bu miras **korunmalıdır**. V9'a taşınmaması gereken şey geçmişteki ağır komite/governance yüzeylerinin tümünü kopyalama zorunluluğudur. Her yeni karar için 5-agent kurul, farklı authority root, ikinci claim registry veya yeni engine yapmak, bu çalışmanın ölçülebilir amacına ters düşer. Eski anayasal hükümler korunup normatif geçiş gereken maddeler ayrıca sahibi tarafından onaylanmalıdır; bu tasarım belgesi geriye dönük yürürlük vermez.

## 2.2 Mimari boşluk: Bilmek → seçmek → yürütmek → yeniden değerlendirmek

V8-next'te `world/`, `experts/`, `opportunities/`, `risk/`, `economics/`, `adapters/`, `audit/`, `evaluation/`, `oracle/` ve `system_proving/` mevcut modüllerdir [R1]. Dolayısıyla piyasa durumu, fırsat, expert ve audit **eksik kavramlar değildir**. Açık boşluk, bu parçaların değişen piyasa koşullarında birbiriyle tutarlı **sürekli karar kontratı** üretip üretmediğidir.

V9'un mimari sıçraması daha çok sınıf, daha çok ajan veya daha çok kural değil: *taze market bilgisi → önceki görüşü güncelle → işlem niyetini seç → risk/kapasite kontrolü → native gerçekleşme → gerekçe geçerliliğini yeniden değerlendir*. Bu süreç pozisyon kapatıldığında değil, pozisyon açıkken de sürer.

## 2.3 Laboratuvardan ürün döngüsüne

V8 ekonomi ve kanıt altyapısı güçlü, fakat bugüne kadar tek bir `volume_confirmed_breakout` araştırma kampanyası gibi dar koşullarda testler öne çıktı. V9, yeni evrenlere / altcoin perps'e geçişi **ayrı veri ve likidite uygunluk aşaması** olarak tanımlar. Araştırma maliyetini azaltmak için önce hızlı sinyal/karar taraması, sonra yalnız final adaylarda native NautilusTrader replay'i kullanır. Hızlandırma hiçbir zaman replay semantiğini, stop sırasını veya maliyet modelini sessizce değiştiremez.

---

# III. Bugüne kadar ne ölçüldü? Empirik dayanak

## 3.1 Baseline: tanımı ve kapsamı

Raporlanan deney evreni: BTCUSDT Binance USDT-M perpetual, 1H, 2.160 bar, 2025-01-01–2025-04-01; tek 90 günlük **development** pencere; 10.000 USDT simülasyon sermayesi; maker 0.0002/taker 0.0005; %2 koruyucu stop/%4 hedef. 123 fırsat kaydedildi, baseline 45 kampanya açtı ve 44'ünü kapattı. Kapalı işlemlerde net −8,67470686 USDT ve ≈−0,02208R/işlem raporlandı; native komisyon toplamı ≈36,766 USDT; funding uygulanmadı. Bu 10.000 USDT gerçek portföy önerisi, 20 USDT'lik canlı hesap fizibilitesi veya sonradan oluşan veri değildir [P2, P3].

### A/B/C/D4 ayrıştırma özeti

| Araştırma sorusu | Gerçek gözlem | Geçerli çıkarım | İzin verilmeyen çıkarım |
|---|---|---|---|
| **A Expert seçiciliği** | Grammar-only A1 baseline defteriyle aynı; 123 fırsatın tamamı consensus desteği alıyor | Mevcut gate bu bandda ek seçim yaratmadı | Uzmanlık genelde faydasız |
| **B Entry** | Native B4 ~20 işlem, −0,14537 net R/işlem; bazı model gecikme kolları negatif | Basit onay/erteleme maliyet yaratabiliyor | Bütün giriş teyitleri kötü |
| **B3 realistic profile** | 11 giriş, G8 reconciliation bozuk, koruma eksiği | **INVALID**; ekonomik tabloya katılmaz | Bu rakamlar gerçek slippage'ı ölçüyor |
| **C4 +1R stop→BE** | 21 native protective-stop update; ~+0,14173 net R/işlem; eşleşmiş +0,1008R, GA [−0,0426,+0,2442] | İşlem yönetimi mekanik olarak değişti; sonuç **INCONCLUSIVE** | Kanıtlanmış breakeven edge |
| **D4 kalıcı retest/reclaim** | 123 watching, 65 armed, 25 girilen kampanya; net −0,04524R (defter), −0,08500R native-bracket; PnL −36,12 USDT | Gerçek kalıcılık var, fakat bu kural V8'i geçmedi | Bütün lifecycle politikaları gereksiz |

D4 ile V8 arasında ortak 12 opportunity için raporlanan D4−V8 farkı −0,91391R, %95 GA [−1,62986,−0,26449]; fakat aynı 123 fırsat üzerinden tüm-birim farkı −0,00130R, %95 GA [−0,17133,+0,16040]. Farklı karşılaştırma birimleri farklı sorular sorar; küçük ortak örnekleme dayanarak genel “zararlı” hükmü verilemez [P4].

## 3.2 D4'ün esas mekanizması: Seçim ile gerçekleşme ayrı

D4, V8'in açtığı 45 kampanyanın yalnız 12'sine girdi, 33'ünü kaçırdı; baseline'ın girmediği 13 fırsata girdi. Rapora göre ortak 12 fırsatta girişler ortalama 3,8 bar gecikti ve giriş fiyatı ortalama 0,68931R kötüleşti. 65 ARMED fırsatın 38'i `POSITION_OCCUPIED`, ikisi kapasite/sıra dolayısıyla iptal edildi [P4]. Bu, “daha iyi fırsat alt kümesi seçmek” ile “daha iyi portföy sonucu üretmek” arasındaki uçurumu somutlaştırır. Ancak D4'ün aynı kapanış MARKET ve bar-only semantiği gerçek piyasaya hazır değildir; funding eksiktir.

## 3.3 Audit doğruluğu: önemli bağımsız itirazlar

2026-10-30 ZIP'i üzerinden yapılan bağımsız inceleme, 89 native fill, 45 entry, 29 stop, 15 target ile ücret toplamlarının genel düzeyde uzlaştığını; ancak bazı audit artifact'lerinde **89/89 cashflow kaydının son kampanyaya etiketlenmesi**, 45 entry event'inde kampanya referanslarının yanlış/eksik olması, lifecycle opportunity/decision join bozukluğu, giriş mumundan sonraya görünmeyen high/low yolunun yanlış kullanılması ve `G7 PASS` ile eksik protection ID join'leri arasında çelişki bildirdi [P5]. Bu inceleme orijinal tape ve runtime olmadan ZIP düzeyinde yapıldığı için sorunların güncel koda hâlâ uygulanıp uygulanmadığı **yeniden doğrulanmalıdır**; otomatik olarak çözülmüş sayılmaz.

Bu düzeyde bir bağ kopukluğu `AUDIT_COMPLETE` etiketiyle örtülemez. V9'un **P0 başlangıç koşulu**, ilgili iddialar için `opportunity → decision → order → fill → campaign → cashflow` lineage bütünlüğünü native event seviyesinde kanıtlamak ve MFE/MAE'nin entry-time sınırlarını düzeltmek veya ölçümü geçici olarak `NOT_IDENTIFIABLE` ilan etmektir.

## 3.4 Mevcut açık ekonomik sınırlamalar

Funding akışı ve mark atfı; aynı-bar intrabar sıra; spread/quote/order-book/queue eksikliği; per-fill identity ve partial fill; native bracket/position ID callback order; altcoin likiditesi, minimum notional ve quantization; tek 90 günlük rejim; sealed OOS kullanımı. Bunlar farklı şiddette engellerdir. Birinin giderilmesi tümünü gidermez. Ayrıca geçmiş V8 next handoff ZIP'i D3'ün B4 replikasyonu olduğunu belirtir; D4 ise **daha sonra yapılmış ayrı çalışma** olup kendi 14/14 raporlanan doğrulamasına rağmen ekonomik üstünlük kanıtlamaz [P3, P4].

---

# IV. Bilimsel temel: piyasayı 'anlamak' ne anlama gelir?

## 4.1 Metafizik değil, güncellenebilir epistemik durum

Bir algoritmanın piyasayı 'anlaması', piyasanın geleceğini bildiği anlamına gelmez. Ölçülebilir tanım: **mevcut bilgiye dayalı sürümlenmiş piyasa görüşü** oluşturmak; bu görüşün geçerlilik alanını, belirsizliğini ve zaman sınırını belirtmek; yeni bilgi geldiğinde önceki kararın hâlâ uygun olup olmadığını sınamak. Bu, gözlemden aksi yöne ısrar etmek yerine `ABSTAIN`, `WAIT`, `REASSESS` gibi eylemleri birinci sınıf yapar. Seçici sınıflandırmanın risk–coverage değiş tokuşu bu tasarımın genel istatistiksel analojisidir; bilgisayarlı görü çalışmalarındaki risk garantileri finansal getiriye doğrudan aktarılamaz [L04, L05].

## 4.2 Zamanın dört ayrı anlamı

Her market/derived event için en az `event_time`, `exchange_publication_time` (varsa), `local_receipt_time`, `decision_time` ayrı tutulmalı. Eski candle'ın `bar_end` zamanı, geçmişte gerçek bilgiye erişildiğini kanıtlamaz. PIT bilgi kümesi

\[
\mathcal F_t = \sigma\{x_i: \operatorname{available\_at}(x_i)\leq t\}
\]

olmak üzere, belirli politika sürümü için `Action_t = π(F_t, Portfolio_t, PolicyVersion)` verisi ile tekrar üretilebilir olmalıdır. Retroaktif `funding`, `OI` veya dış veri eklemek, mevcut hipoteze yeni veri bilgisi kazandırıyorsa yeni dataset/version ve ayrı deney kimliği gerektirir.

## 4.3 MarketBelief: sınırlı ve yanlışlanabilir temsil

**İlk implementasyon varsayımı:** `MarketBeliefV0` yeni bir ontoloji, kalibre edilmemiş rejim olasılık motoru veya bağımsız karar otoritesi değildir; mevcut PIT `MarketState` üzerinden üretilen sürümlü bir **immutable view**dır. Hiçbir yeni belief değişkeni, varsayılan V8 giriş/çıkış davranışını kendiliğinden değiştiremez. Representation, prediction ve decision-utility ayrı araştırma hedefleridir.

```text
MarketBeliefV0  # PROPOSED; no implication of existing class
  instrument_id: String
  decision_cut_ns: Int
  source_event_ids: List[EventId]
  input_available_max_ns: Int
  market_state_ref: StateRef
  data_quality: VALID | STALE | INCOMPLETE | UNKNOWN
  volatility_context: Optional[VersionedObservation]
  structure_context: Optional[VersionedObservation]
  regime_labels: List[VersionedScore]  # NOT calibrated probabilities
  invalidation_events: List[EventId]
  measurement_version: ContentHash
  confidence_semantics: NONE | VALIDATED_MEASURE_ID
```

`trend`, `range`, `shock`, `transition` birbirini dışlamak zorunda olmayan **özelliklerdir**. Basitçe birim-toplamlı dağılım adı vermek matematiksel hata olur: kalibre edilmiş ve açıkça birbirini dışlayan olaylar olmadan `regime_distribution` alanı **yoktur**. Şok sırasında trend de olabilir. `confidence=0.91` gibi çıplak sayı yasaktır; confidence ancak neye ilişkin olduğu, referans olayı, penceresi ve validasyon verisiyle yorumlanır. Mevcut bar OHLCV'den çıkarılmış likidite proxy'si L1/L2 emir defteri olarak adlandırılamaz.

**Birincil ilk kullanım (`M1`):** Veri kalitesi veya açıkça önceden tanımlanmış volatilite koşulu altında yeni *girişin* ayrı bir kuralla reddedilmesi; `HOLD/EXIT` veya sermaye miktarı otomatik değiştirilmez. Aynı deneyde `baseline V8` / `raw-feature threshold` / `belief-view condition` karşılaştırılır. Yeni temsil her iki basit karşılaştırıcıyı geçemiyorsa **diagnostic-only** kalır.

**İkinci aşama:** İşe yarayan tek değişken kanıtlanırsa zaman içi stabilite, değişim algılama, multi-horizon etkileşim, kalibrasyon ve conditional outcome distribution ayrı family olarak araştırılır. Adams–MacKay [L01] yalnız aday change-point yöntemi; yararlı trading kararı kanıtı değildir.

## 4.4 Multi-horizon ve market state çevrimi

15m fırsat barı, 1h bağlam ve 4h durum gözlemi gibi saat ölçekleri kullanıcı hedefleriyle uyumludur; ilk doğrulama için mevcut 1H BTC enstrümanının dışına geçmek gerekmez. Çoklu ölçeklerde tamamlanmamış üst periyot mumlarını kullanmak `PIT` ihlalidir. `MarketBelief` güncellemesi, **relevant market event** veya karara etki eden risk/pozisyon değişikliği olduğunda; zorunlu her tick'te bütün expert'ları hesaplayarak değil, dependency invalidation ile uygulanmalıdır.

## 4.5 Değişim tespiti ve hata payı

Rejim tahminleri hatalı olabilir. False transition ile yanlış expert yönlendirmeyi önlemek için (i) `UNKNOWN` ve abstention; (ii) transition hysteresis/tutarlılık; (iii) minimum event/time validity; (iv) regime classifier karşılaştırması; (v) sınırlı drift/coverage monitor önerilir. Eşikler önceden sürümlenip test edilir; bu makale rakamsal optimum belirtmez.

## 4.6 Market understanding nasıl yanlışlanır?

Üç iddia testte ayrılmalıdır: `PIT_VALIDITY` (bilgi gerçekten karar anında var mı?), `REPRESENTATION_UTILITY` (etiket, aynı bilgiyle kurulan basit durumdan farklı test edilebilir koşullu davranış tanımlıyor mu?) ve `DECISION_UTILITY` (bu fark risk/pozisyon/execution sabitken ekonomik sonucu değiştiriyor mu?). Bir market belief'ın daha çok alanı olması hiçbiri için kanıt değildir.

Ön kayıtlı ilk koşullu hedef örneği: `future 1H absolute return > a × trailing ATR` gibi **gözlemlenecek olayın**, veri ufkunun ve eşiklerinin en baştan dondurulması; belirsizlik tahmini kalibre edilemiyorsa olasılık iddiası yok. Bilginin *eyleme etkisi* ayrıca `changed_action_count`, `avoidance_cost`, `calendar_aligned_net_equity_delta` ile ölçülür. Sadece tahmin skorundaki fark, trading aktivasyon izni vermez.

`M1` karşılaştırması dört karar verebilir: (i) hiçbir karar değişmez → temsil ekonomik karar girdisi olamaz; (ii) karar değişir ama ledger yetersiz → `INCONCLUSIVE`; (iii) ekonomi kötüleşir → `NO_EDGE` veya `REJECTED` (önkayıt kriterine göre); (iv) bağımsız geçerli sınama yeterli fayda verir → sınırlı politika promotion incelemesi. Farklı dönemlerde gözlenen farklı sonuçlar gizlenmez.

---

# V. Expert intelligence: uzmanların görüşü, hakikatin çoğalması değil

## 5.1 Kimlik ve rol

Expert bir *observer*dır; ekonomik opportunity ID üretmez, sermaye tahsis etmez, emir göndermez. `ExpertStance = {expert_id, version, habitat_id, opportunity_id, support/contradict/abstain, reason_code, observed_features, availability_bounds, lineage}`. Aynı kanıta dayanarak oy veren kopya expert'ların çoğunluk oluşturması bilgi üretmez. Orijinal V8'in clone invariance ve opportunity sovereignty ilkeleri korunur [P1].

## 5.2 Context-aware uzmanlık

Önerilen V9 davranışı: expert önce kendi habitatına uygunluğunu belirtir; uygunluk yoksa `ABSTAIN`. `MarketBelief` expert görüşü için ortak bilgi bağlamıdır, ancak **sabit ve yanlış olabilecek bir regime-router'ın expert'ları zorla susturması** varsayılan değildir. Yeni routing, consensus, confidence calibration veya learned scorer ancak mevcut self-gating baseline'a karşı testten sonra ekonomik karar yoluna alınır.

## 5.3 A deneyinden çıkarılan gerçek ders

Bir consensus gate'in 123 fırsatın 123'ünü geçirmesi, 28 expert'ın bütünüyle gereksiz olduğunu kanıtlamaz; yalnız o gate'in **marginal selection effect = 0** olduğunu gösterir. Bu durumda gereken, yeni 28 expert değil: gerçek `support/contradict/abstain` distribution, hangi fırsatı hangi model eledi, ablation ve dependency-adjusted evidence measurement. Ölçülecek metrikler: altered decision count, alternative coverage, incremental net equity, non-entry opportunity opportunity cost, regime-conditioned error; yalnız win rate veya consensus oranı değil.

## 5.4 Model çeşitleri

Rule-based, istatistiksel ve makine öğrenmeli expert'lar **aynı üretim sözleşmesine** bağlanabilir; buna izin verilmesi bunların tümünün etkin olduğu anlamına gelmez. Her modelin veri lineage, training split, calibration, uncertainty ve artifact hash'i vardır. Model sonuçları anlık gözlemlerle kendiliğinden yeniden eğitilmez; challenger policy olarak ayrı araştırma ve promotion gerektirir.

---

# VI. Opportunity Lifecycle: hafıza, strateji değil

## 6.1 Fırsat, karar, emir ve pozisyon ayrıdır

V8'in **opportunity sovereignty** ilkesini koruyan tek kanonik fırsat kaydı bulunur. Fırsatın epistemik durumu, emir ve pozisyonun gerçekleşmiş durumuyla **birleştirilmez**. İlk sürümün asgari fırsat durumları `DETECTED`, `ACTIVE`, `INVALIDATED`, `EXPIRED`; `WATCHING` ayrı bir gözlem etiketi olabilir, karar aksiyonu değildir. `ARMED/RETEST_SEEN` D4'e özgü araştırma policy state'leridir, default-on V9 yaşam döngüsü değildir. `ADMITTED/EXECUTED/CLOSED` opportunity enum'ları değil, ayrı decision/order/position ilişkilerinden türetilen görünüm olabilir.

Her fırsat `BirthSnapshot` immutable, sonraki `EvaluationSnapshot` append-only olur. `Expiry` fırsatın varlık hipotezinin sona ermesidir, emir iptali veya pozisyon kapanışı değildir. Canlı pozisyon, fırsat expired olsa bile kendi ayrı risk/protection güvenlik sözleşmesine tabidir. D4'ün kötüleşen fiyat ve occupancy sonuçları zorunlu gecikme eklenmemesi için pozitif gerekçedir [P4].

## 6.2 Decision-time re-evaluation

Aynı fırsatın doğuş anındaki kanıtları immutable `BirthSnapshot` olarak kalır. Sonraki market belief ve expert stances, ayrı `EvaluationSnapshot` olarak eklenir. Durum değişimleri tekrar oynatılabilir; cancel/expiry, fill sayılmaz. `OpportunityBook` fırsatın geçmişini tutar; **Entry Policy** o andaki fiyatın ekonomik olarak kabul edilir olup olmadığını hesaplar. Bir firmanın her fırsatı beklemeye alması veya her güncellemede emir açması gerekmez.

## 6.3 D4'e karşı tasarım savunması

D4 state machine gerçek ve baseline'dan farklı davrandı, ama −36,12 USDT'lik raporlanan sonuçla immediate girişe üstün gelmedi. Bu, `OpportunityBook`'un hafıza ve açıklama için değersiz olduğunu göstermez; **belirli retest/reclaim admission kuralının** ekonomik üstünlüğü desteklenmediğini gösterir. V9 fırsatı izlerken `WAIT` kararını ve `EXPIRED` fırsat durumunu ayrı kaydedecek; bekleme zorunluluğu ancak ayrı ekonomik politika ve kanıtla etkinleştirilecektir [P4].

## 6.4 Fırsat ile emir arasındaki tek yönlü güven sınırı

`Opportunity` veya `ExpertStance` doğrudan Nautilus order objesi üretemez. Emir istemi `TraderDecision` → `EntryIntent` → `RiskAdmission` → native adapter yolundan geçer. Her bağlantı `decision_id`, `opportunity_id`, `policy_hash` taşır. Fırsat sayısı, expert sayısı veya izlenen sembol sayısı artırıldığında toplam risk yetkisi otomatik büyümez.

---

# VII. Trader Decision Policy: çalıştırılabilir v0, araştırma hedefi vN

## 7.1 Dört farklı sözcük alanı: karar ≠ niyet ≠ olay ≠ gerekçe

Council'ın saptadığı `WAIT/WATCH`, `ADJUST/MODIFY` tutarsızlığı **bu revizyonda giderildi**. Aşağıdaki adlar V9 tasarımının önerilen **kanonik sözlüğüdür**, kodda şimdiden bulunduğu iddia edilmez. Eski adlar migration adapter'da dönüştürülebilir; ekonomi sözleşmesinde iki eşanlamlı eylem bulunamaz.

| Tür | Kanonik değerler | Sahip ve anlamı |
|---|---|---|
| `DecisionAction` | `WAIT`, `ENTER`, `HOLD`, `REDUCE`, `EXIT`, `ABSTAIN` | Versioned policy bir *karar* üretir; `ABSTAIN` gerekli girdiler/yetki bilinmediğinde öneri yoktur |
| `IntentKind` | `SUBMIT_ENTRY`, `CANCEL_ENTRY`, `AMEND_PROTECTION`, `SUBMIT_REDUCE`, `SUBMIT_EXIT`, `SAFETY_RECONCILE` | Bir kararın uygulanabilir alt isteği; emir değildir |
| `OpportunityStatus` | `DETECTED`, `ACTIVE`, `INVALIDATED`, `EXPIRED` | Fırsat gözlemi; eylem değil |
| `VenueOrderStatus` | `NOT_SUBMITTED`, `SUBMITTING`, `ACCEPTED`, `PARTIALLY_FILLED`, `FILLED`, `CANCEL_PENDING`, `CANCELED`, `REJECTED`, `EXPIRED`, `UNKNOWN_AT_VENUE` | Native order/event gerçekliği; yerel policy değil |
| `PositionStatus` | `FLAT`, `OPEN`, `REDUCING`, `CLOSING`, `UNKNOWN_AT_VENUE` | Venue ile uzlaştırılmış pozisyon durumu |
| `ReasonCode` | `NO_OPPORTUNITY`, `PRICE_UNFAVORABLE`, `STALE_DATA`, `RISK_LIMIT`, `POSITION_OCCUPIED`, `ENTRY_PENDING`, `VENUE_UNCERTAIN`, `PROTECTION_GAP`, `THESIS_INVALID`, `TIME_STOP`, `NOTIONAL_TOO_SMALL`, `ESTIMATE_UNKNOWN` | Denetim için açıklama, tek başına trade emri değil |

`WATCH` insan için fırsat izleme anlatımıdır; V9 karar aksiyonu değildir. `MODIFY`, `ADJUST`, `PROTECT` ve `TIME_STOP` yüksek seviyeli `DecisionAction` değildir: `AMEND_PROTECTION` bir niyet, `TIME_STOP` bir neden, `CANCEL_TARGET` bir alt intent olabilir. `REJECT` ise hangi katmanda reddedildiğine göre `RiskDecision.REJECTED` veya `VenueOrderStatus.REJECTED` olur. Bu terminoloji farklı nesnelerin durumunu tek enum'da şişirmeyi önler.

## 7.2 Otorite ve karar anı

Bir karar tetikleyicisi `completed_bar_available`, risk/event update, order event, position event veya açıkça tanımlı timer olabilir. **Decision cut** tekdüze (`decision_cut_ns`) ve veri erişilebilirliğiyle bağlıdır: her input için `available_at_ns <= decision_cut_ns`. Native `ts_event`, snapshot'ın erişildiği an yerine geçmez.

Önerilen değişmez akış:

```mermaid
flowchart TD
  MD[Available market / account / venue events] --> SF[Stable PIT decision frame]
  SF --> EV[Existing MarketState + MarketBelief view]
  EV --> OP[OpportunityBook and expert stances]
  OP --> DP[DecisionPolicyV0 or versioned challenger]
  PN[Reconciled native position, pending orders and confirmed protection] --> DP
  DP --> IN[Intent proposal]
  IN --> RG{Independent hard risk + state authority}
  RG -->|Allowed| NT[Nautilus native adapter]
  RG -->|Rejected| RE[Reasoned decision receipt]
  NT --> PN
  NT --> RE
  RE -. offline evidence .-> KA[Research and Kaizen extension]
```

`TraderDecision` hiçbir zaman native `Order`un gerçekleştiğini ilan edemez. Emir, pozisyon ve korumanın gerçek durumu Native adapter/venue reconciliation tarafından belirlenir. Hard risk, karar politikasından bağımsızdır. Aynı timestamp'li iki olay için veri kaynaklı `event_id`, tüketim sırası ve callback semantiği yoksa karar sırası biliniyor varsayılmaz.

## 7.3 Yasal eylem matrisi

| Reconciled state | Yasal politika kararı | İzin verilmeyenler | Güvenli sonuç |
|---|---|---|---|
| `FLAT`, no pending order, PIT valid, baseline opportunity qualified | `ENTER` / `WAIT` | `HOLD`, `REDUCE`, `EXIT` | Baseline niyeti ancak hard risk onayından geçer |
| `FLAT`, no qualified opportunity | `WAIT` | `ENTER` | No order; reason logged |
| `FLAT`, input stale / source unavailable | `ABSTAIN` | Yeni risk | No new entry; stale reason |
| `ENTRY_PENDING` veya `CANCEL_PENDING` | `WAIT` | İkinci entry, fill varsayımı | Venue reconcile; cancel sonucu henüz kesin değil |
| `OPEN`, verified protection | `HOLD` veya yetkili `REDUCE/EXIT` | Koruma kaybı; ikinci entry by default | Mevcut bracket korunur |
| `OPEN`, unverified / uncovered protection | `ABSTAIN` *policy plane* | Yeni risk, tahmini amends | Ayrı safety controller koruma/azaltma/reconcile uygular |
| `UNKNOWN_AT_VENUE` / restart | `ABSTAIN` | New entry, local-state assumption | Risk-blok + venue inquiry + operator notice |
| Kill switch / hard loss limit | `ABSTAIN` policy | Yeni risk artırımı | Risk controller'ın zorunlu risk azaltma prosedürü |

`WAIT` düz piyasa koşullarında aktif, meşru *no trade* kararıdır; `ABSTAIN`, hesap/venue/kanıt otoritesi yetersizliğinde ekonomik politika yargısının geri çekilmesidir. İkisi de istek atılmadı diye aynı nedenle raporlanmamalı.

## 7.4 V9 DecisionPolicyV0 — Baseline-equivalent çalıştırılabilir sözleşme

**Amaç:** V8'in native karar davranışını **değiştirmeden** yeni karar kimliği, neden, PIT kesiti ve olay tekrarlanabilirliği kazandırmak. Bu, mevcut kodda uygulanmış algoritma değil, repo-grounded acceptance sırasında V8'in karar fonksiyonuna bağlanacak normatif *aday prosedürdür*. İzin matrisi ve hard safety checks, mevcut baseline'da yanlışlıkla güvenlik boşluğu bulursa byte-equality zorlanmaz; bu sapma `SAFETY_REPAIR` olarak ayrıca belgelenir. Diğer durumlarda karar ve native fill eşdeğerliliği korunmalıdır.

```python
# PSEUDOCODE — cannot be placed in production unchanged.
def decide_v0(frame, baseline_v8, reconcile, risk):
    # Venue/protection safety does not wait for market-data validity.
    # frame contains a frozen PIT cut, policy/config hash and event IDs
    venue = reconcile.snapshot(frame.venue_sequence)  # observed, not guessed
    if venue.status_unknown or not venue.consistent:
        return receipt("ABSTAIN", reason="VENUE_UNCERTAIN", safety="RECONCILE")
    if risk.kill_switch_active or venue.exposure_limit_breached:
        return receipt("ABSTAIN", reason="RISK_LIMIT", safety="RISK_REDUCE")
    if venue.has_unverified_open_exposure:
        return receipt("ABSTAIN", reason="PROTECTION_GAP", safety="RECONCILE")
    if venue.entry_or_cancel_pending:
        return receipt("WAIT", reason="ENTRY_PENDING")
    if venue.has_open_position:
        # Existing verified static bracket remains sovereign, even if market data is stale.
        return receipt("HOLD", reason="BASELINE_PROTECTION_PRESERVED")
    if not frame.is_causally_valid or frame.market_is_stale:
        return receipt("ABSTAIN", reason="STALE_DATA")
    # Baseline is delegated exactly; no new EV, regime or price model used.
    proposal = baseline_v8.evaluate(frame.baseline_inputs)
    if proposal is None:
        return receipt("WAIT", reason="NO_OPPORTUNITY")
    approved = risk.admit(proposal, venue, frame.exchange_metadata)
    if not approved.ok:
        return receipt("WAIT", reason=approved.typed_reason)
    if not frame.stable_idempotency_key.is_unused:
        return receipt("WAIT", reason="DUPLICATE_DECISION")
    return receipt("ENTER", intent=from_baseline(proposal),
                   reason="BASELINE_ADMITTED")
```

**Not:** Bu psödokod `HOLD` halinde mevcut V8'in kurallı stop/target kapanışının Native engine tarafından çalışmasını engellemez. Baseline'da güvenli gerçek exit/stop kaynakları varsa bunlar ayrıca bağlanır. `risk.admit` ve `baseline_v8.evaluate` var olan API adları olarak **sunulmuyor**: uygulanırken mevcut kaynak fonksiyonlarına eşlenmelidir. `stable_idempotency_key.is_unused` kalıcı store/venue identity ile atomik sınanmalı; salt bellekte `set()` ve çağrı öncesi kontrol yarışa açık olur.

**Policy v0 kapsam dışı:** Calibrated EV, router, state-conditioned sizing, yeni bekleme politikası, otomatik rotation, otomatik stop amend ve streaming LLM inference. `HOLD` mevcut native protective orders'ın korunmasıdır; her bar yeni order oluşturma çağrısı değildir.

## 7.5 Karar kaydının değişmez alanları

```json
{
  "schema_version": "v9.decision.v0",
  "decision_id": "content-addressed-or-durable-id",
  "decision_cut_ns": "int64 from actual run",
  "source_event_ids": ["native-or-catalog-id"],
  "data_available_max_ns": "int64 from actual observation",
  "policy_hash": "sha256 of source and config contract",
  "market_state_ref": "immutable market-state pointer",
  "opportunity_id": null,
  "reconciled_venue_snapshot_id": "native snapshot reference",
  "action": "WAIT",
  "intent_ids": [],
  "reason_codes": ["NO_OPPORTUNITY"],
  "execution_authority": "DIAGNOSTIC_ONLY",
  "economic_estimate_status": "NOT_ESTIMATED",
  "safety_status": "VERIFIED_OR_NOT_APPLICABLE"
}
```

JSON içindeki metinler **şema örneğidir**, gözlenmiş run değildir. Üretim alanı zaman, hash, native order/client ID ile gerçek veri üzerinden doldurulmalı; `UNKNOWN` gizlenmemelidir. Bir `decision_id`, farklı hesap/venue snapshot altında rastgele tekrar kullanılamaz. Idempotency anahtarı `(strategy_id, policy_hash, account, canonical_opportunity_id, intent_revision)` ve native persisted client_order_id ilişkisiyle tanımlanır; kesin tuple uygulamadan önce gerçek NETTING/OCO semantiğine göre sınanır.

## 7.6 Öncelik, unknown ve eşitlik çözümü

Öncelik sırası: **(P0) exchange/venue gerçekliğini uzlaştır → (P1) kill-switch ve açık koruma bütünlüğü → (P2) açık fill/cancel/replace hareketini bitir → (P3) açık pozisyonu mevcut doğrulanmış statik kurallarla yönet → (P4) flat koşulda mevcut V8 baseline kararını değerlendir → (P5) new challenger kararını *yalnız deney bayrağı altında* sun.** Aynı anda tetiklenen olaylarda, at-most-once intent side-effect ve account-specific serial mutation garantisi verilir; pending venue order için yeni bağımsız intent açılmaz.

**Bilinmeyen ekonomik beklenti:** `expected_net_value=UNKNOWN` ise *yeni V9 utility-optimal allocation* açılamaz. Mevcut baseline'ın önceden onaylı mekanik koşullarını diagnostic veya yetkili mevcut deployment kontratı kapsamında taklit etmek `unknown EV = zero` varsayımı anlamına gelmez. Bilinmeyen liquidation distance ile canlı yeni risk açılmaz; diagnostic simülasyon ayrı etiketlenir. İki benzer ekonomik fırsatta edge-estimate yoksa **keyfi ID sırasıyla daha yüksek sermaye seçilmez**, mevcut baseline/occupancy politikası korunur.

## 7.7 Dinamik trader hedefi: ölçülebilir fakat şimdilik kilitli

Uzun vadeli hedef, ortak uygun ufuk altında tanımlanan aksiyon faydasıdır:

\[
Q_h(s,a) = \mathbb{E}[\Delta E_{t:t+h}\mid \mathcal F_t,a,\pi^{\mathrm{cont}}]
-\lambda\,\rho_h(s,a),
\qquad a\in\mathcal A_{\mathrm{admissible}}(s).
\]

Bu **araştırma hipotezidir**, çalışan v0 politikasının hesaplaması değildir. Önce ortak değerlendirme ufku `h`, continuation policy, equity/fee/funding tanımı, risk functional ve ajan dışı kalibrasyon prosedürü sabitlenmelidir. `\Delta E` zaten masraflar sonrası net equity ise spread, fees ve funding ikinci kez çıkarılmaz. `opportunity_cost` ancak aynı zamanda, aynı sermaye ve venue kısıtında ex-ante uygulanabilir alternatif tanımı varsa ayrıca raporlanır; keyfî skalar ceza değildir. `Q` hesaplanamıyorsa `NOT_IDENTIFIABLE`, optimizer yok. Uzun vadeli karar beyni bu deneysel ilkeyle gelişebilir; bugünkü kodmuş gibi anlatılamaz.

## 7.8 Karar sözleşmesi fixture seti

| Fixture | Başlangıç | Olay | Beklenen V0 karar / niyet | Kritik iddia |
|---|---|---|---|---|
| `DEC-001` | Flat, PIT valid, baseline opportunity true | Yeni completed bar | `ENTER` + baseline intent | Native parity; yeni EV yok |
| `DEC-002` | Flat, market stale | Yeni bar | `ABSTAIN`, no intent | Stale risk yok |
| `DEC-003` | Flat, no opportunity | Taze bar | `WAIT` | İzleme ≠ zorunlu entry |
| `DEC-004` | Entry submitted | Aynı bar duplicate signal | `WAIT/ENTRY_PENDING` | Bir order daha yok |
| `DEC-005` | Partial fill + open qty | Position update | `HOLD` ancak verified protection varsa | Kısmi exposure korunur |
| `DEC-006` | Venue timeout, order unknown | Retry | `ABSTAIN/RECONCILE` | Kör tekrar submit yok |
| `DEC-007` | Open protected position | Regime label flips | `HOLD` | v0 pozisyonu belief ile kapatmaz |
| `DEC-008` | Risk limit triggered | Entry opportunity | `ABSTAIN/RISK_LIMIT` | Expert risk override yok |
| `DEC-009` | Same bar replay duplicated | Same event ID | No second side-effect | Idempotency |
| `DEC-010` | Closed native stop, opportunity active | Fill callback | Reconcile, next valid cut | Fırsat ve pozisyon farklı durum |

Bunlar gerçek koda karşı tests/specification hâline gelecek **expected cases**dir, şu anda başarılı test raporu değildir.

---

# VIII. Entry & Order Management: gerçek durumun eşzamanlı nesneleri

## 8.1 Ayrım: fırsat kalitesi ≠ giriş kalitesi ≠ fill kalitesi

D4'te gözlenen 3,8 bar bekleme, daha kötü giriş fiyatı ve occupied fırsatlar; seçici görünen bir politikanın ekonomik açıdan iyi olduğu anlamına gelmediğini gösterir [P4]. Bu nedenle `EntryIntent`, **fırsatın kimliği** veya `OpportunityBook`un state'i değil, bir karar sonucu oluşturulmuş, süresi ve fiyat şartları olan typed istektir.

```text
EntryIntentV1 (PROPOSED):
  decision_id, opportunity_id, instrument_id, account_id
  policy_hash, exchange_metadata_hash
  side, requested_qty, allowable_price_bound, trigger_availability_ns
  expires_at_ns, order_kind, stop_basis_ref
  estimated_cost_status, submission_idempotency_key
```

`MARKET_NOW`, `LIMIT_WITH_TTL`, `SKIP_PRICE`, `SKIP_STALE` gibi seçenekler ayrı *entry-policy outcome/reason* olarak temsil edilir; `WAIT_BELIEF` kanonik `DecisionAction` değildir. `LIMIT_WITH_TTL` için price-touch tek başına fill ispatı değildir; maker queue, latency ve spread iddiaları veri/sim destek düzeyini aşamaz.

## 8.2 Üç ortogonal state machine

Üst düzey anlatı `INTENT→ORDER→POSITION` kolaylığı için çizilebilir ama **doğrusal yürütme** iddiası yanlıştır. Partial fill sırasında emir hâlâ kısmen açıktır; pozisyon ve koruma aynı anda vardır. Aşağıdaki makine ilişkileri eşzamanlıdır.

```text
INTENT:  PROPOSED -> RISK_REJECTED | APPROVED -> SUBMIT_PENDING
         -> NATIVE_ACK | UNKNOWN_SUBMISSION | SUPERSEDED
ORDER:   NOT_SUBMITTED -> SUBMITTING -> ACCEPTED -> PARTIALLY_FILLED
                  -> FILLED | CANCEL_PENDING -> CANCELED | REJECTED
         any uncertain state -> UNKNOWN_AT_VENUE -> RECONCILED
POSITION: FLAT -> OPEN(partial or full) -> REDUCING -> FLAT
               any uncertain state -> UNKNOWN_AT_VENUE -> RECONCILED
PROTECTION: UNNEEDED(flat) | REQUIRED(qty>0) | COVERED | GAP | REPLACING
```

`protection` ayrı bir doğrulanmış ilişki/görünüm olabilir; yeni bir network service olması gerekmez. `PositionStatus.OPEN` yalnız `ORDER.FILLED` sonrasında başlamaz; **ilk nonzero fill'den itibaren** açık miktar ve risk vardır. Koruma kapsamı `verified_reduce_only_qty >= exposed_qty` gibi kaba bir kuraldan daha zordur; aynı pozisyon için ters yönde stop/target çifte sayılması, margin/NETTING dönüşleri ve native order list semantics dikkate alınmalıdır. Gerçek değer, exchange native ID ve open qty ile hesaplanır.

## 8.3 Olay kimlikleri ve otorite

`decision_id`, `intent_id`, `client_order_id`, `venue_order_id`, `trade_id/last_trade_id`, `native_position_id`, `campaign_id` ve `cashflow_id` farklı kimliklerdir; aynı `ts_event` bağlayıcı anahtar değildir. `client_order_id → intent_id` doğum anında; `venue_order_id → client_order_id` native ack alındığında; `last_trade_id → order_id → campaign_id` her fill olayında kayıt edilir. NETTING position ID ile campaign ID ayrı kalır. Çoğulluk: 1 intent → ≥0 orders (retries/replacements), 1 order → ≥0 fill events, 1 position → birçok campaign event olabilir. Bu kardinaliteler denetlenebilir kayıt olmalıdır.

**Mülkiyet:** Policy yalnız niyet önerir; Risk Guard onaylar/reddeder; Native Adapter order mutasyonu yapar; venue'nin ACK/FILL/CANCEL/REJECT cevapları realized state'i günceller; Safety Reconciler riskteki açık pozisyonu bağımsız korur. Hiçbir `OrderSubmitted` kaydı `OrderAccepted` yerine geçmez.

## 8.4 Yarış durumları ve sınır koşulları

| Yarış / hata | Yasak kestirme | Asgari güvenli tepki |
|---|---|---|
| Entry submit timeout | "Emir gitmedi" varsayıp aynı order'ı yeniden yolla | Idempotent client ID ile venue sorgusu, belirsizlikte yeni risk blok |
| Cancel pending iken partial fill | Cancel success sanmak | Native fill'i işleyip exposure/protection güncelle, order status'u ayrı izle |
| Stop amend reject | Eski stop iptal edildi sanmak | Eski korumayı doğrula; gap oluştuysa safety workflow |
| Stop cancel/replace ile position closes | Yeni stop koymaya devam et | Confirmed qty/position identity ile stale amend iptal |
| Duplicate/reordered callbacks | Fill'i iki kere muhasebeleştir | Monotonic order version + dedup trade ID |
| Restart after disconnect | Local JSONL'i venue hakikati saymak | Account/venue positions + pending orders + cash yeniden oku, reconcile |
| Unknown protection status | Sadece `HOLD` ve sessizlik | Koruma/risk acil prosedürü, yeni risk yasağı, operatör uyarısı |
| TTL expiration | Cancel gönderince fill olmaz kabulü | ACK gelene kadar `CANCEL_PENDING`, geç fill'ler hesaplanır |

**Koruma invariantı:** Bilinen ve onaylanmış açık risk için, eski stop'un iptali ve yeni stop'un exchange tarafından kabulü arasındaki potansiyel boşluk tahminle kapatılamaz. Venue native atomic modify/replace destekliyorsa sürüme özel test edilecek; desteklemiyorsa yeni proteksiyon planı gerçekte oluşturulmadan eski korumadan vazgeçilmez *veya* safety controller'ın açıkça belgelenmiş risk azaltma prosedürü uygulanır. Bu, her venue ve OMS için farklı davranabileceğinden "atomik" olduğu varsayılmaz.

## 8.5 Restart / reconciliation protokolü

1. Strategy **yeni risk açmayı durdurur** ve current reconciliation epoch kaydeder.
2. Venue/account açık pozisyon, bekleyen emir, executed fills ve cash durumunu native API ile okur; zamanlar/source IDs saklanır.
3. Local intent/order/position history ile çift yönlü farkı çıkarır; orphan/misattribution belirler.
4. Açık pozisyonun qty/stop/target kapsamını doğrular. Belirsiz risk, `RECONCILIATION_BLOCKED`; yetkili risk azaltımı gerekiyorsa önceden tanımlı operasyonel playbook işler.
5. Tekrarlanmış event'lerin etkisizliği doğrulanır, yalnız uzlaşmış state sonrası yeni giriş tekrar açılır.
6. Persisted receipt'ler yeniden başlatmaya dayanır; sistem `UNKNOWN_AT_VENUE`yü sahte `FLAT`a dönüştürmez.

Bu algoritma **önerilen kabul sözleşmesidir**. Canlı ortamda güvenilir olduğu iddia edilmez; native NETTING/isolated margin + exchange incident testleri gerekir.

## 8.6 Execution fixture'ları

`ORD-001` one order N partial fills → qty sum ve per-fill fee doğruluğu; `ORD-002` cancel/fill cross → final qty doğru; `ORD-003` submit timeout → duplicate zero; `ORD-004` stop amendment REJECTED → protection false-PASS yok; `ORD-005` native STOP/target child relation → gerçek order IDs; `ORD-006` restart after accepted-but-unseen order → new risk blocked; `ORD-007` simultaneous stop/target with bar OHLC → STOP-FIRST yalnız sim policy, tarihsel gerçek değil; `ORD-008` native order sequence tied to exact NautilusTrader 2.0.0rc4; `ORD-009` mark/funding timestamp separation. Golden inputs ve beklenen etki, implementasyonda kendi üretici kodundan bağımsız hesaplanır.

**Düzgün API için ölçüt:** Bir piyasa olayını veya callback'i iki kez oynatmak para, emir ve risk yan etkisini çoğaltmamalıdır. Aynı timestamp ama farklı native trade ID'ler ise gerçekten farklı fill'ler olarak korunmalıdır.

---

# IX. Dynamic Position Management: sürekli değerlendirme, sınırlı eylem

## 9.1 Hedef ve mevcut kanıtın sınırı

V9 pozisyon açıkken piyasa değişimini gözlemlemeyi bırakmamalıdır. **Bu, her market-state güncellemesinde stop'u değiştirmek veya pozisyonu kapatmak anlamına gelmez.** Native stop güncelleme mekanikleri ve C4'te raporlanan 21 amend, bir davranışın mekanik araştırmasını destekler. C4 eşleştirilmiş tahmin farkı +0,1008R ve CI sıfırı kapsar; üstünlük kanıtı değildir [P3]. İlk v0 **mevcut statik bracket** davranışını korur. Dinamik policy default-off sürümlü challenger'dır.

## 9.2 Immutable PositionThesis ve reconciliation

`PositionThesis = {entry_decision_id, opportunity_id, entry_cut, entry_evidence_ids, policy_version, initial_risk_per_unit, initial_protective_stop, invalidation_rule_version}` başlangıç gerekçesinin **tarihsel kanıtıdır**. Sonraki görüş, immutable thesis'ı değiştirmez; `PositionEvaluationSnapshot` olarak eklenir. `position_qty`, native `avg_entry_px`, open reduction orders, confirmed stop, realized fill events ve funding liability **native gerçeklik**tir. İzleme anında gereken veri kesiti PIT'dir. Orijinal R paydası sonradan yeniden ölçeklenmez.

## 9.3 Dinamik aksiyonların tek anlamı

`HOLD`: mevcut korumanın ve native target/stop yolunun korunması; trade açma veya stop iptal anlamına gelmez. `REDUCE` ve `EXIT`: quantity-bounded intent ve hard risk admission gerektirir. `AMEND_PROTECTION`: yeni bir karar eylemi değil, önceden yetkilendirilmiş pozisyon policy'sinin alt intent'idir. `TIME_STOP` yalnız çıkış gerekçesidir. Orijinal stop'u uzaklaştırmak, hedef dışında risk büyütmek ve default-on sürekli amend yasaktır.

## 9.4 İlk test edilebilir dinamik challenger (P1)

Tek politika seçimi ön-kayıt gerektirir. Örnek aday: `BE_AFTER_FAVORABLE_EXCURSION_V1` (C4 ile ilişkili ama ondan otomatik türetilmiş geçerli edge değildir). Gerekli koşullar:

- Olay tetikleyicisi yalnız *tamamlanmış ve erişilebilir* fiyat veya verified native market event; intrabar MFE, ticari order fill'iyle aynı şey değildir.
- `original_R > 0`; referans ve stop yüzdesi değişmez. Eğer R tanımsızsa amend yok.
- `new_stop` current valid stop'a göre **risk artırmaz**, venue tick/step'e yuvarlandıktan sonra da değişiklik anlamlıdır.
- `cooldown_bars`, `minimum_stop_delta_ticks`, `max_amends_per_position`, `reentry_cooldown` sayıları development verisinden sonuç görülerek ayarlanamaz; **konfigürasyon sürümü ve preregistered planı** zorunludur. Bu makale optimum sayı icat etmez.
- `AMEND_PROTECTION` ile stopun exchange tarafından kabulü ayrı olaydır; reject, timeout ve partial fill yaratılan boşluğu otomatik `PASS`e çeviremez.
- Protection reconciliation korunmazsa durum `BLOCKED`; önceden tanımlı safety action uygulanır ve kayıt edilir.

Kıyas: aynı takvim, başlangıç sermayesi, giriş, ücret, funding, maliyet/fill ve risk koşullarıyla `static_bracket` karşısında *tek* challenger. `amends/trade`, `turnover`, trade count, marked equity, loss tail, protection-gap duration, occupancy, missed opportunities raporlanır. Yalnız matched winner R başarı ölçütü değildir.

## 9.5 Değişimin anlamlılığını ayıran iki sayaç

(1) `decision_reassessments`: her yeni etkin inputta açıklanabilir görüş güncellemesi. (2) `venue_mutations`: gerçek submit/cancel/amend/fill işlemleri. Çok sayıda değerlendirme, çok sayıda emir üretmek zorunda değildir. Churn ve histerezis eşikleriyle karar, niyet ve gerçekleşme ayrı ölçülür. MarketBelief titreşimi `range → transition → range` üretirse v0 `HOLD` değişmez; ilerideki position policy yalnız ayrı testle eylem üretebilir.

## 9.6 Position safety fixture'ları

`POS-001`: partial filled qty için confirmed stop coverage; `POS-002`: reject old-stop remains/cannot claim coverage; `POS-003`: stop amend + native fill race; `POS-004`: two consecutive identical belief events → no duplicate amendment; `POS-005`: adverse mark staleness → no risk-increasing amendment; `POS-006`: restart open position and missing protection → emergency reconcile; `POS-007`: original R denominator invariant; `POS-008`: dynamic off → native baseline semantic parity; `POS-009`: max amendments exceeded → `HOLD` with reason; `POS-010`: end-of-window open position marked equity. Bunların hepsi uygulanabilir golden fixtures, bugün geçmiş sayılan test değildir.

---

# X. Portfolio / Risk: kıt sermaye ve ex-ante alternatifler

## 10.1 İşgal olgusu, fırsat maliyeti tahmini değildir

D4'te `POSITION_OCCUPIED=38` ve iki kapasite reddi oluştu [P4]. Bu **hangi fırsatların reddedildiğini** kanıtlar; kabul edilselerdi net kazanç yazacağını kanıtlamaz. V9 v0, `blocked_by_position`, açık risk, candidate expiry, risk-conflict ve applicable quantity/venue constraints kayıtlarını tutar. Mümkün kılınmamış ikinci bir portföyün sonradan fiyat yolu üzerinden kazanılmış sayılması **gerçekleşmiş PnL değildir**.

## 10.2 İki ayrı miktar: factual exposure ve modeled alternative

| Ölçü | Kaynak | İşlem kararına etkisi (v0) |
|---|---|---|
| Factual occupied time | Native position/order timestamps | Raporla, baseline tek-pozisyon politikasını değiştirme |
| Factual available margin | Venue/account snapshot | Hard risk gating |
| Counterfactual trade opportunity | Frozen competing policy simulation | `SIMULATED_COUNTERFACTUAL`, realizasyon iddiası yok |
| Estimated opportunity cost | Ex-ante conditional model, time-aligned alternatives | **UNKNOWN** → rotation yasak; kendi başına allocator yetkisi yok |

Portföy alternatifleri ex-ante hesaplanacaksa aynı risk, sermaye, işlem maliyetleri, entry/exit fees, exposed time ve realized fill constraints korunmalıdır. Hindsight ile `best replacement` seçimi veri sızıntısıdır. Aynı simbolde NETTING, farklı altcoinlerde hedge/margin constraints ayrı senaryolardır.

## 10.3 Risk üstünlüğü ve 20 USDT fizibilitesi

Risk guard; equity/margin, max loss, kill-switch, liquidation distance, mark quality, venue minQty/minNotional, tickSize/stepSize, fee/funding buffer ve isolated mode varsayımlarını, politika ne önerirse önersin tekrar doğrular. `qty` step'e yuvarlanınca sıfır olursa `NOTIONAL_TOO_SMALL/QUANTITY_ROUNDS_TO_ZERO` bir **geçerli no-trade**dir. Küçük bakiye/kaldıraç daha yüksek EV üretmez. `liquidation_distance` eldeki bar verisiyle ve venue-specific account model olmadan kesin hesaplanamıyorsa `UNKNOWN`; canlı risk yetkisi doğmaz.

## 10.4 İlk allocator:

Herhangi bir öğrenilmiş ranker/rotation eklenmez. Mevcut `risk/admission`, `economics/allocation` ve native campaign logic korunur; telemetry çevresi genişler. **Aktif allocator için gerekli deney**: dondurulmuş ex-ante alternatife göre fiyat/kapasite/admission karşılaştırması, same-capital event-driven replay, ücret, funding, mark/equity, giriş gecikmesi, yeni risk açma ile mevcut pozisyonu kapatmanın opportunity cost'u; sealed OOS'a kadar default-off.

## 10.5 Birincil ekonomik karşılaştırma

Tanımlı geçerli takvim zamanlarında, açık pozisyonların doğru mark ile değerlendiği **net marked equity** birincil estimand'dır:

\[
\Delta_{\mathrm{portfolio}}
=\frac{E^{\mathrm{challenger}}_{t_1}-E^{\mathrm{challenger}}_{t_0}}{E_0}
-\frac{E^{\mathrm{baseline}}_{t_1}-E^{\mathrm{baseline}}_{t_0}}{E_0}.
\]

İki politika aynı `E_0`, `t0/t1`, contract universe, fee/funding, mark method, execution profile ve risk budget kullanır. Bağımlılığı koruyan `daily/weekly aligned equity increments` ikincil test örneklemi oluşturabilir; kesim sonu fark tek başına inference vermez. `Net return` ile business OPEX (varsa) ayrı raporlanır; business net trading net yerine geçmez. `avg net R per trade`, `per opportunity R`, `drawdown`, `occupancy`, `turnover`, `rejected notional` açıklayıcı ikinci çıktılardır.

---

# XI. Native execution ve claim-uyumlu veri / fill otoritesi

## 11.1 NautilusTrader mevcut canonical engine olarak kalır

`v8-next/` Python/NautilusTrader uygulama sınırıdır. Ek C++ matching engine, ikinci live OMS veya bütün trading kararlarını LLM'ye devreden agent framework'ü kurulmaz. Depodaki NautilusTrader sürüm pin'i 2.0.0rc4 olarak gözlenmişti [R2], fakat **local HEAD ve güncel pin** ikinci repo-grounded review sırasında tekrar kaydedilmelidir. Güncel `latest` dokümanındaki callback davranışı otomatik 2.0.0rc4 garantisi değildir. Historical exchange bar replay ile gerçek venue latency/queue aynı iddia türü değildir.

## 11.2 Execution profile authority matrix

| Profile (versioned) | Girdi / semantik | Neyi ölçebilir? | İddia yasağı |
|---|---|---|---|
| `BAR_SAME_CLOSE_DIAGNOSTIC` | OHLCV, aynı-kapanış MARKET varsayımı; kaynağa özel | Karar farklılığı, baseline parity, kaba benchmark | Elde edilebilir canlı fill, maker priority, stable net edge |
| `NEXT_OBSERVABLE_CONSERVATIVE` | Bar close sonrası gözlenebilir fiyat; explicit adverse slippage ve STOP-FIRST tie varsayımı | Varsayıma bağlı costed sensitivity; tam eşit native comparison | Gerçek intrabar sıra, kesin realized spread, actual venue queue |
| `TRADE_TICK_REPLAY` | PIT tick/trade stream + native fill version | Daha ayrıntılı trigger/order timing | Unseen queue priority / impact |
| `L1_BBO` | PIT bid/ask + trades/fill model | Quote-based spread bounds; selected market orders | Limit queue fill certainty |
| `L2_BOOK` | Timestamped depth/trades + explicit fill assumptions | Depth-based execution scenarios | L3 order-level exact priority, self-impact without evidence |
| `PROSPECTIVE_SHADOW` | Gerçek zamanlı observation + dry-run | Veri sürekliliği, karar/niyet davranışı | Gerçek private venue execution, portfolio realizations |
| `LIVE_VERIFIED` | Ayrı onaylı private account and reconciliation | Gerçek fill ve hesap sonuçları (izinli kapsam) | Gelecek kâr garantisi |

Profile bir kalite merdivenidir ama her profil otomatik üstün değildir; veri PIT kalitesi, instruments, mark/funding ve yerel engine state doğruluğu ayrı kontrol edilir. `BAR_SAME_CLOSE_DIAGNOSTIC` ile raporlanan ekonomi yalnız varsayımsal, **otoritesi sınırlı** sayılır; next-observable profile gerçek fill kanıtı da değildir. `B3` realistic profile reconciliations `INVALID` ise başarılı bir maliyet modeli gibi sunulamaz. STOP-FIRST ancak OHLC belirsizliğini modelleyen konservatif simülasyon politikasıdır, gerçek piyasa patikası değildir [T1,T2,P3].

## 11.3 Funding / mark / settlement olay modeli

`funding_rate_publication` (bilginin erişildiği an) ile `funding_settlement` (cashflow doğduğu an) farklı olaylardır. Her settlement kendi `rate_id`, `timestamp`, `mark/reference price`, `account position exposure just before settlement`, `cashflow_ref`, `native trade/position lineage` taşımalıdır. Gelen rate'in gelecekteki kapanıştan elde edilmiş fiyatla hesaplanması **PIT ihlali** olabilir; gerçek settlement atfı pozisyon o anda mevcut değilse geçmişe taşınamaz. Native funding simülasyonu var diye bizim kullanıcının replay'inde uygulanmış sayılmaz.

Eşitlik kontrolü (uygun instrument işaretiyle):

\[
\mathrm{Cash}_{t_1}=\mathrm{Cash}_{t_0}+\sum_{i\in\text{fills}}\mathrm{RealizedPricePnL}_i -\sum_i \mathrm{Fees}_i +\sum_{k\in\text{settlements}}\mathrm{FundingCashflow}_k +\mathrm{OtherDocumentedCashflows}.
\]

\[
\mathrm{MarkedEquity}_t = \mathrm{Cash}_t + \mathrm{UnrealizedPnL}_t
\quad (\text{in the account's explicitly declared accounting convention}).
\]

İşlem kayıtlarının mark/equity hesabı cross/isolated, collateral, settlement currency ve instrument multiplier'a duyarlıdır; bu yalın eşitlik bir **bağımsız test şeması**dır, bütün venue'ların birebir matematiği olduğu iddiası değildir. Realized/unrealized ve funding aynı maliyeti iki kere sayamaz. `MISSING_MARK` varsa uygun equity estimand `BLOCKED`, uydurulmuş mark ile kâr iddiası yok.

## 11.4 Realistic fill / fees qualification

`order_type`, `time_in_force`, `post_only`, `reduce_only`, `trigger_price_source`, `native version`, `latency_assumption`, `limit_touch_fill_rule`, `fee_schedule_version`, `slippage_rule` profile içinde hash ile dondurulur. `touched_price == filled_order` varsayımı maker için kabul edilmez. Kısmi fill farklı fiyat ve komisyonla ayrı kayıt; stop veya cancellation ACK belirsizliği hataya dönüşebilir. Asgari test, aynı fill tape üzerinde farklı emission order/pairing mutantlarının yanlış PASS üretmediğini göstermelidir.

## 11.5 Veri sınırı ve altcoin genellemesi

Basit 1H BTC development verisi, altcoin perpetual evrenindeki delisting, temporary suspension, tick/step updates, spread widening, mark anomalies, liquidation, funding frequency ve fill impact için veri değildir. Altcoin araştırması PIT universe membership, listing age, quote volume as-of, contract specs as-of, min notional, availability, data gaps ve survivorship farklarını kaydetmelidir. Başlangıçtaki 20 USDT senaryosu `FEASIBILITY_NOT_ESTABLISHED` olarak işaretlenir; bakiyenin tamamını risk etme veya yüksek kaldıraç, iyi karar kalitesiyle eşanlamlı değildir.

## 11.6 Aşamalı araştırma ekonomisi

PIT-cache → ucuz, **diagnostic-only** tarama → sınırlı DEV native sanity → tam native finalist → rolling validation → ayrı yetkili sealed final OOS → prospective shadow. Hızlı tarama, native fill varsayımlarını geçerliymiş gibi bildirmez. Tarama sırasında bakılan bütün varyantlar trial family içinde görünür; başarısız screening görünmez test sayılmaz.

---

# XII. Economic evidence, bağımsız audit ve bilimsel doğrulama protokolü

## 12.1 Tarihsel audit riski: mevcut kod için değil, artefakt için kesin konuş

30 Ekim 2026 tarihli ZIP üzerinde yapılan bağımsız artifact incelemesi, **o run'ın** `cashflows.jsonl` kaydındaki 89/89 campaign join'inin yanlış `C0045` ilişkisi taşıdığını; native entry callback'lerindeki 45 kaydın hiçbirinin doğru campaign'e bağlanmadığını; 45 lifecycle `decision_id` alanının null olduğunu; 0/45 fırsat eşleşmesi ve bazı tarihsel path-MFE/MAE çelişkileri bulunduğunu raporladı [P5]. Manifest hash'lerinin doğru oluşu **raporun semantik doğruluğu** değildir. Bu bulguların bugünkü local HEAD'te devam edip etmediği **bilinmiyor**; v1.1 bunları güncel bug kesinliği diye sunmaz.

**P0-AUDIT çalışma sırası:**

1. `repo_commit`, Nautilus sürümü, dataset hash, config/policy hash ve historical audit ZIP'i pinle; yerel HEAD ve D4 unpushed farklarını ayrı kaydet.
2. Historical ZIP için immutable defect matrix (F01–F08), raw offending IDs ve önceki gate statuslarını koru; artifact geçmişini düzeltip üzerine yazma.
3. Güncel native replay'de aynı ID ilişkilerini *yeniden ölç*: cashflow→fill→order→campaign; entry decision/opportunity join; protection child IDs; realized/unrealized cash accounting.
4. **Independent golden-oracle**: elle hesaplanmış iki campaign, aynı timestamp'te farklı client order ID, bir order ile iki partial fill, funding open vs closed exposure, stop/target ve kesim sonu açık pozisyon. Validator'ı üreten kodla aynı join helper'ından beklenen sonuç türetme.
5. **Fault injection**: yanlış fakat *tam dolu* campaign join, duplicated fill, missing funding event, stale mark, wrong child order ID, wrong time cut, missing protective order, synthetic target winner MFE=0. Her mutantın doğru sebeple reddedildiği kaydedilmeli.
6. Güncel kod başarısızsa kaynak/konfigürasyon ve testleri minimum scope ile düzelt; yeni run'ın gate statuslarını üret; daha önceki `PASS` iddialarını otomatik üst sürüme taşımadan superseding report yaz.

`orphan_count=0` gerekli olabilir, fakat **yeterli değildir**: bütün kayıtların yanlış `campaign_id`ye bağlanması sıfır orphan üretebilir. Native event'lerin kendi tekil kimliklerine ve bağımsız accounting oracle'a göre doğru mapping kanıtı gereklidir.

## 12.2 Audit'in dört bağımsız hükümleri

| Hüküm | Hangi soruyu cevaplar? | Standart başarısızlık |
|---|---|---|
| `MECHANICAL_VERDICT` | State, order/fill/stop/transition doğru mu? | `FAIL/UNKNOWN` |
| `ACCOUNTING_VERDICT` | Cashflow, funding, fee, mark, equity doğru mu? | `FAIL/BLOCKED` |
| `SCIENTIFIC_VERDICT` | PIT, baseline, family, sample ve OOS bağımsızlığı geçerli mi? | `INVALID/INCONCLUSIVE` |
| `PROMOTION_AUTHORITY` | Bu delil hangi ortamda hangi davranışı etkinleştirmeye yetkili? | `NOT_AUTHORIZED` |

Bu dört sonuç, mevcut gate isimleri (`G0–G9` gibi) ile adlarını zorla yeniden yazmak için değil **semantik sınır** için tanımlanır. Var olan `audit/pipeline.py`, `evaluation/gate_registry.py`, `evaluation/store.py`, `system_proving/` ve `oracle/utility.py` ile eşleme yapılır [R3]. Sürüm ve gate semantiği değişimi geçmiş receiptleri geriye dönük güncellemez.

## 12.3 Provenance bir DAG, tek bir lineer zincir değil

```mermaid
flowchart TD
  E[Market/venue event ids] --> S[PIT state snapshot]
  S --> O[Opportunity id]
  S --> X[Expert stance ids]
  O --> D[Decision ids]
  X --> D
  P[Reconciled position/account] --> D
  D --> I[Intent id]
  I --> N[Native client & venue order id]
  N --> F[Native fill trade ids]
  F --> C[Campaign/position relations]
  C --> A[Cashflow fees funding marks]
  A --> U[Marked equity & benchmark outcome]
```

Her karar birden fazla expert stance, bir order birçok partial fills, bir position birden fazla campaign event taşıyabilir. Beklenen cardinality ve unique key açıkça belirtilir. `campaign_id`, `native_position_id`, `symbol`, `opportunity_id` interchangeable değildir. `last_trade_id` tekrar ediyorsa cashflow double-count engellenir. Report producer ve verifier, aynı türdeki yanlış reference mapping'i paylaşarak sahte PASS üretememelidir.

## 12.4 Sonuç otoritesi: belge değil veri birinci sınıf

Her rapor şunları bağlar: input dataset hashes, PIT availability policy, source and config hashes, exchange metadata version, native engine and fill model version, starting equity, mark/funding coverage, branch/head sha, baseline comparison, family_id, all attempted variants, terminal no-trade outcomes, recognized missingness. Eksik alan `UNKNOWN/BLOCKED` taşır; sahte sıfır, sentetik p-value veya gerçek işlemmiş gibi counterfactual yazılmaz.

**MFE/MAE:** karar barının yüksek/düşük fiyatı girişten sonra yaşanmış sayılmaz; native fill zamanından önceki fiyatlar pozisyon patikasına eklenmez. Kapalı kazanan pozisyon için gözlenen exit price ile aritmetik olarak çelişen `MFE_R=0`, geçerli rapor olamaz. Yalnız completed bars ile intrabar ekstrem sırası kesin bilinmiyorsa `PATH_PARTIALLY_IDENTIFIED` ve konservatif *bound* raporlanabilir; kesin sıralama uydurulamaz.

## 12.5 Ekonomik testte birincil estimand ve belirsizlik

Birincil karşılaştırma **aynı takvimde, aynı başlangıç bakiyesi ve risk/venue kısıtlarıyla, açık exposure'ı da içeren net marked equity değişimi**dir (§10.5). İşlem sayısı veya winrate birincil kriter değildir; farklı policy'ler farklı trade listelerine yol açar. D4'ün 12 ortak fırsatı üzerinde hesaplanan farkı, 123 fırsatlı portföyün veya bağımsız gelecek dönemlerin farkı gibi yorumlama yanlıştır. Tek 90 günlük BTC 1H DEV penceresi, birleştirilmiş politika için confirmatory kanıt değildir.

İkinci raporlar: gross/net cash, fee, funding, slippage, protected exposure, time-in-position, aborted orders, queued/cancelled intents, `blocked_by_position`, reason-code distributions, R denominator, entry delay, latency sensitivity, liquidation feasibility. Cost estimate eksikse net profitability iddiası `BLOCKED` olur. Revenue/trading return ve business OPEX attribution ayrı tutulur.

## 12.6 Araştırma hipotezi ve çoklu test sözleşmesi

İlk V9 deneyleri aşağıdaki **tek değişiklik** ilkesini taşır; önerilen isimler repo üzerinde mevcut run değil, gelecekteki araştırma kayıtlarıdır:

| Family | Tek fark | Baseline | Primary claim and no-go |
|---|---|---|---|
| `V9-M1` | Bir PIT market-state observation'ının entry gate'e etkisi | V8 baseline ve raw threshold | Aynı takvim net marked equity; mekanik gate geçse de ekonomik fark yoksa diagnostic |
| `V9-E1` | Bir dependency-group expert contribution | Grammar-only / current expert policy | Altered decision count, portfolio difference; clone inflation başarısız |
| `V9-I1` | Fiyat bound/TTL policy | Native baseline entry | Fill authority ve price/timing; invalid execution profile → invalid outcome |
| `V9-P1` | Tek stop-management amendment policy | Static bracket | Protection integrity ve churn; post-cost portfolio difference |
| `V9-A1` | Ex-ante occupancy allocation | Single-position baseline | Matched-capital schedule; estimated utility UNKNOWN → rotation yok |
| `V9-K1` | Bounded research automation | Manual/scripted bounded task | Verified answer per wallclock/token; bu trading alpha testi değildir |

Her family için deneyden **önce**: `data_role`, eligible universe + PIT membership, observation availability policy, baseline revision/hash, challenger revision/hash, single altered behavior, parameter candidates, full family register, equity estimand, smallest economically meaningful improvement (predeclared; value must be *justified*, not invented), risk ceiling, block/cluster scheme, budget, stopping rule, negative null, sealed OOS access authority kayıt edilir. **Sonuç görülerek** eşik geriye dönük optimize edilmez. Yetersiz independent effective sample → `INCONCLUSIVE`, yoktan oluşturulan p-value yok.

**Çoklu test istatistikleri:** White WRC [L06], Hansen SPA [L07], DSR [L08], PBO/CSCV [L09] *aday yöntemlerdir*. Bunların veri/örneklem varsayımları mevcut kolda sağlanmadan otomatik `PASS` sayılmaz. Trial sayısı, valid outcomes ve effective independence ayrı kavramlar; ajanın sevdiği `N_eff`yi seçmesine izin verilmez. Test `NO_EDGE`, `INCONCLUSIVE`, `INVALID`, `BLOCKED` ile tamamlanabilir. `SUPPORTED_EDGE` yalnız korunan veri ve nitelikli execution ile bağımsız operatör kararına sunulabilir; hiçbir arXiv yöntemi kâr sertifikası değildir.

## 12.7 OOS izolasyonu ve selection-debt

`DEVELOPMENT` geniş ama kayıtlı araştırma alanıdır; rolling validation prosedürü frozen olduğunda değerlendirme alanıdır; `SEALED_FINAL_OOS` ayrı izinli runner'da ve Pi filesystem'inden uzakta tutulur. Sonucu görülen pencerede yeniden model ayarlamak bağımsız doğrulamayı tüketir. OOS bir kez görüldükten sonra dosya adına/branch'e yeni isim verip "taze" sayılmaz. Prospective shadow gerçek emir fill'inin vekili değildir. Altcoin listing/delisting evren filtreleri as-of kodlanır.

## 12.8 Yerleşik ekonomik ve güvenlik testleri

Aşağıdaki testler için **hiç sonuç uydurulmaz**; her biri repo implementasyonunda doğrulanmalıdır: `AUD-001` 2 campaigns incorrect but complete join -> FAIL; `AUD-002` wrong `last_trade_id` -> FAIL; `AUD-003` exit winner with impossible MFE -> FAIL; `AUD-004` missing mark with open position -> ACCOUNTING BLOCKED; `AUD-005` funding event after position close attributed to earlier open -> FAIL; `AUD-006` partial fill aggregate duplicate -> FAIL; `AUD-007` protection ref missing despite child order -> contradictory PASS disallowed; `AUD-008` economic claim on same-close bar -> AUTHORITY DENIED; `AUD-009` sealed OOS accessible from agent worktree -> SECURITY FAIL; `AUD-010` negative dev trial omitted from family -> SCIENTIFIC INVALID.

---

# XIII. Autonomous Kaizen: trading core'a EK yetenek

## 13.1 Rol ve bağımsızlık

**Trading core Pi'ye bağlı olmayacak.** Offline/ayrı süreçte çalışan Pi Agent, mevcut `audit/`, `evaluation/`, `oracle/`, `research` ve GitHub issue altyapısına read/write sınırlarıyla bağlıdır. Canlı `on_bar` veya `on_order_filled` callback'i LLM yanıtı beklemez. Pi durursa strategy devam eder, planlanmış risk kuralları bozulmaz.

## 13.2 En küçük inandırıcı araştırma döngüsü

```mermaid
flowchart LR
    AU[Native audit / evidence] --> ME[Research memory]
    ME --> ID[Pi: choose bounded question]
    ID --> PR[Preregister family, baseline and budget]
    PR --> WT[Isolated code worktree]
    WT --> TR[Deterministic tests + native replay]
    TR --> VE[Mechanics / economics / science validators]
    VE --> ME
    VE --> GI[Evidence-linked GitHub issue / PR]
    GI --> HU[Human decision / controlled promotion]
```

Tek research director varsayılan. `pi-goal-x` hedef/iş bitirme ve bounded workflow, `pi-subagents` gereken bağımsız reviewer için kullanılır; 5-agent sürekli konsey değil. Codemode çok sayıda yerel kayıt/issue taramasına yararlı, ama kısmi yan etkiler için transaction garantisi vermez. Bağımsız reviewer, deterministic validator'ın PASS/FAIL hükmünü değiştirme yetkisi taşımaz [D1, D2, L12, L13].

## 13.3 Issue tipleri

`BUG_VALIDATED`, `RESEARCH_HYPOTHESIS`, `EVIDENCE_GAP`, `ARCHITECTURE_PROPOSAL`, `INVALID_EXPERIMENT`, `REPRODUCTION`, `PROMOTION_REQUEST`. Her issue, `source_commit`, `data_window`, `policy_family`, `previous_trial_ids`, `acceptance_criteria`, `runtime_budget`, `allowed_files`, `evidence_refs` içerir. Yeni issue açılmadan önce semantik benzerlik taraması ve aynı lineage dedup yapılır; *false positive* dedup görüldüğünde iki hipotez kaydı korunabilir.

## 13.4 Risk temelli review

Rutin belge/test değişikliği tek builder + focused tests ile ilerler. Native execution, funding, risk, OOS policy, evaluation thresholds veya ekonomik iddia değiştiriyorsa bağımsız reviewer ve kapsamlı deterministic doğrulama gerekir. Reviewer'ın ayrı model olması tek başına bağımsızlık garantisi değildir; ayrı context, raw receipt ve base/head SHA farkına doğrudan erişim gerekir. Geçmiş pi-goal-x auditor churn'ünde görüldüğü gibi `COMPLETE` rozetine ulaşmak deneyin amacı değildir.

## 13.5 Research memory

`evaluation/store.py` ve mevcut trial ledger önceliklidir. Ek minimum tablo: `hypothesis_family`, `attempt`, `artifact_digest`, `conclusion`, `reopen_condition`, `related_issue`, `cost_wallclock`. Başarısız, deneysel, belirsiz sonuçlar silinmez. VectorDB veya knowledge graph **ölçülmüş arama/duplicate sorunu ortaya çıkmadan** eklenmez.

## 13.6 Yetki matrisi

| Eylem | Pi/Builder | Deterministic runner | İnsan/operatör |
|---|---|---|---|
| Read DEV evidence | İzinli/denetimli | İzinli | İzinli |
| Hipotez/issue/branch/PR | Sınırlandırılmış | Receipt | Onay/sahiplik |
| Research code değişimi | İzole worktree | Denetler | Gerekirse onay |
| Trade risk/validator override | **Yasak** | Hard-reject | Değişim için ayrı süreç |
| Sealed OOS erişimi | **Yasak** | Yetkili ayrı süreç | Explicit grant |
| Production merge/deploy | **Yasak** | Immutable receipt | Explicit approval |
| Live orders | **Yasak** | Trading core dışı | Ayrı üretim yetkisi |

## 13.7 İlk pilotun ölçülebilir başarısı ve ikinci ürün yasağı

**Kaizen'in mevcut hedef mimariye dahil edilmesi**, ek bir agent framework'ünün bugün geliştirilmesini şart koşmaz. Pilot **tek** bounded Issue/hipotez üzerinde başlar: Pi `DEV` kanıtlarını okur, geçmiş family kayıtlarını kontrol eder, bir preregistration önerir, izinli worktree'ye yalnız ilgili test/kod yazar, mevcut CLI/native runner'ı çağırır, kabul/ret/INCONCLUSIVE sonucunu silmeden kaydeder ve gerekçeli PR veya kapanış notu hazırlar. Aynı görev, aynı budget, aynı acceptance ve aynı hardware'da manuel/scripted baseline ile karşılaştırılır.

Pilot başarı metrikleri: reproducible task completion, verifier-detected defects, wall-clock, token/tool cost, attempts, unauthorised access count, duplicate proposal count. **Pozitif Sharpe bulması başarı ölçütü değildir.** İlk pilot, negatif veya `BLOCKED` bir sonucu doğru kaydedebildiği için başarılı olabilir. Tek task pilotu gerçek hız kazancı ispatlamaz; daha geniş throughput çalışması ayrıca yapılmalıdır.

`research_ops/` kalıcı queue, lease, semantic vector memory ve multi-agent swarm ihtiyaç kanıtlanmadan açılmaz. Agent audit/evaluation eşiklerini, sealed OOS'u, live order API'sini veya merge yetkisini alamaz. Pi'den bağımsız çekirdek için test: Pi process tamamen kapalıyken aynı prerecorded event tape, aynı deterministic decisions ve safety davranışı üretir.

## 13.8 Performans

16 GB Windows workstation ve 8 GB VPS için önerilen başlangıç: tek native process; tek builder; reviewer ardışık; thread/RAM limitleri; full suite yalnız ilgili milestone; 1–2 hipotezlik bounded research cycle; max wall-clock/LLM token/deneme sayısı; OOM/timeout `OPERATIONAL_FAILURE` olarak ayrılır. Gerçek hız artışı ancak aynı kabul ölçütü ve aynı hardware/model bütçesiyle ölçülen `accepted_results per compute-hour` üzerinden iddia edilebilir. Dış raporlardaki cent bazlı fiyatlar kontrata veya yerel ölçüme dönüşmeden maliyet garantisi değildir.

---

# XIV. Gerçek mevcut kodla V9 hedeflerinin eşleştirilmesi

Aşağıdaki tablo, GitHub'da önceki incelemelerde gözlenen dosyalarla ve proje raporlarıyla eşleşen **hedef sorumluluk haritasıdır**; 2 Kasım 2026 local çalışma ağacının tekrar okunduğunu iddia etmez. İç API imzaları, runtime test ve yerel push edilmemiş değişiklikler tam incelenmeden somut refactor sınırı kesinleşmez.

| Mevcut yol | V8 rolü | V9 hedefi | Karar | Yeni davranışın kabul ölçütü |
|---|---|---|---|---|
| `world/`, `domain/market.py` | Market, causal representation | MarketBelief/transition/uncertainty | `REFINE` | PIT, state version, known unknown |
| `experts/` | Behavior observer | Habitat-conditional stance, independent contribution | `REFINE` | Non-degenerate ablation, unchanged baseline default |
| `opportunities/book.py`, `models.py` | Canonical OpportunityBook | Immutable birth + multiple evaluation views | `REFINE` | Persistence without forced D4 wait |
| `economics/decisions.py`, `observer_policy.py` | Decision economics | DecisionPolicyV0 canonical action/intent/event vocabulary; reasoned parity | `REFACTOR` | DEC-001..010 fixtures, unknown/priority/idempotency, baseline parity |
| `risk/admission.py`, `sizing.py` | Hard limits | Revalidate every intent/order adjustment | `KEEP+REFINE` | Risk and venue reject fail-closed |
| `economics/allocation.py`, `domain/positioning.py` | Portfolio/exposure | Occupancy-aware policy and attribution | `REFINE` | Opportunity blocked-by-position trace |
| `adapters/` | Nautilus strategy & order | Entry/Position policy adapters | `KEEP+REFINE` | Native callback/fill/stop identity |
| `audit/pipeline.py`, `audit/reconciliation.py` | Forensic audit | Independent oracle, false-full-join mutants, protected equity and MFE time-bound safety | `P0 REPAIR` | Native joins correct independently, not merely zero orphan |
| `evaluation/store.py` | Trials/lineage | Reuse as append-only research memory | `KEEP` | All variants and failed attempts counted |
| `evaluation/gate_registry.py`, `kaizen_delta.py` | Gates and benchmark deltas | Separate correctness and economic promotion | `REFINE` | Reproducible outcome under fixed hashes |
| `oracle/utility.py` | Economic feasibility contract | Retain economic constraints | `KEEP` | No unsupported EV autopromotion |
| `system_proving/` | Receipt/proving tools | Fault-injection and structural qualification | `REFINE` | Invalid joins/gates rejected |
| `app/cli.py` | Unified CLI | Bounded research/adaptation commands | `SMALL EXTENSION` | No second CLI or hidden native path |
| `research_ops/` (**conditional**) | Not yet a canonical package | Only if pilot proves need: Pi queue/lease/budget/GitHub reconciliation | `ADD_IF_NEEDED` | A full bounded issue→trial→receipt pilot |

**Uyarı:** Eski `index.html` monografındaki V8 `src/v8/` veya Rust dosyaları aktif uygulama olarak kullanılmaz; depo `AGENTS.md` ve owner boundary `v8-next/` tek aktif kod alanıdır. Belgedeki eski `KaizenController` otorite tanımları V9 çalışma ortamında yeniden yazılmadan önce hangi gerçek modüllerin aktif olduğuyla eşleştirilmeli, birden çok sovereign controller inşa edilmemelidir [R1, R2].

---

# XV. Mimari tercih: minimal / orta / karmaşık

| Alternatif | İçerik | Neden/neden değil |
|---|---|---|
| **A — Minimum extension** | V8-next + yeni decision contract + Pi manuel bounded tasks | İlk dikey dilim için ideal; research scheduling az |
| **B — Bounded persistent Kaizen** | A + mevcut ledger'la çalışan küçük queue/lease/budget/receipts | V9 için önerilen **Kaizen eki**; runner tekrarlarını ve audit churn'ünü azaltabilir |
| **C — Agent swarm + vector memory + adaptive bandits** | Ek agency, bilgi grafikleri, karmaşık scheduler | Bu donanım ve henüz kanıtlanmamış araştırma hacmi için **DEFER** |

**Önemli ayrım:** Buradaki Mimari B seçimi **V9 trading core'un yerine agent control plane koymak değildir**. Ana ürün tasarımı IV–XII bölümlerindeki market-aware trader'dır; araştırma otomasyonu kendi içinde orta düzeyde kalıcılığa sahiptir.

---

# XVI. Aşamalı uygulama ve bağımlılık kapıları: önce doğru, sonra adaptif

Bu program takvim sayısından çok **evidence gates** ile yönetilir. `Phase complete` tarihi verilmez; ancak belgedeki sözleşmenin repo-yerel versiyonları testle doğrulandığında statü değişir.

## P0-A — Repo-grounded current state envanteri

- `ddawnlll/v8` doğru local HEAD, dirty files, branch, son D4 commitleri/uzak dal farkları; v8-next aktif uygulama mı ve Nautilus pin değişmiş mi kaydedilir.
- Her V9 önerisi için `KEEP / REFINE / REFACTOR / ADD / DEFER`, mevcut class/function, owner, affected tests ve proof of absence ile **traceability** hazırlanır.
- `site/index.html` tarihi V8 kaynağıdır. `docs/v9/V9_ARCHITECTURE_MONOGRAPH_v1.1.md` kaynak belge, `site/v9.html` generated çıktı olarak korunur.
- **Gate:** yanlış repo/branch üzerinden kaydedilmiş çalışma olmayacak; baseline native fill counts ve audit artefakt digestleri sabit olacak.

## P0-B — Audit/venue safety repair (trading P0)

- F01–F08 eski audit bulgularının hangileri bugünkü kodda var, hangileri kapatılmış, `UNVERIFIED` mi commit+test bazında belgele.
- Per fill native IDs, campaign/opportunity/decision refs, funding/mark/cash reconciliation, independent hand-computed oracle ve 10 mutation/fault fixtures.
- Safety order/position/protection state machines ve restart reconciliation; exact Nautilus callback order; `UNKNOWN_AT_VENUE`, duplicate suppression.
- **Gate:** eski yanlış campaign join/doubled cashflow/protective false PASS'ın *mekanik olarak tespit edildiği* kanıtlanmadan ekonomik politika testi yetki kazanmaz. Bir local test geçişi gerçek venue güvenliği sertifikası değildir.

## P0-C — DecisionPolicyV0 vertical slice (trading P0)

- §7'deki kanonik action/intent/event/reason sözlüğünü existing code API'lerine **minimum müdahale** ile bağla.
- Immutable decision receipt, native order intent key, causally available MarketState/venue snapshot.
- `DEC-001..010`, `ORD-001..009`, `POS-001..010` testleri; *baseline-off* parity. Correct safety repair nedeniyle fark gerekirse gerekçe/fixed scenario ayrı `SAFETY_REPAIR` kayıtla.
- **Gate:** Aynı source snapshot→same action, duplicate→no additional order, open position→no unverified protection, Pi-off trading unchanged. Bu aşama **ekonomik iyileştirme değil**, mekanik sözleşme doğrulamasıdır.

## P1-A — Market Intelligence V1 single-use challenger

- Önce yalnız PIT quality/volatility view; calibrated regime probs, BOCPD ve learned router default-off.
- `V9-M1` preregistration: one behavior, raw feature baseline, simple threshold baseline, test edilen olay, changed-decision accounting, costed calendar equity.
- **Gate:** Mekanik valid bir view, ekonomik faydasızsa diagnostic kalır; yeni state sistemi ekonomik authority kazanmaz.

## P1-B — Entry / Expert / Position ayrı ablations

- `V9-E1`: correlated expert family ablation ve clone testleri.
- `V9-I1`: entry price cap veya TTL *bir tane*, fill profile nitelikli olmadan net edge iddiası yok.
- `V9-P1`: static bracket karşısında *bir* protective amendment challenger; safety gate ve churn budget hard.
- **Gate:** Her family ayrı baseline, aynı ekonomi/riske bağlı karar impact, failure reason ve trial debt.

## P1-C — Portfolio observability ve altcoin feasibility

- Önce occupancy/id-reason/capacity/margin telemetry; optimizer veya position rotation default-off.
- PIT listing/delist/volume universe, exchange minimum notional, margin/liquidation distance ve altcoin data coverage qualified dataset.
- **Gate:** Gelmemiş fiyatı bilerek hindsight rotation seçen allocator yasak. 20 USDT live feasibility **ayrı** test edilir, BTC 10k fixture genel geçer kanıt değil.

## P2 — Autonomous Kaizen eklentisi ve longitudinal verification

- Pi + mevcut audit/store/CLI ile tek bounded task, negative/blocked outcomes, evidence-linked Issue/PR, read-only external artefact references.
- Same-budget manuel/script baseline. Reviewer yalnız riskli kod/audit değişiminde; deterministic result override edemez.
- **Gate:** Pi olmadan native engine aynı çalışır; OOS ve live order credential erişimi yok; kalıcı scheduler ancak ölçülmüş darboğaz sonrasında.

## P3 — Production qualification ayrı bir proje kapısı

- True venue lifecycle: reconnect, rate limits, order protection, transfer/fee/margin metadata, emergency halt, on-call protocol, shadow/paper and prospective evidence.
- Risk boundaries ve exact capital/instrument approval. V9 monografı tek başına live mandate değildir.

**Çalışma ayrımı:** P0 safety düzeltmeleri ile Pi'nin salt geliştirme üretkenliği pilotu bazı görevlerde paralel olabilir; ancak ekonomik araştırma verdictlerinin promotion'a yönlendirilmesi P0 evidence-gated olmadan yapılamaz. Büyük mimari hedef korunur, fakat her davranış kademeli etkinleşir.

---

# XVII. Kabul kriterleri: fikir değil, sınanabilir davranış

| ID | Sorumluluk | Mekanik gate | Ekonomik gate / statü |
|---|---|---|---|
| `G-MKT-01` | Market belief PIT | Future-data mutation test sonucu değiştirmez; UNKNOWN yasal | Rejim edge'i iddiası için ayrı comparison |
| `G-EXP-01` | Expert contribution | Clone invariance; attribution + ablation | Marjinal net utility; no effect → KEEP/DEFER |
| `G-OPP-01` | Opportunity lifecycle | No episode duplicate; event/time validity | D4 kuralı yalnız candidate |
| `G-DEC-01` | Trader decisions | Her native order intent bir `decision_id` ile bağlı; duplicate/unknown fixtures geçerli | Decision delta + portfolio accounting |
| `G-ENT-01` | Execution | Same-bar disclosure; partial fill/stop join | Realistic profile invalid → BLOCKED |
| `G-POS-01` | Position | Native stop updates correct and idempotent | C4 OOS olmayan +0.1008R yeterli değil |
| `G-POR-01` | Portfolio | No over-risk; occupancy and blocked candidate lineage | Calendar-aligned costed marked equity |
| `G-AUD-01` | Audit correctness | Independent full-join oracle + mutation detection; MFE native bounds | Audited receipt required for economic claim |
| `G-KAI-01` | Kaizen | Complete issue→trial→receipt; no OOS/merge access | Reduced walltime only if benchmarked |
| `G-OPS-01` | Live readiness | Restart, venue risk, native protection proven | Ayrı production authority; RFC ≠ approval |

## 17.1 Anti-regression invariant'ları

`policy_feature_off` eski V8 baseline davranışını korur; `source/time` monotonic; idempotent same-event replay; STOP-FIRST yalnız uygun bar-only diagnostic bağlamında; STOP native order without position id ≠ verified protection; `cashflow` realized/unrealized ayrımı; sealed data reachable olmayan agent worktree; code/venue/schema hash değişince trial identity farklı; negative trial append-only tutulur. Bu değişmezler birer test fikri değil, uygulanması gereken kabul sözleşmesidir.

## 17.2 Ekonomik hüküm dili

`IMPLEMENTED` mekanik doğru yürütmeyi; `MECHANICALLY_VALIDATED` belirli native senaryodaki doğrulamayı; `ECONOMICALLY_INCONCLUSIVE` belirsiz sonucu; `ECONOMICALLY_SUPPORTED` uygun bağımsız koşulları; `LIVE_AUTHORIZED` ayrı üretim yetkisini ifade eder. `PASS` raporunun kapsamı belirtilmeden başka seviyeye taşınamaz. Arşivlenmiş V8 monografının eski normatif adlandırmalarıyla görece durum geçişleri ayrı ADR olarak çözülür.

---

# XVIII. Risk kaydı ve neden yapmayacağımız şeyler

| Risk | Şiddet | Karşı önlem / bilinmeyen |
|---|---|---|
| Market regime classifier overfit | High | Dondurulmuş PIT features, ablation, rolling validation |
| Many expert consensus illusion | High | Clone/lineage controls, actual selection changes |
| Entry false fill / same-close lookahead | Critical | Native sequencing tests, L1/L2 when claims need it |
| Position stop mismatch | Critical | Native callback and reduce-only / order list tests |
| Funding/cashflow misattribution | High | Settlement event/campaign-level reconciliation |
| Portfolio occupancy hindsight fallacy | High | Same-calendar constrained native replay |
| Sealed OOS contamination by agents | Critical | Physical isolation + explicit operator grant |
| Audit PASS with wrong join | Critical | Fault injection and multi-key native reconciliation |
| Autonomous hyperparameter p-hacking | High | Trial ledger, family size, explicit stop conditions |
| Pi agent runaway auditor loop | Medium/High | Per-run time, token and retry budget; evidence-focused completion |
| 20 USDT quantization / liquidation | High | Venue fee/lot/margin feasibility; fail closed |
| Compute exhaustion / VPS OOM | Medium | Single native process and pinned resource budgets |

**Bilinçli olarak yapılmayacaklar:** yeni repo/engine; live LLM market controller; ikinci `OpportunityBook`, economics ledger, auditor registry veya trader's brain; 28 expert'ı topluca sıfırlamak; kanıtlanmadan compulsory retest; fine-tuning live model in-place; automated agent main merge; daemon agent swarm; knowledge graph/vector DB without measured need; garantili edge ifadesi; 1H OHLCV'den gerçek order-book physics çıkarma.

---

# XIX. Architecture Decision Records (ADR)

### ADR-001 — Kaynak ve repo
**Karar:** `ddawnlll/v8` içinde `v8-next/` tek çalışma kodu; V8 monografı archive/historical. **Alternatif:** yeni V9 repo. **Ret:** migration, duplicate code, baseline loss. **Reversal:** mevcut tasarımın ölçülmüş ve düzeltilemeyen yapısal sınırı.

### ADR-002 — Trader core LLM'siz
**Karar:** market/expert/entry/position/risk kararları sürümlü algoritmik politikalardır; LLM yalnız offline research. **Reversal:** ayrı güvenilir latency/repro/risk testleri ve açık yetki; bu monografta önerilmez.

### ADR-003 — MarketBelief önce ölçüm, sonra alpha
**Karar:** PIT/belief/uncertainty tanımları semantic foundation; production routing ancak economic evidence sonrası. **Reversal:** basit market state baseline'ın yeterli olduğu kanıtlanırsa yeni model kaldırılır.

### ADR-004 — Fırsat ayrı, emir ayrı
**Karar:** opportunity identity korunur, entry intent ayrıştırılır; D4 retest default-on değil. **Reversal:** decision/entry ayrımının kayıt veya sonuç kalite katkısı olmadığı ölçülürse mevcut API içinde birleştirilir.

### ADR-005 — Dinamik pozisyon yönetimi policy seviyesinde
**Karar:** native bracket korunur; C4 default-off, hypothesis. **Reversal:** bounded replay ile mekanik kararsızlık saptanırsa özellik ertelenir.

### ADR-006 — Portfolio ilk başta attribution
**Karar:** yeni ranker/simultaneous position allocation önce değil, occupancy ölçümü önce. **Reversal:** matched multi-opportunity benchmark yeterli örneklem ve artı katkı gösterirse allocator challenger.

### ADR-007 — Audit doğruluğu ekonomik araştırmadan önce
**Karar:** P0 reconciliation, funding ve timing gaps sınıflandırılır; yanlış PASS yok. **Reversal:** kaynağı güncel kodla yeniden doğrulanmış no-finding kayıtlar ilgili problemi kapatır.

### ADR-008 — Kaizen küçük ve ikincil
**Karar:** Pi + mevcut trial/evaluation + GitHub; bütçeli pilot, single-agent default. **Reversal:** yerel accepted-task-per-hour ölçümünde başka yapı anlamlı üstünse.

### ADR-009 — Monograf source-of-truth
**Karar:** V9 için `docs/v9/` altında sürümlü Markdown; `site/v9.html` derlenmiş output, elle düzenlenmez; `site/index.html` V8 historical kalır. **Reversal:** owner aynı site index'ini V9 ana giriş olarak değiştirmeyi açıkça yetkilendirirse; yine Markdown canonical kalır.

---

# XX. Kod/Docs geçişi: bu belge repoda nasıl yaşamalı?

```text
ddawnlll/v8/
  docs/
    v9/
      V9_ARCHITECTURE_MONOGRAPH.md       # BU MAKALE, immutable first draft + revisions
      V8_TO_V9_DELTA.md                  # code-path map + KEEP/REFINE/ADD
      V9_IMPLEMENTATION_PLAN.md          # issues, gates, milestones
      V9_SOURCE_REGISTER.md              # bibliography + evidence provenance
  site/
    index.html                           # historical generated V8 monograph
    v9.html                              # generated V9 reader, not source
  tools/
    build_monograph.py                   # existing V8 compiler preserved
    build_v9_monograph.py                # optional tiny wrapper/new manifest if necessary
  v8-next/
    src/v8_next/...                      # same codebase, evolutionary patches
```

**Dokümantasyon kompozisyonu:** Mevcut `tools/build_monograph.py` V8 bölüm listesini `NAMES` ile sabitliyor ve `tools/heads/head_en.html` temel şablonundan üretim yapıyor [R4]. V9 sürümü ayrı `manifest` veya küçük generic include listesi ile aynı görsel/head alışkanlığını kullanabilir; V8 `NAMES` listesine rastgele ekleme yaparak eski index'i istemeden değiştirmemeli. Önce Markdown source-of-truth eklenir, ardından HTML deterministik üretilir ve generated-file hash/derleme testi PR'da kaydedilir. Bu monograftaki hiçbir öneri repo üzerinde otomatik uygulanmamıştır.

---

# XXI. Örnek 30 günlük çalışma planı (kapıya bağlı, garanti değil)

| Dönem | Çıktı | Temel gate |
|---|---|---|
| Gün 1–4 | Local Git tree, code map, audit findings triage, V9 docs | Bütün path ve provenance referansları gerçek |
| Gün 5–9 | Campaign/fill/stop/equity/funding correctness tests | İlişkiler doğru veya açık BLOCKED |
| Gün 10–14 | DecisionPolicyV0 baseline-equivalent vertical slice; MarketBelief diagnostic-only | Baseline parity, UNKNOWN, order/position invariants |
| Gün 15–19 | EntryIntent/PositionThesis ve occupancy telemetry (yeni davranış default-off) | Native lifecycle, protection, risk hard gates |
| Gün 20–24 | Yalnız P0 geçerse bir preregistered native ablation; aksi hâlde mekanik tamir | Same-calendar net equity veya açık BLOCKED/INCONCLUSIVE |
| Gün 25–30 | Pi tek-task araştırma pilotu veya ihtiyaç duyulan P0 düzeltmesi | Negative/inconclusive output dürüst, no live authority |

Bu plan araştırma raporunun varsayılan 30 günlük programıdır, katı takvim/garantili süre değildir. P0 audit kilidi çözülemezse ekonomik Phase 4 ertelenir; Pi self-improvement operational tests paralel yapılabilir ama yanlış ekonomik metriği “öğrenme” kaynağı sayamaz.

---

# XXII. Sınanabilir başarısızlık koşulları / Projeyi nasıl yanlışlarız?

1. `MarketBelief` yanlış data availability üretir veya yeni bilgi olmadan geçmiş kararı değiştirirse mekanik **FAIL**.
2. Expert ablation tekrar baseline ile aynıysa daha karmaşık consensus için ekonomik **NO_EDGE/DEFER**.
3. Fırsat hafızası yalnız bekleme zorunluluğu getirip D4 benzeri gecikme ve PnL zararına sebep olursa policy **REJECT**; kimlik/audit hafızası yine korunabilir.
4. Giriş iyileşmesi native realistic fill modelde yeniden üretilemiyorsa **INVALID/BLOCKED**; ucuz screening sonucu destek sayılmaz.
5. Position Manager stop update'leri idempotent veya reduce-only değilse üretim entegrasyonu **BLOCKED**.
6. Portföy değişimi yalnız trade-level ortalamayı iyileştirip calendar equity'yi iyileştirmiyorsa economic superiority iddiası **REJECT/INCONCLUSIVE**.
7. Audit yanlış campaign-to-fill bağlayıp `PASS` üretiyorsa ilgili kanıt zincirinin bütün verdictleri **BLOCKED**.
8. Pi Agent aynı negatif fikri farklı isimle yüzlerce kez optimize ediyorsa Kaizen pilotu **FAIL**.
9. Agent ayrı sealed OOS veya live order API'sine erişebiliyorsa güvenlik sınırı **FAIL**.
10. V9 mimari katkıları ekstra complexity karşısında basit V8 baseline'a göre ölçülmüş fayda üretmiyorsa yeni modüller **ROLLBACK/DEFER**.

---

# XXIII. Açık sorular, sınırlamalar ve gelecek araştırma

**Açık deneysel sorular:** (i) MarketBelief regime priors gerçekten fayda sağlıyor mu? (ii) 28 expert'ın hangileri bağımsız, işe yarar? (iii) Stop yönetimi değişikliği farklı dönemlerde, altcoin'lerde ve funding dahil koşullarda kârlı mı? (iv) Pozisyon işgali fırsat maliyeti doğru yönlü tahmin edilebilir mi? (v) Entry limit order fill olasılığı daha yüksek çözünürlükte ölçülebilir mi? (vi) 20 USDT altcoin perpetual hesabı gerçek min notional ve fee koşullarında çalışabilir mi? (vii) Pi research loop, aynı bütçeli manuel ve basit workflow'a göre kanıtlı soru yanıtlama hızını artırıyor mu?

**Temel limit:** Kullanıcının projedeki tarihi dokümanlarında güçlü governance iddiaları bulunabilir; bu çalışma onları yeni codebase'in hazır özellikleri saymaz. Bazı yerel değişiklikler varsayılan GitHub dalında bulunmayabilir. Bağımsız ZIP audit'inin sorunları farklı tarihteki run'a ilişkindir; güncel kodda düzeltme olup olmadığı yeniden ölçülmelidir. ArXiv akademik çalışma sonuçları V9'un kendi kârlılık validasyonu değildir.

**Değerlendirme programının başarı tanımı:** İlerleme, eklenen agent/subsystem sayısı veya monograf uzunluğu değil; (a) daha doğru gözlenebilir piyasa/karar state'i; (b) valid native execution; (c) kararlara ekonomik attribution; (d) falsifiable after-cost policy comparisons; (e) kaybolmayan negative evidence; (f) insan kontrollü production riskidir.

---

# XXIV. Kaynakça ve provenance register

*Aşağıdaki URL'ler erişilen birincil kaynaklara veya kullanıcı tarafından gönderilen proje artifact'larına işaret eder. Literatür sonuçlarının V9'a taşınması bu makalenin `DESIGN_INFERENCE` yorumudur; doğrudan deneysel kanıt değildir.*

## A. Hakemli araştırma ve doğrulanmış preprint'ler

- **[L01]** Adams, R. P. & MacKay, D. J. C. (2007), *Bayesian Online Changepoint Detection*, arXiv:0710.3742. https://arxiv.org/abs/0710.3742 — rejim/değişim tespiti için aday yöntem.
- **[L02]** Moskowitz, T. J., Ooi, Y. H., Pedersen, L. H. (2012), *Time Series Momentum*, Journal of Financial Economics 104(2), 228–250. https://doi.org/10.1016/j.jfineco.2011.11.003 — diğer futures evrenlerindeki bulgu, altcoin'e direkt edge garantisi değil.
- **[L03]** Almgren, R. & Chriss, N. (2001), *Optimal Execution of Portfolio Transactions*, Journal of Risk. https://doi.org/10.21314/JOR.2001.041 — risk/impact/maliyet değiş tokuşu.
- **[L04]** El-Yaniv, R. & Wiener, Y. (2010), *On the Foundations of Noise-free Selective Classification*, JMLR 11. https://jmlr.org/papers/v11/el-yaniv10a.html — reject option ve coverage.
- **[L05]** Geifman, Y. & El-Yaniv, R. (2017), *Selective Classification for Deep Neural Networks*, arXiv:1705.08500. https://arxiv.org/abs/1705.08500 — seçici sınıflandırma, finansal ekonomik garanti değildir.
- **[L06]** White, H. (2000), *A Reality Check for Data Snooping*, Econometrica 68(5). https://doi.org/10.1111/1468-0262.00152 — multiple testing / benchmark search.
- **[L07]** Hansen, P. R. (2005), *A Test for Superior Predictive Ability*, Journal of Business & Economic Statistics 23(4). https://doi.org/10.1198/073500105000000063 — SPA karşılaştırması; yöntem uygunluğu önkoşulu.
- **[L08]** Bailey, D. & López de Prado, M. (2014), *The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting, and Non-Normality*, Journal of Portfolio Management 40(5). https://doi.org/10.3905/jpm.2014.40.5.094 — seçilmiş Sharpe inflation.
- **[L09]** Bailey, D., Borwein, J., López de Prado, M. & Zhu, Q. (2017), *The Probability of Backtest Overfitting*, Journal of Computational Finance. https://doi.org/10.21314/JCF.2016.322 — PBO/CSCV; veri bağımlılığı ve örneklem büyüklüğüyle sınırlı.
- **[L10]** Kim, J. & Park, H. (2025), *Designing Funding Rates for Perpetual Futures in Cryptocurrency Markets*, arXiv:2506.08573. https://arxiv.org/abs/2506.08573 — teorik funding tasarımı; exchange simulator'a doğrudan doğrulama değil.
- **[L11]** Santoni, M. L., Jouanne, V. & Scullin, M. L. (2026), *Equity Strategy Backtesting: Luck or Edge? The MinervaScore as a Statistical Robustness Grade*, arXiv:2608.23808v2. https://arxiv.org/abs/2608.23808 — gerçek ileri dönem veride skorla performans ilişkisinin anlamlı bulunmadığı raporlanır.
- **[L12]** Li, Y. vd. (2025), *R&D-Agent-Quant: A Multi-Agent Framework for Data-Centric Factors and Model Joint Optimization*, arXiv:2505.15155v2, NeurIPS 2025. https://arxiv.org/abs/2505.15155 — research/development/feedback mimari örneği.
- **[L13]** Mao, J. vd. (2026), *Reliable Before Profitable: QuantHarness for Governing Financial Strategy Development with LLM Agents*, arXiv:2610.26101. https://arxiv.org/abs/2610.26101 — trajectory evidence ve agent governance; trading edge değil.
- **[L14]** Lu, C. vd. (2024), *The AI Scientist: Towards Fully Automated Open-Ended Scientific Discovery*, arXiv:2408.06292. https://arxiv.org/abs/2408.06292 — LLM ile araştırma otomasyonu; V9 review authority için yeterli değil.
- **[L15]** Du, W. & Chung, S. (2026), *Can AI Agents Make Open-Ended Scientific Discovery? Evidence from Station*, arXiv:2610.08927. https://arxiv.org/abs/2610.08927 — araştırma sürekliliği, farklı görev popülasyonu.
- **[L16]** Sabashvili, A. (2026), *Conformal Prediction Algorithms for Time Series Forecasting: Methods and Benchmark*, arXiv:2601.18509. https://arxiv.org/abs/2601.18509 — zaman serisinde exchangeability sınırlaması.

## B. Mevcut yazılımın birincil dokümantasyonu

- **[T1]** NautilusTrader, *Backtest Execution Flow*. https://nautilustrader.io/docs/latest/concepts/backtesting/execution-flow/ — callback/same timestamp semantiği, v2.0.0rc4 ile sürüm eşleşmesi ayrıca nitelendirilmeli.
- **[T2]** NautilusTrader, *Backtest Data and Venues*. https://nautilustrader.io/docs/latest/concepts/backtesting/data-and-venues/ — bar/tick/L1/L2/L3 model yetenekleri.
- **[R1]** `ddawnlll/v8` source tree (`v8-next/src/v8_next/`). https://github.com/ddawnlll/v8/tree/main/v8-next/src/v8_next — kod envanteri; güncel yerel branch ile parity doğrulanmalı.
- **[R2]** `v8-next/pyproject.toml`, `README.md`, `AGENTS.md`; root `AGENTS.md`. https://github.com/ddawnlll/v8/tree/main/v8-next — aktif Python/Nautilus kod sınırı ve test koşulları.
- **[R3]** `v8-next/src/v8_next/audit/pipeline.py`, `evaluation/store.py`, `gate_registry.py`, `kaizen_delta.py`, `oracle/utility.py`, `opportunities/book.py`, `app/cli.py`. https://github.com/ddawnlll/v8/tree/main/v8-next/src/v8_next — mevcut core research/audit modülleri.
- **[R4]** `tools/build_monograph.py` ve root `README.md`. https://github.com/ddawnlll/v8/blob/main/tools/build_monograph.py — docs Markdown → generated monograph HTML; V8 `NAMES` sabit.

## Council bilimsel hakemlik kaynakları

- **[C1]** `Pasted text(10).txt` — Blind Model Council review 1 (592 satır); kapsamı yalnız monograf; code audit değildir.
- **[C2]** `Pasted text (2)(2).txt` — Blind Model Council review 2 (104 satır); tek belge üzerinden akademik ve mimari eleştiri.
- **[C3]** `Pasted text (3).txt` — Blind Model Council review 3 (664 satır); trading karar semantiği, partial fills, accounting ve test stratejileri.
- **[C4]** `V9_MODEL_COUNCIL_SYNTHESIS_v1.md` — yorum/karar tablosu; üç raporun bilimsel bağımsızlığını veya repo kodunun doğruluğunu kanıtlamaz.

## C. Proje kanıtları (kullanıcı tarafından sağlanan, internet yayını değildir)

- **[P1]** `index(3).html`, *V8 Final Research Monograph* — eski V8 constitution, docs/ contracts, kaizen vision, historical architecture. Kullanıcı dosyası.
- **[P2]** `audit-20261030T223550Z-6ffc87e.zip` — native audit artifact set; exact run fingerprint archive manifestinde.
- **[P3]** `V8_NEXT_V9_RESEARCH_COMPLETE_HANDOFF.zip` — A/B/C/D3, 616 arşiv üyesi, Türkçe `V9_RESEARCH_HANDOFF_TR.md`, `OUTSTANDING_ISSUES_TR.md`, original JSONL, SHA-256 doğrulama manifestleri.
- **[P4]** `D4_ANSWER_TR.md`, `D4_lifecycle_opportunity_states.jsonl`, `D4_lifecycle_screening.json` — ayrı D4 retest/reclaim DEV native raporu. Kaynak yerel run yeniden yürütülmedi.
- **[P5]** `v8_next_independent_raw_audit_review.md` — 2026-10-30 audit ZIP'ine dair bağımsız artifact-based inceleme; güncel kod düzeltmelerini yeniden test etmez.
- **[D1]** Deep Research I, `Pasted text(9).txt`, Kasım 2026 — literatür ve otonom araştırma üzerine kullanıcı dokümanı; bazı performans/maliyet iddiaları bağımsız tekrar ölçülmedi.
- **[D2]** Deep Research II, `Pasted text (2)(1).txt`, Kasım 2026 — repo-odaklı güven sınırları ve düşük karmaşıklık araştırması; kaynak/claim sınırlamalarını açıkça beyan eder.

---

# XXV. Model Council hakem cevapları ve değişiklik izi

Üç blind review belgenin **aynı sürümünü** okudu; onların fikir birliği dış kodu doğrulamak için bağımsız emprik kanıt sayılamaz. Birinci hakem `Pasted text(10).txt` [C1], ikinci hakem `Pasted text (2)(2).txt` [C2], üçüncü hakem `Pasted text (3).txt` [C3]. Editorial synthesis [C4] yeni mimari hedefin korunması ama broad implementation izninin verilmemesi yönündedir.

| Council kusuru | Önceki v1.0 | v1.1 düzeltmesi | Kalan doğrulama |
|---|---|---|---|
| Central policy `argmax` uygulanamıyor | §7.4 soyut hedef | §7.4 explicit DecisionPolicyV0; §7.7 optimizer future-only | Local function API + native parity |
| WAIT/WATCH, MODIFY/ADJUST | Çoklu isim | §7.1 dört/altı typed alan, state enum ve reasons | Enum/contracts source compatibility |
| 89/89 cashflow ve historical audit | “P0 repair” genel | §12.1 hand-computed oracle + false-full-join mutants | Local HEAD status unknown |
| Fill & funding authority | Genel OHLC uyarısı | §11.2 profile matrix + §11.3 settlement model | Actual engine callback/tape qualification |
| MarketBelief etiket torbası | Regime distribution | §4.3 validated-score vs probabilities; §4.6 prereg falsifiable use | M1 data and result |
| Correlated expert evidence | Clone invariance tekil | §5 + E1 group ablation | Dependency graph measured |
| Position churn/unprotected exposure | Qualitative safeguards | §8.4 races, §9.4 bounded amendment, §9.6 fixtures | Venue semantics, tests |
| Linear order lifecycle | `INTENT→ORDER→POSITION` | §8.2 orthogonal intent/order/position/protection state | Native event sequence tests |
| Opportunity cost hindsight | Factual vs simulated yalnız anlatım | §10.2 dual metrics + no rotation UNKNOWN | Same-capital paired portfolio trials |
| OOS family design | Genel araştırma kuralları | §12.6 one-change/family/protocol | Precise thresholds prereg before running |
| Agentic second product | Conditional research_ops | §13.7 one-task pilot, Pi absent parity | Measured overhead and isolation |

**Kısmen reddedilen hakem önerisi:** Market Intelligence, Position Management veya Portfolio sorumluluğunu *hedef mimariden* çıkarma önerisi. Bunların kârlı olduğu iddia edilmemektedir; yeni araştırma hedefi olarak kalmaları, kontrolsüz üretim aktivasyonundan farklıdır. V9'un trading zekâsına ait bilimsel sorular korunurken, uygulama P0 dar karar ve veri doğruluğundan başlar.

## XXV-A. Normatif terimler ve adlandırma kilidi

Bu belge içinde `DecisionAction.WAIT` ≠ `OpportunityStatus.WATCHING`; `IntentKind.AMEND_PROTECTION` ≠ `DecisionAction.EXIT`; `VenueOrderStatus.REJECTED` ≠ `RiskDecision.REJECTED`. İdeal implementasyonda aynı semantik kavram için ikinci synonym enum bulunmaz. `UNKNOWN` ekonomik tahmin ve venue state'de farklı **typed** nedenlerle kullanılır.

## XXV-B. Mimari tasarımı yanlışlayabilecek deneyler

V9'un piyasa zekâsı iddiası yanlışlanabilir: `M1` feature/belief karar kalitesini değiştirmiyor ya da basic threshold'dan kötü; `E1` expert contribution yok; `I1` entry delay returns negative; `P1` amend churn net PnL'yi kötüleştiriyor; allocator fırsat maliyeti ex-ante tanımlanmıyor; `K1` agentic pilot bounded manual task'tan yavaş/yanlış. Bu bulgular ilgili *policy'yi* reddetmeye veya diagnostic'e indirmeye yeterli olabilir; **korunan mevcut V8 runtime'ın tüm varlığını** reddetmez.

---

# XXVI. Nihai sentez

**V8'in değerli çekirdeği korunur:** point-in-time market state, expert-observer, canonical OpportunityBook, risk/utility separation, NautilusTrader native execution, evidence lineage ve bilimsel yanlışlama. **V9'un yeniliği**, bu parçaların birbirinden kopuk açıklamalar olarak kalmayıp tek bir **sürekli trader karar çevrimi** üretmesidir: piyasa görüşünün güncellenmesi, fırsatın yeniden değerlendirilmesi, fiyat farkındalığı olan giriş, pozisyon tezi ve koruma yönetimi, sermaye/occupancy bilinci, ekonomik sonucunun native audit ile ölçümü. Bu davranışların doğruluğu önce; kârlılığı sonra test edilecektir.

**Otonom Kaizen ek yetenektir.** Pi Agent yeni hipotezleri seçer, sınanabilir araştırma planları üretir, izole kod yazar, mevcut audit/experiment store'u çağırır, GitHub Issues/PR üzerinden insanın incelemesini sağlar. Pi ne bir intrabar strateji callback'idir ne ikinci ekonomist ne de trading risk otoritesi. Pi kapalıyken V9 trading çekirdeği kendi bütünlüğüyle çalışır.

Bu revize monografın kabul edilmesi tek başına **profitable bot** veya production authorization değildir; ama V8'den V9'a geçişi soyut “daha akıllı trader” söyleminden çıkarıp kod eşleme, falsifiable interface, native mekanik test ve ekonomik benchmark setine dönüştürür. V9'un asıl ölçütü daha fazla kod değil, **kararların nedenlerini, alternatiflerini ve sonuçlarını daha doğru ölçüp güvenilir biçimde geliştirebilen bir trader sistemi** olmaktır.

*Belge sonu · V9-ARCH-RFC-1.1-REVISED · 2026-11-02*
