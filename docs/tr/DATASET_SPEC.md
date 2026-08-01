# V8 Veri Kümesi Spesifikasyonu

**Durum:** PROVISIONAL_DECISION. Kurallı depo, yalnızca-eklenen bir kanıt
günlüğü artı tekrarlanabilir somutlaştırmalardır. Zaman damgası satırları tek
başına candidate kararları için yetersizdir; candidate satırları tek başına
karar yolunu gizler.

## 1. Depolama katmanları ve birleştirmeler

1. **Ham kanıt:** satıcı/mekan yükleri, değiştirilemez içerik hash'leri ve kaynak
   meta verileri. Yıkıcı düzeltme yok.
2. **Karar defteri:** MarketState, ExpertEvaluation ve CandidateTransition;
   yalnızca her `knowledge_time` anında kabul edilebilir bilgi.
3. **Execution defteri:** Order, Fill, PositionLifecycle; gerçek dış olaylar.
4. **Sonuç defteri:** CounterfactualOutcome ve olgun etiketler; karar
   feature'larından erişim-ayrık.
5. **Araştırma somutlaştırmaları:** sabitlenmiş bir `ExperimentManifest`'ten
   üretilen sürümlenmiş candidate, geçiş ve zaman damgası tabloları.

Tüm tablolar UUID birincil anahtarlar, UTC zaman damgaları, `schema_version`,
`producer`, `code_version`, uygulanabilir olduğunda `experiment_id` ve
`recorded_at` kullanır. Zaman değerleri asla aşırı yüklenmez: her kaynak olgusu
`event_time`, `available_time` ve `ingested_time` sağlar; her karar
`knowledge_time` sağlar.

| Varlık (PK) | Gerekli yük / referanslar | Sahiplik ve sızıntı kuralı |
|---|---|---|
| `MarketState(state_id)` | as_of, evren/sürüm, ham manifest hash'i, feature grafiği/sürümü, kalite, soyağacı hash'i | Durum yapıcı; her feature maksimum girdi kullanılabilirliğini `<= as_of` taşır. |
| `ExpertEvaluation(evaluation_id)` | expert/sürüm, state_id, uygulanabilirlik, kanıt, karar, knowledge_time | Expert; sonuç defterine başvuramaz. |
| `CandidateEpisode(candidate_id)` | episode anahtarı, expert/sürüm, ebeveyn id, doğum anlık görüntüsü, güncel projeksiyon | Yaşam-döngüsü hizmeti; değiştirilemez doğum alanları. |
| `CandidateTransition(transition_id)` | candidate id, sıra, from/to, neden, saatler, anlık görüntü/kanıt ref'leri | Yaşam-döngüsü hizmeti; yalnızca-eklenen, yalnızca yasal geçiş. |
| `TriggerSnapshot(snapshot_id)` | yüklem sürümü, gözlemlenen girdiler, state id, karar saati | Expert; girdi kullanılabilirliği denetlenir. |
| `CounterfactualOutcome(outcome_id)` | candidate id, ufuk, simülatör/config/hash, son nokta/sansür, sonuç | Simülatör; yalnızca-sonuç erişimi. |
| `Order(order_id)` | candidate id (null olabilir), kurallı plan/sürüm, gönderim/onay zamanları, mekan | Execution hizmeti; geriye-dönük fiyat düzenlemesi yok. |
| `Fill(fill_id)` | emir id, mekan execution id, olay/kullanılabilirlik zamanı, fiyat/miktar/ücretler | Execution alımı; mekan olay ID'sini tekilleştir. |
| `PositionLifecycle(position_event_id)` | pozisyon id, olay türü, dolumlar, durum, saatler | Execution projeksiyonu; dolumlardan/emirlerden yeniden inşa edilir. |
| `ExperimentManifest(experiment_id)` | git/kod hash'i, veri anlık görüntü hash'leri, evren, bölmeler, feature'lar, etiketler, simülatör, tohumlar | Deney çalıştırıcı; çalışma başladıktan sonra değiştirilemez. |

Null değerler `null_reason` gerektirir; yokluk asla sıfır ya da olumsuz sonuç
olarak yorumlanmaz. Null olmayan bir yabancı anahtar, aynı ya da açıkça
adlandırılmış değiştirilemez veri anlık görüntüsü içindeki bir varlığa/sürüme
çözülmelidir.

## 2. Veri kümesi birimleri

Üç farklı model-hazır birim yayınla; hedeflerini asla örtük olarak
karıştırma.

* **Zaman-durum satırı:** bir `(instrument, decision_clock, state_version)`;
  betimleyici kapsam ya da router araştırması için yararlıdır, candidate-kalite
  örneklerinin yerine geçmez.
* **Candidate satırı:** bildirilmiş bir gözlem kesiminde (`birth`, `trigger`
  ya da `accept`) yalnızca o an kabul edilebilir feature'larla bir candidate ve
  ayrıca olgunlaşmış sonuç/sansür durumu. Varsayılan scorer birimidir.
* **Geçiş satırı:** bir yasal durum değişikliği; tetikleyici/sona erme ve
  operasyon modelleri için yararlıdır. Etiket ufku doğumda değil, o geçişte
  başlar.

Candidate kümeleri skor karşılaştırmasından önce sabitlenmelidir. Yakın
kaçırmalar ve bastırılmış duplikeler `ExpertEvaluation`/geçiş olguları olarak
saklanır; bir protokol örnekleme popülasyonlarını ve ağırlıklarını tanımlamadıkça
sentetik olumsuzlara dönüşmezler. Trade edilmemiş candidate'ları gerçekleşmiş
dolumlarla etiketleme; karşı-olgusal bir hedef gerekiyorsa bildirilmiş bir
karşı-olgusal execution politikası kullan.

## 3. Bölme, etiket ve popülasyon politikası

* Her karar anında geçerli olan, listeden çıkarılmış/pasif araçları da içeren
  bir PIT evreni inşa et. Araç kimlik eşlemeleri ve kurumsal-aksiyon
  ayarlamaları sürümlenir.
* Zaman aralıklarına göre böl, sonra feature ya da etiket aralığı
  doğrulama/test ile örtüşen herhangi bir eğitim candidate'ını temizle ya da
  ambargoya al. İlişkili/tekrarlanan episode'ları (`episode_key`, araç, olay
  kümesi) deneyin öngördüğü gibi grupla.
* Sonuçlar yalnızca `label_available_time`'dan sonra eğitilebilir hale gelir:
  maks(etiket ufku sonu, gerekli veri kullanılabilirliği, simülatör tamamlanması).
  Bir karar, bundan önce bir etiket ya da kalibrasyon istatistiği kullanamaz.
* Örtüşme ve bağımlılığı ağırlıklandır/raporla: candidate süresi, eşzamanlılık,
  araç/olay kümesi ve herhangi bir benzersizlik ağırlığı. Örtüşen episode'lar
  için IID metriklerini nitelendirmeden sunma.
* Sansürlü satırlar yalnızca kayıtlı bir kuralla hariç tutulur; hayatta-kalma/
  rakip-risk yöntemleri bunları kullanabilir. `EXPIRED` ve `INVALIDATED`
  nedenlerdir, evrensel başarısızlıklar değildir.

PIT, revizyon ve hayatta-kalma gereksinimleri şunlar tarafından
**LITERATURE_SUPPORTED**'dır:
[ML for Trading: Financial Data Universe](https://ml4trading.io/third-edition/chapters/02_financial_data_universe) ve
[Fundamental and Alternative Data](https://ml4trading.io/third-edition/chapters/04_fundamental_alternative_data).
Seçilen tablolar ve fiziksel karar/sonuç ayrımı **DESIGN_INFERENCE**'dır.

## 4. Ucuz kabul testleri

1. Herhangi bir araştırma satırını `as_of=D` ile sorgula; her feature'ın ham
   sürümünün ve maksimum kullanılabilirliğinin `<= D` olduğunu iddia et.
2. D'den sonra bir kaynağı revize et; orijinal durum/candidate
   somutlaştırmasını eski manifest hash'inden yeniden üret.
3. Test sonuçlarını değiştirdikten sonra bir katı iki kez çalıştır; eğitim
   satırları, ölçekleyiciler, eşikler ve tahminler bayt-bayt aynı olmalı.
4. Tarihsel evrene listeden çıkarılmış bir araç ekle; bitiş zamanından önce
   görünmeli ve sonrasında görünmemelidir.
5. Her candidate hedefinin açık `MATURE`/sansür durumuna ve
   `label_available_time`'a sahip olduğunu iddia et; feature projeksiyonunda
   etiketsiz sonuç sütunları olan bir scorer dışa aktarımını başarısız kıl.
6. Ham/geçiş olaylarını replay et; birincil-anahtar benzersizliğini,
   yabancı-anahtar çözümünü, monoton candidate sırasını ve eşleşen
   somutlaştırılmış durumu iddia et.
