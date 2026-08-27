# D-150: Sürekli Epistemik Ardıllık ve Yaşayan Politika Anayasası

**Araştırma monografı, anayasa değişikliği adayı ve uygulama spesifikasyonu.**

`ONAY İÇİN TASLAK` • `NO_ECONOMIC_CLAIM` • `V8.5` • `2026-08-27`

Bu metin, mevcut anayasal, Kaizen, Oracle, delil, gölge (shadow), holdout veya hak-yetki kurallarının yerine geçmeksizin *V8 Araştırma Monografı*nı genişletir.

---

## 1. Belge durumu ve okuma kuralı

**ONAY İÇİN TASLAK / NO_ECONOMIC_CLAIM.** Bu belge `D-150 — Sürekli Epistemik Ardıllık ve Yaşayan Politika Anayasası`nı teklif eder. Araştırma destekli anayasal ve uygulama spesifikasyonudur. Bir alım-satım politikasını teşvik etmez, sermaye dağıtımına yetki vermez, yeni bir Oracle yaratmaz, Kaizen'in yerine geçmez veya sentetik delilleri ekonomik hakikate dönüştürmez.

Bu metin projenin `LITERATURE_SUPPORTED`, `PROJECT_EVIDENCE_SUPPORTED`, `DESIGN_INFERENCE`, `PROVISIONAL_DECISION`, `LOCKED_INVARIANT`, `OPEN_QUESTION` ve `REJECTED_OPTION` kelime dağarcığını devralır. Ayrıca mevcut V8 kısıtlamalarını korur: sentetik testler ekonomiyi kanıtlamaz; iddia yetkisi delil yetkisini aşamaz; ekonomik iddialar makbuza bağlı köken (provenance) gerektirir; ve mühürlenmiş değerlendirme nesneleri dokunulmazdır (immutable).

> **Temel tez.** D-150 yeni bir ticaret zekası alt sistemi değildir. V8'in delil anayasasına eksik olan zamansal yasayı ekler:
> $$\text{PolitikaKimliği} \neq \text{DelilDurumu}$$
> Bir politika byte düzeyinde tamamen aynı kalırken, kullanımını destekleyen deliller güçlenebilir, zayıflayabilir, tartışmalı hale gelebilir veya feshedilebilir (revoked).

---

## 2. Özet

V8 halihazırda iki güçlü ancak eksik fikir barındırmaktadır: Kaizen yoluyla politika evrimi ve dokunulmaz, yetkiye bağlı makbuzlar yoluyla delil egemenliği. Eksik olan, yeni deliller geldikçe değişmeyen bir politikanın geçerliliğinin nasıl evrildiğinin anayasal tanımıydı. Statik sertifikasyon, geçmişteki bir `PASS` sonucunu zamansızmış gibi ele alır. Bu varsayım, durağan olmayan finansal piyasalar, genişleyen sentetik/karşıt test uzayları, ileriye dönük gölge delilleri, yeni icra gözlemleri ve yeni keşfedilen başarısızlık mekanizmalarıyla bağdaşmaz [R1, R2, R3, R7].

D-150 **sürekli epistemik ardıllık** ilkesini getirir. Mühürlenmiş her değerlendirme dokunulmaz kalır. Yeni delil, halef bir `EvaluationEpoch` yaratır; eski bir davayı asla yeniden yazmaz. Her epoch; politikaya, koda, konfigürasyona, delil soyuna, dünya kapsamına, yetkiye ve zamana bağlı, geri alınabilir, skaler olmayan bir delil sertifikası üretir. Sertifika aktif kalabilir, yerini yenisine bırakabilir (`SUPERSEDED`), karantinaya alınabilir (`QUARANTINED`) veya iptal edilebilir (`REVOKED`). Maddi bir çürütme (defeater), teşhis, meydan okuyucu (challenger) inşası, korumalı değerlendirme ve olası ardıllık için mevcut Kaizen yaşam döngüsüne aktarılır [R8, R9, R10, R11, R13].

---

## 3. Kaynak temeli ve mevcut V8 monografı ile ilişkisi

**PROJECT_EVIDENCE_SUPPORTED.** V8 kod tabanı ve monografı D-150'nin yeniden kullandığı temelleri içerir: yanlışlama öncelikli anayasa; zaman-içi (Point-in-time) `MarketState`; değişmez ekonomik nesneler; 3 boyutlu Yetki tensörü (`EvidenceAuthority`, `DecisionAuthority`, `RealizationStatus`); altı yasal iddia sınıfı (`StatutoryClaimClass`); D-136 `EvidenceGraph`; D-141 Uzman yeterliliği; D-138 ileriye dönük gölge makbuzları; yegane kural koyucu araştırma/hüküm patikası olarak Kaizen; ve salt okunur `AuthorityProjection`, ayrık `SUPPORTED_EDGE`/`REALIZED_CASHFLOW`, sentetik M0 izolasyonu ve değişmez `EvaluationCase` epoch'ları içeren V8.5 M0 adayı.

D-150 bu nedenle V8.5 mimarisini baştan başlatmaz. Tek bir eksik sözleşmeyi kapatır: bir dava mühürlendikten sonra delil geçerliliğinin yaşam döngüsü.

---

## 4. Problem: Durağan olmayan dünyada statik sertifikasyon

### 4.1 Statik PASS bir kaza ebediyet iddiasıdır

```
politika
  ↓
değerlendirme
  ↓
PASS
  ↓
sertifika
  ↓
???
```

Eksik ok problemdir. Statik bir sertifika, piyasa dağılımı değiştiğinde, yeni bir arıza ailesi keşfedildiğinde, icra kalitesi düştüğünde veya daha güçlü bir değerlendirici geldiğinde ne olacağını söylemez. Kavram kayması ve dağılım kayması, istisnai durumlar değil, zaman serisi sistemlerinin olağan özellikleridir [R2, R3, R4].

### 4.2 Eski davayı yeniden açmak epistemik olarak yıkıcıdır

Yeni gözlemler aynı mühürlü nesneye eklenirse, `case_hash`, delil seti, ispat yükü ve hüküm soyu zamana bağlı değişken bir duruma dönüşür. Tarihsel bir karar verildiğinde tam olarak neyin bilindiğini yeniden inşa etmek imkansız hale gelir. D-150 bunun yerine değerlendirmeyi, değişmez enstantanelerin yalnızca-ekleme (append-only) ardıllığı olarak ele alır.

> **Reddedilen model:** `certificate.json` yeni testler geldikçe değerlerin üzerine yazıldığı değişken bir pano satırıdır. Bu model tarihsel denetlenebilirliği yok eder.

---

## 5. Araştırma hedefi

D-150 tek bir soruyu yanıtlar:

$$\text{Değişmeyen bir } P \text{ politikası verildiğinde, geçmişi yeniden yazmadan, yetkiyi yükseltmeden veya Kaizen'i atlamadan, } t \text{ anında yeni kabul edilebilir delil geldiğinde V8, } P\text{'nin epistemik durumunu nasıl güncellemelidir?}$$

Hedef sistem **yaşayan bir politika**dır: kendi kendini değiştiren canlı bir strateji değil, aktif kalma hakkı sürekli olarak güncel delillere bağlı olan bir politika.

$$\text{GüncelDestek} = f(\text{PolitikaKimliği}, \text{DelilEpochu}, \text{Yetki}, \text{İspatYükü}, \text{Zaman})$$

Bu nedenle araştırma hedefi "daha fazla test" değildir. **Sürekli yanlışlanabilirlik** için yönetilen bir mekanizmadır.

---

## 6. Hedef dışı konular ve anayasal sınır

| D-150 yapar | D-150 açıkça YAPMAZ |
|---|---|
| Zaman içinde delil geçerliliğini sürümler. | Dördüncü bir Oracle yaratmaz. |
| Değişmez ardıl değerlendirme epoch'ları oluşturur. | İkinci bir Kaizen yaratmaz. |
| Yeni delilin mevcut güvenceyi geçersiz kılmasını, karantinaya almasını veya iptal etmesini sağlar. | Mevcut politikayı otomatik olarak mutasyona uğratmaz. |
| Maddi çürütücüleri (defeater) Kaizen'e iletir. | Meydan okuyucuları (challenger) otomatik terfi ettirmez. |
| Sertifikaları dünya/delil kapsamına ve yetkisine bağlar. | Sentetik dayanıklılığı `SUPPORTED_EDGE`'e dönüştürmez. |
| Tarihsel kararları birebir korur. | Eski makbuzları yerinde yeniden yazmaz veya "düzeltmez". |
| Beyan edilen istatistiksel planlar altında sürekli izlemeye izin verir. | Tekrarlanan gözlemlemeyi istatistiksel olarak bedava kılmaz. |

---

## 7. Araştırma sentezi

### 7.1 Sürekli değerlendirme
Robustness Gym, statik bir test nesnesinin gelişen koşulları ve sınırlamaları öngörememesi nedeniyle değerlendirmeyi sürekli bir uygulayıcı süreci olarak açıkça çerçeveler [R1]. AndroidWorld gibi dinamik kıyaslamalar, tek bir değişmez test kümesine dayanmak yerine parametreli görev varyasyonları üretir [R6]; MACEval benzer şekilde kapalı uçlu kıyaslama aşırı uyumunu azaltmak için boylamsal değerlendirmeyi hedefler [R7]. V8'in analoğu, kendi iyiliği için kıyaslama karmaşası değil, tam mevcut politikaya bağlı yeni delil dönemleridir.

### 7.2 Dağılım kayması akış teşhisi
Sıralı kayma tespiti çalışmaları, birikmiş devreye alma maliyetini önlemek için değişiklikleri yeterince erken tespit etmeyi vurgular [R3]. Martingallerle Tanısal Çalışma Zamanı İzleme, çoklu akış monitörlerinin kayma nedenlerini ayırt etmeye ve bunları uygun müdahalelere bağlamaya yardımcı olabileceğini gösterir [R4]. Bu, D-150'nin izlemeyi tek bir sağlık puanına daraltmak yerine tiplendirilmiş `DefeaterReceipt`'leri koruma seçimini destekler.

### 7.3 Sıralı istatistikler
Tekrarlanan izleme, tek bir sabit örneklemli hipotez testine eşdeğer değildir. Sıralı model güven kümeleri, zaman açısından tekdüze izleme garantileri sağlamak için e-süreçleri / güven dizilerini kullanır [R5]; sağlam güven dizisi çalışmaları, açık kontaminasyon varsayımları altında her an geçerli aralıkların nasıl oluşturulabileceğini gösterir [R14]. D-150 bu nedenle sıralı istatistiksel delillere yalnızca varsayımları ve durdurma kuralı açık olan bildirilmiş bir izleme planı aracılığıyla izin verir.

### 7.4 Üretilen ve nedensel piyasa dünyaları
Nedensel piyasa simülatörleri, bildirilen nedensel yapıyı koruyan karşıolgusal finansal yörüngeler üretmeyi amaçlar [R8]. Financial Wind Tunnel, stres testi için kontrol edilebilir sentetik senaryolar geliştirir [R9], GAN-Diffusion çerçevesi ise stilize edilmiş olguların ve varlıklar arası bağımlılığın önemsiz üretim problemleri olarak kaldığını vurgular [R10]. D-150'nin sonucu ihtiyatlıdır: üretilen dünyalar dayanıklılık kanıtlarını genişletebilir, ancak üretilen başarı gerçek ekonomik kanıt haline gelmez.

### 7.5 Karşıt birlikte evrim ve değerlendirici ardıllığı
COvolve, yeni ortamların politika zayıflıklarını ortaya çıkarması için çevre ve politika tasarımcılarını açıkça birlikte geliştirir [R11]. FAMOU'nun çalışması, stratejiler geliştikçe sabit değerlendiricilerin bayatlayabileceğini savunur ve bu nedenle değerlendirici birlikte evrimini ve zayıflık baskısını sunar [R12]. D-150, oyun varsayımlarını içe aktarmadan aynı üst düzey içgörüyü kullanır: test dağılımı evrilebilir, bu nedenle sertifika geçerliliği yalnızca politika kimliğine değil, belirli bir delil dönemine bağlı olmalıdır.

### 7.6 Ters stres
Son ters stres çalışmaları, ampirik bağımlılık yapısını korurken şoklara bağlı tutarlı çok değişkenli senaryolar oluşturur [R13]. Bu, yeni minimal makul bozucuların ekonomik iddia yetkisi elde etmeden bir sağlamlık iddiasını geçersiz kılabileceği gelecekteki bir Dökümhaneyi destekler.

---

## 8. Çekirdek model: Politika × Delil × Zaman

```
                   POLİTİKA SOYU
            P17 ───────────────────────► P18
             │                           ▲
             │                           │
             │ E0  ACTIVE                │
             │ E1  ACTIVE                │
             │ E2  CONTESTED             │
             │ E3  REVOKED ──Defeater────┘
             │
             ▼
         DELİL SOYU
```

Kaizen halihazırda yatay ekseni sürümler: **politika ardıllığı**. D-150 dikey ekseni ekler: **değişmeyen bir politika için delil ardıllığı**.

$$\text{PolitikaKimliği}(P_{17}, E_0) = \text{PolitikaKimliği}(P_{17}, E_3)$$
$$\text{DelilDurumu}(P_{17}, E_0) \neq \text{DelilDurumu}(P_{17}, E_3)$$

Kavramsal ekleme budur. D-150 bu nedenle Kaizen'e rakip değil, Kaizen ortamına bir anayasa değişikliğidir.

---

## 9. Kanonik mimari

```
 GERÇEK PİYASA ────────────┐
 GÖLGE / PROSPECTIVE ──────┤
 SENTETİK DÜNYALAR ────────┤
 KARŞIT DÜNYALAR ──────────┤
 D-136 / D-141 ────────────┤
 3 ORACLE ─────────────────┘
             │
             ▼
        DELİL GİRİŞİ
             │
     kabul + yetki projeksiyonu
             │
             ▼
     DEĞERLENDİRME EPOCHU
      değişmez / hash-bağlı
             │
             ▼
      GÜVENCE DOKUSU
             │
      ┌──────┴──────┐
      ▼             ▼
   DESTEKLİ      DEFEATER
      │             │
      ▼             ▼
  sertifika      KAIZEN
  ardıllığı      teşhisi
      │             │
      │         challenger
      │             │
      └──────┬──────┘
             ▼
        SONRAKİ EPOCH / POLİTİKA
```

**Sahiplik kuralı.** D-150 zamansal delil durumuna sahiptir. Assurance delil bileşimine sahiptir. Kaizen politika iyileştirmesine ve normatif ardıllığa sahiptir. ClaimRegistry mevcut normatif yolda kalır.

---

## 10. Kanonik nesneler

### 10.1 EvaluationCaseManifest
```
EvaluationCaseManifest {
  case_id, policy_hash, code_hash, config_hash,
  production_growth_contract_id, information_contract_id,
  utility_contract_id, cost_model_id, capacity_model_id,
  universe_id, authority_projection_id, created_at, sealed_hash
}
```
Manifest neyin yargılandığını tanımlar. Bir kez mühürlendikten sonra dokunulmazdır.

### 10.2 EvaluationEpoch
```
EvaluationEpoch {
  epoch_id, case_id, parent_epoch_id?,
  evidence_delta_hash, cumulative_evidence_root,
  world_coverage_root, monitoring_plan_id?,
  assurance_receipt_id, certificate_id, opened_at, sealed_at
}
```
Epoch değişken bir zaman kovası değildir. Beyan edilen bir delil tetikleyicisi yeniden yargılama gerektirdiğinde üretilen değişmez bir ardıl enstantanedir.

### 10.3 ProductionEvidenceCertificate
```
ProductionEvidenceCertificate {
  certificate_id, policy_hash, epoch_id, claim_vector,
  hard_defeaters, authority_bounds, world_coverage,
  statistical_plan_ids, status, issued_by_verdict_receipt,
  supersedes?, revokes?
}
```

---

## 11. Sertifika durum makinesi

```
               ┌──────────────┐
               │    ACTIVE    │
               └──────┬───────┘
                      │ yeni epoch
          ┌───────────┼────────────┐
          │           │            │
          ▼           ▼            ▼
     SUPERSEDED   QUARANTINED    REVOKED
          │           │            │
          │           │            └──► Kaizen teşhisi
          │           └──► ek delil gereklidir
          └──► halef sertifika günceldir
```

| Durum | Anlam | Sermaye semantiği |
|---|---|---|
| `ACTIVE` | Mevcut delil dönemi bildirilen güvence taleplerini karşılar. | Mevcut yetkili politikanın ötesinde yeni bir ekonomik yetki yoktur. |
| `SUPERSEDED` | Aynı politika/dava soyu için daha yeni bir sertifika mevcuttur. | Yalnızca tarihseldir; güncel yetki değildir. |
| `QUARANTINED` | Delil tartışmalıdır, eskidir, eksiktir veya ölümcül olmayan bir endişe çözüm gerektirir. | Dağıtım politikası önceden var olan operasyon/risk kurallarını takip eder; D-150 tek başına geri dönüş icat etmez. |
| `REVOKED` | Güçlü bir çürütücü (hard defeater) zorunlu bir iddiayı veya ön koşulu geçersiz kılar. | Mevcut güvence geri çekilir; maddi başarısızlık Kaizen'e ve mevcut yönetişime devredilir. |

---

## 12. Yalnızca-ekleme (append-only) epoch kanunu

1. Mühürlenmiş bir `EvaluationCaseManifest` asla değiştirilemez.
2. Mühürlenmiş bir `EvaluationEpoch` asla değiştirilemez.
3. Yeni delil asla eski bir makbuzu düzenlemez; ardıl bir epoch yaratır.
4. Ardıl epoch ebeveynini, delil deltasını, kümülatif delil kökünü ve güncel yargıyı kriptografik olarak bağlar.
5. Tarihsel sertifikalar, tarihsel delil kümeleri altında neyin desteklendiğinin geçerli açıklamaları olarak kalır; güncel yetki olmaktan çıkabilirler.
6. Hatalı bir tarihsel nesneye yapılan herhangi bir düzeltme, asla üzerine yazma olarak değil, yeni bir geçersiz kılma/yenisiyle değiştirme nesnesi olarak temsil edilir.

$$\text{YeniDelil}(t+1) \implies \text{YeniEpoch}(t+1), \quad \text{asla } \text{MutasyonaUğrat}(\text{Epoch}_t) \text{ DEĞİL}$$

---

## 13. Yeni bir epoch'u ne oluşturur?

| Tetikleyici | Örnek | Gerekli eylem |
|---|---|---|
| İleriye dönük piyasa delili | Yeni gölge haftası/ayı tamamlanır. | İzleme manifestosu gözlem sınırını bildirirse epoch oluşturun. |
| Dağılım kayması | Bildirilen kayma monitörü eşiği aşar. | Tanısal makbuzu mühürleyin; ilgili iddiaları yeniden karara bağlayın. |
| Yeni sentetik/karşıt aile | Dökümhane varlıklar arası bulaşma dünyalarını ekler. | Yeni dayanıklılık dönemi; bağımsız gerçek deliller değişmedikçe ekonomik iddialara dokunulmaz. |
| Minimal makul çürütücü | Ters stres yakındaki bir arıza yüzeyi bulur. | Etkilenen dayanıklılık veya hayatta kalma iddiasına meydan okuyun/iptal edin. |
| Değerlendirici kusuru | D136 sağlayıcısı veya D141 oracle'ı geçersiz kılınır. | Bağımlı delilleri geçişli olarak geçersiz kılın ve bir ardıl dönem üretin. |
| İcra modeli değişikliği | Ücret/kayma/kapasite varsayımı değişir. | Yeni dava veya dava ailesi sürümü; karşılaştırılabilirliğin değişmediğini varsaymayın. |
| Politika/kod/konfig değişikliği | Mevcut mantık değişir. | Yalnızca yeni delil dönemi değil, yeni politika soyu/davası. |

---

## 14. D-150 altında delil kabul edilebilirliği

D-150 delil yetkisini yeniden tanımlamaz. V8.5 kabul kurallarını tüketir.

| Delil kaynağı | Neyi etkileyebilir | Kendi başına neyi tesis EDEMEZ |
|---|---|---|
| Gerçek korumalı OOS | Ekonomik replikasyon, istatistiksel delil, beyan edilen yetki dahilinde hata teşhisi. | Gerçek mekan uzlaşmalı delil olmadığı sürece fiziksel gerçekleşmiş nakit akışı. |
| İleriye dönük gölge (shadow) | Gölge sözleşmesine bağlı olarak prospektif davranış, kayma, operasyonel geçerlilik. | Otomatik terfi veya uzlaşma yetkisi. |
| Sentetik dünyalar | Dayanıklılık, anlamsal tutarlılık, güvenlik, karşı örnek keşfi. | `SUPPORTED_EDGE`, beklenen gerçek getiri, `REALIZED_CASHFLOW`. |
| Karşıt / ters stres | Negatif delil, güçlü çürütücüler (hard defeaters), güvenlik açığı topolojisi. | Pozitif ekonomik avantaj (edge). |
| D141 | Uzman semantik yeterliliği ve sınırlandırılmış davranışsal iddialar. | Kârlılık. |
| Hindsight / Target Oracle | Sınırlar, kurtarılabilirlik, pişmanlık, beyan edilen yetki altında karar alanı analizi. | Destekleyici delil olmadan gerçekleşmiş nakit akışı veya ex-ante seçilebilirlik. |

---

## 15. Zamansal delil kaynağı olarak Piyasa Dünyası Dökümhanesi

D-150 Dökümhaneyi yaratmaz. Dökümhane geliştikçe mevcut güvenceye ne olacağını tanımlar. Bu önemlidir çünkü sentetik piyasa araştırması da evrilmektedir: nedensel simülatörler karşıolgusal geçerliliği hedefler [R8]; kalite odaklı GAN/difüzyon çalışmaları stilize olguları ve çok değişkenli bağımlılığı hedefler [R10]; ve kontrol edilebilir simülatörler politikaları tek bir tarihsel bandın dışındaki koşullara maruz bırakır [R9].

```
Foundry v1
  ├─ yapısal
  ├─ blok yeniden örnekleme
  └─ cerrahi
       │
       ▼
P17 / Epoch 4 → ROBUSTNESS_SUPPORTED

Foundry v2
  ├─ çoklu varlık bulaşması
  ├─ dallanan karşıolgusallar
  └─ ters stres
       │
       ▼
P17 / Epoch 7 → YENİ_DEFEATER → QUARANTINE / REVOKE
```

**Anayasal sonuç:** önceki bir dayanıklılık PASS sonucu, beyan edilen dünya kapsamı hakkında dürüst bir tarihsel iddia olarak kalır, ancak test evreni genişledikten sonra otomatik olarak yeterli olmaz.

---

## 16. Değerlendirici esareti olmaksızın birlikte evrim

Karşıt birlikte evrim caziptir çünkü politika adapte oldukça sabit bir değerlendirici bayatlayabilir [R11, R12]. V8 yine de bir ajanın değerlendiriciyi lehte bir not vericiye dönüştürmesini engellemelidir.

| İzin Verilen | Yasak Olan |
|---|---|
| Dünya popülasyonu yeni arıza yüzeylerini ortaya çıkaracak şekilde evrilir. | Politika ajanı sonuçları gördükten sonra kendi mühürlü yeterlilik dünyalarını düzenler. |
| Yeni değerlendirici aileleri yeni sürümlenmiş delil kaynakları haline gelir. | Yeni değerlendirici tarihsel delil semantiğini sessizce geçersiz kılar. |
| Daha zorlu dünyalar yeni negatif/dayanıklılık kanıtları üretir. | Sentetik başarı ekonomik kanıta yükseltilir. |
| Politika ve dünya popülasyonları geliştirmede birlikte evrilebilir. | Korumalı ekonomik OOS, dünya/politika birlikte evrimine katılır. |
| Politika dondurulduktan sonra taze yenilik kasası dünyaları üretilir. | Yeterlilik tohumları politika üretim ajanına ifşa edilir. |

D-150 her değerlendirici/dünya ailesi sürümünü epoch kimliğine bağlar, böylece değerlendirici evrimi görünmez olmak yerine denetlenebilir hale gelir.

---

## 17. İleriye dönük gölge ve yaşayan delil

D-138 halihazırda otomatik ekonomik iddiası olmayan, hash-bağlı gölge makbuzları sağlar. D-150 bu makbuzlara zamanda bir yer verir. Bir gölge gözlem penceresi orijinal terfi davasını mutasyona uğratmaz; ardıl bir epoch'a delil deltası sağlar.

```
P17 / E0  politika donduruldu
   │
   ├── gölge penceresi S1 ──► E1
   ├── gölge penceresi S2 ──► E2
   └── kayma / başarısızlık ──► E3 → QUARANTINE / REVOKE
```

Bu, sürekli görüntülenen bir akışı tekrar tekrar açılan bir OOS testine dönüştürmeden ileriye dönük izlemeyi denetlenebilir hale getirir.

---

## 18. Sıralı izleme ve isteğe bağlı durdurma güvenlik duvarı

Sürekli değerlendirme istatistiksel bir tuzak yaratır: sıradan sabit ufuklu p-değerlerinin tekrar tekrar incelenmesi yanlış alarm riskini şişirebilir. D-150 bu nedenle **operasyonel izleme delillerini** tek seferlik ekonomik terfi delillerinden ayırır. Sürekli istatistiksel çıkarım gerektiğinde, `MonitoringPlan` uygun bir e-süreci veya güven dizisi gibi zaman açısından geçerli bir yöntemi, varsayımlar, tahmin edilen değer (estimand), güncelleme sıklığı ve durdurma semantiği ile birlikte belirtmelidir [R5, R14].

```
MonitoringPlan {
  estimand, data_stream, update_rule, method_id, assumptions,
  alert_boundary, minimum_information, action_on_alert
}
```

**Kural:** D-150 projenin `SUPPORTED_EDGE` için mevcut WRC + gerçek DSR + Hansen SPA yükünü ortadan kaldırmaz. Sıralı izleme, açıkça onaylanmış bir yöntem ikamesi ekonomik yükü değiştirmediği sürece ayrı bir delil kanalıdır.

---

## 19. Güçlü çürütücüler ve geçişli fesih

D-150 yenilgiyi ortalamak yerine bağımlılık ilişkileri üzerinden yaymalıdır.

| Çürütücü (Defeater) | Anında etki |
|---|---|
| PIT / geleceği okuma ihlali | Kirlenmiş yörüngeye bağımlı olan her iddiayı iptal edin. |
| Defter/nakit akışı koruma hatası | Bu deftere bağımlı ekonomik iddiaları engelleyin. |
| Yetki yükseltme | Türetilen iddiayı ve projeksiyon yolunu geçersiz kılın. |
| Değerlendirici tahrifatı / öz-sertifikasyon | Değerlendiriciden türetilen delilleri geçersiz kılın ve bağımsız denetimi tetikleyin. |
| Holdout yeniden kullanımı | Etkilenen soy için OOS yetkisini yakın. |
| Yeni felaket potansiyeline sahip makul dünya | Karşılık gelen dayanıklılık/hayatta kalma iddiasına meydan okuyun; ilişkisiz gerçek delilleri silmez. |
| İcra yetkisi uyumsuzluğu | Daha güçlü dolum/etki semantiği gerektiren iddiaları düşürün/bilinmeyene alın. |

$$\text{GüçlüÇürütücü}(\text{gerekli\_alt\_iddia}) \implies \text{Üstİddia PASS kalamaz}$$

---

## 20. Kaizen devri: delil evrimi → politika evrimi

D-150 Kaizen'in başladığı yerde biter.

```
Yeni delil
    ↓
EvaluationEpoch
    ↓
Assurance yargısı
    ↓
DefeaterReceipt
    ↓
sertifika QUARANTINED / REVOKED
    ↓
KAIZEN
    ↓
teşhis
    ↓
hipotez
    ↓
değişmez meydan okuyucu (challenger)
    ↓
DEV / WFA / korumalı değerlendirme
    ↓
yeni politika soyu
```

D-150 yeniden değerlendirme talep edebilir veya bir defeater üretebilir, ancak parametreleri seçemez, ekonomik bir meydan okuyucu üretemez veya normatif bir terfi basamaz. Bu, Kaizen'i çoğaltmak yerine mevcut egemenliğini korur.

---

## 21. Veri rolü ve holdout semantiği

Delil ardıllığı soya göreceli olmalıdır. Bir veri kümesi doğası gereği "sonsuza kadar OOS" değildir; rolü bir politika/araştırma soyuna ve beyan edilen bir kullanıma göre tanımlanır.

```
DataRoleLedger / Soy L17
  2022-2024  DEVELOPMENT
  2025-H1    GENERATOR_CALIBRATION
  2025-H2    GENERATOR_VALIDATION
  2026-H1    POLICY_FROZEN_OOS
  2026-H2    PROSPECTIVE_SHADOW
```

L17 için korumalı OOS'un açılması bir `HoldoutBurnReceipt` oluşturur. Halef bir politika ortaya çıkan sonuçları geliştirme bilgisi olarak kullanabilir, ancak aynı bant halef soy için dokunulmamış OOS yetkisini geri kazanamaz.

---

## 22. Dünya kapsamı sertifika kimliğinin parçasıdır

Dünya uzayı beyanı olmayan bir dayanıklılık sertifikası anlamsızdır. D-150 bu nedenle dayanıklılıkla ilgili her döneme bir `WorldCoverageManifest` bağlar.

```
WorldCoverageManifest {
  generator_families, generator_versions, parameter_domains,
  seed_roots, scenario_count, behavioral_cells, cross_asset_cells,
  tail_stress_cells, execution_stress_cells, novelty_vault_id?,
  generator_passport_ids
}
```

Tek başına dünya sayısı bir kapsam metriği değildir. On bin adet birbirine yakın kopya yol, dikkatle oluşturulmuş minimal bir makul bozucudan daha az bilgi sağlayabilir. Bu nedenle sertifika yalnızca `N_worlds`ü değil, aile ve davranış uzayı kapsamını da tutmalıdır.

---

## 23. Kaizen girdisi olarak başarısızlık fenotipleri

D-150 belirli bir hata genomu uygulaması gerektirmez, ancak sürekli delilleri eyleme geçirilebilir kılan kayıp ayrıştırma makbuzunu standartlaştırır.

```
FailureAttribution {
  detection_loss, representation_loss, selection_loss,
  allocation_loss, execution_loss, exit_capture_loss, friction_loss,
  interactions, unidentified_residual
}
```

Bu, sürekli döngünün "PnL düştü, başka bir filtre ekle"ye dönüşmesini engeller. Yeni bir dönem hangi iddianın veya mekanizmanın bozulduğunu belirlemeli ve Kaizen vekil metrikleri körü körüne optimize etmek yerine bu mekanizmayı hedeflemelidir.

---

## 24. Referans algoritmalar

### 24.1 Algoritma A — yeni delil girişi
```rust
fn ingest_evidence(case, current_epoch, evidence) {
    verify(case.sealed_hash);
    verify(current_epoch.sealed_hash);
    verify(evidence.provenance);
    admissibility = classify_for_claims(evidence);
    authority = project_authority_read_only(evidence);

    if evidence_changes_policy_code_config_or_contract(evidence) {
        return NEW_CASE_REQUIRED;
    }

    delta = EvidenceDelta(evidence, admissibility, authority);
    next_epoch = seal_successor_epoch(current_epoch, delta);
    return adjudicate(next_epoch);
}
```

### 24.2 Algoritma B — ardıl epoch yargısı
```rust
fn adjudicate(epoch) {
    graph = reconstruct_cumulative_assurance_graph(epoch);
    propagate_invalidations(graph);
    verdict_vector = evaluate_claim_rules(graph);

    if hard_required_claim_fails(verdict_vector) {
        certificate = REVOKED_or_QUARANTINED;
        emit DefeaterReceipt;
        handoff_to_kaizen();
    } else {
        certificate = ACTIVE;
    }

    supersede_previous_current_certificate();
    seal_all_outputs();
    return certificate;
}
```

---

## 25. Önerilen anayasal değişmezler

1. **D150-I01 — Zamansal Koşulluluk:** hiçbir politika sertifikası zamansız değildir.
2. **D150-I02 — Dokunulmaz Tarihçe:** mühürlenmiş davalar, epoch'lar ve makbuzlar yalnızca-eklenirdir.
3. **D150-I03 — Yeni Delil / Yeni Epoch:** yargı durumunu değiştiren kabul edilebilir yeni delil ardıl bir epoch oluşturur.
4. **D150-I04 — Politika / Delil Ayrımı:** politika kimliği ve delil durumu bağımsız eksenlerdir.
5. **D150-I05 — Yetki Yükseltme Yasağı:** ardıllık, delil yetkisini kaynaklarının ötesine yükseltemez.
6. **D150-I06 — İddiaya Özel Kabul Edilebilirlik:** delil bir iddia için kabul edilebilir, diğeri için yasak olabilir.
7. **D150-I07 — Sentetik Ekonomik-Olmayan Yasası:** sentetik pozitif sonuçlar ekonomik avantajı veya gerçekleşmiş nakit akışını kanıtlayamaz.
8. **D150-I08 — Negatif Sentetik Güç:** sentetik/karşıt deliller bildirilen makullük/yetki dahilinde dayanıklılık iddialarını yanlışlayabilir veya bunlara meydan okuyabilir.
9. **D150-I09 — Güçlü Çürütücü Baskınlığı:** gerekli güçlü arızalar ilişkisiz başarılarla ortalanamaz.
10. **D150-I10 — Değerlendirici Sürüm Bağlama:** değerlendirici/dünya ailesi sürümleri epoch kimliğinin parçasıdır.
11. **D150-I11 — Sıralı Gözetleme Güvenlik Duvarı:** sürekli istatistiksel izleme zaman açısından geçerli yöntemler gerektirir veya tanısal kalır.
12. **D150-I12 — Kaizen Egemenliği:** D-150 otonom olarak bir politika meydan okuyucusu üretemez veya terfi ettiremez.
13. **D150-I13 — Yasal Hak Basma Sürekliliği:** ClaimRegistry hak basma yetkisi mevcut Kaizen/yargı/denetim yolunda kalır.
14. **D150-I14 — Holdout Yakımı:** ortaya çıkarılan korumalı OOS, etkilenen soy için dokunulmamış yetkiyi geri kazanamaz.
15. **D150-I15 — İptal Birinci Sınıftır:** iptal tarihin olağanüstü bir bozulması değil, sıradan bir yaşam döngüsü durumudur.
16. **D150-I16 — Bilinmeyen Yasaldır:** yetersiz veya karşılaştırılamaz delil uydurma güven değil, `UNKNOWN`/`QUARANTINED` üretir.
17. **D150-I17 — Kapsama Bağlı Dayanıklılık:** dayanıklılık iddiaları dünya/değerlendirici kapsamını adlandırmalıdır.
18. **D150-I18 — Otomatik Terfi Yasağı:** biriken PASS epoch'ları ekonomik terfi yükünü asla atlatamaz.

---

## 26. Zorunlu D-150 sabotaj süiti

| ID | Sabotaj | Beklenen sonuç |
|---|---|---|
| `D150-T01` | Mühürlü EvaluationCase'i değiştirme. | Panik/engelleme: dokunulmaz dava ihlali. |
| `D150-T02` | Sertifikadan sonra mühürlü epoch'u değiştirme. | Panik/engelleme. |
| `D150-T03` | E0'ı düzenleyerek gölge delili ekleme. | Reddetme; E1 gerektirir. |
| `D150-T04` | Sentetik PASS ile SUPPORTED_EDGE basmaya çalışma. | Kabul edilemez. |
| `D150-T05` | Sentetik FAIL ile dayanıklılık ön koşuluna saldırma. | Çürütücü üst iddiaya yayılır. |
| `D150-T06` | Yeni delilde PIT ihlali görünmesi. | Bağımlı güncel güvence iptal edilir. |
| `D150-T07` | Halefinden sonra eski sertifikanın güncel kalması. | Başarısız; eskisi SUPERSEDED olmalıdır. |
| `D150-T08` | Politika hash'i değişir ancak kod yalnızca delil epoch'u oluşturmaya çalışır. | Başarısız; yeni dava/politika soyu gerekir. |
| `D150-T09` | Epoch bağlaması olmadan değerlendirici sürümü değişir. | Başarısız. |
| `D150-T10` | Tekrarlanan sabit p-değeri izlemesi. | Tanısal delil olarak kalır / zaman-geçerli delil olarak engellenir. |
| `D150-T11` | Holdout-yakılmış verinin dokunulmamış OOS olarak yeniden sunulması. | Kapalıya düşer (fail closed). |
| `D150-T12` | Assurance Fabric doğrudan ClaimRegistry'ye yazar. | Derleme/yetenek hatası. |
| `D150-T13` | D-150 doğrudan meydan okuyucu parametreleri oluşturur. | Yetenek hatası. |
| `D150-T14` | Güçlü çürütücünün birçok PASS metriğiyle ortalanması. | FAIL kalır. |
| `D150-T15` | Tanımlanamayan delilin sıfıra zorlanması. | Başarısız; UNKNOWN korunur. |
| `D150-T16` | Yeni Foundry ailesi mevcut politikayı bozar. | Yalnızca etkilenen iddialar için yeni epoch + meydan okuma/iptal. |
| `D150-T17` | İptalden sonra tarihsel sertifikanın silinmesi. | Başarısız; tarih yeniden inşa edilebilir kalmalıdır. |
| `D150-T18` | Ebeveyn epoch hash uyumsuzluğu. | Soy doğrulama hatası. |
| `D150-T19` | Sertifikanın delil/dünya kapsam kökünden yoksun olması. | Düzenleme başarısız olur. |
| `D150-T20` | Tüm izleme PASS'lerinin otomatik terfi denemesi. | Başarısız; terfi yetkisi değişmez. |

---

## 27. Asgari uygulama düzeni

D-150 paralel bir bürokrasi olarak değil, mevcut V8.5 güvence/Kaizen yüzeylerinin dar bir uzantısı olarak uygulanmalıdır.

```
v8-core/src/assurance/
  continuous.rs      # EvaluationEpoch ardıllık mantığı
  certificate.rs     # sertifika yaşam döngüsü / durum makinesi
  case.rs            # mühürlü EvaluationCase kimliği
  defeater.rs        # güçlü çürütücü makbuzları
  receipt.rs         # epoch/sertifika kriptografik bağları

v8-core/src/kaizen/
  ...                # mevcut teşhis/challenger/deney/karar yolu

v8-core/src/shadow.rs
  ...                # değişmeyen kaynak sınırı; makbuzlar ardıl dönemleri besler

v8-core/src/world/
  ...                # dünya delil kaynağı; D-150 ekonomik yetki vermez
```

**Uygulama tercihi.** Mevcut bir modül davranışı sahiplenebiliyorsa hiçbir yeni alt sistem eklenmemelidir. En küçük doğru uygulama tercih edilir.

---

## 28. D-147 / D-148 / D-149 ve mevcut hukukla uyumluluk

| Mevcut karar | D-150 muamelesi |
|---|---|
| D-132 Kaizen/Claim egemenliği | Korundu. D-150 ikinci bir karar veya basım yolu yaratmaz. |
| D-136 EvidenceGraph | Delil/yargı alt tabakası olarak yeniden kullanıldı. |
| D-138 Shadow | İleriye dönük makbuz kaynağı olarak yeniden kullanıldı; D-150 zaman içindeki etkisini sürümler. |
| D-141 Expert Proving Ground | Yeterlilik makbuzları ardıl dönemleri tetikleyebilir; yetki sınırlı kalır. |
| D-147 V8.5 M0 adayı | Salt okunur yetki projeksiyonunu, değişmez davaları, sentetik kısıtlamaları ve istatistiksel borcu korur. |
| D-148 hızlı denetim motoru | Yeniden üretim/değerlendirmeyi verimli şekilde yürütebilir; epistemik anlamda değişiklik yoktur. |
| D-149 tam metin çapa değişmezi | Bu makale, kanonik belgeler yolu altında onaylanıp işlenirse tam metin/çapa gereksinimini karşılamayı amaçlar. |

---

## 29. Onay kapıları

D-150 yalnızca aşağıdakilerin tümü kodda ve yönetişimde kanıtlandığında geçmelidir:

1. EvaluationCase ve EvaluationEpoch dokunulmazlık testleri geçer.
2. Sertifika ardıllığı ebeveyn hash'lerinden ve delil deltalarından yeniden oluşturulabilir.
3. D-150/Assurance'tan doğrudan yasal ekonomik iddialar basan hiçbir yol yoktur.
4. Sentetik deliller iddia kapsamlı ve ekonomik-olmayan-pozitif kalır.
5. Güçlü çürütücüler deterministik olarak yayılır.
6. Politika hash değişikliği yeni bir dava/politika soyunu zorunlu kılar.
7. Holdout-yakma semantiği bozulmadan kalır.
8. Sıralı izleme, sabit ufuklu istatistiksel eşikleri her an geçerli delil olarak sessizce yeniden kullanamaz.
9. Tarihsel sertifikalar değiştirme/iptal sonrasında yeniden inşa edilebilir kalır.
10. D150-T01–T20 bağımsız denetimle geçer.

> **Onay hedefi:** D-150, daha zengin bir Dökümhane beklemeden bir delil yaşam döngüsü değişikliği olarak onaylanabilir. Dökümhane daha sonra evrilebilir; D-150'nin görevi gelecekteki herhangi bir delil kaynağının tarihe güvenle girmesini sağlamaktır.

---

## 30. Açık pinler

| Pin | Soru | Çözülene kadar varsayılan |
|---|---|---|
| `D150-P01` | Hangi operasyonel tahminler her an geçerli sıralı istatistikler gerektirir? | Geçerli bir MonitoringPlan olmadığı sürece yalnızca tanısal. |
| `D150-P02` | Her sertifika iddiası hangi tazelik/son kullanma politikasını kullanmalıdır? | Evrensel bir son kullanma tarihi yoktur; yalnızca iddiaya özel tetikleme kuralları. |
| `D150-P03` | Bir sözleşme/çevre değişikliği ne zaman yeni bir dönem yerine yeni bir dava yaratır? | Politika, kod, konfig, fayda, maliyet, kapasite, bilgi veya yetki semantiği önemli ölçüde değişirse: yeni dava. |
| `D150-P04` | Dünya uzayı kapsamı skaler hazırlık olmadan nasıl özetlenmelidir? | Tiplendirilmiş kapsam vektörü + manifestolar; skaler puan yok. |
| `D150-P05` | Gelecekteki sentetik yeterlilik yalnızca test amaçlı M0'ın ötesinde kabul edilebilir mi? | Ayrı D serisi değişikliğine kadar hayır. |

---

## 31. Önerilen D-150 karar metni

> **D-150 — Sürekli Epistemik Ardıllık ve Yaşayan Politika Anayasası.**
>
> V8, politika kimliği ile delil geçerliliğinin birbirinden ayrı ve sürümlenen boyutlar olduğunu kabul eder. Mühürlenmiş hiçbir değerlendirme, delil dönemi veya sertifika yeniden açılamaz veya üzerine yazılamaz. Güncel bir güvence iddiasına kabul edilebilir olan her yeni gerçek, ileriye dönük, sentetik, karşıt, Oracle, D-136, D-141, icra veya denetim delili, kriptografik olarak bağlı yeni bir `EvaluationEpoch` üzerinden sisteme girer. Her halef dönem kesin soyu, yetki sınırlarını, delil kaynağını, değerlendirici/dünya kapsamını, istatistiksel plan kimliğini ve güçlü çürütücü durumunu korur.
>
> Bir ardıl dönem mevcut `ProductionEvidenceCertificate`i koruyabilir, yerini alabilir, tartışmalı hale getirebilir, karantinaya alabilir veya iptal edebilir. İptal tarihsel sertifikasyonu silmez; yalnızca güncel yetkisini sonlandırır. Maddi yenilgi tiplendirilmiş bir `DefeaterReceipt` olarak yayılır ve teşhis ile meydan okuyucu araştırması için mevcut Kaizen yaşam döngüsüne devredilir. D-150 sıfır bağımsız politika değiştirme, terfi, ClaimRegistry hak basma veya ekonomik yetki hakkına sahiptir.
>
> Sentetik ve karşıt deliller sınırlandırılmış dayanıklılık, anlamsal, güvenlik veya bütünlük iddialarına meydan okuyabilir veya bunları yanlışlayabilir, ancak başarılı sentetik performans hiçbir zaman tek başına `SUPPORTED_EDGE`, `REALIZED_CASHFLOW`, beklenen gerçek getiri veya fiziksel uzlaşma tesis edemez. Sürekli istatistiksel izleme yalnızca önceden kaydedilmiş, varsayıma bağlı, zaman açısından geçerli bir izleme yöntemi altında çıkarımsal yetki alır; aksi takdirde tanısal delildir. Mevcut tüm anayasal yetki, holdout, denetim, istatistik ve iddia ayırma yasaları, ayrı olarak onaylanmış bir kararla açıkça geçersiz kılınmadıkça yürürlükte kalır.

---

## 32. Sonuç

D-150 V8'i genişletmek adına genişletmek yerine belirli bir boşluğu kapatır. Kaizen halihazırda politika evrimini sağlar. D-136 delil gözlemlenebilirliğini sağlar. D-138 ileriye dönük makbuzları sağlar. D-141 uzman yeterliliğini sağlar. V8.5 Güvencesi iddia bileşimini sağlar. Eksik olan unsur, tüm bu sistemler *yarın yeni delil* ürettiğinde ne olacağını söyleyen yasadır.

Cevap sürekli epistemik ardıllıktır: her tarihsel kararı koruyun, mühürlenmiş delilleri asla yeniden açmayın, mevcut delil durumunu sürümleyin, yeni gerçek/sentetik/karşıt gözlemlerin mevcut güvenceye meydan okumasına izin verin ve maddi yenilgiyi Kaizen'e gönderin. Ortaya çıkan sistem kalıcı olarak "sertifikalı bir bot" değildir; güvenilir kalma izni en güçlü güncel kabul edilebilir delillere bağlı olan bir politikadır.

$$\text{Politika } P, E_0 \text{ epoch'unda desteklendi} \quad \neq \quad \text{Politika } P \text{ şimdi destekleniyor.}$$
$$\text{Yaşayan V8} = \text{Politika Soyu} \times \text{Delil Soyu} \times \text{Zaman}$$

---

## 33. Referanslar ve kaynak haritası

1. **[R1] Robustness Gym: Unifying the NLP Evaluation Landscape**. Goel et al. (2021). [https://arxiv.org/abs/2101.04840](https://arxiv.org/abs/2101.04840)<br>
   *Değerlendirmeyi tek seferlik statik bir nesne yerine sürekli bir süreç olarak çerçeveler.*
2. **[R2] Handling Concept Drift in Global Time Series Forecasting**. Liu, Godahewa, Bandara, Bergmeir (2023). [https://arxiv.org/abs/2304.01512](https://arxiv.org/abs/2304.01512)<br>
   *Durağan olmayan zaman serisi dağılımlarının tahmin modellerini nasıl bozabileceğini gösterir.*
3. **[R3] Towards Practicable Sequential Shift Detectors**. Cobb & Van Looveren (2023). [https://arxiv.org/abs/2307.14758](https://arxiv.org/abs/2307.14758)<br>
   *Sıralı dağılım kayması tespiti için pratik gereksinimleri tanımlar.*
4. **[R4] Diagnostic Runtime Monitoring with Martingales**. Hindy et al. (2024). [https://arxiv.org/abs/2407.21748](https://arxiv.org/abs/2407.21748)<br>
   *Kayma nedenlerini teşhis etmek ve yaşam döngüsü müdahalelerine bağlamak için akış martingal monitörlerini kullanır.*
5. **[R5] Sequential Model Confidence Sets**. Arnold et al. (2024). [https://arxiv.org/abs/2404.18678](https://arxiv.org/abs/2404.18678)<br>
   *Model güven kümelerini e-süreçleri ve güven dizilerini kullanarak sıralı ortamlara genişletir.*
6. **[R6] ANDROIDWORLD: A Dynamic Benchmarking Environment for Autonomous Agents**. Rawles et al. (2024). [https://arxiv.org/abs/2405.14573](https://arxiv.org/abs/2405.14573)<br>
   *Sabit bir test kümesinin ötesinde dinamik parametreli değerlendirme görevlerini gösterir.*
7. **[R7] MACEval: A Multi-Agent Continual Evaluation Network for Large Models**. Chen et al. (2025). [https://arxiv.org/abs/2511.09139](https://arxiv.org/abs/2511.09139)<br>
   *Kapalı uçlu kıyaslama aşırı uyumunu azaltmak için dinamik sürekli değerlendirme önerir.*
8. **[R8] Towards Causal Market Simulators**. Thumm & Ontaneda Mijares (2025). [https://arxiv.org/abs/2511.04469](https://arxiv.org/abs/2511.04469)<br>
   *Karşıolgusal finansal yörüngeler için üretici zaman serisi modellemesini yapısal nedensel modellerle birleştirir.*
9. **[R9] Financial Wind Tunnel: A Retrieval-Augmented Market Simulator**. Cao et al. (2025). [https://arxiv.org/abs/2503.17909](https://arxiv.org/abs/2503.17909)<br>
   *Stres testi ve model değerlendirmesi için kontrol edilebilir sentetik piyasa dinamikleri sunar.*
10. **[R10] High-Quality Synthetic Financial Time-Series using a GAN-Diffusion Framework**. Masi, Coletta & Bartolini (2026). [https://arxiv.org/abs/2605.27113](https://arxiv.org/abs/2605.27113)<br>
    *Stilize olguları ve varlıklar arası korelasyon yapısını korumanın zorluğunu vurgular.*
11. **[R11] COvolve: Adversarial Co-Evolution of LLM-Generated Policies and Environments**. Sygkounas et al. (2026). [https://arxiv.org/abs/2603.28386](https://arxiv.org/abs/2603.28386)<br>
    *Politikaları ve ortamları karşıt birlikte evrilen popülasyonlar olarak modeller.*
12. **[R12] Beyond Static Evaluation: Co-Evolutionary Mechanisms for LLM-Driven Strategy Evolution in Adversarial Games**. Li et al. (2026). [https://arxiv.org/abs/2606.10389](https://arxiv.org/abs/2606.10389)<br>
    *Stratejiler geliştikçe sabit değerlendiricilerin nasıl bayatlayabileceğini gösterir.*
13. **[R13] Reverse Stress Testing for Multivariate Scenarios: A Conditional Framework for Stressed Time Series**. Sparviero & Viola (2026). [https://arxiv.org/abs/2606.09274](https://arxiv.org/abs/2606.09274)<br>
    *Bağımlılık yapısını korurken şoklara bağlı tutarlı çok değişkenli stresli senaryolar oluşturur.*
14. **[R14] Huber-Robust Confidence Sequences**. Wang & Ramdas (2023). [https://arxiv.org/abs/2301.09573](https://arxiv.org/abs/2301.09573)<br>
    *Açık kontaminasyon varsayımları altında her an geçerli güven dizileri sağlar.*
