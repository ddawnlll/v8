# D-159 Araştırma Geçerliği Denetimi: Makbuz Öz-Doğrulama, Politika-Bağlı Parite, Kapı Yetki Duvarı ve Yönetim Mutabakatı (Tam Metin Şartname)

**Durum:** PROVISIONAL_DECISION · **Tarih:** 2026-09-07 · **Kurallar:** 5, 12, 28–31, 44, 51–57
**Ardıllık:** D-153, D-152, D-151, D-150, D-149, D-147, D-138, D-136, D-118, D-116'yı genişletir; tüm kilitli değişmezleri korur. Ek ekonomik yetki vermez ve hiçbir kapıyı gevşetmez.
**Kapatılan issue'lar:** #327, #328, #329, #330.
**Eserler:** `v8-core/src/benchmark/gate_authority.rs`, `v8-core/src/benchmark/receipt.rs`, `v8-core/src/benchmark/ledger.rs`, `v8-core/src/benchmark/parity.rs`, `v8-core/src/benchmark/external.rs`, `v8-core/src/benchmark/certificate.rs`, `v8-core/src/benchmark/runner.rs`, `v8-core/src/benchmark/types.rs`, `v8-core/src/main.rs`, `v8-core/tests/d152_gate_vector_authority_firewall.rs`, `v8-core/tests/d153_receipt_ledger_selfverify.rs`, `v8-core/tests/d153_parity_adapters_policy_bound.rs`, `v8-core/tests/d153_benchmark_fabric_sabotage.rs`, `docs/contracts/D153_BENCHMARK_FABRIC_SPEC.md`, `docs/tr/D153_BENCHMARK_FABRIC_SPEC.md`, `docs/contracts/IMPLEMENTATION_LAYOUT.md`, `docs/CHANGELOG.md`.
**Normatif metin:** Bu dosya İngilizce `docs/contracts/D159_RESEARCH_VALIDITY_AUDIT_SPEC.md` metninin Türkçe aynasıdır. Normatif yetki İngilizce tam metindedir; çelişki halinde İngilizce metin geçerlidir.
**ID tahsis notu:** D-154, D-155, D-156, D-157 ve D-158 eşzamanlı performans çalışma akışına (#332–#336; `perf/332-cargo-profile-split`, `perf/333-consolidated-test-harness`, `perf/334-bootstrap-scratch-buffer`, `perf/335-zero-copy-hist-bar`, `perf/336-rayon-parallelism` dalları) tahsis edilmiştir ve bir kısmı `main`'e merge edilmemiştir. Bu denetim bu nedenle D-159 altında kaydedilir. Bu karar hiçbir D-15x tanımlayıcısını yeniden kullanmaz, yeniden tanımlamaz veya çift tahsis etmez.

---

## 1. Problem Tanımı

D-153 Benchmark Fabric, güven zincirinde dört bağımsız kırıkla yayınlandı.
Dördünün ortak etkisi zayıf delili *doğrulanabilir* kılmak değil, *doğrulanmış
gibi göstermek* oldu:

1. **#327 — kapı vektörü kayıtlı kapı vektörü değildi.**
   `GateVector` altı pozisyon taşıyordu; oysa D-152 §5 ve D-153 §2.4 G0–G9'u dokuz
   telafi edilemez pozisyon olarak kaydeder. Ayrıca `GateState`, "bu kapı hiç
   hesaplanmadı" durumunu ifade edemiyordu. G6–G9'u hesaplamayan bir koşu
   "hiçbir şey başarısız olmadı" şeklinde okunuyordu. Ayrı olarak
   `PolicyCertificate` hazırlığını yerel olarak türetiyordu ve skalar bir
   `CapabilityScore`'dan `PRODUCTION_READY` yazdırabiliyordu; yani bir renderer
   içinde yetki basıyordu.

2. **#328 — makbuzlar ve defter, depoladıkları digest'e güveniyordu.**
   `BenchmarkReceipt::compute_digest()` elle derlenmiş bir alan listesinin hash'ini
   alıyordu ve defter `digest == entry_hash` şeklinde yazıyordu. Bu listenin
   dışındaki hiçbir alan — eser provenansı, metod sürümleri, kapı provenansı —
   sabit digest altında değişebilirdi. Okuma anında canonical byte'lardan digest
   yeniden hesaplayan hiçbir yol olmadığı için, tahribat yapısal olarak
   tespit edilemezdi.

3. **#329 — harici parite uydurmaydı.**
   `external.rs::evaluate_parity(policy_id)` kendi `policy_id` argümanını
   `_policy_id` olarak çöpe atıyor ve iki sabit diziyi
   (`[0.012, -0.005, ...]` ile `[0.0121, -0.0049, ...]`) karşılaştırıyordu.
   `fill_timing_mae_ms` sabit `0.0`'dı ve `maximum_drawdown_discrepancy_bps`
   PnL farkının motor başına 1.5 / 1.2 / 1.1 ile çarpılmasıyla üretiliyordu.
   Bu, harici bir motora karşı parite değil; parite şartnamesinin yasakladığı bir
   bps toleransı içinde her zaman "neredeyse eşit" raporlayan sabit bir vektördür.
   D-153 §2.6'yı yalnızca isim olarak karşılıyordu.

4. **#330 — yönetim, ağaçtan sapmıştı.**
   D-153 şartname başlığı `RATIFIED_DECISION` iddia ederken her iki karar defteri
   `PROVISIONAL_DECISION` diyordu; defterler, şartname başlığı ve CHANGELOG hiç
   var olmamış `v8-core/tests/benchmark_fabric_adversarial.rs` dosyasını citation <!-- AUDIT-DOC-PATHS: NEGATIVE_CITATION `v8-core/tests/benchmark_fabric_adversarial.rs` is cited here precisely because it never existed; the real D-153 suite is `v8-core/tests/d153_benchmark_fabric_sabotage.rs`. -->
   ediyordu; D-153'ün Türkçe tam metin aynası yokken Türkçe defter onu citation
   ediyordu; `IMPLEMENTATION_LAYOUT.md` silinmiş adapter API'sini anlatmaya devam
   ediyordu; ve CHANGELOG, aynı karar ailesindeki D-156 benchmark-evaluator
   OPEN_PIN'i (hâlâ) açıkken D-153 için "Ratified and fully completed" diyordu.

Ortak arıza modu dördünde de aynıdır: **depolanmış bir iddia, kendi ispatı
muamelesi gördü.** D-159 yapılan değişiklikleri kaydeder ve tekrarını önleyen
değişmezleri sabitler.

---

## 2. Normatif Şartlar

### 2.1 Kapı vektörü ve yetki duvarı (#327)

**R2.1.1** `GateVector` kaydedilen pozisyonların aynen G0–G9'unu ifşa ETMELİDİR.
Pozisyon → ad → sahip eşlemesinin tek kaynağı `types::GATE_DESCRIPTORS`'dır.

**R2.1.2** `GateState` dört varyantlı bir lattice OLMALIDIR: `Pass`, `Fail`,
`Blocked` ve `Missing`. `Missing` bir pass değildir ve "uygulanamaz" da değildir:
kapının hiç hesaplanmadığı anlamına gelir. `readiness()` `Missing` karşısında
değerini düşürMELİ ve hiçbir zaman `Missing` ile terfi etMEMELİDİR.

**R2.1.3** Her kapı başarısızlığı bir `GateFailureClass` TAŞIMALIDIR; böylece
başarısızlık veri yokluğuna, anlamsal ayrışmaya, istatistiksel refütasyona veya
politika ihlaline atanabilir, opak bir boolean değildir.

**R2.1.4** `ReadinessVerdict`, `gate_authority::AuthorityFirewall` tarafından
üretilMELİ ve girdilerin bir *projeksiyonu* OLMALIDIR. Hiçbir renderer, rapor
veya sertifika yetkiyi sıfırdan hesaplamaya yetkili değildir.

**R2.1.5** `cap_authority(a_in, a_out)` monotone yükselememeyi zorunlu
kILMALIDIR: `EvidenceAuthority` sıralamasında `a_out ≤ a_in`. Her render adımı
bu özelliğe karşı assertion edilmeli; özellik testle doğrulanır, varsayılmaz.

**R2.1.6** `SUPPORTED_EDGE` veya konuşlandırma terfisi iddiasının tamamı
`ClaimRegistry` üzerinden çözülMELİDİR. `AuthorityDecision::Registered` varyantı
yalnızca registry üyeliğini doğrulayan `AuthorityFirewall::route_claim` üzerinden
erişilebilir olmalıdır. Zorunlu delilin yokluğu, `N/A`, `UNKNOWN`, `MISSING` veya
`BLOCKED` değeri `NO_ECONOMIC_CLAIM` veya `BLOCKED` üretMELİDİR; asla pass değil.

**R2.1.7** `PolicyCertificate`, kapı vektörünün izin verdiğinden daha güçlü bir
durum dizesi türetememelidir. `to_status_string()` projeksiyon verilmiş verdictün
fonksiyonudur; `MISSING`/`Blocked` kapıları sertifikayı tavanlar.

**R2.1.8 (taşınan OPEN_PIN, çözülmüş değil).** D-152 §5 G7'yi prospective
shadow, G8'i live realization, G9'u certificate olarak adlandırır; D-153
`GateVector` alan adları `g7_generalization`, `g8_prospective_shadow`,
`g9_live_realization` şeklindedir. Bu karar bu çelişkiyi yargılamaz. Eşleme
pozisyoneldir, hiçbir defter yeniden yazılmaz ve çelişki
`OPEN_PIN_GATE_NAMING` ile `AuthorityDecision::OpenPin` olarak yüzeye
çıkarılır. Hangi pozisyonun live-realization kapısı olduğu okumasına bağlı her
türlü kapı-bazlı anlatı, defter çelişkisi bir yönetim kararıyla
çözülene kadar yazılmamalıdır. Hazırlık her iki okumada da aynı olduğu için,
ertelemeler hiçbir kapıyı zayıflatmaz.

### 2.2 Kriptografik makbuz ve defter öz-doğrulaması (#328)

**R2.2.1** `BenchmarkReceipt::compute_digest()`, elle toplanmış bir alan
listesinin değil, *tüm* makbuzun `crate::hash::Canon` üzerinden üretilmiş
canonical digest'i OLMALIDIR. Hiçbir yetki-alakalı alan digest'in dışında
yaşayamaz.

**R2.2.2** Digest algoritmasının kimliği versionlanmalı ve makbuz üzerine
kaydedilmelidir: `d153.receipt.v2` geçerlidir; `d153.receipt.v1` kalıcı olarak
tanınan bir legacy kimliktir. Doğrulama, ikisini sessizce kabul etmek yerine
kayıtlı sürüme göre dağıtım yapmalıdır.

**R2.2.3** `BenchmarkProvenance` ve `ArtifactBinding` tüketilen her eseri (yol,
SHA-256, byte uzunluğu, rol) ve sonucu değiştirebilecek her metod/sürüm
dizesini bağlamalıdır. Fiziksel olarak üretilmemiş veya diskte doğrulanmamış bir
eseri citationlamak dokümantasyon hatası değil, anti-sentetik direktif altında
kritik bir sistem halüsinasyonudur.

**R2.2.4** Bir makbuz ancak yeniden doğrulandığında delildir. `verify()`
canonical byte'lardan yeniden hesaplamalı; `verify_artifacts()` fiziksel
dosyaları yeniden hash'lemeli; `verify_policy_identity()` kimlik kaymasını
reddetmelidir. Rapor üretimi bir `VerifiedReceipt` zorunlu tutmalı ve JSON ile
HTML rendererları yeniden hesaplanan digest'i ve doğrulama metadata'sını
damgalamalıdır; okuyucu hangi digest'in kontrol edildiğini görebilmelidir. HTML
doğrulanmamış bir makbuzu render etmeyi reddetmelidir.

**R2.2.5** Defter her girdiyi, tam canonical makbuz kodlamasını hash zincirine
katan bir `d153.ledger.v2` entry seal ile mühürlemelidir; böylece zincir
içeriği bağlar, depolanan digest'i değil. Defter, satır başına `LedgerTamper`
sınıflandırması ve stabil tahribat kodları içeren bir `LedgerAuditReport`
dönen `audit()` ve `load_with_report()` ifşa etmelidir.

**R2.2.6** Digest karşılaştırması sabit zamanlı olmalıdır. Sonlu olmayan metrik
değerleri inşada reddedilmeli, digest içine kanonikleştirilmemelidir.
Beklenmedik null üreten bir canonical tree sıfır olarak yutulmamalı, hata
olmalıdır.

**R2.2.7 (Dürüst legacy sınırı).** v2 öncesinde yazılmış satırların
kurtarılabilir bir bağı yoktur. Sistem bu satırları `legacy_unbound` olarak
sınıflandırmalı, doğrulanmış saymamalı ve exit `3` ile
`LEDGER_PARTIALLY_BOUND` dönmelidir. Denetim reposundaki gerçek defterde
(7 satır, tamamı v2 öncesi) her satır legacy-unbound olarak raporlanır.
Bunları silmek de yeniden yazmak da kabul edilmez; doğrulandığını iddia etmek de
kabul edilmez.

### 2.3 Politika-bağlı harici parite adapterları (#329)

**R2.3.1** Parite iki fiziksel defter eserinden — bir native taraf ve bir
referans taraf — hesaplanmalıdır ve her ikisi de değerlendirmeden önce case
evidence manifest'inde beyan edilmelidir. In-process bir referans implementasyon
ve sabit bir beklenen vektör yoktur.

**R2.3.2** `SemanticMapping` (sürüm `v8.d153.parity.mapping.v1`) iki kaydın
nasıl karşılık geldiğini beyan etmelidir: pairing key, PnL alanı, opsiyonel
fill-time alanı, opsiyonel sequence alanı. Bir parite sonucu yalnızca adlandırılmış
bir mapping'e göre anlamlıdır; mapping kimliği makbuza yazılır. Mapping'siz parite
default'a düşmez, tanımsızdır.

**R2.3.3** Tolerans tabanlı parite `docs/contracts/PARITY_AND_IDENTITY_SPEC.md`
tarafından yasaklanmıştır. PnL karşılaştırması `==` yerine IEEE-754 bit-deseni
eşitliği (`to_bits()`) kullanmalıdır; böylece `NaN`, işaretli sıfır ve son-bit
kayması ortalamayarak yok edilmek yerine ayrıştırılır. Sonuçlar `ExactMatch`,
`Diverged`, `UnsupportedSemantics`, `UnpairedRecords` veya `DataBlocked`'dır;
"tolerans içinde" diye bir sonuç yoktur.

**R2.3.4** Fill-time ayrışması, iki taraf da fill time taşıdığı sürece mismatch
sayılmalıdır. Taraflardan herhangi biri fill time taşımıyorsa tanısal `None`
olmalıdır — asla `0.0`. Uydurulmuş sıfır hata yasaktır.

**R2.3.5** Drawdown ve equity tanısal değerleri equity eğrilerinden, beyan
edilen `sequence_field` varsa onun sırasıyla hesaplanmalıdır. Mapping bir
sequence alanı beyan ettiği halde defterler kısmen sequence'lıysa, drawdown
tanısı `None` olmalıdır; en iyi tahmin değil.

**R2.3.6** `EngineVersion` ve metod sürümleri gerçek sürüm veya build
tanımlayıcıları olmalıdır. Placeholder değerler (`"N/A"`, `"unknown"`, `"TBD"`,
boş) değerlendirmeyi bloklamalıdır (`DataBlocked`), içinden geçirmemelidir.

**R2.3.7** Parite yetkisi *türetilmeli*, depolanmamalıdır.
`ParityReceipt::authority()` D-152 `BENCHMARK_DIAGNOSTIC_AUTHORITY` tavanından
hesaplanır; serileştirilmiş makbuz yalnızca `authority_class()` ifşa eder ve
ters-serileştirmeyle sahtelenebilecek bir `authority` alanı taşımaz. Parite
çıktısı egemen-olmayan tanısal bir gözlemdir.

**R2.3.8** `BenchmarkReceipt::with_parity()` kimlik uyumsuzluğunu, politika
uyumsuzluğunu, case-hash uyumsuzluğunu ve çelişen eser hash'lerini
reddetmelidir; eser bağlarını birleştirmeli ve makbuz digest'ini yeniden
hesaplamalıdır. Parite, alakasız bir makbuza aşılanamaz.

**R2.3.9 (Dürüst açık, taşınan).** `reconciliation_gaps()`, komisyon, funding ve
terminal balance paritesinin D-116 mutabakatı için **map'lenmemiş** olduğunu
açıkça beyan etmelidir; böylece PnL ve fill-time `ExactMatch` tam ekonomik
mutabakat sanılmaz.

**R2.3.10** Silinen uydurma API (`CommodityExecutionAdapter`,
`LeanParityAdapter`, `SkfolioParityAdapter`, `VectorBtParityAdapter`,
`ExecutionParityReport`, `evaluate_parity`, `parity_passed`) geri gelMEMELIDİR.
Regression test'leri source seviyesinde, sabit literallerin, çöpe atılan
`_policy_id` parametresinin ve uydurma drawdown çarpanlarının
`v8-core/src/benchmark/` içinde bulunmadığını iddia eder.

### 2.4 Yönetim ve dokümantasyon mutabakatı (#330)

**R2.4.1** Normatif durumun her eser için tam olarak bir sahibi olmalıdır. Bir
şartname başlığı ile karar defteri durumda çelişirse, defter hükmeder ve başlık
düzeltilir. D-153 `PROVISIONAL_DECISION` olarak kalır.

**R2.4.2** `docs/`, `docs/contracts/`, `docs/tr/` ve karar defterlerinin
citationladığı her yol, ağaçta mevcut bir dosyaya çözülmelidir. Phantom
referanslar typo değil sözleşme ihlalidir; çünkü üretilmemiş eserlerin görünür
provenans kazanma mekanizmaları tam olarak budur.

**R2.4.3** Rule 44 / D-149 kayıtsız tam metin şartname ister ve Türkçe defter
Türkçe tam metni citationlar. Bu nedenle `docs/tr/DECISION_REGISTER.md`
tarafından citationlanan her karar bir EN kaynak ve bir TR ayna
taşımalıdır; var olmayan bir aynayı gösteren bir defter satırı Rule 44 anchor
ihlalidir.

**R2.4.4** `docs/contracts/IMPLEMENTATION_LAYOUT.md` as-built ağaca
mutabık kılınmalıdır: yeni modüller kaydedilmeli (§1.1 ağacı, §2 dosya
sözleşmesi), silinmiş API yüzeyleri kaldırılmalı, sapmalar §4'te kaydedilmeli ve
sessiz drift bırakılmamalıdır.

**R2.4.5** `docs/CHANGELOG.md` tamamlanma iddiaları gözlenen doğrulamayla
sınırlandırılmalıdır. Aynı karar ailesindeki bir kayıtlı OPEN_PIN açıkken
"Ratified and fully completed" kabul edilmez; girdi neyin implement edildiğini,
neyin kaç testle doğrulandığını ve neyin blokeli kaldığını söylemelidir.

**R2.4.6** Monograflar (`site/index.html`, `site/tr.html`) üretilmiş
eserlerdir. `tools/build_monograph.py` ile yeniden üretilmelidir, elle
düzenlenmemelidir; böylece üretilmiş HTML, `docs/` kaynağından ayrılamaz.

**R2.4.7** R2.4.2 için bir muhafız mevcuttur. `tools/audit_doc_path_refs.py`
dokümantasyonda citationlanan depo yollarını çözer ve çözülemeyen
referanslarda fail eder. Nesir, git object id ve commit sha'lar hariç tutulur;
böylece muhafız gürültüyle devre dışı bırakılmak yerine actionable kalır.

---

## 3. Açıkça Verilmeyenler

D-159 kısıtladığından başka hiçbir yetki vermez. Özellikle:

1. `SUPPORTED_EDGE` yok, konuşlandırma yetkisi yok, terfi yok. Kapsamdaki her
   verdict `NO_ECONOMIC_CLAIM` kalır (Anayasa Rule 12).
2. D-153 bu kararla ratifiye edilmez ve durumu yükseletilmez.
   `PROVISIONAL_DECISION` ayakta.
3. D-156'nın kayıtlı benchmark-evaluator OPEN_PIN'i **açık**: kayıtlı, veriye
   dayalı evaluator olmadan benchmark makbuzu üretilmez.
4. #327'nin G7–G9 adlandırma çelişkisi bir **OPEN_PIN** olarak duruyor.
5. v2 öncesi defter satırları doğrulanmış değil, **bağsız (unbound)**.
6. D-116 komisyon / funding / terminal balance paritesi **map'lenmemiş**.
7. Bu çalışmanın hiçbir yerinde ekonomik metrik, p-değeri, etki büyüklüğü,
   tolerans veya beklenen iyileşme tanımlanmaz. Uydurma vektörler ve çarpanlar
   kalibre edilmez, silinir.
8. Bu daldaki denetim işi **maintainer incelemesi için PR** olarak teslim
   edilir. Merge edilmez ve `main`'e doğrudan push yapılmaz.

---

## 4. Doğrulama Sözleşmesi

| Kontrol | Komut / kanıt | Zorunlu sonuç |
|---|---|---|
| Canonical kapı vektörü + duvar | `cargo test --manifest-path v8-core/Cargo.toml --test d152_gate_vector_authority_firewall` | 15 passed |
| Makbuz + defter öz-doğrulama | `cargo test --manifest-path v8-core/Cargo.toml --test d153_receipt_ledger_selfverify` | 40 passed |
| Politika-bağlı parite adapterları | `cargo test --manifest-path v8-core/Cargo.toml --test d153_parity_adapters_policy_bound` | 50 passed |
| BFS sabotaj suite'i | `cargo test --manifest-path v8-core/Cargo.toml --test d153_benchmark_fabric_sabotage` | 24 passed (BFS-001..024) |
| Workspace regresiyon | `cargo test --manifest-path v8-core/Cargo.toml` | 0 failed |
| Lint kapısı | `cargo clippy --manifest-path v8-core/Cargo.toml --all-targets -- -D warnings` | clean |
| Python boundary dondurulmuş | `.venv/bin/python tools/audit_python_boundary.py` | pass |
| Sentetik sızıntı | `python3 tools/audit_synthetic_leakage.py` | pass |
| Ekonomik iddia muhafızı | `python3 tools/audit_economic_claim.py` | pass |
| Doküman yol referansları (yeni, R2.4.2) | `python3 tools/audit_doc_path_refs.py` | pass with scoped baseline |
| Monograflar yeniden üretildi (R2.4.6) | `uv run --with markdown tools/build_monograph.py --lang en|tr ...` | yeniden üretildi, elle düzenlenmedi |
| Parite CLI, tam eşit | özdeş defterlerde `v8-core benchmark parity …` | `PARITY_EXACT_MATCH`, exit `0`, gap'ler yazdırılır |
| Parite CLI, ayrışma | pertürbe referansta aynı komut | `PARITY_DIVERGED`, exit `1` |
| Parite CLI, placeholder sürüm | `--engine-version N/A` | blocked, exit `1` |
| Parite CLI, beyansız eser | listelenmemiş defter yolu | blocked, exit `1` |
| Legacy defter denetimi | `.audit/benchmark/ledger.jsonl` üzerinde `v8-core benchmark ledger audit` | 7 satır `legacy_unbound`, exit `3`, `LEDGER_PARTIALLY_BOUND` |

---

## 5. Mevcut Sözleşmeler İçin Sonuçlar

- **D-153 §2.6** artık yazıldığı gibi uygulanmaktadır (tipli adapterlar,
  kayıtlı anlamsal ayrışma, parite atfı); sabit vektörler olarak değil. §2.6'nın
  normatif metni değişmemiştir; yalnızca implementasyon durumu değişmiştir.
- **D-152 §5/§6** bir uygulama noktası kazanır: yetki duvarı benchmark delili ile
  yetki arasındaki tek sınırdır ve hazırlık bir sertifika tarafından yerel olarak
  üretilamaz.
- **D-118 / D-138** kimlik ve hashleme kopyalanmaz, yeniden kullanılır: `Canon`
  canonical byte'ları ve mevcut içerik-adresli eser hash'i. D-153'ün "kayıtlı bir
  sebep olmadan yeni kimlik mekanizması yok" non-goal'u ayakta.
- **D-116** parite mutabakatı defterin ima edebileceğinden daha dardır ve bu
  darlığın makine-okunur beyanı `reconciliation_gaps()`'tır.
- **D-149 / Rule 44** hem D-153 (TR ayna eklendi) hem bu karar (EN tam metin +
  TR ayna) için karşılanmıştır.
