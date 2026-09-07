# D-160: V8.6 Faz-1 Yürütme-Kulvarı Beratı — Attic Tasfiyesi, Hükümler ve Göç Yetkisi

**Durum:** `PROVISIONAL_DECISION` (geri alınabilir; ekonomik yetki vermez).
**Tarih:** 2026-09-07. **Dal:** `exec/v86-autonomous` (PR #361).
**Yetki:** V8.6 Üretim Rekalibrasyonu Araştırma Monografı §18 (B Aşaması
arşivleme emri), §11 (değerlendirme yetkisi), Ek A (göç tasfiye tablosu);
issue'lar #344 (W1), #345 (W2), #346 (W3), #347 (W4).
**Öncüller:** D-149 (Kural 44 tam-metin çapası), D-153 (Benchmark Fabric),
D-156 (kanıt sertleştirme), D-159 (araştırma-geçerliği denetimi).

## 1. Bu karar neyi kapsar

V8.6 göç programının Faz-1'i, çalışma-zamanı davranışını DEĞİŞTİRMEDEN
depoyu uygulamaya hazır hale getirir:

1. Kanıtlanabilir ölü kodu `v8-core/attic/` altına arşivle (W1/W2/W3).
2. UNKNOWN hüküm satırlarını kanıtla kapat (W4).
3. Bayat dirty-911 çalışmasını, davranış değişikliği kaçırmadan tasfiye et.
4. D-153 doğrulama tablosunu değişmez kısıt olarak mühürle.
5. V8.6 uygulama iş kalemlerine (§6/§14/§15/§18) gereksinim izlenebilirliğiyle
   berat ver.

Kapsamdaki her hüküm `NO_ECONOMIC_CLAIM` olarak kalır. p-değeri, etki
büyüklüğü, tolerans, beklenen iyileşme veya güven değeri üretilmemiştir.

## 2. Attic tasfiyeleri (davranış-koruyan taşımalar)

| Kulvar | Taşındığı yer | İçerik | Makbuz |
|---|---|---|---|
| W1 (#344) | `v8-core/attic/kaizen-governance/` (net 9 dosya) | `correlation`, `derivatives`, `governance`, `mega`, `provenance`, `pyramiding`, `cost_surface`, `liquidity_floor`, `verification` | Sıfır-kullanıcı taraması; `cargo check` yeşil |
| W1 düzeltmesi | canlı ağaca iade | `kaizen/{controller,verdict}.rs` | §3 (anayasal kapı, sıfır-kullanıcı sezgiselinden üstündür) |
| W1 KEEP | canlı, OPEN_PIN kapandı | `campaign`, `chop_suppression`, `exit_trailing`, `quantization`, `research_debt` + kapanışı (`challenger`, `diagnosis`, `hypothesis`, `adaptive`, `robustness`, `validation`, `iteration`) | Canlı kullanıcılar: `usdm_sim.rs`, `main.rs`, `benchmark/kaizen_feed.rs`, `d153_benchmark_fabric_sabotage` |
| W2 (#345) | `v8-core/attic/evaluation/` (7 dosya) | `manifest`, `statistics`, `surfaces`, `paths`, `regression`, `html_report`, `deployment_case` + `EvaluationEngine` tasfiyesi | §4 demet kapısı |
| W2 karantina | canlı, etiketli | `friction`, `production_growth`, `scope` (büyümek için `needs:authority`; tek kullanıcı `tests/production_growth_contract.rs`) | 5/5 test yeşil |
| W3 (#346) | `v8-core/attic/w3-dead-quartet/` (4 dosya) | `checkpoint`, `world/learned`, `analysis/scorecard`, `opportunity/harness_t1_t12` | Dosya-başı kullanıcı taramaları; `cargo check` yeşil |
| W4 (#347) | taşıma yok | `differential.rs` KEEP (uyur); `system_proving/*` KEEP + karantina etiketi | `.audit/w4/VERDICT.md` R2(a–c) makbuzları |

Attic dizinleri DERLENMEZ (bu dizine `mod` bildirimi yok);
`tools/audit_doc_path_refs.py`, taşınan alıntıları `RETIRED` (git
tarihçesinde gerçek öncül) sayar ve geçer.

## 3. W1 düzeltmesi: anayasal kapı sezgisellerden üstündür

W1 sonrası `tools/audit_reachability.py` (D-132/Kural 35 icrası) BAŞARISIZ
oldu: `v8-core/src/kaizen/{controller,verdict}.rs` dosyalarını egemen
bileşen olarak şart koşuyor ("tüm ekonomik iddialar
ClaimValue/ClaimRegistry/Kaizen'den geçmelidir"). W1'in kapısı erişilebilirlik
içeriyordu. İkili kendi kendine yeterli (yalnızca canlı
`claims`/`authority`/`hash`/`research_debt` bağımlılıkları) ve iade edildi;
erişilebilirlik `PASS (%100)` düzeyine döndü. Kural: gelecekteki hiçbir attic
taşıması, bir anayasal icra aracının adını verdiği dosyayı, önce aracın
yetkisini değiştirmeden kaldıramaz — kapıyı taşımaya uydurmak yasaktır.

## 4. Doğrulama kapıları (kulvarda hepsi yeşil)

- `cargo check`: her taşımadan sonra rc=0, sıfır uyarı.
- Oracle-coverage makbuzu: W2 öncesi/sonrası stdout bayt-bayt aynı.
- Full-audit sertifikası: W2 öncesi/sonrası, 10 adlı duvar-saati alanı
  (`*_duration_sec`, `total_wall_time_sec`, S6 sayaçları) hariç bayt-bayt
  aynı; her artefakt özeti aynı (normalleştirici: `.audit/w2/norm_cert.py`).
- **D-153 mührü** (`.audit/d153_pin/baseline.json`): W1/W2/W3 boyunca
  132/132 değişmedi — BFS sabotaj 24, minerva/pano 3, parite adaptörleri 50,
  makbuz/defter öz-doğrulama 40, d152 duvarı 15.
- Beklenen test-sayısı farkı: attic'e giden iç testler derlemeden çıkar
  (`harness_t1_t12` 13, `checkpoint`/`scorecard`/`evaluation` birim
  testleri). Bu tasfiyedir, regresyon değil; değişmez tablo D-153 mührüdür.

## 5. D-153 değişmezlik kısıtı (kayıtlı kullanıcı yönergesi)

D-153 doğrulama tablosu (D-153 kayıt satırı: BFS-001..024 24/24, #327
15 test, #328 40 test, #329 50 test), Faz-1 veya Faz-2 çalışması sonucu
DEĞİŞMEMELİDİR. Farklı sayı bildiren gelecekteki koşum, yeni bir kararla
hükme bağlanana dek DUR koşuludur, yeniden- taban değil. D-153 satırının
kendisine bu kararla dokunulmamıştır.

## 6. Dirty-911 tasfiyesi: ham taşıma yok, fikirler saklı

Bayat `main@c2539cd8` çatalındaki commitlenmemiş 911 satırlık çalışma
(fonlama uzlaşma yenilemesi, likidasyon `cum`-işaret çevirmesi,
trailing-stop yenilemesi, bölünme-öncesi tek-dosyalı `usdm_sim` düzenine
karşı geçerlik tanıkları) TAŞINMADI: taban `usdm_sim/` bölünmesi ile
D-152/D-156/D-159 öncesidir; taşıma, davranış-koruyan kulvara kayıtsız
davranış değişikliği kaçırır ve §4 demet mührünü hükümsüz kılardı. Yerel
`main` ağacına dokunulmadı. Her yeni iddia bir V8.6 iş kalemi olarak saklıdır
(§7); likidasyon formülü sorusu, kod değişmeden ÖNCE adlı bir venue
şartnamesine karşı hükme bağlanmalıdır.

## 7. Göç programı yetkisi (Faz-2 iş kalemleri)

Bu karar, R#-izlenebilirlikli uygulama issue'larına berat verir: V8.6 §6
(NautilusTrader yürütme altlığı), §14 (venue uygunluk katmanı — fonlama
defteri sahipliği ve likidasyon parite sorusu dahil), §15 (portföy/risk
yetkisi — taşınan trailing-stop iddiası dahil), §18 (göç programı). W14
(diferansiyel halef sorusu), adlı bir halef belirdiğinde W4
`differential.rs` KEEP hükmünü gözden geçirebilecek açık ipliktir.

## 8. Arıza anlambilimi

- W2 mührüne karşı demet sapması → BAŞARISIZ, taşıma geri alınır
  (issue-başı anlambilim geçerlidir).
- D-153 mühür sapması → DUR, yeni karar olmadan yeniden-taban yok (§5).
- Makbuzsuz hüküm → ENGELLİ (W4 kuralı geçerlidir).
- Kayıtsız mimari kod → gölge, birleştirmeyi engeller (AGENTS.md §9).

## 9. Taşınan OPEN_PIN'ler

`OPEN_PIN_GATE_NAMING` (D-152 §5 - D-153 §2, D-159'dan); D-156 kayıtlı
benchmark değerlendiricisi; v2-öncesi defter satırları bağsız; D-116
komisyon/fonlama/terminal-bakiye paritesi eşlenmemiş (likidasyon `cum`-işaret
sorusu da eklendi, §6). Hiçbiri burada hükme bağlanmadı.

Değişen artefaktlar: bu şartname + `docs/tr/D160_V86_PHASE1_EXECUTION_LANE_SPEC.md`,
`docs/decisions/DECISION_REGISTER.md`, `docs/tr/DECISION_REGISTER.md`,
`docs/contracts/IMPLEMENTATION_LAYOUT.md`, `docs/CHANGELOG.md`,
`site/index.html`, `site/tr.html`, `v8-core/attic/*`, kulvar makbuzları
`.audit/{d153_pin,w2,w3,w4,dirty911}/` altında.
