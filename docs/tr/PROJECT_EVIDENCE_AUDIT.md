# Proje Kanıt Denetimi — V6/V7/V8

**Denetim kapsamı.** Bu, V8 araştırma programı için sürümler-arası bir kanıt
envanteridir; bir V7 postmortem'i ya da ekonomik bir iddia değildir. Geçici V8
mimari brief'ini (`v8-0.2.html`), bu checkout'ta bulunan sürümlenmiş V7
materyallerine karşı okur. 2026-07-31'de `/Users/hootie/src/v8` içinde hiçbir
V6 dizini, dosyası, commit referansı ya da başka bir V6 artefaktı bulunmadı.
Dolayısıyla dosyaya-dayalı bir V6 sonucu yoktur.

## Kanıt standardı

| Etiket | Bu denetimdeki anlamı |
|---|---|
| **Dosyaya-dayalı olgu** | Adlandırılmış bir yerel artefakt tarafından doğrudan ifade edilen ya da mekanik olarak temsil edilen. Bu denetim tarafından otomatik olarak bağımsız şekilde yeniden üretilmez. |
| **Yorum (Interpretation)** | Dosyaya-dayalı olgular karşılaştırılarak çıkarılan bir sonuç. Alıntılanan artefaktlar ve yeniden çalıştırma olmadan ölçülmüş bir sonuç olarak terfi ettirilemez. |
| **Doğrulanmamış öneri** | V8'de ya da bir V7 hedef spesifikasyonunda tanımlanan, incelenen dosyalarda kabul edilebilir sonuç kanıtı olmayan mimari ya da deney. |

Mevcut en güçlü ekonomik-sertifikasyon kaydı hâlâ
`v7/specs/simulation_authority_certification_v1.json` dosyasıdır: `status: FAIL`,
`autopilot_permission: BLOCKED`, `economic_verdict: INVALID_NOT_CERTIFIED` ve
`profitability_claim: FORBIDDEN`. Dolayısıyla burada incelenen hiçbir proje
dosyası bir kârlılık iddiasını desteklemez.

## Dosyaya-dayalı ampirik sonuçlar ve mühendislik gözlemleri

### 1. P1 Tier-B Lite yön/execution kampanyası

Kaynak: `v7/docs/P1_TIER_B_LITE_FINDINGS.md` (oturum tarihi 2026-07-27/28).
Belge, raporlanan tüm kampanya rakamlarının geliştirme OOF veya zamansal holdout
olduğunu ve donmuş kuyruğunun açılmadığını söyler.

| Artefaktın raporladığı gözlem | Durum ve sınırlayıcı koşul |
|---|---|
| Numpy lojistik zamansal holdout doğruluğu 0.5033 çoğunluğa karşı 0.5087 idi; Ridge işaretli-terminal-getiri OOS IC'si +0.015 idi; karıştırılmış-etiket canary uplift'i +1.18pp idi; GRU OOF doğruluğu 0.470–0.486 idi. | Dosyaya-dayalı teşhis ölçümleri. Kampanyanın 0.60 yön kapısını geçmezler. |
| Yukarı ve aşağı sapma (excursion) IC'leri sırasıyla +0.124 ve +0.152 iken işaretli-getiri IC'si +0.015 idi. | Dosyaya-dayalı: bu feature kümesi ve örneklem için yol büyüklüğü yönden daha tahmin edilebilirdi. Ticareti yapılabilir edge **göstermez**. |
| 271.021 geliştirme olayı üzerindeki 36 breakout-executor konfigürasyonu, belirtilen maliyet modelinde tamamı trade başına −14.6 ile −23.6 bps arasında kaybetti. | Executor'a, feature'lara, ufka, veriye ve maliyet varsayımlarına özgü dosyaya-dayalı teşhis sonucu. |
| 85 sembol üzerinde deterministik replay'de, anlık yön beklentisi −0.61146 R/direktif ve yön-karıştırılmış kontrol −0.60802 idi; güven gecikmesi −0.00212 R/direktif ve trade ettiğinde −0.5435 R/trade idi. | Dosyaya-dayalı kampanya sonucu. Belge başarısız ekonomik kapıları raporlar ve çekimserliğin direktif-bazlı karşılaştırmaları yanıltıcı yaptığını söyler. |
| Uzun-ufuk nokta tahminleri bazı 24s/48s hücrelerinde pozitif oldu, ama raporlanan her gün-kümeli %95 güven aralığı sıfırı içerdi. | Dosyaya-dayalı teşhis sonucu; uzun-ufuk kârlılığının doğrulaması değil. Ufuklar, o zamanki kilitli 5dk/15dk/1s otoritesinin dışındadır. |
| 83-kurallı koşullandırma taraması, sıfır pozitif holdout net beklentisi ve sıfırı dışlayan sıfır kümeli aralık üretti. | Kaynağın kendisi bunu hurda (scratch) analiz olarak sınıflandırır; taahhüt edilmiş otorite-hash'li kanıt değildir; önceden kayıt için bir ipucudur, karar kaydı değildir. |

**Yorum.** Kabul edilebilir proje kanıtı *bu belirli* P1 önermesini reddeder:
test edilen 75-dakikalık, 16-bps-gidiş-dönüş ayarındaki bardan-türetilmiş Tier-B
Lite feature'ları yeterli maliyet-sonrası yön sinyali sağlamadı. Tüm davranışsal
yapıyı, tüm koşullu stratejileri ya da Candidate Episode'ları genel olarak
reddetmez. V8 mimarisi, P1 başarısızlığını expert ayrıştırması lehine ya da
aleyhine kanıt olarak ele almamalıdır.

### 2. Doğrulamanın yakaladığı mühendislik başarısızlıkları

Kaynak: `v7/docs/P1_TIER_B_LITE_FINDINGS.md`.

| Dosyaya-dayalı başarısızlık | Kaynağın onu neyin yakaladığını/sınırladığını söylediği | Mimari çıkarım (yorum) |
|---|---|---|
| Başlangıçta yürütülmemiş dokuz kampanya/simülasyon yolu, eksik import'lar, çalıştırılamayan bir Modal CLI, eksik replay manifest/otorite sidecar'ı, anlamsız bir karıştırılmış-etiket canary'si ve NumPy skalerleri için Decimal dönüşüm hatası dahil kusurlar içeriyordu. | Uçtan-uca kampanya yürütme ve kapalı-başarısız kontrolleri onları açığa çıkardı. | Beyan edilmiş bir iş akışı, iş akışının çalıştığının kanıtı değildir; V8, bileşen eklemeden önce çalıştırılabilir dikey-dilim kapılarına ihtiyaç duyar. |
| Pencerelemeli bir replay, tam terminal sınırındaki bir fonlama mutabakatını atladı ve tam-tape replay ile uyumsuzluk yarattı. | Diferansiyel replay farkı buldu; sınır kapsayıcı yapıldı ve bildirildiğine göre 59 adapter/simülatör sözleşme testi geçti. | Sınır-politikası testleri ve tam-versus-pencere replay, herhangi bir kurallı simülatör için haklı kilitli kontrollerdir. |
| Execution-RL kodu altı ek kusura sahipti ve hiç çalışmamıştı; maliyet çağrıları argümanları yanlış geçirdi, değerlendirici/mask sözleşmeleri uyuşmadı ve yol ekonomik mantığı tekrarladı. | Onarımdan sonraki smoke yürütme 780 episode, 2.539 adım ve 2.000 gradyan güncellemesi çalıştırdı. | Smoke tamamlanması yalnızca çalıştırılabilirliği kurar; ekonomi ya da politika doğrulaması değildir. |
| RL örnekleyici, `SYSTEM.md` direktiften-izleyiciye-politikaya episode'lar tanımlamasına rağmen, sabit-adımlı bar pencereleri kullandı ve ne direktifleri ne de dedektörü kullandı. | Bulgular belgesindeki kaynak-kodu denetimi. | Bu RL sonucunu bir sniper, router ya da Candidate Episode tasarımı hakkında kanıt olarak kullanma. |
| RL durum makinesi asla `ACTIVE`'e ulaşmadı; HOLD/REDUCE erişilemezdi. Daha sonraki bir sıfır-sonuç, bir ARMED/WAIT durum-makinesi çelişkisine dayandırıldı ve sıfır trade raporlaması `DEGENERATE_NO_TRADE`'e onarıldı. | Zorlanmış sentetik trade'ler, aksiyon histogramları ve durum-yolu denetimi. | Yaşam-döngüsü iddiaları geçiş kapsamı artı huni metrikleri gerektirir; `NO_TRADE`/sıfır ödül kaynak (provenance) taşımalıdır. |

### 3. Açık sınırlarıyla başarılı mühendislik örüntüleri

| Örüntü | Dosyaya-dayalı destek | Sınır |
|---|---|---|
| Kapalı-başarısız veri ve otorite bağlama | `v7/README.md`, `v7/RESEARCH_PROTOCOL.md` ve V7 spec'leri aralıkları, hash'leri, manifestleri, OOF/donmuş bölme kurallarını bağlar ve eksik otorite sidecar'larını reddeder. | Sertifikasyon, donmuş OOS izolasyonunun zorlanmış salt-okunur bir değerlendirici mount'u değil, bir konvansiyon olduğunu söyler. |
| Bağımsız bir decimal test oracle'ı ile kurallı skaler simülasyon | Sertifikasyon skaler golden testleri, geçen 36 modal testi, bir oracle, sonuç hash'ini ve defter mutabakatını kaydeder. | Aynı sertifikasyon, çözülmemiş paralel ekonomik yolları tanımlar ve P1 ekonomik hükmünü geçersiz/sertifikasız olarak işaretler. |
| Diferansiyel replay ve karıştırılmış-yön kontrolü | Bulgular, tam/pencere replay'ın bir fonlama-sınırı hatasını yakaladığını ve model tarafının yanında bir yön-karıştırılmış kontrol raporladığını bildirir. | Sonuçlar yalnızca tanımlı P1 replay/politika ayarını değerlendirir; kontroller V8'in önerdiği expert'leri doğrulamaz. |
| Kümelenmiş belirsizlik ve örtüşme farkındalığı | Bulgular, uzun tutuşları gün-kümeli bootstrap ve örtüşmeyen alt-örneklemeyle yeniden fiyatlar ve saf t-istatistiği güvenini reddeder. | Belge birkaç ufuk/maliyet taramasını hurda analiz olarak etiketler; kampanya koşumunda yeniden çalıştırma gerektirir. |
| Tahminin sert risk otoritesinden ayrılması | `execution_rl_policy_v1.json`, snipers'lara yalnızca-tahmin çıktıları verir ve risk için deterministik limitler ayırır. | Aynı hedef tasarımı, trade tarafını, zamanlamayı ve yönetimi doğrulanmamış bir RL politikasına bırakır; bu kapılı bir hedef mimarisidir, elde edilmiş bir yetenek değil. |
| Hızın üzerinde hesaplama doğruluğu | `V7_COMPUTE_INFRASTRUCTURE_V1.md` CPU referansı, sessiz CUDA geri dönüşü olmaması, tam etiket/simülasyon alanları ve parite kapıları gerektirir. | README/Operatör Testleri, birçok uzun, donanıma-bağımlı, CUDA, stres ve ekonomik kapının operatör-sahipli olduğunu ya da paketleme sırasında çalıştırılmadığını belirtir. |

## Dosyalar-arası çelişkiler ve bayat otoriteler

| Gerilimdeki dosyalar | Dosyaya-dayalı çelişki | Gerekli ele alış |
|---|---|---|
| `v7/specs/simulation_authority_certification_v1.json` vs `v7/docs/P1_TIER_B_LITE_FINDINGS.md` | Sertifikasyon, P1 adapter/replay entegrasyonunun ve tek ekonomik API'nin çözülmemiş olduğunu söyler; daha sonraki bulgular belgesi adapter/replay'in uygulandığını ve çalıştırıldığını söyler ama sertifikasyonun kendini güncellememesi gerektiğini açıkça belirtir ve bayat kalır. | Bağımsız bir operatör yeniden çalıştırıp güncelleyene kadar sertifikasyonu mevcut engelleyici otorite olarak ele al. Bulgular o yeniden çalıştırmaya yol gösterebilir, onu geçersiz kılamaz. |
| `v7/SYSTEM.md` / `execution_rl_policy_v1.json` vs bulgular §8 | Hedef tasarım sniper direktif → izleyici → devam eden pozisyon yönetimli execution politikası der; denetim, uygulanan RL'nin keyfi bar pencereleri örneklediğini ve `ACTIVE`'e giremediğini söyler. | Mevcut RL'yi bağımsız, eksik bar-trading deneyi olarak etiketle. Onu entegre Candidate execution olarak sunma. |
| V8 `Candidate ≠ order` / bağımsız execution dili vs V7 politika otoritesi | V8 bir Candidate ve kurallı yaşam-döngüsü execution'ı çerçeveler; V7 hedef politikası execution RL'ye tüm taraf, hedef risk ve emir kararlarını verir. | Bu, deneysel olarak çözülmesi gereken bir tasarım uyumsuzluğudur: önce atıf için sabit/kurallı bir executor seç ya da öğrenilmiş executor'ın karşı-olgusal atıf sözleşmesini açıkça tanımla. |
| V8 bağımsız execution iddiası vs V8'in ana hedefteki kendi uyarısı | Ana prompt, alpha ve execution'ın etkileşebileceğini ve istatistiksel olarak bağımsız varsayılmaması gerektiğini söyler. | Yalnızca operasyonel ayrımı/atfı geçici bir değişmez olarak koru; istatistiksel bağımsızlık iddia etme. |
| V8'in candidate-merkezli, davranış-expert mimarisi vs mevcut kanıt | V8, H1/H2/H3/H5/H6'yı geçici/açık olarak adlandırır; V7 P1, davranışa-özgü expert'ler ya da tam candidate yaşam döngüleri değil, yönden-nötr bir bar feature kampanyası ölçtü. | Hiçbir V7 sonucu yönlendirmeyi, expert uzmanlaşmasını, candidate skorlamayı ya da sıralamayı doğrulamaz. Her birine belirtilen en ucuz baseline ile başla. |

## V8 iddia yaklaşımı

Bu tablo *mevcut proje kanıtını* sınıflandırır; daha geniş literatürü değil.

| V8 öğesi | Kanıt sınıflandırması | Denetim sonucu |
|---|---|---|
| Candidate, otomatik olarak bir emir yerine yaşam-döngüsü taşıyan bir hipotezdir | Destekleyici mühendislik gerekçeli **DESIGN_INFERENCE** | Test edilebilir bir veri/atıf tasarımı olarak koru: tetiklenmiş, sona ermiş, geçersizleştirilmiş ve reddedilmiş candidate'ları kaydet. Hiçbir proje dosyası henüz getirileri ya da kalibrasyonu iyileştirdiğini göstermez. |
| MarketState sızıntı-güvenli paylaşılan bağlam olarak | **PROVISIONAL_DECISION** | V7'de onu destekleyebilecek nedensel-feature ve otorite disiplinleri zaten vardır. Test edilmiş bir MarketState şeması ya da ham feature'lara karşı karşılaştırma mevcut değildir. |
| Davranışa-özgü Expert'ler bir global modeli yener | **OPEN_QUESTION** | P1'in global/yön zayıflığı uzmanlaşma için yetersiz kanıttır. Eşit-veri, eşit-maliyet OOS karşılaştırması gerektir. |
| Self-gating vs açık router | **OPEN_QUESTION** | V8 compute/geri çağırım/duplike ödünleşimlerini tanımlar ama ampirik karşılaştırma yoktur. Ucuzsa self-gating ile başla; yalnızca ölçülebilir bir hedefi varsa yönlendirmeyi test et. |
| Candidate scorer kaliteyi artırır, trade'leri yalnızca azaltmaz | **OPEN_QUESTION** | V7 tam çekimserlik tuzağını belgeler. Yalnızca direktif-başına beklentiyi değil, eşleşen kapsamı ve trade-başına ekonomi/kalibrasyonu karşılaştır. |
| Candidate'lar-arası sıralama | **PROVISIONAL_DECISION / koşullu** | Yalnızca kabul edilebilir candidate'lar tanımlı bir kıt-sermaye/portföy kısıtı için rekabet ettiğinde haklıdır. Önce uygulama. |
| Kurallı, kaynak-kökenli execution ve deterministik sert risk | **LOCKED_INVARIANT adayı** | Proje destekli en güçlü mühendislik ilkesidir, ama sertifikalı sayılmadan önce otorite sertifikasyonu bağımsız olarak yenilenmelidir. |
| Öğrenilmiş execution RL | **Başlangıç V8 baseline'ı için REJECTED_OPTION** | Entegrasyon/state-machine başarısızlıkları ve kabul edilebilir ekonomik sonucu olmayan kapılı bir V7 hedefidir. Yalnızca pozitif bir deterministik baseline ve tek bir sertifikalı ekonomik otoriteden sonra yeniden tanıt. |
| Yüksek çözünürlüklü Tier-A/S verisi | **DESIGN_INFERENCE** | V7 kanıtı, barlar zayıf olduğu için daha zengin akış/L1 bilgisini test etmeyi motive eder, ama hiçbir Tier-A/S ekonomik PASS sağlanmaz. Bir edge iddiasından önce veri kalitesi ve nedensel inşa kapılanmalıdır. |

## Minimum kanıt-kapılı V8 başlangıç noktası

Aşağısı denetimden türetilen bir yorum/öneridir; V8'in çalışacağı iddiası
değildir:

1. `Candidate | None` yayan 2–3 deterministik, self-gating davranış tanımı inşa
   et; tetik yokluğu ve giriş-öncesi geçersizleştirme dahil her yaşam-döngüsü
   terminal durumunu kaydet.
2. Tek sürümlenmiş, deterministik execution politikası ve tek kaynak-kökenli
   ekonomik defter kullan. Tam-tape/pencere eşdeğerliğini, fonlama sınırlarını,
   maliyetleri, dolumları ve sıfır-trade raporlamasını doğrula.
3. Ufku, maliyetleri, evreni, baseline'ı, donmuş bölmeyi, kapsam-eşleşen
   metrikleri, kümeleme birimini ve terfi kapısını önceden kaydet. Reddedilmiş
   bir geliştirme hipotezini onarmak için donmuş bir holdout'u açma.
4. Her eklemeyi hemen daha basit baseline'a karşı test et: expert vs global; tam
   yaşam döngüsü vs yalnızca-trade; scorer vs ham candidate'lar; ranker yalnızca
   sermaye çekişmesinde; uyarlanabilir execution vs kurallı execution.
5. Önceki bileşen artımlı bir donmuş-OOS kazancından yoksun olduğunda ya da
   ekonomik otorite sertifikasız olduğunda öğrenilmiş yönlendirmeyi, öğrenilmiş
   skorlamayı, sıralamayı ve RL execution'ı engelle.

## Denetim sınırları

- Bu denetim V6 artefaktı bulmadı, bu yüzden V6-versus-V7 nedensel ya da
  tarihsel bir iddiada bulunmaz.
- Kampanya verisini, replay'ı, GPU'yu ya da operatör-sahipli doğrulamayı yeniden
  çalıştırmadı; raporlanan sayısal sonuçlar, kaynak dosyalarının atadığı kanıt
  durumunu korur.
- Denetim, çalışma alanı kökünün kendisinin bir Git deposu olmadığını buldu. V7
  iç içe bir depodur; bu yüzden kaynak (provenance) kontrolleri orada
  çalıştırılmalı ve commit ile artefakt hash'leriyle kaydedilmelidir.
