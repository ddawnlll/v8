# D-161 — V8.6 CLI ayrıştırmasını clap'e devretme

Durum: PROVISIONAL_DECISION. Tarih: 2026-09-07. Issue: #351 (M09).
Yetki: kullanıcı tarafından onaylanan V8.6 uygulaması, tam metin monograf §12 CLI ve Appendix C ANA-A7; WORK_ITEM_POLICY §§3–4. Ekonomik yetki verilmez.

## 1. Korunan öneri ve kapsam

Önerinin eksiksiz özgün metni [V8.6 tam metin](../contracts/V8_6_PRODUCTION_RECALIBRATION_FULL_TEXT.html) dosyasında korunur. SHA256: c766a472eb9095f87864c4dfeaf898877a06fd47eccdd44e8697c613a6eb01b1. Öneri geçicidir; bu sınırlı karar finans, RNG, parity veya Kaizen yetkilerini değiştirmez.

M09 genel komut satırı ayrıştırmasını doğrulanmış clap sürümüne devreder. Alan işlemleri mevcut komut handler'larında kalır. Yeni Rust modülü `v8-core/src/cli.rs` komut/argüman şeması ve ayrıştırma sınırını; `main.rs` dispatch'i sahiplenir. Bağımlılık ve lockfile gerçekten mevcut doğrulanmış sürümü belirtir; monografın 4.6.6 adayı mevcut değilse sessizce değiştirilmez.

## 2. Geçerli girdi uyumluluğu

29 mevcut üst komutu, konumsal argümanları, seçenekleri ve geçerli varsayılanları e7d80f22888ff1e94f1be882c878f6af801d5375 tabanında envanterle. Geçerli komut anlamı, birimler, girdi dosyaları, alan handler'ları ve alan hata çıkış kodları korunur. JSON request doğrulaması mevcut sahibinde kalır. Ayrıştırma ikinci finansal doğrulama motoru değildir.

## 3. Geçersiz girdide açık davranış değişikliği

Bozuk sayısal seçenek, bilinmeyen seçenek/komut, yinelenen tek değerli seçenek, eksik zorunlu değer ve fazla konumsal değer alan işlemi başlamadan tanı mesajı ve çıkış 2 üretir. Eski esnek döngülerden farklı olarak açıkça verilen bozuk girdi varsayılana düşmez. Varsayılan yalnız seçenek verilmediğinde uygulanır. Help çıkışı 0'dır. Bu kasıtlı CLI doğruluk değişikliğidir; hata mesajı byte uyumluluğu iddia edilmez ve geçerli trading politikası değişmez.

Envanterde bulunan her fark receipt'e yazılır. Geçersiz girdiye dayanan caller açıkça düzeltilir veya bloke bırakılır; gizli compatibility fallback eklenmez.

## 4. Sahiplik ve kaldırma

clap Command/Arg/ArgMatches veya derive eşdeğeri kullanılır. Taşınan handler'lardaki manuel flag tarama, bozuk sayıyı varsayılana çevirme ve konumsal sayı kontrolleri kaldırılır. Bütün eski parser'ları koruyan sınırsız tail argümanlı bir üst clap wrapper'ı M09'u karşılamaz. Alan request-file komutlarının handler'ları korunur; komut satırı zarfları clap ile tanımlanır.

## 5. Doğrulama

R1: envanter bütün aktif komut/argüman/varsayılan ve eski handler'ı listeler.
R2: gerçek main dispatch clap sonuçlarını tüketir ve eski genel döngüler kaldırılır.
R3: Rust testleri geçerli komutlar, varsayılanlar, bilinmeyen/eksik/yinelenen/bozuk/fazla girdiler, help ve alan dispatch'ini kapsar. Entegrasyonda hedefli test/check, sonunda gerekli tam kontroller çalışır.

Komutlar çalışana kadar receipt PENDING'dir. Parser testi engine entegrasyonu veya V8.6 tamamlanması kanıtı değildir. Sentetik test girdisi production kanıtına giremez.

## 6. Hata ve geri dönüş

Mevcut olmayan pin/API veya belirsiz alan sözleşmesi ilgili sınırda OPEN_PIN'dir. Rust-only ve frozen Python korunur. Geri dönüş kayıtlı parent ve bağımsız CLI değişikliğidir; otonom merge, force-push ve eski branch silme yoktur. EN/TR karar ve layout kayıtları implementasyona eşlik eder.
