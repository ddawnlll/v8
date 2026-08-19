# V8 Değerlendirme Kanıt Sistemi ve Bilimsel Denetim Spesifikasyonu (v8.eval.v1)

**Durum:** DESIGN_INFERENCE / LOCKED_INVARIANT.  
**Kapsam:** Eski tekil rapor (HTML/text) üretim mantığını; otonom araştırma ajanlarının (Scout -> Investigator -> Decision döngüsü) üzerinde hipotez kurup doğrulayabileceği, sorgulanabilir, değişmez (immutable) ve içerik adresli bir bilimsel kanıt paketi (Evidence Bundle) ile değiştirir.

---

## 1. Paradigma Dönüşümü: Rapor Üretecinden Bilimsel Kanıt Altyapısına

Geleneksel kantitatif backtest sistemleri ve önceki V8 sürümleri, değerlendirme adımını yalnızca bir **rapor oluşturma aracı** olarak görüyordu (P&L eğrileri, Sharpe oranları, özet kazanma oranları içeren statik HTML/metin çıktısı).

**v8.eval.v1** ile değerlendirme sistemi kökten yeniden tanımlanmıştır:
> **Bir değerlendirme koşusu yalnızca bir rapor üretmez. Otonom ajanların üzerinde araştırma yapabileceği, sorgulayabileceği, yanlışlanabilir hipotezler kurup bütün korpus üzerinde doğrulayabileceği / çürütebileceği değişmez (immutable) ve içerik adresli bir Kanıt Paketi (Evidence Bundle) üretir.**

```
                                 ESKİ YAKLAŞIM (Yalnızca Çıktı)
                      ┌──────────────────────────────────────────┐
                      │  Input Tape ──► Engine ──► Final P&L/HTML│
                      └──────────────────────────────────────────┘

                                V8.2+ BİLİMSEL PARADİGMA
 ┌──────────────────────────────────────────────────────────────────────────────────────────┐
 │                                                                                          │
 │   Piyasa Verisi (PIT) ──► S0-S7 Pipeline ──► Değişmez Kanıt Paketi (v8.eval.v1)         │
 │                                                  │                                       │
 │                          ┌───────────────────────┴───────────────────────┐               │
 │                          ▼                                               ▼               │
 │                 Yapılandırılmış Kanıt Deposu                 Deterministik Şema Önbelleği │
 │              (Parquet İzleri, DAG, Defterler)               (Dağılımlar, Boşluklar, İstat)│
 │                          │                                               │               │
 │                          └───────────────────────┬───────────────────────┘               │
 │                                                  ▼                                       │
 │                                       Otonom Ajan Sürüsü                                 │
 │                         ┌─────────────────────────────────────────┐                      │
 │                         │  • Triage Ajanı (Anomali Tespiti)       │                      │
 │                         │  • Scout Ajanları (Hipotez Üretimi)     │                      │
 │                         │  • Investigator Ajanları (Korpus Testi) │                      │
 │                         │  • Decision Ajanı (Sicil Yönetimi)      │                      │
 │                         └────────────────────┬────────────────────┘                      │
 │                                              ▼                                           │
 │                                   Doğrulanmış Bulgu Grafı                                │
 │                                 (EPİSTEMOLOJİK / İSTATİSTİKSEL)                          │
 │                                              │                                           │
 │                          ┌───────────────────┴───────────────────┐                       │
 │                          ▼                                       ▼                       │
 │                   İnsan HTML Raporu (A-W)                 Makine Kanıt API'si            │
 │                    (Yönetici Görüntüsü)                  (JSON-RPC / Substrat)           │
 └──────────────────────────────────────────────────────────────────────────────────────────┘
```

Buradaki HTML raporu, insan operatörler için yalnızca bir **okuma arayüzüdür (viewport)**. Nihai otorite ise tamamen **makine tarafından okunabilir, şema doğrulamalı, yapılandırılmış Parquet/JSONL kanıt paketindedir**. Ajanlar asla HTML parse etmeye çalışmaz.

---

## 2. Literatür Dayanağı ve Metodolojik Temeller

2025–2026 ajan değerlendirme ve kantitatif finans literatürü, `v8.eval.v1` mimarisini doğrudan desteklemektedir:

```
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│                                LİTERATÜR EŞLEŞTİRME MATRİSİ                                  │
├─────────────────────────┬──────────────────────────────────┬─────────────────────────────────┤
│ Kaynak / Makale         │ Temel İlke                       │ V8.eval.v1 Uygulaması           │
├─────────────────────────┼──────────────────────────────────┼─────────────────────────────────┤
│ Harness-Bench           │ Sonuç tek başına yetersizdir;    │ Ham yürütme izleri (traces),    │
│ (arXiv:2605.27922)      │ nihai çıktılar + yürütme izleri  │ doğrulayıcı çıktıları ve durum  │
│                         │ + kullanım istatistikleri şart.  │ DAG'ı P&L ile birlikte saklanır.│
├─────────────────────────┼──────────────────────────────────┼─────────────────────────────────┤
│ ClawTrack               │ Outcome Grading ile Process      │ Süreç telemetrisi: Hedef uyumu, │
│ (arXiv:2607.28037)      │ Grading ayrılmalıdır; trajectory,│ filtre verimliliği, dedup/veto  │
│                         │ denetim günlükleri, snapshotlar. │ korunum denkliği izlenir.       │
├─────────────────────────┼──────────────────────────────────┼─────────────────────────────────┤
│ A²E Protokolü           │ Görev temsili, ortam ve gerçek   │ Tiplenmiş yürütme kayıtları:    │
│ (arXiv:2608.07346)      │ yürütme kaydını ayıran protokol. │ signals -> candidates ->        │
│                         │                                  │ transitions -> trades.          │
├─────────────────────────┼──────────────────────────────────┼─────────────────────────────────┤
│ On Randomness in Evals  │ Tek koşu varyansı yanıltıcıdır;  │ pass@1, iyimser tekrar ve       │
│ (arXiv:2602.07150)      │ tutarlılık sınırları (bounds)    │ kötümser tutarlılık sınırları   │
│                         │ birlikte raporlanmalıdır.        │ pertürbasyon altında ölçülür.   │
├─────────────────────────┼──────────────────────────────────┼─────────────────────────────────┤
│ Princeton Ajan          │ 4 Güvenilirlik Sütunu:           │ Güvenilirlik Zarfı: Outcome,    │
│ Güvenilirliği           │ Consistency, Robustness,         │ trajectory ve resource tutar-   │
│ (arXiv:2602.16666)      │ Predictability, Safety.          │ lılığı çevre şartlarında test.  │
├─────────────────────────┼──────────────────────────────────┼─────────────────────────────────┤
│ Insights Generator      │ Büyük iz korpusu doğrudan LLM'e  │ İki kademeli ajan araştırması:  │
│ (arXiv:2605.21347)      │ verilmez; Şema Önbelleği +       │ Scout hipotez üretir,           │
│                         │ Scout / Investigator ayrımı.     │ Investigator korpusta kanıtlar. │
├─────────────────────────┼──────────────────────────────────┼─────────────────────────────────┤
│ AlgoXpert Çerçevesi     │ Parametre uçurumları (cliffs) &  │ Sağlamlık Yüzeyleri: maliyet,   │
│ (arXiv:2603.09219)      │ IS-WFA-OOS bozulma metrikleri.   │ stop, hedef ve ortak kırılganlık│
├─────────────────────────┼──────────────────────────────────┼─────────────────────────────────┤
│ SysTradeBench           │ Fail-closed geçerlilik kapıları; │ Geçerlilik Kapıları: Sızıntı,   │
│ (arXiv:2604.04812)      │ donmuş strateji sağlama toplamı. │ Muhasebe, SIMD/İş Parçacığı.    │
├─────────────────────────┼──────────────────────────────────┼─────────────────────────────────┤
│ AgentRx                 │ Yürütme yörüngesinden hata adımı │ Biçimsel Hata Ontolojisi:       │
│ (arXiv:2602.02475)      │ ve sınıfı çıkarma.               │ 9 ana kategorili taksonomi.     │
├─────────────────────────┼──────────────────────────────────┼─────────────────────────────────┤
│ Bailey vd. (PBO/DSR)    │ Çoklu test enflasyonu, deflated  │ Araştırma Defteri ve kümülatif  │
│ & White Reality Check   │ Sharpe ve aşırı uyum olasılığı.  │ deneme cezası hesabı.           │
└─────────────────────────┴──────────────────────────────────┴─────────────────────────────────┘
```

---

## 3. Tekil Çıktı Yerine Güvenilirlik Zarfı (Reliability Envelope)

Deterministik bir motorda dahi çalışma şartları (execution circumstances) üretim ortamlarında değişkenlik gösterebilir. V8, tekil bir metrik yerine çok boyutlu bir **Güvenilirlik Zarfı** tanımlar:

$$\text{Güvenilirlik Zarfı} = \mathcal{E}(\text{İş Parçacıkları}, \text{SIMD}, \text{Önbellek}, \text{İşlemci}, \text{Girdi Pertürbasyonları}, \text{Maliyet Şokları})$$

### Temel Değişmez: Yürütme Şartları Altında Semantik Değişmezlik
$$\forall c_1, c_2 \in \text{YürütmeŞartları}, \quad \text{Semantik}(S, c_1) \equiv \text{Semantik}(S, c_2) \implies \text{Ekonomi}(S, c_1) \equiv \text{Ekonomi}(S, c_2)$$

1. **İş Parçacığı Paritesi ($T \in \{1, 2, 4, 8\}$):** Paralellik seviyesi değiştikçe aday dağıtımı veya durum toplama işlemi bit düzeyinde sapıyor mu?
2. **SIMD / Skaler Paritesi:** AVX2/AVX-512 vektör kod yolları ile skaler yedek yollar birebir aynı kararları üretiyor mu?
3. **Soğuk / Sıcak Önbellek:** Önbelleğin önceden ısıtılmış olması geçmişe bakış indekslerini veya kayan nokta yuvarlamalarını etkiliyor mu?
4. **Girdi Pertürbasyonları:** 1 barlık zaman damgası kayması, mikro-kayma veya eksik fonlama oranları altında sistemin stabilitesi.
5. **Parametre Komşuluk Kararlılığı:** Gösterge eşiklerindeki $\pm 2\%$ değişim keskin bir performans uçurumuna ($\Delta \text{Sharpe} > 50\%$) yol açıyor mu?

---

## 4. Değişmez Kanıt Paketi Dizin Yapısı (`v8.eval.v1`)

Her değerlendirme koşusu `evaluation/<RUN_ID>/` altında tamamen bağımsız bir kanıt paketi oluşturur:

```
evaluation/
└── RUN_ID/
    ├── manifest.json                  # Giriş kapısı ve kriptografik makbuz
    ├── executive.json                 # Makine tarafından okunabilir özet ve kritik hükümler
    ├── report.html                    # İnsan operatör sunum arayüzü (A–W Bölümleri)
    │
    ├── provenance/                    # Kriptografik köken ve yeniden üretim DAG'ı
    │   ├── environment.json           # Host CPU, işletim sistemi, Rust derleyici ve bayraklar
    │   ├── inputs.json                # Veri kaynakları, sembol listesi, aralık, bar sayıları
    │   ├── hashes.json                # İkili dosya, bant, konfigürasyon ve eser sağlama toplamları
    │   ├── config.json                # Değerlendirici konfigürasyon anlık görüntüsü
    │   └── artifact_dag.json          # Üretilen tüm eserlerin bağımlılık grafı
    │
    ├── data/                          # Veri adli tıp katmanı
    │   ├── bars.parquet               # PIT olarak içeri alınmış OHLCV ve fonlama satırları
    │   ├── data_quality.parquet       # Bar bazında kalite bayrakları, boşluk göstergeleri
    │   └── feature_census.parquet     # Öznitelik dağılımları, boşluk oranları, çeyreklikler
    │
    ├── execution/                     # Tam işlem hattı olay telemetrisi
    │   ├── evaluations.parquet        # S0: Bar seviyesindeki tüm uzman değerlendirme denemeleri
    │   ├── signals.parquet            # S1: Üretilen ham davranışsal sinyaller
    │   ├── candidates.parquet         # S2: Oluşturulan aday epizotlar (candidates)
    │   ├── transitions.parquet        # S3-S4: Durum geçişleri (tekilleştirme, bekleme süreleri)
    │   ├── vetoes.parquet             # S5: Risk, kapasite ve portföy veto olayları
    │   └── trades.parquet             # S6-S7: Kabul edilen emirler, dolumlar ve işlem günlükleri
    │
    ├── economics/                     # Finansal performans adli tıp katmanı
    │   ├── portfolio.parquet          # Kümülatif portföy metrikleri ve düşüş (drawdown) serisi
    │   ├── experts.parquet            # Uzman bazında getiri ayrıştırması ve atıf
    │   ├── costs.parquet              # Spread, komisyon, kayma ve fonlama maliyet yükü
    │   └── equity_curve.parquet       # Adım adım yüksek çözünürlüklü bakiye eğrisi
    │
    ├── paths/                         # İşlem içi yol ve yörünge adli tıbbı
    │   ├── mfe_mae.parquet            # Maksimum Lehte / Aleyhte Sapma (MFE/MAE) kayıtları
    │   ├── markouts.parquet           # Tetikleme sonrası fiyat yörüngeleri (t+1..t+k)
    │   ├── exits.parquet              # Çıkış bariyeri sınıflandırması ve temas sıraları
    │   └── intrabar_ambiguity.parquet # Bar içi Yüksek/Düşük temas belirsizliği ve cezaları
    │
    ├── slices/                        # Dilim ve rejim bazlı koşullu performans
    │   ├── regime.parquet             # Volatilite ve trend rejim dilimleri
    │   ├── direction.parquet          # Uzun (Long) vs Kısa (Short) asimetrisi
    │   ├── time_of_day.parquet        # Seans, gün içi saat ve haftanın günü performansı
    │   ├── volatility.parquet         # ATR ve gerçekleşen volatilite çeyreklikleri
    │   └── liquidity.parquet          # Hacim ve emir akışı dengesizliği (OFI) dilimleri
    │
    ├── robustness/                    # Karşıolgusal yüzeyler ve kararlılık
    │   ├── cost_surface.parquet       # Sürtünme maliyeti vs Net Beklenti ızgarası
    │   ├── exit_surface.parquet       # SL/TP/Zaman aşımı geometri pertürbasyon ızgarası
    │   ├── parameter_surface.parquet  # Parametre komşuluğu duyarlılık ızgarası
    │   ├── perturbations.parquet      # Enjekte edilmiş stres ve veri bozulma testleri
    │   └── degradation.parquet        # IS -> WFA -> OOS -> Holdout bozulma oranları
    │
    ├── statistics/                    # Titiz hipotez testi eserleri
    │   ├── bootstrap.json             # Beklenti ve Sharpe için durağan bootstrap GA'ları
    │   ├── permutations.json          # İşlem sırası ve getiri permütasyon dağılımları
    │   ├── nulls.json                 # 10 ailelik sıfır hipotezi (null) karşılaştırmaları
    │   ├── reality_check.json         # White Reality Check ve Hansen SPA testleri
    │   ├── multiple_testing.json      # Yaşam boyu araştırma denemeleri ve DSR düzeltmeleri
    │   └── backtest_overfit.json      # Bailey Backtest Aşırı Uyum Olasılığı (PBO / CSCV)
    │
    ├── correctness/                   # Rust motoru değişmezlik ve parite makbuzları
    │   ├── invariants.json            # Korunum ve yaşam döngüsü değişmezlik kontrolleri
    │   ├── replay_digest.json         # Deterministik yeniden oynatma sağlama doğrulaması
    │   ├── thread_parity.json         # 1 vs 2 vs 4 vs 8 iş parçacığı parite sonuçları
    │   ├── simd_parity.json           # AVX2/AVX-512 vs Skaler bit düzeyinde parite
    │   └── implementation_parity.json # Minimal referans orakıl karşılaştırma raporu
    │
    └── analysis/                      # Ajan akıl yürütme ve bulgu grafı
        ├── schema_cache.json          # LLM sorguları için önceden hesaplanmış kolon istatistikleri
        ├── hypotheses.jsonl           # Ön kayıtlı ve Scout tarafından üretilen hipotezler
        ├── findings.jsonl             # Doğrulanmış, Çürütülmüş veya Belirsiz bulgular
        ├── anomalies.jsonl            # Otomatik aykırı değer ve teşhis uyarıları
        └── recommendations.jsonl      # Bir sonraki ön kayıtlı meydan okuyucu önerileri
```

---

## 5. `manifest.json` Giriş Kapısı ve Muhasebe Korunum Değişmezi

Ajanlar büyük Parquet dosyalarını taramadan önce ~10 KB boyutundaki `manifest.json` dosyasını inceler:

```json
{
  "schema": "v8.eval.v1",
  "run_id": "RUN-20260819-BTC-001",
  "timestamp_utc": "2026-08-19T03:00:00Z",
  "git_commit": "a1f89c0d2e4b6789123456789abcdef01234567",
  "binary_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "tape_hash": "7a3560f7690623a9d4fa1534da6cc0a7d9796e625a6eb8ee99b3b0d2de0bc5ef",
  "config_hash": "2c26b46b68ffc68ff99b453c1d30413413422d706483bfa0f98a5e886266e7ae",
  "dataset": {
    "instrument": "BTCUSDT",
    "timeframe": "1h",
    "raw_bars": 9948,
    "warmup_bars": 1188,
    "eligible_bars": 8760,
    "start_utc": "2025-07-01T00:00:00Z",
    "end_utc": "2026-07-01T00:00:00Z"
  },
  "funnel_conservation": {
    "evaluations": 245280,
    "setups_triggered": 42647,
    "deduplicated": 14766,
    "vetoed_risk_capacity": 27879,
    "admitted_trades": 2,
    "invariant_holds": true,
    "accounting_equation": "42647 == 14766 (dedup) + 27879 (veto) + 2 (admitted)"
  },
  "validity_gates": {
    "temporal_leakage": "PASS",
    "accounting_conservation": "PASS",
    "determinism_replay": "PASS",
    "simd_scalar_parity": "PASS",
    "thread_parity": "PASS",
    "overall_validity": "VALID"
  },
  "economic_verdict": "INSUFFICIENT_EVIDENCE",
  "summary_metrics": {
    "gross_expectancy_R": -0.012,
    "net_expectancy_R": -0.048,
    "total_trades": 2,
    "sharpe_ratio": -0.18,
    "max_drawdown_R": 1.96
  },
  "critical_findings": [
    "F-0012: Extreme veto rate (99.99%) driven by unparameterized EXISTING_EXPOSURE_CONFLICT.",
    "F-0014: Expert identity collapse in admission veto logs."
  ],
  "artifacts": {
    "root_dir": "evaluation/RUN-20260819-BTC-001",
    "total_size_bytes": 14820942
  }
}
```

### Muhasebe Korunum Denklemi
$$\text{Kurulumlar (Setups)} = \text{Tekilleştirilen (Dedup)} + \text{Veto Edilen (Risk/Kapasite)} + \text{Kabul Edilen (Admitted)}$$
Herhangi bir uyumsuzlukta sistem derhal **FAIL-CLOSED** vererek koşuyu geçersiz ilan eder.

---

## 6. Veri Adli Tıp Katmanı: Zamansal Bütünlük ve Kalite DAG'ı

1. **Zamansal Bütünlük (Temporal Integrity):**
   - Zaman damgası kesin monoton artış denetimi: $\forall t_i, t_i < t_{i+1}$.
   - Bilgi erişim zamanı (availability time) doğrulaması: $t_{\text{karar}} \ge t_{\text{erişim}} > t_{\text{olay}}$.
   - Borsa takvimine göre eksik bar ve tatil denetimleri.
   - Geliştirme ve OOS bölümleri arasında kesin arındırma (purge) ve bekleme (embargo) aralıkları.

2. **Öznitelik Nüfus Sayımı (Feature Census):**
   - Her öznitelik için: $N$, Boşluk $\%$, NaN sayısı, Sonsuz (Inf) değerler, Sıfır varyans uyarısı, Çeyreklikler ($p_1, p_{25}, p_{50}, p_{75}, p_{99}$), Min/Max, Süreksizlik sıçramaları ve Bayat tekrarlayan dizi tespiti.

3. **Kaynak Kökeni DAG'ı (Provenance):**
   - Her bir veri sütunu, onu üreten Rust fonksiyonunun kriptografik sağlama toplamına ve ham veri kaynağına bağlanır.

---

## 7. Huni Adli Tıbbı: Uzman Bazında Dönüşüm ve Kayıp Beklenti

Her uzmanın sinyal hunisi adım adım denetlenir:

$$\text{Gözlenen Barlar} \xrightarrow{E} \text{Uygun Değerlendirmeler} \xrightarrow{S} \text{Kurulum} \xrightarrow{D} \text{Dedup} \xrightarrow{R} \text{Risk/Kapasite} \xrightarrow{A} \text{Kabul} \xrightarrow{T} \text{İşlem} \xrightarrow{X} \text{Sonuç}$$

Her aşama için:
- **Sayı ve Dönüşüm Oranı:** Her adımı geçen sinyal yüzdesi.
- **Gerekçe Kodları:** Reddedilme nedenleri (`COOLDOWN_ACTIVE`, `OPPOSITE_EXPOSURE_ACTIVE`, `HEAT_CAP_EXCEEDED` vb.).
- **Kayıp Beklenti Tahmini ($\Delta \mathbb{E}[R]$):** Filtrelenen sinyallerin karşıolgusal getirisi ile kabul edilenlerin karşılaştırılması (risk filtresinin zararlı işlemleri mi elediği yoksa karlı fırsatları mı kaçırdığı tespiti).
- **İz Kimlikleri (Trace IDs):** Ajanların doğrudan ilgili adaya inebilmesini sağlayan kimlik dizileri.

---

## 8. Ekonomik Adli Tıp Katmanı

Ekonomik çıktı üç bağımsız bileşene ayrıştırılır: **Ham Kenar (Gross Edge)**, **Sürtünme Kaybı (Friction Drag)** ve **Gerçekleşen Net Kenar (Net Realized Edge)**:

$$\text{Net } R = \text{Brüt } R - (\text{Komisyon } R + \text{Kayma } R + \text{Fonlama } R + \text{Gecikme Cezası } R)$$

```
┌───────────────────────────┬───────────────────────────┬───────────────────────────┐
│ Getiriler ve Beklenti     │ İşlem ve Risk İstatistiği │ Yürütme Ekonomisi         │
├───────────────────────────┼───────────────────────────┼───────────────────────────┤
│ • Brüt Beklenti ($R$)     │ • Örneklem Sayısı ($N$)   │ • Toplam Komisyon ($R$)   │
│ • Net Beklenti ($R$)      │ • Kazanma Oranı ($\%$)    │ • Kayma (Slippage) ($R$)  │
│ • Medyan $R$ / İşlem      │ • Kar Faktörü ($PF$)      │ • Net Fonlama Yükü ($R$)  │
│ • Yıllıklandırılmış Getiri│ • Kazanç/Kayıp Oranı      │ • Yıllık Devir Hızı       │
│ • Sharpe Oranı (Yıllık)   │ • Maksimum Düşüş ($R$)    │ • Brüt -> Net Erime Oranı │
│ • Sortino Oranı           │ • Ortalama Düşüş ($R$)    │ • Başa Baş Maliyet Limiti │
│ • Calmar Oranı            │ • CVaR / Beklenen Kayıp   │ • Kapasite Tahmini ($)    │
└───────────────────────────┴───────────────────────────┴───────────────────────────┘
```

---

## 9. Karşıolgusal Sağlamlık Yüzeyleri

Tekil parametre noktaları yerine 4 temel boyutta sürekli tepki yüzeyleri incelenir:

1. **Maliyet Yüzeyi:** $\mathbb{E}[R](c)$ ($c \in [0, 20\text{ bps}]$). Başa baş sıfır noktası belirlenir.
2. **Stop Yüzeyi:** $\mathbb{E}[R](\text{Stop\_R})$ ($\text{Stop\_R} \in [0.2R, 3.0R]$). Stop-loss darlığı duyarlılığı.
3. **Hedef Yüzeyi:** $\mathbb{E}[R](\text{Target\_R})$ ($\text{Target\_R} \in [0.5R, 10.0R]$). Kar al kırpılma etkisi.
4. **Vade (Zaman Aşımı) Yüzeyi:** $\mathbb{E}[R](\text{Expiry\_Bars})$ ($\text{Expiry} \in [1, 100\text{ bar}]$).
5. **Ortak Kırılganlık Metrikleri:**
   - **Plato Genişliği:** $\mathbb{E}[R] > 0$ olan parametre yarıçapı.
   - **Performans Uçurumu (AlgoXpert):** Komşu parametreler arasındaki maksimum türev $\max |\nabla \text{Sharpe}|$.
   - **Yerel Kırılganlık İndeksi:** $\pm 5\%$ parametre pertürbasyonu altında performans varyansı.

---

## 10. Yol Adli Tıbbı ve Yörünge Sınıflandırması

Her işlem yüksek çözünürlüklü bar içi yol metrikleri üretir:
- **Stop Çok Dar:** İşlem SL oldu fakat orijinal vade içinde $+1.0R$ lehte seviyeye ulaştı.
- **Hedef Çok Dar:** İşlem TP oldu fakat hemen ardından $> +2.0R$ güçlü hareket devam etti.
- **Ölü İşlem (Dead Trade):** Ne SL ne TP yaklaşıldı ($|MAE| < 0.2R, |MFE| < 0.2R$); sürenin $\%80$'inde sıfır bilgi ile sermaye bağlandı.
- **Kötü Giriş:** Giriş anından itibaren anında MAE oluştu ($MFE < 0.05R$).
- **İyi Sinyal / Kötü Yürütme:** $t+k$ anındaki markout pozitif ancak spread/kayma nedeniyle gerçekleşen işlem negatif.
- **Kötü Sinyal / Şanslı Çıkış:** Yörünge ağırlıklı olarak aleyhte ancak anlık bir iğne ucu ile karlı kapandı.

---

## 11. 10 Ailelik Sıfır Hipotezi (Null Model) Test Paketi

1. **Rastgele Giriş (Uniform):** Zamanlama bilgisini sınar.
2. **Rastgele Yön (Long/Short):** Giriş zamanını korur, yönü rastgele belirler.
3. **Rastgele Zaman Damgaları (Poisson):** İşlem sayısı ve süresini korur, zamanı dağıtır.
4. **Her Zaman Long:** Piyasa yukarı yönlü sürüklenme baz çizgisini ölçer.
5. **Her Zaman Short:** Piyasa aşağı yönlü sürüklenme baz çizgisini ölçer.
6. **Ters Sinyal ($S \to -S$):** Yönsel işaret doğruluğunu test eder.
7. **Karıştırılmış Uzman Etiketleri:** Uzman kimliğinin önemini sınar.
8. **Frekansı Eşlenmiş Rastgele Strateji:** İşlem sıklık dağılımını korur.
9. **Süresi Eşlenmiş Rastgele Strateji:** İşlem elde tutma süresi dağılımını korur.
10. **Rejimi Eşlenmiş Rastgele Strateji:** Rastgele işlemleri yalnızca aynı volatilite rejiminde açar.

---

## 12. Çoklu Test Muhasebesi ve Araştırma Borcu Defteri

Kümülatif arama uzayında yanlış pozitif olasılığı hızla 1'e yaklaşır:

$$P(\text{Yanlış Pozitif}) = 1 - (1 - \alpha)^K \xrightarrow[K \to \infty]{} 1.0$$

1. **Deflated Sharpe Ratio (DSR):** Sharpe oranını normallikten sapma, örneklem uzunluğu ve $K$ deneme sayısına göre iskonto eder.
2. **White Reality Check & Hansen SPA:** Seçilen en iyi stratejinin tüm aile arama uzayı hesaba katıldıktan sonra anlamlı olup olmadığını test eder.
3. **Backtest Aşırı Uyum Olasılığı (PBO / CSCV):** Kombinatoryal çapraz doğrulama ile aşırı uyum olasılığını hesaplar.
4. **Küresel Araştırma Defteri:** Proje yaşamı boyunca test edilen her hipotez `research_ledger.jsonl` defterine işlenir; ceza tek koşudan değil kümülatif tarihten hesaplanır.

---

## 13. Araştırma Defteri ve Hipotez Kaydı (`hypotheses.jsonl`)

```json
{
  "hypothesis_id": "H-0192",
  "parent_hypothesis": "H-0145",
  "created_by": "agent:scout-volatility",
  "created_at_run": "RUN-20260819-BTC-001",
  "status": "SUPPORTED",
  "claim": "bollinger_breakout LONG, YUKSEK_VOLATILITE rejiminde erken stop kaybi yasiyor.",
  "preregistered_test": {
    "cohort_filter": "expert == 'bollinger_breakout' and direction == 'LONG' and regime == 'HIGH_VOL'",
    "counterfactual_variant": "stop_multiplier = 1.5",
    "primary_metric": "net_expectancy_R",
    "required_n": 100,
    "significance_threshold_p": 0.01
  },
  "evidence_for": [
    "Kohort N=342, baz net_R = -0.14R, karsi-olgusal net_R = +0.08R (bootstrap p=0.004).",
    "Stop olan islemlerin %38.4'u stop sonrasi +1.0R lehte fiyata ulasti."
  ],
  "evidence_against": [
    "Genis stop altinda Maksimum Dusus (MaxDD) 12.4R'den 16.8R'ye yukseliyor."
  ],
  "falsification_criterion": "Etki, el surulmemis Donmus OOS Fold 2 uzerinde p < 0.05 ile dogrulanmalidir.",
  "derived_challengers": ["EXP-V8-CHALLENGER-BB-042"]
}
```

---

## 14. Doğrulama Ayrımı: IS $\to$ WFA $\to$ Donmuş OOS $\to$ Holdout

Kronolojik 4 kademeli arındırılmış veri yapısı:

$$\text{Geliştirme (IS)} \longrightarrow \text{Walk-Forward (WFA Folds)} \longrightarrow \text{Donmuş OOS} \longrightarrow \text{Kilitli Holdout}$$

Her kademe geçişinde bozulma oranları ($\text{Degradation}$) hesaplanır.

---

## 15. Uygulama Riski vs İstatistiksel Geçerlilik (2B Matris)

İstatistiksel güç ile motor doğruluğu bağımsız eksenlerdir:

```
                            İSTATİSTİKSEL GEÇERLİLİK × MOTOR DOĞRULUĞU
 ┌──────────────────────────────────────┬──────────────────────────────────────────────────────────┐
 │                                      │                      MOTOR DOĞRULUĞU                     │
 │                                      ├────────────────────────────┬─────────────────────────────┤
 │                                      │ Motor Doğrulandı (PASS)    │ Motor Şüpheli (FAIL)        │
 ├────────────────┬─────────────────────┼────────────────────────────┼─────────────────────────────┤
 │ İSTATİSTİKSEL  │ Kenar Geçerli (PASS)│ ADAY TERFİ EDİLİR          │ ENGELLENDİ / KARANTİNA      │
 │ GEÇERLİLİK     │ Kenar Geçersiz(FAIL)│ REDDEDİLEN HİPOTEZ         │ YORUMLANAMAZ / BOZUK        │
 └────────────────┴─────────────────────┴────────────────────────────┴─────────────────────────────┘
```

V8, 20 kanonik senaryolu minimal referans orakıl ile Rust motorunu bağımsız olarak doğrular.

---

## 16. Pertürbasyon ve Stres Test Paketi

1. **Veri Pertürbasyonları:** 1 dakikalık zaman damgası kaymaları, eksik fonlama satırları, yapay spread genişlemeleri ($2\times..5\times$), rastgele eksik bar enjeksiyonu.
2. **Piyasa Stresi:** Volatilite şokları ($1.5\times$), likidite boşluğu ($10\times$ kayma çarpanı).
3. **Motor Pertürbasyonları:** Dinamik iş parçacığı değişimi, soğuk önbellek koşusu.

---

## 17. Otonom Ajan Güvenilirlik Profili

- **Bulgu Tutarlılığı:** Aynı kanıt üzerinde farklı Scout ajanları aynı hatayı buluyor mu?
- **Atıf Tutarlılığı:** Investigator ajanları aynı kök nedene ulaşıyor mu?
- **Öneri Tutarlılığı:** Tutarlı meydan okuyucu önerileri üretiliyor mu?
- **Kalibrasyon:** Ajan $\text{güven} = 0.90$ dediğinde bulguların $\%90$'ı OOS üzerinde doğrulanıyor mu?

---

## 18. Yapılandırılmış Bulgu Şeması (`findings.jsonl`)

Bulgular makine tarafından doğrulanabilir nesnelerdir (`F-08421`).

---

## 19. Hata Ontolojisi ve Taksonomi

9 temel kategori: `DATA`, `SIGNAL`, `ADMISSION`, `EXECUTION`, `EXIT`, `STATISTICS`, `ENGINE`, `PORTFOLIO`, `UNCLASSIFIED_NEW_FAILURE_CLASS`.

---

## 20. Koşular Arası Regresyon Analizi

Her koşu; önceki koşu, kilitli baz çizgi ve üretim hedefi ile otomatik olarak karşılaştırılır ($\Delta \text{Net Expectancy}$, $\Delta \text{MaxDD}$, semantik sapma kontrolü).

---

## 21. Toplamsal Performans Ayrıştırması

Performans artışları haksız nedensellik iddiaları olmadan toplamsal bileşenlerine ayrıştırılır:

$$\Delta \mathbb{E}[R]_{\text{toplam}} = \Delta \mathbb{E}[R]_{\text{çıkış}} + \Delta \mathbb{E}[R]_{\text{maliyet}} + \Delta \mathbb{E}[R]_{\text{yön}} + \Delta \mathbb{E}[R]_{\text{rejim}} + \epsilon_{\text{artık}}$$

---

## 22. Kesin Geçerlilik Kapıları vs Puanlar (Fail-Closed)

Veri sızıntısı, muhasebe korunum hatası, determinizm kaybı veya SIMD sapması durumunda koşu derhal **FAIL-CLOSED** olarak sonlandırılır; ortalama skor içinde eritilmez.

---

## 23. Semantik Sapma Kapısı

Kod yamaları 4 sınıfa ayrılır: `BUG_FIX`, `IMPLEMENTATION_OPTIMIZATION`, `SEMANTIC_STRATEGY_CHANGE`, `NEW_CHALLENGER`.

---

## 24. Çok Ajanlı İnceleme Mimarisi

Değerlendirme sonrası otomatik süreç:
`Rust Engine -> Evidence Bundle -> Schema Builder -> Triage Agent -> Scout Agents -> Hypothesis Pool -> Investigator Agents -> Finding Graph -> Report / API -> Decision Agent`.

---

## 25. Kademeli Hesaplama ve Önbellek Bütçesi

- **Tier 0 (Zorunlu, < 2 sn):** Değişmezler, muhasebe korunumu, temel ekonomi, MFE/MAE, bit düzeyinde fark.
- **Tier 1 (İçerik Adresli Önbellek, < 30 sn):** Bootstrap, permütasyonlar, 10 sıfır modeli, maliyet/çıkış yüzeyleri.
- **Tier 2 (Hipotez Odaklı, < 5 dk):** Karşıolgusal yeniden oynatma, parametre yüzeyleri, WFA, pertürbasyonlar.
- **Tier 3 (Yalnızca Terfi Kapısı):** Donmuş OOS açımı, PBO/DSR/SPA, bağımsız referans paritesi.

---

## 26. Kanonik İnsan Raporu Yapısı (A'dan W'ye Bölümler)

- **A — Çalışma Kimliği ve Köken:** Sağlama toplamları, git commit, ikili kimlik.
- **B — Geçerlilik Kapıları:** Tüm donanımsal ve veri kapılarının Geçti/Kaldı durumu.
- **C — Veri Bütünlüğü:** Zaman bütünlüğü, eksik bar, öznitelik sayımı.
- **D — Yürütme Korunumu:** Huni muhasebe korunum denklemleri.
- **E — Portföy Ekonomisi:** Net/Brüt getiri, Sharpe, Sortino, Calmar.
- **F — Uzman Puan Tablosu:** Tüm uzmanların karşılaştırmalı tablosu.
- **G — Uzman Derin Adli Tıbbı:** Uzman bazında dönüşüm ve kayıplar.
- **H — İşlem Yolu Analizi:** Bar içi MFE/MAE, bariyer temas sıraları.
- **I — Maliyet ve Yürütme Yüzeyi:** Komisyon, kayma ve fonlama duyarlılık eğrileri.
- **J — Çıkış Karşıolgusalları:** Alternatif SL, TP ve vade kuralları.
- **K — Rejim / Dilim Teşhisi:** Volatilite, Trend, Saat ve Likidite dilimleri.
- **L — İstatistiksel Kanıt:** Bootstrap güven aralıkları ve permütasyon testleri.
- **M — Çoklu Test ve Araştırma Borcu:** Yaşam boyu deneme sayacı, White Reality Check, DSR.
- **N — WFA / OOS Kararlılığı:** Kronolojik katlama tutarlılığı ve bozulma oranları.
- **O — Parametre Kırılganlığı:** Plato genişliği, uçurumlar ve kırılganlık indeksi.
- **P — Motor Doğruluğu:** İş parçacığı, SIMD ve referans orakıl kontrolleri.
- **Q — Stres ve Pertürbasyon:** Yapay piyasa ve veri stres sonuçları.
- **R — Koşular Arası Regresyon:** Önceki koşu ve baz çizgiye göre delta metrikleri.
- **S — Hata Atfı:** Ontolojik taksonomi eşleştirmesi ve kök neden.
- **T — Doğrulanmış Bulgular:** Investigator ajanları tarafından ispatlanmış sonuçlar.
- **U — Çürütülmüş Hipotezler:** Resmen yanlışlanmış iddialar.
- **V — Bilinmeyenler ve Epistemik Boşluklar:** Kararsız sonuçlar.
- **W — Önerilen Deneyler:** Bir sonraki ön kayıtlı meydan okuyucu spesifikasyonları.
