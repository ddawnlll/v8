# Nicemlenmiş Hesaplama Uygulanabilirlik Denetimi

**Durum:** `NO_ECONOMIC_CLAIM`  
**Tarih:** 2026-08-20  
**Kapsam:** V8'in bugün nicemlenmiş hesaplama uygulayıp uygulamadığı,
nicemlemenin determinizm sözleşmesini güçlendirip güçlendirmeyeceği ve böyle bir
tasarım düşünülmeden önce çözülmesi gereken bitişik uygulama kusurları.

## 1. Yönetici hükmü

`PROJECT_EVIDENCE_SUPPORTED`: V8 bugün nicemlenmiş hesaplama uygulamıyor.
Yetkili Rust çalışma yolu IEEE-754 `f64`, bit kodlu kimlikler, sabit indirgeme
sırası ve skaler/SIMD/backend parite kontrolleri kullanıyor. Bu deterministik bir
kayan nokta tasarımıdır; tamsayı, sabit nokta, FP8 veya INT8 tasarımı değildir.

`LITERATURE_SUPPORTED`: tamsayı-only çıkarım hesaplama ve depolama maliyetini
azaltabilir; fakat açık bir nicemleme şeması ve doğruluk koruma prosedürü
gerektirir [1]. İlan edilmiş bir öğrenilmiş sıkıştırma ortamında integer-only
çıkarımın platformlar arası tutarlılık sağlayabildiği gösterilmiştir [2]. Paralel
kayan nokta işlemlerinin birleşmeli olmaması yeniden üretilebilirlik riskidir;
bu V8'in mevcut sabit sıra/backend parite kontrollerini destekler, nicemlemeyi
zorunlu kılmaz [3].

`OPEN_QUESTION`: V8'de bit genişliği, signedness, scale, zero-point, rounding,
clipping/saturation, accumulator genişliği, overflow, kalibrasyon popülasyonu,
aralık dışı davranış, dequantization sınırı veya backend parite oracle'ı
tanımlayan bir karar yoktur. Nicemleme bu nedenle varsayılan olarak yoktur.

## 2. Proje kanıtı

Kaynak taraması üretim nicemleme sözleşmesi veya uygulaması bulmadı. Bit-düzeyi
kimlik, binary ledger depolama ve `f64` backend paritesi nicemleme değildir.

`PROJECT_EVIDENCE_SUPPORTED`: aşağıdaki D-103 çözümünden sonra 2026-08-20 Rust
release handoff testi 253/253 geçti; Python sınır ve yasak bileşen denetimleri
de geçti. Bu sonuç yalnız mevcut
deterministik-`f64` iddiasını destekler.

## 3. Eksik nicemleme sözleşmesi

Bir teklif en azından nicemlenecek alanları, sayı formatını, scale/zero-point'i,
rounding ve overflow davranışını, PIT uyumlu geliştirme kalibrasyonunu, yetkili
`f64` baseline'a karşı frozen-OOS hata ölçülerini, backend golden vektörlerini,
kimlik/sürüm kopuşlarını ve değiştirebileceği maliyet kararını önceden
kaydetmelidir.

`LITERATURE_SUPPORTED`: finansal zaman serisi PTQ'da dört-bit sonuçlar
kalibrasyon dönemine ve rejime duyarlı olabilir; bozulma sürdüğünde sekiz-bit
veya yalnız-ağırlık alternatifleri daha dayanıklı olabilir [4]. Bu bulgu V8 için
fayda kanıtlamaz; kalibrasyonun sıradan bir uygulama ayrıntısı sayılamayacağını
gösterir.

## 4. Bitişik depo değerlendirme sınırı
 
`PROJECT_EVIDENCE_SUPPORTED`: `v8-core/src/evaluation/` altındaki değerlendirme kanıt sistemi
sentetik verilerden arındırılmış ve Anayasa Kuralı 12 (`NO_ECONOMIC_CLAIM`) gereksinimlerine
tam olarak bağlanmıştır. Ekonomik otorite ve istatistiksel testler yalnızca kayıtlı `statistics/` ve
`report.rs` yolunda kalır; `evaluation/` bağımsız veya sertifikasız ekonomik iddialar yaymadan
dikey kanıt yüzeyleri (otorite taksonomisi, soybağı DAG'ı, PIT zamansal girişim-yokluğu ve çoklu-test araçları)
ile Target Oracle coverage kayıtlarını sunar.
 
## 5. Karar
 
`PROVISIONAL_DECISION`: mevcut deterministik `f64` sözleşmesini koru.
Nicemlemeyi; tam sözleşme, daha basit baseline karşılaştırması, frozen-OOS hata
kanıtı, backend paritesi ve registry kararı (D-118) olmadan ekleme.
 
Bu denetim kârlılık, doğrulanmış execution, promoted sistem veya hız iddiası
taşımaz.

## Kaynaklar

1. Jacob vd., arXiv:1712.05877, https://arxiv.org/abs/1712.05877
2. He vd., arXiv:2202.07513, https://arxiv.org/abs/2202.07513
3. Shanmugavelu vd., arXiv:2408.05148, https://arxiv.org/abs/2408.05148
4. Ye ve Wanjiku, arXiv:2608.12259, https://arxiv.org/abs/2608.12259
