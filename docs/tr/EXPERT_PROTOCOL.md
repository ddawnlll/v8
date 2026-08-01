# V8 Expert ve Yönlendirme Protokolü v0.1

**Durum:** PROVISIONAL_DECISION. Bu bir araştırma sözleşmesidir, edge kanıtı değildir.

## 1. Kapsam ve değişmez

Bir `Expert`, tek bir davranış ailesi hakkında sürümlenmiş, yanlışlanabilir,
çalıştırılabilir tek bir hipotezdir. Zaman-noktası bir `MarketState` tüketir ve
sıfır ya da daha fazla `CandidateEpisode` geçişi yayabilir. Asla bir emir
göndermez, sermaye tahsis etmez ya da başka bir Expert'in tanımını yeniden
yazmaz.

`MarketState S_t` yalnızca `availability_time <= decision_time t` olan veriyi
içerir. Karar saati, kaynak manifesti, feature kodu hash'i, Expert sürümü ve
kurallı execution sürümü her değerlendirmeye eklenir.

Aşağıdaki terimler farklıdır:

| Terim | Anlam | Bir emre karar verebilir mi? |
|---|---|---|
| Davranış | Gözlemlenebilir koşullu örüntü, nedensel bir açıklama değil | Hayır |
| Habitat | Davranışın uygulanabilir sayıldığı durum bölgesi | Hayır |
| Kurulum (setup) | Test edilebilir bir tez yaratan ön koşullar | Hayır |
| Tetikleyici (trigger) | Bekleyen tezi çalıştırılabilir kılan gözlemlenebilir koşul | Hayır |
| Geçersizleştirme (invalidation) | Tezi sonlandıran kanıt | Hayır |
| Sona erme (expiry) | Tezin bayatladığı zaman/olay sınırı | Hayır |
| Risk geometrisi | Önceden bildirilmiş giriş, stop, hedef, zaman aşımı ve boyutlandırma girdileri | Hayır |
| Candidate | Tanımlanmış yaşam-döngüsü taşıyan hipotez | Hayır |
| Order | Kabul edilmiş bir candidate için kurallı execution talimatı | Evet, yalnızca executor |
| Outcome | Sürümlenmiş karşı-olgusal ya da gerçekleşmiş sonuç | Hayır |

## 2. Minimum arayüz

```text
evaluate(expert_version, state_snapshot, active_candidates) -> [ExpertEvaluation]
ExpertEvaluation = NOT_APPLICABLE | EVIDENCE | CandidateTransition
```

Her değerlendirme; uygulanabilirlik nedenlerini, girdi anlık görüntü/içerik
hash'lerini, sıralı kanıt maddelerini, yakın-kaçırma (near-miss) nedenlerini,
candidate kimliğini ve geçen hesaplamayı kalıcı hale getirir. `None` denetlenebilir
bir sonuç değildir ve saklanan araştırma çıktısında yasaktır. Expert'ler yalnızca
yalnızca-eklenen candidate geçmişi aracılığıyla durumlu olabilir; gizli
değiştirilebilir durum yasaktır. Bir Expert birden fazla candidate yönetebilir;
kimliklerinin deterministik olması koşuluyla: `hash(expert_version, symbol,
setup_anchor_event_id, direction, geometry_version)`. Terminal bir candidate'ı
yeniden açmak yasaktır; görünür yeniden aktivasyon, `parent_candidate_id` ile bir
halef yaratır.

## 3. Yönlendirme karşılaştırması ve taban çizgi

Kilitli başlangıç taban çizgisi **tam self-gating'tir**: her karar olayında her
ucuz Expert'i çağır. Tüm router'lar için atıf referansı budur.

| Mimari | Durum | Koşul |
|---|---|---|
| A: tam self-gating | BASELINE | Gerekli ilk karşılaştırma |
| B: deterministik ön-router | PROVISIONAL | Yalnızca değerli-candidate geri çağırımını koruyorsa ve bağlayıcı bir maliyet/gecikme kısıtını azaltıyorsa kabul et |
| C: öğrenilmiş router | DEFERRED | Gelecekten-türetilmiş etiketler kullanmamalı; donmuş OOS üzerinde B ve A'yı yenmelidir |
| D: hiyerarşik router | DEFERRED | Aynı kanıt standardı, artı istikrarlı hiyerarşi atfı |
| E: hibrit | DEFERRED | Yalnızca C/D'ye karşı değil, doğrudan A'ya karşı karşılaştır |
|

"Değerli candidate", **önceden kayıtlı kurallı, out-of-sample** sonucu
karşılaştırma eşiğini geçen candidate demektir; geriye-dönük seçilmiş olumlu bir
yol anlamına gelmemelidir. Router ölçümleri: değerli-candidate geri çağırımı,
yanlış hariç tutma, toplam CPU/gecikme, kullanım, örtüşme/duplike oranı,
zaman/varlıklar arası istikrar ve eşleştirilmiş net-ekonomik etki. Yalnızca
hesaplama tasarrufu bir router'ı kabul ettiremez; self-gating bildirilmiş bir
operasyonel bütçeyi ihlal etmedikçe.

## 4. Expert kabulü ve emekliliği

Bir Expert registry'ye yalnızca şunlarla kabul edilir: bir mekanizma hipotezi;
donmuş spesifikasyon; sahiplik/sürüm; tam yaşam-döngüsü verisi; deterministik
taban çizgi; maliyetlendirilmiş kurallı simülasyon; kronolojik OOF artı
dokunulmamış OOS planı; ve açık reddetme koşulu. Yalnızca replikasyondan sonra
terfi ettirilir; `PASS` belirtilen kapının geçtiği anlamına gelir, evrensel
geçerlilik değil. Veri ya da sözleşme ihlalinde, kullanılamayan girdilerde,
önceden kayıtlı sınırların ötesinde sürüklenmede ya da başarısız replikasyonda
emekli et/karantinaya al. Parametre varyantları ayrı Expert'ler değildir.

## 5. Kanıt ve kaynaklar

* **PROJECT_EVIDENCE_SUPPORTED:** V7 denetimi çalıştırılabilir dikey dilimler,
  kurallı otorite ve tam yaşam-döngüsü kapsamı gerektirir; mevcut ekonomik
  sertifikasyon `FAIL`'dir ve kârlılık iddialarını engeller
  (`PROJECT_EVIDENCE_AUDIT.md`).
* **LITERATURE_SUPPORTED:** seyrek MoE kapıları expert'leri aç bırakabilir/
  yük-dengesizliği yaratabilir; bu yüzden yönlendirme, estetik gerekçe değil
  ölçülmüş kullanım ve geri çağırım gerektirir
  ([Shazeer et al., 2017](https://arxiv.org/abs/1701.06538)). Bu, bir MoE'nin
  trading için faydalı olduğunu göstermez.
* **DESIGN_INFERENCE:** self-gating, ikinci bir yanlış-negatif karar noktası
  getirmediği için en küçük denetlenebilir taban çizgidir.
