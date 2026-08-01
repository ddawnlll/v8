# V8 MarketState Sözleşmesi

**Durum:** PROVISIONAL_DECISION. Bu bir nedensellik sözleşmesidir; duruma-dayalı
yönlendirmenin ya da önerilen herhangi bir feature'ın tahmin değeri olduğuna dair
kanıt değildir.

## 1. Terimler ve saatler

Bir veri noktası `d` için dört ayrı zamanı sakla (UTC, kaynağın desteklediği
yerde nanosaniye hassasiyeti):

| Alan | Anlam | `D` anında bir kararı kapılayabilir mi? |
|---|---|---|
| `event_time` | Altta yatan piyasa/ekonomik olayın gerçekleştiği zaman. | Hayır, tek başına. |
| `source_time` | Mekan/yayıncı tarafından beyan edilen zaman damgası. | Hayır, tek başına. |
| `available_time` | V8'in yapılandırılmış canlı akışının bu tam sürümü teslim edebileceği en erken zaman. | Evet, ancak `<= D` ise. |
| `ingested_time` | Bu çalışmanın onu sakladığı zaman. | Asla kullanılabilirlik vekili değildir. |

`knowledge_time`, karar saati `D`'dir: bir kararın kullandığı her girdinin
kullanılabilir olduğu en büyük zaman. Her karar artefaktında saklanır.

**LOCKED_INVARIANT — kabul edilebilirlik:**

```text
d, D anında kabul edilebilirdir ancak d.available_time <= D
  VE d.version, D anında kullanılabilir olan sürümdür
  VE d, D anında zaman-noktası araç evrenindedir.
```

`available_time` yapılandırılmış akış gecikmesini ve bilinçli işleme
gecikmesini içerir. Bilinmediğinde, veri noktası üretim-benzeri araştırma için
**kabul edilemez**; muhafazakâr, belgelenmiş bir sınır yalnızca açıkça
`RESEARCH_ONLY` olarak işaretlenmiş bir çalıştırma için kullanılabilir.
Makbuz/ETL zamanı bilinmeyen bir tarihsel kullanılabilirlik zamanını
onaramaz.

## 2. MarketState değeri

Karar saati `D`'de, `MarketState` değiştirilemez, sürümlenmiş bir değerdir:

```text
S(D, U, C) = {
  state_id, as_of=D, universe_id=U, clock_policy_id=C,
  observations: [ObservationRef],
  features: [FeatureValue], quality: StateQuality,
  provenance: {raw_manifest_hash, feature_graph_version, code_version},
  lineage_hash
}
```

`U` zaman-noktası işlem yapılabilir evrendir; `C` oturum, mekan, gecikme,
bar-kapanış ve kesinlik (finality) politikasını tanımlar. Bir durum, **tek bir
karar saati** için bir anlık görüntüdür; değiştirilebilir bir önbellek ya da
"rejim"in eşanlamlısı değildir. Rejim etiketleri, kendi kullanılabilirlik ve
model sürümlerine sahip isteğe bağlı feature'lardır.

Her `FeatureValue` şunlara sahiptir:

```text
feature_name, value, dtype, feature_version, input_lineage_hash,
calculation_time, max_input_available_time, quality_flag, null_reason
```

Yapıcı, `max_input_available_time <= as_of` olduğunu iddia etmelidir. Türetilmiş
değerler yalnızca kabul edilebilir ham sürümlerden hesaplanmalıdır. Bir feature,
kullanılamayan bir girdiyi daha sonraki düzeltilmiş bir değerle sessizce
değiştiremez.

## 3. Gözlem ve bar semantiği

* Ham piyasa olayları, mevcut olduğunda mekan sırasını/düzenini kullanır; aksi
  halde sağlayıcı sırasını korur ve sıralama kalitesini işaretler. Eşit zaman
  damgalarında deterministik tie-break `(venue, channel, sequence,
  received_sequence)` uygulanır.
* Bir bar `[start, end)` yalnızca `bar_available_time` anında kullanılabilir
  olur; normalde `end + feed_latency + aggregation_latency`; kapanış/yüksek/
  düşük/hacim barın içinde görünmez. `current_bar` feature'ları yasaktır;
  ancak feature açıkça olay-zamanı artımlıysa ve kendi kesimini kaydediyorsa
  izin verilir.
* Çapraz-varlık birleştirmeleri as-of birleştirmelerdir: her varlık için en son
  kabul edilebilir gözlemi seç, `age_ns` değerini sakla ve açık bir maksimum-yaş
  politikası uygula. Eksik/bayat bağlam temsil edilir; gelecekten ileri
  doldurma (forward-fill) yapılmaz.
* Takvimler, sembol eşlemeleri, sözleşmeler, kurumsal aksiyonlar, fonlama/basis
  ve dış yayınlar sürümlenmiş girdilerdir. Revizyonlar/geç düzeltmeler yeni
  sürümler yaratır; daha erken `D` anında görünen sürümü asla üzerine yazmazlar.
* Normalizörler/ölçekleyiciler yalnızca, etiketleri ve ham girdileri kendi
  ayrım ambargolarını sağlayan eğitim gözlemleri üzerinde fit edilir;
  `fit_window`, `fit_as_of` ve parametre hash'ini serileştir. Kesitsel
  istatistikler yalnızca aktif PIT bileşenlerini kullanır.

## 4. Durum kalitesi ve null'lar

`StateQuality ∈ {COMPLETE, DEGRADED, INVALID}`. `DEGRADED` yalnızca, tüketen
Expert'in eksik/bayat alan politikasını bildirdiği yerde izin verilir; `INVALID`
bir değerlendirme üretemez. Null sıfır değildir: `null_reason ∈
{NOT_PUBLISHED, NOT_YET_AVAILABLE, NOT_APPLICABLE, SOURCE_GAP, STALE,
REJECTED}`.

## 5. Sızıntı önleme kapıları

1. Durumları bir as-of sorgu parametresiyle inşa et; "latest" okumaları yasakla.
2. Tüm ham ve türetilmiş `max_input_available_time` değerlerini `D`'ye karşı
   doğrula.
3. Değerlendirmeden önce kaynak sürümünü, ayarlama politikasını, evren
   üyeliğini ve feature grafiğini bir `ExperimentManifest` içinde kilitle.
4. Karar/candidate aralığına göre kronolojik olarak böl; etiket ufku
   doğrulama/test bilgisiyle örtüşen eğitim örneğini temizle ya da ambargoya
   al.
5. Dönüşümleri, imputasyonu, seçim eşiklerini ve etiketleri yalnızca her eğitim
   katının içinde fit et. Global standardizasyon, hedef kodlama ya da
   gelecekten-türetilmiş evren yok.
6. Karar-zamanı olgularını yalnızca-sonuç sütunlarından fiziksel olarak ve
   erişim kontrolleriyle ayır (`decision_*` vs `outcome_*` şemaları).

## 6. Ucuz çalıştırılabilir testler

* **Gelecek reddi:** `available_time=D+1ns` olan bir feature girdisi ekle; durum
  inşası başarısız olmalı.
* **Bar-kapanış testi:** `D < bar_available_time` iken bar kapanış/yüksek
  isteği `NOT_YET_AVAILABLE` döndürmeli.
* **Revizyon replay:** `D`'den sonra bir dosyayı/yayını revize et; `D`'deki bir
  as-of yeniden inşa önceki durum hash'ini üretmeli, daha sonraki bir yeniden
  inşa farklı olabilir.
* **Birleştirme testi:** `D`'den sonraki bir çapraz-varlık kotasyonu
  birleşemez; bayat bir kotasyon yaş/kalite bayrağını açığa çıkarmalıdır.
* **Kat testi:** bir doğrulama satırını değiştir ve fit edilmiş eğitim
  ölçekleyicisinin ve tüm eğitim feature değerlerinin değişmediğini doğrula.

## 7. Kanıt ve alıntılar

* **LITERATURE_SUPPORTED:** finansal veri kümeleri zaman damgası, ayarlama,
  tanımlayıcı ve revizyon tanımlarını gömer; zaman-noktası ihlalleri ve
  hayatta-kalma yanlılığı maddi araştırma riskleridir:
  [ML for Trading, Financial Data Universe](https://ml4trading.io/third-edition/chapters/02_financial_data_universe).
* **LITERATURE_SUPPORTED:** yeniden beyan edilen bir finansal rakam, orijinal
  raporlama tarihine geri doldurulmamalıdır; bitemporal/as-of depolama uygun
  korumadır:
  [ML for Trading, Fundamental and Alternative Data](https://ml4trading.io/third-edition/chapters/04_fundamental_alternative_data).
* **DESIGN_INFERENCE:** adlandırılan saatler, katı bilinmeyen-kullanılabilirlik
  işleme ve kalite enum'u, bu gereksinimleri test edilebilir kılan V8
  seçimleridir.
