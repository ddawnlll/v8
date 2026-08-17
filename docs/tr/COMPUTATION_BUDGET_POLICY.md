# Hesaplama Bütçesi Politikası (D-099)

**Durum:** PROVISIONAL_DECISION. Bu politika ajan ve operatörün doğrulama
işini yönetir. Bilimsel geçerlilik kapılarını gevşetmez ve ekonomik iddia
üretmez.

## Kural

Beş saniyeden uzun sürmesi beklenen her hesaplamadan veya zaten yeşil olan bir
kontrolü tekrar çalıştırmadan önce şunları belirt:

1. Sonucun değiştirebileceği karar nedir?
2. Hangi yeni semantik riski ya da belirsizliği çözüyor?

Hesaplamayı ancak beklenen marjinal karar değeri toplam maliyetini aşıyorsa
çalıştır:

```text
beklenen değer ≈ P(sonuç kararı değiştirir) × etki × yenilik
                 + tekrar kullanım değeri
                 − çalışma süresi − kullanıcı gecikmesi
                 − bağlam/araç maliyeti − tekrar maliyeti
```

Bu, sahte kesinlik üreten bir hesap değil, karar yardımcısıdır. Sonuç açıkça
pozitif değilse hesaplamayı çalıştırma.

## Zorunlu istisnalar

Bu kural zorunlu bir semantik-sınır kapısını atlamaya izin vermez. Bir değişim
şunlardan birini etkiliyorsa en küçük uygun kapıyı çalıştır:

- doğruluk semantiği veya bilinen bir hata;
- determinizm, scalar/SIMD/backend parity, kimlik veya serileştirme;
- güvenlik, authority, veri bütünlüğü veya fail-closed davranış; ya da
- açıkça istenen handoff/release kapısı.

Bu sınırları etkileyemeyen bir değişimde önceki yeşil test kanıttır; tekrar
edilecek ritüel değildir. Özellikle yalnızca dokümantasyon veya biçimlendirme
değişimi kod test paketini yeniden çalıştırmayı gerektirmez.

## İşletim sınırları

1. Canlı kararı ayıran en küçük kontrolü seç. Yeni semantik kapsama eklemeyen
   tam matris yerine hedefli test kullan.
2. Tam handoff paketi her handoff için en fazla bir kez, anlamlı kod
   değişimleri bittiğinde çalışır. Sonradan üretilen doküman, biçim veya metin
   değişti diye tekrar edilmez.
3. Yeşil sonuçtan sonra ek doğrulama için bütçe 60 saniyedir. Aşılırsa dur ve
   mevcut kanıtı, kalan belirsizliği ve onu çözecek tam sonraki kontrolü
   bildir.
4. Bazı sınırlar tamamlayıcıdır; CPU/GPU parity fixture ile capability probe
   gibi. Ortak karar önce adlandırılırsa bunlar tek, sınırlı gate bundle olarak
   çalışabilir.
5. Ortama bağlı doğrulama makbuzu yoksa bunu dürüstçe bildir; ilgisiz yerel
   hesaplamayla güven üretmeye çalışma.
