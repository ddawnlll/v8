# V8 Simülasyon Doğruluğu Spesifikasyonu v0.1

**Durum:** Semantik için LOCKED_INVARIANT adayı; ekonomik sertifikasyon şu anda
`PROJECT_EVIDENCE_AUDIT.md` içinde açıklanan V7 otoritesi tarafından
engellenmiştir. Burada hiçbir simülasyon sonucu iddia edilmez.

## Sadakat merdiveni ve izin verilen iddialar

| Seviye | Doğruluk kaynağı | İzin verilen kullanım | Yasak iddia |
|---|---|---|---|
| 0 | gelecek yol/geometri | etiket araştırması, dolum yok | çalıştırılabilir PnL |
| 1 | nedensel OHLC/bar olayları | sabit piyasa-tarzı giriş/çıkış çalışmaları | intrabar yol ya da kuyruk önceliği |
| 2 | trade/tick replay | verinin desteklediği yerde gecikme-bilinçli agresif dolumlar | emir-defteri kuyruk pozisyonu |
| 3 | sıralı L2 + kalibre edilmiş emir/dolum verisi | pasif/kısmi-dolum çalışmaları | kalibre edilmemiş kuyruk/maker dolumları |

Hipotezi yanlışlayabilen en düşük seviyeyi kullan. V8 **Level 1**'de başlar;
**Level 0** asla çalıştırılabilir-PnL iddiasını destekleyemez ve **Level 3** bir
yol haritası hakkı değildir. Bir simülasyon raporu veri kümesi manifestini,
kaynak kalitesini, simülatör kod hash'ini, konfigürasyon hash'ini, tohumları,
emir/dolum defterini ve çıktı hash'ini bağlar.

## Kurallı Level-1 olay sırası

1. Yalnızca sıralı kaynak olaylarını al; bir veri/sıra boşluğunu reddet.
2. `decision_time` anında `MarketState`'i dondur; Expert ve candidate kararları
   daha sonraki veriyi görmez.
3. Bir emri yalnızca candidate'ın kaydedilmiş kabul olayından sonra yarat.
4. Bildirilen `submission_time` anında gönder; en erken bar dolumu, daha yüksek
   sadakatli bir kaynak başka bir zamanı gözlemlenebilir kılmadıkça, sonraki
   uygun bar açılışıdır.
5. Önceden bildirilmiş fonlama sıralamasını uygula (başlangıçta
   `SETTLEMENT_BEFORE_ORDERS`), bacak başına ücretler/kayma, sonra hesap/pozisyon
   mutasyonunu tam olarak bir kez.
6. Hem stop hem hedefe değen bir bar için belirsizliği kaydet ve
   `STOP_FIRST` kullan. Boşluk-aşan piyasa çıkışları açılış fiyatından dolar;
   bir zaman aşımı bildirilen olayında çıkar; tape sonu, önceden kayıtlı
   olduğu gibi kapatır ya da sansürü işaretler.
7. Değiştirilemez emir, dolum, pozisyon, fonlama, maliyet ve terminal-defter
   olayları yay.

Kısmi dolumlar, iptaller ve pasif limitler Level 1'de desteklenmez ve
kapalı-başarısız olmalıdır. Stres için kullanılıyorsa rastgeleleştirme
tohumlanır, günlüklenir ve asla açıklanmayan varsayılan değildir. Borsa olay
zamanını, alma/kullanılabilirlik zamanını ve simülatör işleme sırasını ayırt
et.

## Gerekli altın (golden) ve diferansiyel testler

* aynı-bar stop/hedef, boşluklar, zaman aşımı sınırı, giriş-bar sayımı;
* başlangıç/bitiş sınırlarında ve tam-tape ile pencere replay'ında fonlama;
* her iki bacakta ücretler/kayma ve muhasebe/NAV mutabakatı;
* trade-yok ve sıfır-dolum kaynağı; eksik veri kapalı-başarısız;
* aynı tape/config/tohum için deterministik replay/hash eşitliği;
* hızlandırılmış ekonomiden önce skaler referans ile hızlandırılmış replika
  paritesi;
* Level N, sessizce Level N+1 semantiği sağlamamalıdır.

Bunlar mevcut `v7/lab/sim.py` semantiğiyle ve fonlama terminal-sınır kusurunun <!-- AUDIT-DOC-PATHS: FOREIGN_REPOSITORY `v7/lab/sim.py` belongs to the audited V7 materials, not to this repository tree. -->
diferansiyel replay gerektirdiği denetim bulgusuyla uyumludur. Bunlar
**PROJECT_EVIDENCE_SUPPORTED mühendislik kontrolleridir**, piyasa kanıtı değildir.

## Kanıt sınırı

Olay-güdümlü execution önemlidir çünkü sinyal, gönderim, dolum ve pozisyon
olaylarının farklı zamanları vardır; eşzamanlılıklarını varsaymak look-ahead ve
dolum yanlılığı yaratır. Bu bir simülasyon-tasarımı olgusudur; V8'in trade
edebileceği iddiası değildir. Yukarıdaki sayısal politikalar bilinçli olarak
muhafazakâr tasarım seçimleridir.
