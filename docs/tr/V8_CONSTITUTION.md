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

## Minimum tutarlı mimari

```text
sürümlenmiş zaman-noktası tape/durum
  -> deterministik kendi-kendine kapılanan Expert'ler (2–3)
  -> candidate olay deposu (tüm sonuçlar)
  -> deterministik kabul + risk sınırı
  -> kurallı Level-1 simülatör / tek defter
  -> önceden kayıtlı hipotez laboratuvarı
```

Bu diyagramın ötesindeki her şey, ilgili registry deneyinin geçmesini gerektirir.
