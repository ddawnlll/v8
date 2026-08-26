# V8.5 M0 Ratifikasyon Adayı

**Durum:** `M0 RATIFICATION CANDIDATE` / bağlayıcı değil / `NO_ECONOMIC_CLAIM`

**Sürüm:** DRAFT-2 (sunulan V8.5 mimarisinin cerrahi revizyonu)

> [!IMPORTANT]
> **Otoritatif Tam Metin Şartnamesi:**
> 35 bölümden oluşan eksiksiz V8.5 mimari şartnamesi ve araştırma monografı kalıcı olarak [`docs/tr/V85_ARCHITECTURE_SPEC.md`](V85_ARCHITECTURE_SPEC.md) dosyasında kayıtlıdır. Tüm geliştirmeler, iddialar ve ispatlar bu tam metne çıpalanır.

Bu belge aktif anayasa değişikliği değil, V8 genişletme teklifidir. İnsan maintainer tarafından ratifiye edilmiş bir D-series supersession gelene kadar mevcut V8 Anayasası ve kayıtlı kararlar üst otoritedir. Mimari korunmuş, ilk uygulama kapısındaki yetki sınırları daraltılmıştır.

## M0 anayasal sınırlar

1. `SUPPORTED_EDGE` ve `REALIZED_CASHFLOW` birbirinden ayrı ve birbirine çevrilemez kanuni iddialardır. Donmuş OOS/istatistik kanıtı fiziksel settlement yetkisi üretemez.
2. `AuthorityProjection`, mevcut üç boyutlu `crate::authority::Authority` üzerinde salt-okunur kanonik görünümdür. Yetki mint edemez, `ClaimRegistry` yazamaz, iddia sınıfını değiştiremez, hüküm veremez veya terfi yolu oluşturamaz. Güvenlik koşulu `AdmissibleClaims(output) ⊆ AdmissibleClaims(input)`; bilinmeyen veya karşılaştırılamaz eşlemeler fail-closed olur.
3. Assurance Fabric, karara bağlanmış D-136 kanıtı üzerinde deterministik bileşim görünümüdür. Yalnız `EvidenceAttestation`, argüman, `ClaimRule` değerlendirmesi ve `DefeaterReceipt`/`AssuranceCaseReceipt` üretir. Normatif iddia mint’i bağımsız denetim ve mevcut kuvvetler ayrılığıyla yalnız Kaizen hüküm yolunda kalır.
4. M0’da sentetik full-chain Foundry/System Proving Ground çıktısı yalnız deterministik `#[cfg(test)]` sabotaj ve entegrasyon harness’ıdır. Production `EvaluationCase`, rapor, sertifika veya `ClaimRegistry` yoluna giremez. Gelecekteki genişleme ayrı ratifiye D-series değişikliği, transitive taint ve yalnız-negatif sentetik yetki gerektirir.
5. Açık ratifiye supersession gelene kadar WRC + genuine DSR + Hansen SPA, `SUPPORTED_EDGE` için aktif yüktür. Gelecekteki varsayım-farkındalıklı `StatisticalPlan`, yalnız sonuç öncesi D-series yetkili `MethodSubstitutionReceipt` ve eşit/daha güçlü hata kontrolü kanıtıyla yöntem değiştirebilir.
6. Mühürlü `EvaluationCase` değişmez ve yeniden açılamaz. Yeni ilan edilmiş shadow/live gözlemleri değişmez `EvaluationEpoch` snapshot’ları üretir; politika, kod, config, veri rolü, istatistik planı veya yetki kuralı değişimi yeni case üretir. Sertifikalar süreli olup `SUPERSEDED`, `REVOKED`, `NARROWED` veya `EXPIRED` olabilir.
7. DSR yön/tip uyuşmazlıkları, yetersiz örnek fallback’leri ve vekil PBO/DSR çıktıları `BLOCKING_IMPLEMENTATION_DEBT` sayılır; gerçek ve sürümlenmiş makbuzlar oluşana kadar `NO_ECONOMIC_CLAIM` kalır.

## Production Growth Contract

Amaç uzun vadeli maliyet-sonrası geometrik sermaye büyümesidir. M0 asgari deterministik alanları açıklar: başlangıç/mevcut özsermaye, gerçekleşmiş/gerçekleşmemiş PnL, ücretler, funding, slippage, açık pozisyonlar, drawdown ve geometrik büyüme formülü sürümü. Eksik FX, kapasite, yükümlülük veya değerleme girdileri `UNKNOWN`/`INCOMPLETE_ECONOMICS` kalır; sıfır/default kullanılamaz. Haftalık eşdeğer ve stretch hedefler yetkisiz `PlanningAmbition` metadata’sıdır; politika seçimi, challenger sıralaması, durma, sizing, çıkış, terfi veya readiness’e ulaşamaz.

## M0 uygulama sırası

- **M0:** yetki/claim/istatistik/sentetik/lifecycle P0 sınırlarını kapat; governance iş maddesini ve yeniden kullanım matrisini kaydet.
- **M1:** pasif Assurance Fabric, değişmez case/epoch makbuzları, hard-defeater yayılımı ve capability testlerini uygula; terfi kapalı kalsın.
- **M2:** deterministik PGC metrikleri, gerçek tipli istatistikler, trial debt ve korunmuş OOS ile gerçek-veri deployment-equivalent mahkemesini çalıştır.
- **M2b:** Foundry/SPG’yi yalnız `#[cfg(test)]` full-chain sabotaj harness’ı olarak çalıştır.
- **M3+:** TEVV, shadow/live epoch, revocation ve gelecekteki sentetik genişlemeyi ancak sahip kararları ve kapıları oluşturulduktan sonra ekle.

## Zorunlu doğrulama

Ratifikasyon adayı; yetki yükseltmeme, claim mint capability, sentetik izolasyon, DSR tipleme, vekil metrik karantinası, mühürlü case değişmezliği, epoch sıralaması, holdout burn, deterministik PGC muhasebesi ve sertifika iptali için Rust contract/sabotaj testleri gerektirir. Sertifikasız tüm ekonomik çıktılar `NO_ECONOMIC_CLAIM` kalır.

İlgili governance iş maddesi: `docs/issues/ISSUE_V85_RATIFICATION_CANDIDATE.md`.
