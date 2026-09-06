# D-152 Senaryo-Merkezli Delil Profili ve Quad Tenzi̇li (Tam Metin Şartname)

**Durum:** PROVISIONAL_DECISION · **Tarih:** 2026-09-06 · **Kurallar:** 12, 28–31, 44, 51–56
**Ardıllık:** D-147, D-150, D-151'i genişletir; kilitli değişmezi değiştirmez; yalnızca sunum yetkisini daraltır.

## 1. Ölçüm krizi

12-aylık quad (`research/tape/quad-1h-12m/tape.jsonl`) mühendislik tanısı için faydalıdır ancak
manşet skaler (`+%50.9`, `TOTAL REALIZED RUST CASHFLOW`) olarak politika kalitesine terfi ettirildi.
Bu terfi Kural 12 adlandırmasını ihlal eder (simüle çıktı gerçekleşmiş diliyle yazıldı) ve beş ayrı
delil alanını (geçmiş tanı, sağlamlık, dondurulmuş-OOS tekrar, ileriye dönük gölge, gerçekleşmiş
uzlaşı) tek skalere indirger. D-152 quad'ı silmeden tipli tanı mahkemesine tenzil eder.

## 2. Ontoloji

Tanı patolojisi (`BURNED_DIAGNOSTIC`, terfi `NONE`), senaryo hücresi (hücre başına görünür, ortalama
yok), sağlamlık topolojisi (pasaport-bağlı negatif yetki), tekrar (`REPLICATION_ONLY`), ileriye
dönük destek (`PROSPECTIVE_ONLY`), gerçekleşme (`REALIZATION_ONLY`), sertifikalı edge (yalnızca
Kaizen + WRC + gerçek DSR + SPA). `SUPPORTED_EDGE`, `SIMULATED_CASHFLOW`, `REALIZED_CASHFLOW`
ayrık ve birbirine dönüşmez.

## 3–9. (İngilizce tam metinle aynı)

Senaryo mahkemesi 12 alegoriyi (A01–A12) ve 14 Foundry ailesini yeniden kullanır; sentetik PASS
hiçbir şey vermez, sentetik FAIL yalnızca pasaportu geçen jeneratörle ve yalnızca
`StructuralRobustness` sınıfı iddialara karşı challenge eder; G0–G9 kapıları §5'teki gibidir;
kanonik çıktı `PolicyEvidenceProfile`'dır (`assurance/` sahibidir); quad etiketleri §7'deki gibi
tanıya çevrilir; 12-aylık quad mevcut soy için `BURNED_DIAGNOSTIC`'tir; yanlışlama hipotezleri ve
14-testlik adversarial paket ile doğrulanır. Ekonomik hüküm `NO_ECONOMIC_CLAIM` kalır.

Tam bağlayıcı tanım için İngilizce tam metin
(`docs/contracts/D152_SCENARIO_CENTRIC_EVIDENCE_PROFILE_SPEC.md`) geçerlidir.
