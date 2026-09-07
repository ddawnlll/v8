# D-153 Benchmark Fabric Şartnamesi (Tam Metin Anayasal Şartname)

**Durum:** PROVISIONAL_DECISION · **Tarih:** 2026-09-06 · **Kurallar:** 12, 28–31, 44, 51–57
**Ardıllık:** D-147, D-150, D-151, D-152'yi genişletir; tüm kilitli değişmezleri ve epistemik sınırları korur.
**Eserler:** `v8-core/src/benchmark/`, `v8-core/tests/d153_benchmark_fabric_sabotage.rs`, `v8-core/tests/d152_gate_vector_authority_firewall.rs`, `v8-core/tests/d153_receipt_ledger_selfverify.rs`, `v8-core/tests/d153_parity_adapters_policy_bound.rs`, `v8-core/src/kaizen/`, `docs/decisions/DECISION_REGISTER.md`, `docs/contracts/D153_BENCHMARK_FABRIC_SPEC.md`.
**Normatif metin:** Bu dosya İngilizce `docs/contracts/D153_BENCHMARK_FABRIC_SPEC.md` metninin Türkçe aynasıdır. Normatif yetki İngilizce tam metindedir; ayna ikinci bir authority değildir ve İngilizce metinle çeliştiği yerde İngilizce metin geçerlidir.

> **Durum düzeltmesi (D-159, issue #330).** Bu başlık daha önce
> `RATIFIED_DECISION` gösteriyordu, oysa her iki karar defteri de D-153'ü
> `PROVISIONAL_DECISION` olarak kaydetmişti. Durumu defterler belirlediği için
> sapan taraf başlıktı ve defter yükseletilmek yerine başlık hizalandı. Ayrıca bu
> başlık `v8-core/tests/benchmark_fabric_adversarial.rs` dosyasını referans  ediyordu; <!-- AUDIT-DOC-PATHS: NEGATIVE_CITATION `v8-core/tests/benchmark_fabric_adversarial.rs` is cited here precisely because it never existed; the real D-153 suite is `v8-core/tests/d153_benchmark_fabric_sabotage.rs`. -->
> bu dosya bu depoda hiç var olmadı. D-153 sabotaj suite'i
> `v8-core/tests/d153_benchmark_fabric_sabotage.rs` dosyasıdır. §2.6'daki
> "anlamsal ayrışma kaydı tutan açık tipli adapterlar" şartı, ratifikasyon
> anında sabit in-process vektörler olarak uygulanmıştı; bugün
> `v8-core/src/benchmark/parity.rs` içindeki esere bağlı adapterlar olarak
> uygulanmaktadır (issue #329). Her iki düzeltme de §§2–5'teki hiçbir normatif
> şartı değiştirmemektedir.

---

## 1. Yönetici Tezi ve Problem Tanımı

V8'in epistemik altyapısı önceden güçlü bireysel doğrulama organlarına sahipti:
- Assurance Fabric ve ClaimRegistry (D-131, D-148, D-150)
- Market World Foundry (D-141, D-144)
- System Proving Ground (D-141)
- PolicyEvidenceProfile ve G0–G9 senaryo kapıları (D-152)
- Kaizen araştırma geçmişi ve borç takibi (D-137, D-145)

Ancak politika-arası değerlendirme; birleşik, değişmez, içerik-adresli, çok
popülasyonlu bir benchmark protokolünden yoksundu. D-153 olmadan politika
karşılaştırmaları şu açıklıklara açıktı:
1. Benchmark çökmesi: benchmark yetenek skorlarının ekonomik hazırlık veya edge ile karıştırılması.
2. Değerlendirici artefact'ı: politikalara, belirli bir simülasyon ya da backtest kabuk tuzağına karşı optimizasyon yapma fırsatı.
3. Common-mode arızası: politika üreteçleri ile değerlendiriciler arasında özdeş varsayımlar.
4. Metrik telafisi: ılımlı rejimlerdeki güçlü performansın, kuyruk senaryolarındaki felaketi matematiksel olarak örtmesine izin verilmesi.
5. Kabul edilemez ileriye dönük iddialar: sentetik simülasyon başarısının gelecekteki nakit akışı olasılığına dışavumu.

D-153, **Benchmark Fabric (BF)**'i kurar: dondurulmuş politikaları yönetilen
gerçek, sentetik ve harici referans popülasyonları üzerinde değerlendiren, paralel
bir authority kökü yaratmadan çalışan, delile bağlı bir tanısal değerlendirme
ölçüm aletidir.

---

## 2. Epistemik Hiyerarşi ve Çökmeme Değişmezleri (Kurallar 57.1 – 57.8)

1. **Benchmark ≠ Assurance:** Benchmark Fabric tanısal ve karşılaştırmalı bir ölçüm aletidir. Tanısal göstergeler, arıza topolojileri ve göreli marjlar hesaplar. `SUPPORTED_EDGE` veya konuşlandırma yetkisi VERMEZ. Hazırlık ve terfi yetkisi münhasıran Assurance Fabric, G0–G9 kapıları ve ClaimRegistry'de kalır.
2. **CapabilityScore ≠ Readiness:** Benchmark CapabilityScore (0.0 – 100.0) çok boyutlu davranışsal yeteneği ölçer. Canlı yürütme hazırlığını ölçmez ve hiçbir sert kapıyı geçersiz kılamaz.
3. **CapabilityScore ≠ Future-Profit Probability:** CapabilityScore, gelecekteki getiriler üzerinde bir olasılık dağılımı değildir. Denetlenmiş bir `CapitalOutcomeProjection` olmadan bir benchmark skorunun doğrudan bir sermaye tahsis çarpanına dönüştürülmesi anayasal olarak yasaktır.
4. **Sert Kapılar Ortalama ile Silinemez:** Her benchmark hücresi ve `GateVector` içindeki her kapı (G0–G9, B0–B9) telafi edilemez. Zorunlu kapılardan herhangi birindeki sıfır veya başarısızlık, diğer alanlardaki 99+ skora rağmen toplam benchmark başarısızlığına yol açar.
5. **Sentetik Asimetri:** Sentetik değerlendirmeler sıkı biçimde asimetriktir:
   - Geçerli sentetik başarısızlık (`synthetic_fail_may_challenge`), sertifikalı bir World Passport kapsamındaki sağlamlık, yürütme güvenliği ve kararlılık iddialarını falsifiye edebilir.
   - Sentetik başarı (`synthetic_pass_confirms_no_edge`) sıfır ekonomik edge verir ve gelecekteki kârlılığı kanıtlayamaz.
6. **Harici Ölçüm Aleti Sınırları:** Harici değerlendiriciler (QuantConnect LEAN veya harici yürütme hakemleri gibi) egemen authority değil, ölçüm aleti olarak ele alınır. Açık tipli adapterların arkasında, anlamsal ayrışma ve parity atıf kaydı tutarak çalışmalıdırlar.
7. **Holdout ve Pristine Data Koruması:** Tüketilmiş holdout delili, yeniden adlandırarak veya benchmark vakaları içine sararak "unburn" edilemez. Yanmış tanı verisine karşı çalışan benchmark koşuları açıkça `BURNED_DIAGNOSTIC` olarak etiketlenmeli ve sıfır terfi ağırlığı taşımalıdır.
8. **Araştırma Borcu ve Çoklu Test Muhasebesi:** Benchmark koşuları araştırma trial bütçesi tüketir. Parametre süpürmeleri veya challenger iterasyonları boyunca her değerlendirme Kaizen trial borcunu artırır ve aile-geneli hurdle rate'i şişirir.

---

## 3. Benchmark Ontolojisi ve Şemaları

### 3.1 BenchmarkVersion
Deterministik, içerik-adresli bir sürüm tanımlayıcısı:
- `version_id`: Semantik sürüm dizesi (örn. `v8.5.0-bf1`).
- `specification_hash`: Tam benchmark şartnamesinin, popülasyon tanımlarının ve metrik denklemlerinin SHA-256 özeti.
- `created_at_utc`: ISO-8601 zaman damgası.
- `population_hashes`: Popülasyon adından değişmez manifest hash'ine eşleme.
- `is_frozen`: Benchmark bataryasının değişikliğe kilitli olduğunu gösteren boolean.

### 3.2 BenchmarkCase ve BenchmarkCaseManifest
Tek bir değerlendirme birimi:
- `case_id`: Benzersiz tanımlayıcı (örn. `BC-REAL-CHRON-01`, `BC-FOUNDRY-VOL-04`).
- `population_type`: `Real`, `SyntheticFoundry`, `ExternalReference` veya `StressDefeater`.
- `data_role`: `BURNED_DIAGNOSTIC`, `CROSS_VALIDATION`, `OUT_OF_SAMPLE_FROZEN`, `SYNTHETIC_GENERATED` veya `EXTERNAL_INDEPENDENT`.
- `archetype_or_family`: Belirli rejim alegorisi (A01–A12) veya Foundry ailesi (F01–F14).
- `environment_spec_hash`: Yürütme ortamı parametrelerinin (latency, slippage modeli, ücret tarifeleri) hash'i.
- `input_manifest`: Enstrüman, çözünürlük, zaman aralığı, bar sayısı ve veri içerik hash'ini içeren veri seti manifesti.

### 3.3 MetricObservation ve 10 Benchmark Alanı
Vaka başına 10 dik yetenek alanında kaydedilen gözlemler:
1. `PredictiveEdge`: Yönsel doğruluk, maliyet sonrası beklenti, bilgi oranı (yalnızca gerçek popülasyonlar).
2. `ExecutionEfficiency`: Efektif slippage sürükleme, maker doluş oranı, spread yakalama verimliliği.
3. `DrawdownResilience`: Maksimum drawdown, ulcer index, toparlanma süresi, kuyruk kaybı varyansı.
4. `VolatilityAdaptation`: Volatilite sıçramaları altında performans, kaldıraç duyarlılığı.
5. `StructuralStability`: Getirilerin durağanlığı, parametre perturbasyon duyarlılığı.
6. `RegimeRobustness`: Tüm alegori/ailelerdeki en kötü senaryo hücresi performansı.
7. `TailRiskConfinement`: Value-at-Risk containment, koşullu drawdown at risk (CDaR).
8. `CostModelIntegrity`: Gerçekçi ve düşmanca ücret modelleri sonrası brüt kazançların korunumu.
9. `ExternalRefereeParity`: Harici yürütme taban çizgilerine (LEAN / hakem) karşı hizalanma ve takıl hatası.
10. `DefeaterProximity`: En yakın falsifiye edici rejim perturbasyonuna uzaklık (reverse stress).

Her gözlem ham değeri, normalize skoru [0, 100], güven aralığını ve doğrulama durumunu kaydeder.

### 3.4 CapabilityScore Matematiği
Benchmark skoru şöyle hesaplanır:
$$\text{Score} = \left( \sum_{i=1}^{10} w_i \cdot \text{DomainScore}_i \right) \times \text{CoverageFactor} \times \prod_{j=1}^{m} \mathbf{1}_{\{\text{Gate}_j = \text{Pass}\}}$$
Burada:
- $\sum w_i = 1.0$; alan ağırlıkları önceden tanımlıdır ve `BenchmarkVersion` içinde dondurulmuştur.
- $\text{CoverageFactor} \in [0.0, 1.0]$ eksik veya atlanmış senaryo hücrelerini cezalandırır.
- `GateVector` içindeki zorunlu kapılardan herhangi biri başarısız olursa çarpım 0 olur ve nihai skor 0'a zorlanır (sert başarısızlık).

---

## 4. Popülasyon Taksonomisi ve Adapterlar

1. **Yanmış Tarihsel Tanı:** Mühendislik patolojisi tespiti için kullanılan geliştirme veri setleri (kanonik 12 aylık quad dahil). Her zaman `BURNED_DIAGNOSTIC` olarak işaretlenir.
2. **Kronolojik Gerçek Popülasyonlar:** Sıkı nedensel zaman sınırlarına sahip walk-forward örneklem-dışı dilimler.
3. **Purged Combinatorial Cross-Validation (CPCV):** Birden fazla bölüntü üzerinde dağılım kararlılığını ölçen, örtüşmeyen purged test katları.
4. **Market World Foundry Popülasyonları:** Doğrulanmış World Passport'larla üretilen sentetik dünyalar (D-141, D-144). Aşırı kuyrukları ve metamorfik değişmezliği değerlendirir.
5. **Reverse Stress Defeater Popülasyonu:** Politikanın arıza sınırını bulmak için tasarlanmış düşmanca minimal perturbasyon ortamları.
6. **Harici Yürütme Hakemi:** LEAN referans adapterı veya bağımsız işlem defteri üzerinden bağımsız işlem eşleştirme ve PnL hesaplaması.

---

## 5. CapitalOutcomeProjection ve Olasılık Sınırları

`CapitalOutcomeProjection` disiplinli, delil-sınırlı bir ileriye dönük sonuç görünümü temsil eder:
- `evidence_grade`: `DiagnosticOnly`, `SyntheticRobustnessOnly`, `ReplicationBacked` veya `EmpiricallyCertified`.
- `evidence_grade` değeri `DiagnosticOnly` veya `SyntheticRobustnessOnly` ise ileriye dönük olasılık iddiaları sıkı biçimde yasaktır.
- Sentetik popülasyonlar işin içindeyse, projekte edilen ileriye dönük kâr beklentisi `UNSUPPORTED_FORWARD_CLAIM` değerine kenetlenir.
- Yeniden yatırma/bileşik getiri modelleri likidite tabanlarını, piyasa kapasitesini ve yürütme sürüklemesini hesaba katmalıdır.

---

## 6. Kaizen Benchmark Entegrasyonu ve Trial Borcu

1. **Benchmark Delta Defteri:** Kaizen, Challenger ile Incumbent'ı karşılaştıran her benchmark koşusunun append-only bir makbuzunu kaydeder.
2. **Çoklu Test Düzeltmeleri:** Başarısız olan veya keşif amaçlı her benchmark koşusu genel trial sayacını ($N_{\text{trials}}$) artırır ve sonraki ardıllık iddiaları için gereken DSR/WRC istatistiksel eşiklerini sıkılaştırır.
3. **Bridge Çalışmaları:** Bir `BenchmarkVersion` güncellendiğinde veya yeniden kalibre edildiğinde, resmî bir bridge çalışması hem Incumbent'ı hem önceki taban çizgilerini her iki sürümde değerlendirmeli ve standart sürekliliğini garanti etmelidir.
