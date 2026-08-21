# Tarihsel Piyasa Arketipleri Kaydı ve Çoklu Epizot Alegorik Denetim Süiti

**Durum:** ONAYLANMIŞ DENETİM (D-125, ALLEGORY-001)  
**Sahip Otorite:** `TARGET_ORACLE_SPEC.md` §9, `WORK_ITEM_POLICY.md` v1.2, `v8-core/src/evaluation/allegory.rs`  
**Akademik Referanslar:** arXiv:2607.19497 (Trend-Following Skew & Multi-Horizon Persistence), arXiv:2106.08420 (Dynamic Momentum Turning Points), arXiv:2102.02865 (Crypto Bear/Bull Asymmetry), arXiv:2608.03616 (Liquidation Cascades & OI Clearing), arXiv:0902.4159 (Order-Book Liquidity & Impact), arXiv:2602.00776 (Flash Crash Microstructure), arXiv:2208.01445 (Cross-Asset Correlation Dynamics), arXiv:2506.08573 (Perpetual Funding Mechanics), arXiv:2504.15790 (Pump & Dump Accumulation Separation), arXiv:2308.07041 (Stablecoin Collateral Death Spirals).

---

## 1. Yönetici Özeti ve Epistemik Çerçeve

Tekil tarihsel tarihler üzerinden geriye dönük testler yapmak (örneğin "05 Şubat 2026 BTC Kırılımı"), anlatısal cımbızlamaya ve hindsight aşırı uyumuna (overfitting) açıktır. **ALLEGORY-001**, V8 denetim motorunu **4 Süper-Sınıf** altında toplanan **12 Kanonik Piyasa Arketipi (A01–A12)** üzerinden çoklu epizotlu sistematik bir kayıt sistemine genişletir.

### Temel Değişmezler
1. **Sıfır Hindsight Sızıntısı:** Hiçbir arketip "beklenen işlem" veya sabit kural tanımlamaz. Her epizot, ex-ante aday kabullerini ex-post kısıtlanmamış / sermaye-kısıtlı fırsat sınırına karşı ölçer.
2. **Zorunlu Anti-Alegori (Negatif Kontrol) Kalibrasyonu:** Her yönsel veya zorunlu akış arketipi, asimetrik uyumu önlemek için birebir eşleşen bir negatif kontrol ile test edilir (ör. *Sıkışma $\to$ Sahte Kırılım*, *Kapitülasyon $\to$ Kaskat Devamı*).
3. **Anayasa Kural 12 (`NO_ECONOMIC_CLAIM`):** Tüm karneler ve değerlendirmeler `MODEL_DERIVED_AUDIT` otoritesinde ve `NO_ECONOMIC_CLAIM` etiketiyle yayınlanır.

---

## 2. 12 Kanonik Arketip ve Süper-Sınıflar

### I. Yönsel Fırsat (Directional Opportunity)
* **A01: Sıkışma $\to$ Genişleme (Compression $\to$ Expansion 🚀):**
  * *Audit Sorusu:* Motor genişleme öncesi volatilite sıkışmasını algılayıp sınırlı kayma (slippage) ile katılabildi mi?
  * *Negatif Kontrol:* Sıkışma $\to$ Ölü Aralık / Sahte Genişleme.
* **A02: Yavaş Tırmanış Trendi (Slow Grind Trend 🐢):**
  * *Audit Sorusu:* Motor erken 'aşırı alım' çıkışı yapmadan trend kalıcılığını koruyabildi mi?
  * *Temel Metrikler:* `trend_start`, `first_useful_signal`, `first_accepted_campaign`, `total_trend_mfe`, `realized_capture`, `premature_exits`, `re_entry_count`.
  * *Negatif Kontrol:* Yavaş Tırmanış $\to$ Ani Ortalamaya Dönüş Çöküşü.
* **A03: Başarısız Kırılım / Tuzak (Failed Breakout 🪤):**
  * *Audit Sorusu:* Motor sahte kırılım ile yapısal kabulü (acceptance) ayırt edebildi mi?
  * *Temel Metrikler:* `close_acceptance`, `volume_participation`, `derivatives_confirmation`, `retest_survival`, `structural_invalidation`.
  * *Negatif Kontrol:* Gerçek Kırılım $\to$ Yapısal Kabul.
* **A04: Kapitülasyon $\to$ V-Dönüş (Capitulation $\to$ V-Reversal 🔄):**
  * *Audit Sorusu:* Motor short pozisyonu zirve düşüşte terk edip ters yön tanıma gecikmesini yönetebildi mi?
  * *Temel Metrikler:* `short_capture`, `short_exit_latency`, `opposite_campaign_recognition_latency`.
  * *Negatif Kontrol:* Kapitülasyon $\to$ Kaskat Devamı.
* **A05: Parabolik Tükeniş (Blow-Off / Exhaustion 🎈):**
  * *Audit Sorusu:* Motor parabolik tükenişi kazanç budama kırpması olmadan tespit edebildi mi?
  * *Negatif Kontrol:* Momentum İvmelenmesi $\to$ Uzatılmış Devam.

### II. Zorunlu Akış Stresi (Forced-Flow Stress)
* **A06: Sıkıştırma vs Organik Trend (Squeeze vs Organic 🧨):**
  * *Audit Sorusu:* Motor zorunlu açık pozisyon (OI) tasfiyesi ile organik spot genişlemesini ayırt edebildi mi?
  * *Negatif Kontrol:* Organik Spot Genişlemesi $\to$ Sürdürülebilir OI Büyümesi.
* **A07: Likidasyon Kaskatı / Flash Crash (☢️):**
  * *Audit Sorusu:* İcra riski, limit dolumları ve mark price emir defteri kurumasından sağ çıkabildi mi?
  * *Temel Metrikler:* `warning_lead_time`, `crash_capture`, `max_heat`, `liquidation_proximity`, `slippage_regret`, `reversal_latency`.
  * *Negatif Kontrol:* Standart Volatilite Çubuk Fitili.

### III. Düşük Fırsat / Çekişmeli (Low-Opportunity / Adversarial)
* **A08: Testere Piyasası Cehennemi (Chop / Whipsaw Hell 🪚):**
  * *Audit Sorusu:* Motor yönsüz gürültüde NO_TRADE üstünlüğüne uyarak sermayeyi koruyabildi mi?
  * *Temel Metrikler:* `no_trade_superiority`, `whipsaw_avoidance_rate`, `fee_drag_preservation`.
  * *Negatif Kontrol:* Mikro Aralık Temiz Genişleme.
* **A09: Ortalamaya Dönüş Aralığı (Mean-Reversion Range 🧲):**
  * *Audit Sorusu:* Motor aralık sınırlarını trend başlangıcı sanmadan değerlendirebildi mi?
  * *Negatif Kontrol:* Aralık Sınırı Gerçek Yapısal Kırılımı.
* **A12: Manipülasyon / Yapısal Çöküş (Manipulation / Depeg 🎭):**
  * *Audit Sorusu:* Bütünlük filtreleri organik olmayan hacmi veya teminat ölüm spirallerini tespit etti mi?
  * *Negatif Kontrol:* Organik Yüksek Hacimli Fiyat Keşfi.

### IV. Portföy / Türevler (Portfolio / Derivatives)
* **A10: Varlıklar Arası Rotasyon / Bulaşma (Rotation / Contagion 🌐):**
  * *Audit Sorusu:* Portföy tahsisi korele varlıklarda sistemik beta riskini üç kez üst üste almayı engelledi mi?
  * *Negatif Kontrol:* Bağımsız Varlık Özgül Hareketleri.
* **A11: Fonlama / Basis Bozulması (Funding Dislocation ⚖️):**
  * *Audit Sorusu:* Motor türev piyasa yığılma stresini spot fiyata yansımadan önce gördü mü?
  * *Negatif Kontrol:* Yüksek Fonlamalı Sürdürülebilir Fiyat Trendi.

---

## 3. Karne ve Çalıştırma

Motor `v8-core allegory-audit` üzerinden çalıştırılır:

```bash
cargo run --manifest-path v8-core/Cargo.toml --bin v8-core -- allegory-audit \
  --tape research/tape/btcusdt-1h-12m/tape.jsonl \
  --out .audit/rust_audit_current/allegory_scorecard.json
```
