# V8 Anayasası v0.1

1. V8 bir falsifikasyon programıdır, edge vaadi değildir.
2. Bir iddia `LITERATURE_SUPPORTED`, `PROJECT_EVIDENCE_SUPPORTED`,
   `DESIGN_INFERENCE`, `PROVISIONAL_DECISION`, `LOCKED_INVARIANT`,
   `OPEN_QUESTION` ya da `REJECTED_OPTION` olarak etiketlenir; etiketler asla
   birbirinin yerine kullanılmaz.
3. MarketState yalnızca karar anında gözlemlenebilir bilgileri içerebilir. Olay
   (event), bilgi (knowledge), kullanılabilirlik (availability) ve karar (decision) zamanı ayrı alanlardır.
4. Candidate, order ve outcome birbirinden ayrı, değiştirilemez kayıtlardır.
   Tüm terminal candidate durumları—sona erme (expiry), geçersizleştirme
   (invalidation) ve reddetme (rejection) dahil—saklanır.
5. Eklenen her bileşen, önceden kayıtlı, maliyetlendirilmiş, donmuş
   out-of-sample bir karşılaştırmada kendisinden hemen daha basit olan
   deterministik taban çizgiyi yenmelidir.
6. Başlangıç mimarisi şudur: zaman-noktası durum → tüm ucuz kendi-kendine
   kapılanan (self-gating) deterministik Expert'ler → yalnızca-eklenen
   (append-only) candidate günlüğü → deterministik kabul kuralları → tek
   kurallı execution/defter. Router, öğrenilmiş scorer, ranker ve RL execution
   varsayılan olarak yoktur.
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
13. Ontoloji: her Candidate'ın tam olarak bir kaynak Expert'i vardır; tek bir
    karar olayı birden fazla Expert'ten Candidate üretebilir. Bir Expert, tek
    bir davranış ailesi (behavior family) içindeki tek bir yanlışlanabilir
    çalıştırılabilir hipotezdir; parametre ve geometri değişiklikleri o hipotez
    ailesinin varyantlarıdır, ayrı Expert değildir. Her Expert
    `mechanism_family_id`, `behavior_family_id`, `expert_id`, `expert_version`
    ve varsa `variant_id` taşır.
14. Karmaşıklık bütçesi iki ayrı eksende tanımlıdır ve asla tek bir sayıya
    indirgenmez. (a) **Runtime:** aktif Expert sayısı sınırsızdır; tek sınır
    determinizm ve hesap bütçesidir. Expert sayısı bir geçerlilik kısıtı
    değildir. (b) **Kanıt:** tek bir donmuş OOS değerlendirmesinde eşzamanlı
    olarak iddia taşıyan davranış ailesi sayısı önceden kayıtlıdır ve kural
    11'in aile düzeyi çokluk düzeltmesine girer. Pipeline konumu başına en
    fazla bir öğrenilmiş bileşen. Router, paylaşılan scorer, ranker, RL
    execution ve online learning yoktur.
15. Öğrenme offline ve registry-kapılıdır. Sonuç verisi aktif bir Expert'in
    tanımını asla değiştirmez; yalnızca, terfiden önce donmuş bir OOS
    karşılaştırmasını ve registry incelemesini geçmek zorunda olan challenger
    sürümler üretebilir.
16. Risk kabulü deterministik ve exposure-farkındadır. Taban çizgi
    (enstrüman, yön) başına tek bir aktif exposure tutar; çakışan bir Candidate
    reddedilir (`CAPACITY_REJECTED` / `EXISTING_EXPOSURE_CONFLICT`) ve yine de
    karşı-olgusal (counterfactual) olarak ölçülür. Bu bir **atıf
    varsayılanıdır**, bir risk tavanı değil: gerçekleşen PnL'in tek bir
    Expert'e atfedilebilir kalmasını sağlar. Portföy ısı sınırıyla birlikte —
    kural 14'ün Expert sayısı değil — portföy ölçeğini sınırlayan şey budur.
    İkisinden birini gevşetmek bir registry kararıdır (O-012, O-018), asla bir
    konfigürasyon değişikliği değil.
17. Araştırma materyalizasyonları tape'ten bir kez derlenir ve yeniden
    kullanılır; eğitim materyalize edilmiş görünümleri okur, asla ham tape'i
    okumaz ve yalnızca feature, Expert, simülatör ya da outcome tanımları
    değiştiğinde yeniden derler.

## Minimum tutarlı mimari

```text
sürümlenmiş zaman-noktası tape/durum
  -> deterministik kendi-kendine kapılanan Expert'ler (N, sınırsız)
  -> candidate olay deposu (tüm sonuçlar)
  -> deterministik kabul + risk sınırı
  -> kurallı Level-1 simülatör / tek defter
  -> önceden kayıtlı hipotez laboratuvarı
```

Bu diyagramın ötesindeki her şey, ilgili registry deneyinin geçmesini gerektirir.
