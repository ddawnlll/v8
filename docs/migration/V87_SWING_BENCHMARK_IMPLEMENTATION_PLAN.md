# V8.7 Swing Benchmark uygulama planı

Durum: DRAFT / NOT STARTED. Tarih: 2026-09-11.
Tam kapsam: [V8.7 tam metin önerisi](../contracts/V87_SWING_BENCHMARK_SPEC.md).
Bu plan yalnızca dokümantasyon teslimatıdır; uygulama kodu ve koşu sonucu yoktur.

## 1. Çalışma kuralları

- Tüm yeni uygulama ve testler Rust içinde `v8-core/` altında yapılır.
- Önce mevcut gerçek çağrı yolu haritalanır; Python bulgusu Rust hatası diye
  varsayılmaz. Mevcut kirli çalışma ağacı ve başka işler korunur.
- Her iş paketi küçük, doğrulanabilir değişikliklere bölünür. Mevcut reset
  politikasının relevant checks ve tier yaklaşımı uygulanır.
- Mühendislik kontrolleri için test fixtures yalnızca test harness'inde;
  ekonomik değerlendirme yalnızca gerçek gözlemlerle. Tape eksikse skip/absence
  açık raporlanır, skipped ekonomik test başarı kanıtı değildir.
- Bir skor hedefine ulaşmak hiçbir iş paketinin definition of done'ı değildir.
- Harici issue/PR, deployment veya canlı işlem bu planla otomatik başlatılmaz.

## 2. Bağımlılık sırası

`SB01 → SB02/SB03 → SB04 → SB05 → SB06 → SB07 → SB08 → SB09 → SB10`

SB02 muhasebe ve SB03 zaman bölme ayrı ele alınabilir, fakat koşu kimliğinde
birleşmeden ekonomik karşılaştırma yapılmaz. SB09 public shadow kayıt altyapısı
erken hazırlanabilir; sayılacak policy kanıtı ilgili sürüm dondurulduktan sonra
başlar. SB10 teknik release ile ekonomik yeterliliği ayrı sonuçlandırır.

## 3. İş paketleri

| ID | İş ve mevcut başlangıç noktası | Bağımlılık | Çıktı / kabul ölçütü |
|---|---|---|---|
| SB01 | Dört yıllık veri, burn geçmişi ve Rust çağrı yolu envanteri. `benchmark/case.rs`, `runner.rs`, `population.rs` | Yok | Gerçek tarih/sembol/kapsam/hash tablosu; DEVELOPMENT/BURNED/USAGE_UNKNOWN/PROTECTED rolleri; mevcut CLI→runner→cashflow→report haritası; resmi evaluator açığı görünür |
| SB02 | Yaşam döngüsü ve para uzlaşması. `cashflow.rs`, `portfolio.rs`, `execution_boundary.rs` | SB01 | Tekil round-trip, fill atfı, kısmi kapanış/reversal/MTM; para ve getiri ayrımı; equity uzlaşması; parse hatası sıfıra dönüşmez |
| SB03 | 24/12/12 veri planı ve causal fold yürütmesi. `benchmark/population.rs` | SB01 | Gerçek role göre tarihli partition manifesti; warmup, label maturity, purge/embargo, açık pozisyon taşıma, fold return/trade atfı |
| SB04 | Gerçek veriyle uçtan uca diagnostic runner ve immutable artifact paketleme. `benchmark/runner.rs`, `receipt.rs`, `ledger.rs` | SB02, SB03 | Açık tarih aralığında çalışan Rust yol; tam kimlik; PARTIAL/COMPLETE ayrımı; atomik yayın; sürümlü eski ledger doğrulaması; diagnostic resmi receipt gibi sunulmaz |
| SB05 | Swing baseline, gerçek maliyet ve risk karşılaştırması. `experts/squeeze_swing.rs`, `portfolio.rs`, `usdm_sim.rs` ve aktif execution yolu | SB04 | Bir sade baseline; önceden ilan edilmiş holding/risk; cash/buy-hold/equal-weight/simple-trend karşılaştırmaları; funding kapsamı, intrabar ambiguity, correlation görünür |
| SB06 | Trial registry ve istatistik ailesi. `evaluation/`, `statistics/`, `benchmark/observation.rs` | SB05 | Tüm gerçek denemeler; ortak zaman matrisi; bağımlılık duyarlı belirsizlik; uygun DSR/WRC/SPA/PBO hesapları; eksik/power yetersizliği açık; başka tape fallback yok |
| SB07 | Scorer ve gate sözleşmesi. `benchmark/scoring.rs`, `gate_authority.rs`, `certificate.rs`, `report.rs` | SB06 | Kalibrasyon kaydı; eksik kanıt sabit puan almaz; gate semantic mapping; kriterlerin gerçek evidence bindings'i; eski/yeni ölçek ayrı |
| SB08 | Dondurulmuş walk-forward, sınırlı ablation ve final değerlendirme | SB07 | Önceden ilan edilmiş dört fold ve family; tüm sonuçlar görünür; final yalnızca role uygunsa açılır; tekrar bakış yeni trial olarak kayıtlı |
| SB09 | Gerçek prospektif shadow | SB04, sayılacak sonuçlar için policy freeze | Gerçek alınma/karar zamanları; late/missing data; restart/replay/dedup; işlemin sonuç ufku; tarihsel replay ile ayrım; yeterlilik yoksa UNDERPOWERED |
| SB10 | Teknik sürüm ve bağımsız ekonomik değerlendirme | SB08, SB09 durum raporu | Technical release checklist; unresolved listesi; yeniden üretim; Tier D dokümantasyon/otorite işleri; ekonomik sonuç ayrı, NO_ECONOMIC_CLAIM geçerli |

Tablodaki yollar mevcut başlangıç noktalarıdır; yeni dosya yaratma veya bu
modüllerin bütün fonksiyonlarının yeterli olduğu iddiası değildir. SB01 hedef
değişiklik yerlerini gerçek call graph üzerinden kesinleştirir.

## 4. Her pakette uygulanacak adımlar

### SB01 — veri ve kullanım geçmişi

1. Sembol/ürün/venue/frekans bazında gerçek dosyaları say; ilk/son zaman,
   boşluk, tekrar ve funding/mark kapsamını çıkar.
2. Kaynak hash'lerini manifestle karşılaştır; hash'in kaynağın doğruluğu veya
   geçmiş kullanılabilirlik zamanı olmadığını ayrı alanlarla koru.
3. Deney ve burn kayıtlarıyla dönemleri policy lineage bazında etiketle.
4. 24/12/12 şemasını gerçek takvime çevir. Protected kalmadıysa planı
   diagnostic + gelecekteki shadow olarak düzenle; veriyi yeniden adlandırma.
5. Aktif evaluator/CLI boşluklarını ve mevcut Rust doğrulamalarını listele.

Çıkış şartı: dört yıllık kapsama ilişkin doğrulanmış tablo veya açık eksik
envanter; hiçbir bilinmeyen dönem otomatik protected değil.

### SB02 — önce para doğru olsun

1. Gerçek kayıtta bir pozisyon kimliğinin birden fazla yaşam döngüsünü seç.
2. Fill/order/lifecycle bazında kapanışları bağla; tutar ve return türlerini ayır.
3. Netting reversal, partial exit, açık pozisyon ve funding geçişlerini ele al.
4. Bağımsız hesap uzlaşması üret; fee/slippage iki kez düşülmesini sınayan test ekle.
5. Eski sonuçlar yeniden hesaplanacaksa yeni run kimliği kullan; eski dosya korunur.

Çıkış şartı: hesap özsermayesi ile olay bazlı defter hassasiyet sözleşmesi
içinde eşleşir; anomaliler ERROR/UNRESOLVED, sıfır kâr değildir.

### SB03–SB04 — veri planı gerçek yürütmeye bağlansın

1. Önerilen protokol ve manifest şemasını Rust'ta doğrulanabilir hale getir.
2. Varsayılan 500-bar mantığını authoritative değerlendirmeden ayır; smoke
   ayrı profil olsun. Kesin CLI bayrakları SB01'de mevcut parser'a göre belirlenir.
3. Fold'lara ihtiyaç kadar geçmiş warmup yükle; kararlar sadece olgun bilgi görsün.
4. Sürekli equity ve giriş-kohortu trade raporunu ayrı üret; sınırda açık
   işlemlerin devam verisi sonraki eğitime erken sızmasın.
5. Gerçek küçük veriyle tüm yolu çalıştır; ardından izinli bir yıllık diagnostic.
6. Kesilmiş iş/restart, cache identity, dosya hash ve eski digest testlerini tamamla.

Çıkış şartı: aynı veri/kod/config ile tekrar üretilebilir sonuç; dataset/config
değişince kimlik değişir; tamamlanmamış koşu başarılı gösterilemez.

### SB05–SB07 — ekonomik soru ve ölçüm tanımlansın

1. Hedefi mutlak risk kontrollü getiri mi, benchmark excess mi olduğuyla yaz;
   birincil comparator ve risk bütçesini deneyden önce kaydet.
2. Tek swing baseline kur; 2–14 gün tutuş hipotezini gerçekleşen dağılımla ölç.
3. Funding olay çizelgesi, komisyon, fiyat etkisi varsayımları ve intrabar
   belirsizliği strategy/baseline için aynı rapor temelinde göster.
4. Az sayıda aday ailesini preregister et; denenmiş/terk edilmiş tüm ayarlar kayıtlı.
5. Efektif örneklem/CI ve istatistikleri gerçek ortak zaman matrisinden hesapla.
6. Raw metrics tamamlanınca scorer'ı development verisinde kalibre et. Önceki
   50/20 hedefini geçmek için ağırlık veya referans değiştirme.
7. Gate başına gerekli gözlem, predicate ve eksik davranış testleri oluştur;
   identity/determinism/ledger/causality kontrollerini birbirine karıştırma.

Çıkış şartı: iyi görünen tek metrik başarısız kontrolü telafi etmez; eksik
alanlar görünür; official evaluator/authority yoksa resmi certificate üretilemez.

### SB08–SB10 — doğrulama ve sürüm kapanışı

1. Aday seçim algoritması ve refit bütçesini dondur; dört fold'u sırayla yürüt.
2. Sonuçları bütün olarak raporla: net return, excess, drawdown, risk/exposure,
   turnover, maliyet, hold dağılımı, censored oranı, rejim ve belirsizlik.
3. Ablation geliştirme/seçim ailesine dahildir. Test sonucuyla yeni ablation
   tasarlanırsa o test korunmuş rolünü kaybeder.
4. Final role uygunsa tek frozen policy/protocol üzerinde aç. Başarısız sonuçta
   parametre değiştirip aynı finali yeniden bağımsız sınav gibi kullanma.
5. Shadow'u takvim doldu diye başarılı sayma; gerçek sonuç olgunluğu, olay sayısı,
   rejim ve veri kapsamıyla yeterlilik bildir.
6. Teknik checklist ve ekonomik sonucu ayrı kapat. Negatif strateji sonucunda
   testleri gevşetmek yerine adayın reddini/yeniden araştırmayı kaydet.

## 5. Kabul test matrisi

| Kontrol | Gerekli kanıt | Başarısızlık davranışı |
|---|---|---|
| Veri rolü | Bilinen burn period'u final'e sokma denemesi reddedilir | INVALID_ROLE |
| Nedensellik | Tamamlanmamış üst zaman mumu ve olgunlaşmamış label kullanımı yakalanır | INVALID_CAUSALITY |
| Muhasebe | Reused position id, partial/reversal ve gerçek kayıt equity uzlaşması | INVALID_ACCOUNTING |
| Maliyet | Bir kez fee/funding, gömülü slippage'ın tekrar düşülmemesi | INVALID_COST_BASIS veya eksik maliyet |
| Fold sınırı | Carry pozisyon, warmup ve late outcome doğru atfedilir | INVALID_SPLIT |
| Tekrar üretim | Aynı kimlikte sonuç eşitliği; ilan edilmiş determinism kapsamı | DETERMINISM_FAILURE |
| Artifact | Değiştirilmiş/eksik dosya ve partial run reddi | INVALID_ARTIFACT |
| Geçmiş ledger | Bilinen sürümler kendi kanonunda; bilinmeyen sürüm fail closed | UNSUPPORTED_VERSION/INVALID_LEDGER |
| İstatistik | Gerçek aile kapsamı, ortak eksen, eksiklik ve yeterlilik | UNDERPOWERED/UNRUN; asla varsayılan PASS |
| Skor | Eksik kanıt puan kazanmaz; eski ve yeni scorer kimlikleri ayrı | UNAVAILABLE |
| Shadow | Replay prospektif sayılamaz; freeze öncesi sonuç karışamaz | INELIGIBLE_EVIDENCE |
| Otorite | Yüksek score veya gate PASS canlı/economic yetki üretemez | NO_ECONOMIC_CLAIM |

Kontrol adları taslak davranış etiketleridir; yeni Rust error enum'u burada
uygulanmış sayılmaz. Mevcut taxonomy yeterliyse korunur.

## 6. Çalıştırma ve doğrulama bütçesi

Her küçük değişiklik: touched fmt, compile/clippy ve ilgili Rust testleri.
Gerçek veri kabulü yalnızca değişen davranış için küçük ama sonuç ufku yeterli
bir diagnostic parçada; final veri rutin test fixture'ı değildir.

Milestone/release sınırında mevcut proje komutları:

```sh
cargo check --manifest-path v8-core/Cargo.toml
cargo clippy --manifest-path v8-core/Cargo.toml
cargo test --manifest-path v8-core/Cargo.toml
.venv/bin/python tools/audit_python_boundary.py
python3 tools/audit_synthetic_leakage.py
python3 tools/audit_economic_claim.py
```

Bu komutlar bu dokümantasyon değişikliğinde çalıştırılmış değildir. Yeni
benchmark CLI örnekleri çalışır komut gibi uydurulmaz; SB04 tamamlandığında
gerçek help/exit-code doğrulamasıyla runbook'a eklenir.

Hızlandırma sırası: ölçülmüş süre/bellek profili → decode/feature cache →
bağımsız koşu paralelliği → resume. Tüm dört yılı her commite koşmak yoktur.
Cache protected bilgiyi sızdırıyorsa hız optimizasyonu kabul edilmez.

## 7. Tahmini takvim ve sürüm dilimleri

| Dilim | Planlama tahmini | İçerik |
|---|---|---|
| V8.7-dev.1 | 2–4 iş günü | SB01 ve SB02 başlangıcı: envanter, para doğruluğu |
| V8.7-dev.2 | Sonraki 4–7 iş günü | SB02–SB04: fold + gerçek diagnostic yol |
| V8.7-dev.3 | Sonraki 5–10 iş günü | SB05–SB07: baseline, maliyet, statistics/scorer |
| V8.7-rc | Sonraki 3–5 iş günü | SB08 ve teknik yeniden üretim; kalan açıklar |
| Prospektif ekonomik değerlendirme | Veri/işlem olgunluğuna bağlı | SB09; bitiş tarihi veya skor sözü yok |

Yaklaşık 3–6 haftalık teknik iş hipotezidir; bir mühendis akışı ve mevcut
altyapının yeniden kullanılabilir olması varsayılır. Dört yıllık veri bozuksa,
resmi evaluator eksikliği beklenenden büyükse veya funding erişimi yetersizse
SB01 sonrası yeniden tahmin yapılır. Tag'ler öneridir; bu plan onları yaratmaz.

## 8. Geçiş ve geri dönüş

Eski benchmark diagnostic/repro modunda tutulur, yeni protokol ayrı kimlik
ve çıktı kökü kullanır. Aynı gerçek, korunmamış veri üzerinde eski/yeni fark
raporu çıkarılır; fark scorer değişimi, muhasebe düzeltmesi, pencere veya
policy değişimi diye atfedilir. Eski skorun üstüne yeni skor yazılmaz.

Yeni yol sorunluysa eski diagnostic yol kullanılabilir, fakat eski yolun
otoritesi yükseltilmez. Eski ledger ve ham tape üzerinde geri alınamaz
migrasyon yoktur. Yeni çıktıların kaldırılması geçmiş kanıtı etkilemez.

## 9. Açık kararlar ve tamamlanma takibi

SB01 ile kesinleşecek: dört yılın tarihleri ve burn haritası, ilk sembol
evreni, gerçek aktif execution/evaluator yolu, veri kalitesi açıkları.
SB05 öncesi kesinleşecek: ekonomik mandat, primary baseline, risk bütçesi,
aday ailesi ve deney bütçesi. SB07 öncesi kesinleşecek: normalizasyon,
coverage davranışı, gate semantic mapping ve authority gereksinimi.

Şu an tamamlanan tek teslimat tam metin öneri ve uygulama planıdır.
SB01–SB10 NOT STARTED. Skor, getiri, gate geçişi veya dört yıllık test sonucu
bu dokümantasyon teslimatında üretilmemiştir.
